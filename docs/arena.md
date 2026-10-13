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
| `map NAME` | one of the arena's maps (`MAPS` in `tools/arena/arena.py`): `small` (that 12 x 8 floor), `big` (16 x 8, walled, open) or `ruins` (16 x 8, walled, with cover and hazards). `--map NAME` on the command line. 16 x 8 is the largest the battle screen shows whole (the cartridge's view is 20 x 8 squares; the engine takes 16 x 10) |

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

The site's **Arena** tab is the native arena (below): the scenarios to play now, each a
fight to play by hand beside what a thousand fights say. The first ten scenarios, by rules
v0, were a page of their own that boarded the train; that page is gone, and they open in
the arena by their codes (`#arena:scenario=A-02` on the site), played by rules v1:

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

### Playtesting

The site goes on GitHub Pages for playtesters: **Actions → Publish playtest → Run workflow**
(`.github/workflows/pages.yml`) builds it with `make site` and publishes it at
`https://jedi12many.github.io/a-platform-between/` (the arena: its **Arena** tab, or
`#arena`). It runs only when started by hand.

Each scenario has a **code** (`A-01`, `R-13` ...). Its **Give feedback** button opens a new
GitHub issue from the playtest form (`.github/ISSUE_TEMPLATE/playtest.yml`) with the
title (`[A-02] Magic is safe`), the scenario, the **build** (the commit the site was built
from, in `build.json`) and the times played in that browser already filled in; the tester
says how it went, what felt wrong and what felt right. Issues are labelled `playtest`; the
code in the title says which scenario, the build which rules. Keep a code with its
scenario: if a scenario changes a lot, give it a new code rather than reuse the old one.

The scenarios live in `tools/arena/scenarios.py`, which writes each one as a tiny Siding
(`arena-01`...`arena-10`, ids 1101-1110, bundled into the browser game) and the page's
data, measured by the arena. Their gear is in the registry (the sword, pistols, wand and
coats, ids 9-14). Change a scenario there, `make site`, and the page follows.

## The native arena

