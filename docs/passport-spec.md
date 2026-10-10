# Passport spec

The portable character record. One logical format, the same text everywhere; what changes
is how it travels ([Carriers](#carriers)):

| Carrier | Where |
|---|---|
| **QR code** | The everyday way: printed on a Passport or a Boarding Pass, shown on a phone, drawn on the C64's screen at a trip's end; scanned with a phone |
| **File** | A file the game reads at the boarding desk (an SD2IEC's `PASS`); modern builds |
| **Typed** | The old-school way, and the fallback: the lines, typed at the boarding desk |
| **Hub account** | Online; holds the full Legend |

The web **Passport Office** converts between carriers.

## Format version 2 (implemented in `core/src/passport.c`)

Version 2 is **variable length**: it stores only what a character actually has. A new
character's password is short; a level-100 legend's is long. Your Passport gets thicker as
your legend grows.

A Python reference implementation, written from this spec independently of the C, lives
in `tools/passport/passport.py`; the test suite's golden passwords come from it.

### Fields

Packed most-significant bit first, in this order.

**Fixed part (160 bits):**

| Field | Bits | Notes |
|---|---|---|
| Format version | 4 | `2`. Passports keep to 1-7: 8 starts a Boarding Pass ([boarding.md](boarding.md)), which carries a Passport's fields after its own |
| Name | 40 | 8 symbols from ` ABCDEFGHIJKLMNOPQRSTUVWXYZ-'.!?`, space-padded |
| Race | 5 | |
| Class | 4 | |
| Level | 7 | 1–100 |
| XP | 7 | 0–99, progress toward the next level |
| Stats | 42 | 6 × 7 bits (0–100): Might, Grace, Grit, Wits, Presence, Fate |
| Unspent stat points | 8 | |
| Unspent skill points | 8 | |
| Debt | 16 | |
| Flags | 7 | bit 0 verified, bit 1 retired, bit 2 tabletop, rest reserved |
| Tagged skills | 12 | one bit per skill |

**Counted lists (only what the character has):**

| List | Count | Each entry |
|---|---|---|
| Trained skills | 4 bits (0–12) | skill 4 bits + training 7 bits, in skill order, training > 0 |
| Powers | 4 bits (0–8) | power id 8 bits (1–255) + rank 7 bits (0–100), in slot order |
| Equipped items | 3 bits (0–6) | slot 3 bits + item id 10 bits (1–1023) |
| Pack items | 3 bits (0–6) | slot 3 bits + item id 10 bits |
| Echoes | 4 bits (0–8) | Echo id 10 bits + state 2 bits, oldest first |

**Then:** zero bits to a byte boundary; a **CRC-16/CCITT-FALSE** (poly 0x1021, init
0xFFFF) over all the bytes so far; zero bits to a multiple of 5.

### The password

- Alphabet: `0123456789ABCDEFGHJKMNPQRSTVWXYZ` (Crockford base 32: no I, L, O or U).
- Lines of **19 data symbols plus one check symbol**. The last line may be shorter (at least
  one data symbol plus its check). The check symbol is `sum(value[i] × (2i + 1)) mod 32`
  over the line's data. Odd weights mean any single wrong symbol changes it, so typos are
  caught on the line where they happen.
- Decoding is forgiving: lower case is fine, spaces, dashes and line breaks are ignored,
  `O` reads as `0`, and `I`/`L` read as `1`.
- Errors the decoder reports: wrong length, unknown symbol, line check (with line number),
  checksum, different version.
- Encoding refuses a character whose fields don't fit, rather than silently truncating.

### What's refused

Every decoder (the rules core, `core/src/passport.c`; the Python reference,
`tools/passport/`; the cartridge, `cart/passport.s`) refuses the same passwords, the same
way; `make test-python` and `make test-cart` hold them to it.

- **The wrong length**: more symbols than the longest there can be (149 for a Passport,
  163 for a Boarding Pass, 84 for a Travel Stamp), counted as they're read; a last line
  of one symbol; the bits running out before the fields, the padding and the CRC are all
  read; or 5 bits or more left after the CRC.
- **A checksum**: the CRC wrong, a padding bit that isn't 0; or a character no game has,
  whatever its CRC. A list longer than it can be (12 trained skills, 8 powers, 6 items
  equipped and 6 in the pack, 8 Echoes); a skill past the last or trained twice, a
  training of 0; a power 0; an item slot past the sixth or used twice, an item 0; an
  Echo 0. Reading stops at the first of these, as each entry is read: a skill or slot is
  judged when it's read, before what follows it; a training, power, item or Echo when its
  entry is whole. After the CRC: a level outside 1-100, XP of 100 or more, a stat, a
  training or a power's rank over 100.
- A Travel Stamp's lists hold 8 at most, refused as they're read.

A Boarding Pass is told from a Passport by its first symbol (the top 4 bits of its value:
8), so a game can take either at one prompt.

### How long

| Character | Symbols | Lines |
|---|---|---|
| New: 3 tagged skills, 1 item, 1 Echo | 55 | 3 |
| Longest possible: everything trained, 8 powers, 12 items, 8 Echoes | 149 | 8 |
| The longest Boarding Pass, carrying that | 163 | 9 |

A new character from the test suite:

```
4PB794AR0A0105AM7HDT
8V4000RD8000K60M2A4D
502008208GRN703
```

Long passwords are fine to type once in a while, but nobody should have to. For everyday
use: a QR code (on the printed sheet, or a phone's screen), a file on the SD card, an
account on modern clients.

## Carriers

The text is the same however it travels, so a scanned code, a file and a typed one all
go through the same decoder.

- **QR code.** The password's lines joined, no spaces, in QR's alphanumeric mode: our
  alphabet is part of it, so the code is the text itself, about 5.5 bits a symbol. A
  Boarding Pass fits a version 4 QR, a Travel Stamp a version 2 or 3 (low error
  correction). The line check symbols ride along (QR corrects errors itself; they cost 5%
  and keep one text for every carrier). The Waystation prints one on each Passport and
  Boarding Pass ([tabletop.md](tabletop.md)); the C64 draws the Travel Stamp's in its view
  at a trip's end, for a phone to scan back to the Waystation.
- **File.** On a disk, the boarding desk first loads `PASS` (a SEQ or PRG file of the
  text, any line breaks and spaces ignored) from the drive the game came from: on an
  SD2IEC, from the game's folder or its disk image. With no file, it asks for the lines.
  A Kung Fu Flash has no way for a running cartridge to read its card; a cartridge image
  with the pass written into it is a later option. The game never writes a file: saves
  are passwords.
- **Typed.** The lines, typed at the boarding desk, the old-school way: forgiving of case,
  spaces, dashes, `O` and `I`/`L`, and naming the line of a typo.

## Receipts and Travel Stamps

A Departure doesn't return a new Passport; it returns a **receipt** of what changed, which
is applied to the character as they are now. On retro platforms and at the table the
receipt travels as a short **Travel Stamp** password, as a QR code or typed. See
[boarding.md](boarding.md).

## Registries

Races, classes, skills, items and Echoes live in **global, append-only registries**, as
text files in `registry/` (see `registry/README.md`). IDs are never reused or changed.
Every Departure ships with the full registry; an engine that can't present an item shows
it as an Unidentified Relic and keeps it.

## Trust

- **Single-player**: accept cheating. It's your game.
- **Multiplayer**: the hub server is authoritative. Characters imported from a password are
  marked *unverified* until the hub replays or approves them.
- The checksum catches mistakes, not cheaters. Any key baked into a C64 binary can be read.
