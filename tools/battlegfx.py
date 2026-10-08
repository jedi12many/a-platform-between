"""The battle screen's graphics (docs/c64-hardware.md, E9): one file every front end with
graphics loads for a fight, built from the art below and checked against the C64's rules.

    python3 tools/battlegfx.py OUT.bgfx [--sheet SHEET.png] [--c64 DIR]

--c64 also writes it as the C64 loads it (fe/c64/scene.c), three program files with
their load addresses: btab (the tables, loaded where the program says), bchr (the
characters, at $E000) and bspr (the sprite shapes, at $F000), both in VIC bank 3, under
the KERNAL's ROM, where the VIC sees them and nothing else lives during a fight.

The screen is the C64's multicolour character mode: 40 x 25 characters from one set of
256, each cell either hires (colours 0-7: the text) or multicolour (the tiles: three
colours shared by the screen and one of the cell's own, from the first eight), and
sprites on top: 24 x 21, multicolour, with two colours shared by all sprites and one
each. Every figure is two sprites, a multicolour body and, over it, a hires outline in
black (worked out here from the body, a pixel wide), so figures stand out of any floor.

The file (all bytes):

    0    "BG", version 1
    3    sprite shared colours (2), screen background, tile shared colours (2)
    8    tiles: 8 x (9 characters, 9 colours), left to right, top to bottom; a colour
         with 8 added is multicolour
    152  the marked centre of each tile (8), a square you can reach this turn
    160  looks: 16 x (body, outline, down body, down outline, colour): the races at
         their ids (0-6), a stranger at 7, foe n at 7 + n (8-15)
    240  effects: the cursor, a bolt, a spark, a slash (sprite shapes)
    244  (zeros to 256)
    256  the foes' names, 8 x 32 bytes: a length, then the bestiary's display name in
         ASCII ("Ash rat"), as an encounter record has it: a fighter's look is found
         by its name (an unknown name is a stranger)
    512  the characters: 256 x 8 bytes
    2560 the sprite shapes: 64 bytes each (the last unused), as many as the looks need

Characters 0-31 are the frames, bars and marks; 32-127 the font, at their ASCII codes;
128 and up the tiles.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = 512                    # the tables, before the characters (client/apb_scene.h)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "registry"))
from c64pic import PALETTE  # noqa: E402
import registry  # noqa: E402

(BLACK, WHITE, RED, CYAN, PURPLE, GREEN, BLUE, YELLOW,
 ORANGE, BROWN, PINK, DGREY, GREY, LGREEN, LBLUE, LGREY) = range(16)

SPRITE_SHARED = (DGREY, LGREY)          # sprite multicolour 1 ($D025) and 2 ($D026)
SCREEN_BG = BLACK
TILE_SHARED = (DGREY, GREY)             # multicolour character colours 1 and 2

# ------------------------------------------------------------------ the font

def font8x8():
    src = open(os.path.join(HERE, "..", "fe", "modern", "font8x8.h")).read()
    rows = re.findall(r"\{([^}]*)\}", src.split("font8x8[95][8] = {")[1])[:95]
    return [[int(v, 16) for v in re.findall(r"0x([0-9A-Fa-f]{2})", r)] for r in rows]


def glyph(rows):
    """font8x8 rows (bit 0 leftmost) as C64 character bytes (bit 7 leftmost), bolder:
    each stroke a pixel wider, the way C64 games' own fonts were."""
    out = []
    for r in rows:
        b = 0
        for x in range(8):
            if (r >> x) & 1:
                b |= 0x80 >> x
        out.append((b | (b >> 1)) & 0xFF)
    return out


# ------------------------------------------------------------------ the UI

def hires(rows):
    return [int(r.replace(".", "0").replace("#", "1"), 2) for r in rows]


