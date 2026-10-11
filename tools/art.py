"""The game's art, read from its files (docs/art.md): the figures, the effects and the
map's tiles in content/art/, as text grids anyone can read in a diff, and that the art
desk (tools/artdesk/) edits. tools/battlegfx.py builds the battle graphics from them.

    import art
    figures = art.load("figures")        # an Art: .shared, .entries
    figures.entry("HUMAN").rows           # 21 rows of 12: . a b c
    art.check_all()                       # every file, every rule: a list of problems

    python3 tools/art.py check            # says what's wrong, if anything

A file is lines. `#` starts a comment line; blank lines are skipped. A header names the
colours every entry shares (`shared C1 C2`, and for tiles `background C`); then each
entry is a line `KIND NAME OPTION` and its rows, one line each:

    figure NAME COLOUR     21 rows of 12: . see-through, a b the shared colours, c its own
    effect NAME hires      21 rows of 24: . or #
    effect NAME multi      21 rows of 12: . a b c
    tile NAME COLOUR       rows of k (background) d g (shared) o (its own: one of the first
                           eight); 16 x 32 in tiles32, 8 x 16 in tiles16

Colours are named: black white red cyan purple green blue yellow orange brown pink dgrey
grey lgreen lblue lgrey (the C64's 0-15, in order).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.environ.get("APB_ART") or os.path.join(HERE, "..", "content", "art")  # (tests: a copy)

COLOURS = ["black", "white", "red", "cyan", "purple", "green", "blue", "yellow", "orange",
           "brown", "pink", "dgrey", "grey", "lgreen", "lblue", "lgrey"]
TERRAIN = ["open", "wall", "pit", "rough", "cover", "hazard", "high", "exit"]

# What each file holds: its kind of entry, and each kind's size and dots.
FILES = {
    "figures": {"figure": (12, 21, ".abc")},
    "effects": {"effect hires": (24, 21, ".#"), "effect multi": (12, 21, ".abc")},
    "tiles32": {"tile": (16, 32, "kdgo")},
    "tiles16": {"tile": (8, 16, "kdgo")},
}


class Problem(Exception):
    pass


class Entry:
    def __init__(self, kind, name, option, rows, line):
        self.kind, self.name, self.option, self.rows, self.line = kind, name, option, rows, line

    @property
    def colour(self):
        """A figure's or a tile's own colour, 0-15."""
        return COLOURS.index(self.option)


class Art:
    def __init__(self, name, header, entries, comments):
        self.name, self.header, self.entries, self.comments = name, header, entries, comments

    @property
    def shared(self):
        return tuple(COLOURS.index(c) for c in self.header["shared"])

    @property
    def background(self):
        return COLOURS.index(self.header["background"][0])

    def entry(self, name):
        for e in self.entries:
            if e.name == name:
                return e
        raise Problem(f"{self.name}: no {name}")


def path_of(name, folder=None):
    return os.path.join(folder or ART, name + ".txt")


def parse(name, text):
    """The file's text as an Art; Problem if it breaks a rule (with the line)."""
    if name not in FILES:
        raise Problem(f"{name}: not one of the art files ({', '.join(FILES)})")
    kinds = FILES[name]
    header, entries, comments = {}, [], []
    lines = text.split("\n")
    i = 0

    def where(n):
        return f"{name}.txt line {n + 1}"

    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln:
            i += 1
            continue
        if ln.startswith("#"):
            if not entries:
                comments.append(ln)
            i += 1
            continue
        words = ln.split()
        if words[0] in ("shared", "background"):
            want = 2 if words[0] == "shared" else 1
            if len(words) != want + 1 or any(c not in COLOURS for c in words[1:]):
                raise Problem(f"{where(i)}: '{ln}': give {want} colour name"
                              f"{'s' * (want > 1)} ({', '.join(COLOURS)})")
            header[words[0]] = words[1:]
            i += 1
            continue
        if len(words) != 3:
            raise Problem(f"{where(i)}: '{ln}': an entry starts KIND NAME OPTION")
        kind = words[0] + (" " + words[2] if words[0] == "effect" else "")
        if kind not in kinds:
            raise Problem(f"{where(i)}: '{ln}': {name}.txt holds "
                          f"{' or '.join(sorted(kinds))} entries")
        w, h, dots = kinds[kind]
        if words[0] in ("figure", "tile") and words[2] not in COLOURS:
            raise Problem(f"{where(i)}: '{words[2]}' isn't a colour ({', '.join(COLOURS)})")
        if words[0] == "tile" and COLOURS.index(words[2]) > 7:
            raise Problem(f"{where(i)}: a tile's own colour must be one of the first eight "
                          f"({', '.join(COLOURS[:8])}): the C64's multicolour cells")
        if any(e.name == words[1] for e in entries):
            raise Problem(f"{where(i)}: there's already a {words[1]}")
        rows = lines[i + 1:i + 1 + h]
        for k, r in enumerate(rows):
            if len(r) != w or any(c not in dots for c in r):
                raise Problem(f"{where(i + 1 + k)}: {words[1]}'s row {k + 1} must be {w} of "
                              f"{' '.join(dots)}: '{r}'")
        if len(rows) != h:
            raise Problem(f"{where(i)}: {words[1]} needs {h} rows, has {len(rows)}")
        entries.append(Entry(words[0], words[1], words[2], rows, i + 1))
        i += 1 + h
    for need in ("shared",) + (("background",) if name.startswith("tiles") else ()):
        if need not in header:
            raise Problem(f"{name}.txt: no '{need}' line")
    if name.startswith("tiles"):
        have = [e.name for e in entries[:8]]
        if have != TERRAIN:
            raise Problem(f"{name}.txt: the first eight tiles must be the terrain, in the "
                          f"rules' order: {' '.join(TERRAIN)} (they're {' '.join(have)})")
    return Art(name, header, entries, comments)


def load(name, folder=None):
    with open(path_of(name, folder)) as f:
        return parse(name, f.read())


def check_all(folder=None):
    problems = []
    for name in FILES:
        try:
            load(name, folder)
        except (Problem, OSError) as e:
            problems.append(str(e))
    return problems


def main(argv):
    if argv[1:2] != ["check"]:
        print(__doc__)
        return 2
    problems = check_all()
    for p in problems:
        print("art:", p)
    if not problems:
        print("art: " + ", ".join(f"{n}.txt ({len(load(n).entries)})" for n in FILES) + ": all well")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
