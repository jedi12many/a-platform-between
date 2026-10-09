# Making it feel modern: our C64 craft guide

Modern C64 games look and feel modern because they are polished, not because they use
exotic tricks. They use cheap raster splits and colour chosen by brightness. They have a
real soundtrack, with sound effects that borrow a voice from it. Their loaders work on
whatever drive the player has. Their art is made inside the hardware's rules. And they
are finished, patched, and honest about the hardware they need. The showpiece techniques
(FLI and NUFLI pictures, VSP scrolling, opened side borders, sampled speech) belong to
demos and title screens: in play they take the whole CPU, flicker, or crash some
machines.

This guide is what that means for *A Platform Between*: what we keep doing, what we
build next, and what we leave alone. The research behind it, with every source, is
[research/modern-c64-game-craft.md](research/modern-c64-game-craft.md). **Read its
caveat**: the researchers' web access was blocked, so most findings come from
search-engine summaries of the sources rather than the pages themselves. Numbers marked
unverified there (rastertime of music players, compiler benchmarks, fade tables) are to
be measured here before we rely on them.

## Where we stand

Our screens already have the shape the research recommends. What we haven't built yet
is the part players notice most.

| | What we have | What the best modern games do | Next |
|---|---|---|---|
| Story screen | Multicolour bitmap picture on rows 1-12, raster split to hires text in our own font | The same: a cheap split, a readable 40-column font | Transitions; portraits |
| Battle screen | Character-mode tiles, two-sprite figures, a Y-sorted multiplexer, joystick | Sprites sorted by Y, double-buffered, set from raster interrupts | Comfort: fewer keys, faster turns |
| Sound | Eight SID effects on one voice | A tracker soundtrack, with effects that borrow a voice | E10: music |
| Colour | Pictures fitted in Lab colour, on the Pepto palette | Colour chosen by brightness (luma); pictures checked on early machines too | Check on the 5-luma palette |
| Loading | KERNAL LOAD, sequential files; made for SD2IEC | Loaders that detect the drive, with a KERNAL fallback | ELoad on SD2IEC |
| Saving | One save file, by DOS commands | Saves the game manages itself; never saves through custom drive code | Save slots |
| Speed | cc65, with `-Cl` in the fight | Hot paths found by profiling, then rewritten | A profiler in our harness |

## Rules we work by

1. **Cheap tricks only during play.** Raster splits, colour changes, sprite
   multiplexing, opening the top and bottom borders, FLD: yes. FLI, NUFLI, interlace,
   VSP, opened side borders and sampled sound: never during play. A still,
   full-screen chapter plate while the game waits for a key is the one place an
   expensive mode could go.