UI = {
    0: ["........"] * 8,
    1: ["........", "........", "........", "...#####", "...#....", "...#.###", "...#.#..", "...#.#.."],  # corner
    2: ["........", "........", "........", "########", "........", "########", "........", "........"],  # top
    3: ["........", "........", "........", "#####...", "....#...", "###.#...", "..#.#...", "..#.#..."],
    4: ["...#.#..", "...#.#..", "...#.#..", "...#.#..", "...#.#..", "...#.#..", "...#.#..", "...#.#.."],  # side
    5: ["...#.#..", "...#.#..", "...#.###", "...#....", "...#####", "........", "........", "........"],
    6: ["..#.#...", "..#.#...", "###.#...", "....#...", "#####...", "........", "........", "........"],
    7: ["..#.#...", "..#.#...", "..#.#...", "..#.#...", "..#.#...", "..#.#...", "..#.#...", "..#.#..."],  # right side
    8: ["........", "........", "########", "........", "########", "........", "........", "........"],  # bottom
    9: [".######.", "#......#", "#......#", "#......#", "#......#", ".######."] + ["........"] * 2,  # bar: empty
    10: [".######.", "########", "########", "########", "########", ".######."] + ["........"] * 2,  # full
    11: [".######.", "####...#", "####...#", "####...#", "####...#", ".######."] + ["........"] * 2,  # half
    12: ["........", "........", "...##...", "..####..", "..####..", "...##...", "........", "........"],  # a dot
}

# ------------------------------------------------------------------ tiles
# Each tile is 12 multicolour dots wide and 24 rows tall (3 x 3 characters): letters
# k (the background, black), d and g (the shared dark grey and grey), o (the tile's own
# colour). The tiles are the battle map's squares (docs/combat.md): open, wall, pit,
# rough, cover, hazard, high ground, exit.

def blank(c="d"):
    return [[c] * 12 for _ in range(24)]


def slab_floor():
    t = blank("d")
    for y in range(24):
        for x in range(12):
            sx, sy = x % 6, y % 12
            if sx == 5 or sy == 11:
                t[y][x] = "k"                       # the seams between slabs
            elif sx == 0 or sy == 0:
                t[y][x] = "g"                       # each slab's lit edge
    for x, y in ((2, 4), (8, 15), (3, 19), (9, 6)):
        t[y][x] = "g"                               # wear
    return t


