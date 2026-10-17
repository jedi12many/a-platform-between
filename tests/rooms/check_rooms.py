"""Rooms (docs/rooms.md): the explore prototype's generator (tools/arena/web/rooms.js, run in
Node) must build the same floors as the reference written from the doc
(tools/rooms/rooms.py), and every floor must keep the doc's promises: every room reached by
its doors, the stairs in the deepest; in each room, every door, the stairs, every foe and
the cache reachable on foot (round walls, pits and hazards) from its first door; the start
room empty; and the people (Vell on every floor, Pell on floors 2 and 3, the parleys) on
open ground and out of everything's way.

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
        # People (docs/rooms.md, People): on open ground, out of everything's way.
        if r["parley"] and r["kind"] != "fight":
            bad.append(f"room {r['i']}: a {r['kind']} room talks first")
        if r["talk"]:
            t = (r["talk"]["x"], r["talk"]["y"])
            if tiles[t[1]][t[0]] != rooms.OPEN or t not in got or t in spots or t == (7, 3):
                bad.append(f"room {r['i']}: {r['talk']['who']} stands at {t}, not free open ground")
            tiles[t[1]][t[0]] = rooms.WALL
            if not all(s in rooms.reached(tiles, *first) for s in spots):
                bad.append(f"room {r['i']}: {r['talk']['who']} at {t} is in the way")
    who = [r["talk"]["who"] for r in f["rooms"] if r["talk"]]
    if who.count("trader") != 1:
        bad.append(f"{who.count('trader')} traders on the floor")
    if who.count("courier") > (1 if f["floor"] in (2, 3) else 0):
        bad.append(f"{who.count('courier')} couriers on floor {f['floor']}")
    return bad



def js_open(cases):
    script = ("const R = require(process.argv[1]); const cases = JSON.parse(process.argv[2]);"
              "console.log(JSON.stringify(cases.map(([y, f]) => R.buildOpen(y, f))));")
    out = subprocess.run(["node", "-e", script, os.path.join(ROOT, "tools", "arena", "web", "rooms.js"),
                          json.dumps(cases)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def open_promises(f):
    """What's wrong with an open floor, by docs/open-floors.md's promises: [] if nothing."""
    bad = []
    w, h = f["w"], f["h"]
    t = [[int(c) for c in row] for row in f["rows"]]
    if (w, h) != rooms.open_size(f["floor"]) or len(t) != h or any(len(r) != w for r in t):
        bad.append(f"{w} x {h}, not floor {f['floor']}'s size")
        return bad
    if any(t[y][x] != rooms.WALL for y in range(h) for x in range(w) if x in (0, w - 1) or y in (0, h - 1)):
        bad.append("the border isn't all wall")
    start, stairs = tuple(f["start"]), tuple(f["stairs"])
    dist = rooms.by_foot(t, start)
    walk = [(x, y) for y in range(h) for x in range(w) if rooms.walkable(t[y][x])]
    if any(q not in dist for q in walk):
        bad.append("not one region: some walkable squares can't be reached from the start")
    if t[stairs[1]][stairs[0]] != rooms.OPEN or dist.get(stairs) != max(dist[q] for q in walk if t[q[1]][q[0]] == rooms.OPEN):
        bad.append("the stairs aren't on the open square farthest from the start")
    if start[0] != min(q[0] for q in walk):
        bad.append("the start isn't on the west side")
    walls = sum(row.count(rooms.WALL) for row in t) - 2 * (w + h) + 4
    if not 0.06 <= walls / ((w - 2) * (h - 2)) <= 0.25:
        bad.append(f"walls are {walls / ((w - 2) * (h - 2)):.2f} of the floor")
    bands = f["bands"]
    if not bands or not bands[0]["stairs"] or bands[0]["parley"] or rooms.crow((bands[0]["x"], bands[0]["y"]), stairs) < 2:
        bad.append("no stairs' band by the stairs (first, not talking)")
    if len(bands) > max(1, len(walk) // 150):
        bad.append(f"{len(bands)} bands, more than one a 150 squares")
    spots = [(b["x"], b["y"]) for b in bands]
    for k, s in enumerate(spots[1:], 1):
        if rooms.crow(s, start) < 10 or any(rooms.crow(s, o) < 10 for o in spots[:k]):
            bad.append(f"band {k} at {s} is nearer than 10 to the start or another band")
    seen = set()
    for b in bands:
        if not b["foes"] or (b["foes"][0]["x"], b["foes"][0]["y"]) != (b["x"], b["y"]) or len(b["foes"]) > 4:
            bad.append(f"band at {(b['x'], b['y'])} has {len(b['foes'])} foes, the first not on its spot")
        for e in b["foes"]:
            q = (e["x"], e["y"])
            if t[q[1]][q[0]] not in rooms.OPEN_STANDS or q not in dist or q in seen or q in (start, stairs):
                bad.append(f"a foe at {q} isn't on a square of its own to stand on")
            seen.add(q)
    things = [(c["x"], c["y"]) for c in f["caches"]] + [(p["x"], p["y"]) for p in f["people"]]
    for q in things:
        if t[q[1]][q[0]] not in rooms.OPEN_STANDS or q not in dist or q in seen or q == stairs:
            bad.append(f"a cache or a person at {q} isn't free ground that can be reached")
    for p in f["people"]:
        q = (p["x"], p["y"])
        if any(rooms.crow(q, s) < 6 for s in spots) or any(rooms.crow(q, e) < 6 for e in seen):
            bad.append(f"{p['who']} at {q} is within 6 of a band")
    who = [p["who"] for p in f["people"]]
    if who.count("trader") != 1 or who.count("courier") != (1 if f["floor"] in (2, 3) else 0):
        bad.append(f"the people are {who}")
    return bad


def check_open(rng):
    """Open floors (docs/open-floors.md): rooms.js's buildOpen as the reference's build_open,
    each keeping the doc's promises."""
    cases = [[rng.randrange(65536), rng.randrange(1, 13)] for _ in range(300)] + [[0, 1], [65535, 255], [48213, 1]]
    js = js_open(cases)
    same, sizes, n_bands, n_foes = 0, {}, 0, 0
    for (y, fl), got in zip(cases, js):
        want = rooms.build_open(y, fl)
        if got != want:
            fail(f"yard {y} floor {fl}: rooms.js builds a different open floor from the reference")
            continue
        same += 1
        for b in open_promises(want):
            fail(f"yard {y} floor {fl} (open): {b}")
        sizes[f"{want['w']}x{want['h']}"] = sizes.get(f"{want['w']}x{want['h']}", 0) + 1
        n_bands += len(want["bands"])
        n_foes += sum(len(b["foes"]) for b in want["bands"])
    print(f"ok   {same} of {len(cases)} open floors the same from rooms.js as from the reference, each keeping "
          f"the doc's promises (" + ", ".join(f"{v} {k}" for k, v in sorted(sizes.items()))
          + f"; {n_bands} bands, {n_foes} foes)")

