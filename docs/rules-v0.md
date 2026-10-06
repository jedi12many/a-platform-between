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

On a normal task, every rating *is* your chance: Melee 62 succeeds 62% of the time.

## The core roll: d100 + skill

> **Roll d100, add your skill (or stat, or power). Beat the target number (TN).**

| Task | TN |
|---|---|
| Easy | 80 |
| Routine | 90 |
| **Normal** | **100** |
| Tricky | 110 |
| Hard | 120 |
| Very hard | 130 |

On a normal task (TN 100), your rating is exactly your chance: d100 + 62 beats 100 on 39
or more, 62 times in 100. Every 10 points of TN is 10% harder.

| Roll | Result |
|---|---|
| A natural **100**, or **doubles** (11, 22 … 99) that beat the TN | **Crit**: success, with something extra |
| Total beats the TN | **Success** |
| Total within 20 under the TN | **Success at a cost**: it works, but something goes wrong |
| Lower than that | **Fail**, and things move |
| A natural **01** | Always fails |

**Bonuses add to your roll** (a buff, help from an ally, the right tool). **Anything
working against you raises the TN** (armor, a difficult lock, a stubborn will).

Implemented: `apb_d100`, `apb_resolve`, `apb_check`, `apb_chance` (the exact percentage
for any rating and TN, for sheets and screens).

## Stats

| Stat | Covers |
|---|---|
| **Might** | Strength, melee, carrying, forcing doors |
| **Grace** | Agility, aim, stealth, fine work |
| **Grit** | Toughness, health, resisting poison and fear |
| **Wits** | Intelligence, tech, lore, noticing things |
| **Presence** | Force of personality, talking, leading, channeling |
| **Fate** | Luck, timing, how the multiverse treats you |

A raw stat check adds the stat instead of a skill ("d100 + Grit to keep going").

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
**rank** from 0 to 100, which you add to the roll to use it, and which also scales its
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

## Defenses are target numbers

Defenses don't get their own roll. A defense is the **TN the attacker has to beat**:

> **TN = 50 + the defense**

| Defense | Stops |
|---|---|
| **Armor** | weapons |
| **Ward** | powers |
| **Resolve** | persuasion, intimidation, fear |

Defenses run 0 to 100 like everything else, so **100 against 100 is 50%**: d100 + 100
against TN 150. Stat blocks print the TN directly ("Iron golem: Armor TN 140"), so nobody
adds the 50 at the table. A puzzle, a lock or a hazard is the same kind of number: its
difficulty is its defense.

A defense can differ by damage type: an iron golem's Armor is TN 140 against blades and
bullets, but only TN 80 against lightning.

The wall is meant to be steep. A defense is a **problem for the party to solve**, not a
number to grind past. Every answer is a plain number you add or subtract:

| Option | What it does | Examples |
|---|---|---|
| **Buff** the attacker | + to the roll | Overclock +20, Bless, a war cry, a stim |
| **Debuff** the defense | − to the TN (the defense stops at 0) | Rust −20, Shatter, an EMP, Sunder |
| **Pierce** | − to the TN, for one weapon or one fight | adamant oil, armor-piercing rounds, a rune of opening |
| **Exploit** | use the damage type it's weak to | lightning on iron, fire on frost |
| **Called shot** | aim for a weak spot: a lower TN, at a penalty to the roll | a seam in the plates, the visor |
| **Help** | an ally sets you up: + to the roll | a feint, covering fire, a distraction |

Every point now counts in full, so buffs and debuffs are kept modest: ±10 to ±20 is a big
deal.

### The wizard and the iron golem

An iron golem: **Armor TN 140** (TN 80 against lightning). A fighter with **Melee 70**:

| Plan | Roll | Needs to beat | Chance |
|---|---|---|---|
| The fighter alone | d100 + 70 | 140 | **30%** |
| The wizard casts **Rust** on the golem (TN −20) | d100 + 70 | 120 | **50%** |
| The wizard **Overclocks** the fighter (+20) | d100 + 90 | 140 | **50%** |
| Both, on the next turn | d100 + 90 | 120 | **70%** |
| The fighter oils the blade with **adamant** (Pierce 20) | d100 + 70 | 120 | **50%** |
| The wizard throws **lightning** (Channel 60) | d100 + 60 | 80 | **80%** |
| A **called shot** at a seam (TN 90, −20 to the roll) | d100 + 50 | 90 | **60%** |

Alone, the fighter is in trouble. With a plan, the odds swing hard. That's what the
character with the right scroll, the right spell or the right idea is for, at the table
and on a C64 alike.

