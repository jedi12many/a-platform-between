# Plan B: the upper limits

*A plan, not yet built. Plan A is what the cartridge does now ([cartridge.md](cartridge.md)): a
framed screen, a map of 16-pixel squares over a story log, eight sprites, a careful list
of tricks we don't use ([c64-craft.md](c64-craft.md#what-we-wont-do)). Plan B asks how far
a stock C64 and a 1 MB EasyFlash can go for this game, and what it costs.*

## The pitch

Switch it on, and the train pulls in. Then you are walking: a whole-screen world, four
travelers in a line behind you, scrolling smoothly in eight directions at 50 frames a
second. The dungeon is dark beyond your lantern. Water ripples, the Static crawls, and a
camp stove flickers. The party's faces and health sit in the bottom border, where a C64
isn't supposed to draw anything. Someone speaks, and a text window rises out of the floor
in a proportional typeface, as on a Macintosh. Foes see you, the grid fades up under your
feet, and the fight is on the same screen with nothing loaded. A hit shakes the screen
and stops time for a few frames. On the title, a voice says "Tickets, please."

All of that is a stock PAL C64 with one SID, and the two ways we ship: a **Kung Fu Flash 2**
(the game as an EasyFlash cartridge image) and a **modern SD2IEC** (the same game as
files). Nothing needs a modification, a REU or an accelerator (*The two targets*).

## How it's possible

Three things make the ceiling higher than 1985's:

- **1 MB of cartridge, copied in at memory speed.** On a Kung Fu Flash 2, Plan A already
  copies 8 KB assets out of the cartridge in a few frames. Plan B goes further: animation,
  cutscenes and the world's tiles come in as they're needed, so the 64 KB of RAM holds
  only this moment's things. On an SD2IEC the same assets load at quiet moments instead.
