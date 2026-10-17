# The art: figures, effects and tiles

*How it should look, and the work to do: [art-direction.md](art-direction.md). Pictures of
it as the C64 shows it: `python3 tools/artpreview.py`.*

The battle screen's graphics, on every front end, are built from four text files in
`content/art/` (and the tiles come in looks besides: *Looks*), which anyone can read in a diff and the **art desk** edits in a browser.
`tools/battlegfx.py` builds them into the C version's graphics file (`BGFX`: the C64's
`btab`/`bchr`/`bspr`, the desktop and the browser) and the cartridge's (asset 0). The
story's pictures are another matter: see `tools/c64fit.py` and `docs/c64.md`.

## The art desk

    make artdesk          (python3 tools/artdesk/serve.py)

and open <http://localhost:8064/>. It runs on this machine only, and saves straight into
`content/art/`; then `make` builds the game with the new art (and `git diff` shows it).

The art desk is one tool in the **studio** (`make studio`): its other tab is the native
arena ([arena.md](arena.md#the-native-arena)), which draws the art as it is now, so a figure
saved here can be fought with straight away. On the published site it's the **Art desk**
tab (`make site`; `serve.py --publish` writes it as plain files): there's no server there
to save into the game's files, so Save is **Download**, and the changed file is sent in.

- **Files**: Figures, Effects, Tiles 32 (the C version's map), Tiles 16 (the cartridge's),
  and **Look**: which look's tiles the two Tiles buttons open (the yard's, or the forest's,
  the mountains', the town's, the dungeon's; see *Looks*).
  A dot after a file's name: it has changes not saved yet. **Save** (Ctrl+S) saves them
  all; **Revert** goes back to what's saved.
- **Entries**: pick one from the list. **New**, **Duplicate**, **Rename**, **Delete**. The
  first eight tiles are the rules' terrain, in its order (open, wall, pit, rough, cover,
  hazard, high ground, exit): they can be redrawn but not renamed, moved or deleted. A
  tile after them is **scenery**, for rooms to come (E13): it's kept and checked, but the
  game doesn't place it yet. Under the figures' list the desk says which race or foe has
  no figure (the build needs one for each, and a stranger's).
- **Paste…**: art drawn elsewhere, pasted as text: a grid of characters (digits, letters,
  dots), one row a line, with its name on a line before it and `colour: red` on another if
  you like. Say which dot each character becomes (the choices show their colours: a
  figure has only three and see-through, so two characters may have to share one), and
  whether art too big for the entry is trimmed at the edges of what's drawn or squeezed
  in; a figure keeps its feet on the bottom row. The preview shows it in the game's
  colours, and the notes say what was given up. It goes in as a new entry, or into the
  one open (Undo takes it back). A new race or foe also needs its entry in the registry
  before the game draws it.
- **Dots**: the buttons 1-4 (or the keys) are the dots an entry can have, in their colours:
  1 is see-through (a figure, an effect) or the background (a tile). The left button paints
  the chosen dot, the right button the first.
- **Tools**: Pen (P), Line (L), Box (B), Fill (F), Pick a dot (I); Undo (Ctrl+Z), Redo
  (Ctrl+Y), Flip, the shifts (round the edge), Clear.
- **Colours**: each file's shared colours at the top left; each figure's and tile's own
  colour at the right (a tile's is one of the first eight: it's a multicolour cell's).
- **As the game shows it**: a figure on the C version's 32-pixel squares with its hires
  outline (standing, and down), and on the cartridge's 16-pixel ones with the outline
  drawn in; a tile side by side, as a square you can reach (the reach dot), and on the
  cartridge with the cursor on it; an effect on a square.

The rules hold by construction: there's no way to paint a dot the C64 can't show there.
A save goes through `tools/art.py`'s checks on the server, so a file that breaks one isn't
written, and the desk says why. `make test-art` drives the desk in headless Chromium.

## The files

`#` starts a comment; blank lines don't matter. A file starts with the colours its entries
share, then its entries: a line `KIND NAME OPTION`, then the rows, one dot a character.
Colours are named: black white red cyan purple green blue yellow orange brown pink dgrey
grey lgreen lblue lgrey (the C64's 0-15). `python3 tools/art.py check` checks them all.

| File | Header | Entries | Size | Dots |
|---|---|---|---|---|
| `figures.txt` | `shared C1 C2` (sprite multicolour 1, 2) | `figure NAME COLOUR` | 12 x 21 | `.` see-through, `a` `b` shared, `c` its own |
| `effects.txt` | `shared C1 C2` (the same) | `effect NAME hires` | 24 x 21 | `.` off, `#` on |
| | | `effect NAME multi` | 12 x 21 | as a figure's |
| `tiles32.txt` | `background C`, `shared C1 C2` | `tile NAME COLOUR` (one of the first eight) | 16 x 32 | `k` background, `d` `g` shared, `o` its own |
| `tiles16.txt` | the same | the same | 8 x 16 | the same |

A multicolour dot is two pixels wide, as on the C64. A figure's name is its race's or
foe's in the registry (`registry/*.txt`: `HUMAN`, `ASH_RAT`), or `STRANGER`; a figure
stands with its feet on the bottom row. The effects the battle screen uses are `CURSOR`,
`BOLT`, `SPARK` and `SLASH`.

## Looks

The same eight terrain tiles, redrawn for a place: a **look**. There are four besides the
yard's own (`tiles32.txt`, `tiles16.txt`, what the game draws now): **forest**, **mountain**,
**town** and **dungeon**, each a pair of files, `tiles32-forest.txt` and `tiles16-forest.txt`,
in the same format. A look has its own background and shared colours (three of the C64's
registers, so changing look costs nothing on screen) and each tile its own colour.

After the eight terrain tiles a look holds:

- **Variants**: a terrain's name with a number (`open2`, `open3`, `wall2`), the same terrain
  drawn another way, so a floor isn't one tile repeated. Squares pick them now and then.
- **Scenery**: any other name (`mushrooms`, `lamp`, `skull`): drawn on open ground now and
  then, and nothing more; it changes no rule.

How a room picks them is in [rooms.md](rooms.md#looks); the arena's exploring (E13) draws
the looks now, and the game will when rooms come to it. On the cartridge a look is an asset
of its own, every tile 12 of the map's 256 characters (its four, with the reach dot, with
the cursor), so a tiles16 file holds at most **21** tiles: `art.py` refuses more, and
`battlegfx.py --looks` builds each look's characters to prove they fit. The first pass at
the four looks was drawn by a program as starting points: redraw them freely in the desk.

**Alternatives** are numbered: `forest2`, `forest3`, a whole look drawn again, each a pair
(`tiles32-forest2.txt` and `tiles16-forest2.txt`), counting up from 2 with no gaps.
`art.py` finds them on disk and holds them to the same rules (and says so when a pair is
missing its other half); the desk and the arena list them beside the four. A figure can be
drawn again the same way, as a new entry in `figures.txt` named after the race or foe with
a number (`HUMAN2`, `RUST_GUARD2`): the builds draw only the figure named exactly, so an
alternative waits there to be picked, and costs the cartridge nothing until it is.

## What the build adds

Some of what the game shows isn't drawn but made from the art, the same way every time
(`tools/battlegfx.py`; the desk's previews do the same):

- **A figure down**: its rows squashed into the bottom six (`fallen`).
- **The C version's outline**: a hires sprite in black over each figure, every pixel next
  to the body (`outline`). The cartridge has no sprite to spare for it, so its figures
  have the outline drawn into the body instead, in the first shared colour, which the
  cartridge makes black (`outlined`).
- **A square you can reach**: the tile with a black dot in its middle (`marked`,
  `marked16`). **The cartridge's cursor**: a bracket at each corner, in the tile's own
  colour, which the cartridge sets to the cursor's (`cursor16`).

The cartridge sets some colours itself: the 16-pixel tiles' background and shared
colours (black, dgrey, grey: `cart/screen.s`) and the figures' second shared colour
(lgrey: `cart/tactics.s`). The build refuses art that changes them, and says where to
change them too.
