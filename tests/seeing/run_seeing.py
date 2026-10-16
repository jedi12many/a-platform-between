"""Seeing and being seen (docs/open-floors.md): the rules lab's core/next/seeing.c against
the reference written from the doc, tools/rules/seeing.py.

1. Hand-worked values, from the doc, not from either implementation: sight ranges, the
   distance's step, lines blocked and through cover, a group's helpers.
2. Reviewed approaches (tests/seeing/*.txt): each one's log must match its reviewed log
   (tests/seeing/expected/), from the reference and from the engine, natively and on
   sim65 (the 6502).
3. Random approaches (maps of walls and cover, parties of 1 to 4, bands, light, paths):
   the engine's log must be the reference's, roll for roll; some on sim65; and under
   AddressSanitizer and UBSan, no complaint.

    python3 tests/seeing/run_seeing.py [--update]   (--update rewrites the reviewed logs
                                                      from the reference: read the diff)
"""

import glob
import os
import random
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HERE = os.path.join(ROOT, "tests", "seeing")
sys.path.insert(0, os.path.join(ROOT, "tools", "rules"))
import combat  # noqa: E402
import seeing  # noqa: E402

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  ", msg)


def numbers(case):
    """The case as seeing_check.c reads it."""
    t, p = case["tiles"], case["party"]
    steps = [case["start"]] + case["path"]
    head = [case["seed"], case["light"], len(t[0]), len(t), int(p["sneaking"]), int(p["light"]),
            len(p["travelers"]), len(case["bands"]), len(steps)]
    out = [" ".join(map(str, head))] + ["".join(map(str, row)) for row in t]
    out += [f"{v['stealth']} {v['notice']}" for v in p["travelers"]]
    out += [f"{b['x']} {b['y']} {b['sense']} {b['stealth']} {int(b['hiding'])}" for b in case["bands"]]
    out += [f"{x} {y}" for x, y in steps]
    return "\n".join(out) + "\n"


def engine(exe, case):
    cmd = ["sim65", exe] if exe.endswith(".sim") else [exe]
    p = subprocess.run(cmd, input=numbers(case), capture_output=True, text=True, cwd=ROOT,
                       timeout=600)
    if p.returncode:
        return None, f"exit {p.returncode}: {p.stderr.strip()[:200]}"
    return p.stdout, None


def hand_worked():
    """Values worked out from the doc by hand."""
    bad = []
    # Range: Notice / 5, doubled by day, halved at night, at least 1.
    for notice, light, want in ((40, seeing.DAY, 16), (40, seeing.DUSK, 8), (40, seeing.NIGHT, 4),
                                (3, seeing.NIGHT, 1), (55, seeing.NIGHT, 5), (0, seeing.DAY, 1)):
        if seeing.sight_range(notice, light) != want:
            bad.append(f"range of Notice {notice} by {seeing.LIGHTS[light]} isn't {want}")
    # Distance: +10 a full 4 squares past the first 4.
    for d, want in ((3, 0), (7, 0), (8, 10), (11, 10), (12, 20), (18, 30)):
        got = sum(v for v, why in seeing.modifiers(seeing.DAY, d, False, False, False, False)
                  if why == "distance")
        if got != want:
            bad.append(f"{d} squares off is {got:+d}, not {want:+d}")
    # Lines: a wall stops one, cover on it counts once, an end's square doesn't.
    m = [[0] * 7 for _ in range(5)]
    m[0][3] = seeing.WALL
    m[2][3] = seeing.COVER
    m[2][5] = seeing.COVER
    m[4][0] = seeing.COVER
    for a, b, want in (((0, 0), (6, 0), None), ((0, 2), (6, 2), True), ((0, 4), (6, 4), False),
                       ((0, 2), (3, 2), False), ((0, 1), (6, 1), False), ((0, 0), (6, 0), None)):
        if seeing.sight(m, *a, *b) != want:
            bad.append(f"the line {a}-{b} is {seeing.sight(m, *a, *b)}, not {want}")
    # The doc's example: a sneaking group, the others rolling 62, 40 and 81 with Stealth 45,
    # 30 and 25 against 100: +10, -10, +10.
    shifts = [seeing.helper_shift(r, combat.resolve(r, r + s, 100), True)
              for r, s in ((62, 45), (40, 30), (81, 25))]
    if shifts != [10, -10, 10]:
        bad.append(f"the doc's helpers move the TN {shifts}, not +10 -10 +10")
    # Looking, the other way round; a cost does nothing; 01 and crits count double.
    for roll, rating, tn, sneaking, want in ((50, 60, 100, False, -10), (10, 40, 100, False, 10),
                                             (85, 0, 100, False, 0), (1, 90, 100, False, 20),
                                             (100, 0, 150, False, -20), (1, 90, 100, True, -20)):
        v = seeing.helper_shift(roll, combat.resolve(roll, roll + rating, tn), sneaking)
        if v != want:
            bad.append(f"a helper rolling {roll} + {rating} against {tn} moves it {v:+d}, not {want:+d}")
    if bad:
        fail("hand-worked: " + "; ".join(bad))
    else:
        ok("hand-worked: ranges by light, the distance's step, lines blocked and through cover, "
           "a group's helpers (the doc's example)")


