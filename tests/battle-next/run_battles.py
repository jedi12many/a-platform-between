"""The rules lab's tests (docs/turn.md): rules v1's battle engine, core/next/battle.c.

1. Scenarios (tests/battle-next/*.txt): each battle's log must match
   tests/battle-next/expected/, reviewed by hand, and the sim65 (6502) build must print
   the same log, so the engine can replace v0's on the C64 at the freeze.
2. Every roll is re-checked: the dice follow the seed; each result follows the TN; each
   attack's damage and each condition's damage at a turn's start follow the rules
   (tools/rules/combat.py, tools/rules/turn.py): the weapon, the stat bonus, Soak, a
   weakness, a barrier; each shake-off is against its condition's TN.
3. The engine and the reference agree on random fighters with random conditions put on
   in random order (tests/battle-next/turn_check.c): Speed v1, Speed, Dodge, Armor, Ward
   and Soak with their conditions counted, and which conditions it has (the same twice,
   opposites, immunity, the limit of four).
4. Random battles (maps, hazards, fighters, conditions and actions, many not allowed) run
   under AddressSanitizer and UBSan: no crash, no hang, nobody standing in a wall.

    python3 tests/battle-next/run_battles.py [--update]
"""

import glob
import os
import random
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "rules"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))

import combat  # noqa: E402
import passport  # noqa: E402
import turn  # noqa: E402

failures = 0
RESULTS = ["fail", "cost", "success", "crit"]
HERE = os.path.join(ROOT, "tests", "battle-next")
VULNERABLE = {c["tag"]: c["effects"]["vulnerable"] for c in turn.CONDS.values()
              if "vulnerable" in c["effects"]}


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def run(cmd, timeout=600, env=None, stdin=None):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=timeout, env=env,
                       input=stdin)
    return p.returncode, p.stdout, p.stderr


def fighters(path):
    """What each fighter hits with, from the scenario: (weapon, stat bonus, damage type)."""
    out = []
    for line in open(path):
        w = line.split()
        if not w or w[0].startswith("#"):
            continue
        if w[0] == "traveler":
            ch = passport.decode(w[1])
            item = int(w[2])
            it = combat.ITEMS.get(item)
            arch = it["archetype"] if it and it["tier"] else 0
            melee = arch not in (1, 4)                  # ranged, focus
            out.append((combat.weapon_damage(item) if it and it["tier"] else combat.UNARMED,
                        combat.melee_bonus(ch) if melee else 0, it["damage"] if it and it["tier"] else 0))
        elif w[0] == "foe":
            v = [int(x) for x in w[2:18]]
            out.append((v[8], 0, v[11]))
    return out


def levels(path):
    """Each fighter's level, in the order they join: a traveler's from its Passport, a
    foe's from its line (1 if not said)."""
    out = []
    for line in open(path):
        w = line.split()
        if w and w[0] == "traveler":
            out.append(passport.decode(w[1])["level"])
        elif w and w[0] == "foe":
            out.append(int(w[w.index("level") + 1]) if "level" in w else 1)
    return out


def resists(path):
    """Every Resist a condition can be put on with (docs/turn.md): twice each fighter's
    level (a foe's from its line, else 1), and 0 for a hazard's or the scenario's."""
    out = {0}
    for line in open(path):
        w = line.split()
        if w and w[0] == "traveler":
            out.add(2 * passport.decode(w[1])["level"])
        elif w and w[0] == "foe":
            out.add(2 * (int(w[w.index("level") + 1]) if "level" in w else 1))
    return out


def absorbed(lines, i, who):
    """The barrier lines just before line i for fighter `who`: what they took."""
    took = 0
    j = i - 1
    while j >= 0:
        m = re.match(r"  (\d+)'s barrier takes (\d+)$", lines[j])
        if not m:
            if re.match(r"  \d+ is no longer BARRIER$", lines[j]):
                j -= 1
                continue
            break
        if int(m.group(1)) == who:
            took += int(m.group(2))
        j -= 1
    return took


