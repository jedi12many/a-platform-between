"""The battle map's graphics (docs/frames.md, E12): one file every front end with graphics
loads for a fight, built from the art below and checked against the C64's rules.

    python3 tools/battlegfx.py OUT.bgfx [--sheet SHEET.png] [--c64 DIR]

--c64 also writes it as the C64 loads it (fe/c64/scene.c), four program files with their
load addresses: btab (the tables, loaded where the program says), bchr (the characters,
at $E000), and the sprite shapes in two parts, bspr (at $EC00, 48 shapes) and bspr2 (at
$FC00, the rest, up to 15): all in VIC bank 3, under the KERNAL's ROM, where the VIC sees
them, around the story's text screen at $F800, which stays on under the map.

The map is the top of the framed screen, rows 0-15: the C64's multicolour character
mode, ten squares across and four down, each 32 x 32 pixels (4 x 4 characters), each
cell multicolour (three colours shared by the screen and one of the cell's own, from the
first eight); and sprites on top: 24 x 21, multicolour, with two colours shared by all
sprites and one each. Every figure is two sprites, a multicolour body and, over it, a
hires outline in black (worked out here from the body, a pixel wide), so figures stand
out of any floor. The frames under the map (the story, the party, the dice) are text, in
the story's font.

The file (all bytes):

    0    "BG", version 2
    3    sprite shared colours (2), screen background, tile shared colours (2)
    8    tiles: 8 x (16 characters, 16 colours), left to right, top to bottom; a colour
         with 8 added is multicolour
    264  each tile's middle four characters (2 x 2) with a dot on them, a square you can
         reach this turn: 8 x 4
    296  looks: 16 x (body, outline, down body, down outline, colour): the races at
         their ids (0-6), a stranger at 7, foe n at 7 + n (8-15)
    376  effects: the cursor, a bolt, a spark, a slash (sprite shapes)
    380  (zeros to 384)
    384  the foes' names, 8 x 32 bytes: a length, then the bestiary's display name in
         ASCII ("Ash rat"), as an encounter record has it: a fighter's look is found
         by its name (an unknown name is a stranger)
    640  the characters: 256 x 8 bytes (0 is blank)
    2688 the sprite shapes: 64 bytes each (the last unused), as many as the looks need,
         up to 63
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES = 640                    # the tables, before the characters (client/apb_scene.h)
SHAPES_LOW = 48                 # sprite shapes at $EC00, the rest at $FC00
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
    each stroke a pixel wider, the way C64 games' own fonts were, except where that would
    close a one-pixel gap (an m, a w, a #), which stays open."""
    out = []
    for r in rows:
        b = 0
        for x in range(8):
            if (r >> x) & 1:
                b |= 0x80 >> x
        grow = (b >> 1) & ~b & ~(b << 1)        # right of a stroke, not touching the next
        out.append((b | grow) & 0xFF)
    return out


# ------------------------------------------------------------------ tiles
# Each tile is 16 multicolour dots wide and 32 rows tall (4 x 4 characters): letters
# k (the background, black), d and g (the shared dark grey and grey), o (the tile's own
# colour). The tiles are the battle map's squares (docs/combat.md): open, wall, pit,
# rough, cover, hazard, high ground, exit. Flat, so the squares that matter stand out.

TW, TH = 16, 32


def blank(c="g"):
    return [[c] * TW for _ in range(TH)]


