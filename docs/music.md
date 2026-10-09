# Music

The game's music, on every machine (milestone E10, [c64-craft.md](c64-craft.md#1-music-e10)):
a Departure's tunes written as text, compiled to one small file, and played by one player
fifty times a second into the SID's registers. The C64 plays them on its SID; the desktop
and the browser play the same registers through a synthesiser that works like it. One
player, so the music is the same everywhere, and testable the way everything else is: the
Python reference (`tools/music/player.py`), the C player (`client/music.c`) and the 6502
player (`fe/c64/music.s`) must write the same registers, frame by frame.

Why not GoatTracker 2, which the craft guide suggested: its player is GPL, which a game
shipping it would have to answer to; and it packs songs only from its window, so a build
can't. This player is ours, small, and documented here; a converter from GoatTracker's
`.sng` can come later if a composer wants to work in it.

## Writing music

A Departure's music is a text file beside its `.qs`, `NAME.music`. `tools/music/musicc.py
build NAME.music -o MUSIC` compiles it; `check` checks it. Comments start with `#`.

```
instrument lead
  wave pulse
  adsr 0 9 a 6          # attack, decay, sustain, release: one hex digit each
  pulse 40 3 20 c0      # start, speed (signed, a frame), low, high: widths / 16
  vibrato 10 5 2        # delay (frames), depth (a semitone >> 5), speed (frames)

instrument kick
  wave noise =c5        # one line a frame: waveform, then a pitch
  wave pulse =c3
  wave pulse =g2
  adsr 0 8 0 0

instrument chord
  wave pulse
  wave pulse +4
  wave pulse +7
  loop 0                # after the last line, back to line 0 (else the last one holds)
  adsr 0 0 f 4
  pulse 80 0 80 80

pattern theme lead
  c4/4 e4/2 g4/2 >c5/4 b4/4 a4/8 r/8

pattern beat kick
  c4/2 r/2 c4/2 c4/2

tune platform tempo 7
  1: theme | theme theme+5
  2: | beat
  3: r16 | bassline
```

- **Instruments** (at most 32): a waveform table, one step a frame from each note's start:
  `tri`, `saw`, `pulse`, `noise`, joined with `+` and with `ring` and `sync` if wanted,
  then a pitch: `+n` or `-n` semitones from the note (default `+0`), or `=c5` a fixed
  note (drums). `loop n` goes back to step n after the last; without it, the last step
  holds. `adsr` sets the envelope; `pulse` the pulse width and how it sweeps between two
  limits; `vibrato` a wobble that starts after a delay.
- **Patterns** (at most 128): notes `c4`, `f#3`, `bb2` (octaves 0-7), each `/n` rows long
  (the length carries on until changed; up to 64; longer ones are tied for you); `r` a
  rest; `~` a tie, holding the note before; `>` before a note or tie slurs it into the
  next (no new attack); `@name` changes instrument. A pattern names its first instrument.
- **Tunes** (at most 32): a tempo (frames a row, 2-31), then each voice's patterns in
  order, `+n`/`-n` to transpose one. `|` marks where the voice loops back to when it runs
  out; a voice with no `|` plays once and stops, so a tune with none is a sting. `rN` is
  N rows of silence (a built-in pattern). Voices left out are silent.
- **Names** (tunes, instruments, patterns): small letters, digits and `_`. Story tunes are
  named as Quest Script's `~ music` names them; the battle screen plays `battle`, and
  after a fight `won` or `lost`, if the file has them.

## The file

Little-endian. At most 1536 bytes (the C64 keeps it under its I/O, with the player's note
table and state; a longer file is refused).

| Offset | Size | What |
|---|---|---|
| 0 | 3 | `MU`, version 1 |
| 3 | 1 | tunes T (1-32) |
| 4 | 1 | instruments N (0-32) |
| 5 | 1 | waveform steps W (0-128) |
| 6 | 1 | patterns P (0-128) |
| 7 | 1 | 0 |
| 8 | 8 T | tunes: tempo, 0, then each voice's sequence (3 offsets) |
| | 10 N | instruments: AD, SR, first waveform step, pulse start, speed (signed), low, high, vibrato delay, depth, speed |
| | 2 W | waveform steps: control, pitch |
| | 2 P | pattern offsets |
| | | tune names: length, then letters, T times |
| | | sequences and patterns |

Offsets are from the start of the file. **A waveform step** is a SID control byte (its gate
bit ignored) and a pitch: `$80` + a note is that note, anything else a signed 7-bit offset
from the playing note (`$7F` is -1). A control byte of `$FF` is a jump: its pitch byte is
the step to go to.

**A sequence** (one a voice): `$00`-`$7F` play that pattern; `$80`-`$BF` transpose by
(byte - `$A0`) semitones from here on; `$FE` the loop point; `$FF` the end (back to the
loop point, or the voice stops).

**A pattern:** `$00`-`$5F` a note (0 is C-0, 95 is B-7); `$60` a rest; `$61` a tie; `$80`-`$BF`
the length from here on, (byte & `$3F`) + 1 rows; `$C0`-`$DF` instrument (byte & `$1F`);
`$E0` the next note or tie is slurred; `$FF` the end. Anything else is refused.

