# A Platform Between

*Tales from the Waystation*

Bite-sized RPG novellas, each a 4–6 hour **Departure**, set in a weird science-fantasy
multiverse: D&D, Fallout, time travel, every tech level, magic, strange playable races.
Your character carries their level, gear and choices from one Departure to the next, on
modern PC, on old machines (Commodore 64, Apple II, Amiga, SNES, DOS), and at the table.

> *Static. Then the bar. A Rad-Dryad is wiping down glasses with a rag that keeps catching
> fire. Across from you, a tall thing in a velvet coat slides a brass ledger forward. Your
> name is written in it. Below your name, a number — and it's large.*
>
> *"Welcome back to the living," says the Stationmaster. "Let's discuss your fare."*

## Status

Pre-production. Everything here is a draft for discussion.

## Code

The rules core lives in [`core/`](core/): portable C that builds both for modern machines
and for the Commodore 64 with [cc65](https://cc65.github.io/). The same test suite runs
natively and on a simulated 6502, and must give identical results.

```sh
make test        # build and run the tests natively
make test-6502   # run the same tests on the sim65 6502 simulator (needs cc65)
make crosscheck  # the demo's native and 6502 output must be byte-identical
make c64         # build the C64 demo: build/demo.prg (needs cc65)
make check-content  # compile-check every Departure in content/
make demo        # build and run the native demo
```

## Docs

| Doc | What it covers |
|---|---|
| [Pillars](docs/pillars.md) | The ideas everything else hangs off |
| [World bible](docs/world-bible.md) | The Waystation, the Stationmaster, Debt, the mystery, races, realms |
| [Translation](docs/translation.md) | Tech/Magic levels, how gear and bodies change between realms, Force It and Dissonance |
| [Echoes](docs/echoes.md) | How a character's choices follow them and come back |
| [Seasons](docs/seasons.md) | Seasons as DLC, carrying over, skipping a season, replaying (Rewind) |
| [Sidings](docs/sidings.md) | Non-story content: procedural Deep Yards, mini-games |
| [Parties](docs/parties.md) | Solo vs. party Departures, rosters, bringing four of your own |
| [Boarding](docs/boarding.md) | One character in several games at once: snapshots, receipts, Travel Stamps |
| [Waystation on the web](docs/waystation-web.md) | The station is a website: build, shop, trade, meet; the clients are the trains |
| [Tabletop](docs/tabletop.md) | Platform 0: printed sheets, gamebooks, Conductor modules, coming home |
| [Rules v0](docs/rules-v0.md) | d100, the 100 scale, skills, powers, creation, levels |
| [Passport spec](docs/passport-spec.md) | The portable character record: password, file, hub account |
| [Platforms & engines](docs/platforms.md) | One script, many engines; build order |
| [Engine plan](docs/engine-plan.md) | Story VM, Quest Script, C64 budget, milestones E0–E7 |
| [Quest Script](docs/quest-script.md) | The language Departures are written in (public reference) |
| [VM spec](docs/vm-spec.md) | Departure image format, bytecode, runtime checks, saves |
| [Roadmap](docs/roadmap.md) | Phases from paper rules to multiplayer |
| [Departures](docs/departures/) | One-page treatments of the first solo Departures |
