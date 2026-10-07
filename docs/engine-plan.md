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

The C64 is the tightest target, so it sets the budget for everyone. Measured at E7
(the details: [c64.md](c64.md)):

| Region | Size |
|---|---|
| Main program: the VM's interpreter, rules core, C64 front end | 22.6 KB |
| Buffers: one car (6 KB at most), the depot (2 KB), battle state, saves | 11.9 KB |
| C stack | 0.4 KB |
| Overlay area: LOAD (7.4 KB, with the Deep Yards' generator), PASS (14.5 KB, with its own buffers) or BATTLE (15.1 KB), one at a time | 15 KB |
| **Total** | **about 50.2 KB** of the 51 KB below $D000 with BASIC switched out: 0.8 KB free |
| Picture, in the RAM under the KERNAL ROM ($E000) | 3.5 KB of 8 KB |

The 4 KB of RAM under the I/O chips ($D000) is still unused.

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
- **The party decides together.** It elects a leader, and either the leader makes the
  call or the party votes: every player picks an option, the votes are shown as they come
  in, most votes wins, and the leader breaks a tie ([party-play.md](party-play.md)).
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
- **Each character takes its own turn** in the order of play, and its player chooses its
  action then, as in *Pool of Radiance*: move, attack, cast, guard, wait, flee, or quick
  (the computer plays it). A **combat log** recaps what happened since your last turn,
  so nobody has to watch every turn ([party-play.md](party-play.md)).
- **Retreat is always an option**, and every encounter ends with a result the story picks
  up: won, lost, fled, or something the Departure defines (parleyed, captured).

### Every machine plays as equals

Co-op will mix machines: a modern PC next to a C64 Ultimate on a network link. Neither
mode depends on machine speed:

- Story mode waits for people (reading and voting), not processors.
- Encounters are turn-based: thinking speed matters, machine speed doesn't.
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

- Each client sends its player's votes and turns (a few bytes each) to the host.
- The **host is authoritative** (the details: [party-play.md](party-play.md)): it tallies votes, runs the same rules core, picks the
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
| **E2** | **Starting and ending a Departure**: boarding snapshots and receipts (see [boarding.md](boarding.md)), applying receipts in the rules core, Boarding Pass and Travel Stamp formats, reward manifests from the compiler, mid-Departure saves, Rewind | Play *The Fare*, apply its receipt to a Passport, carry it into a test Departure; two receipts from overlapping Departures both land |
| **E3** | **Encounters**: turn-based fights on a battle map in the rules core, called from Quest Script; voting for co-op story choices is designed alongside | A fight in *The Fare*, covered by transcript tests |
| **E4** | **C64 front end**: text window, menus, status bar, picture area, disk loading of cars, `.d64` disk images | *The Fare* playable on a C64 (VICE emulator) |
| **E5** | **Vertical slice**: chapter 1 of *Eighteen Minutes* | Playable on terminal and C64 |
| **E6** | **Modern front end**: SDL2 desktop and browser builds | *The Fare* and the slice playable in a browser |
| **W1** | **The Waystation, static site**: creator, Passport editing and level-ups, tabletop sheets, with the rules core as WebAssembly. Can start any time after E1. See [waystation-web.md](waystation-web.md). | A character made in the browser boards *The Fare* in the terminal |
| **E7** | **Deep Yards prototype**: seeded procedural floors | A 10-floor descent playable on terminal and C64 |
| **E8** | **Departure 01, whole**: *Eighteen Minutes*, chapters 2–5 and its Echoes | Playable start to end on terminal, C64, desktop and browser |

After E8: the browser Workshop for community authors, Apple II, DOS, Amiga and SNES
front ends, party support.

### E1 in detail

**Goal:** make a character and play *The Fare* start to finish in a terminal, with
identical transcripts on the PC and the 6502.

| Step | What | Done when |
|---|---|---|
| **E1.1 Registry as data** | Items, Echoes, skills, races and classes in one text file each, under `registry/`. A script generates `apb_registry.h` and the tables the compiler and Python tools use. | The header is generated and the build is unchanged. *Done.* |
| **E1.2 Compiler front half** (`tools/qsc/`, Python) | Lexer and parser for Quest Script v0, name resolution, friendly errors with line numbers and "did you mean". | `the-fare.qs` parses; a test file of broken scripts gives the right messages. *Done.* |
| **E1.3 Compiler back half** | Code generation per the VM spec, byte-pair text compression, the `.apd` writer, and the route map ("only one road to victory" warnings). | `the-fare.apd` builds under the size limits. *Done: 5.5 KB, text at 55%.* |
| **E1.4 Story VM** (`vm/`, C) | Loader and verifier, the instruction loop, text decoding, menus. All input arrives as choices through the HAL. | A hand-made image runs; corrupt images are refused, not crashed. *Done: The Fare plays on PC and 6502 with identical transcripts; 300 damaged images, no crashes.* |
| **E1.5 Boarding desk** (C, on the HAL) | How a client starts: enter a Passport password, check it, and board. Characters are made at the web Waystation ([waystation-web.md](waystation-web.md)); until W1 exists, `tools/passport` makes them for testing. Boarding Passes arrive with E2. | A Passport can be entered, by hand and by a choice list in tests, and a mistyped one is caught with its line number. *Done: `client/desk.c`; typos, wrong-length lines, forged checksums and restarts tested on PC and 6502.* |
| **E1.6 Terminal front end** (`fe/term/`) | The stdio HAL: wrapping, menus, status line. A `--choices file` mode that reads choices and writes a transcript. | *The Fare* is playable by hand. *Done: `make play`; wraps at 40 columns by default, plays `.apd` files or split directories.* |
| **E1.7 Playthrough tests** | Choice lists covering every route through *The Fare*, golden transcripts, run natively and on sim65. | Transcripts match on both; CI runs them. *Done: one traveler of every race and class, every outcome of both checks; a coverage build proves every instruction runs (it found two passages no route could reach), and every check is re-rolled from the rules and the Passport.* |

Order: E1.1, then E1.2–E1.3 (compiler) and E1.4–E1.5 (C) can proceed side by side, then
E1.6 and E1.7.

Out of scope for E1: combat (E3), saves and Passport hand-off (E2), pictures, the C64
screen (E4).

### E2 in detail

**Goal:** a Departure starts from a Boarding Pass and ends in a receipt that lands on the
character, on any machine. *The Fare*'s receipt is applied to a Passport and carried into
a test Departure; two receipts from overlapping Departures both land.

| Step | What | Done when |
|---|---|---|
| **E2.1 Applying receipts** (`core/`) | The receipt moves into the rules core; `apb_receipt_apply` follows [boarding.md](boarding.md). Receipts are net, and record each Echo's state at boarding so a timeline shift can be told. A Python reference (`tools/passport/receipt.py`) for the website. | C and Python agree on hand-worked and random receipts, on PC and 6502; overlapping receipts both land in either order. *Done: `make test-receipts`; it found 16-bit XP overflow in `apb_gain_xp`.* |
| **E2.2 Reward manifests** (`tools/qsc/`) | The compiler writes the most a Departure can give: XP, items, Echo states, Debt either way. Each reward command pays once per trip (the VM keeps track), so the bound is real. | Every playthrough's receipt fits its manifest; the manifest for *The Fare* is checked by hand. *Done: `qsc.py build --manifest`; a loop test proves rewards pay once on PC and 6502; receipts that claim too much are refused.* |
| **E2.3 Boarding Pass** | Format: character check, Departure, ticket number, dice seed. A Python issuer (the server side); the desk takes the pass and checks it matches the Passport and the Departure. | A pass for another character or Departure is refused with a plain message. *Done: 18 symbols; the ticket is a random number the server remembers, in place of a signature; the terminal boards with one.* |
| **E2.4 Travel Stamp** | Format: ticket number plus the receipt, with check symbols, typed at the website. Encoder in C, decoder in Python. | Every playthrough's receipt survives the round trip; typos are caught by line. *Done: The Fare's stamp is 26 symbols; every stamped playthrough and 400 random receipts round-trip, on PC and 6502.* |
| **E2.5 The round trip** | Terminal: board with Passport and pass, play, print the stamp. `tools/passport` applies a stamp to a Passport, as the website will. | *The Fare*'s stamp lands on a Passport that then boards a test Departure. *Done: `tools/waystation/station.py` issues passes into a ticket ledger and lands stamps; reused, forged and never-issued stamps are refused, and two overlapping trips both land.* |
| **E2.6 Saves** | Mid-Departure saves per [vm-spec.md](vm-spec.md), through `hal_save`/`hal_load`. | A playthrough saved and resumed at every menu gives the same transcript. *Done: about 100 bytes for The Fare; 38 save points resume exactly (3 on the 6502); 150 damaged saves are refused or play on, under the sanitizers; `s` saves in the terminal, `--resume` picks up.* |
| **E2.7 Rewind** | Replaying a Departure: reduced rewards, the Rewind fee, Echoes it planted replaced. | A Rewind's receipt follows [seasons.md](seasons.md). *Done: the pass's last bit marks a Rewind (the Waystation sets it for a Departure already played); the train forgets that Departure's Echoes; landing halves XP and Debt paid and charges 500 Debt, the same in C and Python.* |
| **E2.8 Receipts that teach** | A receipt can add a tagged skill, for the Arrivals ([lines.md](lines.md)). Needs a Passport-compatible way to carry it. | A test Arrival grants a tag that lands on the Passport. *Deferred: depends on whether the Arrivals take over the extra tag from the character creator ([lines.md](lines.md)), still a proposal.* |

### E3 in detail

**Goal:** a fight in *The Fare*, played on a battle map in the terminal, by the rules in
[combat.md](combat.md), with a way around it.

| Step | What | Done when |
|---|---|---|
| **E3.1 Combat rules** (`core/`) | Dodge, defense TNs, damage with margin, stat bonus, crits, glancing hits and Soak; area attacks; terrain; fleeing. A Python reference written from combat.md. | C and Python agree on hand-worked and random attacks, on PC and 6502; the worked fight in combat.md is a test. *Done: `make test-combat`, 9,000 random attacks and 300 sheets. It caught the transcript dice check counting one total too many as a cost.* |
| **E3.2 The battle** (`core/`) | Maps, movement and sight, the order of play, foe behaviors, rounds, the ways a fight ends. Deterministic, driven by a stream of actions. | Scripted battles give identical logs on PC and 6502. *Done (6.3 KB of 6502 code): seven reviewed scenarios, every roll re-checked; 300 random battles under the sanitizers. Building it settled three rules in combat.md: a blast can't catch its thrower, shooters move only as far as they must, cover protects whoever stands in it.* |
| **E3.3 Quest Script** | `foe`, `map` and `fight` with `won:`/`lost:`/`fled:` branches; the image format; the verifier. A warning for a fight with no way around. | The compiler's tests cover fights; damaged fight data is refused. *Done: the shared bestiary (`registry/foes.txt`); `map` and `fight` with plain-word errors; encounter records in the depot, checked on load in Python and C, 150 damaged copies under the sanitizers; the warning for a fight with no way around.* |
| **E3.4 VM and HAL** | The VM hands a fight to the battle engine; the HAL draws the map and asks for actions. Health carries over; `~ heal`. | A test image's fight plays through the harness on PC and 6502. *Done: `FIGHT` runs the battle engine through four HAL calls; health carries over, `~ heal` restores it, saves keep it; five fight playthroughs (won, lost, fled by exit and by roll, an ambush, a sneak) match on PC and 6502 with every roll re-checked, and resume from any story menu. The 6502 harness needs a 4 KB car and 2 KB depot buffer to fit.* |
| **E3.5 Terminal battle map** | The map at 40 columns, the action menu, the round's results. | A fight is playable by hand. *Done: the map two characters to a square with a key to its squares, a roster (health, the TN to hit each foe), and two menus a turn, "Where to?" (stay, next to or toward a foe, the exit, cover, high ground) and "Then?" (attack with its TN, defend, flee with its TN or take the exit, wait, back), offering only what's possible; events as sentences with every roll. Images now carry foe names. A recorded skirmish in `make test-term`, nothing over 40 columns.* |
| **E3.6 A fight in *The Fare*** | Something worth fighting, and a road around it. Transcript tests, coverage, saves around fights. | Every route still covered; transcripts match on both. *Done: the Lost Property office off the concourse, its own chapter, keeps every car under 4 KB. Ash rats guard a porter's hook (a new item, id 8). Fight them, creep past (Stealth: a success skips the fight, a cost starts it on your terms, a fail in an ambush) or leave them be; a loss heals 10. Six new playthroughs run every instruction, saved and resumed at every menu, on PC and 6502. The image fuzzer found a menu offset that wrapped past 65535 and got through the verifier; it's fixed, with a regression test.* |
| **E3.7 Voting (design)** | How a party votes on story choices and declares actions at once. | A reviewed design. *Done: [party-play.md](party-play.md). An elected leader; the party chooses "the leader decides" or democracy (one vote per character, the leader breaks ties); the best at it rolls story checks; personal moments; fights turn by turn as in* Pool of Radiance*, with a combat log and a recap since your last turn; the network messages. The VM never sees a vote, only the decision.* |
| **E3.8 *Pool of Radiance* turns** | The turn from review ([combat.md](combat.md), *Your turn*): guard (a free attack on the first foe to come close), wait (act at the end of the round), free attacks on anyone pulling away, done, and quick (the computer plays a character). The terminal shows the log, and a recap. Cast and use come with powers and items. | Python reference and C agree; battle scenarios for each new action match on PC and 6502; *The Fare*'s fight still covered. *Done: guard replaces defend, and help is gone; a foe with the guard rule stands guard when nobody's in reach; wait reorders only the round it's used in; free attacks for anyone pulling away, both sides; quick (`apb_battle_quick`) plans a traveler's turn with the foes' own rules. A new scenario covers each, re-checked roll by roll on PC and 6502; the terminal offers wait and quick, and its recorded skirmish shows them; The Fare's flee cases gained free attacks and new seeds, and every instruction still runs.* |

### E4 in detail

**Goal:** *The Fare* on a C64 disk, and proof it plays without a C64 in the room.

| Step | What | Done when |
|---|---|---|
| **E4.1 Fit in 64 KB** | Measure; split the game into a main program and overlays loaded from disk (LOAD, PASS, BATTLE); a memory map; 6 KB chapters | It links for the C64, with room for the stack. *Done: [c64.md](c64.md). The whole game was 38 KB of code before any Departure; now 21 KB stays and the rest loads when needed. Two cc65 traps found and fixed in the memory map: the C stack started inside the overlay area, and a function's local constants landed on its own label.* |
| **E4.2 The C64 front end** (`fe/c64/`) | The HAL on the KERNAL: text wrapped at 40 columns with "-- more --", menus by key, typed lines, the 1541 for files, saves and overlays | *The Fare* boards and plays. *Done: the battle screen, status line, checks and receipt moved into shared client code (`client/*view.c`), so the C64 and the terminal say the same words; the terminal's transcripts didn't change by a byte.* |
| **E4.3 The disk** | `.d64` images from the build | `make c64` writes *The Fare*'s disk. *Done: `tools/d64.py`, checked against VICE's c1541.* |
| **E4.4 Play it without a C64** | The real program on a 6502 emulator, the KERNAL answered in Python, from the disk image | `make test-c64`: transcripts match; the Travel Stamp is the terminal's. *Done: it also proved a save survives switching off, and found a function left in the wrong overlay; `fe/c64/check_overlays.py` now refuses any overlay that reaches into another.* |
| **E4.5 Real hardware** | VICE on a PC, then a real C64 | You play *The Fare* from the disk. |
| **E4.6 Pictures and a status bar** | The picture area and a fixed status bar | A picture shows at the bench. *Done: pictures live in the RAM under the KERNAL and show on rows 1-12 through a raster split, under a status bar on row 0, over a 12-row text window the front end now draws itself; a fight takes the whole screen. `tools/c64pic.py` makes them from PNGs (placeholders for The Fare, for now). The C stack went from 1.5 KB to 512 bytes, measured: the deepest route uses about 115.* |

### E5 in detail

**Goal:** chapter 1 of *Eighteen Minutes* ([01-eighteen-minutes.md](departures/01-eighteen-minutes.md)),
"Arrival", playable on the terminal and the C64: the ticket, the Translation, the station,
the countdown, the first death and the crew who don't remember you.

*Done:* `content/s1/01-eighteen-minutes/eighteen-minutes.qs`, `make play-e18`, and
`build/eighteen-minutes.d64`.

- **The loop.** Every move on Kepler-Nine costs minutes (`~ sub minutes`). The ring is the
  hub, and it checks the clock. At zero the reactor goes, you wake on Dock 3, and the
  station resets: three flags are cleared and `minutes` goes back to 18. What you learned
  stays: flags that are never cleared, and `visited`. The dock heals you fully: you wake
  whole.
- **The rest of chapter 1.** Teodor Vasz forgets you; MERIDIAN says "welcome back". When
  you've seen both, the chapter ends, on what you've found out (MERIDIAN locked the
  reactor; the safe holds seeds).
- **Translation and checks.** Each race and class has its own Translation. There are
  seven checks, from easy to hard, and a fight with the maintenance drone, a new foe
  (id 4, a guard). You can go around it by Stealth, or by Tech if your Tech is 30 or more.
- **Four chapters.** The largest car is 3.7 KB. The 6502 test harness has room for 4 KB,
  so the command deck went into "The Spine" with the reactor.
- **Tests.** Nine playthroughs run every instruction (544), on PC and 6502, each saved
  and resumed at every menu. A random search found them: it plays random routes and
  keeps the fewest that cover what the others miss. On the C64, a recorded route plays
  from the disk: board, beat the drone, die, wake, MERIDIAN, Teo, the end.
- **A compiler bug.** cc65 miscompiled the VM's flag clear: on the 6502, flags 8 and up
  stayed set. It's rewritten, with a regression case (`tests/vm/flags.qs`).
- **Pictures.** Eight placeholders (`pictures/sketch.py`).

*Not yet:* chapters 2-5 and the Echoes the ending plants. This slice ends at "you go to
find the crew".

### E6 in detail

**Goal:** *The Fare* and the slice, playable in a browser and on a desktop, from the same
C ([modern.md](modern.md)).

*Done:* `fe/modern/`. `make modern` builds the desktop (SDL2), and `make web` builds the
browser (WebAssembly, with Emscripten). One screen module implements the whole HAL on
the C64's 40 x 25 layout, drawn at 640 x 400 with full-colour pictures (`tools/apic.py`).
Each platform adds only a window, the keys and clicks, and where saves go: a directory on
a desktop, IndexedDB in a browser.

**Tests.** `make test-modern` plays the C64's three test routes on the desktop. Its
transcripts must be the C64's reviewed ones, except where the machines are meant to
differ (`~`, picture names), so the Travel Stamps match. The browser must then give the
desktop's transcripts, line for line, and its saves survive a page reload. Real keys
and clicks are checked in headless Chromium.

**Two things learned.**
- In a browser the VM can't block waiting for a key, so the build uses Asyncify to
  sleep until there is one.
- Debian's Emscripten drops `main` when the page decides when to start, so the page
  calls an exported `web_start` instead.

*Not yet:* a look of its own (a wider column, a proportional font, sound), and a
keyboard for phones.

### W1 in detail

**Goal:** a character made in the browser boards *The Fare* in the terminal
([waystation-web.md](waystation-web.md)).

*Done:* `make waystation`. It's a static site, with the rules core as WebAssembly
(`waystation/ws.c`), and four pages:

- make a traveler (bought or rolled stats);
- read a Passport and spend its points;
- print a tabletop sheet;
- land a Travel Stamp, taken on trust until W2.

The core gained `apb_stamp_decode`. It reads every stamp the Python reference writes,
and refuses the same damaged ones, on PC and 6502 (`make test-receipts`).

`make test-waystation` makes a traveler in headless Chromium and checks her Passport
against the Python reference's. It boards her on The Fare in the terminal with a
Boarding Pass, then lands her Travel Stamp in the browser, as it is and as a Rewind,
and checks the result against the reference. It also checks spending points, rolling
stats and refusing typos.

*Not yet:* the Arrivals as a character's first trip, and the server (W2): accounts,
Boarding Passes, the ticket ledger, checked stamps.

### E7 in detail

**Goal:** a 10-floor descent of the Deep Yards ([deep-yards.md](deep-yards.md)), the first
Siding, built from a seed, playable on the terminal and the C64.

*Done:* `content/sidings/deep-yards/deep-yards.qs`. Play it with `make play-yards`, on
`build/deep-yards.d64`, or with `make modern` / `make web`.

**The language.** Quest Script gained three things, and the rest is ordinary story:
- `kind: siding`: it asks for a yard number at boarding, and pays no Debt and plants no
  Echoes.
- `~ pick VAR N on KEY`: a choice made by the yard and the floor, never by the dice.
- `yard POOL` with `fight yard POOL on FLOOR`: maps built for each floor.

**The generator.** The maps come from `core/src/yard.c`, specified in
[deep-yards.md](deep-yards.md) closely enough that `tools/yards/yard.py`, written from the
page, gives the same bytes on thousands of maps. On the C64 it runs in the LOAD overlay
and builds each floor's map in the free space after the depot, so it costs the main
program nothing but its two new instructions.

**Making room.** The C64's main program had about 150 bytes free.
- The PASS overlay's buffers moved into the overlay (`OVL2BSS`, 1 KB).
- The C stack went from 512 to 384 bytes (the deepest route uses 115).
- The 6502 test harness no longer holds everything at once: one build has the yards,
  the other the boarding desk.

**Two mistakes found by testing, fixed.** The first mixing function was linear, so a
floor's picks came in fixed pairs: `make test-yards` now checks picks are independent.
The first foe numbers were too steep for anyone to reach the bottom.

**Tests.** `make test-yards` checks the generator against the reference. Twelve VM
playthroughs cover every instruction, on PC and 6502, saved and resumed at every menu,
and 150 damaged copies play under the sanitizers. On the C64 a descent plays from the
disk, and the desktop and the browser play the same yard to the same transcript.

*Not yet:* Translation per floor (it needs the VM to carry a realm), daily yards with
leaderboards (W2), and party yards.

### E8 in detail

**Goal:** all of *Eighteen Minutes* ([01-eighteen-minutes.md](departures/01-eighteen-minutes.md)),
the first Departure of Platform 1, playable from the ticket to the Stationmaster's ledger
on every front end, planting its three Echoes.

*Done:* five more chapters in `content/s1/01-eighteen-minutes/eighteen-minutes.qs`, and
no engine changes: everything it needed, Quest Script already had.

- **The crew.** After chapter 1, the ring becomes a concourse. Four of the crew know one
  thing each: Teodor the pod launch, Ravi the manual override, and Pell and the captain
  the safe's code. A failed check costs minutes, so a try can always wait for another
  loop.
- **The safe and the cause.** The code opens the seed vault, and in the reactor room
  MERIDIAN says why it lets the station die.
- **The last loop.** When you know enough, MERIDIAN agrees to one loop that stays done:
  eighteen minutes, and seven acts with prices. Closing the reactor, launching the pods,
  taking the seeds and MERIDIAN's fate (let go, wiped, or carried out as
  `MERIDIAN_CORE`) don't all fit.
