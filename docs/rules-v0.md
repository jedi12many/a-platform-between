# Rules v0

A first proposal, open for change. What's marked as implemented lives in `core/` and is
tested on both PC and 6502. The numbers are first guesses; playtests will tune them.

## Hard constraints

- Whole numbers only. Every stored value fits in a byte (0–255).
- Everything must be playable by hand at a table, with pencil and percentile dice. See
  [tabletop.md](tabletop.md).
- One deterministic random-number generator, identical on every platform, so a given seed
  produces the same fight on the C64 and on Windows.

## The 100 scale

Characters are meant to live a long time: across Departures, seasons and years.

| | Range |
|---|---|
| Level | 1–100 |
| Stats | 0–100 |
| Skills | 0–100 |
| Powers | 0–100 |

Every rating *is* a percentage chance. A Melee of 62 hits on 62 or less. No conversion,
no table: what you see is your chance.

## The core roll: d100

Roll **d100** (two ten-sided dice, tens and ones; `00` is 100). Compare it to the
**target**: the stat, skill or power being tested, plus or minus the situation.

| Roll | Result |
|---|---|
| **01**, or **doubles** (11, 22 … 99) at or under the target | **Crit**: success, with something extra |
| At or under the target | **Success** |
| Up to 20 over the target | **Success at a cost**: it works, but something goes wrong |
| More than 20 over | **Fail**, and things move |
| **100** | Always fails |

**Modifiers:**

| Situation | Modifier |
|---|---|
| Easy | +20 |
| Routine | +10 |
| Normal | 0 |
| Tricky | −10 |
| Hard | −20 |
| Very hard | −30 |

Targets are kept between 1 and 100. A target of 100 still fails on a 100, and a target of
1 still crits on a 01.

Implemented: `apb_d100`, `apb_resolve`, `apb_check`.

## Stats

| Stat | Covers |
|---|---|
| **Might** | Strength, melee, carrying, forcing doors |
| **Grace** | Agility, aim, stealth, fine work |
| **Grit** | Toughness, health, resisting poison and fear |
| **Wits** | Intelligence, tech, lore, noticing things |
| **Presence** | Force of personality, talking, leading, channeling |
| **Fate** | Luck, timing, how the multiverse treats you |

A raw stat check uses the stat as the target ("roll under your Grit to keep going").

## Skills

Twelve skills, each governed by a stat. A skill's rating is:

> **half its stat + its training**, at most 100

| Skill | Stat | | Skill | Stat |
|---|---|---|---|---|
| Melee | Might | | Tech | Wits |
| Athletics | Might | | Medicine | Wits |
| Ranged | Grace | | Lore | Wits |
| Stealth | Grace | | Persuade | Presence |
| Endurance | Grit | | Channel | Presence |
| Survival | Grit | | Intuition | Fate |

Untrained, you still have half your stat: everyone can try anything. Training is what you
add on top, from 0 to 100.

**Tagged skills** (three, chosen at creation) start with 20 training and learn twice as
fast. That's taken straight from Fallout.

Implemented: `apb_skill`.

## Powers

Powers are what makes a traveler more than a person: spells, psionics, nanite swarms,
mutations, whatever the realm calls them (they Translate like gear). Each power has a
**rank** from 0 to 100, which is its percentage chance to work, and also scales its
effect.

A character holds up to **8 powers**. How powers are gained and raised is not designed
yet; the Passport already stores them.

## Character creation

A traditional creator, the same on every platform (and on paper):

1. **Name**: up to 8 characters.
2. **Race**: +10 to one stat.
3. **Class**: +5 to one stat, and tags two skills.
4. **Stats**: buy them, or roll them.
5. **Tag one more skill** of your choice.
6. **Confirm.** The character starts at level 1.

### Races and classes

| Race | +10 | | Class | +5 | Tags |
|---|---|---|---|---|---|
| Human | Fate | | Warden | Might | Melee, Endurance |
| Hollowborn | Grit | | Rogue | Grace | Stealth, Ranged |
| Glassfolk | Wits | | Tinker | Wits | Tech, Lore |
| Rad-Dryad | Presence | | Channeler | Presence | Channel, Intuition |
| Chronomite | Grace | | Medic | Wits | Medicine, Survival |
| Salvaged | Might | | | | |
| Moth-folk | Presence | | | | |

Classes describe what you *do*, not what genre you're from, so they Translate cleanly:

| Class | Does |
|---|---|
| **Warden** | Stands in front, protects, takes hits |
| **Rogue** | Sneaks, steals, strikes first |
| **Tinker** | Builds, repairs, hacks, jury-rigs (gadgets Translate to charms and traps) |
| **Channeler** | Spells, psionics, nanites: whatever the realm calls it |
| **Medic** | Heals, cures, keeps you going |

### Point-buy (the default)

Every stat starts at **25**. Spend **150 points**, one point per +1. No stat can be bought
above **70** (before race and class bonuses). All 150 must be spent.

### Rolling (the option)

For each stat, roll **3d6 × 5** (15 to 90). Roll six times, then arrange the results among
the stats however you like. Don't like the set? Roll a whole new set, up to **3 times**;
the last set rolled must be kept. Rolled characters average close to bought ones, but can
come out stronger or weaker. That's the point of rolling.

Implemented: `apb_pointbuy_valid`, `apb_roll_stats`, `apb_character_create`.

## Levels

- **Levels 1–100.** Every level costs **100 XP**, so XP is simply "percent of the way to
  the next level".
- **Each Departure awards XP for its level band.** Over the band, the award drops 10% per
  level, to nothing at 10 levels over. Old Departures stay replayable, but they stop
  making you stronger.
- **Each level gives:**
  - **1 stat point**: +1 to any stat.
  - **Skill points**: 1 + Wits ÷ 20 (1–6).
- **Raising a skill costs more the better you are**, by its current rating:

| Rating | Cost per raise |
|---|---|
| under 50 | 1 point |
| 50–74 | 2 points |
| 75–89 | 3 points |
| 90 and up | 4 points |

Each raise adds 1 training, or 2 for a tagged skill.

Roughly: a focused, tagged skill reaches 100 in about 20 levels; mastering several takes
most of the 100. A Departure of 4–6 hours is worth 2–3 levels early on, so level 100 is
dozens of Departures, several seasons, away.

Implemented: `apb_xp_award`, `apb_gain_xp`, `apb_raise_stat`, `apb_raise_skill`.

## Health and death

- **Health = 10 + Grit ÷ 4 + 2 per level.** About 25 for a new character, 235 at most.
- At 0 health you are pulled back to the Waystation. The Departure can be retried; your
  Debt goes up significantly. No permadeath.

Implemented: `apb_health_max`.

## Inventory

- 6 equipped slots + 6 pack slots. Hard limit; forces choices.
- Up to 2 **attuned** legendary items.

## Combat (milestone E3)

Turn-based, zone-based, designed table-first so it plays the same on paper and on a C64.
Solo hero plus optional companions and Echo allies. At high levels, opposed rolls matter
(both sides roll; the better result wins), so a level-100 traveler still meets equals.

## Open questions

- How powers are gained and raised.
- Weapon damage on the 100 scale (by tier, by roll, by margin?). Comes with combat.
- Companions: recruitable per Departure only, or carried on the Passport?
- How fast Debt goes down. Going home should be possible well before level 100, so
  long-lived characters are the ones who choose to stay.
