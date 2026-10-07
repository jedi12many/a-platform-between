"""Fit any picture to the C64's rules (docs/c64.md, "Pictures"): art from anywhere (a
drawing, a photo, an image model) into a 160 x 96 PNG that tools/c64pic.py shows
unchanged.

    python3 tools/c64fit.py IN OUT.png [--box X0,Y0,X1,Y1] [--dither ordered|none]
                                       [--shared C,C,C]

1. **The shape.** The middle of the picture is cut to 10:3 (the screen's picture strip)
   and scaled to 160 x 96, each pixel standing for a patch twice as wide as it is tall.
   `--box` keeps a region instead, as fractions of the width and height (0,0.2,1,0.8
   is the full width, the middle 60%), and scales it to the strip whatever its shape:
   art that isn't 10:3 can be squeezed a little rather than cut.
2. **The shared three.** Every choice of three among the colours the picture uses most is
   tried; the one that leaves the least error wins. (`--shared` names them instead, by
   number 0-15, background first.)
3. **Each cell's own.** Every 4 x 8 cell takes the one of the first eight colours that
   suits it best.
4. **The pixels.** Each pixel takes the nearest of its cell's four colours, or with
   `--dither ordered` (the default) a 4 x 4 Bayer pattern between the nearest two, so
   shading survives as checkerboard. (Art that is dithered already often looks better
   with `--dither none`.)
5. **The characters.** At most 256 different cells: past that, the rarest are redrawn as
   the kept pattern that looks most like them.

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


def shape(img, box=None):
    """Cut the middle to 10:3 (or keep `box`) and scale to 160 x 96 (each pixel a 2:1
    patch)."""
    img = img.convert("RGB")
    w, h = img.size
    if box:
        x0, y0, x1, y1 = box
        img = img.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
    elif w * 3 > h * 10:
        cw = h * 10 // 3
        img = img.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    else:
        ch = w * 3 // 10
        img = img.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch))
    return np.asarray(img.resize((W, H), Image.LANCZOS), dtype=np.float64)


def lab(rgb):
    """sRGB (0-255) to CIE L*a*b*, for distances that look right to the eye."""
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192],
                        [0.1805, 0.0722, 0.9505]])
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], -1)


PAL_LAB = lab(PAL)


def distance(rgb, colours):
    """How different each pixel looks from each colour: (..., len(colours)), as squared
    distance in L*a*b*. A light grey the C64 doesn't have stays grey (or white), rather
    than turning light green because that's about as bright."""
    d = lab(rgb)[..., None, :] - PAL_LAB[list(colours)]
    return (d * d).sum(-1)


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


def limit_characters(rgb, px, shared, own, most=256):
    """At most `most` different cells (the C64 has 256 characters): while there are more,
    the rarest cell pattern is redrawn as whichever kept pattern looks most like it, in
    that cell's own four colours."""
    slots = np.zeros_like(px)
    for n in range(480):
        cy, cx = divmod(n, 40)
        options = list(shared) + [int(own[n])]
        block = px[cy * 8:cy * 8 + 8, cx * 4:cx * 4 + 4]
        for i, c in reversed(list(enumerate(options))):     # a shared colour wins, as in c64pic
            slots[cy * 8:cy * 8 + 8, cx * 4:cx * 4 + 4][block == c] = i
    patterns = [slots[(n // 40) * 8:(n // 40) * 8 + 8, (n % 40) * 4:(n % 40) * 4 + 4].tobytes()
                for n in range(480)]
    counts = {}
    for pat in patterns:
        counts[pat] = counts.get(pat, 0) + 1
    if len(counts) <= most:
        return px
    kept = sorted(counts, key=lambda pat: -counts[pat])[:most]
    kept_arrays = np.array([np.frombuffer(k, dtype=slots.dtype).reshape(8, 4) for k in kept])
    keep = set(kept)
    out = px.copy()
    for n, pat in enumerate(patterns):
        if pat in keep:
            continue
        cy, cx = divmod(n, 40)
        options = np.array(list(shared) + [int(own[n])])
        block = rgb[cy * 8:cy * 8 + 8, cx * 4:cx * 4 + 4]
        d = distance(block, options)                                     # (8, 4, 4)
        cost = np.take_along_axis(d[None], kept_arrays[..., None], -1)[..., 0].sum((1, 2))
        if int(own[n]) in shared:
            # Its own colour is a shared one, so c64pic would read those pixels as the
            # shared colour: a different pattern. Only patterns without them will do.
            cost[(kept_arrays == 3).any((1, 2))] = np.inf
        out[cy * 8:cy * 8 + 8, cx * 4:cx * 4 + 4] = options[kept_arrays[int(cost.argmin())]]
    return out


def fit(path, out_path, dither="ordered", shared=None, box=None):
    rgb = shape(Image.open(path), box)
    shared = shared or choose_shared(rgb)
    own, _ = fit_cells(rgb, shared)
    px = limit_characters(rgb, paint(rgb, shared, own, dither), shared, own)
    img = Image.new("RGB", (W, H))
    img.putdata([c64pic.PALETTE[c] for c in px.ravel()])
    img.save(out_path)
    return shared


def main(argv):
    options = {"--dither": "ordered", "--shared": None, "--box": None}
    args = []
    rest = iter(argv[1:])
    for a in rest:
        if a in options:
            options[a] = next(rest, None)
        else:
            args.append(a)
    dither = options["--dither"]
    shared = [int(c) for c in options["--shared"].split(",")] if options["--shared"] else None
    box = [float(v) for v in options["--box"].split(",")] if options["--box"] else None
    if (len(args) != 2 or dither not in ("ordered", "none") or (shared and len(shared) != 3)
            or (box and not (len(box) == 4 and 0 <= box[0] < box[2] <= 1
                             and 0 <= box[1] < box[3] <= 1))):
        print(__doc__)
        return 2
    trio = fit(args[0], args[1], dither, shared, box)
    import paint as check
    changed, distinct = check.check(args[1])
    print(f"{args[1]}: shared {trio}, {distinct} different cells, {changed} pixels the C64 "
          f"changes" + (" (more than 256 cells: the rarest are drawn with the nearest)"
                        if distinct > 256 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
