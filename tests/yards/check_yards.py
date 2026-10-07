"""The Deep Yards' generator: the C core (core/src/yard.c) against the reference written
from docs/deep-yards.md (tools/yards/yard.py), natively and on sim65.

For pools of foes from the bestiary (all of them, and smaller ones in other orders), the
maps of many yards, floors 0..12 and 255, must be the same bytes. Every map must also be
one the VM accepts (tools/qsc/image.py), with every foe on a square the traveler can
walk to. Picks must agree too, and come out even and independent: two picks on one floor
(the first mixing function paired them off exactly), the same pick on the next floor,
and on the next yard.

    python3 tests/yards/check_yards.py
"""

import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for sub in ("yards", "qsc", "registry"):
    sys.path.insert(0, os.path.join(ROOT, "tools", sub))

import registry  # noqa: E402
import yard  # noqa: E402
from codegen import pool_bytes  # noqa: E402
from image import read_encounter  # noqa: E402

FLOORS = list(range(13)) + [255]
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def run(binary, *args):
    cmd = (["sim65", binary] if binary.endswith(".sim") else [binary]) + [str(a) for a in args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=900).stdout


def reachable_foes(record):
    e = read_encounter(record, "floor")
    w = e["w"]
    start = e["starts"][0]
    seen, todo = {start}, [start]
    while todo:
        x, y = todo.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < e["h"] and (nx, ny) not in seen \
                        and e["tiles"][ny * w + nx] not in (1, 2):
                    seen.add((nx, ny))
                    todo.append((nx, ny))
    return all((f["x"], f["y"]) in seen for f in e["foes"])


def independent():
    """Pairs of picks spread evenly over every combination (within 10%)."""
    import collections
    ys = range(0, 65536, 11)
    pairs = {
        "two picks on one floor": ((yard.pick(y, f, 1, 4), yard.pick(y, f, 2, 4))
                                   for y in ys for f in range(1, 11)),
        "one pick on the next floor": ((yard.pick(y, f, 0, 4), yard.pick(y, f + 1, 0, 4))
                                       for y in ys for f in range(1, 10)),
        "one pick in the next yard": ((yard.pick(y, f, 0, 6), yard.pick(y + 1, f, 0, 6))
                                      for y in ys for f in range(1, 10)),
    }
    for what, gen in pairs.items():
        c = collections.Counter(gen)
        expect = sum(c.values()) / max(1, len(c))
        worst = max(abs(v - expect) / expect for v in c.values())
        if len(c) not in (16, 36) or worst > 0.10:
            fail(f"picks aren't independent: {what}, {len(c)} combinations, {worst:.0%} off even")
    return len(pairs)


def main():
    reg = registry.load()
    foes = list(reg["foes"])
    rng = random.Random(7)
    pools = [foes] + [rng.sample(foes, rng.randrange(1, len(foes) + 1)) for _ in range(5)]
    maps = 0
    for k, names in enumerate(pools):
        pool = pool_bytes(names, reg)
        start, count = rng.randrange(65536), 40
        want = []
        y = start
        for _ in range(count):
            for f in FLOORS:
                want.append(yard.build(y, f, pool).hex())
            y = yard.mix(y, 0x5A5A)
        for record in want:
            maps += 1
            b = bytes.fromhex(record)
            try:
                read_encounter(b, "floor")
            except Exception as e:  # noqa: BLE001
                fail(f"pool {names}: a map the VM would refuse: {e}")
                continue
            if not reachable_foes(b):
                fail(f"pool {names}: a foe the traveler can't reach: {record}")
        for binary, n in (("build/yardgen", count), ("build/yardgen.sim", 3)):
            got = run(binary, pool.hex(), start, n).split()
            if got != want[:len(FLOORS) * n]:
                bad = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), len(got))
                fail(f"{binary}, pool {names}: map {bad} differs from the reference"
                     f"\n  C:      {got[bad] if bad < len(got) else '(none)'}"
                     f"\n  Python: {want[bad]}")
    pairs = independent()
    picks = 0
    for _ in range(300):
        y, key, salt, n = rng.randrange(65536), rng.randrange(256), rng.randrange(255), rng.randrange(1, 256)
        got = run("build/yardgen", "pick", y, key, salt, n).strip()
        if got != str(yard.pick(y, key, salt, n)):
            fail(f"pick {y} {key} {salt} {n}: C says {got}, the reference {yard.pick(y, key, salt, n)}")
        picks += 1
    got = run("build/yardgen.sim", "pick", 48213, 7, 3, 6).strip()
    if got != str(yard.pick(48213, 7, 3, 6)):
        fail(f"a pick on the 6502: {got}")
    print(f"yards: {maps} maps from {len(pools)} pools and {picks} picks agree with the "
          f"reference (natively; a sample on the 6502); {pairs} kinds of pairs of picks "
          f"independent; {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
