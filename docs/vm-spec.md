# Story VM and Departure image spec (v0)

How a compiled Departure is laid out, and how the Story VM runs it. Audience: whoever
writes the compiler (`tools/qsc/`), the VM (`vm/`) or a platform front end.

> **Status:** v0. The compiler (`tools/qsc/`) writes this format, and its verifier
> (`tools/qsc/image.py`) checks it; `qsc dump FILE.apd` disassembles an image. Byte layouts
> may change until E1 ships; after that, changes bump the image version.

## Principles

1. **The compiler does the work.** Parsing, name resolution, checks, compression and
   layout all happen on a PC. The VM is a small loop.
2. **The VM never trusts an image.** Every operand is bounds-checked when it is used.
   A bad image stops the VM with an error; it never reads or writes outside its buffers.
   A load-time verifier runs the same checks up front for friendlier errors.
3. **Same results everywhere.** No floating point, no host-dependent behavior. Playthrough
   transcripts must match on every platform.
4. **All multi-byte numbers are little-endian** (native on the 6502, x86 and in
   WebAssembly; the 68000 Amiga and the 65816 SNES front ends read them byte by byte).

## The image

A Departure image is a **depot** (loaded once, stays in memory) plus one **car** per
chapter (loaded one at a time). On a PC they sit in one `.apd` file; on a C64 disk each is
its own file (`DEPOT`, `CAR00`, `CAR01`, ...), so the loader stays trivial.

### `.apd` container

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | magic `APD1` |
| 4 | 2 | depot length |
| 6 | 1 | car count (1..64) |
| 7 | 1 | reserved, 0 |
| 8 | 2 × cars | each car's length |
| … | | depot bytes, then each car's bytes, in order |

### Depot

| Field | Size | Notes |
|---|---|---|
| magic | 2 | `DP` |
| image version | 1 | `0` for v0 |
| kind | 1 | `0` official, `1` branch |
| departure id | 2 | |
| season | 1 | 0 for branch |
| realm TL, ML | 1 + 1 | |
| level min, max | 1 + 1 | |
| flag count | 2 | ≤ 512 |
| var count | 1 | ≤ 128 |
| scene count | 2 | ≤ 1024 |
| start scene | 2 | |
| image hash | 2 | CRC-16/CCITT-FALSE over the depot (with this field zeroed) followed by every car in order; saves record it |
| title | 1 + n | length-prefixed ASCII, ≤ 40 |
| var initial values | var count | |
| scene directory | 3 × scenes | per scene: car (1), offset into that car's code (2) |
| BPE pair table | 1 + 2 × pairs | pair count (≤ 128), then two bytes per pair |
| picture names | 1 + … | count, then length-prefixed names; index = picture id |
| encounters | 1 + … | count (≤ 32), then each one's length (2) and record; index = encounter id |

#### Encounters

A battle map and its foes, everything a fight needs (rules: [combat.md](combat.md)). The
whole record is checked when the depot loads: sizes, squares, positions (inside the map,
on ground you can stand on, no two fighters on one square) and every number's range.

| Field | Size | Notes |
|---|---|---|
| width, height | 1 + 1 | 1–16, 1–10 |
| squares | (w × h + 1) / 2 | row by row, two to a byte, high nibble first: 0 open, 1 wall, 2 pit, 3 rough, 4 cover, 5 hazard, 6 high ground, 7 exit |
| starts | 1 + 2 each | 1–4 travelers' squares: x, y |
| foes | 1 + 18 each | 1 to 8 − starts. Each: x, y, health, grace, dodge, armor, ward, soak, speed, attack, damage, damage type (0–4), ranged (0/1), power (0/1), area (0–4), weakness (0–4, or 255 for none), behavior (0 charge, 1 shoot, 2 guard), coward (0/1) |
| foe names | 1 + 1–20 each | one per foe, in the same order: a length, then the name in ASCII (from the bestiary, "Rust-guard"), for the battle screen. The record must end exactly here |

### Car