def fight_cases(rng):
    """Fights on open floors: each band of some random floors, with the leader somewhere
    near it (or anywhere), as (floor, band, leader)."""
    cases = []
    for _ in range(60):
        y, fl = rng.randrange(65536), rng.randrange(1, 13)
        f = rooms.build_open(y, fl)
        for k, b in enumerate(f["bands"]):
            if rng.randrange(4):
                lx = max(0, min(f["w"] - 1, b["x"] + rng.randrange(-9, 10)))
                ly = max(0, min(f["h"] - 1, b["y"] + rng.randrange(-9, 10)))
            else:
                lx, ly = rng.randrange(f["w"]), rng.randrange(f["h"])
            cases.append((y, fl, k, lx, ly))
    return cases


def check_fights(rng):
    """A fight's window and the party's places (docs/open-floors.md, Where the fight is):
    rooms.js's fightWindow and fightPlaces as the reference's."""
    cases = fight_cases(rng)
    script = ("const R = require(process.argv[1]); const cases = JSON.parse(process.argv[2]);"
              "console.log(JSON.stringify(cases.map(([y, f, k, lx, ly]) => {"
              " const o = R.buildOpen(y, f), b = o.bands[k], w = R.fightWindow(b.foes, [lx, ly], o.w, o.h);"
              " const rows = []; for (let j = 0; j < R.H; ++j) rows.push(o.rows[w[1] + j].slice(w[0], w[0] + R.W));"
              " const room = { rows: rows, foes: b.foes.map(e => ({ x: e.x - w[0], y: e.y - w[1] })) };"
              " return [w, R.fightPlaces(room, [lx - w[0], ly - w[1]], 4)]; })));")
    js = json.loads(subprocess.run(["node", "-e", script, os.path.join(ROOT, "tools", "arena", "web", "rooms.js"),
                                    json.dumps(cases)], capture_output=True, text=True, check=True).stdout)
    same, outside = 0, 0
    for (y, fl, k, lx, ly), got in zip(cases, js):
        o = rooms.build_open(y, fl)
        b = o["bands"][k]
        w = rooms.fight_window(b["foes"], (lx, ly), o["w"], o["h"])
        rows = [o["rows"][w[1] + j][w[0]:w[0] + rooms.W] for j in range(rooms.H)]
        room = {"rows": rows, "foes": [{"x": e["x"] - w[0], "y": e["y"] - w[1]} for e in b["foes"]]}
        want = [w, rooms.fight_places(room, (lx - w[0], ly - w[1]), 4)]
        if got != want:
            fail(f"yard {y} floor {fl} band {k + 1}, the leader at {lx},{ly}: rooms.js puts the fight at "
                 f"{got}, the reference at {want}")
            continue
        same += 1
        outside += not (w[0] <= lx < w[0] + rooms.W and w[1] <= ly < w[1] + rooms.H)
    print(f"ok   {same} of {len(cases)} fights' windows and the party's places the same from rooms.js "
          f"as from the reference ({outside} with the leader too far to fit)")


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
            if r["parley"]:
                kinds["parley"] = kinds.get("parley", 0) + 1
            if r["talk"]:
                kinds[r["talk"]["who"]] = kinds.get(r["talk"]["who"], 0) + 1
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
    check_open(rng)
    check_fights(rng)
    print(f"rooms: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