2. **Raster interrupts set the VIC and play music, nothing else** (Cadaver's rule). Game
   logic stays in the main loop.
3. **Colour by brightness.** Pair and dither colours of near-equal luma; large luma jumps
   read as noise. Check pictures on the early VIC's 5-luma palette as well as the
   9-luma one (red, blue, brown and dark grey collapse together on the earliest
   machines).
4. **Every action answers.** A key, a step, a hit or a refusal gets a sound and something
   on the screen, at once. No silent waits: if the disk is working, the screen says so
   (the border colour, a line of text).
5. **Fights are written, not rolled.** The most admired modern C64 RPG was faulted for
   its random encounters. Every fight in a Departure is placed by its author, and short.
6. **Respect the player's hardware.** It must work on SD2IEC, real drives, Pi1541 and
   Ultimate devices through the KERNAL. Every speed-up has a KERNAL fallback. Saves use
   standard DOS commands only. The release states PAL or NTSC, the drive, and any memory
   it needs.
7. **Everything stays testable.** Each improvement comes with a check in our own
   harnesses (py65, sim65, the Python references). Where the research gave no reliable
   number, we measure it.

## The plan

In order. Each step is playable and tested on its own, like E9's.

### 1. Music (E10): done

Built as [music.md](music.md) says, with one change from the first plan: **our own
player**, not GoatTracker 2's. GoatTracker's player is GPL, and its packer runs only
inside its own window, so a build couldn't make a tune from source. Ours is small enough
to write three times and test against itself:

- **The player:** a tune file of at most 1.5 KB, written as text (`NAME.music`) and
  compiled by `tools/music/musicc.py`; instruments with wavetables, pulse sweeps and
  vibrato, patterns, looping voices and stings; fades between tunes. The same player in
  Python (the reference), C (desktop and browser) and 6502 (the C64, in the main program,
  run once a frame from the raster interrupt), and `make test-music` holds all three to
  the same 25 registers, frame by frame, and each real tune's frame to half a PAL frame.
- **The music:** one file per Departure, with tunes for its moods and places, cued from
  Quest Script (`~ music NAME`, `~ music off`); a fight plays `battle`, then `won` or
  `lost`. The Fare has eight, *Eighteen Minutes* twelve, the Deep Yards eleven (one for
  each realm a floor can be). Silence is a cue too: Kepler-Nine's meltdown cuts to it.
- **Sound effects:** `client/sfx.c` stays the one table; the player plays an effect on its
  third voice, which goes back to the music after.
- **The desktop and the browser:** the C player into a synthesiser that works like the
  SID, from the same registers; so the music is the same everywhere, and testable.
- **Measured:** about 1,700 cycles a frame (27 raster lines), up to 8,200 when all three
  voices start new patterns, in the bottom border. Loading is still the KERNAL's, whose
  serial routines hold interrupts off byte by byte, so the music may stutter while a file
  loads; not yet heard on real hardware.
- **Still to do:** the composer. The tunes in the repository are ours, written to the
  scenes; a commissioned score would replace them file by file, in the same notation.

### 2. Transitions

- **Fades:** each colour steps to its next-darker neighbour by luma, through a 16-entry
  table, every few frames, on the picture's colours, colour RAM and the border and
  background. Fading in needs its own ramps up from black (the fade-out table doesn't
  invert). We derive both tables from the luma order in Python (`tools/`), test them,
  and use them everywhere: the C64, the desktop and the browser.
- **Wipes:** moving the raster split a line a frame opens and closes the picture like a
  curtain, at almost no cost.
- **Where:** between scenes, into and out of a fight (fade, then the battle screen fades
  in), at a chapter title, at the end of a trip.
- **The rule:** short. A fade is a third of a second, and a key press skips it.

### 3. Comfort in a fight

Pool of Radiance's rules still hold up. Its interface doesn't, and that is what players
of the C64 version complained about: too many keys for one action, no single "done".
Ours already has a command bar, a cursor, Done and Back. Next:
- **Bump to attack:** moving onto a foe in reach attacks it.
- **Faster turns:** a key that speeds up or skips the foes' animations, and Quick for
  the player's own.
- **One key for Back everywhere,** on the keyboard and the joystick (a long press of
  fire, or the second button where there is one).
- **The joystick for everything,** menus included, as on the battle screen.

### 4. Loading and saving

- **ELoad for SD2IEC,** built into its firmware, beside the KERNAL path, as Cadaver's
  loader does: detect the drive, use the fast path if there is one, otherwise the KERNAL.
  Measure its speed first.
- **Saves:** standard DOS commands only (custom drive code can't save on SD2IEC), and
  slots the game manages: it writes the new save beside the last one and only then
  replaces it, so a failed save never loses the trip.
- **One disk where possible:** a `.d81` image for drives that take it, with the `.d64`s
  kept as the lowest common denominator.
- **Cartridges:** not now. If an EasyFlash build ever comes, it needs disk saves too,
  because cartridge saves are unreliable on the emulating hardware most people own.

### 5. Speed

- **A cycle profiler** in the py65 harness, using ld65's labels, so we know where the time
  goes in a fight and in the VM.
- **Then the cc65 techniques that work** (ilmenit's guide): globals instead of the C
  stack for hot functions, arrays laid out by field, lookup tables instead of
  arithmetic and switches, and avoiding integer promotion. The worst paths move to ca65.
- **Not now: another compiler.** Oscar64 and llvm-mos make faster code, but switching
  would lose sim65 testing and our overlay setup.

### 6. The art pipeline

- **CharPad and SpritePad files** read by our Python tools, so artists can use the
  standard editors, while `tools/test_pictures.py` and `tools/battlegfx.py` stay the
  judges.
- **The early palette check** (rule 3), in `tools/test_pictures.py`.
- **A real VIC-II check:** where VICE with its ROMs is available, a headless run that
  takes a screenshot, compared with `tools/vic.py`'s drawing.

### 7. Presentation

- **Portraits in dialogue:** a speaker's face in sprites over the picture window. The
  story screen has all eight sprites free.
- **A title screen** with the title tune, and the departures board.
- **E11, pictures that move:** colour cycling and a few changing characters per frame
  (the klaxon on Dock 3, the reactor's glow, the countdown), the border as an alarm.
- **Decoration in the opened top and bottom borders,** if it earns its place.

### 8. The release

- **The hardware, stated plainly:** PAL or NTSC, the drives that work, the memory.
- **An emulator in the download,** set up and ready, as RGCD did.
- **Patches after release,** like the best modern games.
- **A physical edition** some day: a manual, a map, the soundtrack, and a printed
  Passport card.

## Before a screen ships

- Every key and joystick move gets a sound and a visible answer.
- Nothing waits without saying so; any wait longer than a second shows progress.
- Colours read on the 9-luma and the 5-luma palettes, and on the desktop's.
- It fades in and out, and a key press skips the fade.
- It works with the keyboard alone and the joystick alone.
- It works on SD2IEC and through the KERNAL on a 1541, and saves on both.
- Its test transcript is reviewed, and its screenshots looked at.

## What we won't do

| Technique | Why not |
|---|---|
| FLI, NUFLI, IFLI in play | They leave the CPU almost nothing, and interlace flickers |
| VSP and AGSP scrolling | They crash some real C64s |
| Opening the side borders | A cycle-exact write on every line: the whole CPU |
| Sampled speech and digis | Costly, and almost silent on the 8580 SID |
| 80-column text in 4 x 8 letters | Close to illegible |
| Custom drive code for saving | It fails on SD2IEC |
| Random encounters | The criticism the best modern C64 RPG got |

## What we still need to find out

- How many raster lines and bytes a GoatTracker player takes with one of our tunes.
- Whether the music keeps time during a KERNAL load.
- How fast ELoad is on today's SD2IEC firmware.
- Whether the C64 Gold Box games drew their fighters as sprites or characters (for
  reference, not to copy).
