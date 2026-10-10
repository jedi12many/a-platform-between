"""The game's own font on the C64 (docs/c64.md, "The screen"): the story's text, in place
of the ROM's characters.

    python3 tools/c64font.py OUT [--sheet SHEET.png]

The same letters as the battle screen's (tools/battlegfx.py: font8x8, each stroke a pixel
wider), laid out the way the C64's upper/lower case set is, by screen code, so
fe/c64/c64.c writes text as it always has: @ at 0, a-z at 1-26, [ \\ ] ^ _ at 27-31, space
to ? at 32-63, ` at 64, A-Z at 65-90, { | } ~ at 91-94; the frames' own characters
(docs/frames.md) at 96-99: the line between the frames, and a health bar's cells, empty,
half and full (fe/modern/render.c draws the same); and 128-255 the same in reverse, for
the status bar and "-- more --". The other codes are blank.

OUT is a program file that loads at $E000 (where the picture goes later); the game copies
it to $D000, under the I/O, where the VIC sees it (fe/c64/split.s, font_install).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from battlegfx import font8x8, glyph  # noqa: E402

LOAD_AT = 0xE000


def screen_code_of(ascii_code):
    """Where an ASCII character sits in the set, or None."""
    if ascii_code == 0x40:
        return 0
    if 0x61 <= ascii_code <= 0x7A:
        return ascii_code - 0x60
    if 0x5B <= ascii_code <= 0x5F:
        return ascii_code - 0x40
    if 0x20 <= ascii_code <= 0x3F:
        return ascii_code
    if ascii_code == 0x60:
        return 0x40
    if 0x41 <= ascii_code <= 0x5A:
        return ascii_code
    if 0x7B <= ascii_code <= 0x7E:
        return ascii_code - 0x20
    return None


FRAMES = {   # screen code: rows, bit 7 the left
    0x60: [0x10] * 8,                                           # the line between frames
    0x61: [0x7E, 0x42, 0x42, 0x42, 0x42, 0x7E, 0x00, 0x00],     # a bar's cell: empty
    0x62: [0x7E, 0x72, 0x72, 0x72, 0x72, 0x7E, 0x00, 0x00],     # half
    0x63: [0x7E, 0x7E, 0x7E, 0x7E, 0x7E, 0x7E, 0x00, 0x00],     # full
}


def build():
    charset = bytearray(2048)
    for at, rows in FRAMES.items():
        charset[at * 8:at * 8 + 8] = bytes(rows)
    glyphs = font8x8()                      # ASCII 32-126
    for code in range(0x20, 0x7F):
        at = screen_code_of(code)
        if at is not None:
            charset[at * 8:at * 8 + 8] = bytes(glyph(glyphs[code - 0x20]))
    for at in range(128):
        charset[(128 + at) * 8:(129 + at) * 8] = bytes(b ^ 0xFF for b in charset[at * 8:at * 8 + 8])
    return bytes(charset)


def sheet(charset, path):
    from PIL import Image
    img = Image.new("RGB", (16 * 9 * 2, 16 * 9 * 2), (40, 40, 40))
    for ch in range(256):
        cx, cy = ch % 16, ch // 16
        for y in range(8):
            for x in range(8):
                on = (charset[ch * 8 + y] >> (7 - x)) & 1
                c = (154, 210, 132) if on else (0, 0, 0)
                for dx in (0, 1):
                    for dy in (0, 1):
                        img.putpixel(((cx * 9 + x) * 2 + dx, (cy * 9 + y) * 2 + dy), c)
    img.save(path)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    charset = build()
    with open(argv[1], "wb") as f:
        f.write(bytes([LOAD_AT & 0xFF, LOAD_AT >> 8]) + charset)
    if "--sheet" in argv:
        sheet(charset, argv[argv.index("--sheet") + 1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