def wall():
    t = blank("g")
    for y in range(24):
        for x in range(12):
            if y < 6:
                t[y][x] = ("o" if y == 0 else "g") if y < 5 else "k"   # its top, lit
            else:
                r = (y - 6) % 6
                off = 0 if ((y - 6) // 6) % 2 else 3
                if r == 5 or (x + off) % 6 == 5:
                    t[y][x] = "k"                   # mortar
                elif r == 0:
                    t[y][x] = "d"
    return t


def pit():
    t = slab_floor()
    for y in range(3, 22):
        for x in range(1, 11):
            t[y][x] = "k"
    for x in range(1, 11):
        t[3][x] = "g"
    for y in range(4, 22):
        t[y][1] = "d"
    for y in range(8, 21, 4):
        for x in range(3, 10, 3):
            t[y][x] = "o"                           # far down, something glints
    return t


def rough():
    t = slab_floor()
    for (x, y, w, h, c) in ((1, 3, 4, 3, "g"), (7, 2, 3, 2, "o"), (2, 10, 3, 3, "o"),
                            (7, 9, 4, 4, "g"), (1, 17, 3, 2, "g"), (6, 16, 4, 3, "o"),
                            (9, 20, 2, 2, "g")):
        for dy in range(h):
            for dx in range(w):
                t[y + dy][x + dx] = c
        for dx in range(w):
            if y + h < 24:
                t[y + h][x + dx] = "k"              # each lump's shadow
    return t


def cover():
    t = slab_floor()
    for y in range(4, 22):
        for x in range(1, 11):
            t[y][x] = "o"                           # a crate
    for x in range(1, 11):
        t[4][x] = "g"
        t[12][x] = "k"
        t[21][x] = "k"
    for y in range(4, 22):
        t[y][1] = "g"
        t[y][10] = "k"
    for y, x in ((6, 3), (6, 8), (16, 3), (16, 8)):
        t[y][x] = "k"                               # nails
    return t


def hazard():
    t = slab_floor()
    for y in range(2, 22):
        for x in range(1, 11):
            t[y][x] = "o" if ((x + y // 2) % 4) < 2 else "k"   # warning chevrons
    return t


def high():
    t = blank("g")
    for y in range(24):
        for x in range(12):
            if y >= 18:
                t[y][x] = "d" if y < 23 else "k"    # the raised step's front
            elif y == 0 or x == 0:
                t[y][x] = "o"                       # its lit edge
            elif x == 11 or y == 17:
                t[y][x] = "d"
    return t


def exit_():
    t = slab_floor()
    for y in range(1, 23):
        for x in range(1, 11):
            t[y][x] = "o"                           # a lit doorway
    arrow = ["....k.....", "...kk.....", "..kkkkkkk.", ".kkkkkkkk.", "..kkkkkkk.",
             "...kk.....", "....k....."]
    for dy, row in enumerate(arrow):
        for dx, c in enumerate(row):
            if c == "k":
                t[8 + dy][1 + dx] = "k"
    return t


TILES = [  # (art, its own colour)
    (slab_floor(), BLACK), (wall(), WHITE), (pit(), BLUE), (rough(), RED),
    (cover(), RED), (hazard(), YELLOW), (high(), WHITE), (exit_(), YELLOW),
]

# ------------------------------------------------------------------ figures
# 12 multicolour dots wide, 21 tall: a and b the sprites' shared dark grey and light
# grey, c the figure's own colour, . see-through. Feet on the bottom row.

LOOKS = {
    "HUMAN": (PINK, [
        "....bbbb....", "...bccccb...", "...bccccb...", "....cccc....", ".....cc.....",
        "...aaaaaa...", "..aabbbbaa..", "..aabbbbaa..", ".caabbbbaac.", ".c.aabbaa.c.",
        ".c.aaaaaa.c.", "...aaaaaa...", "...aa..aa...", "...aa..aa...", "...aa..aa...",
        "...aa..aa...", "...aa..aa...", "...aa..aa...", "..aaa..aaa..", "..aaa..aaa..",
        "............"]),
    "HOLLOWBORN": (BROWN, [
        "...cccccc...", "..cbbccbbc..", "..cccccccc..", "..cc.aa.cc..", "...cccccc...",
        ".cccccccccc.", "ccaaccccaacc", "cca.cccc.acc", "cc..cccc..cc", "cc..caac..cc",
        "cc..cccc..cc", "....cccc....", "...cc..cc...", "...cc..cc...", "...cc..cc...",
        "...cc..cc...", "..ccc..ccc..", "..ccc..ccc..", "..aaa..aaa..", "............",
        "............"]),
    "GLASSFOLK": (CYAN, [
        ".....b......", "....bcb.....", "...bcccb....", "...cbcbc....", "....ccc.....",
        "...bcccb....", "..bcbcbcb...", ".bc.ccc.cb..", ".c..cbc..c..", ".b..ccc..b..",
        "....cbc.....", "...cc.cc....", "...cb.bc....", "...c...c....", "...c...c....",
        "...b...b....", "..bc...cb...", "..cc...cc...", "............", "............",
        "............"]),
    "RAD_DRYAD": (GREEN, [
        "..cc.cc.cc..", ".cccccccccc.", "cccbcccbcccc", ".ccccccccc..", "...aaaaaa...",
        "...abbbba...", "...aaaaaa...", "..aaaaaaaa..", ".ca.aaaa.ac.", "c..aaaaaa..c",
        "...aaaaaa...", "...aaaaaa...", "...aa..aa...", "...aa..aa...", "...aa..aa...",
        "..aaa..aaa..", ".aaa....aaa.", ".a.a....a.a.", "............", "............",
        "............"]),
    "CHRONOMITE": (YELLOW, [
        "....aaaa....", "...acccca...", "..acbcbca...", "..accbcca...", "...acccca...",
        "....aaaa....", "...aaaaaa...", "..aacccaa...", ".a.acbca.a..", ".a.acccaa.a.",
        "...aaaaaa...", "...aa..aa...", "...aa..aa...", "...aa..aa...", "...aa..aa...",
        "..aaa..aaa..", "............", "............", "............", "............",
        "............"]),
    "SALVAGED": (CYAN, [
        "....aaaa....", "...abbbba...", "...acccca...", "...abbbba...", "....aaaa....",
        "..bbbbbbbb..", ".babbbbbbab.", ".ba.bbbb.abaaaa", ".ba.bbbb.aaaa.", ".bb.bbbb.bb.",
        "....aaaa....", "....acca....", "....aaaa....", "...bb..bb...", "...bb..bb...",
        "...aa..aa...", "...aa..aa...", "..aaa..aaa..", "..aaa..aaa..", "............",
        "............"]),
    "MOTH_FOLK": (PURPLE, [
        "...b....b...", "....b..b....", "....bbbb....", "....bccb....", ".....bb.....",
        "cc..aaaa..cc", "ccc.abba.ccc", "cccbaaaabccc", "cccc.aa.cccc", ".ccc.aa.ccc.",
        "..cc.aa.cc..", "....aaaa....", "....a..a....", "....a..a....", "....a..a....",
        "...aa..aa...", "............", "............", "............", "............",
        "............"]),
    "STRANGER": (LGREY, [
        "....aaaa....", "...aaaaaa...", "...aaaaaa...", "....aaaa....", "...aaaaaa...",
        "..aaaaaaaa..", "..aaaaaaaa..", "..aaaaaaaa..", "..aaaaaaaa..", "..aaaaaaaa..",
        "..aaaaaaaa..", "..aaaaaaaa..", "...aa..aa...", "...aa..aa...", "...aa..aa...",
        "...aa..aa...", "..aaa..aaa..", "............", "............", "............",
        "............"]),
    "RUST_GUARD": (ORANGE, [
        "...cccccc...", "..cccccccc..", "..caaaaaac..", "..cccccccc..", "...cccccc...",
        ".cccccccccc.", "ccbccccccbcc", "cc.cccccc.cc", "cc.ccaacc.cc", "bb.cccccc.bb",
        "...cccccc...", "...ccaacc...", "...cc..cc...", "...cc..cc...", "...cc..cc...",
        "...cc..cc...", "..ccc..ccc..", "..aaa..aaa..", "............", "............",
        "............"]),
    "SCRAP_GUNNER": (BROWN, [
        "....cccc....", "...cbbbbc...", "....cccc....", "...cccccc...", "..cccccccc..",
        "..cc.cc.ccaaaaa", "..cc.cc.caaaaa.", "..cc.cc.cc..", "....cccc....", "....cccc....",
        "...cc..cc...", "...cc..cc...", "...cc..cc...", "..ccc..ccc..", "..aaa..aaa..",
        "............", "............", "............", "............", "............",
        "............"]),
    "ASH_RAT": (GREY, [
        "............", "............", "............", "............", "............",
        "............", "............", "............", "...bb.......", "..bbbb......",
        ".bccccc.....", "bbcccccccc..", "bccccccccccb", ".ccccccccc.b", "..cccccccc.b",
        "..c.cc.c.c..", "..a....a....", "............", "............", "............",
        "............"]),
    "MAINT_DRONE": (YELLOW, [
        "............", "............", "....aaaa....", "...abbbba...", "..abbbbbba..",
        ".aaaaaaaaaa.", ".accccccca..", ".acaaaaaca..", ".acabbbaca.b", ".acaaaaacabb",
        ".accccccca.b", ".aaaaaaaaa..", "..a......a..", "..a......a..", ".aaa....aaa.",
        "............", "............", "............", "............", "............",
        "............"]),
}
REG = registry.load()
RACES = [n for n, _ in sorted(REG["races"].items(), key=lambda kv: kv[1]["id"])]
FOES = [n for n, _ in sorted(REG["foes"].items(), key=lambda kv: kv[1]["id"])]

EFFECTS = {
    "CURSOR": ["###....###"] + ["#........#"] * 2 + [".........."] * 15 + ["#........#"] * 2 + ["###....###"],
    "BOLT": ["............", "............", "............", "............", "............",
             "............", "............", "............", "....bbbbcc..", "..bbbbcccccc",
             "....bbbbcc..", "............", "............", "............", "............",
             "............", "............", "............", "............", "............",
             "............"],
    "SPARK": ["....#...#...", ".#..#..#..#.", "..#.....#...", "...#...#....", "#....#.....#",
              "...#...#....", "..#.....#...", ".#..#..#..#.", "....#...#...", "............",
              "............", "............", "............", "............", "............",
              "............", "............", "............", "............", "............",
              "............"],
    "SLASH": ["..........##", ".........##.", "........##..", ".......##...", "......##....",
              ".....##.....", "....##......", "...##.......", "..##........", ".##.........",
              "##..........", "............", "............", "............", "............",
              "............", "............", "............", "............", "............",
              "............"],
}

# ------------------------------------------------------------------ building

class Problem(Exception):
    pass


def mc_sprite(rows):
    """12 x 21 multicolour art into 63 bytes: 00 see-through, 01 a, 10 c, 11 b."""
    code = {".": 0, "a": 1, "c": 2, "b": 3}
    out = []
    for y in range(21):
        row = (rows[y] if y < len(rows) else "")[:12].ljust(12, ".")
        bits = 0
        for ch in row:
            if ch not in code:
                raise Problem(f"a sprite has '{ch}': use . a b c")
            bits = (bits << 2) | code[ch]
        out += [(bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF]
    return out


def hires_sprite(rows, width=24):
    out = []
    for y in range(21):
        row = (rows[y] if y < len(rows) else "").ljust(width, ".")[:24].ljust(24, ".")
        bits = int("".join("1" if ch == "#" else "0" for ch in row), 2)
        out += [(bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF]
    return out


def outline(rows):
    """The hires outline round a multicolour body: every pixel next to it (four ways)
    that isn't part of it."""
    solid = set()
    for y, row in enumerate(rows[:21]):
        for x, ch in enumerate(row[:12]):
            if ch != ".":
                solid |= {(2 * x, y), (2 * x + 1, y)}
    edge = set()
    for (x, y) in solid:
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in solid and 0 <= nx < 24 and 0 <= ny < 21:
                edge.add((nx, ny))
    return ["".join("#" if (x, y) in edge else "." for x in range(24)) for y in range(21)]


def fallen(rows):
    """Down: the figure fallen in a heap, its rows squashed into the bottom six."""
    rows = [r[:12].ljust(12, ".") for r in rows[:21]]
    used = [r for r in rows if r.strip(".")]
    keep = [used[i * len(used) // 6] for i in range(6)] if used else []
    return ["." * 12] * 15 + keep


def tile_chars(art, own):
    """A tile's 9 characters (bytes) and colours, checked against the cell rule."""
    code = {"k": 0, "d": 1, "g": 2, "o": 3}
    chars, colours = [], []
    for cy in range(3):
        for cx in range(3):
            data = []
            for y in range(8):
                b = 0
                for x in range(4):
                    ch = art[cy * 8 + y][cx * 4 + x]
                    if ch not in code:
                        raise Problem(f"a tile has '{ch}': use k d g o")
                    b = (b << 2) | code[ch]
                data.append(b)
            chars.append(data)
            colours.append(own | 8)
    return chars, colours


def build():
    charset = [[0] * 8 for _ in range(256)]
    for n, rows in UI.items():
        charset[n] = hires(rows)
    for i, rows in enumerate(font8x8()):
        charset[32 + i] = glyph(rows)
    tiles = bytearray()
    marked = bytearray()
    next_char = 128
    centres = []
    for art, own in TILES:
        if own > 7:
            raise Problem("a tile's own colour must be one of the first eight")
        chars, colours = tile_chars(art, own)
        codes = []
        for data in chars:
            charset[next_char] = data
            codes.append(next_char)
            next_char += 1
        tiles += bytes(codes) + bytes(colours)
        centres.append(chars[4])
    for data in centres:                       # each tile's centre with a reach dot on it
        dotted = list(data)
        dotted[2] = (dotted[2] & 0b11000011)                    # a black ring...
        dotted[5] = (dotted[5] & 0b11000011)
        for y in (3, 4):
            dotted[y] = (dotted[y] & 0b00000000) | 0b00111100   # ...round a spot of the
                                                                # tile's own colour
        charset[next_char] = dotted
        marked.append(next_char)
        next_char += 1
    shapes = []

    def add(data):
        shapes.append(data + [0])
        return len(shapes) - 1

    looks = bytearray()
    order = RACES + ["STRANGER"] + FOES
    if len(RACES) > 7 or len(FOES) > 8:
        raise Problem("more races or foes than the file has looks for: make it bigger")
    if [REG["races"][n]["id"] for n in RACES] != list(range(len(RACES))):
        raise Problem("the races' ids aren't 0, 1, 2...")
    for name in order:
        if name not in LOOKS:
            raise Problem(f"{name} has no figure here: draw one")
        colour, rows = LOOKS[name]
        down = fallen(rows)
        looks += bytes([add(mc_sprite(rows)), add(hires_sprite(outline(rows))),
                        add(mc_sprite(down)), add(hires_sprite(outline(down))), colour])
    looks += bytes(5 * (16 - len(order)))
    effects = bytes([add(hires_sprite(EFFECTS["CURSOR"], 20)), add(mc_sprite(EFFECTS["BOLT"])),
                     add(hires_sprite(EFFECTS["SPARK"], 12)), add(hires_sprite(EFFECTS["SLASH"], 12))])
    if len(shapes) > 64:
        raise Problem(f"{len(shapes)} sprite shapes: the C64 has room for 64")
    head = bytes(b"BG\x01") + bytes(SPRITE_SHARED) + bytes([SCREEN_BG]) + bytes(TILE_SHARED)
    out = head + bytes(tiles) + bytes(marked) + bytes(looks) + effects
    out += bytes(256 - len(out))
    names = bytearray()
    for n in FOES:
        shown = REG["foes"][n]["display"].encode("ascii")[:20]
        names += bytes([len(shown)]) + shown + bytes(31 - len(shown))
    out += bytes(names) + bytes(256 - len(names))
    out += bytes(b for ch in charset for b in ch)
    out += bytes(b for s in shapes for b in s)
    return out, len(shapes)


def sheet(data, path):
    """Everything in the file, drawn as the C64 would: the tiles, then every sprite."""
    from PIL import Image
    shared = data[3:8]
    chars = data[512:2560]
    sprites = data[2560:]
    n = len(sprites) // 64
    img = Image.new("RGB", (8 * 30 * 2, 40 + ((n + 9) // 10) * 26), (40, 40, 48))

    def dot(x, y, c, w=2):
        for dx in range(w):
            img.putpixel((x + dx, y), PALETTE[c])

    for t in range(8):
        codes, colours = data[8 + t * 18:8 + t * 18 + 9], data[17 + t * 18:17 + t * 18 + 9]
        for k in range(9):
            ch = chars[codes[k] * 8:codes[k] * 8 + 8]
            own = colours[k] & 7
            for y in range(8):
                for x in range(4):
                    v = (ch[y] >> (6 - 2 * x)) & 3
                    c = (shared[2], shared[3], shared[4], own)[v]
                    dot(4 + t * 30 + (k % 3) * 8 + x * 2, 4 + (k // 3) * 8 + y, c)
    for s in range(n):
        spr = sprites[s * 64:s * 64 + 63]
        ox, oy = 4 + (s % 10) * 30, 36 + (s // 10) * 26
        mc = any(b & 0x55 and b & 0xAA for b in spr) or s % 2 == 0
        for y in range(21):
            bits = (spr[y * 3] << 16) | (spr[y * 3 + 1] << 8) | spr[y * 3 + 2]
            for x in range(24):
                if (bits >> (23 - x)) & 1:
                    dot(ox + x, oy + y, BLACK if s % 2 else WHITE, 1)
    img = img.resize((img.size[0] * 3, img.size[1] * 3), Image.NEAREST)
    img.save(path)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    try:
        data, n = build()
    except Problem as e:
        print(f"battlegfx: {e}")
        return 1
    with open(argv[1], "wb") as f:
        f.write(data)
    if "--sheet" in argv:
        sheet(data, argv[argv.index("--sheet") + 1])
    if "--c64" in argv:
        out = argv[argv.index("--c64") + 1]
        os.makedirs(out, exist_ok=True)
        for name, at, part in (("btab", 0x0000, data[:TABLES]),
                               ("bchr", 0xE000, data[TABLES:TABLES + 2048]),
                               ("bspr", 0xF000, data[TABLES + 2048:])):
            if at and at + len(part) > 0xFFFA:
                raise SystemExit(f"battlegfx: {name} runs into the 6502's vectors")
            with open(os.path.join(out, name), "wb") as f:
                f.write(bytes([at & 0xFF, at >> 8]) + part)
    print(f"{argv[1]}: {len(data)} bytes, {n} sprite shapes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
