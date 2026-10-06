# Tabletop: Platform 0

The oldest platform at the Waystation is **Platform 0**, where the trains are drawn in
pencil. It's our name for the tabletop edition: the same characters, rules and stories,
played in person with dice and paper. The other Platforms are lines of Departures
([lines.md](lines.md)); Platform 0 isn't a line but the one where any line can be played
by hand.

Bring your character from any machine: print their sheet from the Passport, play at the
table, then bring them home with everything they earned.

## Why it works

The rules were built to run on a 1 MHz Commodore 64, so they're small enough to run in
your head:

- **One roll, d100 + skill.** Roll, add the number on your sheet, beat the target
  number. No other dice, no bonus stacks.
- **On a normal task, every rating is a percentage.** "Stealth 47" means 47% against TN
  100. Players never need the rules to
  know their chances.
- **Whole numbers, simple math.** Halving and adding is the hardest arithmetic in the game.
- **Short tables.** The result table, target numbers, Translation and Dissonance all fit on one
  page.

## What a tabletop player gets

### 1. A printed character sheet

Type or paste a Passport password into the Passport Office (or the sheet tool) and print:

- name, race, class, level, XP;
- stats, and every **skill's rating already worked out** (half stat + training), with
  tagged skills marked, and each skill's chance at TN 100, 120 and 140;
- powers and their ranks;
- health;
- gear, with how each item **Translates** at different Tech and Magic Levels;
- Echoes, listed by name ("Spared Jace Cutter"), as **codewords**;
- unspent stat and skill points;
- the password itself, and a **QR code** of it, at the bottom.

The sheet tool will build on the Python Passport reference in `tools/passport/`.

### 2. The rules

- **The Traveler's Handbook** (players): creation, the d100 roll, skills, powers,
  Translation, levelling up. The same rules as [rules-v0.md](rules-v0.md), written for
  reading at a table.
- **The Conductor's Handbook** (the game master is the **Conductor**): running scenes,
  setting target numbers, Dissonance, Echoes, awarding XP, and filling in the Passport afterwards.

### 3. Departures on paper

The Quest Script compiler gets two more outputs, so every Departure we write can also
be printed:

- **Solo gamebooks.** Numbered sections ("turn to 117"), checks printed with their targets
  ("roll TECH − 10"), and flags as **codewords** you tick on your sheet, like the old
  Fighting Fantasy and Fabled Lands books. Solo Departures are a natural fit.
- **Conductor modules.** Scenes with read-aloud text, choices as options and hooks,
  checks and outcomes. Party Departures are a natural fit.

Echoes work the same everywhere. A codeword you earn at the table is an Echo in your
Passport, and a C64 Departure will remember it.

## Coming home: the Passport Office

At the end of a tabletop Departure:

1. The Conductor (or a solo player) records what changed: XP, items, Echoes, Debt.
2. The Passport Office produces the character's new password, with the **tabletop** flag
   set (`APB_FLAG_TABLETOP`).
3. Type it into any other platform and keep playing.

### Trust

- **Single-player:** tabletop progress counts in full. It's your character.
- **Online:** like any hand-entered password, a tabletop Passport is *unverified* in the
  online Waystation until it's checked. Later, **organized play** (certified Conductors at
  events, like D&D's Adventurers League) can stamp tabletop Passports as verified.

## Keeping the rules table-friendly

This is a design rule for everything from now on:

- Every number a player needs is on their sheet.
- One d100 roll per action.
- No rule may depend on something a table can't do: no hidden formulas, no long
  calculations. The computer versions can automate bookkeeping, but never add rules the
  table can't run.
- Combat (milestone E3) is designed and playtested **on paper first**, then coded.

## Plan

| Step | What | When |
|---|---|---|
| **P1** | Character sheet printer: password in, printable HTML sheet out | Soon; builds on `tools/passport/` |
| **P2** | Traveler's Handbook draft, from rules v0 | With E3 (combat) |
| **P3** | Gamebook output from the compiler | After E1 |
| **P4** | Conductor modules, and a Conductor's Handbook | With party Departures |
| **P5** | Organized play and verified tabletop Passports | With the online Waystation |

## Open questions

- Print-and-play only, or physical books and boxed sets too?
- How tabletop powers and combat feel without a computer doing the bookkeeping. This
  gets tested at a real table before E3 is coded.
