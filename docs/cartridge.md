# The cartridge and the disk: A Platform Between in 6502 assembly

The game is being rebuilt in 100% 6502 assembly (ca65), for two ways of playing it on a
real C64: a 1 MB EasyFlash cartridge image (`.crt`) that starts the moment the machine is
switched on, for a Kung Fu Flash (or any EasyFlash); and a disk (`.d64`, or its files on
an SD card) for an SD2IEC. One engine, the same on both: only the module that fetches
assets (`cart/assets.s`) knows which it came on. The game owns the machine; on a disk,
the KERNAL is kept only to load the assets.

What stays from the C engine (`core/`, `vm/`, `fe/c64/`): the rules, the story's language
and its compiler, and the Waystation. They're the specification now:

- **Quest Script** (`tools/qsc/`, [quest-script.md](quest-script.md)) still compiles each
  Departure to the bytecode in [vm-spec.md](vm-spec.md); the cartridge has a VM for it,
  in 6502 assembly, and the chapters go into cartridge banks.
- **The Python references** (`tools/passport/`, `tools/rules/`, `tools/yards/`,
  `tools/music/`) are the test oracle: the cartridge's Passports, dice, fights and tunes
  must agree with them, checked on a 6502 emulator.
- **The Waystation website** still makes characters and lands Travel Stamps, so a
  Passport means the same thing on the website and on the cartridge.
- The C version (E1-E12) stays in the repository, tested, as a working reference.

## The EasyFlash

64 banks of 16 KB. Each bank is two 8 KB chips: ROML, at $8000-$9FFF, and ROMH, at
$A000-$BFFF (or at $E000-$FFFF in Ultimax mode). Two registers in the I/O area, both
write-only:

| Register | What |
|---|---|
| $DE00 | the bank, 0-63 |
| $DE02 | the mode: $05 Ultimax (as it boots: ROMH at $E000), $06 8 KB (ROML), $07 16 KB (ROML and ROMH), $04 off; add $80 for the LED |

And 256 bytes of RAM at $DF00-$DFFF, there whatever the bank or mode (while the I/O is
in). The cartridge's ROMs show only while $01 has LORAM and HIRAM set (`$37`); with
`$35` the CPU sees RAM there instead. The game sets the mode once, at boot (16 KB), and
only `assets.s` ever writes the bank.

**The boot** (`cart/boot.s`): at power-on the EasyFlash is in Ultimax mode, bank 0's ROMH
at $E000, so the reset vector is ours. The boot copies a few bytes to the EasyFlash's RAM
and runs them there (ROMH moves to $A000 the moment the mode changes): bank 0, 16 KB
mode, on to `start` (`cart/start.s`) in ROML, which sets the port (its value before its
direction: the other way round, every ROM, this code with it, goes out for a moment),
quiets the chips, and copies the resident engine from ROMH to RAM.

**The disk** (`cart/diskstart.s`): `LOAD"APB",8` and `RUN`. The program has the resident
engine in it, which it copies up to its place, and the KERNAL stays (its timers on, its
interrupts off) to load the assets.

## Memory

The game runs with `$01 = $35`: RAM everywhere but the I/O, no BASIC, no KERNAL. The
cartridge comes in only while an asset is copied out of it, the KERNAL only while one
loads from a disk (`cart/assets.s`).

