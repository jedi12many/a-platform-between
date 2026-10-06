# Engine plan

How we get from the rules core we have to Departures playable on a terminal, a
Commodore 64, and eventually every platform on the list.

## The shape of it

Five layers. Only the bottom one changes between platforms.

```
  Quest Script source (.qs)            written by us, in plain text
          │  qsc: the compiler (Python, runs on our PCs)
          ▼
  Departure image (.apd)               bytecode + compressed text, split into "cars"
          │
  ┌───────▼────────────────────────────────────────────────┐
  │ Story VM          runs the bytecode: scenes, choices,  │  portable C,
  │                   flags, checks, Echoes, combat calls  │  same code on
  │ Rules core        dice, checks, Translation, Echoes,   │  every platform
  │ (done)            Passport                             │
  ├────────────────────────────────────────────────────────┤
  │ Platform layer    text, menus, pictures, input, disk,  │  one per platform
  │ (HAL)             sound                                │
  └────────────────────────────────────────────────────────┘
```

This is the Infocom/SCUMM approach: write each Departure once, ship it everywhere.

### Why each piece

- **Quest Script** lets writers write. A Departure is mostly prose and choices, and it
  should read like prose and choices, not code.
- **A compiler on the PC** does all the heavy work (parsing, checking, compressing), so the
  C64 only has to run a small, simple loop.
- **The Story VM in portable C** is the same build discipline as the rules core: the same
  tests run natively and on the 6502.
- **A thin platform layer (HAL)** keeps each new platform small: draw text, show a menu,
  show a picture, read a key, load a file.

## Content model

What a Departure is made of:

| Thing | What it is |
|---|---|
| **Car** | A loadable chunk, about one chapter. Only one car is in memory on the C64. |
| **Scene** | A location or moment: text, an optional picture, and a menu of choices. |
| **Choice** | A menu line, optionally gated (by a flag, stat, item, Echo or check). |
| **Check** | A d100 roll against a stat or skill, branching on fail / cost / success / crit. |
| **Encounter** | A fight: enemy group, zones, win/lose/flee branches. |
| **Flags and vars** | Story memory inside one Departure. |
| **Echoes** | Story memory across Departures (plant, read with canon default, transform). |
| **Rewards** | XP, items, Debt changes, written to the Passport at the end. |

Exploration is **scene-based**: every location is a scene with exits and actions in its
menu, like a gamebook with a full RPG underneath. This works identically on all five
retro platforms and makes Departures fast to write. Platforms with the power for it can
add a small tile map per location later as presentation; the story logic doesn't change.

The **Waystation hub is just another Departure image**: the departure board, the bar, the
ticket window are scenes. Picking a ticket loads that Departure. No separate hub engine.

## Quest Script, a first taste

Proposed syntax, inspired by [ink](https://www.inklestudios.com/ink/) (indentation, `*`
for choices, `->` to go somewhere), with our game's verbs built in:

```
== arrival
@picture kepler_dock
The airlock cycles. Somewhere above you, a calm voice says:
"Reactor failure in eighteen minutes."

* [Head for the bridge]                 -> bridge
* [Search the dead technician]
    check WITS vs 1
      crit:    You find a keycard *and* the override code. ~ give KEYCARD ~ set knows_code
      success: You find a keycard. ~ give KEYCARD
      cost:    You find a keycard, but the alarm sees you. ~ give KEYCARD ~ set alarm
      fail:    Nothing. The voice says: "Seventeen minutes."
    -> arrival
* {echo WOLF_PUP = SWORN} [Whistle for the wolf]
    Impossible, here. And yet: claws on the deck plating.
    -> wolf_arrives
* [Wait]                                -> loop_reset
```

## The compiled image

- **Bytecode**: 8-bit opcodes, compact operands, jumps within a car, `goto car:scene`
  between cars.
- **Text** is compressed with **byte-pair encoding**: roughly 40–50% smaller, and the C64
  decoder is a few dozen lines. All text sits in a string table per car.
- **Variables**: 512 flag bits and 128 byte variables per Departure. More than enough for a
  4–6 hour story, and only 192 bytes.
