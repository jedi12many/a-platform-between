# Walk the yard: the walking engine

*Plan B's first demo ([plan-b.md](plan-b.md), B1): a whole-screen floor scrolling smoothly
in eight directions at 50 frames a second on a stock PAL C64. Built (W1); the party,
foes and people as sprites (W2) and the HUD in the border (W3) come next.*

    make walk           build/walk.prg (a Kung Fu Flash 2 runs it), build/walk.d64 (LOAD"WALK",8 and RUN)
    make test-cart      ...and tests/walk/run_walk.py with it

It walks yard 48213's first floor, the explore prototype's ([rooms.md](rooms.md)): its nine
rooms side by side as one area of 48 x 24 squares, in the forest look
([art.md](art.md#looks)), each square dressed as the prototype dresses it. A joystick in
port 2 walks; the screen follows.

It's a program of its own (`cart/walk/`), not yet part of the cartridge's game: the
engine first, proven, then the game moves onto it.

## The pieces

| File | Job |
|---|---|
| `tools/walk/walk.py` | the reference: the floor's asset, and walking, the camera and the scroller, frame by frame |
| `cart/walk/start.s` | the start (a BASIC line, SYS 2061), the machine taken, the frame loop |
| `cart/walk/gen.s` | the scroller's copying code, written at the start |
| `cart/walk/irq.s` | the raster interrupt: a frame's registers, the swap, the colours |
| `cart/walk/move.s` | walking: the joystick, sliding, the corner nudge |
| `cart/walk/camera.s` | the camera, and the scroller's three stages |
| `cart/walk/edge.s` | the area's characters and colours, and drawing rows and columns of them |
| `cart/walk/floor.s` | the floor's asset, built in |
| `tests/walk/run_walk.py` | the harness: the program on an emulated C64, held to the reference |

## The rules

The prototype's, in whole numbers:

- **A position** is the top left of the leader's 16-pixel square, in sixteenths of a
  pixel (16 bits).
- **Walking**: 23 sixteenths a frame (1.44 pixels: the prototype's 4.5 squares a second),
  16 each way on a diagonal. Across first, then down, each a **slide**: if the body fits
  moved, it moves. If not, and the other axis is within 7 pixels of a square's edge
  where the body would fit, it steps toward that edge instead, by the step or the
  distance, whichever is less (the prototype's nudge round a corner).
- **The body** is pixels 3 to 12 of its square, both ways (the prototype's 0.3 of a square
  either side of the middle). It fits where every square under it can be stood on: not
  wall, pit or hazard, and no foe or person there.
- **The camera** is the area's pixel at the view's top left. Where the leader wants it:
  the leader's middle in the view's middle (152 across, 96 down), kept within 0-455 and
  0-191 (so the screen's 40 x 25 characters stay on the area). Each frame it moves an
  eighth of the way there, at least a pixel, at most two (the prototype eases at 6 a
  second: an eighth a frame, near enough).

## The screen

Multicolour characters, 38 columns and 24 rows shown (the VIC's narrower window hides the
fine scroll's edges), of a 40 x 25 screen. A square is 2 x 2 characters, the look's tile
drawn seamless: character 1 + 4 tile + 2 (lower) + 1 (right), colour RAM the tile's own.
The camera at pixel (x, y) shows the area's character (x / 8, y / 8) at the top left, with
the fine scroll at 7 - (x mod 8) and 7 - (y mod 8).

At the start, the area's characters and their colours are written out as two maps of 96
x 48 bytes (`CHAR_MAP` at $A000, `COLOUR_MAP` at $E000), so any row or column of the
screen is a straight copy.

## The scroller

Two screens in VIC bank 3 ($C000 and $C400): one shown, one made. The colour RAM can't be
doubled, so the colours are made in a **shadow** in RAM ($9800) and copied in at once.
When the camera's next step would cross into the next character (across, down or both),
the step takes three frames:

| Stage | The frame loop | The camera next frame |
|---|---|---|
| `IDLE` | the shown screen copied into the other, shifted a column, a row or both (`SHIFT_AB` or `SHIFT_BA`: 1,000 bytes unrolled, `LDA from+i-41,X` / `STA to+i`, X the shift + 41), and the new edges copied from the map | held in its cell (it stops at the edge) |
| `SHIFTED` | the shadow shifted the same way, in place (`SHADE_UP` first byte first for a step forward, `SHADE_DOWN` last first for back), its new edges copied | into the new cell; the interrupt swaps the screens and copies the shadow in |
| `COLOURED` | nothing heavy: the frame of the swap | held in its (new) cell |

So the camera is decided one frame ahead, waits at a cell's edge for one frame while the
screen is made, and can't make a step more than once in three frames (more than fast
enough: walking crosses a character every five or six). The copying code, 6,001 bytes a
block, five blocks, is written by `gen.s` at the start ($2000-$97FF), not carried in the
program.

## A frame

The raster interrupt comes at line 250, under the 24 rows. It counts the frame, and if the
frame loop finished the last one, shows what it decided: `$D016` and `$D011` (the fine
scroll), `$D018` (the screen), and on a step's swap, the shadow into the colour RAM, top
first (`BLAST`, about 8,200 cycles: past the top of the screen by the time the raster gets
there, line 51, and ahead of it all the way down). If the loop wasn't done, the frame is
**late**: nothing changes, and it's counted.

The frame loop wakes at each frame: it reads the joystick, walks, and moves the camera
(and does the scroller's work), then leaves its decision for the next interrupt.

## Measured

On the harness's model of the C64 (its bad lines taking 40 cycles each; no sprites yet),
over a walk of 1,467 frames (the script's knocks into walls and corners, then a walk
through the floor's doors to its stairs, 136 coarse steps):

| | Cycles |
|---|---|
| A PAL frame | 19,656 |
| Its 25 bad lines | 1,000 |
| The busiest frame loop (a shift and its edges) | 13,471 |
| The busiest interrupt (a swap and the colours) | 8,243 |
| Late frames | 0 |

The busiest loop and the busiest interrupt never share a frame (the interrupt's copy comes
in the swap's frame, whose loop rests), so the costliest frame has about 5,000 cycles to
spare: room for W2's sprites, which the harness will count too.

## Tested

`tests/walk/run_walk.py` runs the program on py65, with the C64's memory map, the
joystick and the raster played in Python:

- every frame's leader, camera and scroller stage are the reference's;
- every frame **as the VIC showed it** is right: each row of characters and colours is
  read at its own bad line, from the screen `$D018` points at then and the colour RAM as
  it is then, so a copy racing the raster, or a screen written while it's shown, would be
  caught; and compared with the area as the reference's camera sees it, every visible
  character and colour, and the fine scroll's registers;
- no frame is late, and the busiest loop and interrupt are reported;
- the walk reaches the stairs.

`--shot FRAME FILE.png` draws a frame as shown.

What the harness doesn't model yet: sprites' cycles (W2), and the VIC's exact cycle of a
bad line within its line; it wants checking in VICE's x64sc and on a real C64.

## The floor's asset

What `tools/walk/walk.py asset YARD FLOOR OUT` writes (`Floor.asset`), and the program has
built in (`floor.s`):

| Offset | Size | What |
|---|---|---|
| 0 | 3 | the look's background and two shared colours |
| 3 | 1 | how many tiles |
| 4 | 32 | each tile's colour RAM value |
| 36 | 2 | where you start: square x, y (the start room's (7, 3)) |
| 38 | 1,152 | the squares, 48 x 24, a row at a time: the tile (bits 0-4), and $80 if it can't be stood on |
| 1,190 | 8 + 32 a tile | the characters: 0 blank, then each tile's four |