- **The Echoes.** `MERIDIAN`, `KEPLER_CREW` and `SEED_VAULT` are planted from what you
  did, and handing the seeds to the Stationmaster takes 5,000 off your Debt.
- **Nine chapters.** The largest car is still 3.7 KB (chapter 1's station). Two more
  pictures: the safe, and the Stationmaster from The Fare.
- **The pictures, painted.** All thirteen pictures (The Fare's five, six more for
  Kepler-Nine, the Deep Yards' two) are painted in code with `tools/paint.py` in place of
  the first placeholders, each checked to come through the C64's colour rules unchanged
  ([c64.md](c64.md), "Pictures").
- **Tests.** Eleven playthroughs run every instruction (1,085, from 544), every one to the
  end, on PC and 6502, saved and resumed at every menu. Each starts with one of chapter
  1's routes, and a random search found the rest of the way; it prefers choices it
  hasn't made, which keeps the trips short. On the C64 (and on the desktop and in the
  browser, to the same transcript) the test route now plays the whole Departure: the
  pods launched, the seeds taken, MERIDIAN let go, and the seeds handed over.

*Not yet:* art drawn by hand. A Boarding Pass for the C64 route, so its Travel Stamp can be
compared with the terminal's as The Fare's is.

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

- **C64 memory (measured at E1.4).** The VM is about 9.9 KB of 6502 code and needs about
  21 KB of buffers (a 16 KB car, a 4 KB depot). A test program that also links the full
  stdio library and the Passport code overflows the default C64 memory layout by about
  1.3 KB. Plan for E4: bank out BASIC ROM for 8 KB more RAM, size the depot buffer to the
  image, leave stdio and the Passport encoder out of the game itself, and look for code
  size savings in the VM.
  *E3.2's battle engine was 10.4 KB of 6502 code,* as much as the whole VM. Rewritten
  around one static battle kept as a table of bytes (cc65 makes much smaller code for
  static arrays than for structs reached through pointers), it is 6.3 KB, with identical
  results. Still to do for the C64 (E4): load it from disk only when a fight starts, a
  classic overlay.
  *E3.4: the VM is now 15+ KB of code and 22 KB of buffers;* with the battle engine and
  stdio it no longer fits the 64 KB simulator with a 16 KB car, so the 6502 test harness
  runs with a 4 KB car and a 2 KB depot buffer (`-DAPB_VM_CAR_MAX`, `-DAPB_VM_DEPOT_MAX`).
  E4 needs a real memory map: smaller cars (chapters), overlays for the battle and the
  desk, and no stdio.
  *E4: done that way* ([c64.md](c64.md)): a 21 KB main program, three overlays in a 15 KB
  area, 6 KB chapters, no stdio. It fits with about half a kilobyte to spare, so the
  next big thing (pictures) needs a new idea, not a squeeze.
  *E2 adds about 2 KB to `passport.c`:* Boarding Pass decoding and Travel Stamp encoding,
  which a client needs, beside the Passport and pass encoders, which only tests and the
  website need. cc65 links whole files, so E4 should split them (`apb_receipt_apply` is
  already kept out of clients, in its own file).

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
