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

- **Walking is free.** With no foes in the room, a step is a key press (8 ways), or click a
  square to walk there; no turns, no Speed. Out of a fight you don't walk into a pit or a
  hazard: you go round (the floor is built so you always can). Rough ground and cover are
  just ground.
- **Doors.** Step onto a door and you're in the next room, one square inside its matching
  door.
- **Coming into a room with foes in it starts a fight**, at once, on that room's map: you
  where you came in, the foes where they stand. It's the battle engine's ordinary fight:
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

## On the C64 (later)

- **Memory:** a room is 128 tiles (64 bytes, two to a byte); a floor's nine are built again
  from the yard whenever they're needed, so only what's cleared and taken is kept (a
  byte a room).
- **Drawing:** the view's 32 columns of the room, the floor's map in the 8 to its right
  (a character a room); the figures are the battle screen's sprites. A step is a sprite
  moving 16 pixels; a door redraws the view.
- **Authored rooms:** a Departure writes its rooms in Quest Script as it writes battle
  maps, with doors naming the room they lead to and things to act on (open, look, take,
  a check); generated floors are for Sidings like the Deep Yards.

## Still open

- **More than one traveler** walking (E14): the party moves as one figure out of fights, and
  spreads out round the door when one starts?
- **Being seen.** Foes that notice you across the room (a check against your Stealth),
  rather than every fight starting as you come in; and sneaking past.
- **Things to act on:** locks, levers, traps, a body to search: what a room's squares can
  hold beyond a cache.
- **Bigger places:** rooms wider than the screen, scrolling, for towns and the open.
