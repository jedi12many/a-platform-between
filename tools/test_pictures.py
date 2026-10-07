"""Tests for the pictures (docs/c64.md, "Pictures").

    python3 tools/test_pictures.py

- Every picture a Departure ships (content/**/pictures/*.png) comes through the C64's
  rules unchanged: no pixel altered, at most 256 different cells.
- tools/c64pic.py shares the three colours used most, unless they leave a cell with two
  colours of its own; then it finds three that fit (a picture made by hand to show it).
- tools/c64fit.py turns a soft, many-coloured painting into a picture the C64 shows
  unchanged.
"""

import glob
import os
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c64pic  # noqa: E402
import paint  # noqa: E402
import c64fit  # noqa: E402

failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print("FAIL:", what)


def shipped():
    pictures = sorted(glob.glob(os.path.join(HERE, "..", "content", "**", "pictures", "*.png"),
                                recursive=True))
    check(pictures, "no pictures found")
    for path in pictures:
        changed, distinct = paint.check(path)
        check(changed == 0 and distinct <= 256,
              f"{os.path.relpath(path, os.path.join(HERE, '..'))}: the C64 changes {changed} "
              f"pixels ({distinct} different cells)")
    print(f"ok  {len(pictures)} pictures come through the C64's rules unchanged")


def shared_that_fit():
    # Grey is used most, then dark grey, then a lot of yellow in one place; black and
    # red share the cells along the bottom, so the three used most (grey, dark grey,
    # yellow) leave those cells with two colours of their own.
    px = [[c64pic.PALETTE.index(c64pic.PALETTE[12])] * c64pic.W for _ in range(c64pic.H)]
    for y in range(0, 40):
        for x in range(0, 160):
            px[y][x] = 11                                      # dark grey sky
    for y in range(40, 60):
        for x in range(0, 60):
            px[y][x] = 7                                       # a yellow wall
    for y in range(88, 96):
        for x in range(0, 160):
            px[y][x] = 0 if x % 4 < 2 else 2                   # black and red, together
    counts = [0] * 16
    for row in px:
        for c in row:
            counts[c] += 1
    shared = c64pic.choose_shared(px, counts)
    check(sorted(shared) != sorted([12, 11, 7]), "the three used most don't fit, and were kept")
    pic, _ = c64pic.convert(px)
    shown = c64pic.render(pic)
    changed = sum(1 for y in range(c64pic.H) for x in range(c64pic.W)
                  if shown.getpixel((x * 2, y)) != c64pic.PALETTE[px[y][x]])
    check(changed == 0, f"with the shared three it found, the C64 still changes {changed} pixels")
    print(f"ok  when the three used most don't fit, c64pic shares {shared}, which do")


def fitting():
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "in.png"), os.path.join(tmp, "out.png")
        img = Image.new("RGB", (2000, 600))
        d = ImageDraw.Draw(img)
        for y in range(600):
            d.line((0, y, 2000, y), fill=(40 + y // 4, 20 + y // 10, 80 - y // 15))
        d.ellipse((1300, 80, 1600, 380), fill=(250, 140, 60))
        d.rectangle((0, 420, 2000, 600), fill=(30, 30, 40))
        d.polygon([(300, 420), (500, 150), (700, 420)], fill=(20, 60, 30))
        img.filter(ImageFilter.GaussianBlur(6)).save(src)
        for dither in ("ordered", "none"):
            c64fit.fit(src, out, dither)
            changed, distinct = paint.check(out)
            check(Image.open(out).size == (c64pic.W, c64pic.H), "c64fit: wrong size")
            check(changed == 0 and distinct <= 256,
                  f"c64fit --dither {dither}: the C64 changes {changed} pixels ({distinct} cells)")
    print("ok  c64fit makes a soft painting into a picture the C64 shows unchanged")


def main():
    shipped()
    shared_that_fit()
    fitting()
    print(f"picture tests: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