def recheck(name, path, log):
    seed = int(next(line.split()[1] for line in open(path) if line.startswith("seed")))
    dice = combat.d100s(seed)
    who = fighters(path)
    resists_ = resists(path)
    lv = levels(path)
    last = None
    rolls = 0
    tiers = {}
    ranks = {}
    for ln in open(path):
        w = ln.split()
        if w and w[0] == "power":
            ranks[(int(w[1]), w[2])] = int(w[3])
    lines = log.splitlines()
    for i, line in enumerate(lines):
        a = re.match(r"  (\d+) attacks (\d+): (\d+)\+(-?\d+)=(-?\d+) vs (\d+): (\w+), (\d+) damage "
                     r"\[soak (\d+)([A-Z ]*)\]$", line)
        r = re.match(r"  (\d+) (?:tries to flee|shoves \d+|tries to shake off (\w+)): "
                     r"(\d+)\+(-?\d+)=(-?\d+) vs (\d+): (\w+)$", line)
        t = re.match(r"  (\d+) takes (\d+) from (\w+) \[soak (\d+)([A-Z ]*)\]$", line)
        u = re.match(r"  (\d+) uses (\w+) \(tier (\d+)\)", line)
        h = re.match(r"  (\d+)'s (\w+) on (\d+): (\d+)\+(-?\d+)=(-?\d+) vs (\d+): (\w+), (\d+) damage "
                     r"\[soak (\d+)([A-Z ]*)\]$", line)
        if u:
            tiers[int(u.group(1))] = int(u.group(3))
            if int(u.group(3)) != turn.power_tier(ranks.get((int(u.group(1)), u.group(2)), 0)):
                fail(f"{name}: {line.strip()}: the rank says tier "
                     f"{turn.power_tier(ranks.get((int(u.group(1)), u.group(2)), 0))}")
            last = None
            continue
        if h:
            att, pw, tgt, roll, _, total, tn, result, dmg, soak, tags = h.groups()
            att, tgt, roll, total, tn, dmg, soak = map(int, (att, tgt, roll, total, tn, dmg, soak))
            if (att, roll, total) != last:
                rolls += 1
                want = next(dice)
                if roll != want:
                    fail(f"{name}: roll {rolls} is {roll}, the dice say {want}")
                    return rolls
            last = (att, roll, total)
            if RESULTS[combat.resolve(roll, total, tn)] != result:
                fail(f"{name}: {line.strip()}: the rules say {RESULTS[combat.resolve(roll, total, tn)]}")
            p = turn.POWERS[pw]
            if (registry_shape(p) == "hex" or p["element"] == 4) \
                    and tn not in (turn.resist_tn(lv[tgt]), turn.resist_tn(lv[tgt], True)):
                fail(f"{name}: {line.strip()}: a hex is against Resist: 50 + {turn.resist(lv[tgt])}")
            want = 0
            if registry_shape(p) in ("bolt", "burst", "hex"):
                kind = p["element"]
                base = (turn.hex_damage if registry_shape(p) == "hex" else turn.power_damage)(tiers[att])
                want = combat.damage(roll, total, tn, base, 0,
                                     0 if kind == 1 else soak)
                if kind is not None and any(VULNERABLE.get(tg) == kind for tg in tags.split()):
                    want *= 2
                want -= absorbed(lines, i, tgt)
            if dmg != want:
                fail(f"{name}: {line.strip()}: the rules say {want} damage")
            continue
        if a:
            att, tgt, roll, _, total, tn, result, dmg, soak, tags = a.groups()
            att, tgt, roll, total, tn, dmg, soak = map(int, (att, tgt, roll, total, tn, dmg, soak))
            if (att, roll, total) != last:
                rolls += 1
                want = next(dice)
                if roll != want:
                    fail(f"{name}: roll {rolls} is {roll}, the dice say {want}")
                    return rolls
            last = (att, roll, total)
            if RESULTS[combat.resolve(roll, total, tn)] != result:
                fail(f"{name}: {line.strip()}: the rules say {RESULTS[combat.resolve(roll, total, tn)]}")
            weapon, bonus, kind = who[att]
            want = combat.damage(roll, total, tn, weapon, bonus, soak)
            if any(VULNERABLE.get(tg) == kind for tg in tags.split()):
                want *= 2
            want -= absorbed(lines, i, tgt)
            if dmg != want:
                fail(f"{name}: {line.strip()}: the rules say {want} damage")
        elif r:
            last = None
            rolls += 1
            _, cond, roll, _, total, tn, result = r.groups()
            if int(roll) != next(dice):
                fail(f"{name}: {line.strip()}: the roll doesn't follow the dice")
                return rolls
            if RESULTS[combat.resolve(int(roll), int(total), int(tn))] != result:
                fail(f"{name}: {line.strip()}: wrong result")
            # Against its number + the Resist of whoever put it on (a fighter's, or 0).
            if cond and int(tn) - turn.CONDS[cond]["shake"] not in resists_:
                fail(f"{name}: {line.strip()}: {cond} is shaken off against "
                     f"{turn.CONDS[cond]['shake']} + a Resist ({sorted(resists_)})")
        elif t and t.group(3) in turn.CONDS:
            f, dmg, cond, soak, tags = t.groups()
            n, kind = turn.CONDS[cond]["effects"]["dot"]
            want = n if kind is None else max(0, n - int(soak))
            if kind is not None and any(VULNERABLE.get(tg) == kind for tg in tags.split()):
                want *= 2
            want -= absorbed(lines, i, int(f))
            if int(dmg) != want:
                fail(f"{name}: {line.strip()}: the rules say {want}")
        elif line.startswith("round") or "gets a free attack" in line:
            last = None
    return rolls


