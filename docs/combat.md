# Combat

*Draft for review (milestone E3). Every number here is a starting point for playtests.*

Fights are **encounters**: turn-based, on a battle map, designed table-first so they play
the same with minis on a mat and on a C64. They use the core roll from
[rules-v0.md](rules-v0.md): **d100 + your rating, beat the TN.** No other dice.

## Who's in a fight

A **combatant** is a character or a foe. Everything about one is a number on the sheet or
the foe card:

| Number | For a character | Notes |
|---|---|---|
| **Health** | 10 + Grit ÷ 4 + 2 per level | carries over between fights in a Departure; full again at the Waystation |
| **Dodge** | Grace ÷ 5 (0–20) | you're harder to hit; lost when you can't move (pinned, knocked down) |
| **Armor** | 10 × the tier of the armor you wear (0–90) | stops weapons |
| **Ward** | from powers and items that grant it | stops powers |
| **Soak** | from magic and tech that grant it (a shield belt, stoneskin) | taken off every hit's damage |
| **Speed** | 4 + Grace ÷ 25 (4–8) | squares you can move in a round |
| **Attack** | Melee, Ranged or Channel, by weapon | the skill you roll |

A foe card prints its numbers directly, including its defense TNs, so nobody adds at the
table:

```
RUST-GUARD          scrapyard automaton
Health 20   Speed 4   Soak 2
Hit it: TN 74 (TN 54 with energy)
Claws: Melee 45, damage 6 kinetic
```

## Hitting

> **Defense TN = 50 + Dodge + Armor** (Ward instead of Armor against powers)

The same table as every roll, read for a fight:

| Result | What happens |
|---|---|
| **Crit** (a natural 100, or doubles that succeed) | a hit for **double damage** |
| **Success** | a hit |
| **Success at a cost** (within 20 under) | a **glancing** hit: half the weapon's damage, nothing for the margin |
| **Fail** | a miss |

Buffs add to the roll and debuffs take off the TN, exactly as in
[rules-v0.md](rules-v0.md) (*Defenses are target numbers*). A defense can differ by damage
type: a foe weak to energy prints a lower TN for it.

## Damage

Damage is variable, but it comes from the roll you already made, not a second die:

> **Damage = the weapon's damage + 1 for every full 10 you beat the TN by + your stat bonus**
> **− the target's Soak** (never below 0)

| Part | Value |
|---|---|
| Weapon damage | **5 × the weapon's tier** (a rusted sabre, tier 1: 5; a pulse rifle, tier 4: 20). Bare hands: 2. Foes print theirs. |
| Margin | +1 for every full 10 the total beats the TN by: a strong hit hurts more |
| Stat bonus | melee: **Might ÷ 20** (0–5). Ranged and powers: none (their skill already does the work) |
| Crit | double everything before Soak |
| Glancing | half the weapon's damage (rounded down), no margin, no stat bonus |
| Soak | taken off each hit. A sabre can just scrape a golem: that's a roadblock, not a bug |

### Area attacks

Some weapons and powers have an **area** (a grenade, a fireball: *Area 1* means the target
square and every square touching it). Roll once; compare that one total with each
combatant's TN in the area, friend or foe, and work out each one's damage separately.
Dodge still counts: you dive clear.

## The battle map

A map is a grid up to **16 × 10** squares, drawn in the Quest Script as rows of
characters (it fits a 40-column screen with room for text, and copies onto squared paper):

| Square | Means |
|---|---|
| `.` | open ground |
| `#` | **wall**: blocks movement and sight |
| `O` | **pit**: can't be entered or crossed on foot; it doesn't block sight |
| `~` | **rough** (water, rubble, snow): costs 2 squares of movement |
| `+` | **cover** (crates, a low wall): costs 2 to enter; +20 to your TN against ranged attacks and powers aimed past it |
| `^` | **hazard** (fire, radiation): 5 damage to anyone who enters it or starts a round there; Soak counts |
| `=` | **high ground**: +10 to your attacks against anyone not on high ground |
| `>` | **exit**: a way out of the fight |
| `@` | where a traveler starts |
| `a`–`z` | where a foe starts (the foe is named in the script) |

