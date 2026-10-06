# Roadmap

## Phase 0: paper

- Rules v0, Translation tables, Echoes, Passport spec, seasons, Sidings, parties (this repo).
- Paper playtests of the core roll and combat.
- One-page treatments for the first three solo Departures.

## Phase 1: rules core and reference engine

- **Rules core in portable C** (`core/`): dice, checks, characters, Translation,
  Dissonance, Echoes, Passport passwords. Builds natively and for the C64; the same tests
  pass on both. *Started.*
- Quest Script v0, its compiler, and the Story VM. See [engine-plan.md](engine-plan.md)
  for the milestones (E0–E7).
- *Departure 00: The Fare*, the first of the Arrivals ([lines.md](lines.md)), as the
  engine's test content.
- A Deep Yards prototype: seeded procedural floors using the same rules core.

## Phase 2: first retro build

- C64 front end (the 6502 toolchain is already working).
- Departure 01 playable on modern PC and C64, with password Passports between them.

## Phase 3: more platforms and the community

- Apple II (shares the 6502 engine), then DOS, Amiga, SNES.
- The browser Workshop: community authors write, test and share Branch Lines.
- The web Passport Office.

## Phase 4: the Waystation online

The Waystation is a website: the station you visit between trains. See
[waystation-web.md](waystation-web.md). A static first version (W1) can come much earlier.


- Social hub: profiles, lobby, trading, rosters. Retro players join by uploading Passports.
- Server-authoritative rules using the Phase 1 core.
- Daily Deep Yards seeds and leaderboards.

## Phase 5: party Departures

- Party Departures for 2–4 characters: friends' imported characters, or four of your own.
- Stretch: retro machines online (C64 WiFi modems, Amiga TCP/IP).

## Release model

- **Season 1 (the Waystation)** is the base game. Later seasons are DLC: new station,
  Stationmaster, main story, biome. See [seasons.md](seasons.md).
- Steam and itch.io for modern; disk images plus limited physical runs for retro.
