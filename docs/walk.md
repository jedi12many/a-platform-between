# Walk the yard: the walking engine

*Plan B's first demo ([plan-b.md](plan-b.md), B1): a whole-screen floor scrolling smoothly
in eight directions at 50 frames a second on a stock PAL C64, the party, foes and people
on it as sprites, and the party's portraits and health in the opened bottom border; and
open floors of any size up to 80 x 48 squares ([open-floors.md](open-floors.md)). Built
(W1, W2, W3, W4).*

    make walk           build/walk.prg (a Kung Fu Flash 2 runs it), build/walk.d64 (LOAD"WALK",8 and RUN),
                        build/walk-crowd.prg (yard 7602's eighth floor: a crowd to test the sprites),
                        and build/walk-open.prg (yard 48213's sixth floor as an open floor: 80 x 40)
    make test-cart      ...and tests/walk/run_walk.py and tests/walk/vice_walk.py on all three

It walks yard 48213's first floor, the explore prototype's ([rooms.md](rooms.md)): its nine
rooms side by side as one area of 48 x 24 squares, in the forest look
([art.md](art.md#looks)), each square dressed as the prototype dresses it, its foes and
people standing where the prototype puts them. Or an open floor
([open-floors.md](open-floors.md)), as `buildOpen` builds it and the prototype dresses it,
its bands' foes and its people standing where they stand (`walk.py asset YARD FLOOR DIR
open`). A joystick in port 2 walks the party; the screen follows.

It's a program of its own (`cart/walk/`), not yet part of the cartridge's game: the
engine first, proven, then the game moves onto it.

## The pieces

| File | Job |
|---|---|
| `tools/walk/walk.py` | the reference: the floor's asset, and walking, the camera and the scroller, frame by frame |
| `cart/walk/start.s` | the start (a BASIC line, SYS 2061), the machine taken, the frame loop |
| `cart/walk/gen.s` | the scroller's copying code, written at the start |
| `cart/walk/colours.s` | a step's colours: the colour RAM's rows from the colour map, as the raster passes them |
| `cart/walk/irq.s`, `irq.inc` | the raster interrupt's way in (a `JMP` each handler points at the next) and out |
| `cart/walk/border.s` | the border opened: the bands above and below the view, the frame begun (a frame's registers, the swap, the colours), the HUD |
| `cart/walk/move.s` | walking: the joystick, sliding, the corner nudge |
| `cart/walk/camera.s` | the camera, and the scroller's five stages |
| `cart/walk/figures.s` | the figures: the party's trail, who's in sight, the sprites shared out into a program |
| `cart/walk/mux.s` | the multiplexer: a program carried out, its first eight after the HUD and each event at its line |
| `cart/walk/edge.s` | the floor on its pages (its colours and squares), and drawing rows and columns of characters from the squares |
| `cart/walk/floor.s` | the floor's asset and its squares, built in |
| `tests/walk/run_walk.py` | the harness: the program on an emulated C64, held to the reference |
| `tests/walk/vice_walk.py`, `vice.py` | the program on x64sc, VICE's cycle-exact C64, its pictures held to the harness's, pixel for pixel |

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
  the leader's middle in the view's middle (152 across, 96 down), kept within 0 and
  (2 w - 40) x 8 + 7 across, (2 h - 25) x 8 + 7 down, for a floor of w x h squares (so the
  screen's 40 x 25 characters stay on the area: 0-455 and 0-191 for 48 x 24). Each frame it moves an
  eighth of the way there, at least a pixel, at most two (the prototype eases at 6 a
  second: an eighth a frame, near enough).

## The screen

Multicolour characters, 38 columns and 24 rows shown (lines 55-246: the fine scroll's
edges hidden, by the side borders and by the black bands above and below: see "The
border"), of a 40 x 25 screen. A square is 2 x 2 characters, the look's tile
drawn seamless: character 1 + 4 tile + 2 (lower) + 1 (right), colour RAM the tile's own.
The camera at pixel (x, y) shows the area's character (x / 8, y / 8) at the top left, with
the fine scroll at 7 - (x mod 8) and 7 - (y mod 8).

At the start, the floor is laid out a page for each row of squares (`COLOUR_MAP` from
$7C00): the row's colours from the page's start, a byte a column of characters (a
square's two columns and two rows share its colour), so a row of the colour RAM is a
straight copy; then, from 2 w, the squares themselves, a byte each (its tile, and whether
it can be stood on). So a floor can be up to 80 squares wide (3 x 80 <= 256) and 48 deep
(to $ABFF). The characters aren't kept: a new edge's are worked out from its squares as
it's drawn (1 + 4 tile + 2 lower + 1 right), a row's two at a time and a column's a square
at a time, about as fast as copying them was.

## The scroller

Two screens in VIC bank 3 ($C000 and $C400): one shown, one made. When the camera's next
step would cross into the next character (across, down or both), the step takes five
frames, each frame's share small enough to leave room for the figures:

| Stage | The frame loop | The camera next frame |
|---|---|---|
| `IDLE` | the shown screen's first 500 bytes copied into the other, shifted a column, a row or both (`SHIFT_AB` or `SHIFT_BA`: unrolled, `LDA from+i-41,X` / `STA to+i`, X the shift + 41) | held in its cell (it stops at the edge) |
| `HALF` | its other 500 | held |
| `SHIFTED` | the new edges, worked out from the squares; the colours' copies aimed at the rows to be shown (those whose row of squares changed) | held |
| `SHADED` | nothing heavy; then, done, each row's colours copied as the raster passes it | into the new cell; the interrupt swaps the screens and copies the rows not done |
| `COLOURED` | nothing heavy: the frame of the swap | held in its (new) cell |

So the camera is decided one frame ahead, waits at a cell's edge while the screen is
made, and can't make a step more than once in five frames (enough: walking crosses a
character every five or six).

**The colours.** The colour RAM can't be doubled: the new colours must land in each row
between the VIC reading it for the last frame of the old screen (at the row's bad line)
and for the first of the new. So each row's colours are copied straight from the colour
map (`COLOUR_ROWS`: a row a call, `LDA map+c,Y` / `STA COLOUR_RAM+40r+c`, Y the screen's
first column on the area, 8 cycles a byte), its page aimed in the `SHIFTED` frame at the
row of squares it'll show (`AIM_ROWS`: each row's 40 high bytes written), if that's
changed: after a step across none has, after a step down or up every other row. In the
frame before the swap, the loop, done, copies each row as soon as the raster is past its
bad line (from row 0, till line 243); the swap's interrupt copies the rest, top first,
ahead of the raster. Both copy from the map, so a row the swap catches half copied is
copied again the same. On the crowd floor the loop gets 15-23 rows done first; on the
open floor 11-23; on the first floor, all but one or two. (So that frame is kept light:
work moved into it starves the copy, and the swap's interrupt, copying the rest, runs
into the next frame.)

The copying code is written by `gen.s` at the start (`SHIFT_AB` $2800, `SHIFT_BA` $4000:
6,002 bytes each, an `RTS` half way, so a half is a call; `COLOUR_ROWS` $5800, 25 x 241
bytes; `AIM_ROWS` $7000, 25 x 121), not carried in the program.

## A frame

A frame's raster interrupts, in order (`border.s`, `mux.s`):

| Line | Interrupt | What |
|---|---|---|
| 244 (243) | bottom | the band under the view begun (see "The border"); the frame counted, and if the frame loop finished the last one, what it decided shown: `$D016` and `$D011` (the fine scroll), `$D018` (the screen), its sprites' program; the HUD's sprites set; and on a step's swap, the other interrupts let in, the colours' rows the loop didn't copy (see "The scroller") |
| 264 | HUD | the HUD's sprites' pointers, written in line 266: it shows on 268-288; the band at 25 rows (the border's top compare) |
| 1 | world | the program's first eight sprites: their Ys first, by line 11 (the HUD's Y) |
| 52 | top | the band above the view ended: the pointers of the figures crossing its top, then the view on at 55 |
| events | the sprites reused down the screen, each at its line (by 238) |

If the loop wasn't done when the bottom came, the frame is **late**: nothing changes, and
it's counted. The frame loop wakes at each frame: it reads the joystick, walks, moves the
camera (and does the scroller's work), and makes the next frame's sprites, then leaves its
decision for the next bottom.

## The border

The VIC shuts its border when the raster meets the bottom compare (line 247 at 24 rows,
251 at 25) and opens it at the top compare (51 at 25 rows, 55 at 24) if the screen's on.
The engine is at 25 rows (RSEL) at 247 and at 24 at 251, so it never shuts: the border's
open above and below the screen, and sprites show there; at 25 again by 51, so it opens
once and for all. Only the side borders stay shut (opening those takes the whole CPU).

Then the view is kept to lines 55-246, as the 24 rows would have it, by blacking out the
rest: an invalid mode (ECM with multicolour), every pixel black, from line 247 to 54. Its
switch must fall between two lines' pixels: line 246's last (cycle 55) and 247's first
(17), and 54's and 55's. The interrupt comes two lines early (getting in takes some 80
cycles), waits for the line by polling the raster, and writes at a counted cycle. The
VIC stops the CPU on a bad line (cycles 12-54) and for each sprite's fetch (from 3 cycles
before it: 58-63 for sprites 0-2, the next line's 1-10 for 3-7), and the fine scroll
decides which lines are bad, so each edge has three ways:

- **Fine scroll 0-5** (and 7 at the top): the write is timed for the gap (line 246's
  cycle 59-65); if a sprite's fetch stops the CPU in it, the write comes out after the
  stop, by the next line's cycle 14.
- **Fine scroll 6**: the line before the edge is bad (row 24's first, or row 0's): the
  write is started before the bad line stops the CPU, and lands just after it, in the gap.
- **Fine scroll 7** at the bottom: line 247 would be bad (row 24's first): the fine scroll
  is made 5 in line 246 so it isn't, and the VIC idles from 247, showing the byte at
  $FFFF: the interrupt's vector's high byte, made $FF (the vector's a `JMP` at $FF00), so
  black.

The figures' sprites crossing an edge are hidden in the bands by giving them an empty
shape: their pointers written between the VIC's fetch of them for the edge's last line and
its first (at the bottom all eight, empty; at the top those crossing, their own, from slots
the world interrupt fills). With fine scroll 6 those writes fall a line off: figures
crossing the top come in a line late (56), and the view's last line (246) shows none.

**The limit**: when a figure crosses an edge, the VIC stops the CPU for its fetch, and if
that stop lands in the instruction before the edge's write, the write comes out a few
cycles late: up to 6 pixels at the left of the band's first line (or the view's) stay as
they were, in that frame; with an open floor's crowd crossing the bottom edge at once
(several figures' fetches in a row), up to 32 (4 characters). The VICE check counts these
(in about 1 picture in 20 on the first floor, and 4 of 277 on the open floor); a sync to
the cycle would remove them.

## The HUD

The party's portraits and health along the bottom border, lines 268-288: all eight
sprites, after every figure's sprite has ended (a figure's sprite starts by line 245, so
it's done by 266; its pointer is empty from 247). Traveler k's portrait is sprite 2 k (their
kind's shape facing right, multicolour) at X 39 + 80 k, and their health sprite 2 k + 1
(hires, light green) beside it: the number (29/29: health is 10 + Grit / 4 + 2 a level,
the explore prototype's travelers at level 1), a bar, and the class's first three
letters, in a 3 x 5 font. The floor's asset carries the four health shapes (24-27) and
the HUD's sprites' places and colours (`walk.py`'s `hud`); the bottom interrupt sets
them, and the HUD's pointers come in line 266. The world interrupt, after the HUD's last
line, sets the world's sprites again.

## The figures

The party walks in marching order behind the leader, and the floor's foes and people
stand on their squares, each a multicolour sprite: the figure's battle art
([art.md](art.md)), drawn into a sprite by `walk.py` (its 16 x 16 pixels into the
sprite's top left, the outline in shared colour 1, black, and its own colour; and
mirrored, facing left). The floor's asset carries them (32 shapes at most: 2 for each of
up to 12 kinds), copied at the start to $D000, under the I/O, where the VIC sees them. A
floor has up to 80 foes and people.

- **The trail**: each frame the leader's pixel moves, it goes on a trail of the last 32.
  Traveler k (0 the leader) stands 9 k entries back (about 13 pixels a traveler at a
  walk), and isn't drawn until the trail is that long. Each faces as their x last changed;
  each bobs up a pixel while ((frames moved + 4 k) & 8), if the leader moved this frame.
- **Foes and people** face the leader: left if the leader's x + 8 is less than theirs.
  The floor keeps them in order down the area, so only the rows in sight are looked at.
- **In sight**: a sprite's position is its square's pixel less the camera's, plus 27
  across and 47 down; it's in sight if it's within 8-334 across and 35-245 down (some of
  it inside the 38 x 24; the VIC shows a sprite from the line after its Y).
- **Sharing out the sprites**: those in sight, sorted down the screen (those level keep
  their order: the party first), each take the next VIC sprite in turn (0 to 7, then
  round again), if it's free by their top line. A sprite is free 23 lines below the top of
  the figure it last showed (its 21 lines and two to set it again); since the figures come
  in order down, the next in turn is always one free soonest. The first eight
  are set at the frame's start; each after reuses a sprite, an **event** at the line the
  figure before it on that sprite ends. A figure with no sprite free in time, past 26
  events, or whose event would come after line 238 (the bottom's interrupt is next), is
  **left out** (counted, not drawn), and the turn stays.

The loop writes this as a **program** (a page: the first eight sprites' x, y, pointer and
colour as the VIC has them, then the events, 8 bytes each: line, sprite, x, x's ninth bit,
y, pointer, colour; at the end which sprites are on, their ninth bits and how many events)
into one of two pages ($BE00, $BF00) while the interrupt carries out the other: shown from
the next frame. The world interrupt (`mux.s`) sets the first eight from code unrolled for
each page, then raster interrupts at each event's line: each sets every event due by the
next line and asks for the next one's, or for the bottom's. The code that writes a program,
and the events' interrupt that reads one, each have a copy for either page, so nothing is
copied or patched.

The sort is cheap because the floor's figures come in order down: the party's (four at
most) are sorted, then merged with them. And a figure is in sight without its pixels
being looked at when its square is inside the window's edge squares.


## Measured

On the harness's model of the C64 (its bad lines taking 40 cycles each, each sprite
showing on a line 2), over three walks: yard 48213's first floor (1,467 frames: the
script's knocks into walls and corners, then through the floor's doors to its stairs, 136
coarse steps), yard 7602's eighth, the crowd (1,726 frames, 215 coarse steps), and yard
48213's sixth as an open floor, 80 x 40 (1,941 frames, 183 coarse steps, to its stairs past
the band guarding them):

| | The first floor | The crowd | The open floor |
|---|---|---|---|
| A PAL frame | 19,656 | 19,656 | 19,656 |
| Its 25 bad lines | 1,000 | 1,000 | 1,000 |
| Sprites shown | 7,589, up to 7 a frame | 16,034, up to 14 a frame | 14,898, up to 16 a frame |
| Left out | 0 | 42 | 30 |
| The busiest frame loop | 12,771 | 16,283 | 17,098 |
| The latest a frame loop's done (the bottom's at 244) | line 143 | line 200 | line 226 |
| Colour rows copied in the frame before a swap (of 25) | 23-24 | 15-23 | 11-23 |
| The busiest interrupt (the colours' copy apart) | 1,356 | 1,302 | 1,329 |
| Late frames | 0 | 0 | 0 |

The tightest frames are a step's first two, each shifting half a screen (4,000 cycles of
copying) beside the figures. The swap's frame was the tightest while the colours went
through a shadow (shifted in place over two frames, then all copied in at the swap: 16,000
cycles a step, 8,000 of them in the swap's interrupt); now they're 8,000 cycles of copying
straight from the map, most of it in the frame before the swap, behind the raster, and
4,000 aiming the copies in the `SHIFTED` frame, which has nothing else heavy.

## Tested

`tests/walk/run_walk.py` runs the program on py65, with the C64's memory map, the
joystick and the raster played in Python:

- every frame's leader, camera and scroller stage are the reference's;
- every frame's sprites **as the VIC showed them** are the reference's: a sprite starts
  where its y register meets the raster's low byte and shows from the next line, and is
  recorded at its first line in the view with a shape, with its x, pointer and colour then,
  so an event set a line late, or a register written while its sprite shows, would be
  caught; and none left out where the reference draws it;
- every frame's HUD is the asset's: its eight sprites from line 267;
- every frame **as the VIC showed it** is right: each row of characters and colours is
  read at its own bad line, from the screen `$D018` points at then and the colour RAM as
  it is then, so a copy racing the raster, or a screen written while it's shown, would be
  caught; and compared with the area as the reference's camera sees it, every visible
  character and colour, and the fine scroll's registers;
- no frame is late, and the busiest loop and interrupt are reported;
- the walk reaches the stairs.

`--shot FRAME FILE.png` draws a frame as shown.

Its model of the VIC's time is a line's: a bad line takes 40 cycles from its cycle 12, and
each sprite showing 2 of the line before's from its 55, and the unused bits of the VIC's
registers read as 1s. So `tests/walk/vice_walk.py` runs the program on **x64sc**, VICE's
cycle-exact C64 (with stand-in ROMs: the program takes the machine; driven through its
remote monitor, the joystick's script in RAM at $0200), stops it at the world interrupt
every few frames, and compares its whole picture, borders and all, with the picture as
it's meant to be, drawn from the harness's snapshot of each line: the view as the rows were
read, the figures in their shapes only in the view, the bands black, the HUD. It found what
the harness can't: the VIC showing a sprite from the line after its Y, `$D018`'s unused
bit reading as 1, the top compare needing 25 rows at line 51, and a sprite started again
at the HUD's Y (11) in the next frame's top border when the world interrupt set its Y
after line 11. `make test-cart` runs it on both floors, every seventh frame. Without x64sc (`apt-get
install vice`, and `xvfb-run`) it says so and passes. It wants checking on a real C64 too.

## The floor's asset

What `tools/walk/walk.py asset YARD FLOOR DIR [open]` writes (`Floor.asset`, `floor.bin`;
and the squares, `squares.bin`), and the program has built in (`floor.s`):

| Offset | Size | What |
|---|---|---|
| 0 | 3 | the look's background and two shared colours |
| 3 | 1 | how many tiles |
| 4 | 32 | each tile's colour RAM value |
| 36 | 2 | where you start: square x, y (the start room's (7, 3), or an open floor's start) |
| 38 | 2 | the floor's width and height, in squares (up to 80 x 48) |
| 40 | 4 | the party's kinds, in marching order |
| 44 | 1 + 12 | how many kinds of figure, then each one's sprite colour |
| 57 | 1 + 240 | how many foes and people (80 at most), then each one's square x, y and kind, in order down the area |
| 304 | 8 + 32 a tile | the characters: 0 blank, then each tile's four |
| 2,000 | 18 | the HUD's sprites: their X's low bytes (8), colours (8), X's ninth bits, which are multicolour |
| 2,048 | 64 a shape | the sprite shapes: kind k's 2 k (facing right) and 2 k + 1 (left); 24-27 the HUD's health (31, empty, is made at the start) |

`squares.bin` is the squares, w x h, a row at a time: the tile (bits 0-4), and $80 if it
can't be stood on. It's loaded past $27FF, with the interrupts' code, and laid out on its
pages (`maps_build`) before `gen.s` writes the copying code there.
