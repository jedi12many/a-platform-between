# Art direction

How the game's art should look, for whoever draws it. [art.md](art.md) is the file
format and what the hardware allows; this page is the style inside it. The pixel-art
skill's C64 notes (`.claude/skills/pixel-art/references/c64.md`) are the craft; where they
and this page differ, this page wins.

## What we're after

The C64 RPGs and adventure games of the last few years, and the best of the old ones:
dark floors, every object lit and edged so it reads on its own, small figures in poses
that say who they are. Ours had gone the other way: flat bright floors, solid blocks for
figures, walls in a repeating grid. On the C64's double-wide pixels that reads as
chunky. Detail and darkness hide the pixel grid; flat fills show it.

**The references are in the repository:** the look `forest2` (`content/art/tiles32-forest2.txt`,
`tiles16-forest2.txt`) and the figures `HUMAN2` and `RUST_GUARD2` (`content/art/figures.txt`).
Draw everything else in their style. (forest2's tiles were drafted by a script and want
finishing by hand: see *The work*.)

## See it as the player will

Judge art at the size it's seen, never only zoomed in the desk:

```
python3 tools/artpreview.py scene forest2 out.png --against forest     # the cartridge's 16-pixel squares
python3 tools/artpreview.py scene forest2 out.png --size 32            # the C version's 32
python3 tools/artpreview.py scene forest2 out.png --figures HUMAN2,RUST_GUARD2
python3 tools/artpreview.py figures out.png HUMAN HUMAN2 --zoom 6
```