| Address | Holds |
|---|---|
| $0000-$00FF | the zero page ([below](#the-zero-page)) |
| $0100-$01FF | the stack |
| $0200-$0FFF | buffers (on a disk, the KERNAL's own are at $0200-$03FF) |
| $1000-$7FFF | the resident engine, copied there at the start (`RESIDENT`), and its state (`BSS`) |
| $8000-$9FFF | the staging RAM: the asset fetched last ([Assets](#assets)) |
| $A000-$BFFF | RAM: a chapter, the map, a fight's state |
| $C000-$CFFF | VIC bank 3: the text screen ($C000), the view's screen ($C400), the view's characters ($C800) |
| $D000-$D7FF | our font (`tools/c64font.py`), in the RAM under the I/O, which the VIC sees |
| $D800-$DFFF | (RAM under the colour RAM, which the VIC sees): sprite shapes, 32 of them |
| $DF00-$DFFF | (I/O) the EasyFlash's RAM: the bank's shadow and the boot's mode switch |
| $E000-$FF3F | a story picture's bitmap (multicolour), its screen at $C400 |
| $FFFA-$FFFF | the 6502's NMI, reset and IRQ vectors, in RAM |

The VIC is in bank 3 ($C000-$FFFF) all the time: the text, the view, the font, the
pictures and the sprites are all there, so it never changes bank.

## The screen

The framed screen ([frames.md](frames.md)): the view on rows 0-15, multicolour (the
map's tiles, or a picture), with sprites; the frames on rows 16-24, hires text in our
font: the story log (columns 0-24), the party (rows 16-19, columns 26-39), the dice log
(rows 20-23, columns 26-39) and the command row (24).

The raster interrupt (`cart/split.s`) does it, twice a frame:

| Line | Sets | Then |
|---|---|---|
| 250 (under the screen) | the view: `$D018` its screen and characters, `$D016` multicolour (`$D011` bitmap mode for a picture) | the music, the keyboard, the sprites' first eight |
| 177 (just before row 16) | the frames: `$D018` = text screen $C000 and font $D000, hires, text mode | |

Only three registers change at the split, and each is written in the same cycles of
the line every frame, so the split doesn't jitter.

## Assets

Everything the game has but the resident engine (the font and tiles, pictures, sprites,
the story's chapters, tunes, code for one moment) is in **assets** of 8 KB, numbered
from 0. Game code asks for one with `asset_fetch` (A = the asset) and finds it staged in
RAM at $8000-$9FFF, to read there or copy on (`mem_copy`, `cart/copy.s`, under the I/O
too). Nothing runs from the cartridge: code in an asset runs from RAM, staged or copied.
No other module knows where an asset came from:

- **On the cartridge**, asset n is bank 1 + n/2, its ROML for n even, its ROMH for n
  odd, copied to the staging RAM with the cartridge in (`$01 = $37`: reads see the ROM,
  writes go to the RAM under it). Interrupts stay on. The bank's shadow (`ef_bank`, in
  the EasyFlash's RAM) is written before `$DE00`, since `$DE00` can't be read.
- **On a disk**, asset n is the file `ANN` (NN in hex), loaded there with the KERNAL
  (`$01 = $36`) from the device the game was loaded from. While it loads, the KERNAL's
  serial routines hold interrupts off at times, so a split may come late for a frame:
  assets are fetched between scenes.

`asset_fetch` remembers what's staged and doesn't fetch it again. Assets are linked at
$8000 (`cart/cart.cfg`, `cart/disk.cfg`), so the same bytes are the cartridge's chip and
the disk's file (with its load address).

## The zero page

Each module owns its part; nothing else touches it.

| Addresses | Owner | Use |
|---|---|---|
| $00-$01 | the CPU's port | $35 while the game runs, $37 in a bank call |
| $02-$0F | free | |
| $10-$17 | `text.s` | the string being printed ($10-$11), the log's column ($12), the word's length ($13), a row pointer ($14-$15) and the one under it, or its colours ($16-$17) |
| $18-$1B | `view.s` | where a tile goes ($18-$19), its colours ($1A-$1B) |
| $1C-$21 | `copy.s`, `assets.s` | a copy's source ($1C-$1D), destination ($1E-$1F) and length ($20-$21) |
| $22-$23 | free | |
| $24-$2F | scratch | arguments and counters (`zp_t0`...): any routine, between calls; never kept across a call |
| $30-$8F | free (the VM, the rules, the music will take theirs from here) | |
| $90-$FF | the KERNAL's, on a disk (while it loads) | |

The interrupt (`split.s`) uses no zero page at all.

## How the code is written

- **One job per file** in `cart/`: `boot.s` (the Ultimax boot), `start.s` and
  `diskstart.s` (each medium's start-up), `main.s` (the main program, the vectors),
  `assets.s` (fetching assets: the only module that knows the medium), `copy.s` (copying
  RAM), `screen.s` (the VIC and its graphics), `split.s` (the raster interrupt), `text.s`
  (the frames' text), `view.s` (the view's tiles), `demo.s` (A0's demonstration), and
  more as they come (`keys.s`, `sprites.s`, `password.s`, `vm.s`, `combat.s`, `music.s`).
  Assets are files of their own (`asset0.s`, ...).
- **No medium in the game's logic**: no `$DE00`, `$DE02` or KERNAL call outside
  `assets.s` (and the start-ups).
- **Every routine has a header**: what it does, what it takes (registers, zero page),
  what it gives back, what must be true before, and which registers and zero page
  it changes.
- **Branches**: a branch whose target might drift out of reach (-128..+127) is written
  as the opposite branch over a `jmp`. ca65 refuses one out of reach in any case.
- **Constants and addresses** live in `cart/hw.inc` (the chips), `cart/zp.inc` (the zero
  page) and `cart/mem.inc` (the memory map), never as bare numbers in the code.
- **Text** is ASCII in the source (`.byte "..."`, ca65's default), turned into screen
  codes as it's printed (`text.s`), so the same strings can come from the Quest Script
  compiler.

## The split's timing

The view's last line is 178; line 179 is a bad line, where the VIC stops the 6502 from
cycle 12 to fetch row 16's characters. So the three writes that change to the frames
(`$D018`, `$D016`, `$D011`) must land between line 178's last character (cycle 55) and
cycle 11 of line 179. The interrupt comes at line 176, waits in a 7-cycle loop for line
178, then counts cycles, so the writes land at cycles 56-62, 60-66 and 64-70 (line 179's
1-7), wherever in the loop line 178 is seen: inside the gap, so nothing shows. `make
test-cart` holds every frame to that, on the emulator's model of the timing (no sprite
may be on lines 176-178, which would steal cycles there). It still wants checking in
VICE's cycle-exact x64sc, and on a real C64.

## Saves: passwords

No disk, no flash writes: a trip is saved as a password, in the Passport's alphabet and
lines ([passport-spec.md](passport-spec.md)). The Passport carries the traveler between
trips; a **trip password** carries a trip at the start of its current chapter: the
Departure, the chapter, the ticket and seed, the trip's flags and counters, and the
traveler as they are, about the size of a Boarding Pass (four lines). The format will be
specified in [boarding.md](boarding.md) beside the pass, with a Python reference, before
it's written in assembly.

## Building and testing

`make cart` builds `build/apb.crt` (`cart/cart.cfg`, `tools/crt.py`) and
`build/apb-disk.d64` (`cart/disk.cfg`) from the same modules. `make test-cart` runs both
on a 6502 emulator (py65) that plays a C64 with an EasyFlash, or a disk drive
(`tests/cart/run_cart.py`): it boots in Ultimax mode from bank 0, banks on `$DE00`, maps
on `$DE02` and `$01`, keeps the I/O apart from the RAM under it, stops on any read of a
ROM the game must not touch, times every register access to its cycle, and fires the
raster interrupt at `$D012`'s line; for the disk, it answers the KERNAL's loads from the
`.d64`. It checks the split's timing, the graphics against the tools' own files, the
view, the frames and the story log. `--shot FILE` saves the screen as the VIC-II would
show it.

## Milestones

- **A0, the framework** (done): the cartridge boots, and so does the disk; the engine
  copies itself to RAM; assets are fetched from either; the raster split shows a map of
  tiles over the frames; the story log prints and scrolls.
- **A1, keys and the command row**: the keyboard matrix read in the interrupt, "-- more
  --", menus, typing a line.
- **A2, passwords**: the Passport and the Boarding Pass decoded and encoded in assembly,
  checked against `tools/passport/`.
- **A3, the story VM**: Quest Script's bytecode, chapters in banks, pictures.
- **A4, sprites and the fight**: the multiplexer, the battle map, the combat rules
  (checked against `tools/rules/combat.py`).
- **A5, music**: the player (`fe/c64/music.s`) moved over, tunes in banks.
- **A6, trip passwords**: saving and resuming a trip.
