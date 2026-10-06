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
| **Check** | d100 + a stat or skill against a target number, branching on fail / cost / success / crit. |
| **Encounter** | A fight on a battle map: terrain, enemies, starting positions (set by how the party arrived), and win/lose/flee branches. |
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
    check TECH tricky
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

## Two modes: story and encounters

A Departure plays like a session with a good game master. Most of it is **story mode**:
the situation is described, the party talks it over and decides. When it comes to a
fight, the map comes out: **encounter mode** is turn-based and tactical, like players
putting their minis on a map the DM just drew.

### Story mode: the party decides

- The **Stationmaster presents the ticket**, and the party decides how to tackle it. At a
  table, the Conductor can take any plan the players invent. On a computer we can't be that
  flexible, so each decision offers **a few good options**, written to be genuinely
  different (the many-roads pillar).
- **The party votes.** Every player picks an option; the votes are shown as they come in.
  Majority wins. A tie goes to the party leader (or, if the party prefers, to a coin the
  Stationmaster flips).
- **Solo, you are the vote.**
- **Some moments are personal.** A scene can ask every player to choose for their own
  character (what you say to the Stationmaster, what you take from the vault) instead of
  voting.
- **Then the story delivers.** The choice leads into the scenes it implies: the party
  chose the mountain path to the castle, so the narration follows them up the switchbacks,
  through the snow, until the rocks start moving. That's the ambush, and the encounter.
- Story mode isn't turn-based, and isn't timed by default. Voting can have an optional
  timer the party sets.

### Encounter mode: the map comes out

- **Turn-based, on a battle map**: a small grid with terrain, cover and the party's
  positions, drawn on screen the way a DM sketches one on a mat. The C64 has done this
  before (the Gold Box games), and at the table it's literally a map and minis.
- **How you got here shapes the fight.** An ambush on the mountain path starts with the
  party strung out on a ledge; sneaking in by the river starts with them unseen. The story
  choice sets the starting positions and who acts first.
- **Each round, everyone declares an action at once**, then the round resolves in
  initiative order. Nobody waits through other players' turns, and clicking faster never
  helps.
- **Retreat is always an option**, and every encounter ends with a result the story picks
  up: won, lost, fled, or something the Departure defines (parleyed, captured).

### Every machine plays as equals

Co-op will mix machines: a modern PC next to a C64 Ultimate on a network link. Neither
mode depends on machine speed:

- Story mode waits for people (reading and voting), not processors.
- Encounters are turn-based with simultaneous declaration: thinking speed matters,
  machine speed doesn't.
- **Turn timers are optional and generous**, set by the party. With none, a game can even
  be played slowly, a turn a day, like the old play-by-mail games.
- **Animations never hold up the game.** Each machine animates results at its own pace (or
  skips them).
- **Real-time mini-games** (handcar racing, say) stay single-player, or compete through
  ghosts and leaderboards, never live against each other.

This also keeps tabletop and digital play identical: talk, vote, then put the minis on the
map.

### How the network works

The whole game is **deterministic**: given the same image, the same starting characters,
the same random seed and the same list of choices, every machine produces the same result.
So co-op never sends game state, only choices:

- Each client sends its player's votes and declared actions (a few bytes each) to the host.
- The **host is authoritative**: it tallies votes, runs the same rules core, picks the
  random seed, and sends every player the decided choice (or the round's actions) and seed.
- Each client replays the round locally and shows it. Results match because the rules
  core is identical everywhere, which the 6502 test runs already prove.
- A few bytes a turn works over anything, including a C64's WiFi modem at 2400 baud.

The same idea runs through the whole engine. **The only input to the VM is a stream of
choices.** That one design gives us:

| Feature | It's just… |
|---|---|
| Playthrough tests | a recorded list of choices, and the transcript it produces |
| Co-op | votes and actions from several players, decided by the host into one choice stream |
| Saves | (later) the starting state plus the choices so far, or a snapshot |
| Bug reports | "here's my choice list" reproduces the bug exactly |

E1 is single-player, but it's built this way from the start.

## Milestones

Each one ends with something playable or testable.

| # | Milestone | Done when |
|---|---|---|
| **E0** | **Specs**: Quest Script v0 (written as a public reference), bytecode and VM spec, HAL interface | Docs reviewed; one real scene written in Quest Script. *Drafted: [quest-script.md](quest-script.md), [vm-spec.md](vm-spec.md), `hal/apb_hal.h`, The Fare chapters 1–2. Awaiting review.* |
| **E1** | **Text VM on the terminal**: compiler (scenes, text, choices, flags, gotos, checks, items, Echoes) with friendly errors and a route map that warns when a Departure has only one road to victory, VM in C with a load-time image verifier, the **character creator** (point-buy or roll, portable C on the HAL), terminal front end | a new character can be made and *Departure 00: The Fare* (the prologue at the Waystation) played in a terminal, and its transcripts match on sim65 |
| **E2** | **Starting and ending a Departure**: Passport in, rewards and Echoes out, mid-Departure saves, Rewind | Play *The Fare*, get a Passport, carry it into a test Departure |
| **E3** | **Encounters**: turn-based fights on a battle map in the rules core, called from Quest Script; voting for co-op story choices is designed alongside | A fight in *The Fare*, covered by transcript tests |
| **E4** | **C64 front end**: text window, menus, status bar, picture area, disk loading of cars, `.d64` disk images | *The Fare* playable on a C64 (VICE emulator) |
| **E5** | **Vertical slice**: chapter 1 of *Eighteen Minutes* | Playable on terminal and C64 |
| **E6** | **Modern front end**: SDL2 desktop and browser builds | *The Fare* and the slice playable in a browser |
| **E7** | **Deep Yards prototype**: seeded procedural floors | A 10-floor descent playable on terminal and C64 |

After E7: the browser Workshop for community authors, Apple II, DOS, Amiga and SNES
front ends, the full Departure 01, party support.

### E1 in detail

**Goal:** make a character and play *The Fare* start to finish in a terminal, with
identical transcripts on the PC and the 6502.

| Step | What | Done when |
|---|---|---|
| **E1.1 Registry as data** | Items, Echoes, skills, races and classes in one text file each, under `registry/`. A script generates `apb_registry.h` and the tables the compiler and Python tools use. | The header is generated and the build is unchanged |
| **E1.2 Compiler front half** (`tools/qsc/`, Python) | Lexer and parser for Quest Script v0, name resolution, friendly errors with line numbers and "did you mean". | `the-fare.qs` parses; a test file of broken scripts gives the right messages |
| **E1.3 Compiler back half** | Code generation per the VM spec, byte-pair text compression, the `.apd` writer, and the route map ("only one road to victory" warnings). | `the-fare.apd` builds under the size limits |
| **E1.4 Story VM** (`vm/`, C) | Loader and verifier, the instruction loop, text decoding, menus. All input arrives as choices through the HAL. | A hand-made image runs; corrupt images are refused, not crashed |
| **E1.5 Character creator** (C, on the HAL) | Point-buy or roll, race, class, extra tag, name, confirm, using only `hal_menu` and `hal_ask_name`. | A character can be made by menu, and by a choice list in tests |
| **E1.6 Terminal front end** (`fe/term/`) | The stdio HAL: wrapping, menus, status line. A `--choices file` mode that reads choices and writes a transcript. | *The Fare* is playable by hand |
| **E1.7 Playthrough tests** | Choice lists covering every route through *The Fare*, golden transcripts, run natively and on sim65. | Transcripts match on both; CI runs them |

Order: E1.1, then E1.2–E1.3 (compiler) and E1.4–E1.5 (C) can proceed side by side, then
E1.6 and E1.7.

Out of scope for E1: combat (E3), saves and Passport hand-off (E2), pictures, the C64
screen (E4).

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