def reviewed(update):
    cases = sorted(glob.glob(os.path.join(HERE, "*.txt")))
    os.makedirs(os.path.join(HERE, "expected"), exist_ok=True)
    bad = []
    for path in cases:
        name = os.path.basename(path)[:-4]
        case = seeing.parse(path)
        ref = "\n".join(seeing.approach(case)) + "\n"
        exp_path = os.path.join(HERE, "expected", name + ".log")
        if update:
            open(exp_path, "w").write(ref)
        want = open(exp_path).read() if os.path.exists(exp_path) else None
        if want is None:
            bad.append(f"{name}: no reviewed log (run with --update, and read it)")
            continue
        if ref != want:
            bad.append(f"{name}: the reference's log isn't the reviewed one")
        for exe in ("build/seeing-check", "build/seeing-check.sim"):
            got, err = engine(exe, case)
            if err or got != want:
                bad.append(f"{name}: {exe} " + (err or "prints another log:\n" + got))
    if bad:
        fail("reviewed approaches: " + "\n  ".join(bad))
    else:
        ok(f"{len(cases)} reviewed approaches ({', '.join(os.path.basename(c)[:-4] for c in cases)}): "
           "the reference, the engine and the 6502 all print the reviewed log")


def random_case(rnd):
    w, h = rnd.randint(8, 40), rnd.randint(5, 20)
    tiles = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if x in (0, w - 1) or y in (0, h - 1):
                tiles[y][x] = seeing.WALL
            else:
                r = rnd.random()
                tiles[y][x] = (seeing.WALL if r < 0.08 else seeing.COVER if r < 0.16 else
                               rnd.choice([0, 3, 6]) if r < 0.22 else 0)
    free = [(x, y) for y in range(h) for x in range(w) if tiles[y][x] != seeing.WALL]
    start = rnd.choice(free)
    pos, path = start, []
    for _ in range(rnd.randint(1, 40)):
        steps = [(pos[0] + dx, pos[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                 if (dx or dy) and tiles[pos[1] + dy][pos[0] + dx] != seeing.WALL]
        if not steps:
            break
        pos = rnd.choice(steps)
        path.append(pos)
    bands = []
    for _ in range(rnd.randint(1, 6)):
        x, y = rnd.choice(free)
        bands.append({"x": x, "y": y, "sense": rnd.randint(0, 100), "stealth": rnd.randint(0, 100),
                      "hiding": rnd.random() < 0.7})
    n = rnd.randint(1, 4)
    return {"seed": rnd.randint(0, 65535), "light": rnd.randint(0, 2), "tiles": tiles,
            "start": start, "path": path, "bands": bands,
            "party": {"sneaking": rnd.random() < 0.6, "light": rnd.random() < 0.3,
                      "travelers": [{"stealth": rnd.randint(0, 100), "notice": rnd.randint(0, 100)}
                                    for _ in range(n)]}}


def randomly():
    rnd = random.Random(20261016)
    bad, fights, checks = [], 0, 0
    for k in range(400):
        case = random_case(rnd)
        ref = "\n".join(seeing.approach(case)) + "\n"
        fights += "the fight" in ref
        checks += ref.count(" looks\n")
        exes = ["build/seeing-check", "build/seeing-check.asan"] + (["build/seeing-check.sim"] if k % 10 == 0 else [])
        for exe in exes:
            got, err = engine(exe, case)
            if err or got != ref:
                bad.append(f"case {k}: {exe} " + (err or "differs"))
        if len(bad) > 3:
            break
    if bad:
        fail("random approaches: " + "; ".join(bad))
    else:
        ok(f"400 random approaches ({checks} rolled checks, {fights} ending in a fight): the engine's "
           "log is the reference's, natively, under the sanitizers, and every tenth on sim65")


def main():
    update = "--update" in sys.argv
    hand_worked()
    reviewed(update)
    randomly()
    print(f"seeing: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