| Field | Size | Notes |
|---|---|---|
| magic | 2 | `CR` |
| car index | 1 | must match its place in the image |
| title string | 2 | string id of the chapter title, `0xFFFF` for an untitled chapter |
| code length | 2 | |
| string count | 2 | ≤ 1024 |
| code | code length | bytecode |
| string offsets | 2 × strings | offset of each string from the start of string data |
| string data | rest | compressed strings, each ending in `0x00` |

A car is at most 6 KB in total: one fits in a C64 at a time, beside the game ([c64.md](c64.md)).

## Text encoding

Strings are ASCII `0x20`–`0x7E`, plus:

| Byte | Meaning |
|---|---|
| `0x00` | end of string |
| `0x01` | insert character name |
| `0x02` | insert race name |
| `0x03` | insert class name |
| `0x04` | insert Debt |
| `0x05` *n* + 1 | insert variable *n* (stored plus one, so it's never `0x00`) |
| `0x06` | insert level |
| `0x0A` | line break inside a paragraph (from `|` lines) |
| `0x80`–`0xFF` | a byte pair (see below) |

**Byte-pair compression.** Code `0x80 + i` stands for the two bytes in entry *i* of the
depot's pair table. Entry *i* may only contain bytes below `0x80 + i`, so expansion always
terminates; the compiler also keeps expansion depth ≤ 16, and the decoder refuses deeper
nesting. The decoder needs a 16-byte stack and nothing else.

Text is stored as ASCII. Front ends convert to their own character set (PETSCII on the
C64) when drawing; string literals in C are not used for game text.

## VM state

| State | Size | Notes |
|---|---|---|
| current car, pc | 1 + 2 | |
| current scene | 2 | |
| flags | 64 bytes | 512 bits; scene `visited` and once-only choice flags are allocated by the compiler from the same pool |
| vars | 128 bytes | |
| expression stack | 16 × int16 | |
| menu | 9 × (string id 2, target 2) | |
| character | `apb_character` | a working copy of the boarding snapshot; the VM never writes a Passport |
| receipt | small | every change made to the character (XP, Debt, items, Echoes), handed to the front end at `END`; see [boarding.md](boarding.md) |
| rng | 2 | `apb_rng` |
| rewards this Departure | 3 × 32 + 2 | (car, offset) of each reward instruction already paid; items given count, for Branch Line limits |

## Instructions

One opcode byte, then fixed operands. `u8`/`u16`/`s8`/`s16` are 1- or 2-byte operands.
"Pop"/"push" refer to the expression stack. Jump targets are offsets within the current
car's code.

### Flow

| Op | Hex | Operands | Effect |
|---|---|---|---|
| `HALT_ERR` | 00 | — | Stop with "bad image" (catches running into zeroed memory) |
| `JMP` | 01 | u16 addr | Jump |
| `JZ` | 02 | u16 addr | Pop; jump if zero |
| `GOTO` | 03 | u16 scene | Enter a scene (loads its car if needed) |
| `SWITCH4` | 04 | u16 × 4 | Pop 0..3; jump to that address (used after `CHECK`) |
| `END` | 05 | u8 outcome | End the Departure: 0 complete, 1 failed; hand the receipt to the front end |

### Text and presentation

| Op | Hex | Operands | Effect |
|---|---|---|---|
| `TEXT` | 10 | u16 string | Print a paragraph |
| `PICTURE` | 11 | u8 picture | Show a picture |
| `PAUSE` | 12 | — | Wait for a key |
| `CHAPTER` | 13 | — | Show the current car's chapter title |

### Menus

| Op | Hex | Operands | Effect |
|---|---|---|---|
| `MENU_CLEAR` | 18 | — | Empty the menu |
| `OPTION` | 19 | u16 string, u16 addr | Add an option (error if more than 9) |
| `MENU` | 1A | — | Show the menu, wait for a pick, jump to its address. Error if empty. |

A scene compiles to: entry code (text, commands), `SET visited`, then a **menu block**:
`MENU_CLEAR`, conditional `OPTION`s, `MENU`. A choice body ends with `JMP` back to the
menu block. Once-only choices are a compiler-allocated flag tested before `OPTION` and set
at the start of the body. The VM has no special support for either.

**Scene layout.** Each scene's code starts with a 2-byte **menu offset** (data, not an
instruction): where its menu block begins, relative to the scene, or `0xFFFF` for a scene
with no menu (one that always moves on). Entering a scene (`GOTO`, or starting the
Departure) begins executing just after those two bytes.

