# Passport spec v0

The portable character record. One logical format, three carriers:

| Carrier | Where |
|---|---|
| **Password** | Every retro build; works on real hardware and any emulator |
| **File** | Disk saves where available; modern builds |
| **Hub account** | Online; holds the full Legend |

The web **Passport Office** converts between carriers.

## Contents and bit budget (draft)

| Field | Bits | Notes |
|---|---|---|
| Format version | 4 | |
| Name | 40 | 8 chars from a 32-symbol alphabet |
| Race | 5 | |
| Class | 4 | |
| Level | 5 | 1–20 |
| XP toward next level | 7 | |
| Stats | 24 | 6 × 4 bits (0–15) |
| Skills / perks | 32 | Bitfield, v0 placeholder |
| Debt | 16 | |
| Equipped items | 60 | 6 × 10-bit registry IDs |
| Pack items | 60 | 6 × 10-bit registry IDs |
| Echoes | 96 | 8 × (10-bit ID + 2-bit state) |
| Flags | 8 | Verified, retired, etc. |
| Checksum | 16 | Catches typos |
| **Total** | **~377** | ≈ 76 base-32 characters |

76 characters is long for a password. Display it as four lines of 19 with a check
character per line so typos are caught where they happen. Options to trim later: shorter
names, item IDs that imply tier, fewer pack slots on retro builds.

## Registries

Items and Echoes live in **global, append-only registries**. IDs are never reused or
changed. Every Departure ships with the full registry; an engine that can't present an
item shows it as an Unidentified Relic and keeps it.

## Trust

- **Single-player**: accept cheating. It's your game.
- **Multiplayer**: the hub server is authoritative. Characters imported from a password are
  marked *unverified* until the hub replays or approves them.
- The checksum catches mistakes, not cheaters. Any key baked into a C64 binary can be read.