- **Forty years of what's known.** Eight-way smooth scrolling at 50 fps with colour,
  multiplexers for 24 or more sprites, opened top and bottom borders, proportional bitmap
  fonts (GEOS did them in 1986), and 8-bit samples that play on both SID chips
  (Mahoney's technique) are all documented and proven, by Sam's Journey among others.
  None of it is exotic any more; what's rare is putting it all in one RPG.
- **Our harness counts cycles.** `make test-cart` already holds the raster split to the
  cycle on an emulated C64. Every trick here comes with a check of its timing, and the
  same harness says when a frame runs over. That is how we find the limit instead of
  guessing at it.

## The budget

A PAL frame is 312 lines of 63 cycles: **19,656 cycles**, 50 times a second. Walking at
the prototype's speed (4.5 squares a second, 16 pixels a square) is about 1.4 pixels a
frame, so the screen moves a whole character about every 5 frames. In a walking frame,
roughly (**estimates, to be measured** by the harness before we rely on them):

| What | Cycles | When |
|---|---|---|
| Bad lines (the VIC reading the screen) | ~1,100 | every frame |
| Sprites: 24 figures, multiplexed in bands | ~2,000-3,000 | every frame |
| Raster interrupts: the bands, the border, the split | ~1,000 | every frame |
| Music (1x speed) | ~1,000-2,000 | every frame |
| The scroll: the next screen built in the hidden buffer, a fifth at a time | ~1,600 | 4 frames of 5 |
| The scroll: colour RAM shifted, racing the beam | ~8,000 | 1 frame of 5 |
| Light, animated tiles, the party's trail | ~1,000 | every frame |
| **Left for the game** (moving, the story VM, AI) | **~5,000-11,000** | |

The costly frame is the one that shifts colour RAM, which can't be double-buffered. That
is the known hard part of colour scrolling, and the reason Plan B's tiles are designed so
a tile's colours go with its characters (*The world*, below).

## The features

Each one has what the player sees, how it's done, what it costs, its risk on real
hardware, and a demo that proves it. They're ordered by how much they're worth.

### 1. A world that scrolls (the big one)

- **Seen:** the explore prototype's scrolling mode
  ([rooms.md](rooms.md#scrolling-to-compare)) on a C64: a 48 x 24-square floor, the view
  following the party smoothly in eight directions at 50 fps, no pauses at doorways. When
  you're walking the whole screen is the world.
- **How:** character mode, 16-pixel squares (2 x 2 characters), fine scrolling with
  `$D016`/`$D011`, and two screens in VIC bank 3: the next one is built in the hidden
  buffer over four frames, and the buffers swap on the fifth. Colour RAM is shifted that
  frame, racing the raster down the screen. Tiles are drawn so that most of a square's
  colour is in the shared colours and its own colour is the tile's, so a colour RAM row
  can be rebuilt from the map row by row.
- **Cost:** the table above. Memory: two 1 KB screens, 2 KB of characters, the floor's
  map (48 x 24 = 1,152 bytes, or 576 at two squares a byte).
- **Risk:** low. It's the standard method, and it's in many released games.
- **Proof, B1** (built: [walk.md](walk.md)): a program that walks yard 48213's floor 1 by joystick, checked
  against the browser prototype: the same floor (`tools/rooms/rooms.py`), the same speed,
  the same camera. The harness counts every frame's cycles and fails if one runs over.

### 2. Many figures, all of them moving

- **Seen:** the party walking in marching order, each traveler animated in eight
  directions; foes idling, turning to look; Vell at her stove; Pell following. 24
  figures or more on a screen.
- **How:** a sprite multiplexer, sorted by Y, set from raster interrupts in bands. The
  game keeps a rule that no more than 8 figures share a band of lines, and lays out rooms
  to keep it (the generator already places people; it can keep to a band too). Animation
  frames come from a cartridge asset, a few frames of each figure, copied in when a floor
  starts.
- **Cost:** about 2 cycles per sprite per line it covers, plus an interrupt per band.
- **Risk:** low. The worst case is a figure flickering if too many crowd one band, which
  the layout prevents.
- **Proof, B2:** B1 with the party of four, all the floor's foes and its people, and a
  check that no frame shows more than 8 sprites on a line.

### 3. The light

- **Seen:** a dungeon that is dark except where your lantern reaches, a pool of light
  that moves with you and flickers. Rooms you've left fall back into the dark. Fog of war
  for free.
- **How:** each look gets a dark copy of its tiles (characters drawn in the look's
  darkest colours), so a square is lit or dark by which copy is on the screen. The light's
  edge is a few squares round the party, redrawn as you step, with a softer middle tone at
  its rim. Flicker comes from changing one shared colour a few times a second.
- **Cost:** a second set of the look's characters (the 21-tile limit becomes about 10
  lit and their dark copies, or fewer frills), and a few dozen cells rewritten each step.
- **Risk:** low.
- **Proof, B3:** the dungeon look in B1, lit.

### 4. Drawing in the border

- **Seen:** the party's portraits, names and health bars along the bottom of the screen,
  in the border, so the whole 25 rows are the world.
- **How:** the top and bottom borders open when `$D011` switches to 24 rows on the right
  line each frame: a couple of writes per frame, not a cycle-exact loop. Only sprites show
  there, so the HUD is sprites: 8 across, 24 x 21 each (portraits, numbers in a sprite
  font).
- **Cost:** a few cycles, and 8 sprites' worth of shapes.
- **Risk:** low. This trick has been used in games for decades. (The *side* borders
  stay shut: opening those needs the whole CPU.)
- **Proof, B4:** the HUD in B2's border, checked line for line.

### 5. A text window that rises

- **Seen:** walking, the screen is all world. Someone speaks, and the story's window
  slides up from the bottom (or a fight's command bar does). It goes back down as you
  walk away.
- **How:** the split Plan A already has (`cart/split.s`), its line moved a few lines
  each frame. The frames below it are text; the world above keeps scrolling.
- **Cost:** nothing new.
- **Risk:** low. The split's timing check moves with it.
- **Proof, B5:** in B2, talk to Vell.

### 6. A proportional typeface

- **Seen:** the story set in a real typeface, letters of their own widths, kerned,
  typed out letter by letter, with small icons inline (a die, a coin). About 55
  characters to a line instead of 40, and easier on the eye.
- **How:** the frames' area becomes a hires bitmap (the picture's bitmap at $E000 ends
  where the frames' rows begin, so the two fit end to end), and a blitter puts each
  glyph where the last one ended. It's the path GEOS took.
- **Cost:** about 3 KB of bitmap, a glyph-drawing routine, the font. Speed doesn't
  matter here: text arrives slower than it's drawn.
- **Risk:** low. The work is in the type design, which is ours to get right.
- **Proof, B6:** The Fare's opening, set in it, against `tests/cart/fare-edge`'s words.

### 7. Juice

- **Seen:** a hit shakes the screen and the game holds still for three frames. A crit
  flashes the border. Iris and dissolve wipes between scenes. Water, lava and the Static
  animated. A spell's bolt trails sparks.
- **How:** screen shake is the fine-scroll registers; hit-stop is the main loop waiting;
  flashes are colour registers; wipes are a sprite ring or characters swapped in order;
  animated tiles swap a few characters' bytes each frame (E11 in
  [c64-hardware.md](c64-hardware.md)).
- **Cost:** small, all of it.
- **Risk:** none.
- **Proof, B7:** a fight from B2 with all of it, and the harness reading the registers
  frame by frame.

### 8. Pictures beyond multicolour (while the story waits)

- **Seen:** a story's important pictures (the train, Vell's face) in far more colour than
  multicolour bitmap allows.
- **How**, in two strengths:
  - **Sprite overlays** (cheap, any time): a picture's multicolour bitmap with a few
    hires sprites laid over the detail that needs it (eyes, lettering), which
    `tools/c64fit.py` can choose.
  - **FLI** (expensive, only while the story waits for a key): a new screen of colours
    every line of the view, so every 4 x 1 pixels can have its own colours. The CPU
    spends the view's 128 lines on it; the rest of the frame is left for the music and the
    keys, and nothing else is running then.
- **Cost:** FLI needs 8 KB of screens and the bitmap, a VIC bank of their own while it
  shows, so the chapter moves aside (it's re-fetched from the cartridge after).
- **Risk:** medium. It's an exception to our rule against FLI in play
  ([c64-craft.md](c64-craft.md#rules-we-work-by), rule 1), which allows an expensive mode
  on a still screen waiting for a key, and this is one.
- **Proof, B8:** The Fare's platform picture in FLI, the music playing over it, every
  frame on time.

### 9. Sound you don't expect from a C64

- **Seen (heard):** the music at double speed for faster notes and filter sweeps; each
  place with its own ambience; and on the title only, a voice: "Tickets, please." and a
  whistle.
- **How:** the player at 2x speed (two calls a frame); 8-bit samples by Mahoney's
  technique, which works on both the 6581 and the 8580, played on the title while nothing
  else runs.
- **Cost:** a 2x player is a few hundred cycles more a frame; samples take most of the
  CPU while they play, and about 8 KB a second of sound from the cartridge (a whistle and
  a sentence: a few banks).
- **Risk:** medium. Samples are another of rule 1's exceptions (the title waits for a
  key), and they need checking on both SID chips.
- **Proof, B9:** the title, recorded off the harness's SID registers and listened to.

### 10. Cutscenes streamed from the cartridge

- **Seen:** the train arriving out of the dark, animated, full screen, for 20 seconds.
- **How:** character-mode animation at 12-25 frames a second, each frame's changed cells
  copied in from the cartridge (deltas, packed). 1 MB holds minutes of it.
- **Cost:** the CPU while it plays; cartridge space.
- **Risk:** low on the Kung Fu Flash 2. On an SD2IEC: loaded first, shown after.
- **Proof, B10:** the arrival, as the title's opening.

## The two targets

We build for two devices, and every feature is measured on both:

| | Kung Fu Flash 2 | SD2IEC |
|---|---|---|
| The game is | an EasyFlash `.crt`, 1 MB | files on the card (`.d64`/`.d81`, or plain files) |
| An 8 KB asset comes in | from a bank, at memory speed: a few frames | loaded through the serial bus: much slower, even with a fast-load protocol |
| So Plan B | streams freely: animation frames, cutscenes, a floor's tiles mid-walk | loads at the quiet moments (a floor's start, a scene's start, behind a wipe) and keeps it in RAM |
| Cutscenes (10) | streamed while they play | loaded first, shown after (shorter, or fewer frames) |
| Samples (9) | played from the cartridge | loaded first; only what fits in RAM |

Everything else (1 to 8) is the same on both, because it happens in RAM once a floor or
a scene is in. That's the rule: **nothing in play may wait on the medium**. Only
`cart/assets.s` knows which one it is, as now, and on the SD2IEC it should use a fast
serial protocol the SD2IEC speaks, with the KERNAL's load as the fallback
([c64-craft.md](c64-craft.md#4-loading-and-saving)).

Other hardware isn't a target. A REU or a second SID (on Ultimate devices) could get
extras one day, but the game is designed and tested without them.

**PAL and NTSC.** Plan B is built and measured for PAL first (19,656 cycles a frame), then
NTSC (17,095: 65 x 263), where the budget is tighter.

## Still off the table

Even in Plan B:

| Technique | Why |
|---|---|
| Opening the side borders in play | it needs a cycle-exact write on every line: the whole CPU |
| VSP and AGSP scrolling | they crash some real C64s; the method in feature 1 doesn't need them |
| Interlace and flicker-colour | it flickers on today's screens |
| Requiring a REU, a second SID or an accelerator | our targets are a Kung Fu Flash 2 and an SD2IEC on a stock C64 |

## The order

The demos build on each other, each a cartridge `make test-cart` checks:

1. **B1 + B2 + B4, "walk the yard":** the scrolling floor, the party and its people, the
   HUD in the border. This is the leap a player sees, and it settles the frame budget for
   everything after it.
2. **B5 + B6:** talking, in the new typeface, the window rising.
3. **B3 + B7:** light and juice.
4. **B9 + B10:** the title, and the arrival.
5. **B8:** FLI pictures, last, as the costliest and least needed.

Plan B is a new front end on the same game: the rules, the story VM, Quest Script, the
Passport, and every reference and test stay as they are. It waits on rules v1 being
frozen, as the C64 does, except B1 and B2, which only walk, and can start now.

## What we need to find out

- The real cycle counts in *The budget*, measured in the harness, and then in VICE's
  x64sc and on a real C64.
- How many figures share a band on our floors, with the party in a line.
- How the light looks with each look's darkest colours (and on the early VIC's 5-luma
  palette).
- Whether Mahoney's samples keep time copied out of the Kung Fu Flash 2 for a whole
  sentence, and how much of them fits in RAM for the SD2IEC.
- How fast a floor's assets load on an SD2IEC with a fast-load protocol, against the
  KERNAL's load: the length of a floor's start.
- What a typeface for the story should look like at 8 pixels tall.
