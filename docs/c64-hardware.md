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
| **the 1541's own CPU** | fast loaders, 5 to 20 times the KERNAL's 400 bytes a second | the KERNAL |
| **raster interrupts** | split screens, colour bars, a flashing border | the picture split |
| **the joystick port** | menus, cursors, movement | not at all |

This page plans how to use them all, within the memory we have.

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
| $0400–$07FF | freed (the old text screen): **the fast loader**, the effects table | 1 KB | in bank 0, always there for the main program |

The BATTLE overlay needs room for the new screen. The plan is to measure first, then:
move the battle screen's drawing into a small assembly module (tile and sprite work is
what assembly is good at), keep the rules in C, and if it still doesn't fit, take the
battle's buffers out of the main program into the overlay (as `OVL2BSS` did for PASS).

## The milestones

**E9: the battle screen** (the mock-up: `docs/` will hold it once agreed).
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

**E10: a fast loader.** Our own drive code, uploaded to the 1541, loading chapters,
overlays and pictures several times faster. The KERNAL's routines stay as a fallback
(other drives, SD2IEC).

**E11: music.** A tune for the title, one for the Waystation, one per Departure.

**E12: pictures that move.** Colour cycling and a few swapped characters per frame: the
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
- **The fast loader:** the test harness answers the KERNAL in Python; it can't run a 1541.
  It will answer the loader's call the same way, which tests everything but the drive's
  side. That side gets checked in VICE by hand (Ubuntu's VICE has no ROMs, so CI can't).
