"""Pictures of the art as the C64 shows it (docs/art-direction.md): figures, and a look's
tiles laid out as a small map with figures standing on it, at the cartridge's 16-pixel
squares or the C version's 32, so art can be judged at the size it's seen, and an
alternative beside what it replaces. Reads content/art/ (or APB_ART) through tools/art.py.

    python3 tools/artpreview.py figures OUT.png [NAME ...] [--zoom N]
    python3 tools/artpreview.py scene LOOK OUT.png [--size 16|32] [--against LOOK]
                                     [--figures NAME,NAME] [--zoom N]

`figures` draws each figure named (every one, if none are) on a dark grey ground, as the
cartridge draws a sprite: its shared colour a is black there. `scene` draws the look's
tiles on a 12 x 6 map with every terrain on it, a variant or scenery on some open squares
(the same ones every time), and figures standing on it (HUMAN and RUST_GUARD, or the ones
named); --against draws another look the same way on its left, to compare: forest
against forest2. Dots are two pixels wide, as on the C64; --zoom enlarges the picture
(whole pixels: 3 by default).
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import art  # noqa: E402
import c64pic  # noqa: E402

PALETTE = c64pic.PALETTE

# The map: every terrain, in the rules' order (. # O ~ + ^ = >), a wood round the edges.
MAP = ["##..#######.",
       "#....~~..###",
       "...+......##",
       "..OO..+..=..",
       "..OO.^^.....",
       "#.......>..#"]
TERRAIN = {".": "open", "#": "wall", "O": "pit", "~": "rough", "+": "cover", "^": "hazard",
           "=": "high", ">": "exit"}
STANDING = [(4, 2), (7, 2), (2, 5), (9, 4)]       # where the figures stand


def _image():
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("artpreview: needs Pillow (pip install Pillow)")
    return Image


def figure(e, shared):
    """A figure as the cartridge draws it: 24 x 21, see-through where it's '.'."""
    Image = _image()
    colour = {"a": 0, "b": shared[1], "c": e.colour}
    im = Image.new("RGBA", (24, 21), (0, 0, 0, 0))
    for y, row in enumerate(e.rows):
        for x, ch in enumerate(row):
            if ch != ".":
                for dx in (0, 1):
                    im.putpixel((2 * x + dx, y), PALETTE[colour[ch]] + (255,))
    return im


def tile(e, look):
    """A tile in its look's colours: 32 x 32 or 16 x 16."""
    Image = _image()
    colour = {"k": look.background, "d": look.shared[0], "g": look.shared[1], "o": e.colour}
    im = Image.new("RGB", (2 * len(e.rows[0]), len(e.rows)))
    for y, row in enumerate(e.rows):
        for x, ch in enumerate(row):
            for dx in (0, 1):
                im.putpixel((2 * x + dx, y), PALETTE[colour[ch]])
    return im


def scene(look, size, names):
    """The map in a look, at squares of `size` pixels, with the figures named on it."""
    Image = _image()
    tiles = art.load(art.tiles_file(size, look))
    figs = art.load("figures")
    by = {e.name: e for e in tiles.entries}
    extra = [e.name for e in tiles.entries[8:]]
    rnd = random.Random(7)
    im = Image.new("RGB", (len(MAP[0]) * size, len(MAP) * size))
    for y, row in enumerate(MAP):
        for x, ch in enumerate(row):
            name = TERRAIN[ch]
            if name == "open" and extra and rnd.random() < 0.25:
                name = rnd.choice(extra)
            im.paste(tile(by[name], tiles), (x * size, y * size))
    for name, (x, y) in zip(names, STANDING):
        s = figure(figs.entry(name), figs.shared)
        # A sprite stands on its square: on 16-pixel squares it's bigger than the square.
        at = (x * 16 - 4, y * 16 - 5) if size == 16 else (x * 32 + 4, y * 32 + 8)
        im.paste(s, at, s)
    return im


def enlarge(im, k):
    return im.resize((im.width * k, im.height * k), _image().NEAREST)


def main(argv):
    args, opts, i = [], {}, 1
    while i < len(argv):
        if argv[i].startswith("--"):
            if i + 1 >= len(argv):
                raise SystemExit(f"artpreview: {argv[i]} wants a value")
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    Image = _image()
    k = int(opts.get("zoom", 3))
    try:
        if args[:1] == ["figures"] and len(args) >= 2:
            figs = art.load("figures")
            names = args[2:] or [e.name for e in figs.entries]
            im = Image.new("RGB", (len(names) * 30 + 6, 27), PALETTE[11])
            for n, name in enumerate(names):
                s = figure(figs.entry(name), figs.shared)
                im.paste(s, (6 + n * 30, 3), s)
            enlarge(im, k).save(args[1])
        elif args[:1] == ["scene"] and len(args) == 3:
            size = int(opts.get("size", 16))
            if size not in (16, 32):
                raise SystemExit("artpreview: --size is 16 or 32")
            names = opts.get("figures", "HUMAN,RUST_GUARD").split(",")
            pics = [scene(opts["against"], size, names)] if "against" in opts else []
            pics.append(scene(args[1], size, names))
            im = Image.new("RGB", (sum(p.width for p in pics) + 8 * (len(pics) - 1), pics[0].height),
                           (30, 30, 36))
            for n, p in enumerate(pics):
                im.paste(p, (n * (p.width + 8), 0))
            enlarge(im, k).save(args[2])
        else:
            print(__doc__)
            return 2
    except (art.Problem, OSError) as e:
        raise SystemExit(f"artpreview: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
