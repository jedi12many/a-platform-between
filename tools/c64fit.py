"""Fit any picture to the C64's rules (docs/c64.md, "Pictures"): art from anywhere (a
drawing, a photo, an image model) into a 160 x 96 PNG that tools/c64pic.py shows
unchanged.

    python3 tools/c64fit.py IN OUT.png [--dither ordered|none] [--shared C,C,C]

1. **The shape.** The middle of the picture is cut to 10:3 (the screen's picture strip)
   and scaled to 160 x 96, each pixel standing for a patch twice as wide as it is tall.
2. **The shared three.** Every choice of three among the colours the picture uses most is
   tried; the one that leaves the least error wins. (`--shared` names them instead, by
   number 0-15, background first.)
3. **Each cell's own.** Every 4 x 8 cell takes the one of the first eight colours that
   suits it best.
4. **The pixels.** Each pixel takes the nearest of its cell's four colours, or with
   `--dither ordered` (the default) a 4 x 4 Bayer pattern between the nearest two, so
   shading survives as checkerboard.

Then it checks the result with tools/paint.py and says how it went. Needs numpy and
Pillow (only this tool; the build doesn't use it).
"""

import itertools
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c64pic  # noqa: E402

W, H = c64pic.W, c64pic.H
PAL = np.array(c64pic.PALETTE, dtype=np.float64)
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 + 1 / 32.0
WEIGHTS = np.array([0.30, 0.59, 0.11]) * 3       # brightness matters most to the eye


def shape(img):
    """Cut the middle to 10:3 and scale to 160 x 96 (each pixel a 2:1 patch)."""
    img = img.convert("RGB")
    w, h = img.size
    if w * 3 > h * 10:
        cw = h * 10 // 3
        img = img.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    else:
        ch = w * 3 // 10
        img = img.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch))
    return np.asarray(img.resize((W, H), Image.LANCZOS), dtype=np.float64)


def distance(rgb, colours):
    """Weighted squared distance from each pixel to each colour: (..., len(colours))."""
    d = rgb[..., None, :] - PAL[list(colours)]
    return (d * d * WEIGHTS).sum(-1)


def cells(rgb):
    """The picture as 480 cells of 32 pixels: (480, 32, 3)."""
    return rgb.reshape(12, 8, 40, 4, 3).transpose(0, 2, 1, 3, 4).reshape(480, 32, 3)


def fit_cells(rgb, shared):
    """Each cell's own colour (0-7) and the total error, for these shared three."""
    c = cells(rgb)
    base = distance(c, shared).min(-1)                       # (480, 32)
    own = distance(c, range(8))                              # (480, 32, 8)
    err = np.minimum(base[..., None], own).sum(1)            # (480, 8)
    best = err.argmin(1)
    return best, err[np.arange(480), best].sum()


def choose_shared(rgb):
    near = distance(rgb, range(16)).argmin(-1)
    common = [int(c) for c in np.argsort(-np.bincount(near.ravel(), minlength=16))[:8]]
    best = None
    for trio in itertools.combinations(common, 3):
        _, e = fit_cells(rgb, trio)
        if best is None or e < best[0]:
            best = (e, trio)
    trio = list(best[1])
    counts = np.bincount(near.ravel(), minlength=16)
    return sorted(trio, key=lambda c: -counts[c])            # background: the most used


def paint(rgb, shared, own, dither):
    out = np.zeros((H, W), dtype=np.int64)
    for n in range(480):
        cy, cx = divmod(n, 40)
        options = list(shared) + [int(own[n])]
        block = rgb[cy * 8:cy * 8 + 8, cx * 4:cx * 4 + 4]
        d = distance(block, options)                         # (8, 4, 4)
        order = np.argsort(d, -1)
        first, second = order[..., 0], order[..., 1]
        if dither == "ordered":
            d1 = np.take_along_axis(d, first[..., None], -1)[..., 0]
            d2 = np.take_along_axis(d, second[..., None], -1)[..., 0]
            # How far along from the nearest to the next: the share the next one gets.
            t = np.sqrt(d1) / np.maximum(np.sqrt(d1) + np.sqrt(d2), 1e-9)
            pick = np.where(t > np.tile(BAYER, (2, 1)), second, first)
        else:
            pick = first
        out[cy * 8:cy * 8 + 8, cx * 4:cx * 4 + 4] = np.array(options)[pick]
    return out


def fit(path, out_path, dither="ordered", shared=None):
    rgb = shape(Image.open(path))
    shared = shared or choose_shared(rgb)
    own, _ = fit_cells(rgb, shared)
    px = paint(rgb, shared, own, dither)
    img = Image.new("RGB", (W, H))
    img.putdata([c64pic.PALETTE[c] for c in px.ravel()])
    img.save(out_path)
    return shared


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    dither = "ordered"
    shared = None
    for i, a in enumerate(argv):
        if a == "--dither":
            dither = argv[i + 1]
        if a == "--shared":
            shared = [int(c) for c in argv[i + 1].split(",")]
    args = [a for a in args if a not in (dither, ",".join(map(str, shared or [])))]
    if len(args) != 2 or dither not in ("ordered", "none") or (shared and len(shared) != 3):
        print(__doc__)
        return 2
    trio = fit(args[0], args[1], dither, shared)
    import paint as check
    changed, distinct = check.check(args[1])
    print(f"{args[1]}: shared {trio}, {distinct} different cells, {changed} pixels the C64 "
          f"changes" + (" (more than 256 cells: the rarest are drawn with the nearest)"
                        if distinct > 256 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
