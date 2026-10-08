"""Tests for the pictures (docs/c64.md, "Pictures").

    python3 tools/test_pictures.py

- Every picture a Departure ships (content/**/pictures/*.png) comes through the C64's
  rules unchanged: no pixel altered.
- tools/c64pic.py takes for the background the colour that lets every cell fit, even
  when it isn't the most used (a picture made by hand to show it), and a cell with too
  many colours keeps its three most used.
- tools/c64fit.py turns a soft, many-coloured painting, and busy art, into pictures the
  C64 shows unchanged.
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
        changed, crowded = paint.check(path)
        check(changed == 0, f"{os.path.relpath(path, os.path.join(HERE, '..'))}: the C64 "
                            f"changes {changed} pixels ({crowded} cells with too many colours)")
    print(f"ok  {len(pictures)} pictures come through the C64's rules unchanged")


def shown(px):
    pic, crowded = c64pic.convert(px)
    img = c64pic.render(pic)
    changed = sum(1 for y in range(c64pic.H) for x in range(c64pic.W)
                  if img.getpixel((x * 2, y)) != c64pic.PALETTE[px[y][x]])
    return changed, crowded, img


def background_that_fits():
    # Grey is used most, but the bottom row of cells has four other colours in each:
    # black, red, blue and yellow, in stripes. Only black as the background lets those
    # cells fit, and the grey cells don't mind.
    px = [[12] * c64pic.W for _ in range(c64pic.H)]
    for y in range(88, 96):
        for x in range(0, 160):
            px[y][x] = (0, 2, 6, 7)[x % 4]
    changed, crowded, _ = shown(px)
    check(changed == 0 and crowded == 0,
          f"black as the background fits everything, but {changed} pixels changed")
    # Five colours in one cell, none of them the background: the three used most stay.
    px = [[0] * c64pic.W for _ in range(c64pic.H)]
    cell = [1] * 12 + [2] * 8 + [5] * 6 + [6] * 4 + [3] * 2
    for i, c in enumerate(cell):
        px[i // 4][i % 4] = c
    changed, crowded, img = shown(px)
    kept = {img.getpixel((x * 2, y)) for y in range(8) for x in range(4)}
    check(crowded == 1 and kept == {c64pic.PALETTE[c] for c in (1, 2, 5)} | ({c64pic.PALETTE[0]} & kept),
          f"a crowded cell kept {kept}")
    print("ok  c64pic picks the background that lets every cell fit, and keeps a crowded "
          "cell's three most used")


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
            changed, _ = paint.check(out)
            check(Image.open(out).size == (c64pic.W, c64pic.H), "c64fit: wrong size")
            check(changed == 0, f"c64fit --dither {dither}: the C64 changes {changed} pixels")
        # Busy art (noise everywhere, like an image model's dithering), with a light grey
        # band that must stay grey.
        rng = __import__("random").Random(3)
        busy = Image.new("RGB", (1600, 900))
        busy.putdata([(v, v, v) for v in (rng.choice((40, 70, 120, 200)) for _ in range(1600 * 900))])
        ImageDraw.Draw(busy).rectangle((0, 300, 1600, 420), fill=(200, 200, 200))
        busy.save(src)
        c64fit.fit(src, out, "none", None, [0, 0.1, 1, 0.9])
        changed, _ = paint.check(out)
        check(changed == 0, f"c64fit on busy art: the C64 changes {changed} pixels")
        greys = {c64pic.PALETTE[i] for i in (0, 1, 11, 12, 15)}
        band = {Image.open(out).getpixel((x, 38)) for x in range(0, 160, 7)}
        check(band <= greys, f"c64fit: a light grey band came out in colour {band - greys}")
    print("ok  c64fit makes a soft painting, and busy art, into pictures the C64 shows unchanged")


def main():
    shipped()
    background_that_fits()
    fitting()
    print(f"picture tests: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
