"""The standard foe by level (docs/bestiary.md, "A standard foe"), measured in the arena by
rules v1: a traveler of level L of each class against one standard foe of level L, a
thousand fights each.

    python3 tools/arena/standard.py                    the table in docs/bestiary.md
    python3 tools/arena/standard.py --fit              and the health, then the attack, that
                                                       would make each level fair
    python3 tools/arena/standard.py --upto 40          only the rows up to level 40

A standard foe of level L is a fair fight for one traveler of level L: the traveler wins
about 4 times in 5, with something like a third of their health left. The table's rows
are read from docs/bestiary.md, so the doc stays the one place its numbers live; --fit
says what to change them to when the rules move. A foe is kinetic and melee, Speed 4,
charging, its Grace the middle of the table's range; travelers are the arena's quick
builder's, with their gear (tier 1, and one more every 5 levels).
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import arena  # noqa: E402

CLASSES = ["WARDEN", "ROGUE", "TINKER", "CHANNELER", "MEDIC"]
FIGHTS = 1000
WIN = 80            # the traveler wins about 4 times in 5
COLUMNS = ["level", "health", "attack", "damage", "armor", "ward", "soak", "grace"]


def table():
    """The standard foe's rows from docs/bestiary.md: [{level, health, ...}]."""
    rows, inside = [], False
    for line in open(os.path.join(ROOT, "docs", "bestiary.md")):
        if line.startswith("| Level | Health | Attack | Damage | Armor"):
            inside = True
            continue
        if inside and line.startswith("|---"):
            continue
        if inside and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            lo, _, hi = cells[7].partition("-")
            rows.append(dict(zip(COLUMNS, [int(c) for c in cells[:7]] + [(int(lo) + int(hi or lo)) // 2])))
        elif inside:
            break
    return rows


def foe_line(f, x, y):
    """The battle runner's foe line (tools/arena/arena.c) for these numbers: a byte each."""
    health = min(255, f["health"])
    return (f"foe {x} {y} {health} {f['grace']} {f['grace'] // 5} {min(255, f['armor'])} "
            f"{min(255, f['ward'])} {f['soak']} 4 {min(255, f['attack'])} {min(255, f['damage'])} "
            f"0 0 0 0 255 0 0 level {f['level']}")


class Standard(arena.Matchup):
    """One traveler against one standard foe, on the arena's default open floor."""

    def __init__(self, cls, foe):
        super().__init__()
        self.set_rules("next")
        self.fights = FIGHTS
        self.travelers.append(arena.Traveler([cls, str(foe["level"])]))
        self.add_foe("RUST_GUARD")              # a stand-in, replaced by the standard foe
        self.foe = foe

    def file(self):
        text, foes = super().file()
        lines = text.split("\n")
        for i, ln in enumerate(lines):
            if ln.startswith("foe "):
                w = ln.split()
                lines[i] = foe_line(self.foe, w[1], w[2])
        return "\n".join(lines), foes


def measure(foe):
    """{class: (won %, health left %)} for one standard foe."""
    out = {}
    for cls in CLASSES:
        m = Standard(cls, foe)
        results, foes = arena.fight(m)
        won = [r for r in results if r["result"] == "won"]
        health = m.travelers[0].health
        left = sum(r["fighters"][0][0] for r in won) / max(1, len(won)) / max(1, health)
        out[cls] = (round(100 * len(won) / len(results)), round(100 * left))
    return out


def fit(foe):
    """The health, then the attack, that bring the five classes' average to about 4 wins
    in 5: health first (in tenths, a byte at most), as a foe that dies too soon can't be
    made fair by hitting harder; then attack in steps of 5."""
    f = dict(foe)
    avg = lambda f: sum(w for w, _ in measure(f).values()) / len(CLASSES)

    def walk(f, a, key, step, top):
        step = step if a > WIN else -step
        while 0 < f[key] + step <= top:
            g = dict(f, **{key: f[key] + step})
            b = avg(g)
            if (step > 0 and b < WIN) or (step < 0 and b > WIN):
                return (g, b) if abs(b - WIN) < abs(a - WIN) else (f, a)
            f, a = g, b
        return f, a

    f, a = walk(f, avg(f), "health", max(1, foe["health"] // 10), 255)
    f, a = walk(f, a, "attack", 5, 255)
    return f, round(a)


def main(argv):
    if not os.path.exists(arena.ARENA_NEXT):
        print("standard: build the arena first: make build/arena-next")
        return 2
    print("A standard foe of level L against a traveler of level L, rules v1 "
          f"({FIGHTS} fights each): won % (health left %)")
    print("level  " + "  ".join(f"{c.title():>11}" for c in CLASSES) + "   average")
    upto = int(argv[argv.index("--upto") + 1]) if "--upto" in argv else 100
    for foe in table():
        if foe["level"] > upto:
            continue
        got = measure(foe)
        avg = sum(w for w, _ in got.values()) / len(CLASSES)
        print(f"{foe['level']:5d}  " + "  ".join(f"{w:4d}% ({l:3d}%)" for w, l in got.values())
              + f"   {avg:5.0f}%" + ("   (health over 255: kept to a byte)" if foe["health"] > 255 else ""),
              flush=True)
        if "--fit" in argv:
            f, a = fit(foe)
            print(f"       fair: attack {f['attack']} (was {foe['attack']}), health {f['health']} "
                  f"(was {foe['health']}): {a}% on average", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
