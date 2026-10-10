# The framed screen (E12, done)

One screen for the whole game, made of frames that stay put: a **view** at the top (the
story's picture, the room the party walks round, or the battle map), the **story log**
under it, the **party** and the **dice log** beside that, and the **commands** at the
foot. What happens shows up in its own frame: prose in the story log, every roll in the
dice log, health in the party frame. The pictures and the map take turns in the view, so
nothing else moves when a fight starts or ends.

Each machine gets its own version, optimized for it, all of them retro: the C64's is the
40 x 25 grid below. The desktop and the browser have the same grid for now, so the tests
can hold them to the C64's transcripts line for line; they can have more room (a wider
story log) later, in the same frames, font and colours.

## On the C64

The C64's way to do this is a raster split between two character modes (and the picture's
bitmap): the view in multicolour, for tiles and pictures; everything under it in hires
characters, for sharp text in our font. Printing is a byte per letter, frame lines are
characters of the font, and sprites (the party, foes, the cursor) live only in the view.

| Rows | Frame | Mode |
|---|---|---|
| 0 | where the party is, and Debt | hires text |
| 1-12 | the picture (160 x 96), in story | multicolour bitmap |
| 0-15 | the room or the battle map: 10 x 4 squares of 32 pixels (4 x 4 characters each), scrolling over bigger maps | multicolour characters, sprites on top |
| 16-23, columns 0-24 | the story log: prose, menus, the fight's narration; scrolls | hires text |
| 16-19, columns 26-39 | the party: up to four travelers, a line each, health as a bar | hires text |
| 20-23, columns 26-39 | the dice log: each roll in two lines; scrolls | hires text |
| 24 | the commands, or the prompt | hires text |

In the story, the raster interrupt shows the picture's bitmap on rows 1-12 and the text
screen round it (`fe/c64/split.s`); in a fight, the map's multicolour characters and
sprites on rows 0-15 and the text screen from row 16 (line 177, `fe/c64/sprites.s`). Both
play the music once a frame ([music.md](music.md)). A picture and a map never show at
once: the view loads whichever the moment needs, which costs nothing on an SD2IEC. The
frames are the same text screen all along ($F800, our font at $D000), so nothing in them
moves when a fight starts or ends.

**What goes where.** The story's prose, menus and a fight's sentences go into the story
log, which waits with "-- more --" (on the command row) before anything scrolls off
unread; a fight's sentences don't wait, the player's turns pace them. Every roll, a check
or a blow, goes into the dice log as two short lines (`client/view.c`,
`apb_view_roll`): what rolled and its total, "Wits 119", then the target and the outcome,
"vs 74: pass" (fail, cost, pass, crit; a blow's miss, graze, hit or crit and its damage),
the newest bright, the one before it grey. The party frame has each traveler's name and
health as a bar of five cells, in halves, red at a third or less; ">" and yellow on
whoever's turn it is in a fight; "down" when they are. Lines are typed on the command row
and then go into the story log, "> " and all, so the transcript has them; a fight's
commands and prompts are there too. The shared code draws through `client/apb_scene.h`'s
`hal_frame_` calls, which each front end keeps its own way.

**The map's look** (the battle screen first, rooms with E13): squares of 32 pixels; flat
tiles, a plain floor with faint seams and solid walls, so only the squares that matter
stand out (cover, a hazard, the exit, a pit); enemies only on the map, never in the party
frame. The figures are the C64's hardware sprites, 24 x 21.

## The party

Up to four travelers (E14). On a real C64 they're the player's own four: original hardware
is offline, so there's no multiplayer budget there, by rule. Playing together with friends
is for the modern machines, or a C64 with modern hardware (an Ultimate) or an emulator.
Until E14, the party frame shows the one traveler.

## Milestones

- **E12 Frames (done):** the framed screen on every machine, with the simpler battle view.
- **E13 Rooms:** a scene can be a room the party walks round, acting on things in reach
  (open, pick a lock, look, take) instead of choosing from a menu.
- **E14 The party:** up to four of the player's own travelers board together; each keeps
  their Passport, and the trip's stamp lands on each.