How the compiler lays a scene out:

```
u16 menu offset
FLAG chapter; NOT; JZ +; SET chapter; CHAPTER      (titled chapters: the first entry shows the title)
entry code                                         (text, commands, ifs, checks)
SET visited                                        (before every way out of the entry code,
                                                    only for scenes some 'visited' tests)
MENU_CLEAR
  [FLAG once; NOT; JZ skip]  [condition; JZ skip]  OPTION label, body
  ...
MENU
body: [SET once]  statements  JMP menu             (or GOTO scene, or END)
```

Compiler flags are numbered after the author's: one per scene that a `visited` condition
tests, one per titled chapter, one per once-only (`*`) choice. All count toward the 512.

**Saving** is only allowed while waiting in `MENU`. A save records the scene, not the pc.
Loading jumps straight to the scene's menu block (scene directory offset + menu offset),
which rebuilds the menu from the saved flags, so it comes back exactly as it was without
re-running the scene's entry text or commands.

### Expressions

| Op | Hex | Operands | Push |
|---|---|---|---|
| `PUSH8` | 20 | u8 | the value |
| `PUSH16` | 21 | s16 | the value |
| `FLAG` | 22 | u16 flag | 1 if set |
| `VAR` | 23 | u8 var | its value |
| `HAS` | 24 | u16 item | 1 if carried |
| `ECHO` | 25 | u16 echo, u8 default | its state, or `default` if unset |
| `RATING` | 26 | u8 rating | a stat (0–5) or a skill's rating (16–27, via `apb_skill`) |
| `LEVEL` | 27 | — | character level |
| `RACE` | 28 | — | race number |
| `CLASS` | 29 | — | class number |
| `EQ` `NE` `LT` `LE` `GT` `GE` | 30–35 | — | pop b, pop a, push a ⋄ b |
| `AND` `OR` | 36–37 | — | pop b, pop a, push logical result |
| `NOT` | 38 | — | pop a, push !a |
| `CHECK` | 39 | u8 rating, u8 tn | d100 + the rating (numbered as for `RATING`) against the TN (50–250): pushes 0 fail, 1 cost, 2 success, 3 crit (via `apb_check`) |
| `FIGHT` | 3A | u8 encounter, u8 surprise | plays the encounter (surprise: 0 none, 1 the foes go first, 2 the travelers do) with the battle engine (`core/src/battle.c`): the traveler takes the first start, with their health now and the first weapon they have equipped; the HAL shows the map and events and asks for each turn (`hal_battle_begin`, `_event`, `_turn`, `_end`). Pushes 0 won, 1 lost, 2 fled; health carries on, and a lost fight the story carries on from leaves 1. The compiler follows it with a `SWITCH4` whose fourth slot is never taken |

`visited` compiles to `FLAG` on the scene's compiler-allocated flag.

### Changing state

| Op | Hex | Operands | Effect | Branch Lines |
|---|---|---|---|---|
| `SET` | 40 | u16 flag | set flag | yes |
| `CLR` | 41 | u16 flag | clear flag | yes |
| `LET` | 42 | u8 var | pop into var (clamped 0..255) | yes |
| `ADD` | 43 | u8 var, u8 n | add, saturating at 255 | yes |
| `SUB` | 44 | u8 var, u8 n | subtract, saturating at 0 | yes |
| `GIVE` | 48 | u16 item | add to pack (no room: lost-and-found message); pays once per trip | tier ≤ 3, limited count |
| `TAKE` | 49 | u16 item | remove if carried | yes |
| `XP` | 4A | u8 n | `apb_gain_xp`; pays once per trip | ignored above the level band |
| `DEBT` | 4B | u8 mode, u16 n | mode 0 set, 1 add, 2 subtract (saturating); pays once per trip | refused |
| `ECHO_SET` | 4C | u16 echo, u8 state | `apb_echo_set` | refused |
| `HEAL` | 4D | u8 n | health + n, up to the most; 255 heals fully | yes |