def registry_shape(p):
    return turn.registry.SHAPES[p["shape"]]


def scenarios(update):
    for path in sorted(glob.glob(os.path.join(HERE, "*.txt"))):
        name = os.path.basename(path)[:-4]
        _, log, err = run(["build/battle-next", path])
        if err:
            fail(f"{name}: {err}")
        expected = os.path.join(HERE, "expected", name + ".log")
        if update:
            with open(expected, "w") as f:
                f.write(log)
        elif not os.path.exists(expected) or log != open(expected).read():
            fail(f"{name}: the log differs from tests/battle-next/expected/{name}.log")
            continue
        _, sim, _ = run(["sim65", "build/battle-next.sim", path])
        if sim != log:
            fail(f"{name}: the 6502 log differs from the native one")
            continue
        rolls = recheck(name, path, log)
        print(f"ok  {name}: the reviewed log, the same on the 6502, {rolls} roll{'s' * (rolls != 1)} "
              "re-checked by the rules")


def agree(count):
    """The engine and tools/rules/turn.py, on random fighters and conditions."""
    rng = random.Random(2026)
    timed = [c for c in turn.CONDS.values() if "race" not in c["effects"]]
    races = list(turn.REG["races"])
    cases, wants = [], []
    for _ in range(count):
        grace, tier = rng.randint(0, 100), rng.randint(0, 4)
        race = rng.choice(races + [None])
        base = [rng.randint(0, 8), rng.randint(0, 20), rng.randint(0, 40), rng.randint(0, 40),
                rng.randint(0, 4)]
        put = [(rng.choice(timed)["name"], rng.randint(1, 6)) for _ in range(rng.randint(0, 7))]
        f = turn.Fighter(race, *base)
        for n, t in put:
            f.put(n, t)
        rid = turn.REG["races"][race]["id"] if race else 255
        cases.append(" ".join(map(str, [grace, tier, rid] + base))
                     + "".join(f" {turn.CONDS[n]['id']}:{t}" for n, t in put))
        ids = [turn.CONDS[n]["id"] for n in f.traits] + [turn.CONDS[o[0]]["id"] for o in f.slots if o]
        wants.append(f"{turn.speed_v1(grace, tier)} {f.speed()} {f.dodge()} {f.armor()} {f.ward()} "
                     f"{f.soak()}:" + "".join(f" {i}" for i in ids))
    _, out, err = run(["build/turn-check"], stdin="\n".join(cases) + "\n")
    got = out.splitlines()
    bad = [(c, w, g) for c, w, g in zip(cases, wants, got) if w != g]
    if err or len(got) != count:
        fail(f"turn-check: {err or 'gave ' + str(len(got)) + ' answers to ' + str(count) + ' cases'}")
    elif bad:
        c, w, g = bad[0]
        fail(f"{len(bad)} of {count} random fighters differ, the first: case '{c}': the reference "
             f"says '{w}', the engine '{g}'")
    else:
        print(f"ok  the engine and tools/rules/turn.py agree on {count} random fighters: Speed, "
              "Dodge, Armor, Ward, Soak, and the conditions they have, at random tiers")


TILES = "......##O~+^=>"


