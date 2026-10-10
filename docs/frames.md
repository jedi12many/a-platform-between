# The framed screen (E12)

One screen for the whole game, made of frames that stay put: a **view** at the top (the
story's picture, the room the party walks round, or the battle map), the **story log**
under it, the **party** and the **dice log** beside that, and the **commands** at the
foot. What happens shows up in its own frame: prose in the story log, every roll in the
dice log, health in the party frame. The pictures and the map take turns in the view, so
nothing else moves when a fight starts or ends.

Each machine gets its own version, optimized for it, all of them retro: the C64's is the
40 x 25 grid below; the desktop and the browser get more room (a wider story log), in the
same frames, font and colours.

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

The raster interrupt switches the VIC at the top of the view and again at row 16 (scanline
179); it plays the music once a frame, as it does now ([music.md](music.md)). A picture
and a map never show at once: the view loads whichever the moment needs, which costs
nothing on an SD2IEC.

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

- **E12 Frames:** the framed screen on every machine, with the simpler battle view.
- **E13 Rooms:** a scene can be a room the party walks round, acting on things in reach
  (open, pick a lock, look, take) instead of choosing from a menu.
- **E14 The party:** up to four of the player's own travelers board together; each keeps
  their Passport, and the trip's stamp lands on each.
