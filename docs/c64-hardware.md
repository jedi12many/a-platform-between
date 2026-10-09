# Making the most of the C64

*A plan, not yet built. It follows a look at how the C64's best role-playing games used the
machine (Pool of Radiance, The Bard's Tale, Ultima V, Wasteland).*

Today the game uses one 40-column text screen in the ROM's font, one still picture split
in above it, and the KERNAL's disk routines. The commercial games of the day used far
more of the machine:

| The C64 has | They used it for | We use it |
|---|---|---|
| **the SID** | music on the title and in towns; footsteps, bowstrings and blows in a fight | not at all |
| **8 hardware sprites**, reused down the screen | figures, cursors, arrows and fireballs that fly | not at all |
| **custom character sets** | a game's own font, frames, icons; whole tile worlds (Ultima) | the ROM's font |
| **raster interrupts** | split screens, colour bars, a flashing border | the picture split |
| **the joystick port** | menus, cursors, movement | not at all |

This page plans how to use them all, within the memory we have.

**Loading is free.** Most C64 players today load from an SD2IEC or similar, not a 1541,
and waiting on the disk isn't a concern for this game. So the C64 version may load as
often as it likes: code, tiles, sprites and pictures each when they're needed, and loaded
again afterwards rather than kept. That's what makes room for everything below.

**Space is free too.** An SD card holds as much as we like: an SD2IEC loads plain files
from the card's folders, and disk images up to a .d81's 800 KB (a .d64 holds 170 KB). So
a Departure can carry a picture for every scene, its own tiles and sprites, and music,
without counting kilobytes on the disk; when one outgrows a .d64, its disk becomes a .d81
(`tools/d64.py` learns the format). Only the C64's 64 KB of memory is a limit, and the
plan works around it by loading things when they're needed.

## Memory

The main program is 22 KB and has about 800 bytes free; its buffers take 13 KB more; the
three overlays share 15 KB at $9400–$CFFF, and the BATTLE overlay already uses 15,095
bytes of its 15,360. So nothing new fits where things are. The room is in the top 16 KB,
**VIC bank 3** ($C000–$FFFF), which the VIC can show without the CPU's help: the RAM
under the I/O chips ($D000–$DFFF, 4 KB, unused today) and under the KERNAL ($E000–$FFFF,
8 KB, of which the picture uses 3.5 KB).

The plan moves the whole display into bank 3, text included:

| Address | Holds | Size | Notes |
|---|---|---|---|
| $D000–$D7FF | **our font**: letters, frames, bar segments, icons | 2 KB | under I/O: the VIC sees it; the CPU writes it with I/O switched out |
| $D800–$DBFF | **the text screen** | 1 KB | the VIC reads RAM here, not the colour RAM the CPU sees |
| $DC00–$DFFF | **sprite shapes**: 16 of 64 bytes | 1 KB | figures (body + outline), cursor, bolt, spark |
| $E000–$E7FF | the picture's characters, **or** in a fight the battle's tiles | 2 KB | a fight takes the whole screen, so the two never show at once |
| $E800–$EBFF | the picture's screen, or the battle map's | 1 KB | |
| $EC00–$EDDF | the picture's colours | 480 B | |
| $EE00–$FFF9 | **sound**: the SID player, effects and tunes | 4.5 KB | runs from the raster interrupt with the KERNAL switched out for a moment |
| $0400–$07FF | freed (the old text screen): the sound-effect player and its table | 1 KB | in bank 0, always there for the main program |

As built, it went a little differently ([c64.md](c64.md#how-it-fits-in-64-kb) has the
map): the text screen went to $F800 and our font to $D000 (the old screen at $0400 holds
the battle screen's buffers now); the story's picture
became a **multicolour bitmap** (the bitmap at $E000, its screen at $F400: three colours
of any sixteen in every cell, and no limit of 256 different cells); and a fight puts its
characters at $E000, its screen at $E800 and its sprite shapes at $F000, then loads the
picture again.

The BATTLE overlay needs room for the new screen. Because loading is free, a fight can
**borrow the chapter's memory**: the car buffer (up to 6 KB) moves to sit just below the
overlay area, a fight's overlay is allowed to run over it, and after the fight the
chapter is loaded again (the VM only keeps its place in it as an offset). The tiles and
sprite shapes for a fight load from the disk too, into bank 3, and the picture is loaded
again when the story shows one.

## The milestones

**E9: the battle screen.** In steps, each one playable and tested:
- **E9a, the screen's logic, on the desktop and in the browser** (done). A battle screen shared
  by every front end with graphics (`client/`), drawing through a small interface: tiles,
  figures, a cursor, marks, effects, text in the panel and the log, sounds. The terminal
  keeps the text screen. Tests play fights through a recording stand-in for the
  graphics, so the screen's every move is in a transcript.
- **E9b, the C64** (done, [c64.md](c64.md#the-battle-screen)). The same screen on the
  VIC: bank 3, tiles in characters, figures in sprites through a multiplexer, keys and a
  joystick, the fight borrowing the chapter's memory.
- **E9c, sound** (done). The SID's effects, from one table (`client/sfx.c`), and the same
  through a small SID-style synthesiser on the desktop and in the browser
  (`fe/modern/sound.c`).
- **E9d, our own font** for all the game's text (done): the story's and the battle
  screen's, the same letters; the text screen moved to bank 3 to use it.

**Bitmap pictures** (done): the story's pictures in multicolour bitmap mode, and
`tools/c64fit.py` giving every cell its best three colours of sixteen.

What the screen does:
- The map in tiles, 24 x 24 pixels (3 x 3 characters) a square, three-quarter view;
  maps wider than 9 squares scroll, as Pool of Radiance's did.
- Every figure is two sprites: a multicolour body and a hires outline over it, so it
  stands out of any floor. With the cursor and a projectile that's 8 for a small fight;
  bigger fights reuse sprites down the screen (a multiplexer in the raster interrupt).
- A hit flashes the struck figure white; a bolt or an arrow flies; the fallen lie down.
- The Gold Box command bar: Move (step by step, keys, numpad or joystick), Aim (a cursor
  onto a target), Guard, Wait, Quick, Done; the roster and the log beside and below.
- Sound effects through the SID: a step, a swing, a shot, a hit, a miss, a death.
- The rules don't change: every battle test and transcript stays as it is.

**After E9**, the order and the reasons are in [c64-craft.md](c64-craft.md), from research
into how modern C64 games are made: music, then transitions, comfort in a fight, ELoad and
save slots, a profiler, the art pipeline, presentation.

**E10: music.** A tune for the title, one for the Waystation, one per Departure: a
GoatTracker 2 player in the main program, subtunes for each mood, and the sound effects
borrowing a voice ([c64-craft.md](c64-craft.md#1-music-e10)).

**E11: pictures that move.** Colour cycling and a few swapped characters per frame: the
klaxon pulsing on Dock 3, the reactor's glow, the Static crawling, the countdown counting;
the border flashing red as the minutes run out, and white at the meltdown.

Along the way: our own font for all text, and the joystick everywhere.

## The desktop and the browser

They get the same: the same tiles and sprites drawn at twice the size, the same effects
and tunes through a small three-voice synthesiser with the SID's waveforms and envelopes
(SDL's audio on the desktop, Web Audio in the browser), the same animations.

## Testing

What `make test-c64` can check, and what it can't:
- **Sprites and tiles:** the emulated screen (`--shots`) learns to draw sprites and custom
  characters, so a fight can be looked at, and its pictures compared.
- **Sound:** the SID's registers are recorded, so a test can say "a hit sounded here"
  without listening to it.
