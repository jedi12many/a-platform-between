"""Pictures for the C64 (docs/c64.md): a 160x96 PNG into a file the game shows on rows
1-12 of the screen, in multicolour character mode.

    python3 tools/c64pic.py convert IN.png OUT.pic        a picture file
    python3 tools/c64pic.py render IN.pic OUT.png         what the C64 will show (x2 wide)
    python3 tools/c64pic.py disk DEPOT PICDIR OUTDIR      picNN for each picture in a
                                                          Departure that has a PNG

The picture is 40 x 12 cells of 4 x 8 multicolour pixels (each pixel twice as wide as
it is tall on the screen, so draw at 160 x 96 and let it stretch). Each cell can use
four colours: three shared by the whole picture (the background and two more) and one
of its own, from the first eight colours (a C64 rule). The converter picks the shared
three by how much they're used, each cell's own colour likewise, then the nearest of
the four for every pixel. Cells that come out the same share a character; with more
than 256 different ones, the rarest are drawn with the nearest one kept.

The file loads at $E000 (the RAM under the KERNAL): 2048 bytes of characters, the
screen at $E800 (rows 1-12 used), the shared colours at $EBE8, each cell's colour at
$EC00.
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


def convert(px):
    counts = [0] * 16
    for row in px:
        for c in row:
            counts[c] += 1
    shared = sorted(range(16), key=lambda c: -counts[c])[:3]
    back, multi1, multi2 = shared
    cells = []
    for cy in range(ROWS):
        for cx in range(COLS):
            block = [px[cy * 8 + y][cx * 4 + x] for y in range(8) for x in range(4)]
            own = [c for c in block if c not in shared]
            if own:
                best = max(set(own), key=own.count)
                cell = best if best < 8 else nearest(PALETTE[best], range(8))
            else:
                cell = 0
            choice = {back: 0, multi1: 1, multi2: 2}
            pair = []
            for c in block:
                if c in choice:
                    pair.append(choice[c])
                elif c == cell:
                    pair.append(3)
                else:
                    options = [back, multi1, multi2, cell]
                    pair.append(options.index(nearest(PALETTE[c], options)))
            rows = bytes((pair[y * 4] << 6) | (pair[y * 4 + 1] << 4) | (pair[y * 4 + 2] << 2)
                         | pair[y * 4 + 3] for y in range(8))
            cells.append((rows, cell))
    # Characters: the same cell shares one; at most 256, the rarest drawn with the nearest.
    freq = {}
    for rows, _ in cells:
        freq[rows] = freq.get(rows, 0) + 1
    kept = sorted(freq, key=lambda r: -freq[r])[:256]
    index = {r: i for i, r in enumerate(kept)}

    def distance(a, b):
        return sum(bin((x ^ y) & 0xFF).count("1") for x, y in zip(a, b))

    for r in freq:
        if r not in index:
            index[r] = index[min(kept, key=lambda k: distance(k, r))]
    charset = bytearray(2048)
    for r, i in index.items():
        if r in kept:
            charset[i * 8:i * 8 + 8] = r
    screen = bytearray([0x20] * 1000)
    colours = bytearray(COLS * ROWS)
    for n, (rows, cell) in enumerate(cells):
        screen[TOP_ROW * COLS + n] = index[rows]
        colours[n] = cell | 8                       # 8 and up: a multicolour cell
    data = bytearray(0xC00 + len(colours))
    data[0:0x800] = charset
    data[0x800:0x800 + 1000] = screen
    data[0xBE8:0xBEB] = bytes([back, multi1, multi2])
    data[0xC00:] = colours
    return b"\x00\xE0" + bytes(data), len(freq)


def render(pic):
    data = pic[2:]
    charset, screen = data[0:0x800], data[0x800:0x800 + 1000]
    back, multi1, multi2 = data[0xBE8:0xBEB]
    colours = data[0xC00:0xC00 + COLS * ROWS]
    img = Image.new("RGB", (W * 2, H))
    for n in range(COLS * ROWS):
        cx, cy = n % COLS, n // COLS
        ch = screen[TOP_ROW * COLS + n]
        options = [back, multi1, multi2, colours[n] & 7]
        for y in range(8):
            b = charset[ch * 8 + y]
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
        pic, distinct = convert(load(argv[2]))
        with open(argv[3], "wb") as f:
            f.write(pic)
        print(f"{argv[3]}: {len(pic)} bytes, {min(distinct, 256)} characters"
              + (f" ({distinct} different cells, the rest drawn with the nearest)"
                 if distinct > 256 else ""))
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
