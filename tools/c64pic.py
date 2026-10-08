"""Pictures for the C64 (docs/c64.md): a 160x96 PNG into a file the game shows on rows
1-12 of the screen, in multicolour bitmap mode.

    python3 tools/c64pic.py convert IN.png OUT.pic        a picture file
    python3 tools/c64pic.py render IN.pic OUT.png         what the C64 will show (x2 wide)
    python3 tools/c64pic.py disk DEPOT PICDIR OUTDIR      picNN for each picture in a
                                                          Departure that has a PNG

The picture is 40 x 12 cells of 4 x 8 multicolour pixels (each pixel twice as wide as
it is tall on the screen, so draw at 160 x 96 and let it stretch). Each cell can use
four colours: the background, shared by the whole picture, and three of its own, any
of the sixteen (the VIC-II's multicolour bitmap mode). The converter takes for the
background the colour that leaves fewest cells with more than three others (the most
used, if that's a tie); a cell with more keeps its three most used, and its other
pixels take the nearest of its four.

The file loads at $E140, in the RAM under the KERNAL, VIC bank 3: the bitmap's rows 1-12
($E140-$F03F, the bitmap at $E000), the screen's rows 1-12 ($F428-$F607, the screen at
$F400: each cell's first two colours), each cell's third colour ($F608, for colour
RAM) and the background ($F7E8).
"""

import os
import sys

from PIL import Image

W, H = 160, 96
COLS, ROWS = 40, 12
TOP_ROW = 1                     # the picture's first screen row

PALETTE = [(0x00, 0x00, 0x00), (0xFF, 0xFF, 0xFF), (0x68, 0x37, 0x2B), (0x70, 0xA4, 0xB2),
           (0x6F, 0x3D, 0x86), (0x58, 0x8D, 0x43), (0x35, 0x28, 0x79), (0xB8, 0xC7, 0x6F),
           (0x6F, 0x4F, 0x25), (0x43, 0x39, 0x00), (0x9A, 0x67, 0x59), (0x44, 0x44, 0x44),
           (0x6C, 0x6C, 0x6C), (0x9A, 0xD2, 0x84), (0x6C, 0x5E, 0xB5), (0x95, 0x95, 0x95)]


def nearest(rgb, choices=range(16)):
    return min(choices, key=lambda i: sum((a - b) ** 2 for a, b in zip(rgb, PALETTE[i])))


def load(path):
    img = Image.open(path).convert("RGB")
    if img.size != (W, H):
        img = img.resize((W, H), Image.NEAREST)
    cache = {}
    px = [[0] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            rgb = img.getpixel((x, y))
            if rgb not in cache:
                cache[rgb] = nearest(rgb)
            px[y][x] = cache[rgb]
    return px


LOAD_AT = 0xE140
BITMAP = 0xE000 + TOP_ROW * 320         # where the picture's bitmap starts
SCREEN = 0xF400 + TOP_ROW * COLS        # its screen rows (two colours a cell)
CELLS = 0xF608                          # its colour RAM (the third)
BACK = 0xF7E8                           # the background
SIZE = BACK + 1 - LOAD_AT


def blocks(px):
    """The picture as 480 cells, each the colours of its 32 pixels, row by row."""
    return [[px[cy * 8 + y][cx * 4 + x] for y in range(8) for x in range(4)]
            for cy in range(ROWS) for cx in range(COLS)]


def crowded(cells, back):
    """Cells with more than three colours besides `back`."""
    return sum(1 for block in cells if len(set(block) - {back}) > 3)


def choose_background(cells, counts):
    """The colour that leaves fewest cells crowded; the most used, if that's a tie."""
    used = sorted((c for c in range(16) if counts[c]), key=lambda c: -counts[c]) or [0]
    return min(used, key=lambda c: (crowded(cells, c), -counts[c]))


def convert(px):
    """The picture file, and how many cells had to change (more than three colours of
    their own: the rest are drawn with the nearest of the four)."""
    counts = [0] * 16
    for row in px:
        for c in row:
            counts[c] += 1
    cells = blocks(px)
    back = choose_background(cells, counts)
    data = bytearray(SIZE)
    for n, block in enumerate(cells):
        cy, cx = divmod(n, COLS)
        own = [c for c in block if c != back]
        three = sorted(set(own), key=lambda c: (-own.count(c), c))[:3]
        three += [back] * (3 - len(three))
        options = [back] + three                     # bit pairs 00, 01, 10, 11
        pair = []
        for c in block:
            pair.append(options.index(c) if c in options
                        else options.index(nearest(PALETTE[c], options)))
        at = BITMAP + cy * 320 + cx * 8 - LOAD_AT
        for y in range(8):
            data[at + y] = ((pair[y * 4] << 6) | (pair[y * 4 + 1] << 4) | (pair[y * 4 + 2] << 2)
                            | pair[y * 4 + 3])
        data[SCREEN + n - LOAD_AT] = (options[1] << 4) | options[2]
        data[CELLS + n - LOAD_AT] = options[3]
    data[BACK - LOAD_AT] = back
    return bytes([LOAD_AT & 0xFF, LOAD_AT >> 8]) + bytes(data), crowded(cells, back)


def render(pic):
    """What the C64 shows, from a picture file: 320 x 96, each pixel twice as wide."""
    data = pic[2:]
    back = data[BACK - LOAD_AT] & 15
    img = Image.new("RGB", (W * 2, H))
    for n in range(COLS * ROWS):
        cy, cx = divmod(n, COLS)
        both = data[SCREEN + n - LOAD_AT]
        options = [back, both >> 4, both & 15, data[CELLS + n - LOAD_AT] & 15]
        at = BITMAP + cy * 320 + cx * 8 - LOAD_AT
        for y in range(8):
            b = data[at + y]
            for x in range(4):
                c = PALETTE[options[(b >> (6 - 2 * x)) & 3]]
                img.putpixel((cx * 8 + x * 2, cy * 8 + y), c)
                img.putpixel((cx * 8 + x * 2 + 1, cy * 8 + y), c)
    return img


def disk(depot_path, pic_dir, out_dir):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "qsc"))
    import image
    with open(depot_path, "rb") as f:
        names = image.read_depot(f.read()).get("pictures", [])
    os.makedirs(out_dir, exist_ok=True)
    for i, name in enumerate(names):
        png = os.path.join(pic_dir, name + ".png")
        if os.path.exists(png):
            pic, _ = convert(load(png))
            with open(os.path.join(out_dir, f"pic{i:02d}"), "wb") as f:
                f.write(pic)


def main(argv):
    if len(argv) == 4 and argv[1] == "convert":
        pic, changed = convert(load(argv[2]))
        with open(argv[3], "wb") as f:
            f.write(pic)
        print(f"{argv[3]}: {len(pic)} bytes"
              + (f", {changed} cells with more than four colours (drawn with the nearest)"
                 if changed else ""))
        return 0
    if len(argv) == 4 and argv[1] == "render":
        with open(argv[2], "rb") as f:
            render(f.read()).save(argv[3])
        return 0
    if len(argv) == 5 and argv[1] == "disk":
        disk(argv[2], argv[3], argv[4])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