"Pays once per trip": the VM remembers (car, offset) of each `GIVE`, `XP` and `DEBT` it
has run since boarding, up to 32 (`APB_VM_REWARD_SITES`), and passes over one it has run
before. The compiler allows at most 32 per Departure, so the list never fills; if a
damaged image has more, the extras pay nothing. This is what makes the compiler's reward
manifest a true bound.

"Refused" means the VM stops with an error if a Branch Line image contains it; the
verifier rejects such an image at load time, and the compiler never emits it.

Unassigned opcodes are errors. There are deliberately no opcodes that set name, race,
class or stats: characters are made by the character creator, never by a Departure.

## Runtime checks

The VM stops with an error (and the front end shows *"The train has derailed: error N at
car:pc"*) if any of these fail:

- pc and every jump target inside the current car's code;
- string, scene, flag, var, picture, item and Echo ids in range;
- expression stack never over- or underflows;
- menu not over 9 options, never empty at `MENU`;
- `GOTO` loads a car whose index and magic match;
- byte-pair expansion depth ≤ 16;
- privileged opcodes absent from Branch Line images;
- no more than 20,000 instructions between one menu and the next (or the end): a damaged
  or hostile image can't hang the machine.

## The verifier

Runs when an image loads, before anything is shown. It walks every car's code linearly,
decoding each instruction (skipping the 2-byte menu offset at each scene start listed in
the scene directory), and applies the runtime checks to every operand, plus:

- every jump target lands on an instruction boundary (modern builds; the C64 build skips
  this one and relies on the runtime checks, since it needs a 2 KB bitmap);
- scene starts in each car appear in increasing order, so the walk can follow the
  directory without searching it;
- the depot's pair table obeys the "only lower codes" rule;
- every string, once expanded, holds only printable ASCII, insert codes and line breaks,
  and its variable inserts are in range;
- every scene's menu offset points at a `MENU_CLEAR`;
- the image hash matches (modern builds: it means reading every car once at boarding,
  which on a C64 disk would take minutes; the C64 checks each car as it loads instead).

The reference implementation is `vm/vm.c`; `tools/qsc/image.py` applies the same rules
in Python.

## Saves

A save is made at a menu: the front end's `hal_menu` returns `APB_MENU_SAVE`, the VM writes
the file `SAVE` through `hal_save`, says "Saved." and shows the menu again.
`apb_vm_resume` reads it back and shows that menu. *The Fare* saves in about 100 bytes; the
most is 768 (`APB_VM_SAVE_MAX`). On the C64 a save is one small file on the Departure's
disk. Little-endian, version 1:

| Field | Size |
|---|---|
| magic, version | 3: `41 53 02` (version 2 added health) |
| departure id, image hash | 2 + 2: a save only loads into the image that made it |
| car, menu offset | 1 + 2: the `MENU` instruction to show again |
| menu entries | 1 + 4 each: string id, target |
| expression stack | 1 + 2 each |
| flags | one byte per 8 of the image's flags |
| vars | one byte per variable |
| rng | 2 |
| Debt at boarding, health now, Branch Line gives | 2 + 1 + 1 |
| rewards already paid | 1 + 3 each: car, offset |
| receipt so far | departure 2, ticket 4, outcome 1, XP 2, Debt paid 2, added 2, items gained and lost (1 + 2 each), Echoes (1 + 4 each: id, state, state at boarding) |
| character | 1 + the working copy as a Passport password |
| CRC-16 | 2, over everything before it |

Like an image, a save is never trusted. Its CRC, magic, image, every count, the car, the
menu (it must be a `MENU` instruction, and under full checks an instruction boundary), each
option's string and target, the dice state (never 0), and the character (a valid Passport)
are all checked before play resumes; anything wrong refuses the save.

## Branch Line ledger

When a Branch Line ends, its flags and vars are stored under its departure id in the
player's Branch Line ledger (save data on modern platforms; a file on the C64 disk). The
Passport is never touched.

Not in v0: commands for a Branch Line to read a ledger entry back (its own, or an earlier
episode's), so community series can remember previous episodes.