`scene` lays a look's tiles out as a small map with every terrain on it and figures
standing there; `--against` puts another look beside it. The arena's explore prototype
(`make studio`, http://localhost:8064/arena/, Explore the yards) lists every look,
alternatives too, to walk around in.

## Tiles: a look

**1. Dark floors, in every biome.** A look's background (`k`) is black, or the darkest
colour that suits the place. The floor is the background with a light texture over it:
single dots on a loose grid, about one a 4 x 4 dots, nudged off the grid, mostly the
darker shared colour (`d`) and one in six or seven the lighter (`g`). Never a flat fill,
never noise. forest2's `open` is the example. Light (day, dusk) is carried by the lit
objects, not the floor.

**2. Objects stand apart, lit from the top left.** A tree, a rock, a bush is a shape of
its own with black round it where it meets the next:

- the lighter shared colour (`g`) on the upper left, as the light falls;
- the darker (`d`) for its body;
- toward the lower right, the body dithered into black (alternate dots), then a black gap;
- its own colour (`o`) for what tells it apart: a trunk, berries, flowers, a glint.

**3. The eight terrains must be told apart at a glance**, in any look, because they're
rules, not decoration (docs/turn.md):

| Tile | What it means in a fight | Draw it as |
|---|---|---|
| `open` | walk freely | the floor's texture, nothing else |
| `wall` | blocks movement and sight | the place's mass: trees close together, cliff, building, masonry |
| `pit` | can't stand; fall in | water, a drop: the biggest dark or blue area |
| `rough` | costs 2 to cross | undergrowth, rubble, scree: busy, low, broken |
| `cover` | costs 2; cover against shots | one solid object a figure could crouch behind: a bush, crate, boulder |
| `hazard` | hurts whoever steps in or stays | something plainly dangerous in a bright colour: thorns, embers, spikes |
| `high` | raised ground | a mound or ledge, lit on top, with a shadow below |
| `exit` | the way out | a path, a gap, a door, in a colour nothing else uses |

**4. Colours that read on black.** A tile's own colour is one of the first eight
(black white red cyan purple green blue yellow). On a black floor, white, cyan, purple,
green and yellow read; red and blue are dark, good only in big areas (water, trunks,
bricks), never for small marks. Pick the look's two shared colours (`d`, `g`) as a
two-step ramp for the biome: forest2 is green and light green. Suggestions:

| Look | Shared (`d`, `g`) | Own colours for |
|---|---|---|
| mountain | grey, light grey | white snow and glints, blue ice, yellow lichen |
| town | brown, orange | red brick and roofs, yellow windows, cyan glass |
| dungeon | dark grey, grey | purple slime, yellow torchlight, red rust |

**5. Tiles tile.** A wall drawn next to itself must make one wood or one cliff without
a seam (draw its shapes across the edges, wrapping); a single object (cover, high, a
scenery tile) keeps a black margin so it sits on any floor. Check with `artpreview`.

**6. tiles16 is drawn, not shrunk.** The cartridge draws the 16-pixel tiles (8 x 16 dots),
and they're what the C64 player sees. Draw them by hand at that size: one object a square
(one tree, not a wood), fewer dots, the same colours as the look's tiles32. At most 21
tiles in a tiles16 file.

**7. Variants and scenery** (after the eight): two or three variants of `open` (a few
flowers, fallen leaves) so the floor isn't one tile repeated, and two or three scenery
tiles (mushrooms, a stump, a sign), small, on the floor's texture.

## Figures

A figure is a sprite: 12 dots by 21 rows, each dot two pixels wide, and **three
colours**: `a` (black on the cartridge, dark grey in the C version), `b` (light grey) and
`c`, its own. `a` and `b` are every figure's, so the cast's clothes, metal and shadow are
greys; `c` is what tells one apart: skin, rust, a glow.

- **Pose:** three-quarter or side on, **facing right** (every figure the same way: nothing
  turns them yet), mid-stride or in a stance, not square to the front. Feet on the bottom
  row.
- **Slim:** the body six to eight dots wide; let the 12-dot box breathe. Limbs one dot
  wide; legs apart so the gap shows.
- **Something to know it by:** each figure belongs to a race or a foe, not a class (every
  class of a race shares it), so its mark is the race's or the foe's: the rust guard's
  spear, moth wings, glass shards, a drone's lamp. It should show in silhouette.
- **A face:** a few dots of `c`, an `a` dot for the eye, hair or a helmet in `a`.
- **Light from the top left:** `b` on the lit side, `a` in shade and for lines inside the
  body (a belt, the gap between arm and coat). Don't draw an outline round the outside:
  the build adds one.
- **Silhouette test:** fill it black. Can you still tell what it is?

`HUMAN2` and `RUST_GUARD2` are the references.

## Naming and the rules of the files

- **Never change or remove the originals.** Draw alternatives beside them:
  - a look: `tiles32-LOOKn.txt` and `tiles16-LOOKn.txt`, both, numbered from 2 with no gaps
    (`forest2`, `forest3`; `mountain2`);
  - a figure: a new entry in `figures.txt` named after the race or foe and a number
    (`HUMAN2`, `MOTH_FOLK2`, `ASH_RAT3`).
- A look's first eight tiles are the terrains, in the order of the table above.
- `python3 tools/art.py check` must say "all well"; `make test-art` must pass.
- The builds draw only the figure named exactly and the four looks the game uses, so
  alternatives cost nothing until we pick them.

## The work

In this order; a pull request each, with `artpreview` pictures of before and after.

1. **Figures:** a `2` for each of the twelve (`HUMAN`, `HOLLOWBORN`, `GLASSFOLK`,
   `RAD_DRYAD`, `CHRONOMITE`, `SALVAGED`, `MOTH_FOLK`, `STRANGER`; the foes `RUST_GUARD`,
   `SCRAP_GUNNER`, `ASH_RAT`, `MAINT_DRONE`). `HUMAN2` and `RUST_GUARD2` exist: take them
   further as `HUMAN3` and `RUST_GUARD3` if you can do better.
2. **forest3:** forest2 finished by hand: water with a lit rim and irregular edge, a
   thicket and thorns that read at 16 pixels, a third open variant.
3. **mountain2, town2, dungeon2** in the dark-floor style.
4. **More biomes** (swamp, ruins, ash plains...): ask first; a new look needs a place in
   the game.

## Checklist, every piece

- [ ] Seen with `artpreview` at 16-pixel squares (and 32 for tiles32).
- [ ] Floor: dark, textured, not flat, not noisy.
- [ ] Every object lit from the top left, black round it.
- [ ] The eight terrains told apart at a glance.
- [ ] Small marks in colours that read on black.
- [ ] Walls tile without a seam.
- [ ] Figures: facing right, slim, one-dot limbs, a mark of their own, no drawn outline.
- [ ] `python3 tools/art.py check` all well; originals untouched.
