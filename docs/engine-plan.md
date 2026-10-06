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
| **Check** | A 2d6 roll from the rules core, branching on fail / cost / success / crit. |
| **Encounter** | A fight: enemy group, zones, win/lose/flee branches. |
| **Flags and vars** | Story memory inside one Departure. |
| **Echoes** | Story memory across Departures (plant, read with canon default, transform). |
| **Rewards** | XP, items, Debt changes, written to the Passport at the end. |

Exploration is **scene-based**: every location is a scene with exits and actions in its
menu, like a gamebook with a full RPG underneath. This works identically on all five
retro platforms and makes Departures fast to write. Platforms with the power for it can
add a small tile map per location later as presentation; the story logic doesn't change.
*(Decision 1 below.)*

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
| **Modern** (SDL2 desktop, plus a WebAssembly build for the browser) | The main commercial version; the browser build is for sharing and playtests | Third |
| **Apple II** | Shares the 6502 VM; new HAL only | Later |
| **DOS** | New HAL; Open Watcom or DJGPP | Later |
| **Amiga, SNES** | New HALs | Later |

This puts the C64 ahead of DOS, which changes the original roadmap. The reason: the
6502 toolchain and tests already work, and anything that fits the C64 fits everywhere.
*(Decision 2 below.)*

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
| **E0** | **Specs**: Quest Script v0, bytecode and VM spec, HAL interface | Docs reviewed; one real scene written in Quest Script |
| **E1** | **Text VM on the terminal**: compiler (scenes, text, choices, flags, gotos, checks, items, Echoes), VM in C, terminal front end | *Departure 00: The Fare* (the prologue at the Waystation) is playable in a terminal, and its transcripts match on sim65 |
| **E2** | **Starting and ending a Departure**: Passport in, rewards and Echoes out, mid-Departure saves, Rewind | Play *The Fare*, get a Passport, carry it into a test Departure |
| **E3** | **Combat**: zone-based, turn-based fights in the rules core, called from Quest Script | A fight in *The Fare*, covered by transcript tests |
| **E4** | **C64 front end**: text window, menus, status bar, picture area, disk loading of cars, `.d64` disk images | *The Fare* playable on a C64 (VICE emulator) |
| **E5** | **Vertical slice**: chapter 1 of *Eighteen Minutes* | Playable on terminal and C64 |
| **E6** | **Modern front end**: SDL2 desktop and browser builds | *The Fare* and the slice playable in a browser |
| **E7** | **Deep Yards prototype**: seeded procedural floors | A 10-floor descent playable on terminal and C64 |

After E7: Apple II, DOS, Amiga, SNES front ends; the full Departure 01; party support.

### Departure 00: The Fare

A short prologue, about 20–30 minutes, built alongside the engine as its test content:
you wake in the Waystation, meet the Stationmaster, learn what you owe, make your
character (race, class, stats, name), and take your first ticket. It exercises every
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

## Decisions

1. **Exploration style.** Recommended: scene-based (gamebook-plus menus) for v1, with tile
   maps as optional per-platform presentation later. Alternative: tile maps from the start.
2. **First retro target.** Recommended: C64 (toolchain already working). Alternative: DOS.
3. **Quest Script.** Recommended: our own ink-inspired language. Alternative: write in ink
   itself and compile ink's output to our bytecode (proven editor, but a much bigger
   runtime to fit on a C64).
4. **Modern front end.** Recommended: SDL2 desktop plus a WebAssembly browser build from
   the same C. Alternative: a separate engine (Godot, Unity) reading the same images.