The same scenarios, played in a modern page instead of on the train: no story, no Boarding
Pass, no Travel Stamp, no C64 screen, and **by rules v1** ([turn.md](turn.md): the rules
lab's movement, conditions and powers), where the train still plays v0. More scenarios
(R-01 to R-20) are there only, to try v1: fire to cross, a ledge to shove foes
off, poisoned bites, chilling shots, flying over pits, running with Dash; and powers: a
Channeler's fire and ice, a Medic beside a Warden, a Tinker's barricade and shock mine, a
Rogue's blink and snare, a Warden's bull rush; hiding, confusion and taunts. It's a tool in
the **studio**, beside the art desk:

    make studio            then open http://localhost:8064/arena/

- **The intro** lists only what needs playing now, a few at a time (`PLAYING` in
  `tools/arena/scenarios.py`: R-18, R-19, R-20, R-13 and R-14 this round); any other opens by
  its link (`arena/#scenario=R-02`). The chosen one shows what we want tested and what to
  watch for, both sides' cards (worked out by the rules, not typed in), and what a thousand
  fights on the computer say. Enter starts the fight.
- **The fight** is the battle map at whatever size the window is, drawn from the game's art
  (`content/art/`) with every pixel crisp. Your turn shows where you can go. Pick a square
  with the arrows (or the keypad's digits for diagonals) or by clicking a lit one. Foes in
  reach from there are marked with the TN to hit them. Click one, or press A, to attack.
  Cards on the right show everyone's health and numbers; the log shows every roll.
- **Every button is always on screen**, with its key, and changes with the moment: your
  turn (Attack, Shove, Dash, Guard, Wait, Pack, Flee, Undo move, End turn, Quick turn),
  aiming, dashing, the pack, the foes' turn, the end. A button that can't be used now is
  greyed, and says why.
- **Shove** (S) a foe next to the square you've chosen, and **Dash** (D): pick a second
  square, as far again, from the first. **Conditions** show as chips on the cards (hover
  for what each does and how long it has left), as tags under the figures, and in the log
  as they go on, tick, are shaken off and end; a race's two traits are blue chips. Numbers
  a condition has moved are green (up) or red (down).
- **The pack** (P): what's held and worn, and the pack's items with their damage, kind and
  the skill each rolls with this traveler. Take one up, wear one, or put one away. It's
  free, as the rules say ([items.md](items.md#swapping)): it doesn't use the turn. Each
  scenario's pack has the arena's gear up to its own tier.
- **Powers** are on the keys **1-4** (and their buttons, with charges left). One with a
  single target goes off at once; with several, aim as for an attack; one that goes on a
  square (a burst, a field, a blink) lights where it can go, and shows what it would touch
  (the blast, the wall's line) under the cursor. **Blink is your move**: pick its square
  first (before walking), then act from there; Esc undoes it. Each card lists its fighter's powers.
  **Hover a power** (its button, or on a card; or Tab to it) for its rule at its tier: the
  roll and what it's against, the damage, the area, the rider, its condition and what that
  does, the charges left ([turn.md](turn.md#powers-in-play) worked out for that power). A
  power you can't use now stays hoverable, greyed, and says why when pressed.
- **Either order** ([turn.md](turn.md#actions)): attack, shove, guard or use a power before
  you've moved, and it happens from where you stand; the turn goes on, the other actions
  greyed out ("You've acted"), so you can still walk or blink, and Enter ends it.
- **Auto** (T) plays your turns as quick does, powers and all
  ([turn.md](turn.md#how-the-computer-uses-powers)); **Fast** (Z) speeds up what's shown.
- **The end** shows how it went (rounds, health left, damage each way, how often you hit,
  the swaps) beside what the computer gets. Fight again (R), give feedback (F: the same
  playtest issue form), or back to the scenarios.

It's the real rules: `tools/arena/web/arena.c` is the rules lab's battle engine
(`core/next/battle.c`) compiled to WebAssembly (`make arena-web` builds `build/arena-web/`),
with one addition only the arena builds (`APB_ARENA`): `apb_battle_rearm`, gear changed
mid-fight. "What the computer says" is a thousand fights by v1 (`build/arena-next`), with
v0's figure beside it; the computer never shoves or dashes. The art comes as
`art.json` (`tools/arena/web/art_json.py`); in the studio it's made from the art files as
they are now, so a figure drawn in the art desk is in the arena when the page is reloaded.
The scenarios, their maps, fighters and packs come from `tools/arena/scenarios.py`. It isn't
on the C64 or the cartridge, and needn't be: if the game ever offers it there, it will be
adapted then.

`make test-arena-web` (`tests/arena/check_native.py`) plays it in headless Chromium: every
scenario starts with the fighters it says and its buttons in view; fights on Auto with fixed
dice (three for each scenario, the rules lab's too) end as `build/arena-next` (the same
engine, natively) says, round for round and health for health; the pack's swaps fight by
the rules and don't use the turn; a Dash goes where it's pointed; a Shove by a pit drops
the foe in; a Fireball on key 2 picks its square, blasts, and spends its charge; a Medic's
Stim lands on the Warden beside her.

The arena runner plays v1 too: `python3 tools/arena/arena.py "Warden 1" vs RUST_GUARD --rules
next`, and a matchup can say `rules next`, `hazard 5 fire ON_FIRE` and `foe ASH_RAT x4 hit
POISONED`.

## How it's checked

`make test-arena-web` plays the native arena in headless Chromium (below), and `make
test-waystation` checks the site's tabs open it. `make test-combat` runs `tests/arena/check_arena.py`: fights from the arena, played again
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

### Rules v1, first measured

The same scenarios by v0 and by v1 (1000 fights each, both sides on quick, which never
shoves or dashes):

| | v0 | v1 | Why |
|---|---|---|---|
| A-01 A fair fight | 82% | 89% | the Salvaged Warden's Plated (Armor +10) |
| A-05 Two of them | 5% | 12% | Plated |
| A-06 Level 4: still a wall | 12% | 52% | Plated, and three levels above the guards (6 either way) |
| A-07 Level 5: new gear | 61% | 80% | v1's gentler tier (8 damage, Armor 15), and +8 for the levels |
| A-08 The swarm (4 rats) | 43% | 76% | Plated: the rats' 2s mostly miss |
| A-10 Shooters in a pair | 44% | 62% | |
| R-01 Through the fire | | 68% | three squares of fire cost about 15 health |
| R-02 Over the edge | | 39% | two rust-guards, without shoving them off |
| R-03 Venom (3 rats) | | 82% | |
| R-05 Wings | | 82% | |
| R-06 Run and gun | | 100% | a Rad-Dryad Channeler (Rooted: Soak +2) against a brute |
| R-07 Fire and ice | | 99% | 99% without powers: Rooted's Soak 2 stops a rat's 2 |
| R-08 Patch them up | | 91% | 80% without the Medic's powers |
| R-09 Hold the line | | 9% | 0% without: a Tinker alone against two gunners and a guard |
| R-10 Blink and snare | | 74% | 49% without; hexes against 50 between equals |
| R-11 Bull rush | | 91% | 14% without; Bull rush alone 84% (the pit), Ground slam 66%, Shield wall 26%, Second wind 23% |
| R-12 They have powers too | | 20% | 29% if the foes have none: the gunner's Snare costs you 9 points |
| R-13 Ground slam, no pit | | 35% | in the ruins (16 x 8: cover, spikes): 10% without powers; the slam alone 36% |
| R-14 Shockwave, no pit | | 17% | the ruins too: Shockwave alone 23% |
| R-15 Above their level | | 44% | 58% if the foes have no powers: a level 6 Warden, five levels up (10 either way), with an iron sword and a chain coat; their hexes need 60, and still cost him 14 points |
| R-16 Level 4, the old gear | | 52% | A-05's fight at level 4: 12% at level 1 |
| R-17 Level 5, the new gear | | 80% | the next level, and the next tier of gear: a step, not a cliff |
| R-18 Out of sight | | 34% | 16 x 8, cover and a line of fire: the computer neither hides nor moves (it snares and shoots from where it starts, as do the gunners), so the room is for the player; what hiding is worth is theirs to find |
| R-19 Mind spike | | 59% | 16 x 8, fire and cover, a guard and three rats: 69% *without* it: the computer trades a 5-damage Firebolt for a 3-damage spike, and a confused foe next to the Channeler lashes out at her as often as at its friends |
| R-20 Taunt | | 69% | 16 x 8, cover and spikes, three guards and a gunner: 32% if the gunner can't taunt: across the bigger room it taunts (3 damage) where it would shoot (6), and helps you |

R-13, R-14 and R-18 to R-20 are on the arena's largest maps (16 x 8) since this round,
with cover and hazards: the small rooms (12 x 6) let a rat cross in a turn, and hid what
cover, fire and spikes do.

From R-07 on, both sides use their powers as [turn.md](turn.md#how-the-computer-uses-powers)
says. Soak is strong against swarms: a Soak equal to a foe's damage
makes it harmless but for crits.

**Tuning the powers** (the second pass): a hex now hurts too (half a bolt's damage), which
took the Rogue's hexes from costing it 13 points to earning it 19; Ground slam stuns
(it knocked down, which costs a foe already next to you nothing, and pushed them out of
reach besides); a Mend puts on its condition, so Second wind heals 5 and then 3 a turn; and
Blink is a move, not an action (the computer blinked into the rats' next move and lost a
shot each time: Blink alone took the Rogue from 49% to 7%). Now it costs no shot, and the
computer blinks only where fewer foes can reach it: in these rooms, never.

Soak is strong against swarms: a Soak equal to a foe's damage
makes it harmless but for crits.

Races' traits are worth more than their +10: Plated alone moves the Warden's fights by
7 to 33 points. Rats that make you bleed (`hit BLEEDING`) take four from 76% back to 39%.

## Next

- Items and powers ([items.md](items.md)), each tried here as it goes into the engine.
- Smarter play for travelers than quick (use cover, focus fire), to measure good play too.
- The Waystation arena: load your traveler, pick your foes, watch the fight; then another
  player's build, played by the computer.
