# The rules, in reading order

Everything about how *A Platform Between* plays, at the table and on every machine, is in
these pages. Read them in this order; each builds on the ones before. **Status** says
what's settled and in the engine (`core/`), what's drafted for review, and what's still
an idea.

| # | Page | What's in it | Status |
|---|---|---|---|
| 1 | [pillars.md](pillars.md) | The ideas everything hangs off: one character in every world, Translation, Echoes, rules that fit on a C64, many roads to victory | settled |
| 2 | [rules-v0.md](rules-v0.md) | The core roll (d100 + rating against a TN), stats, skills, creating a character, levels and XP, health, inventory, defenses | in the engine |
| 3 | [combat.md](combat.md) | Fights: hitting, damage, areas, the battle map, a round, free attacks, fleeing, a worked fight | in the engine |
| 4 | [items.md](items.md) | Items and powers: slots by body, free swapping, at-will and charged uses, shape and element, fields on the map; gaining, raising and swapping powers; class power lists; Out of Time | draft |
| 4b | [races.md](races.md) | Races: the stat bonus, the body (8 worn slots, 2 hands, a pack of 6, Small), two traits each, the lost-and-found | draft |
| 4c | [conditions.md](conditions.md) | Conditions: poisoned, asleep, on fire, slowed, shielded... from attacks, items, maps, realms and races; one short list of effects; shaking them off | draft |
| 5 | [translation.md](translation.md) | Tech and Magic Levels: gear and bodies changing form, Force It, Dissonance | settled; partly in the engine |
| 6 | [echoes.md](echoes.md) | Choices that follow you, in the story only: kinds, positive and negative states (negative ones in solo Departures only), party menus, reach, the Legend kept at the Waystation and the pass carrying only what a Departure needs | Passport Echoes in the engine; the rest drafted |
| 7 | [bestiary.md](bestiary.md) | Making foes: a standard foe by level, roles, how many make a fight, the bestiary measured | draft |
| 8 | [parties.md](parties.md), [party-play.md](party-play.md) | Solo and party Departures; a party's choices and fights | draft |
| 9 | [tabletop.md](tabletop.md) | Platform 0: playing at a table, and keeping the rules table-friendly | draft |
| 10 | [arena.md](arena.md) | Testing the rules: a matchup fought a thousand times, and what it found | tool built |

Around them: [world-bible.md](world-bible.md) (the setting), [boarding.md](boarding.md)
and [passport-spec.md](passport-spec.md) (Boarding Passes, Passports, receipts, Travel
Stamps, trip codes), [quest-script.md](quest-script.md) (writing a Departure), and
`registry/*.txt` (races, classes, skills, items, Echoes, foes: the single source of truth).

## Open questions

The rules' open questions, in one place. Each page keeps its own too.

- **Balance** (from the arena, [arena.md](arena.md#first-findings)): foes have no Ward,
  so powers are too safe; gear outweighs levels; the scrap gunner is too weak. Proposed
  fixes in [bestiary.md](bestiary.md#the-bestiary-today-measured).
- **A traveler's own Ward**: none today, so foes' powers hit easily ([bestiary.md](bestiary.md#still-open)).
- **The late game**: past level 40 gear has topped out ([bestiary.md](bestiary.md#still-open)).
- **Stacking** buffs and debuffs, if playtests show runaway combinations.
- **Companions**: per Departure only, or carried on the Passport? (Ally Echoes are story
  only: [echoes.md](echoes.md#story-not-rules).)
- **Debt**: how fast it goes down, so going home is possible well before level 100.
- **Attunement** (two legendary items) and **resonance** (effects by Tech and Magic
  Level): later ([items.md](items.md#still-open)).
