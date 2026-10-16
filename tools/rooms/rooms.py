"""A floor of rooms (docs/rooms.md), written from the doc, independently of the prototype's
generator (tools/arena/web/rooms.js), so tests can check one against the other.

    python3 tools/rooms/rooms.py show YARD FLOOR      draw a floor's rooms
    python3 tools/rooms/rooms.py json YARD FLOOR      the floor as JSON (what rooms.js builds)
    python3 tools/rooms/rooms.py open YARD FLOOR      an open floor (docs/open-floors.md)
    python3 tools/rooms/rooms.py open-json YARD FLOOR  ... as JSON (rooms.js's buildOpen)

A yard is a number 0..65535 and a floor 1..255; the same two always build the same rooms.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "yards"))
from yard import xs, mix  # noqa: E402

COLS, ROWS = 3, 3
W, H = 16, 8
DIRS = [("N", 0, -1), ("E", 1, 0), ("S", 0, 1), ("W", -1, 0)]
OPPOSITE = {"N": "S", "E": "W", "S": "N", "W": "E"}
TERRAIN = [3, 3, 4, 4, 6, 2, 1, 5]      # rough, rough, cover, cover, high, pit, wall, hazard
POOL = ["ASH_RAT", "SCRAP_GUNNER", "RUST_GUARD", "MAINT_DRONE"]
CACHE = ["IRON_SWORD", "ARC_PISTOL", "CHAIN_COAT", "PULSE_RIFLE", "BALLISTIC_WEAVE"]
STAIRS = (7, 3)
OPEN, WALL, PIT, HAZARD, DOOR = 0, 1, 2, 5, 7
STANDS = (0, 3, 4, 6)                  # open, rough, cover, high ground


def neighbour(i, d):
    """The room next to room i in direction d, or None."""
    cx, cy = i % COLS, i // COLS
    _, dx, dy = next(x for x in DIRS if x[0] == d)
    nx, ny = cx + dx, cy + dy
    return ny * COLS + nx if 0 <= nx < COLS and 0 <= ny < ROWS else None


def reached(tiles, sx, sy):
    """Every square reachable from (sx, sy), 8 ways, through anything but wall, pit and hazard
    (out of a fight, you go round those)."""
    seen, todo = {(sx, sy)}, [(sx, sy)]
    while todo:
        x, y = todo.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in seen and tiles[ny][nx] not in (WALL, PIT, HAZARD):
                    seen.add((nx, ny))
                    todo.append((nx, ny))
    return seen


def build(yard, floor):
    """The floor: {yard, floor, start, stairs, rooms: [...]} (docs/rooms.md, A floor)."""
    state = mix((yard ^ 0x5A5A) & 0xFFFF, (floor * 256 + 255) & 0xFFFF)

    def r(n):
        nonlocal state
        state = xs(state)
        return state % n

    n_rooms = COLS * ROWS
    doors = [dict() for _ in range(n_rooms)]       # room -> {dir: (x, y)} once placed; here: set

    def open_door(i, d):
        j = neighbour(i, d)
        doors[i][d] = None
        doors[j][OPPOSITE[d]] = None

    # 1. The start.
    start = r(3) * COLS
    # 2. The maze.
    stack, seen = [start], {start}
    while stack:
        c = stack[-1]
        opts = [d for d, _, _ in DIRS if neighbour(c, d) is not None and neighbour(c, d) not in seen]
        if not opts:
            stack.pop()
            continue
        d = opts[r(len(opts))]
        open_door(c, d)
        n = neighbour(c, d)
        seen.add(n)
        stack.append(n)
    # 3. Two more doors.
    for _ in range(2):
        i, d = r(n_rooms), DIRS[r(4)][0]
        if neighbour(i, d) is not None and d not in doors[i]:
            open_door(i, d)
    # 4. Depth, and the stairs.
    depth = {start: 0}
    queue = [start]
    while queue:
        c = queue.pop(0)
        for d, _, _ in DIRS:
            if d in doors[c] and neighbour(c, d) not in depth:
                depth[neighbour(c, d)] = depth[c] + 1
                queue.append(neighbour(c, d))
    stairs = max(range(n_rooms), key=lambda i: (depth[i], -i))
    # 5. Where the doors are.
    for i in range(n_rooms):
        if "E" in doors[i]:
            y = 1 + r(6)
            doors[i]["E"] = (W - 1, y)
            doors[neighbour(i, "E")]["W"] = (0, y)
        if "S" in doors[i]:
            x = 1 + r(14)
            doors[i]["S"] = (x, H - 1)
            doors[neighbour(i, "S")]["N"] = (x, 0)
    # 6. Each room.
    rooms = []
    for i in range(n_rooms):
        tiles = [[WALL if x in (0, W - 1) or y in (0, H - 1) else OPEN for x in range(W)] for y in range(H)]
        sides = [d for d, _, _ in DIRS if d in doors[i]]
        for d in sides:
            x, y = doors[i][d]
            tiles[y][x] = DOOR
        here_stairs = STAIRS if i == stairs else None
        first = doors[i][sides[0]]
        must = [doors[i][d] for d in sides] + ([here_stairs] if here_stairs else [])
        for _ in range(3 + r(4) + min(depth[i], 3)):
            x, y, t = 2 + r(12), 2 + r(4), TERRAIN[r(8)]
            if tiles[y][x] != OPEN or (x, y) == here_stairs:
                continue
            tiles[y][x] = t
            got = reached(tiles, *first)
            if not all(m in got for m in must):
                tiles[y][x] = OPEN
        got = reached(tiles, *first)
        if i == start:
            kind = "start"
        elif i == stairs:
            kind = "stairs"
        else:
            kind = ["fight", "fight", "fight", "cache", "empty", "empty"][r(6)]
        foes, cache = [], None

        def square(far):
            taken = {(f["x"], f["y"]) for f in foes}

            def fits(x, y, near_ok):
                return (tiles[y][x] in STANDS and (x, y) in got and (x, y) != here_stairs
                        and (x, y) not in taken
                        and (near_ok or all(max(abs(x - dx), abs(y - dy)) >= 3
                                            for dx, dy in (doors[i][d] for d in sides))))
            for _ in range(32):
                x, y = 2 + r(12), 1 + r(6)
                if fits(x, y, not far):
                    return x, y
            for y in range(1, 7):
                for x in range(2, 14):
                    if fits(x, y, True):
                        return x, y
            return None

        if kind in ("fight", "stairs"):
            g = floor + depth[i] // 2                 # the danger
            n = min(4, 1 + g // 3 + (kind == "stairs"))
            L = min(4, 1 + g // 2)
            for _ in range(n):
                name = POOL[r(L)]
                at = square(True)
                if at:
                    foes.append({"name": name, "x": at[0], "y": at[1]})
        elif kind == "cache":
            item = CACHE[r(len(CACHE))]
            at = square(False)
            if at:
                cache = {"item": item, "x": at[0], "y": at[1]}
        rooms.append({"i": i, "depth": depth[i], "kind": kind,
                      "rows": ["".join(str(t) for t in row) for row in tiles],
                      "doors": {d: list(doors[i][d]) for d in sides},
                      "stairs": list(here_stairs) if here_stairs else None,
                      "foes": foes, "cache": cache})
    people(yard, floor, rooms)
    return {"yard": yard, "floor": floor, "start": start, "stairs": stairs, "rooms": rooms}


def spot(room):
    """Where someone stands in a room (docs/rooms.md, People): the open square nearest
    (8, 3), counting 8 ways, then the topmost, then the leftmost; reachable from the
    room's first door; not a door, the stairs, a foe's or the cache's square, or (7, 3),
    where you arrive on a floor; and not in the way: with someone standing there, every
    door, the stairs, the cache and every foe can still be reached from the first door."""
    tiles = [[int(c) for c in r] for r in room["rows"]]
    first = room["doors"][[d for d, _, _ in DIRS if d in room["doors"]][0]]
    got = reached(tiles, *first)
    taken = {(f["x"], f["y"]) for f in room["foes"]} | {(7, 3)}
    must = [tuple(p) for p in room["doors"].values()] + [(f["x"], f["y"]) for f in room["foes"]]
    if room["stairs"]:
        taken.add(tuple(room["stairs"]))
        must.append(tuple(room["stairs"]))
    if room["cache"]:
        taken.add((room["cache"]["x"], room["cache"]["y"]))
        must.append((room["cache"]["x"], room["cache"]["y"]))
    order = sorted((max(abs(x - 8), abs(y - 3)), y, x) for y in range(H) for x in range(W)
                   if tiles[y][x] == OPEN and (x, y) in got and (x, y) not in taken)
    for _, y, x in order:
        tiles[y][x] = WALL
        clear = reached(tiles, *first)
        tiles[y][x] = OPEN
        if all(m in clear for m in must):
            return [x, y]
    return None


def people(yard, floor, rooms):
    """Who's in the rooms besides foes (docs/rooms.md, People): Vell's camp, the courier
    Pell on floors 2 and 3, and which fights start with a parley. Decided after the rooms
    are built, without their dice: the same yard and floor, the same people."""
    for room in rooms:
        room["talk"] = None
        room["parley"] = room["kind"] == "fight" and mix((yard ^ 0x7A1C) & 0xFFFF, floor * 16 + room["i"]) % 3 == 0
    empty = [r for r in rooms if r["kind"] == "empty"]
    vell = min(empty, key=lambda r: (r["depth"], r["i"])) if empty else rooms[[r["kind"] for r in rooms].index("start")]
    at = spot(vell)
    if at:
        vell["talk"] = {"who": "trader", "x": at[0], "y": at[1]}
    if floor in (2, 3):
        rest = [r for r in empty if r is not vell] or [r for r in rooms if r["kind"] == "cache"]
        if rest:
            pell = max(rest, key=lambda r: (r["depth"], -r["i"]))
            at = spot(pell)
            if at:
                pell["talk"] = {"who": "courier", "x": at[0], "y": at[1]}


FAN = [(0, -1), (1, 0), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, 1), (-1, -1)]   # N E S W NE SE SW NW


def fan_out(room, lead, n):
    """Where a party of n stands when a fight starts in this room (docs/rooms.md, The party):
    the leader at `lead`; the rest, in marching order, on the nearest squares found
    breadth-first from the leader (N, E, S, W, NE, SE, SW, NW) that are open, rough, cover
    or high ground with no foe on them."""
    out, seen, todo = [tuple(lead)], {tuple(lead)}, [tuple(lead)]
    foes = {(f["x"], f["y"]) for f in room["foes"]}
    while todo and len(out) < n:
        x, y = todo.pop(0)
        for dx, dy in FAN:
            if len(out) >= n:
                break
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H) or (nx, ny) in seen:
                continue
            seen.add((nx, ny))
            if int(room["rows"][ny][nx]) not in STANDS or (nx, ny) in foes:
                continue
            out.append((nx, ny))
            todo.append((nx, ny))
    return [list(p) for p in out]


# ------------------------------------------------------------------ open floors

ROUGH, COVER, HIGH = 3, 4, 6
OPEN_STANDS = (0, 3, 4, 6)
STEP8 = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]   # N NE E SE S SW W NW
STEP4 = [(0, -1), (1, 0), (0, 1), (-1, 0)]                                       # N E S W


def open_size(floor):
    """docs/open-floors.md, A floor: 48 x 24 on floors 1-2, 64 x 32 on 3-5, 80 x 40 below."""
    return (48, 24) if floor <= 2 else (64, 32) if floor <= 5 else (80, 40)


def crow(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def walkable(t):
    return t not in (WALL, PIT, HAZARD)


def by_foot(tiles, start):
    """{(x, y): steps} from start, 8 ways, through walkable squares."""
    h, w = len(tiles), len(tiles[0])
    dist, todo = {start: 0}, [start]
    for p in todo:
        for dx, dy in STEP8:
            q = (p[0] + dx, p[1] + dy)
            if 0 <= q[0] < w and 0 <= q[1] < h and q not in dist and walkable(tiles[q[1]][q[0]]):
                dist[q] = dist[p] + 1
                todo.append(q)
    return dist


def build_open(yard, floor, w=None, h=None):
    """An open floor (docs/open-floors.md, A floor, from a yard): {yard, floor, w, h, rows,
    start, stairs, bands, caches, people}."""
    if w is None:
        w, h = open_size(floor)
    state = mix((yard ^ 0x0F10) & 0xFFFF, (floor * 256 + 254) & 0xFFFF)

    def r(n):
        nonlocal state
        state = xs(state)
        return state % n

    # 1. The shell.
    t = [[WALL if x in (0, w - 1) or y in (0, h - 1) else OPEN for x in range(w)] for y in range(h)]
    inside = lambda q: 1 <= q[0] <= w - 2 and 1 <= q[1] <= h - 2  # noqa: E731
    # 2. Clusters.
    for _ in range((w - 2) * (h - 2) // 24):
        c = (2 + r(w - 4), 2 + r(h - 4))
        size = 5 + r(20)
        blob = [c]
        for _ in range(size - 1):
            p = blob[r(len(blob))]
            dx, dy = STEP4[r(4)]
            q = (p[0] + dx, p[1] + dy)
            if inside(q) and q not in blob:
                blob.append(q)
        if any(t[y][x] == WALL or any(t[y + dy][x + dx] == WALL for dx, dy in STEP8) for x, y in blob):
            continue
        for x, y in blob:
            t[y][x] = WALL
        for _ in range(r(3)):
            p = blob[r(len(blob))]
            dx, dy = STEP8[r(8)]
            kind = [COVER, COVER, ROUGH, HIGH][r(4)]
            q = (p[0] + dx, p[1] + dy)
            if t[q[1]][q[0]] == OPEN:
                t[q[1]][q[0]] = kind
    # 3. Open ground.
    for _ in range((w - 2) * (h - 2) // 96):
        x, y, k = 1 + r(w - 2), 1 + r(h - 2), r(5)
        if t[y][x] == OPEN and all(t[y + dy][x + dx] not in (WALL, PIT, HAZARD) for dx, dy in STEP8):
            t[y][x] = [ROUGH, ROUGH, PIT, HAZARD, COVER][k]
    # 4. The start.
    sy = 1 + r(h - 2)
    start = min(((x, y) for y in range(h) for x in range(w) if walkable(t[y][x])),
                key=lambda q: (q[0], abs(q[1] - sy), q[1]))
    # 5. One region.
    dist = by_foot(t, start)
    for y in range(h):
        for x in range(w):
            if walkable(t[y][x]) and (x, y) not in dist:
                t[y][x] = WALL
    squares = sorted(dist, key=lambda q: (q[1], q[0]))
    # 6. The stairs.
    stairs = min((q for q in squares if t[q[1]][q[0]] == OPEN), key=lambda q: (-dist[q], q[1], q[0]))
    # 7. Bands.
    n = max(1, len(squares) // 150)
    stands = [q for q in squares if t[q[1]][q[0]] in OPEN_STANDS]
    spots = [min((q for q in stands if crow(q, stairs) >= 2), key=lambda q: (crow(q, stairs), q[1], q[0]))]
    tries = 0
    while len(spots) < n and tries < 64 * n:
        tries += 1
        q = (1 + r(w - 2), 1 + r(h - 2))
        if (t[q[1]][q[0]] in OPEN_STANDS and q in dist and q != stairs and crow(q, start) >= 10
                and all(crow(q, o) >= 10 for o in spots)):
            spots.append(q)
    bands, taken = [], set()
    for k, spot in enumerate(spots):
        hiding = r(4) != 0
        g = floor + dist[spot] // 16
        count = min(4, 1 + g // 3 + (k == 0))
        L = min(4, 1 + g // 2)
        names = [POOL[r(L)] for _ in range(count)]
        where = [spot]
        seen, todo = {spot}, [spot]
        while todo and len(where) < count:
            p = todo.pop(0)
            for dx, dy in FAN:
                if len(where) >= count:
                    break
                q = (p[0] + dx, p[1] + dy)
                if q in seen or not (0 <= q[0] < w and 0 <= q[1] < h):
                    continue
                seen.add(q)
                if t[q[1]][q[0]] not in OPEN_STANDS or q in (stairs, start) or q in taken:
                    continue
                where.append(q)
                todo.append(q)
        taken.update(where)
        bands.append({"x": spot[0], "y": spot[1], "hiding": hiding, "stairs": k == 0,
                      "parley": k > 0 and mix((yard ^ 0x7A1C) & 0xFFFF, (floor * 64 + k) & 0xFFFF) % 3 == 0,
                      "foes": [{"name": nm, "x": q[0], "y": q[1]} for nm, q in zip(names, where)]})
    # 8. Caches.
    caches = []
    for _ in range(1 + len(squares) // 600):
        for _ in range(64):
            q = (1 + r(w - 2), 1 + r(h - 2))
            if (t[q[1]][q[0]] in OPEN_STANDS and q in dist and q != stairs and crow(q, start) >= 6
                    and all(crow(q, s) >= 4 for s in spots)
                    and all(crow(q, (c["x"], c["y"])) >= 4 for c in caches)):
                caches.append({"item": CACHE[r(5)], "x": q[0], "y": q[1]})
                break
    # 9. People.
    foes = {(f["x"], f["y"]) for b in bands for f in b["foes"]}
    clear = [q for q in stands if q != stairs and all(crow(q, s) >= 6 for s in spots)
             and all(crow(q, f) >= 6 for f in foes) and q not in {(c["x"], c["y"]) for c in caches}]
    people = []
    if clear:
        v = min(clear, key=lambda q: (abs(dist[q] - 8), q[1], q[0]))
        people.append({"who": "trader", "x": v[0], "y": v[1]})
        if floor in (2, 3):
            rest = [q for q in clear if crow(q, v) >= 4]
            if rest:
                half = dist[stairs] // 2
                p = min(rest, key=lambda q: (abs(dist[q] - half), q[1], q[0]))
                people.append({"who": "courier", "x": p[0], "y": p[1]})
    return {"yard": yard, "floor": floor, "w": w, "h": h,
            "rows": ["".join(str(c) for c in row) for row in t],
            "start": list(start), "stairs": list(stairs), "bands": bands, "caches": caches,
            "people": people}


def show_open(f):
    rows = [[SHOW[int(c)] for c in r] for r in f["rows"]]
    for k, b in enumerate(f["bands"]):
        for fo in b["foes"]:
            rows[fo["y"]][fo["x"]] = "abcdefghijklmnopqrstuvwxyz"[k % 26]
    for c in f["caches"]:
        rows[c["y"]][c["x"]] = "$"
    for p in f["people"]:
        rows[p["y"]][p["x"]] = "V" if p["who"] == "trader" else "P"
    rows[f["stairs"][1]][f["stairs"][0]] = "S"
    rows[f["start"][1]][f["start"][0]] = "@"
    out = [f"yard {f['yard']}, floor {f['floor']}: {f['w']} x {f['h']}, {len(f['bands'])} bands, "
           f"{len(f['caches'])} caches"]
    out += ["".join(r) for r in rows]
    for k, b in enumerate(f["bands"]):
        out.append(f"band {'abcdefghijklmnopqrstuvwxyz'[k % 26]}: "
                   + ", ".join(fo["name"] for fo in b["foes"])
                   + (", hiding" if b["hiding"] else ", open") + (", the stairs'" if b["stairs"] else "")
                   + (", talks first" if b["parley"] else ""))
    return "\n".join(out)


SHOW = {0: ".", 1: "#", 2: "O", 3: "~", 4: "+", 5: "^", 6: "=", 7: ">"}


def show(f):
    out = [f"yard {f['yard']}, floor {f['floor']}: start room {f['start']}, stairs in room {f['stairs']}"]
    for room in f["rooms"]:
        rows = [[SHOW[int(c)] for c in r] for r in room["rows"]]
        for n, foe in enumerate(room["foes"]):
            rows[foe["y"]][foe["x"]] = "abcd"[n]
        if room["cache"]:
            rows[room["cache"]["y"]][room["cache"]["x"]] = "$"
        if room["stairs"]:
            rows[room["stairs"][1]][room["stairs"][0]] = "S"
        if room["talk"]:
            rows[room["talk"]["y"]][room["talk"]["x"]] = "V" if room["talk"]["who"] == "trader" else "P"
        out.append(f"room {room['i']} ({room['kind']}, depth {room['depth']}): "
                   + ", ".join(f["name"] for f in room["foes"]) + (f" {room['cache']['item']}" if room["cache"] else "")
                   + (" (they talk first)" if room["parley"] else ""))
        out += ["  " + "".join(r) for r in rows]
    return "\n".join(out)


def main(argv):
    if len(argv) != 4 or argv[1] not in ("show", "json", "open", "open-json"):
        print(__doc__)
        return 2
    yard, floor = int(argv[2]) & 0xFFFF, max(1, min(255, int(argv[3])))
    if argv[1].startswith("open"):
        f = build_open(yard, floor)
        print(show_open(f) if argv[1] == "open" else json.dumps(f, sort_keys=True))
        return 0
    f = build(yard, floor)
    print(show(f) if argv[1] == "show" else json.dumps(f, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
