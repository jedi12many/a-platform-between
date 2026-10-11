"""The arena (tools/arena/, docs/arena.md) against what's already checked.

1. Its fights are the battle engine's: a fight from build/arena, played again through the
   battle tests' own runner (build/battle, tests/battle/battle.c) from the same seed, with
   every traveler on quick, has the same blows in the same order (attacker, target, roll,
   TN, damage) and the same ending, for a melee, a ranged and a power-using traveler, alone
   and in a party, against one foe and several. (Its gear is a registry item's, so both
   runners arm it the same way.)
2. The quick builder makes characters by the rules: a valid Passport, the point-buy spent
   (150 points, none over 70), the race's and class's bonuses, the right level, no
   training over 100, and every level's stat point spent.

    python3 tests/arena/check_arena.py      (make test-combat; needs build/arena, build/battle)
"""

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))
import arena  # noqa: E402

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  ", msg)


# The weapons both runners can arm: (the arena's weapon words, the registry item's id).
ITEMS = {"melee": ("weapon melee 1 kinetic armor 0", 5),        # RUSTED_SABRE
         "ranged": ("weapon ranged 4 energy armor 0", 1),       # PULSE_RIFLE
         "focus": ("weapon focus 2 mind armor 0", 6)}           # MERIDIAN_CORE

MATCHUPS = [
    (["Warden 1 melee"], ["RUST_GUARD"]),
    (["Rogue 2 ranged"], ["ASH_RAT x3"]),
    (["Channeler 3 focus"], ["MAINT_DRONE"]),
    (["Warden 4 melee", "Channeler 4 focus", "Rogue 4 ranged"], ["RUST_GUARD x2", "SCRAP_GUNNER x2"]),
]


def blows(log):
    """The attacks in a log, either runner's: (attacker, target, roll, total, TN, damage)."""
    out = [tuple(map(int, m)) for m in re.findall(
        r"(\d+) attacks (\d+): (\d+)\+-?\d+=(-?\d+) vs (-?\d+)(?:: \w+)?, (\d+) damage", log)]
    end = re.findall(r"the fight is (\w+)", log)
    return out, end[-1] if end else None


def main():
    n = 0
    for travelers, foes in MATCHUPS:
        m = arena.Matchup()
        weapons = []
        for t in travelers:
            words = t.split()
            weapons.append(ITEMS[words[-1]][1])
            m.travelers.append(arena.Traveler(words[:-1] + ITEMS[words[-1]][0].split()))
        for f in foes:
            m.add_foe(f)
        text, _ = m.file()
        for i in range(8):
            m.seed = 100 + 37 * i
            log, _ = arena.fight(m, 0)
            text, _ = m.file()
            lines = text.split("\n")
            w, h = map(int, lines[3].split()[1:])
            rows = lines[4:4 + h]
            scenario = [f"seed {m.seed}", "map"] + [list(r) for r in rows]
            fighters = lines[4 + h:]
            letters = iter("abcdefgh")
            out = []
            for ln in fighters:
                p = ln.split()
                if not p:
                    continue
                x, y = int(p[1]), int(p[2])
                if p[0] == "traveler":
                    scenario[2 + y][x] = "@"
                    out.append(f"traveler {p[3]} {weapons[len(out)]}")
                else:
                    c = next(letters)
                    scenario[2 + y][x] = c
                    out.append(f"foe {c} " + " ".join(p[3:7]) + " " + " ".join(p[7:]))
            scenario = scenario[:2] + ["".join(r) for r in scenario[2:]] + ["end"] + out
            scenario += ["act q"] * 300
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
                f.write("\n".join(scenario) + "\n")
                path = f.name
            p = subprocess.run([os.path.join(ROOT, "build", "battle"), path], capture_output=True,
                               text=True)
            os.unlink(path)
            if "not allowed" in p.stdout or "couldn't place" in p.stdout:
                fail(f"{travelers} vs {foes}, seed {m.seed}: the battle runner refused a move")
            a, b = blows(log), blows(p.stdout)
            if a != b or not a[0]:
                fail(f"{travelers} vs {foes}, seed {m.seed}: the arena's fight isn't the battle "
                     f"runner's: {a[1]} after {len(a[0])} blows, {b[1]} after {len(b[0])}")
            n += 1
    if not failures:
        ok(f"the arena's fights are the battle engine's, blow for blow ({n} fights, "
           f"{len(MATCHUPS)} matchups, every traveler on quick)")

    bad = 0
    for cls in arena.PLANS:
        for level in (1, 2, 7, 25, 60, 100):
            ch = arena.build(cls, level)
            reg = arena.REG
            try:
                again = arena.passport.decode(arena.passport.encode(ch))
            except arena.passport.PassportError as e:
                fail(f"{cls} {level}: not a valid Passport: {e}")
                bad += 1
                continue
            race = reg["races"][arena.DEFAULT_RACE[cls]]
            c = reg["classes"][cls]
            bonus = [0] * 6
            bonus[race["bonus"]] += 10
            bonus[c["bonus"]] += 5
            base = [s - b for s, b in zip(arena.build(cls, 1)["stats"], bonus)]
            if (again["level"] != level or not arena.passport.pointbuy_ok(base)
                    or sum(ch["stats"]) - sum(arena.build(cls, 1)["stats"]) != min(level - 1, sum(
                        100 - s for s in arena.build(cls, 1)["stats"]))
                    or any(t > 100 for t in ch["training"].values())
                    or not set(c["tags"]) <= set(ch["tags"])):
                fail(f"{cls} {level}: not built by the rules: {arena.passport.describe(ch)}")
                bad += 1
    if not bad:
        ok(f"the quick builder's characters keep the rules ({len(arena.PLANS)} classes, levels 1-100)")
    print(f"arena: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
