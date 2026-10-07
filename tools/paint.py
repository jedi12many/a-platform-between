"""A small kit for painting the game's pictures in code (docs/c64.md, "Pictures").

A picture is 160 x 96 pixels in the C64's sixteen colours, each pixel twice as wide as
it is tall on the screen. On the C64 every 4 x 8 cell can show three colours shared by
the whole picture and one of its own from the first eight, and at most 256 different
cells; `check` runs tools/c64pic.py on a picture and says how far it is from what the
C64 can show, so a painting can be made to come through unchanged.

    from paint import Canvas, BLACK, ...
    c = Canvas(BLACK)
    c.rect(0, 70, 159, 95, DGREY)
    c.save("concourse.png")

Coordinates are in picture pixels (x 0-159, y 0-95). `ellipse` takes its sizes in
screen proportions, so a circle looks round once the pixels are stretched.
"""

import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c64pic  # noqa: E402

W, H = c64pic.W, c64pic.H
(BLACK, WHITE, RED, CYAN, PURPLE, GREEN, BLUE, YELLOW,
 ORANGE, BROWN, PINK, DGREY, GREY, LGREEN, LBLUE, LGREY) = range(16)

# Ordered dithering: a 4 x 4 Bayer matrix, thresholds 0-15.
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


class Canvas:
    def __init__(self, background):
        self.px = [[background] * W for _ in range(H)]

    @classmethod
    def fitted(cls, path, box=None, dither="none", characters=256):
        """Art from anywhere, fitted to the C64's rules by tools/c64fit.py (which needs
        numpy), to paint over: a sign's words, a colour put right. Painting adds cells,
        so leave room with fewer `characters`."""
        import c64fit
        c = cls(BLACK)
        c.px, _ = c64fit.fit_pixels(path, dither, None, box, characters)
        return c

    def recolour(self, old, new, x0=0, y0=0, x1=W - 1, y1=H - 1):
        """Every `old` pixel in the box becomes `new`."""
        for y in range(max(0, y0), min(H, y1 + 1)):
            for x in range(max(0, x0), min(W, x1 + 1)):
                if self.px[y][x] == old:
                    self.px[y][x] = new

    # ------------------------------------------------------------------ pixels
    def set(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[y][x] = c

    def get(self, x, y):
        return self.px[y][x] if 0 <= x < W and 0 <= y < H else None

    def mask(self, draw):
        """The pixels a PIL drawing covers: draw(ImageDraw) on a blank mask."""
        m = Image.new("1", (W, H), 0)
        draw(ImageDraw.Draw(m))
        return [(x, y) for y in range(H) for x in range(W) if m.getpixel((x, y))]

    def paint(self, pixels, c, c2=None, level=16, only=None):
        """Colour pixels: c, or a dither of c over c2 at level 0 (all c2) to 16 (all c).
        With `only`, just the pixels that are now that colour (or in that set)."""
        for x, y in pixels:
            if not (0 <= x < W and 0 <= y < H):
                continue
            if only is not None:
                here = self.px[y][x]
                if here != only and not (isinstance(only, (set, tuple, list)) and here in only):
                    continue
            if c2 is None or BAYER[y % 4][x % 4] < level:
                self.px[y][x] = c
            else:
                self.px[y][x] = c2

    # ------------------------------------------------------------------ shapes
    def rect(self, x0, y0, x1, y1, c, c2=None, level=16, only=None):
        self.paint([(x, y) for y in range(max(0, y0), min(H, y1 + 1))
                    for x in range(max(0, x0), min(W, x1 + 1))], c, c2, level, only)

    def poly(self, points, c, c2=None, level=16, only=None):
        self.paint(self.mask(lambda d: d.polygon(points, fill=1)), c, c2, level, only)

    def ellipse(self, cx, cy, rx, ry, c, c2=None, level=16, only=None):
        """rx is in screen units: half as many picture pixels, so circles stay round."""
        hx = rx / 2.0
        self.paint(self.mask(lambda d: d.ellipse((cx - hx, cy - ry, cx + hx, cy + ry), fill=1)),
                   c, c2, level, only)

    def line(self, x0, y0, x1, y1, c, width=1):
        self.paint(self.mask(lambda d: d.line((x0, y0, x1, y1), fill=1, width=width)), c)

    def arc(self, box, start, end, c, width=1):
        """Part of an ellipse's outline, in picture pixels (PIL's angles: 0 is east)."""
        self.paint(self.mask(lambda d: d.arc(box, start, end, fill=1, width=width)), c)

    def figure(self, x, y, c, tall=12, bag=False):
        """A standing person seen from a distance, feet at (x, y)."""
        self.rect(x - 1, y - tall, x + 1, y - tall + 2, c)          # head
        self.rect(x - 2, y - tall + 3, x + 2, y - 4, c)             # coat
        self.rect(x - 2, y - 3, x - 1, y, c)                        # legs
        self.rect(x + 1, y - 3, x + 2, y, c)
        if bag:
            self.rect(x + 3, y - 4, x + 5, y - 1, c)

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, y0, x, y1, c)

    def vgrad(self, x0, y0, x1, y1, top, bottom, only=None):
        """A vertical blend from `top` to `bottom` (two colours), dithered."""
        span = max(1, y1 - y0)
        for y in range(y0, y1 + 1):
            level = 16 - round(16 * (y - y0) / span)
            self.rect(x0, y, x1, y, top, bottom, level, only)

    def glow(self, cx, cy, rx, ry, c, steps=((1.0, 4), (0.75, 8), (0.5, 16)), only=None):
        """A soft light: rings of `c` dithered thinner toward the edge."""
        allowed = None if only is None else (set(only) if isinstance(only, (set, tuple, list))
                                             else {only})
        for scale, level in steps:
            hx, hy = rx * scale / 2.0, ry * scale
            for x, y in self.mask(lambda d: d.ellipse((cx - hx, cy - hy, cx + hx, cy + hy),
                                                      fill=1)):
                if allowed is not None and self.px[y][x] not in allowed:
                    continue
                if BAYER[y % 4][x % 4] < level:
                    self.px[y][x] = c

    def stars(self, x0, y0, x1, y1, c, every, seed):
        """A scatter of single pixels, one per `every` pixels or so."""
        n = seed
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                n = (n * 1103515245 + 12345) & 0x7FFFFFFF
                if n % every == 0:
                    self.set(x, y, c)

    def resolve(self, keep, drop, to):
        """In every 4 x 8 cell that holds both `keep` and `drop`, paint `drop` as `to`:
        a cell can only have one colour of its own (stars give way to the sun)."""
        for cy in range(0, H, 8):
            for cx in range(0, W, 4):
                cell = [(x, y) for y in range(cy, cy + 8) for x in range(cx, cx + 4)]
                colours = {self.px[y][x] for x, y in cell}
                if keep in colours and drop in colours:
                    for x, y in cell:
                        if self.px[y][x] == drop:
                            self.px[y][x] = to

    def text(self, x, y, words, c):
        """Capitals and digits in a 3 x 5 font (each letter 4 pixels apart)."""
        for ch in words:
            rows = FONT.get(ch)
            if rows:
                for dy, row in enumerate(rows):
                    for dx, bit in enumerate(row):
                        if bit == "#":
                            self.set(x + dx, y + dy, c)
            x += 4

    # ------------------------------------------------------------------ output
    def save(self, path):
        img = Image.new("RGB", (W, H))
        img.putdata([c64pic.PALETTE[c] for row in self.px for c in row])
        img.save(path)


