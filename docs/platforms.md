# Platforms & engines

## Write once, play anywhere

The Infocom/SCUMM approach:

- **Quest Script**: a small language for rooms, people, dialogue, encounters, Echoes and
  loot. Compiled to one compact data file per Departure.
- **One small engine per platform** reads that file.

| Platform | CPU | Engine | Presentation in the spirit of |
|---|---|---|---|
| Modern PC | any | Reference engine (headless rules core + renderer) | — |
| DOS | x86 | Own engine | Gold Box |
| Commodore 64 | 6502 | Shared 6502 engine | Ultima |
| Apple II | 6502 | Shared 6502 engine | Wizardry, text-heavy |
| SNES | 65816 | Reuses much of the 6502 engine | 16-bit JRPG |
| Amiga | 68000 | Own engine | Eye of the Beholder |

The rules core is the same everywhere; presentation differs.

## Design to the C64, ship the C64 first

Design every system against C64 limits (64 KB RAM, 1 MHz, disk). The C64 is also the
first retro front end: its toolchain is already working, and if it fits the C64, it fits
everywhere. See [engine-plan.md](engine-plan.md).

## Lore

Each platform is a platform at the Waystation. "The C64 train leaves from Platform 6."

## Toolchain (to evaluate)

- Rules core in C for portability (cc65 / llvm-mos for 6502, vbcc for Amiga, Open Watcom
  or DJGPP for DOS), hot paths in assembly. SNES likely needs hand assembly.
- Quest Script compiler and the modern reference engine in a modern language (TBD).