Distance is counted in squares, diagonals included (a step in any of the 8 directions is 1).
Melee reaches the 8 squares around you; ranged weapons and powers reach anything in sight.
Sight is blocked only by walls, and by other combatants for ranged attacks.

## A round

1. **Order.** Combatants act from highest Grace to lowest (travelers first on a tie). It's
   worked out once per fight, so there's nothing to roll. The story sets who's caught
   off guard: in an **ambush**, the foes get a free round before the first one; if the
   party **sneaks up**, the travelers do.
2. **Each combatant moves up to their Speed and takes one action**, before or after moving:
   - **Attack** with a weapon or power.
   - **Use** an item (a stim, an oil, a grenade).
   - **Defend**: +20 to your TN until your next turn.
   - **Help** an ally next to the same foe: +20 to their next attack on it.
   - **Flee** (see below).
3. In co-op, everyone **declares at once**, then the round plays out in order
   ([engine-plan.md](engine-plan.md)). Solo, you just choose.

Foes act by a short, printed rule (on the card at the table): *close in and attack the
nearest traveler*, *keep distance and shoot*, *guard the door*, *flee at a quarter
health*. No hidden formulas, so a fight plays the same at the table and on the screen.

## Ending a fight

| Ending | When |
|---|---|
| **Won** | every foe is down or has fled |
| **Lost** | every traveler is down (at 0 health). You're pulled back to the Waystation and your Debt goes up; the story's `lost:` branch decides what happens next |
| **Fled** | every traveler still standing has left the map |
| Something the Departure defines | parleyed, captured, the bridge collapsed: the script can end a fight on its own condition |

**Fleeing.** Step onto an exit (`>`) and take the Flee action: you're out. Anywhere else,
it's a roll: **d100 + Athletics against TN 100, +10 for every foe next to you.** Success,
you're out; success at a cost, you're out but each foe next to you gets a free attack;
fail, you're still here. Running away never ends the Departure on its own.

Health carries over: wounds from one fight are still there for the next, until the story
heals you (a rest, a medic, `~ heal`). Back at the Waystation, everyone is whole again.

## A worked fight

Kestrel (Salvaged Warden, level 1) with a rusted sabre and ballistic weave meets a
rust-guard in the scrapyard. Her numbers: Might 85, Grace 40, Grit 60; Melee 62; Health 27;
Dodge 8, Armor 30, so **TN 88** to hit her; Speed 5; sabre damage 5 + Might ÷ 20 = **9**.

1. Kestrel (Grace 40) goes first. **d100 + 62 vs TN 74**: she hits on 13 or more (88%).
   She rolls 57: total 119, 45 over, so +4. Damage 9 + 4 = 13, minus Soak 2: **11**. The
   rust-guard is down to 9.
2. The rust-guard's claws: **d100 + 45 vs TN 88**: a hit on 44 or more, glancing on 24 to
   43. It rolls 71: total 116, 28 over, +2. Damage 6 + 2 = **8**. Kestrel is down to 19.
3. Kestrel rolls 34: total 96, 22 over, +2. 9 + 2 − 2 = **9**. The rust-guard falls.

**The other answer.** Her pulse rifle is energy, and the rust-guard is weak to it: TN 54.
But Kestrel isn't trained in Ranged (Grace ÷ 2 = 20): d100 + 20 vs 54 hits on 35 or more,
66%, for 20 damage, and the first hit ends it. Two plans, both plain numbers on the sheet.

## In the code

`core/src/combat.c` (`apb_dodge`, `apb_speed`, `apb_armor`, `apb_melee_bonus`,
`apb_weapon_damage`, `apb_hit_tn`, `apb_damage`, `apb_attack`, `apb_in_area`,
`apb_flee_tn`, the tiles), checked against `tools/rules/combat.py` by `make test-combat`;
the worked fight above is a test in `tests/test_core.c`.

## What this isn't (yet)

- Powers and their costs (with the power registry), opposed rolls at high level, and
  limits on stacking buffs: later, after playtests.
- Companions and Echo allies fight with the same numbers; how they're recruited is still
  an open question in [rules-v0.md](rules-v0.md).