def check(path):
    """How a PNG comes out on the C64: (pixels it changes, different cells)."""
    px = c64pic.load(path)
    pic, distinct = c64pic.convert(px)
    shown = c64pic.render(pic)
    changed = 0
    for y in range(H):
        for x in range(W):
            if shown.getpixel((x * 2, y)) != c64pic.PALETTE[px[y][x]]:
                changed += 1
    return changed, distinct


def report(paths):
    """Print check() for each picture; True if all come through within the C64's rules."""
    ok = True
    for path in paths:
        changed, distinct = check(path)
        flag = "" if changed == 0 and distinct <= 256 else "  <- the C64 changes it"
        ok = ok and not flag
        print(f"{os.path.basename(path)}: {distinct} cells, {changed} pixels changed{flag}")
    return ok


FONT = {
    "A": ["###", "#.#", "###", "#.#", "#.#"], "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": ["###", "#..", "#..", "#..", "###"], "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"], "F": ["###", "#..", "##.", "#..", "#.."],
    "G": ["###", "#..", "#.#", "#.#", "###"], "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"], "J": ["..#", "..#", "..#", "#.#", "###"],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"], "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"], "N": ["##.", "#.#", "#.#", "#.#", "#.#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"], "P": ["###", "#.#", "###", "#..", "#.."],
    "Q": ["###", "#.#", "#.#", "###", "..#"], "R": ["###", "#.#", "##.", "#.#", "#.#"],
    "S": ["###", "#..", "###", "..#", "###"], "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"], "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"], "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."], "Z": ["###", "..#", ".#.", "#..", "###"],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", ".##", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", "..#", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"],
    ":": ["...", ".#.", "...", ".#.", "..."], "-": ["...", "...", "###", "...", "..."],
    ".": ["...", "...", "...", "...", ".#."], " ": ["...", "...", "...", "...", "..."],
}
