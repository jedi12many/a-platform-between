# Passport spec

The portable character record. One logical format, three carriers:

| Carrier | Where |
|---|---|
| **Password** | Every retro build; works on real hardware and any emulator |
| **File** | Disk saves where available; modern builds |
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
| Format version | 4 | `2` |
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

### How long

| Character | Symbols | Lines |
|---|---|---|
| New: 3 tagged skills, 1 item, 1 Echo | 55 | 3 |
| Longest possible: everything trained, 8 powers, 12 items, 8 Echoes | 149 | 8 |

A new character from the test suite:

```
4PB794AR0A0105AM7HDT
8V4000RD8000K60M2A4D
502008208GRN703
```

Long passwords are fine to type once in a while. For everyday use: disk saves on retro
machines, files and accounts on modern ones, and a QR code on printed sheets.

## Receipts and Travel Stamps

A Departure doesn't return a new Passport; it returns a **receipt** of what changed, which
is applied to the character as they are now. On retro platforms and at the table the
receipt travels as a short **Travel Stamp** password. See [boarding.md](boarding.md); the
stamp format comes with milestone E2.

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
