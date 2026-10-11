# The arena

A place to fight the rules before players do: travelers against foes, fought a thousand
times on the real battle engine (`core/src/battle.c`), both sides played by the computer,
and the results added up. 1v1, 4v1, a party against a patrol: whatever a balance question
needs. Later it becomes a page on the Waystation, where players try their builds against
the computer and each other.

## Running it

    make build/arena
    python3 tools/arena/arena.py arena/warden-vs-rust-guard.txt
    python3 tools/arena/arena.py "Warden 3" "Channeler 3" vs "RUST_GUARD x2"
    python3 tools/arena/arena.py "Warden 1" vs RUST_GUARD --sweep level 1-10
    python3 tools/arena/arena.py "Warden 1" vs RUST_GUARD --show 0     (one fight, blow by blow)
    make arena MATCHUP=arena/party-of-four.txt

A thousand fights take a fifth of a second. It reports how often the travelers win, lose,
flee or are still fighting after 50 rounds (a draw); how many rounds a fight lasts; and for
each fighter its health, what it has left on average, how often it goes down and the damage
it deals. A **sweep** runs the matchup again for each level (every traveler's) or each
count (of the last foe), as a table.

## Matchups

`arena/*.txt` holds some; a matchup is lines:

| Line | Means |
|---|---|
| `fights 1000` | how many fights; each has its own dice (fight *i* is seeded *seed + i*) |
| `seed 1` | the first fight's seed: the same matchup and seed always give the same results |
| `traveler [RACE] CLASS LEVEL [weapon ARCH TIER [TYPE]] [armor TIER] [name NAME]` | a traveler, built by the quick builder; ARCH is melee, ranged or focus |
| `foe NAME [x COUNT]` | a foe from `registry/foes.txt` |
| `sweep level 1-10` / `sweep count 1-6` | a run for each |
| `map`, rows, `end` | the battle map ([combat.md](combat.md#the-battle-map)); `@` and `a`-`z` where fighters start. Without one, a 12 x 8 open floor, travelers down the left, foes down the right |

### The quick builder

`Warden 5` makes a level 5 Warden the rules' own way, so builds can be tried without
making Passports by hand:

- **Race**: the one whose +10 is the class's stat (Salvaged Warden, Chronomite Rogue,
  Glassfolk Tinker and Medic, Rad-Dryad Channeler), unless the line names one.
- **Point-buy**: 150 points into the class's stats in order, 70 at most each (a Warden:
  Might, Grit, Grace, Wits); the class's tags and one more.
- **Each level**: the stat point into the first stat under 100, and the skill points
  (1 + Wits ÷ 20) into the skill it fights with, then Athletics, at the rules' costs.
- **Gear**: a weapon of its class's kind (melee, ranged, or a focus) at **tier 1, and one
  more every 5 levels**; armor a tier lower (the Warden's the same tier). Both can be set
  on the line: the registry needn't have the item yet.

It's a reasonable character, not an optimal one: give the line its gear to try another.

### What the computer does

Both sides play by **quick** ([combat.md](combat.md#your-turn)): a melee fighter charges
the nearest foe, a ranged one or a focus-user shoots whoever it can see. Foes play their
printed behaviour (charge, shoot, guard, coward). So the arena measures the rules with
straightforward play; a clever player does better, and that's fine.

## Playing it

The site has an arena page (`site/arena.html`, served as `arena.html` with `make site`):
**ten scenarios**, each a fight to play by hand on the battle screen, with a traveler made
for it, beside what a thousand fights say. Press Play: the page issues that traveler a
Boarding Pass with new dice, and the train opens on the fight; after it, fight again (at
full health) or leave.

| # | Scenario | Traveler | Against | It shows |
|---|---|---|---|---|
| 1 | A fair fight | Warden 1, rusted sabre, padded coat | a rust-guard | the model fight |
| 2 | Magic is safe | Channeler 1, ember wand | a rust-guard | powers aim at Ward, which is below Armor |
| 3 | Magic up close | the same, in a corridor | a rust-guard | how much of that is distance |
| 4 | The right weakness | Rogue 1, arc pistol | a rust-guard (weak to energy) | a weakness opens Armor |
| 5 | Two of them | Warden 1 | two rust-guards | numbers: two is a wall |
| 6 | Level 4: still a wall | Warden 4, the same gear | two rust-guards | levels count for little |
| 7 | Level 5: new gear | Warden 5, iron sword, chain coat | two rust-guards | a tier of gear counts for a lot |
| 8 | The swarm | Warden 1 | four ash rats | small hits add up |
| 9 | A lone shooter | Rogue 1, scrap pistol | a scrap gunner | a shooter alone is no threat |
| 10 | Shooters in a pair | Warden 1 | two scrap gunners, behind cover | shooters come in groups |

The scenarios live in `tools/arena/scenarios.py`, which writes each one as a tiny Siding
(`arena-01`...`arena-10`, ids 1101-1110, bundled into the browser game) and the page's
data, measured by the arena. Their gear is in the registry (the sword, pistols, wand and
coats, ids 9-14). Change a scenario there, `make site`, and the page follows.

## How it's checked

`make test-waystation` runs `tests/arena/check_play.py`: each scenario's traveler is the
class, level and gear the page says, built by the rules; each Departure compiles clean; the
page's numbers are the arena's; and in headless Chromium every Play boards its scenario
and starts the fight. `make test-combat` runs `tests/arena/check_arena.py`: fights from the arena, played again
by the battle tests' own runner (`tests/battle/battle.c`) from the same seed, must have the
same blows in the same order and the same ending; and the quick builder's characters must
keep the creation and level-up rules, at every level from 1 to 100. The battle engine
itself is held to the Python reference by `tests/battle/run_battles.py`.

## First findings

From the first runs (1000 fights each); to be weighed, not yet acted on.

1. **The Fare's fight is about right.** A new Warden beats a rust-guard **82%** of the
   time, with a third of its health left. Two rust-guards beat it **95%** of the time.
2. **Powers ignore armor, and foes have no Ward.** Every foe in the bestiary has Ward 0, and
   powers are aimed at Ward, not Armor. So a new Channeler beats a rust-guard **99%** of the
   time (the other classes: 79-88%). Foes need Ward values, or powers a cost.
3. **Gear outweighs levels.** Against two rust-guards a Warden wins 5% at level 1, 12% at
   level 4 and **61% at level 5**, the level its weapon goes up a tier; then 84% at 9 and
   98% at 10, the next tier. A level adds 2 health and a few skill points; a tier adds 5
   damage a hit. Levels may need to count for more, or tiers to step more gently.
4. **The scrap gunner is no threat.** Every class beats one 100% of the time at level 1 (15
   health, 4 damage a hit). It should be stronger, or come in groups.
5. **Numbers swamp a lone fighter.** A new Warden handles two ash rats (100%), three
   (90%), not four (43%) or five (7%).
6. **A party of four at level 3 is overwhelming** against two rust-guards and two gunners
   (100%, with only the Warden often going down: it's the one in front).

### After the bestiary's fixes

The fixes in [bestiary.md](bestiary.md#the-bestiary-today-measured) (Ward for every foe,
the gunner's damage up) moved the Channeler against a rust-guard from 99% to 96%, and the
gunner from a certain win to 98%. Ward equal to Armor would bring the Channeler to 87%,
level with the Rogue; a lone gunner stays weak, but two beat a new Warden 73% of the time.
The details, and what's next, are on that page.

## Next

- Items and powers ([items.md](items.md)), each tried here as it goes into the engine.
- Smarter play for travelers than quick (use cover, focus fire), to measure good play too.
- The Waystation arena: load your traveler, pick your foes, watch the fight; then another
  player's build, played by the computer.