def fill(t, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            t[y][x] = c


def slab_floor():
    t = blank("g")
    fill(t, TW - 1, 0, TW - 1, TH - 1, "d")         # a faint seam right and below
    fill(t, 0, TH - 1, TW - 1, TH - 1, "d")
    return t


def wall():
    t = blank("d")
    fill(t, 0, TH - 1, TW - 1, TH - 1, "k")         # its foot
    return t


def pit():
    t = slab_floor()
    fill(t, 1, 3, 14, 28, "k")
    fill(t, 1, 3, 14, 4, "d")                       # the far rim, in shadow
    for x, y in ((4, 10), (10, 15), (6, 21), (11, 24)):
        t[y][x] = "o"                               # far down, something glints
    return t


def rough():
    t = slab_floor()
    for (x, y, w, h) in ((2, 4, 4, 3), (9, 3, 3, 2), (4, 13, 5, 4), (11, 12, 3, 3),
                         (2, 22, 3, 3), (8, 21, 5, 4)):
        fill(t, x, y, x + w - 1, y + h - 1, "d")
        fill(t, x, y + h, x + w - 1, y + h, "k")    # each lump's shadow
    return t


def cover():
    t = slab_floor()
    fill(t, 2, 5, 13, 27, "k")                      # a crate, outlined
    fill(t, 3, 6, 12, 26, "o")
    fill(t, 3, 16, 12, 16, "k")                     # its planks
    return t


def hazard():
    t = slab_floor()
    for top in (7, 15, 23):                         # three waves
        for x in range(2, 14):
            y = top + (0, 1, 2, 1)[(x // 2) % 4]
            t[y][x] = t[y + 1][x] = "o"
            t[y + 2][x] = "k"
    return t


def high():
    t = blank("g")
    fill(t, 0, 0, TW - 1, 1, "o")                   # its lit edge
    fill(t, 0, 0, 0, 25, "o")
    fill(t, 0, 26, TW - 1, 30, "d")                 # the raised step's front
    fill(t, 0, TH - 1, TW - 1, TH - 1, "k")
    return t


def exit_():
    t = slab_floor()
    fill(t, 1, 1, 14, 29, "o")                      # a lit doorway
    arrow = ["....kk......", "...kkk......", "..kkkkkkkkk.", ".kkkkkkkkkk.", ".kkkkkkkkkk.",
             "..kkkkkkkkk.", "...kkk......", "....kk......"]
    for dy, row in enumerate(arrow):
        for dx, c in enumerate(row):
            if c == "k":
                t[12 + dy][2 + dx] = "k"            # this way out
    return t


TILES = [  # (art, its own colour)
    (slab_floor(), BLACK), (wall(), BLACK), (pit(), BLUE), (rough(), BLACK),
    (cover(), RED), (hazard(), YELLOW), (high(), WHITE), (exit_(), GREEN),
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
    """A tile's 16 characters (bytes) and colours, checked against the cell rule."""
    code = {"k": 0, "d": 1, "g": 2, "o": 3}
    chars, colours = [], []
    for cy in range(4):
        for cx in range(4):
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


MIDDLE = (5, 6, 9, 10)          # a tile's middle four characters


def marked(art):
    """The tile with a reach dot in its middle: black, 2 dots wide, 4 rows tall."""
    art = [list(r) for r in art]
    fill(art, 7, 14, 8, 17, "k")
    return art


def build():
    charset = [[0] * 8 for _ in range(256)]
    tiles = bytearray()
    marks = bytearray()
    next_char = 1
    for art, own in TILES:
        if own > 7:
            raise Problem("a tile's own colour must be one of the first eight")
        if len(art) != TH or any(len(r) != TW for r in art):
            raise Problem(f"a tile must be {TW} dots wide and {TH} rows tall")
        chars, colours = tile_chars(art, own)
        codes = []
        for data in chars:
            charset[next_char] = data
            codes.append(next_char)
            next_char += 1
        tiles += bytes(codes) + bytes(colours)
    for art, own in TILES:                     # each tile's middle with a reach dot on it
        chars, _ = tile_chars(marked(art), own)
        for k in MIDDLE:
            charset[next_char] = chars[k]
            marks.append(next_char)
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
    if len(shapes) > 63:
        raise Problem(f"{len(shapes)} sprite shapes: the C64 has room for 63")
    head = bytes(b"BG\x02") + bytes(SPRITE_SHARED) + bytes([SCREEN_BG]) + bytes(TILE_SHARED)
    out = head + bytes(tiles) + bytes(marks) + bytes(looks) + effects
    out += bytes(384 - len(out))
    names = bytearray()
    for n in FOES:
        shown = REG["foes"][n]["display"].encode("ascii")[:20]
        names += bytes([len(shown)]) + shown + bytes(31 - len(shown))
    out += bytes(names) + bytes(256 - len(names))
    assert len(out) == TABLES
    out += bytes(b for ch in charset for b in ch)
    out += bytes(b for s in shapes for b in s)
    return out, len(shapes)


def sheet(data, path):
    """Everything in the file, drawn as the C64 would: each tile, plain and marked, then
    every sprite."""
    from PIL import Image
    shared = data[3:8]
    chars = data[TABLES:TABLES + 2048]
    sprites = data[TABLES + 2048:]
    n = len(sprites) // 64
    img = Image.new("RGB", (8 * 40, 80 + ((n + 9) // 10) * 26), (40, 40, 48))

    def dot(x, y, c, w=2):
        for dx in range(w):
            img.putpixel((x + dx, y), PALETTE[c])

    for t in range(8):
        codes, colours = data[8 + t * 32:8 + t * 32 + 16], data[24 + t * 32:24 + t * 32 + 16]
        for shown in range(2):
            for k in range(16):
                code = codes[k]
                if shown and k in MIDDLE:
                    code = data[264 + t * 4 + MIDDLE.index(k)]
                ch = chars[code * 8:code * 8 + 8]
                own = colours[k] & 7
                for y in range(8):
                    for x in range(4):
                        v = (ch[y] >> (6 - 2 * x)) & 3
                        c = (shared[2], shared[3], shared[4], own)[v]
                        dot(4 + t * 40 + (k % 4) * 8 + x * 2, 4 + shown * 36 + (k // 4) * 8 + y, c)
    for s in range(n):
        spr = sprites[s * 64:s * 64 + 63]
        ox, oy = 4 + (s % 10) * 30, 76 + (s // 10) * 26
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
        shapes = data[TABLES + 2048:]
        for name, at, part in (("btab", 0x0000, data[:TABLES]),
                               ("bchr", 0xE000, data[TABLES:TABLES + 2048]),
                               ("bspr", 0xEC00, shapes[:SHAPES_LOW * 64]),
                               ("bspr2", 0xFC00, shapes[SHAPES_LOW * 64:])):
            with open(os.path.join(out, name), "wb") as f:
                f.write(bytes([at & 0xFF, at >> 8]) + (part or bytes(64)))
    print(f"{argv[1]}: {len(data)} bytes, {n} sprite shapes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
