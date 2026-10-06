# Passport spec v0

The portable character record. One logical format, three carriers:

| Carrier | Where |
|---|---|
| **Password** | Every retro build; works on real hardware and any emulator |
| **File** | Disk saves where available; modern builds |
| **Hub account** | Online; holds the full Legend |

The web **Passport Office** converts between carriers.

## Format version 1 (implemented in `core/src/passport.c`)

Fields are packed most-significant bit first, in this order:

| Field | Bits | Notes |
|---|---|---|
| Format version | 4 | `1` |
| Name | 40 | 8 symbols from ` ABCDEFGHIJKLMNOPQRSTUVWXYZ-'.!?`, space-padded |
| Race | 5 | |
| Class | 4 | |
| Level | 5 | 1–20 in the rules; the format allows up to 31 |
| XP toward next level | 7 | |
| Stats | 24 | 6 × 4 bits (0–15): Might, Grace, Grit, Wits, Presence, Fate |
| Perks | 32 | Two 16-bit bitfields, v0 placeholder |
| Debt | 16 | |
| Equipped items | 60 | 6 × 10-bit registry IDs, 0 = empty |
| Pack items | 60 | 6 × 10-bit registry IDs, 0 = empty |
| Echoes | 96 | 8 × (10-bit ID + 2-bit state), oldest first; state 0 = unset |
| Flags | 7 | Bit 0 verified, bit 1 retired, rest reserved |
| **Payload** | **360** | exactly 45 bytes |
| CRC-16 | 16 | CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF) over the 45 payload bytes |
| Padding | 4 | zero |
| **Total** | **380** | 76 base-32 symbols |

### The password

- Alphabet: `0123456789ABCDEFGHJKMNPQRSTVWXYZ` (Crockford base 32: no I, L, O or U).
- Shown as **4 lines of 20**: 19 data symbols and one **check symbol** per line. The check
  symbol is `sum(value[i] × (2i + 1)) mod 32` over the line's 19 values. Odd weights mean
  any single wrong symbol changes it, so typos are caught on the line where they happen.
- Decoding is forgiving: lower case is fine, spaces, dashes and line breaks are ignored,
  `O` reads as `0`, and `I`/`L` read as `1`.
- Errors the decoder reports: wrong length, unknown symbol, line check (with line number),
  checksum, and newer version.
- Encoding refuses a character whose fields don't fit (rather than silently truncating).

Example (from the test suite):

```
2PB794AR0A0WZCD9K50J
0103RBRMG080G000000N
001G00000007ZR0E08GZ
2M0000000000001MSA0Y
```

80 characters is long. Retro builds should prefer disk saves where they exist and keep the
password as the universal fallback. Options to trim in a later version: shorter names, fewer
pack slots, perks as an index into a smaller table.

## Registries

Items and Echoes live in **global, append-only registries**. IDs are never reused or
changed. Every Departure ships with the full registry; an engine that can't present an
item shows it as an Unidentified Relic and keeps it.

## Trust

- **Single-player**: accept cheating. It's your game.
- **Multiplayer**: the hub server is authoritative. Characters imported from a password are
  marked *unverified* until the hub replays or approves them.
- The checksum catches mistakes, not cheaters. Any key baked into a C64 binary can be read.