- **Save state** (mid-Departure): current car and scene, flags, vars, RNG state, plus the
  character. A few hundred bytes. Separate from the Passport, which is only written when a
  Departure ends.

## C64 memory budget

The C64 is the tightest target, so it sets the budget for everyone:

| Region | Budget |
|---|---|
| Engine code: VM + rules core + HAL + text decoder + disk loader | ≤ 20 KB |
| Current car: bytecode + compressed text | ≤ 16 KB |
| Picture: character set + screen data | ≤ 6 KB |
| Character, save state, flags, registry tables | ≤ 3 KB |
| Stack, buffers, screen | ≤ 4 KB |
| **Total** | **≤ ~49 KB** of the ~50 KB available with BASIC switched out |

A 4–6 hour Departure is maybe 150 KB of raw text. Compressed, that's 75–100 KB, about one
side of a 1541 floppy (170 KB). One Departure per disk side is the target.

## Platform front ends

| Front end | What it's for | When |
|---|---|---|
| **Terminal** (C, stdio) | Development, writing, automated tests | First |
| **sim65** (the 6502 simulator) | Running test playthroughs on a real 6502 instruction set | First |
| **C64** (cc65) | First retro target. The toolchain is already working. | Second |
| **Modern** (SDL2 desktop, plus a WebAssembly build for the browser) | The main commercial version; the browser build is for sharing, playtests and the community Workshop | Third |
| **Tabletop** (Platform 0) | Printed character sheets from Passports; Departures compiled to gamebooks and Conductor modules. See [tabletop.md](tabletop.md). | Sheet printer soon; books after E1 |
| **Apple II** | Shares the 6502 VM; new HAL only | Later |
| **DOS** | New HAL; Open Watcom or DJGPP | Later |
| **Amiga, SNES** | New HALs | Later |

The C64 comes ahead of DOS: the 6502 toolchain and tests already work, and anything
that fits the C64 fits everywhere.

## Testing: scripted playthroughs

Every Departure gets **playthrough tests**: a list of menu picks and a starting seed,
which produce a transcript of everything the game printed. Transcripts are checked in.

- The terminal build and the sim65 build must produce **identical transcripts**.
- A change that alters a transcript shows up in review as a text diff.
- Writers get this for free: "play the whole Departure in two seconds, every way we've
  recorded."

## Milestones

Each one ends with something playable or testable.

| # | Milestone | Done when |
|---|---|---|
| **E0** | **Specs**: Quest Script v0 (written as a public reference), bytecode and VM spec, HAL interface | Docs reviewed; one real scene written in Quest Script. *Drafted: [quest-script.md](quest-script.md), [vm-spec.md](vm-spec.md), `hal/apb_hal.h`, The Fare chapters 1–2. Awaiting review.* |
| **E1** | **Text VM on the terminal**: compiler (scenes, text, choices, flags, gotos, checks, items, Echoes) with friendly errors, VM in C with a load-time image verifier, the **character creator** (point-buy or roll, portable C on the HAL), terminal front end | a new character can be made and *Departure 00: The Fare* (the prologue at the Waystation) played in a terminal, and its transcripts match on sim65 |
| **E2** | **Starting and ending a Departure**: Passport in, rewards and Echoes out, mid-Departure saves, Rewind | Play *The Fare*, get a Passport, carry it into a test Departure |
| **E3** | **Combat**: zone-based, turn-based fights in the rules core, called from Quest Script | A fight in *The Fare*, covered by transcript tests |
| **E4** | **C64 front end**: text window, menus, status bar, picture area, disk loading of cars, `.d64` disk images | *The Fare* playable on a C64 (VICE emulator) |
| **E5** | **Vertical slice**: chapter 1 of *Eighteen Minutes* | Playable on terminal and C64 |
| **E6** | **Modern front end**: SDL2 desktop and browser builds | *The Fare* and the slice playable in a browser |
| **E7** | **Deep Yards prototype**: seeded procedural floors | A 10-floor descent playable on terminal and C64 |