`musicc.py` checks everything it writes, and every player checks every byte it reads
(an offset out of the file, a pattern or instrument that doesn't exist, a sequence that
takes more than 63 steps to reach a pattern, a pattern that takes more than 255 bytes to
reach a note, rest or tie): a bad file plays silence, never crashes.

## The player

Fifty frames a second. Each frame the player works out all 25 SID registers (its "ghost"
copy) and the machine writes them, `$D400` to `$D418`, in order.

### Commands

- `start(t)`: tune t from its beginning, at full volume. Every voice: its sequence's first
  pattern, no transpose, length 1 row, instrument 0, nothing sounding.
- `change(t)`: fade out (a step every 2 frames), then `start(t)`. t = 255: fade out and
  stop.
- `effect(e)`: sound effect e ([client/sfx.c](../client/sfx.c)) on voice 3.
- `volume(v)`: the volume, at once.

Commands take effect at the start of the next frame, before anything else.

### A frame

For each voice, 1 to 3:

1. If it has stopped, nothing (its registers keep what they had; its gate is shut).
2. If its frame count isn't 0, take 1 from it. If it is 0 now, read the next event:
   - In the pattern, length and instrument bytes are taken in turn; `$E0` marks the next
     note or tie slurred; `$FF` moves on through the sequence (a transpose byte sets the
     transpose; `$FE` notes the loop point; `$FF` goes back to it, or, with none, stops
     the voice: its gate shuts and nothing more happens).
   - **A note:** its pitch is the byte plus the transpose (kept to 0-95). If the segment
     before it was slurred, it's legato: only the pitch changes. Otherwise it starts: the
     gate opens, the waveform table goes back to the instrument's first step, the pulse
     width to its start (and its sweep to the instrument's speed), and the vibrato to
     nothing.
   - **A rest** shuts the gate. **A tie** holds what's playing.
   - Either way the frame count is the length × the tempo, and the segment is slurred if
     `$E0` came before it.
3. If the frame count is 1, the segment isn't slurred and a note is sounding, the gate
   shuts: each note ends a frame early, so the next one starts its envelope cleanly.
4. Once the voice has played a note:
   - **The waveform table:** read the step it's at. A jump goes to its step, and if that
     is a jump too, nothing changes this frame (the table holds). Otherwise the step's
     control byte and pitch are used, and the table moves on a step.
   - **The pulse width,** if its speed isn't 0: the sweep is added; past the high limit
     (× 16) it stops there and the sweep turns round; likewise at the low limit.
   - **Vibrato,** if its depth isn't 0: count frames since the note started (up to 255);
     once that's past the delay, move the offset a step (the gap from this note to the
     next semitone, shifted right by the depth; 0 past 15) up for `speed` frames, down for 2 ×
     `speed`, up for `speed`, and round again.
5. Its registers: frequency = the note table's value for (the note + the step's pitch,
   kept to 0-95, or the step's fixed note) + the vibrato offset (16 bits, wrapping); pulse
   width (12 bits); control = the step's control byte with its gate bit replaced by the
   gate; AD and SR from the instrument.

Then the filter registers are 0 and `$D418` is the volume.

**The note table:** the SID's frequency for each note on a PAL C64: f = 440 × 2^((n − 57)
/ 12) Hz, the register = round(f × 2^24 / 985248), at most `$FFFF` (B-7 is past the SID's top,
so it plays as `$FFFF`). On an NTSC machine the music plays
6/5 as fast and a semitone and a bit sharp; this game is PAL first.

**Fades:** each frame, when fading, the volume moves 1 toward its target every 2 frames;
reaching 0 on the way to a new tune starts it.

### Sound effects on voice 3

An effect takes voice 3 from the music, which keeps playing underneath but isn't heard
there. On its first frame, voice 3 gets frequency (its pitch byte × 256), pulse width
`$800`, its AD and SR, and its control byte with the gate open. Each frame after, its
frame count goes down; while it's not 0, its slide is added to the pitch byte (wrapping);
at 0 the gate shuts. 12 frames later the effect is over and voice 3 is the music's again,
with its gate shut until its next note starts. A new effect replaces one that's playing.

## Where it plays

- **The C64:** the player is in the main program (`fe/c64/music.s`, about 2.2 KB), and
  the tunes at `$D800`, under the I/O, with its note table (`$DE00`), the sound effects
  (`$DEC0`) and its state (`$DEF0`). A raster interrupt every frame calls it with the I/O
  switched out and copies its ghost registers to the SID ([c64.md](c64.md)).
- **The desktop and the browser:** `client/music.c`, the same player in C, feeds a
  three-voice synthesiser ([modern.md](modern.md)).
- **The terminal:** no music.

## Testing

`make test-music`: the Python reference plays every tune in `content/` and a set of tests
written to reach every rule above, and writes the 25 registers for each frame; the C
player and the 6502 player (on py65) must write the same, byte for byte. Damaged files must
play silence, never crash.
