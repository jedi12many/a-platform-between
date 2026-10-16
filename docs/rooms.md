# Rooms

*Milestone E13, a design and a prototype. The prototype is in the studio's arena
([arena.md](arena.md)): "Explore the yards". The game itself still explores by scenes and
menus ([engine-plan.md](engine-plan.md)).*

Between fights, the party walks. A **room** is a square grid seen from overhead, the same
grid as the battle map: the same 16-pixel squares on the cartridge, the same tiles, the
same figures. A fight starts where you stand, on the room's own map. Leaving a room by a
door draws the next one in its place: **flip-screen**, one room to a screen, as the first
*Zelda* did, rather than a world that scrolls.

## Why overhead, and why flip-screen

- **One grid for everything.** Walking, looking about and fighting all happen on the map
  the battle engine already plays. Nothing changes screen when a fight begins, and a room
  can be copied onto squared paper and played at a table ([tabletop.md](tabletop.md)).
- **It suits the C64.** Square tiles are 2 x 2 characters, so a room is drawn by writing
  its tiles' characters into the view: 512 bytes of screen and 512 of colour, about as
  long as a frame. An isometric view's diamond tiles don't fit the 8 x 8 character grid:
  it means bitmap mode, figures sorted by depth, and moves that run diagonally across the
  screen, which is twice the art and the drawing code for a look the grid rules don't need.
- **Flip-screen is cheap, and it's the unit an author thinks in.** A room fits the screen,
  so nothing scrolls; a room is a fight-sized place; and a Departure's author writes rooms
  as they write battle maps today. Scrolling (for wide outdoor places) can come later.

## A room

- **Size: 16 x 8 squares**, walls round the edge: 14 x 6 to walk in. That's the largest map
  the battle engine takes (16 across) and the cartridge's view shows (8 down). The view is
  20 squares across, so a room leaves 4 squares (8 columns) at the side, for the floor's
  map.
- **Tiles:** the battle map's eight: open, wall, pit, rough, cover, hazard, high ground,
  and the **door** (the exit tile: in a fight, fleeing through a door takes you back the way
  you came). The **stairs** down, a **cache** and the room's **foes** stand on top.
- **What's in it:** nothing, a fight (its foes are in view as you come in), a cache (step on
  it to take what's in it), or the stairs (always guarded).

## Exploring

- **Walking is free, and smooth.** With no foes in the room you walk while a key (or the
  joystick) is held, 8 ways, about 4½ squares a second, gliding between squares; or click a
  square to walk there. No turns, no Speed. Your footprint (just over half a square) slides
  along walls, and is nudged round a corner into a doorway, so you needn't line up. Out of
  a fight you don't walk into a pit or a hazard: you go round (the floor is built so you
  always can). Rough ground and cover are just ground.
- **No grid while you walk.** The room is drawn without the tiles' seams; you're "on" the
  square under your middle, and that's where a door, a crate or the stairs take you.
- **Doors.** Step onto a door and you're in the next room, one square inside its matching
  door.
