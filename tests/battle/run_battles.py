"""Battle tests (docs/combat.md, milestone E3.2).

1. Scenarios (tests/battle/*.txt): each battle's log must match tests/battle/expected/,
   reviewed by hand, and the sim65 (6502) build must print the same log.
2. Every attack and flee roll is re-checked from the Python reference
   (tools/rules/combat.py): the dice follow the seed, each result follows the TN, and
   each attack's damage follows the weapon, the stat bonus and the target's Soak.
3. Random battles (random maps, fighters and actions, many of them not allowed) run under
   AddressSanitizer and UBSan: no crash, no hang, nobody standing in a wall or a pit.

    python3 tests/battle/run_battles.py [--update]
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

failures = 0
RESULTS = ["fail", "cost", "success", "crit"]


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def run(cmd, timeout=600, env=None):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr


def skill(ch, name):
    s = passport._REG["skills"][name]
    return ch["stats"][s["stat"]] // 2 + ch["training"].get(s["id"], 0)


def fighters(path):
    """What each fighter hits with, from the scenario: (weapon, stat bonus, soak)."""
    out = []
    for line in open(path):
        w = line.split()
        if not w or w[0].startswith("#"):
            continue
        if w[0] == "traveler":
            ch = passport.decode(w[1])
            item = int(w[2])
            arch = combat.ITEMS[item]["archetype"] if item in combat.ITEMS else 0
            melee = arch not in (1, 4)                  # ranged, focus
            out.append((combat.weapon_damage(item), combat.melee_bonus(ch) if melee else 0, 0))
        elif w[0] == "foe":
            v = [int(x) for x in w[2:]]
            out.append((v[8], 0, v[5]))
    return out


def recheck(name, path, log):
    seed = int(next(line.split()[1] for line in open(path) if line.startswith("seed")))
    dice = combat.d100s(seed)
    who = fighters(path)
    last = None
    rolls = 0
    for line in log.splitlines():
        m = re.match(r"  (\d+) attacks (\d+): (\d+)\+(-?\d+)=(-?\d+) vs (\d+): (\w+), (\d+) damage$", line)
        f = re.match(r"  (\d+) tries to flee: (\d+)\+(-?\d+)=(-?\d+) vs (\d+): (\w+)$", line)
        if m:
            a, t, roll, bonus, total, tn, result, dmg = m.groups()
            a, t, roll, total, tn, dmg = int(a), int(t), int(roll), int(total), int(tn), int(dmg)
            if (a, roll, total) != last:                # an area attack shares one roll
                rolls += 1
                want = next(dice)
                if roll != want:
                    fail(f"{name}: roll {rolls} is {roll}, the dice say {want}")
                    return
            last = (a, roll, total)
            if RESULTS[combat.resolve(roll, total, tn)] != result:
                fail(f"{name}: {line.strip()}: the rules say {RESULTS[combat.resolve(roll, total, tn)]}")
            weapon, bonus_, _ = who[a]
            want = combat.damage(roll, total, tn, weapon, bonus_, who[t][2])
            if dmg != want:
                fail(f"{name}: {line.strip()}: the rules say {want} damage")
        elif f:
            last = None
            rolls += 1
            a, roll, bonus, total, tn, result = f.groups()
            if int(roll) != next(dice):
                fail(f"{name}: flee roll {roll} doesn't follow the dice")
                return
            if RESULTS[combat.resolve(int(roll), int(total), int(tn))] != result:
                fail(f"{name}: {line.strip()}: wrong result")
        elif line.startswith("round"):
            last = None                                 # a new turn: a new roll
    return rolls


def scenarios(update):
    for path in sorted(glob.glob(os.path.join(ROOT, "tests", "battle", "*.txt"))):
        name = os.path.basename(path)[:-4]
        _, native, err = run(["build/battle", path])
        if err:
            fail(f"{name}: {err}")
        expected = os.path.join(ROOT, "tests", "battle", "expected", name + ".log")
        if update:
            with open(expected, "w") as f:
                f.write(native)
        elif native != open(expected).read():
            fail(f"{name}: the log differs from tests/battle/expected/{name}.log")
        _, sim, _ = run(["sim65", "build/battle.sim", path])
        if sim != native:
            fail(f"{name}: the 6502 log differs from the native one")
            continue
        rolls = recheck(name, path, native)
        print(f"ok  {name}: native and 6502 logs match, {rolls} roll{'s' * (rolls != 1)} re-checked by the rules")


TILES = "....##O~+^=>"


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
    k = "4PB794AR0A0105AM7HDT8V4000000000K60M2A4A50601902804008ZT0A"
    lines = [f"seed {rng.randrange(65536)}",
             f"surprise {rng.choice(['none', 'foes', 'travelers'])}", "map"]
    lines += ["".join(r) for r in rows] + ["end"]
    for _ in range(travelers):
        lines.append(f"traveler {k} {rng.choice([0, 1, 2, 5, 6, 7])} {rng.randint(1, 40)}")
    for c in letters:
        v = [rng.randint(1, 60), rng.randint(0, 100), rng.randint(0, 20), rng.randint(0, 90),
             rng.randint(0, 90), rng.randint(0, 30), rng.randint(0, 8), rng.randint(0, 100),
             rng.randint(0, 45), rng.randint(0, 1), rng.randint(0, 1), rng.randint(0, 4),
             rng.randint(0, 3), rng.choice([0, 1, 255]), rng.randint(0, 2), rng.randint(0, 1)]
        lines.append(f"foe {c} " + " ".join(map(str, v)))
    for _ in range(rng.randint(5, 60)):
        lines.append(f"act {rng.randint(0, 17)} {rng.randint(0, 11)} {rng.randint(0, 5)} "
                     f"{rng.randint(0, 9)}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return rows


def fuzz(count):
    rng = random.Random(1985)
    path = os.path.join(ROOT, "build", "fuzz-battle.txt")
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:abort_on_error=0",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    endings = {}
    for i in range(count):
        rows = random_battle(rng, path)
        try:
            code, out, err = run(["build/battle.asan", path], timeout=20, env=env)
        except subprocess.TimeoutExpired:
            fail(f"random battle {i} hung")
            continue
        if code or "runtime error" in err or "Sanitizer" in err:
            fail(f"random battle {i}: exit {code}\n{err[-1500:]}")
            continue
        for x, y in re.findall(r"moves to (\d+),(\d+)", out):
            if rows[int(y)][int(x)] in "#O":
                fail(f"random battle {i}: someone moved into a wall or pit at {x},{y}")
        m = re.search(r"the fight is (\w+)", out)
        end = m.group(1) if m else "unfinished"
        endings[end] = endings.get(end, 0) + 1
    print(f"ok  random battles: {count} under the sanitizers, none crashed: "
          + ", ".join(f"{k} {v}" for k, v in sorted(endings.items())))


def main():
    update = "--update" in sys.argv
    scenarios(update)
    fuzz(int(os.environ.get("APB_BATTLE_RUNS", "300")))
    print(f"battle tests: {failures} failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