Results in a fight:

| Result | In combat |
|---|---|
| Crit | a hit that does something extra: double damage, a disarm, a knock-down |
| Success | a hit |
| Success at a cost | a **glancing** hit (half damage), or a hit that leaves you exposed |
| Fail | a miss, and the enemy gets an opening |

Implemented: `apb_defense_tn`, `apb_chance` (the golem table above is a test case).
Defenses, buffs and items that use them arrive with combat.

## Combat (milestone E3)

Turn-based, zone-based, designed table-first so it plays the same on paper and on a C64.
Each round, everyone declares an action at once, then the round resolves in initiative
order; that keeps co-op fair between fast and slow machines.
Solo hero plus optional companions and Echo allies. Defenses work as above. At high
levels, opposed rolls matter (both sides roll d100 + skill; the higher total wins), so a level-100
traveler still meets equals.

Design rules for combat:

- **Tough enemies have answers, but you may not be carrying them.** Every roadblock
  should have at least two answers a *prepared* party might hold: a weakness, a debuff, a
  tool. An unprepared party may have none of them. See *Roadblocks and many roads* below.
- **Every option is a number on the sheet or the card.** No hidden formulas.
- **Items for the occasion matter.** Consumables and specialist gear (oils, scrolls,
  charges) are a core part of the loot, not filler.

## Roadblocks and many roads

**Every Departure has more than one road to victory.** The world isn't scaled to you, so
some obstacles are **roadblocks**: if you didn't prepare for them, you can't get through
today, and the right move is to go another way.

A roadblock can be anything that stops you:

| Roadblock | Answers a prepared traveler might have |
|---|---|
| **An enemy** (the iron golem) | the right weapon or power, a debuff, a weakness, an ally |
| **A puzzle** (the orrery lock) | work it out yourself; or a `TECH`/`LORE` check; or the key you found earlier; or a power that bypasses it |
| **A locked or sealed way** | the key, the code, a `TECH` check, brute `MIGHT`, the right Translation |
| **A hazard** (the radiation field, the drowned stair) | the right gear, `ENDURANCE`/`SURVIVAL`, a Rad-Dryad who drinks the glow |
| **A gatekeeper** (the clerk, the guard captain) | `PERSUADE`, a bribe, a forged pass, an Echo they remember |

**Puzzles reward the player and the character.** On screen and at the table, a puzzle can
be solved by the player's own thinking. A character with the right skill can solve it
with a check instead, and a character with neither can still go around. Nobody is locked
out of the story because they can't solve a riddle, and nobody is robbed of the riddle
because their character is clever.

- **Not every path is open.** A Departure never promises that the road you're on
  continues. It promises that *some* road does, and usually several.
- **Preparation is the skill.** Tickets come with rumors ("iron guardians in the lower
  vaults"). The Waystation's traders sell answers. Six pack slots means you can't carry an
  answer to everything, so what you pack decides which roads open.
- **You can see it before it sees you.** Roadblocks are telegraphed: the scorched walls,
  the crushed armor at the door, the silence. A `LORE`, `INTUITION` or `SURVIVAL` check can
  reveal a roadblock's defenses and weaknesses before you commit.
- **Retreat is always on the table.** Backing off before a fight is free. Fleeing a fight
  in progress is a roll, with a cost if it goes badly, but it never ends the Departure on
  its own. Death pulls you back to the Waystation with more Debt; running away doesn't.
- **The other way is a real way.** Going around means a different route: longer,
  stranger, more dangerous elsewhere, missing what the roadblock guarded, sometimes leading
  to a different ending. It's never a punishment corridor.
- **You can come back.** Characters live a long time. The golem that turned you back at
  level 8 is still there at level 30, and so is what it guards. A Rewind, or a later
  Departure to the same realm, is your second try. Knowing a roadblock's weakness can be a
  **Key** Echo that travels with you.
- **Rewards behind roadblocks stay worth it.** XP fades when you've outgrown a Departure,
  but unique loot and Echoes behind a roadblock can be claimed once, whenever you finally
  get there.

At the tabletop, the Conductor plays it straight: don't fudge the golem down to the
party's level, or hand out the puzzle's answer. Telegraph it, let them scout, and leave
the other road open.

## Open questions

- How powers are gained and raised.
- Weapon damage on the 100 scale (by tier, by roll, by margin?). Comes with combat.
- Limits on stacking buffs and debuffs, if playtests show runaway combinations.
- Companions: recruitable per Departure only, or carried on the Passport?
- How fast Debt goes down. Going home should be possible well before level 100, so
  long-lived characters are the ones who choose to stay.