- **Coming into a room with foes in it starts a fight**, at once, on that room's map: you
  where you came in, the foes where they stand. Everyone settles onto their squares and
  **the grid comes up** (over half a second): the fight is on squares again. It's the battle engine's ordinary fight:
  rules v1 ([turn.md](turn.md)), every action, power and condition.
  - **Won:** the room is clear for good, and you're where the fight left you, at full health
    (*After a fight*, [turn.md](turn.md#after-a-fight)).
  - **Fled** through a door: you're back in the room you came from; the foes stay, healed.
  - **Lost:** the descent ends.
- **A cache** gives its item into your pack, for the next fight (swapping is free).
- **The stairs** take you down a floor, once its room is clear: a new floor, from the same
  yard, harder.
- **The floor's map** shows the rooms you've seen, the doors between them, and where you
  are.

## The party

Up to four travelers (E14) walk as **one party behind a leader**, as the Gold Box games and
*Ultima* had it; the explore brief picks them, in **marching order** (the first leads).

- **Following.** Out of fights you steer the leader; the others walk the leader's own trail,
  each 0.85 of a square behind the one before, so they go where the leader went: round
  pillars, through doorways, never through a wall. They come out from behind the leader as
  the trail grows, after a door or a fight.
- **Fanning out.** When a fight starts, the leader is where they are (one square in off the
  doorway), and the others, in marching order, take the nearest squares to the leader,
  found breadth-first from the leader's square, looking N, E, S, W, NE, SE, SW, NW: open
  ground, rough, cover or high ground with no foe on it, never a door, a wall, a pit or a
  hazard. The same room and the same leader's square always give the same places, on
  every machine (`fan_out` in `tools/rooms/rooms.py`; the page's agrees, in
  `tests/rooms/check_rooms.py`). Then everyone takes their own turns.
- **After a fight** won, everyone's up again at full health (*After a fight*), and the
  party gathers on the leader, who walks on from where they stood.
- **Gear** from crates goes into the party's pack.

### Playing together

Co-op sends choices, never state ([engine-plan.md](engine-plan.md#how-the-network-works)),
so walking needs a rule: **walking is presentation; destinations are choices.**

- Nothing you do while walking changes the game until the party **arrives** somewhere
  that matters: through a door, onto a crate or the stairs, into a room with foes. Those
  arrivals are what goes into the choice stream ("the party goes through room 2's east
  door"), and what saves and tests record; how the leader walked there is animation.
- **The leader walks**; the others see the walk sent a few times a second, smoothed, and
  never trusted by the rules (if it's late or lost, the party just turns up at the next
  arrival). Anyone can **suggest** a place (a marker on a door or a crate); the party can
  vote on a "go here" as on any story choice ([party-play.md](party-play.md)).
- **Played slowly** (a turn a day), walking becomes "go to": a click on a door, a crate or
  the stairs is the turn.
- **No one walks alone.** Every player walking their own figure would mean four views (four
  cameras, scrolling), a race for who steps into a room first, and positions the rules
  would have to trust. Splitting the party, if ever, is a story's choice.
- **On a real C64** it's one player and their own four, offline (E14), with the same
  marching order and fan-out.

## Scrolling, to compare

*A prototype beside flip-screen, to feel the two; nothing's decided.* The explore brief's
**View** (or V while walking) chooses; a link: `arena/#explore=48213:rogue:scroll`.

- **One area.** The floor's nine rooms side by side, 48 x 24 squares, the same rooms as
  flip-screen builds; where two rooms' doors meet, the doorway is a short passage of two
  door squares through a double wall. You walk straight through: nothing redraws.
- **The view** is 16 x 8 squares, a fight's size, and follows you: it eases toward you in
  the middle (kept inside the area), stepping a sixteenth of a square at a time, a C64
  pixel, as its fine scroll would. You see into the next room before you're in it, foes
  and all. **Z** zooms out: 24 x 12, then the whole floor (48 x 24), then back. The page
  scales the view to fit, so zoomed out the squares are drawn smaller (not on whole
  pixels: the whole floor is a map to look at, 24 x 12 the one to walk with). The C64's
  walking engine shows 19 x 12 of its 16-pixel squares ([walk.md](walk.md)), near the
  middle zoom.
- **The minimap** (the side panel, in place of the rooms' grid): the whole floor, four
  pixels a square, black but where the party has been within 6 squares (the fog, cleared
  by distance, not by room, and kept for the floor); the stairs, crates and foes seen; a
  rectangle for the view, whatever its zoom; a dot for the party.
- **A fight** is still the room's: crossing into a room with foes in it, the view settles
  on the room (squarely, as flip-screen shows it) while you step in off the doorway, and
  then the fight begins there, as before. So the two views differ only in how you get
  about, which is what's being compared. (A fight cut from the 16 x 8 round you, wherever
  you stand, is the next step if scrolling wins: then a doorway inside the window isn't an
  exit, and the window's edges are.)
- **On the C64** (from *Still open*, below): sideways is the scroll register set above our
  split; up and down moves the bad lines the split is timed against, so the split's code
  and its timing tests would be reworked; colour RAM can't be double-buffered, so the
  tiles would share its colour, or 640 bytes of it would move each character's scroll.

## A floor, from a yard

A floor is made from a **yard** (a number 0..65535, as the Deep Yards' [deep-yards.md](deep-yards.md))
and its **floor** number (1..255), so the same yard and floor are the same rooms on every
machine, and can be shared. Saves keep only the yard, the floor, the room you're in and
what's been cleared and taken; the rooms are built again.

The numbers come from `xs` and `mix`, as the Deep Yards have them. A generator draws
numbers `r()` from a xorshift16 whose state starts at `mix(yard XOR 0x5A5A, floor × 256 + 255)`;
each `r()` is one `xs` step, returning the new state; "r() mod n" is that 16-bit number mod n.
Rooms are numbered `i = 3 × cy + cx`, in a grid of 3 x 3 (cx and cy 0..2); the directions
are tried in the order **N, E, S, W**.

1. **The start.** Room (0, `r() mod 3`), on the west side.
2. **The doors (a maze).** From the start, a depth-first walk: look at the room on top of
   the stack; list its neighbours not yet reached, in the order N, E, S, W; if there are
   none, take it off the stack; otherwise open a door to the one at `r() mod (how many)`,
   and put it on the stack. Every room is reached, by exactly one way.
3. **Two more doors**, so there's a loop or two: twice, `i = r() mod 9`, `d = r() mod 4`;
   if room `i` has a neighbour that way and no door to it, open one.
4. **Depth.** Each room's distance from the start, through doors (breadth-first, N, E, S,
   W). The **stairs** are in the deepest room; of two as deep, the lower `i`.
5. **Where the doors are.** For each room in order of `i`: a door east has its row
   `1 + r() mod 6` (at x 15 in this room and x 0 in the next); then a door south has its
   column `1 + r() mod 14` (at y 7 in this room and y 0 in the next).
6. **Each room**, in order of `i`:
   1. **The shell:** walls round the edge, open ground inside, the doors (tile 7).
   2. **The stairs**, in the stairs room: at (7, 3).
   3. **Terrain:** `3 + r() mod 4 + min(depth, 3)` times, `x = 2 + r() mod 12`,
      `y = 2 + r() mod 4`, `t = r() mod 8`, in that order. If (x, y) isn't open ground,
      or is the stairs, place nothing. Otherwise put tile `[3, 3, 4, 4, 6, 2, 1, 5][t]`:
      rough, rough, cover, cover, high ground, pit, wall, hazard. Then flood from the
      room's first door (N, E, S, W) through squares that aren't wall, pit or hazard, one
      step in any of the 8 directions: if a door or the stairs can't be reached, take the tile
      away again. (The squares next to the walls are never built on, so the doors always
      join up; the stairs are what this protects.)
   4. **What's in it.** The start room: nothing. The stairs room: a fight. Any other:
      `k = r() mod 6`: 0-2 a fight, 3 a cache, 4-5 nothing.
   5. **A fight's foes.** The room's **danger** is `g = floor + depth / 2`; it has
      `n = min(4, 1 + g / 3)` foes, one more in the stairs room (at most 4), each in turn:
      - **Kind:** `r() mod L` of the pool **ash rat, scrap gunner, rust-guard, maintenance
        drone**, where `L = min(4, 1 + g / 2)`: deeper reaches further down it. A foe's
        level is the floor.
      - **Square:** up to 32 tries of `x = 2 + r() mod 12`, `y = 1 + r() mod 6`, taking the
        first that's open, rough, cover or high ground (0, 3, 4, 6), can be reached (the
        flood above), isn't the stairs, has no foe on it, and is 3 squares or more from
        every door. If all 32 miss, the first such square (nearness to doors aside)
        scanning y from 1 to 6, and x from 2 to 13 within each y.
   6. **A cache's item:** `r() mod 5` of **iron sword, arc pistol, chain coat, pulse rifle,
      ballistic weave**, on a square found as a foe's is (nearness to doors aside).

`tools/rooms/rooms.py` is a reference written from this page, and the prototype's
generator (`tools/arena/web/rooms.js`) must build the same floors from the same yards
(`tests/rooms/check_rooms.py`, on a thousand floors), with every door, the stairs and
every foe reachable.

## People

Besides foes, a floor has people, placed after its rooms are built and without their dice
(`people` in `tools/rooms/rooms.py` and `rooms.js`), so the same yard and floor have the
same people:

- **Vell's camp**, on every floor: in the empty room nearest the start (least depth, then
  lowest number), or the start room if none is empty. She trades.
- **Pell**, a lost courier, on floors 2 and 3: in the deepest empty room that isn't Vell's
  (deepest, then lowest number), or failing that the deepest crate room; none if neither.
- **Foes who talk first**: a fight room (never the stairs') parleys when
  `mix(yard XOR 0x7A1C, floor * 16 + room) mod 3 = 0`, about a third of them. The first
  foe in the room speaks for the rest.

Someone stands on the open square nearest (8, 3), counting 8 ways (then the topmost, then
the leftmost): reachable from the room's first door; not a door, the stairs, a foe's or the
crate's square, or (7, 3), where you arrive; and never in the way, so that with them
standing there every door, the stairs, the crate and every foe can still be reached. They
block the square they stand on, as a wall does while you walk.

## Talk

What people say is a Departure in Quest Script, `content/sidings/yards-talk/yards-talk.qs`,
played by the game's own story VM, compiled to WebAssembly for the page
(`tools/arena/web/story.c`, `build/arena-web/story.js`). One story VM, one language: what a
playtester reads is what the game will do, checks rolled by the rules for the party's
leader (rules v0, as the VM is until v1 is ported), items given and taken, and the story's
flags kept for the whole descent.

The page boards the leader at the top of a descent, and the Departure doesn't end while
you're down there. Between conversations it **waits at a menu for the page**: a menu
whose every label starts with `@` is never shown. The page answers it:

1. `wait`: `@1`...`@8`, the floor (8 for any deeper), which sets the story's `floor`; or
   `@end`, when a new descent begins and this one's story should end.
2. `who`: `@trader`, `@courier`, or a foe's registry name (`@ASH_RAT`) for a parley.

The conversation is then the player's: its text, checks (shown as rolled) and menus come
up in a panel over the room; a number or a click answers. When it's done it goes back to
`wait`, and the page walks again. On the way, a menu of one `@` label is a **signal** to
the page, which answers it at once and acts when the talk ends:

| Signal | The page |
|---|---|
| `@fight` | starts the room's fight |
| `@leave` | clears the room: the foes go, without a fight |
| `@join` | Pell follows the party, behind the last of it, floor to floor |
| `@gone` | Pell leaves the room for good |
| `@stay` | Pell stays at Vell's camp (and stops following) |

Before each talk the page writes the party's pack into the story's copy of the leader
(what they hold and wear stays out of it), so `has` and `~ take` see the pack; after it,
what the story gave or took is the pack. A parley offers what Quest Script asks of a
roadblock: a way to learn more, answers gated on what you carry or know, a check, and
always the fight. What happened to Pell comes back: Vell takes them in if you bring them,
leaves you a gift if you showed them the way, and won't trade if you robbed them (unless
you talk her round).

This is the prototype's convention, not yet the language's: when rooms come to the game,
talking to someone in a room wants a proper way into a scene and back (the "tunnel" scenes
Quest Script plans), and party play wants checks for whoever's talking.

## Looks

A floor is drawn in a **look** ([art.md](art.md#looks)): the forest, the mountains, a town or
a dungeon, the same terrain redrawn as that place. The look decides nothing: a wall is a
wall in a wood or a cellar. In the prototype the floors go forest, mountain, town, dungeon
and round again as you go down, or the brief's **The look** picks one for every floor
(`#explore=YARD:CLASS:look=town`); a Departure or a Siding would name its own.

Each square's tile is picked by a hash of where it is, so a room looks the same every time
it's drawn, in a fight too, and two players see the same room:

    n = ((floor * 9 + room) * 8 + y) * 16 + x
    h = top byte of ((n XOR (yard << 4)) * 0x9E3779B1), 32 bits      (0-255)

- **Scenery** on open ground with no foe, stairs or crate on it, when `h < 16` (one square
  in sixteen): the look's scenery tile `h mod` their number.
- Otherwise a **variant** of the square's terrain (`open2`, `open3`) when the look has any
  and `h mod 8 = 0`: variant `(h / 8) mod` their number; else the terrain's own tile.

Scenery is drawn, not stood on differently: you walk through mushrooms, and a fight on
them is a fight on open ground. Things that block are terrain (cover, wall).

## On the C64 (later)

- **Memory:** a room is 128 tiles (64 bytes, two to a byte); a floor's nine are built again
  from the yard whenever they're needed, so only what's cleared and taken is kept (a
  byte a room).
- **Drawing:** the view's 32 columns of the room, the floor's map in the 8 to its right
  (a character a room); the figures are the battle screen's sprites, so walking smoothly
  is a sprite moving a pixel or two a frame, nothing redrawn; a door redraws the view.
- **The grid** is two copies of the tiles' characters, with and without their seams (2 KB
  each, in the same asset): walking shows the seamless copy, and a fight switches the view's
  character set to the other, one write to `$D018` at the split; the screen itself isn't
  touched. (Or the seams fade in over a few frames by colour: the seam's colour is one of
  the multicolour registers, shared by every tile, stepped from the floor's grey to its own.)
- **Where you are** is kept in pixels while walking (a byte each way, the room being 256
  x 128 pixels at 16 a square), and the square is the pixel position over 16; collisions
  look up the tiles under the footprint's corners.
- **A look** is an asset: its tiles' characters (`battlegfx.py`'s `look16`: 12 a tile, so
  21 tiles at most, the eight terrain first) and its three shared colours, written to
  `$D021`-`$D023` when the floor is fetched; each square's colour RAM is its tile's own.
- **Authored rooms:** a Departure writes its rooms in Quest Script as it writes battle
  maps, with doors naming the room they lead to and things to act on (open, look, take,
  a check); generated floors are for Sidings like the Deep Yards.

## Still open

- **Talk** (*Talk*): one speaker for the party (the leader); signals as host menus rather
  than the language's own; a parley's fight starts as the room's fight always does, not an
  ambush or a sneak by how the talk went.

- **The party's prototype** (*The party*) has followers and the fan-out; still to try:
  suggestion markers, the choice stream an exploration makes, and two browsers sharing a
  stand-in host. And whether a party of four needs harder floors (the danger counts the
  floor and the depth, not the party).
- **Being seen.** Foes that notice you across the room (a check against your Stealth),
  rather than every fight starting as you come in; and sneaking past. Proposed, with
  floors that are one open area instead of rooms: [open-floors.md](open-floors.md).
- **Things to act on:** locks, levers, traps, a body to search: what a room's squares can
  hold beyond a cache.
- **Scrolling or flip-screen:** prototyped both (*Scrolling, to compare*); the C64's cost
  of scrolling is there. The verdict is for playing them.
