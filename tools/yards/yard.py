"""The Deep Yards' generator, written from docs/deep-yards.md, independently of
core/src/yard.c, so tests can check one against the other.

    python3 tools/yards/yard.py show YARD FLOOR [FOE ...]    draw a floor's map

A yard is a number 0..65535; floors and picks come from it by `mix`, never from the dice.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qsc"))
from image import read_encounter  # noqa: E402
from opcodes import MAP_TILES  # noqa: E402

W, H = 12, 8
FOES_MAX = 4
TERRAIN = [3, 3, 4, 4, 6, 2, 1, 5]      # rough, rough, cover, cover, high, pit, wall, hazard


def xs(x):
    """One step of xorshift16 (7, 9, 8), as core/src/rng.c."""
    x ^= (x << 7) & 0xFFFF
    x ^= x >> 9
    x ^= (x << 8) & 0xFFFF
    return x


def mix(yard, key):
    x = yard or 0xACE1
    for _ in range(3):
        x = xs(x)
        x = (x * 0x9E37 + key) & 0xFFFF or 0xACE1
    return xs(x)


def pick(yard, key, salt, n):
    """`~ pick VAR n on KEY`: 1..n."""
    return 1 + mix(yard, (key * 256 + salt) & 0xFFFF) % n


def build(yard, floor, pool):
    """Floor `floor`'s battle map: an encounter record (bytes), from the pool's record."""
    f = floor or 1
    p = read_encounter(pool, "pool")
    state = mix(yard, (f * 256 + 255) & 0xFFFF)

    def r(n):
        nonlocal state
        state = xs(state)
        return state % n

    tiles = [[1 if x in (0, W - 1) or y in (0, H - 1) else 0 for x in range(W)] for y in range(H)]
    ey = 1 + r(6)
    tiles[ey][0] = 7
    for _ in range(6 + f // 2):
        x, y, t = 3 + r(8), 1 + r(6), TERRAIN[r(8)]
        if y == ey:
            continue
        if t == 5 and f < 4:
            t = 3
        tiles[y][x] = t

    reached = {(1, ey)}
    todo = [(1, ey)]
    while todo:
        x, y = todo.pop()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in reached \
                        and tiles[ny][nx] not in (1, 2):
                    reached.add((nx, ny))
                    todo.append((nx, ny))

    n = min(FOES_MAX, 1 + (f - 1) // 4)
    limit = min(len(p["foes"]), 1 + f // 3)
    extra = f - 1
    placed = []

    def ok(x, y):
        return (x, y) in reached and tiles[y][x] in (0, 3, 4, 6) and (x, y) not in placed

    foes = []
    for _ in range(n):
        kind = r(limit)
        spot = None
        for _ in range(32):
            x, y = 7 + r(4), 1 + r(6)
            if ok(x, y):
                spot = (x, y)
                break
        if spot is None:
            spot = next((x, y) for x in range(W - 2, 0, -1) for y in range(1, H - 1) if ok(x, y))
        placed.append(spot)
        stats = list(p["foes"][kind]["stats"])
        stats[0] = min(255, stats[0] + extra)          # health
        stats[7] = min(200, stats[7] + extra)          # attack
        foes.append((spot, stats, p["foes"][kind]["name"]))

    flat = [t for row in tiles for t in row]
    out = bytearray([W, H])
    out += bytes((flat[i] << 4) | flat[i + 1] for i in range(0, len(flat), 2))
    out += bytes([1, 1, ey, len(foes)])
    for (x, y), stats, _ in foes:
        out += bytes([x, y] + stats)
    for _, _, name in foes:
        out += bytes([len(name)]) + name.encode("ascii")
    return bytes(out)


def draw(record):
    e = read_encounter(record, "floor")
    marks = {(x, y): "@" for x, y in e["starts"]}
    marks.update({(f["x"], f["y"]): chr(ord("a") + i) for i, f in enumerate(e["foes"])})
    lines = []
    for y in range(e["h"]):
        lines.append("".join(marks.get((x, y), MAP_TILES[e["tiles"][y * e["w"] + x]])
                             for x in range(e["w"])))
    for i, f in enumerate(e["foes"]):
        lines.append(f"{chr(ord('a') + i)} = {f['name']} (health {f['stats'][0]}, attack {f['stats'][7]})")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "show":
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "registry"))
        import registry
        from codegen import pool_bytes
        names = sys.argv[4:] or ["ASH_RAT", "RUST_GUARD", "MAINT_DRONE"]
        print(draw(build(int(sys.argv[2]), int(sys.argv[3]), pool_bytes(names, registry.load()))))
    else:
        sys.exit(__doc__)
