"""What the C64's VIC-II shows, for a screen in multicolour character mode with sprites:
the reference the front ends' battle screens are checked against (docs/c64-hardware.md).

    from vic import Screen
    s = Screen(charset, background, mc1, mc2, sprite_mc1, sprite_mc2)
    s.put(col, row, char, colour)          # colour 0-7: hires; 8-15: multicolour
    s.sprite(x, y, data, colour, multicolour)
    img = s.image(border)                  # 320 x 200 (or with a border round it)

Sprites are placed by the screen's own pixels (0,0 is the top left of the 40 x 25
characters), drawn in the order given, the later on top, as the VIC draws sprite 0 over
sprite 7. Multicolour sprite pixels are two wide: 01 is sprite_mc1, 10 the sprite's own
colour, 11 sprite_mc2.
"""

import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from c64pic import PALETTE  # noqa: E402

W, H = 320, 200


class Screen:
    def __init__(self, charset, background, mc1, mc2, sprite_mc1, sprite_mc2):
        self.charset = charset
        self.colours = (background, mc1, mc2)
        self.sprite_mc = (sprite_mc1, sprite_mc2)
        self.cells = [[(32, 1)] * 40 for _ in range(25)]
        self.sprites = []

    def put(self, col, row, char, colour):
        if 0 <= col < 40 and 0 <= row < 25:
            self.cells[row][col] = (char, colour)

    def sprite(self, x, y, data, colour, multicolour):
        self.sprites.append((x, y, data, colour, multicolour))

    def pixels(self):
        bg, mc1, mc2 = self.colours
        px = [[bg] * W for _ in range(H)]
        for row in range(25):
            for col in range(40):
                ch, colour = self.cells[row][col]
                glyph = self.charset[ch * 8:ch * 8 + 8]
                for y in range(8):
                    b = glyph[y]
                    if colour & 8:
                        for x in range(4):
                            v = (b >> (6 - 2 * x)) & 3
                            c = (bg, mc1, mc2, colour & 7)[v]
                            px[row * 8 + y][col * 8 + 2 * x] = c
                            px[row * 8 + y][col * 8 + 2 * x + 1] = c
                    else:
                        for x in range(8):
                            if (b >> (7 - x)) & 1:
                                px[row * 8 + y][col * 8 + x] = colour & 7
        for x0, y0, data, colour, multi in self.sprites:
            for y in range(21):
                bits = (data[y * 3] << 16) | (data[y * 3 + 1] << 8) | data[y * 3 + 2]
                for x in range(12 if multi else 24):
                    if multi:
                        v = (bits >> (22 - 2 * x)) & 3
                        if v:
                            c = (None, self.sprite_mc[0], colour, self.sprite_mc[1])[v]
                            for dx in (0, 1):
                                self._plot(px, x0 + 2 * x + dx, y0 + y, c)
                    elif (bits >> (23 - x)) & 1:
                        self._plot(px, x0 + x, y0 + y, colour)
        return px

    @staticmethod
    def _plot(px, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = c

    def image(self, border=None, size=32):
        px = self.pixels()
        img = Image.new("RGB", (W, H))
        img.putdata([PALETTE[c] for row in px for c in row])
        if border is None:
            return img
        framed = Image.new("RGB", (W + 2 * size, H + 2 * size), PALETTE[border])
        framed.paste(img, (size, size))
        return framed
