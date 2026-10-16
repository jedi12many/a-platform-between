# Walk the yard: the walking engine

*Plan B's first demo ([plan-b.md](plan-b.md), B1): a whole-screen floor scrolling smoothly
in eight directions at 50 frames a second on a stock PAL C64, the party, foes and people
on it as sprites. Built (W1, W2); the HUD in the border (W3) comes next.*

    make walk           build/walk.prg (a Kung Fu Flash 2 runs it), build/walk.d64 (LOAD"WALK",8 and RUN),
                        and build/walk-crowd.prg (yard 7602's eighth floor: a crowd to test the sprites)
    make test-cart      ...and tests/walk/run_walk.py on both

It walks yard 48213's first floor, the explore prototype's ([rooms.md](rooms.md)): its nine
rooms side by side as one area of 48 x 24 squares, in the forest look
([art.md](art.md#looks)), each square dressed as the prototype dresses it, its foes and
people standing where the prototype puts them. A joystick in port 2 walks the party; the
screen follows.

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
| `cart/walk/camera.s` | the camera, and the scroller's five stages |
| `cart/walk/figures.s` | the figures: the party's trail, who's in sight, the sprites shared out into a program |
| `cart/walk/mux.s` | the multiplexer: a program carried out, from the frame's start and at each event's line |
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
doubled, so the colours are made in a **shadow** in RAM ($B200) and copied in at once.
When the camera's next step would cross into the next character (across, down or both),
the step takes five frames, each frame's share small enough to leave room for the figures:

| Stage | The frame loop | The camera next frame |
|---|---|---|
| `IDLE` | the shown screen's first 500 bytes copied into the other, shifted a column, a row or both (`SHIFT_AB` or `SHIFT_BA`: unrolled, `LDA from+i-41,X` / `STA to+i`, X the shift + 41) | held in its cell (it stops at the edge) |
| `HALF` | its other 500, and the new edges copied from the map | held |
| `SHIFTED` | the shadow's first 500 shifted the same way, in place (`SHADE_UP` first byte first for a step forward, `SHADE_DOWN` last first for back) | held |
| `SHADED` | its other 500, and its new edges | into the new cell; the interrupt swaps the screens and copies the shadow in |
| `COLOURED` | nothing heavy: the frame of the swap | held in its (new) cell |

So the camera is decided one frame ahead, waits at a cell's edge while the screen is
made, and can't make a step more than once in five frames (enough: walking crosses a
character every five or six). The copying code, 6,002 bytes a block (each half ends in an
`RTS`, so a half is a call), five blocks, is written by `gen.s` at the start
($2800-$9F71), not carried in the program.

## A frame

The raster interrupt comes at line 250, under the 24 rows. It counts the frame, and if the
frame loop finished the last one, shows what it decided: `$D016` and `$D011` (the fine
scroll), `$D018` (the screen), and on a step's swap, the shadow into the colour RAM, top
first (`BLAST`, about 8,200 cycles: past the top of the screen by the time the raster gets
there, line 51, and ahead of it all the way down). If the loop wasn't done, the frame is
**late**: nothing changes, and it's counted.

The interrupt also sets the sprites from the program the loop made last frame (below), and
the frame's first event's interrupt; it lets those interrupts in (`CLI`) before the
colours' copy, so a reuse high on the screen isn't kept waiting behind it.

The frame loop wakes at each frame: it reads the joystick, walks, moves the camera (and
does the scroller's work), and makes the next frame's sprites, then leaves its decision
for the next interrupt.

## The figures

The party walks in marching order behind the leader, and the floor's foes and people
stand on their squares, each a multicolour sprite: the figure's battle art
([art.md](art.md)), drawn into a sprite by `walk.py` (its 16 x 16 pixels into the
sprite's top left, the outline in shared colour 1, black, and its own colour; and
mirrored, facing left). The floor's asset carries them (32 shapes at most: 2 for each of
up to 12 kinds), copied at the start to $D000, under the I/O, where the VIC sees them.

- **The trail**: each frame the leader's pixel moves, it goes on a trail of the last 32.
  Traveler k (0 the leader) stands 9 k entries back (about 13 pixels a traveler at a
  walk), and isn't drawn until the trail is that long. Each faces as their x last changed;
  each bobs up a pixel while ((frames moved + 4 k) & 8), if the leader moved this frame.
- **Foes and people** face the leader: left if the leader's x + 8 is less than theirs.
  The floor keeps them in order down the area, so only the rows in sight are looked at.
- **In sight**: a sprite's position is its square's pixel less the camera's, plus 27
  across and 47 down; it's in sight if it's within 8-334 across and 35-246 down (some of
  it inside the 38 x 24).
- **Sharing out the sprites**: those in sight, sorted down the screen (those level keep
  their order: the party first), each take the VIC sprite free soonest (the lowest
  numbered of those), if it's free by their top line. A sprite is free 23 lines below the
  top of the figure it last showed (its 21 lines and two to set it again). The first eight
  are set at the frame's start; each after reuses a sprite, an **event** at the line the
  figure before it on that sprite ends. A figure with no sprite free in time, or past 26
  events, is **left out** (counted, not drawn).

The loop writes this as a **program** (a page: the first eight sprites' x, y, pointer and
colour as the VIC has them, then the events, 8 bytes each: line, sprite, x, x's ninth bit,
y, pointer, colour; at the end which sprites are on, their ninth bits and how many events)
into one of two pages ($BE00, $BF00) while the interrupt carries out the other: shown from
the next frame. The interrupt (`mux.s`) sets the first eight from code unrolled for each
page, then raster interrupts at each event's line: each sets every event due by the next
line and asks for the next one's, or for line 250 again. Its loads have the shown page
patched in, so nothing is copied.


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
- every frame's sprites **as the VIC showed them** are the reference's: a sprite starts
  where its y register meets the raster, and is recorded then with its x, pointer and
  colour as they are, so an event set a line late, or a register written while its
  sprite shows, would be caught; and none left out where the reference draws it;
- every frame **as the VIC showed it** is right: each row of characters and colours is
  read at its own bad line, from the screen `$D018` points at then and the colour RAM as
  it is then, so a copy racing the raster, or a screen written while it's shown, would be
  caught; and compared with the area as the reference's camera sees it, every visible
  character and colour, and the fine scroll's registers;
- no frame is late, and the busiest loop and interrupt are reported;
- the walk reaches the stairs.

`--shot FRAME FILE.png` draws a frame as shown.

Its model of the VIC's time: a bad line takes 40 cycles, and each sprite showing on a
line 2 (on a real C64 the bus is also handed over a few cycles before the sprites'
fetches, and where in the line they fall matters; neither is modelled); it wants checking in VICE's x64sc and on a real C64.

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
| 1,190 | 4 | the party's kinds, in marching order |
| 1,194 | 1 + 12 | how many kinds of figure, then each one's sprite colour |
| 1,207 | 1 + 96 | how many foes and people (32 at most), then each one's square x, y and kind, in order down the area |
| 1,304 | 8 + 32 a tile | the characters: 0 blank, then each tile's four |
| 2,048 | 64 a shape | the sprite shapes: kind k's 2 k (facing right) and 2 k + 1 (left) |
