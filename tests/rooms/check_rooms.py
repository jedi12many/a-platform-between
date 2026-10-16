"""Rooms (docs/rooms.md): the explore prototype's generator (tools/arena/web/rooms.js, run in
Node) must build the same floors as the reference written from the doc
(tools/rooms/rooms.py), and every floor must keep the doc's promises: every room reached by
its doors, the stairs in the deepest; in each room, every door, the stairs, every foe and
the cache reachable on foot (round walls, pits and hazards) from its first door; the start
room empty.

    python3 tests/rooms/check_rooms.py [COUNT]
"""

import json
import os
import random
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "rooms"))
import rooms  # noqa: E402

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL " + msg)


def js_floors(cases):
    script = ("const R = require(process.argv[1]); const cases = JSON.parse(process.argv[2]);"
              "console.log(JSON.stringify(cases.map(([y, f]) => R.build(y, f))));")
    out = subprocess.run(["node", "-e", script, os.path.join(ROOT, "tools", "arena", "web", "rooms.js"),
                          json.dumps(cases)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def js_fans(cases):
    script = ("const R = require(process.argv[1]); const cases = JSON.parse(process.argv[2]);"
              "console.log(JSON.stringify(cases.map(([y, f, i, x, yy, n]) => R.fanOut(R.build(y, f).rooms[i], [x, yy], n))));")
    out = subprocess.run(["node", "-e", script, os.path.join(ROOT, "tools", "arena", "web", "rooms.js"),
                          json.dumps(cases)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def promises(f):
    """What's wrong with a floor, by the doc's promises: [] if nothing."""
    bad = []
    seen, todo = {f["start"]}, [f["start"]]
    while todo:
        i = todo.pop()
        for d in f["rooms"][i]["doors"]:
            j = rooms.neighbour(i, d)
            if rooms.OPPOSITE[d] not in f["rooms"][j]["doors"]:
                bad.append(f"room {i}'s door {d} has no door back")
            if j not in seen:
                seen.add(j)
                todo.append(j)
    if len(seen) != 9:
        bad.append(f"only {len(seen)} rooms can be reached")
    deepest = max(r["depth"] for r in f["rooms"])
    if f["rooms"][f["stairs"]]["depth"] != deepest:
        bad.append("the stairs aren't in the deepest room")
    for r in f["rooms"]:
        tiles = [[int(c) for c in row] for row in r["rows"]]
        first = r["doors"][[d for d, _, _ in rooms.DIRS if d in r["doors"]][0]]
        got = rooms.reached(tiles, *first)
        spots = [tuple(p) for p in r["doors"].values()] + ([tuple(r["stairs"])] if r["stairs"] else [])
        spots += [(e["x"], e["y"]) for e in r["foes"]] + ([(r["cache"]["x"], r["cache"]["y"])] if r["cache"] else [])
        for s in spots:
            if s not in got:
                bad.append(f"room {r['i']}: {s} can't be reached")
        if r["i"] == f["start"] and r["foes"]:
            bad.append("foes in the start room")
        for e in r["foes"]:
            if tiles[e["y"]][e["x"]] not in rooms.STANDS:
                bad.append(f"room {r['i']}: a foe stands on tile {tiles[e['y']][e['x']]}")
    return bad


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    rng = random.Random(1300)
    cases = [[rng.randrange(65536), rng.randrange(1, 13)] for _ in range(count)] + [[0, 1], [65535, 255], [48213, 1]]
    js = js_floors(cases)
    same = 0
    kinds = {}
    for (y, fl), got in zip(cases, js):
        want = rooms.build(y, fl)
        if got != want:
            fail(f"yard {y} floor {fl}: rooms.js builds a different floor from the reference")
            continue
        same += 1
        for b in promises(want):
            fail(f"yard {y} floor {fl}: {b}")
        for r in want["rooms"]:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(f"ok   {same} of {len(cases)} floors the same from rooms.js as from the reference, "
          f"each keeping the doc's promises (rooms: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + ")")
    # The party's fan-out (docs/rooms.md, The party): the page's as the reference's, from
    # every walkable square of random rooms, each traveler on a square of its own that can
    # be stood on.
    fan_cases = []
    for _ in range(300):
        y, fl = rng.randrange(65536), rng.randrange(1, 13)
        f = rooms.build(y, fl)
        r = f["rooms"][rng.randrange(9)]
        spots = [(x, yy) for yy in range(1, 7) for x in range(1, 15)
                 if int(r["rows"][yy][x]) in rooms.STANDS and not any(e["x"] == x and e["y"] == yy for e in r["foes"])]
        x, yy = rng.choice(spots)
        fan_cases.append([y, fl, r["i"], x, yy, rng.randrange(1, 5)])
    fans = js_fans(fan_cases)
    fan_ok = 0
    for (y, fl, i, x, yy, n), got in zip(fan_cases, fans):
        r = rooms.build(y, fl)["rooms"][i]
        want = rooms.fan_out(r, (x, yy), n)
        if got != want:
            fail(f"yard {y} floor {fl} room {i}: the page fans a party of {n} out to {got}, the reference to {want}")
        elif len({tuple(p) for p in got}) != len(got) or len(got) != n or any(
                int(r["rows"][q[1]][q[0]]) not in rooms.STANDS for q in got[1:]):
            fail(f"yard {y} floor {fl} room {i}: the fan-out {got} isn't {n} squares of their own to stand on")
        else:
            fan_ok += 1
    print(f"ok   {fan_ok} of {len(fan_cases)} parties fanned out the same by the page as by the reference, "
          f"each on squares of their own")
    print(f"rooms: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