After E7: the browser Workshop for community authors, Apple II, DOS, Amiga and SNES
front ends, the full Departure 01, party support.

### Departure 00: The Fare

A short prologue, about 20–30 minutes, built alongside the engine as its test content:
after the character creator, you wake in the Waystation, remember your death, meet the
Stationmaster, learn what you owe, and take your first ticket. It exercises every
engine feature, and it's the opening of the real game.

## Repository layout (planned)

```
core/            rules core (exists)
vm/              Story VM (C)
hal/             platform interface header
fe/term/         terminal front end
fe/c64/          C64 front end
tools/qsc/       Quest Script compiler (Python)
content/s1/      Season 1 Quest Script sources (The Fare, Departure 01, ...)
tests/playthroughs/   input scripts and golden transcripts
```

## Community Departures

Players will be able to write and share their own Departures. That's a design
requirement from E0 on, not a later add-on.

### In the fiction: Branch Lines

Official Departures leave from the Waystation's platforms. Community Departures run on
**Branch Lines**: unofficial tracks laid by travelers, which the Stationmaster tolerates
but doesn't bill for. You board them from a side platform at the Waystation.

### What it means for the engine

- **Quest Script is a public language.** It gets a proper reference manual, stable
  versioning, and compiler errors written for people who aren't programmers ("line 42:
  there's no scene called `brige`; did you mean `bridge`?").
- **The compiler goes where authors are.** It starts as a Python tool; later the same
  compiler runs in the browser (the **Workshop**), with a live preview using the WebAssembly
  build, so authors need nothing installed.
- **The VM never trusts an image.** Every Departure image is verified when it loads: every
  jump, string, scene, item and Echo reference is bounds-checked before anything runs. A
  broken or malicious image is refused with a message, never a crash. This protects the C64
  build as much as the PC one.
- **Same pipeline as ours.** Community authors get the same tools, the same playthrough
  tests, and the same C64 disk-image builder. A Branch Line can run on real hardware.

### Protecting characters and canon

A community Departure must not be able to wreck someone's character or the main story.

| | Official Departures | Branch Lines (community) |
|---|---|---|
| XP | Normal | Normal, capped at the Departure's level band |
| Items | Any | Only existing registry items, at most tier 3, with a per-Departure limit |
| Debt | Paid down | Not paid down (the Stationmaster doesn't bill for them) |
| Echoes | Written to the Passport | Kept in a separate **Branch Line ledger** stored with the save, never in the Passport's 8 slots |
| Reading your Echoes | Yes | Yes, read-only: a Branch Line can react to your canon choices but never change them |

Exceptional community Departures can be **certified** by us and promoted to full
rewards, possibly becoming official.

### Sharing

- Modern: Steam Workshop and a community board in the online Waystation.
- Retro: Branch Lines export as `.d64` (and later other) disk images, like ours.

### Open questions

- Moderation and certification process.
- Whether Branch Lines can define new items and Echoes of their own (they'd live only in
  the Branch Line ledger), or only use the official registries.

## Risks

- **cc65 optimizer bugs.** Already hit one. Mitigation: every test runs on sim65, so we
  find them.
- **Running the C64 build in CI.** Ubuntu's VICE package may ship without the C64 ROMs, so
  CI may not be able to boot the emulator. sim65 covers the logic; real-machine testing
  happens in VICE on your PC.
- **Text volume.** If Departures run long, a car may not fit in 16 KB. Mitigation: more,
  smaller cars; stronger compression later if needed.
- **Writing tools.** A custom language has no editor. Mitigation: plain text with good
  compiler errors first; a VS Code syntax extension later.

## Decisions (settled)

1. **Exploration: scene menus.** Every location is a scene with text, a picture and a menu.
   Tile maps may come later as optional presentation on platforms that can afford them.
2. **First retro target: the Commodore 64.** DOS moves after the Apple II.
3. **Quest Script: our own ink-like language**, designed from the start for community
   authors too. See *Community Departures* below.
4. **Modern front end: SDL2 desktop plus a WebAssembly browser build**, from the same C.
