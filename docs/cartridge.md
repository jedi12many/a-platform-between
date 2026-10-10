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
quiets the chips, and copies the resident engine to RAM. Bank 0 is linked as one 16 KB
piece (`build/cart/apb.b00`): the start-up, then the resident engine, from ROML on into
ROMH, which 16 KB mode puts end to end, and the boot in ROMH's last page.

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
| $0200-$03FF | buffers (on a disk, the KERNAL's own) |
| $0400-$0FFF | a string of the story as it's expanded (`EXPAND_AT`) |
| $1000-$7FFF | the resident engine, copied there at the start (`RESIDENT`), and its state (`BSS`) |
| $8000-$9FFF | the staging RAM: the asset fetched last ([Assets](#assets)) |
| $A000-$B7FF | the chapter: the Departure's car being played (`CAR_AT`, 6 KB) |
| $B800-$BFFF | the Departure's depot (`DEPOT_AT`, 2 KB) |
| $C000-$CFFF | VIC bank 3: the text screen ($C000), the view's screen ($C400), the view's characters ($C800) |
| $D000-$D7FF | our font (`tools/c64font.py`), in the RAM under the I/O, which the VIC sees |
| $D800-$DFFF | (RAM under the colour RAM, which the VIC sees): sprite shapes, 32 of them |
| $DF00-$DFFF | (I/O) the EasyFlash's RAM: the bank's shadow and the boot's mode switch |
| $E000-$F3FF | a story picture's bitmap (multicolour, the view's 16 rows), its screen at $C400 |
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
| 250 (under the screen) | the view: `$D018` its screen and characters, `$D016` multicolour, `$D011` (bitmap mode for a picture), `$D021` (a picture's background) | the keyboard and the joystick (the music, with A5) |
| 176 (the view's row 15) | the frames' background, black: under a picture's lower bar, which the background doesn't touch | |
| 177 (just before row 16) | the frames: `$D018` = text screen $C000 and font $D000, hires, text mode | |

Only three registers change at the split (the background before it, under the view's
black bar), and each is written in the same cycles of
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

**The assets**: asset 0 is the screen's graphics; asset 1 is code, a trip's end (the
receipt, the Travel Stamp, its QR code: `receipt.s`, `stamp.s`, `qr.s`, `qrview.s`),
linked at $8000 and run there once it's staged: nothing else is fetched while it runs;
assets 2 and 3 are code too, a fight: asset 2 (the rules, `combat.s`; the battle,
`battle.s`; the battle screen, `tactics.s`) staged and run the same way, and asset 3 (the
fight itself, `fight.s`, and its words, `fightext.s`) staged first and copied on to
`EXPAND_AT`, $0400, and run there: the story expands no text while it fights. A
Departure's depot is asset 4, its car k (a chapter) asset 5 + k, and its pictures the
assets after the cars (`tools/cart/departure.py`, from `qsc.py build --split`): the
file's length in 2 bytes, then the file (the depot's with the asset of its first picture
between). The VM copies the depot to $B800 and the car it's in to $A000, so the staging
RAM is free again.

**The player's pass, on a disk**: before it asks for typing, the boarding desk reads the
file `PASS` from the game's disk, if there is one (`pass_file`, `assets.s`): a byte at
a time with the KERNAL's OPEN and CHRIN (`PASS,P,R`), never LOADed, so a long file can't
run past the desk's buffer, and only so much of it is kept. Printable ASCII stays,
PETSCII's capitals become ASCII's, anything else (a load address) a space. A pass that
reads boards the traveler with no typing; one that doesn't is said to ("Line 2 of it has
a typo"), and the desk asks for the lines. A cartridge has no file: it always asks.

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
| $22-$23 | `command.s` | the line being typed |
| $24-$2F | scratch | arguments and counters (`zp_t0`...): any routine, between calls; never kept across a call |
| $30-$35 | `password.s` | the text being read or written ($30-$31), a field's value ($32-$33), its bits ($34), a line's check ($35) |
| $36-$37 | `number.s` | the number being written |
| $38-$39 | `rules.s` | a rule's working number |
| $3A-$3F | `vm.s`, `depot.s`, `expand.s` | the next byte of code ($3A-$3B), the string being expanded ($3C-$3D), where its text goes ($3E-$3F) |
| $40-$41 | `qr.s`, `qrview.s` | a module's place in the QR code, or a byte of the view's bitmap |
| $42-$45 | `fight.s`, `fightext.s` (in a fight) | the encounter's record, a foe's name |
| $46-$8F | free (the music will take its from here) | |
| $90-$FF | the KERNAL's, on a disk (while it loads) | |

The interrupt (`split.s`) uses no zero page at all.

## How the code is written

- **One job per file** in `cart/`: `boot.s` (the Ultimax boot), `start.s` and
  `diskstart.s` (each medium's start-up), `main.s` (the main program, the vectors),
  `assets.s` (fetching assets: the only module that knows the medium), `copy.s` (copying
  RAM), `screen.s` (the VIC and its graphics), `split.s` (the raster interrupt), `text.s`
  (the frames' text), `view.s` (the view's tiles), `keys.s` (the keyboard), `command.s`
  (the command row: waiting for keys, "-- more --", menus, typed lines), `password.s`
  (passwords' symbols, lines, bits and CRC), `passport.s` (the Passport's and the
  Boarding Pass's fields), `desk.s` (the boarding desk), `number.s` (numbers as text),
  `play.s` (the game: the desk, the trip, the desk again), `depot.s` (a Departure's depot
  and cars, loaded and checked), `vm.s` (the story VM), `expand.s` (the story's strings),
  `reward.s` (items, XP, Debt, Echoes, the receipt), `rules.s` (the dice, checks, health,
  XP), `dice.s` (the dice log), `party.s` (the party frame), `picture.s` (the story's
  pictures), `receipt.s` (a trip's end), `stamp.s` (the Travel Stamp), `qr.s` (a QR
  code), `qrview.s` (a QR code in the view), `combat.s` (the combat rules), `battle.s`
  (the battle), `tactics.s` (the battle screen), `fight.s` (a fight, from its encounter),
  `fightext.s` (a fight in words), and more as they come (`music.s`). The registry's names are generated into `build/cart/names.s`
  (`tools/registry/registry_asm.py`), never written by hand.
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

## The view

The battle map (and, with E13, rooms) is a grid of **squares of 16 x 16 pixels**, each a
tile of 2 x 2 multicolour characters: 20 squares across and 8 down fill the view's 40 x
16 characters (`cart/view.s`). A square's characters are at twice its column and twice
its row, so every place is worked out with shifts, never a multiplication. The tiles are
the eight of the rules' terrain (open, wall, pit, rough, cover, hazard, high ground,
exit), flat, in `tools/battlegfx.py --cart16`: 2 KB of characters (0 blank, each tile's
four, each tile's four with the reach dot, each tile's four with the cursor: a bracket at
each corner) and a 128-byte table (each tile's 4 characters and 4 colours, then its 4
marked ones, then its 4 with the cursor), in asset 0. The cursor is drawn in the map's
own characters, its colour the square's colour RAM (yellow to move, red to aim), so it
needs no sprite.

A figure is the C version's body, a sprite of 24 x 21: centred on its square across
(`FIGURE_DX`, -4) and standing on it, its feet near the square's foot and its head over
the square above (`FIGURE_DY`, -7), so figures overlap the scenery behind them. That
also keeps every figure clear of the split's lines, 176-178 (`cart/mem.inc`; `make
test-cart` checks it). A fight has eight fighters at most, so fighter n is sprite n and
nothing is multiplexed. With no second sprite for the C version's hires outline, the
outline is drawn into the body (`battlegfx.py`'s `outlined`), in the sprites' first
shared colour, black on the cartridge. The 16 looks' bodies and fallen bodies, 32
shapes, are in asset 0 and copied to $D800 at the start.

## Keys

The game reads the keyboard itself (`cart/keys.s`), once a frame from the raster
interrupt, on either medium: CIA 1's matrix, a row at a time. Each key newly down goes
into a buffer of 8, as ASCII (capitals with SHIFT), or a code for RETURN, DEL, RUN/STOP
and the cursor keys (`KEY_` in `cart/mem.inc`); `key_get` takes the next. A joystick in
port 1 reads like keys (it shares the matrix's columns). The one in port 2 is read first,
on port A with no row selected: its directions as the cursor keys (and `KEY_` codes for
the diagonals), repeating while held, and its button as RETURN; while it's pushed, the
matrix isn't read (it pulls port A's lines low, which would read as keys).

The command row (`cart/command.s`), row 24, is where the game waits for keys:

- `key_wait`: a key, with a cursor blinking where the next character would go.
- `-- more --`: before the story log scrolls, if its top row was printed since the last
  key (7 rows over the bottom one), it waits for a key first, in reverse on the command
  row. So nothing goes off the top unread, and a page is 8 rows.
- `menu_ask`: a digit from 1 to the menu's count; the answer goes into the log ("> 2").
- `line_ask`: a line typed on the command row after "> ", DEL to take one back, RETURN
  to end it; then into the log, "> " and all, so the log keeps everything said.

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

## Passports and Boarding Passes

The traveler is kept in RAM as a record (`cart/char.inc`), filled from what the player
types at the boarding desk (`cart/desk.s`, the C desk's flow and words): a Boarding Pass,
or a Passport alone, a line at a time, then a blank line. A line the wrong length, or one
with a typo, is asked for again by its number.

`cart/password.s` reads a password the forgiving way the spec says (small letters,
spaces, dashes, O for 0, I and L for 1), checks each line's check symbol, and keeps the
bits; it writes bits back as lines of 19 symbols and their check; and it has the CRC-16.
`cart/passport.s` reads a Passport's or a pass's fields into the record (and the pass's
own: Departure, ticket, seed, Rewind), checks the padding and the CRC, and writes a
Passport from the record, refusing a field too big for its bits. It takes everything the
reference does, every list full (215 symbols).

`tests/cart/test_passwords.py` holds them to the Python reference
(`tools/passport/`): random travelers with every field anywhere in its bits, and passes,
must decode to the reference's fields and encode to its text, symbol for symbol; typed
the forgiving way they read the same; damaged ones (a symbol changed, one not in the
alphabet, a line gone, two swapped, the end cut off) are refused as the reference refuses
them, a typo on the line it says.

## Saves: passwords

No disk, no flash writes: a trip is saved as a password, in the Passport's alphabet and
lines ([passport-spec.md](passport-spec.md)). The Passport carries the traveler between
trips; a **trip password** carries a trip at the start of its current chapter: the
Departure, the chapter, the ticket and seed, the trip's flags and counters, and the
traveler as they are, about the size of a Boarding Pass (four lines). The format will be
specified in [boarding.md](boarding.md) beside the pass, with a Python reference, before
it's written in assembly.

## Pictures

The story's pictures are the C64 version's (`tools/c64pic.py`: 160 x 96, multicolour
bitmap, each cell the background and three colours of its own), shown on the view's rows
2-13 by `cart/picture.s`, with a black bar of two rows over and under. The bars' pixels
are all `%11`, colour RAM black, so they never show the background: the split can change
the background to the frames' black while the lower bar is drawn (line 176), and the
cycle-counted writes at line 178 stay as they were. Each picture is an asset after the
cars (`tools/cart/departure.py`: the bitmap's 12 rows, the cells' screen colours, their
colour-RAM colours, the background; 4801 bytes); the depot's asset says which asset is
the first. Showing one blacks the view, puts the bitmap's mode on, and copies the picture
in: a frame or two of black, never a torn picture. A picture with no asset (no PNG when
the Departure was built) or the wrong length leaves the view as it was.

## The story VM

`cart/vm.s` plays a Departure's bytecode as the C engine's `vm/vm.c` does
([vm-spec.md](vm-spec.md)): the same instructions, the same rules (`rules.s`: the dice,
checks, skills, health, XP), the same text, the same receipt. `play.s` opens the depot,
seats the traveler at the boarding desk, boards them, and runs the trip; a story's
paragraph, chapter title, menu or "(press a key)" goes to the story log as the C64
version prints it (`fe/c64/c64.c`), a check's roll to the dice log, and the traveler,
their health a bar of five, to the party frame.

Nothing in an image is trusted. `vm_open` checks the depot as `load_depot` does, each car
is checked as it loads (its header, its sizes), and every operand as it's used: a jump
inside the code, a string, flag, var, item, Echo or rating that exists, a string that
ends inside its car, pairs that are in the table and nest no deeper than 16. (The C
engine also walks a whole car once when it loads; the cartridge finds the same faults when
it reaches them.) A fault stops the VM with vm.c's words: "The train has derailed: bad
jump 1:24". A runaway (20000 instructions without a menu) stops it too.

At a trip's end, the receipt and the Travel Stamp, as the C64 version prints them
(`receipt.s`, `stamp.s`), and the stamp's QR code in the view (`qr.s`, `qrview.s`): the
stamp's text in alphanumeric mode, error correction level L, the smallest of versions 1
to 4 it fits (21 to 33 modules), mask 0 (any reader takes it; choosing the mask by the
standard's penalty is an encoder's nicety). It's drawn in hires, black modules on a white
square with a quiet zone of 4 modules, 4 pixels a module if it fits, else 3. The view
goes back to the platform's map at the desk.

A fight (`FIGHT`) is played as the C64 version plays it (`client/tactics.c` on
`core/src/battle.c`): `fight.s` checks the encounter's record as it reads it (as vm.c's
`encounter_ok` does, but when the fight comes: a bad one stops the VM, "bad encounter")
and sets up the battle; `battle.s` plays it, the same as `core/src/battle.c`, event for
event; `tactics.s` shows it and asks for the traveler's turns: the map in the view, the
reach marks, the cursor, the command bar (Move, Aim, Guard, Wait, Flee, Quick, Done) on
the command row, keys or the joystick; `fightext.s` tells it in `client/battle_text.c`'s
words, each roll in the dice log. After it, the story's tune and its picture come back.
The Deep Yards (`FIGHT_YARD`, `PICK`) stop the VM ("no yards yet").

Until the later milestones: a tune is only a record for the tests (`[music
concourse]`, `[music battle]`, as the C64 version's transcripts have them; so is each
picture shown, `[picture pic02]`; and each prompt in a fight, `[Kestrel: choose.]`).

## Building and testing

`make cart` builds `build/apb.crt` (`cart/cart.cfg`, `tools/crt.py`) and
`build/apb-disk.d64` (`cart/disk.cfg`) from the same modules. `make test-cart` runs both
on a 6502 emulator (py65) that plays a C64 with an EasyFlash, or a disk drive
(`tests/cart/run_cart.py`): it boots in Ultimax mode from bank 0, banks on `$DE00`, maps
on `$DE02` and `$01`, keeps the I/O apart from the RAM under it, stops on any read of a
ROM the game must not touch, times every register access to its cycle, and fires the
raster interrupt at `$D012`'s line; for the disk, it answers the KERNAL's loads from the
`.d64`. Keys go in through the emulated keyboard matrix, from a choices file
(`tests/cart/*.choices`, an answer a line; "-- more --" is answered by itself), and the
story log, read as it scrolls, with each record (a roll, a picture, a tune), must match
its reviewed transcript (`tests/cart/*.expected`; `--update` writes it), the same from
the cartridge and the disk. Each route must also tell the story the C64 version (the C
engine) tells, word for word and roll for roll (`--c64`): *The Fare* by
`tests/c64/fare-edge.expected`, and the desk's route and the fight's (`fare-fight`, into
Lost Property: a Move, a Wait, a Wait refused, an Aim, then Quick) by the C64 program playing them there and then
(`tests/c64/run_c64.py`). A choices line `joy right` or `joy fire` pushes the joystick in
port 2 instead (the C64's run of the route has the keypad's key for it). It checks the split's timing every frame, the graphics
against the tools' own files, the view (the map at the desk; at the end, the last picture
as `tools/c64pic.py` converts it), the frames (the party, the last roll), that every
paragraph is wrapped at 25 as the rule says, that nothing scrolled off unread, and that no
figure's sprite reaches the split's lines. The party's health is checked against the
rules and the fights' words (what the attacks say they took). `--shot-at RECORD FILE`
saves the screen when a record is made: `build/cart-fight-shot.png`, the fight as Kestrel
aims.
A trip that ends shows its Travel Stamp's QR code: its modules must be the `qrcode`
library's for the same text, and OpenCV, reading the view as the VIC shows it, must get
the stamp back (`segno` isn't the reference: it adds a byte the standard doesn't, when the
data's terminator ends on a byte). Disks with a `PASS` file (`tests/cart/kestrel.pass`,
`typo.pass`) board from it, or say why not. `tests/cart/test_ending.py` checks the
stamp encoder against `tools/passport/stamp.py` on random receipts, and QR codes of every
version. `--shot FILE` saves the screen as the VIC-II would show it.
`tests/cart/test_damage.py`
breaks bytes of the depot, the cars and the pictures and plays them (and, with `--fights`,
of the fight's encounter, playing into the fight): the VM must stop cleanly or play on,
and never run anything but its own code. `tests/cart/test_battle.py` holds the fight's
rules and battle to the references (below, A4).

## Milestones

- **A0, the framework** (done): the cartridge boots, and so does the disk; the engine
  copies itself to RAM; assets are fetched from either; the raster split shows a map of
  tiles over the frames; the story log prints and scrolls.
- **The 16-pixel grid** (done): the view's squares 2 x 2 characters, 20 x 8 of them.
- **A1, keys and the command row** (done): the keyboard matrix read in the interrupt,
  "-- more --", menus, typing a line.
- **A2, passwords** (done): the Passport and the Boarding Pass decoded and encoded in
  assembly, checked against `tools/passport/`; the boarding desk.
- **A3a, the story VM** (done): Quest Script's bytecode in assembly, chapters as
  assets, the story told as the C64 version tells it.
- **A3b, pictures** (done): the story's pictures in the view.
- **A3c, the receipt** (done): the trip's end, the Travel Stamp as lines and as a QR
  code, a disk's `PASS` file; a pass's Rewind (in A3a's VM).
- **A4, the fight** (done): the combat rules (checked against `tools/rules/combat.py`),
  the battle (against `core/src/battle.c`'s reviewed logs and random battles), the battle
  screen, the joystick, `FIGHT` in the VM. (No multiplexer: a fight's eight fighters are
  the VIC's eight sprites. The Deep Yards come later.)
- **A5, music**: the player (`fe/c64/music.s`) moved over, tunes in banks.
- **A6, trip passwords**: saving and resuming a trip.
