"""The game's art (content/art/, read through tools/art.py) as one JSON file for the
native arena (tools/arena/web/), which draws it on a canvas at a modern size: the figures,
the effects, the 32-pixel tiles (the yard's, and each look's), the 16-pixel ones the cartridge
draws (for the arena's C64 scale), and the C64's sixteen colours.

    python3 tools/arena/web/art_json.py OUT.json
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import art  # noqa: E402
from c64pic import PALETTE  # noqa: E402


def entries(a):
    return {e.name: {"kind": e.kind, "option": e.option, "rows": e.rows} for e in a.entries}


def build(folder=None):
    """The art in `folder` (content/art/ if None) as the arena draws it."""
    figures, effects = art.load("figures", folder), art.load("effects", folder)
    tiles = art.load("tiles32", folder)

    def look(a):
        return {"shared": list(a.shared), "background": a.background,
                "entries": entries(a), "order": [e.name for e in a.entries]}
    return {
        "palette": ["#%02x%02x%02x" % c for c in PALETTE],
        "colours": art.COLOURS,
        "terrain": art.TERRAIN,
        "figures": {"shared": list(figures.shared), "entries": entries(figures)},
        "effects": {"shared": list(effects.shared), "entries": entries(effects)},
        "tiles": look(tiles),
        "looks": {name: look(art.load(art.tiles_file(32, name), folder)) for name in art.LOOKS},
        "tiles16": look(art.load("tiles16", folder)),
        "looks16": {name: look(art.load(art.tiles_file(16, name), folder)) for name in art.LOOKS},
    }


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[1], "w") as f:
        json.dump(build(), f, separators=(",", ":"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
