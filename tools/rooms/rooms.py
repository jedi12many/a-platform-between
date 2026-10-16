"""A floor of rooms (docs/rooms.md), written from the doc, independently of the prototype's
generator (tools/arena/web/rooms.js), so tests can check one against the other.

    python3 tools/rooms/rooms.py show YARD FLOOR      draw a floor's rooms
    python3 tools/rooms/rooms.py json YARD FLOOR      the floor as JSON (what rooms.js builds)

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
    if len(argv) != 4 or argv[1] not in ("show", "json"):
        print(__doc__)
        return 2
    f = build(int(argv[2]) & 0xFFFF, max(1, min(255, int(argv[3]))))
    print(show(f) if argv[1] == "show" else json.dumps(f, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