def random_battle(rng, path):
    w, h = rng.randint(3, 16), rng.randint(3, 10)
    rows = [[rng.choice(TILES) for _ in range(w)] for _ in range(h)]
    spots = [(x, y) for y in range(h) for x in range(w)]
    rng.shuffle(spots)
    travelers = rng.randint(1, 3)
    foes = rng.randint(1, 5)
    letters = "abcde"[:foes]
    for i, (x, y) in enumerate(spots[:travelers + foes]):
        rows[y][x] = "@" if i < travelers else letters[i - travelers]
    names = list(turn.CONDS)
    k = rng.choice(["4PB794AR084102VANND8CJT000000000E64M4A3N50202G1FKWP",
                    "4542T0000A0105APR5DFA26000000001H60M8A5V5020180615T",
                    "4TZ8G0000C4102V0NNDYHJT000000000E64M4A3T50202G1VY14",
                    "4KDJ000006C1026PP9QKNAT000000030264MMABH50203006BX6"])
    lines = [f"seed {rng.randrange(65536)}",
             f"surprise {rng.choice(['none', 'foes', 'travelers'])}", "map"]
    lines += ["".join(r) for r in rows] + ["end"]
    lines.append(f"hazard {rng.randint(0, 9)} {rng.choice(['kinetic', 'energy', 'fire', 'cold', 'none'])} "
                 f"{rng.choice(names + ['-'])}")
    for _ in range(travelers):
        lines.append(f"traveler {k} {rng.choice([0, 5, 9, 10, 11, 12])} {rng.randint(1, 40)}")
    for c in letters:
        v = [rng.randint(1, 60), rng.randint(0, 100), rng.randint(0, 20), rng.randint(0, 90),
             rng.randint(0, 90), rng.randint(0, 30), rng.randint(0, 8), rng.randint(0, 100),
             rng.randint(0, 45), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 4),
             rng.randint(0, 3), rng.choice([0, 1, 255]), rng.randint(0, 2), rng.randint(0, 1)]
        hit = f" hit {rng.choice(names)}" if rng.random() < 0.5 else ""
        lines.append(f"foe {c} " + " ".join(map(str, v)) + hit)
    for _ in range(rng.randint(0, 6)):
        lines.append(f"{rng.choice(['put', 'put', 'trait'])} {rng.randint(0, 9)} {rng.choice(names)}")
    for _ in range(rng.randint(0, 6)):
        lines.append(f"power {rng.randint(0, travelers - 1)} {rng.choice(list(turn.POWERS))} {rng.randint(0, 100)}")
    for _ in range(rng.randint(5, 60)):
        if rng.random() < 0.2:
            lines.append("act q")
        else:
            lines.append(f"act {rng.randint(0, 17)} {rng.randint(0, 11)} {rng.randint(0, 8)} "
                         f"{rng.randint(0, 9)} {rng.randint(0, 17)} {rng.randint(0, 11)} {rng.randint(0, 4)}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return rows


def fuzz(count):
    rng = random.Random(1986)
    path = os.path.join(ROOT, "build", "fuzz-battle-next.txt")
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:abort_on_error=0",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    endings = {}
    for i in range(count):
        rows = random_battle(rng, path)
        try:
            code, out, err = run(["build/battle-next.asan", path], timeout=20, env=env)
        except subprocess.TimeoutExpired:
            fail(f"random battle {i} hung")
            continue
        if code or "runtime error" in err or "Sanitizer" in err:
            fail(f"random battle {i}: exit {code}\n{err[-1500:]}")
            continue
        for x, y in re.findall(r"(?:steps|is pushed|is shifted) to (\d+),(\d+)", out):
            if rows[int(y)][int(x)] == "#":
                fail(f"random battle {i}: someone stood in a wall at {x},{y}")
        m = re.search(r"the fight is (\w+)", out)
        end = m.group(1) if m else "unfinished"
        endings[end] = endings.get(end, 0) + 1
    print(f"ok  random battles: {count} under the sanitizers, none crashed: "
          + ", ".join(f"{k} {v}" for k, v in sorted(endings.items())))


def main():
    update = "--update" in sys.argv
    scenarios(update)
    agree(int(os.environ.get("APB_TURN_CASES", "3000")))
    fuzz(int(os.environ.get("APB_BATTLE_RUNS", "400")))
    print(f"rules lab: {failures} failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
