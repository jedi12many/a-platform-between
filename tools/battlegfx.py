"""The battle map's graphics (docs/frames.md, E12): one file every front end with graphics
loads for a fight, built from the art in content/art/ (docs/art.md, tools/art.py; edited
with the art desk, tools/artdesk/) and checked against the C64's rules.

    python3 tools/battlegfx.py OUT.bgfx [--sheet SHEET.png] [--c64 DIR] [--cart16 FILE]

--cart16 also writes the cartridge's map graphics, squares of 16 pixels (build16 below).

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
import art  # noqa: E402
import registry  # noqa: E402

(BLACK, WHITE, RED, CYAN, PURPLE, GREEN, BLUE, YELLOW,
 ORANGE, BROWN, PINK, DGREY, GREY, LGREEN, LBLUE, LGREY) = range(16)


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


# ------------------------------------------------------------------ the art
# The art itself is in content/art/ (docs/art.md, tools/art.py), drawn as text grids and
# edited with the art desk (tools/artdesk/). The tiles: k the background, d and g the
# shared colours, o the tile's own. The C version's are 16 multicolour dots wide and 32
# tall (4 x 4 characters); the cartridge's (docs/cartridge.md, "The view"), squares of 16
# pixels, 8 wide and 16 tall (2 x 2 characters). The figures: 12 multicolour dots wide,
# 21 tall, a and b the sprites' shared dark grey and light grey, c the figure's own
# colour, . see-through, feet on the bottom row.

TW, TH = 16, 32
T16W, T16H = 8, 16


def fill(t, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            t[y][x] = c


def _tiles(name):
    a = art.load(name)
    return [([list(r) for r in e.rows], e.colour) for e in a.entries[:8]], a


TILES, _T32 = _tiles("tiles32")          # [(art, its own colour)], the terrain's order
TILES16, _T16 = _tiles("tiles16")
_FIGURES = art.load("figures")
LOOKS = {e.name: (e.colour, e.rows) for e in _FIGURES.entries}
EFFECTS = {e.name: e.rows for e in art.load("effects").entries}
SPRITE_SHARED = _FIGURES.shared          # sprite multicolour 1 ($D025) and 2 ($D026)
SCREEN_BG = _T32.background
TILE_SHARED = _T32.shared                # multicolour character colours 1 and 2
REG = registry.load()
RACES = [n for n, _ in sorted(REG["races"].items(), key=lambda kv: kv[1]["id"])]
FOES = [n for n, _ in sorted(REG["foes"].items(), key=lambda kv: kv[1]["id"])]


def marked16(art):
    """The tile with a reach dot in its middle: black, 2 dots wide, 4 rows tall, across
    all four of its characters."""
    art = [list(r) for r in art]
    fill(art, 3, 6, 4, 9, "k")
    return art


def outlined(rows):
    """A body with its outline drawn in: every see-through dot next to it (four ways) made
    an a, the sprites' first shared colour, which the cartridge makes black. Its figures
    are a sprite each, with none to spare for the C version's hires outline."""
    rows = [r[:12].ljust(12, ".") for r in rows[:21]] + ["." * 12] * (21 - len(rows[:21]))
    out = [list(r) for r in rows]
    for y in range(21):
        for x in range(12):
            if rows[y][x] != ".":
                continue
            if any(0 <= x + dx < 12 and 0 <= y + dy < 21 and rows[y + dy][x + dx] != "."
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = "a"
    return ["".join(r) for r in out]


def cursor16(art):
    """The tile with the cursor on it: a bracket at each corner, in the square's own colour
    (the cartridge sets the cursor's colour in the colour RAM)."""
    art = [list(r) for r in art]
    for y, xs in ((0, (0, 1, 6, 7)), (1, (0, 7)), (2, (0, 7)), (13, (0, 7)), (14, (0, 7)),
                  (15, (0, 1, 6, 7))):
        for x in xs:
            art[y][x] = "o"
    return art


def chars16(art, own):
    """A 16-pixel tile's 4 characters (bytes) and colours, checked against the cell rule."""
    code = {"k": 0, "d": 1, "g": 2, "o": 3}
    chars = []
    for cy in range(2):
        for cx in range(2):
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
    return chars, [own | 8] * 4


# The colours the cartridge sets itself (cart/screen.s: the map's; cart/tactics.s: the
# figures' second shared colour, the first being black there, the drawn-in outline).
CART_TILE_COLOURS = (art.COLOURS.index("black"), art.COLOURS.index("dgrey"),
                     art.COLOURS.index("grey"))
CART_SPRITE_MC2 = art.COLOURS.index("lgrey")


def build16():
    """The cartridge's graphics for a map (docs/cartridge.md, "The view"):

        0     the characters (2 KB: 0 blank, then each tile's four, each tile's four with
              the reach dot, each tile's four with the cursor)
        2048  the table (128 bytes: 8 x (4 characters, 4 colours), then 8 x the 4 marked
              characters, then 8 x the 4 with the cursor); characters left to right, top
              to bottom
        2176  the figures' sprite shapes (2 KB, for $D800): look n's body is shape 2n, and
              its fallen body 2n + 1; multicolour, the C version's bodies with an outline
              drawn in (outlined)
        4224  each look's own colour (16)
        4240  the foes' names, 8 x 21 bytes: a length, then the bestiary's name (a look is
              found by its name: foe k's look is 8 + k)

    The looks are the C version's: the races at their ids (0-6), a stranger at 7, the foes
    at 8-15."""
    if (_T16.background,) + _T16.shared != CART_TILE_COLOURS:
        raise Problem("tiles16.txt: the cartridge's map is black, dgrey and grey (cart/screen.s "
                      "sets them): change them there too, and here")
    if SPRITE_SHARED[1] != CART_SPRITE_MC2:
        raise Problem("figures.txt: the cartridge's figures' second shared colour is lgrey "
                      "(cart/tactics.s sets it): change it there too, and here")
    charset = [[0] * 8 for _ in range(256)]
    table, marks = bytearray(), bytearray()
    at = 1
    for art, own in TILES16:
        if len(art) != T16H or any(len(r) != T16W for r in art):
            raise Problem(f"a 16-pixel tile must be {T16W} dots wide and {T16H} rows tall")
        chars, colours = chars16(art, own)
        table += bytes(range(at, at + 4)) + bytes(colours)
        for data in chars:
            charset[at] = data
            at += 1
    for change in (marked16, cursor16):
        for art, own in TILES16:
            chars, _ = chars16(change(art), own)
            marks += bytes(range(at, at + 4))
            for data in chars:
                charset[at] = data
                at += 1
    shapes, colours = bytearray(), bytearray()
    order = RACES + ["STRANGER"] + FOES
    for name in order:
        colour, rows = LOOKS[name]
        shapes += (bytes(mc_sprite(outlined(rows)) + [0])
                   + bytes(mc_sprite(outlined(fallen(rows))) + [0]))
        colours.append(colour)
    shapes += bytes(2048 - len(shapes))
    colours += bytes(16 - len(colours))
    names = bytearray()
    for n in FOES:
        shown = REG["foes"][n]["display"].encode("ascii")[:20]
        names += bytes([len(shown)]) + shown.ljust(20, b"\0")
    names += bytes(168 - len(names))
    return (bytes(b for ch in charset for b in ch) + bytes(table) + bytes(marks) + bytes(shapes)
            + bytes(colours) + bytes(names))


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
            raise Problem(f"{name} has no figure in content/art/figures.txt: draw one "
                          "(make artdesk)")
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
    if "--cart16" in argv:
        with open(argv[argv.index("--cart16") + 1], "wb") as f:
            f.write(build16())
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
