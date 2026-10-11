# The turn (rules v1)

*Rules v1, in the **rules lab**: the arena plays them now (the runner and the modern
arena, [arena.md](arena.md)); the game (the C64, the cartridge, the story VM) plays rules
v0 ([combat.md](combat.md)) until v1 is frozen ([rules.md](rules.md)), and then moves to
them all at once. Numbers are starting points, to be tuned in the arena.*

This page is what happens in a fight's turn: how far you move and what gets in the way,
the actions, being pushed, and conditions in play. Everything not here (the order of play,
attacks and damage, sight, the foes' rules, fleeing) is as [combat.md](combat.md) has it.

## A turn, in order

1. **It starts.** Guarding ends. If you start on a hazard, it hits you. Your conditions
   tick: damage each turn, then healing each turn. If you're knocked down, you stand up
   (it takes half your Speed). If a condition takes your turn (stunned, asleep, paralyzed,
   frozen), the turn goes straight to step 4.
2. **Move**, up to your Speed; or, instead of walking, **Blink** (a power that shifts
   you to a square: see *Powers in play*).
3. **One action**: Attack, Shove, Dash, Guard, Wait (only before you've moved, once a
   round), Flee, or Done. Swapping gear is free, any time on your turn
   ([items.md](items.md#swapping)).
4. **It ends.** Your timed conditions count down a round (not one put on this turn), and
   each that has run out ends, becoming what it turns into, if anything. Then roll to
   shake off each condition that can be shaken off.

## Speed

**Speed is 5, +1 at Grace 60, and +1 more at Grace 90** (5 to 7). **Heavy armor**
(tier 3 and up) costs 1. A foe's Speed is on its card.

Conditions move it up or down: **only the worst penalty and the best bonus count** (slowed
and chilled together are −2, not −3; slowed and hasted together are 0). Never below 0. A
condition that stops you (entangled) makes it 0 whatever else you have.

## Moving

- A step in any of the 8 directions costs 1, as on open ground. **Rough** ground and
  **cover** cost 2; **walls** and **pits** can't be entered; nor can a square with anyone
  in it.
- **Your path** is the cheapest way there; of those, the one crossing the fewest hazards.
  (At the table, trace it.)
- **Flying** (Winged, Weightless): pits and rough ground cost 1. A flyer can stop over a
  pit; if its flying ends there, it falls.
- **Leaving a foe's side** (starting next to it and ending your move not next to it) gives
  it a free attack, before you go. Being pushed never does.

## Hazards

A hazard (`^`) **hits whoever enters it, on any step** (their own move, a Dash, or being
pushed), **and whoever starts a turn on it**. A hit is **5 damage** (Soak counts) and the
hazard's condition, if it has one. A map names its hazards: **fire** (5 fire damage, on
fire), **acid** (5 energy, corroded), **ice** (5 cold, chilled), **radiation** (5 energy,
irradiated), **poison gas** (no damage type, poisoned); a plain hazard is 5 kinetic and
nothing more. Each hazard square hits you once in a move, however you cross it.

## Actions

| Action | What it does |
|---|---|
| **Attack** | as [combat.md](combat.md#your-turn) |
| **Shove** | a foe next to you: roll **Athletics** against its TN as for a melee attack. Success: it's **pushed 1 square** straight away from you; a crit pushes it 2 and **knocks it down**; at a cost, it's pushed 1, but you're **exposed** (Armor −20) for a round |
| **Dash** | instead of acting, **move again**, up to your Speed, from where you are (leaving a foe's side gives it a free attack, as any move does) |
| **Guard**, **Wait**, **Flee**, **Done** | as [combat.md](combat.md#your-turn) |

## Being pushed

A push moves a fighter a square at a time, straight away from whoever pushed it:

- Into a **wall**, or into **another fighter**: it stops, and takes **3 damage** (Soak counts).
- Into a **pit**: it **falls**, and it's out of the fight (as if down). A flyer doesn't fall.
- Into a **hazard**: the hazard hits it, and it goes on if it's pushed further.

Being pushed never gives free attacks.

## Conditions in play

The conditions are [conditions.md](conditions.md)'s, in `registry/conditions.txt`. Each one
is made of these effects (the first build: the rest come with the powers and gear that
need them):

| Effect | In play |
|---|---|
| Damage each turn | at the start of your turn; of a damage type (Soak counts) or of none (it doesn't) |
| Healing each turn | at the start of your turn, after the damage; never over your health |
| Speed | see *Speed* |
| Dodge, Armor, Ward, Soak | up or down (never below 0); *Dodge 0*: your Dodge counts as 0 |
| Rolls, attacks, melee | added to every roll you make, to your attack rolls, to your melee attack rolls |
| Next attack | added to your next attack roll; then it ends |
| Shake-off | added to your rolls to shake off conditions |
| Immune | the conditions it names never land on you; *immune to a hazard's damage type*: those hazards do you no damage |
| Lose the turn | your turn goes straight to its end |
| Knocked down | Dodge 0; at the start of your turn you stand, which takes half your Speed (rounded up) |
| Ends when hit / when healed | it ends when damage gets through to your health / when you're healed |
| Barrier N | the next N damage is taken off before your health; then it ends |
| Vulnerable | double damage of that type (after Soak) |
| Thorns N | whoever hits you in melee takes N (Soak counts) |
| No powers | you can't attack with a focus |
| No healing | healing does nothing |
| Flying | see *Moving* |
| First | you act first in the order of play (then by Grace) |

**Getting one.** An attack or a weapon that carries a condition puts it on whoever it hits,
a glancing hit too; a hazard on whoever it hits; a race's two traits are on from the start,
always; a scenario or a story can put one on as a fight begins.

**Shaking one off.** At the end of your turn: **d100 + the stat it names + your shake-off
bonuses + your roll bonuses, against its TN**. A success or a crit ends it; a cost doesn't.
A foe's card has no stats but Grace, so a foe shakes off everything with its Grace.

**The same one twice** doesn't stack: the longer time counts. **Opposites cancel**: on fire
and soaked, hasted and slowed, blessed and cursed; the new one goes on and the old one ends.
**Immune** means it never lands.

**At most 4 at a time**, besides a race's two traits. A fifth replaces the one with the
fewest rounds left (one with no countdown counts as the most).

## Powers in play

A power (`registry/powers.txt`, the class lists of [items.md](items.md#power-lists)) is a
**shape** and an **element**, at will or with **charges** (full at each fight's start, in
the arena; at each Departure's, in the game). Using one is your turn's action.

- **Tier** is 1 + rank ÷ 20 (rank 0-19: tier 1; rank 100: tier 6).
- **Its roll** is d100 + **half its class's stat** (a Channeler's Presence, a Warden's
  Might) **+ its rank**, as a skill is half a stat plus its training; plus your roll and
  attack bonuses. A new power's rank is 2 × your level (at least 10).
- **Its TN** is 50 + Dodge + **Ward**, + 20 in cover, as any power's is; a **mind** power's
  is against **Resolve** (half the target's Presence: a foe's, half its Grace) instead of
  Ward.

| Shape | Target | What it does |
|---|---|---|
| **Bolt** | a foe in sight | damage 5 × tier, as a weapon's (margin, crits, glancing hits) |
| **Burst** | a square in sight, not so near that you're in it; or **around** you | everyone in Area 1 (2 from tier 6) round it, friend or foe, one roll; damage 5 × tier |
| **Hex** | a foe in sight | half a bolt's damage (5 × tier ÷ 2, rounded up), and **hexed**: −10 × tier to its attacks for 3 rounds |
| **Ward** | you, or a traveler next to you | its condition, at its tier (shielded: Armor + 10 × tier) |
| **Mend** | you, or a traveler next to you | heals 5 × tier, and puts on its condition (Second wind: regenerating) |
| **Field** | a square in sight, on open or rough ground | a line of tier + 2 squares through it, across the line from you, for 3 of your turns: fire or energy (a hazard: 5 × tier, and its condition), cold (rough ground), kinetic (wall), mind (cover). Not on anyone's square |
| **Shift** | yourself to a square; or a foe next to you | yourself: straight there (8 ways), up to tier + 2 squares, through nothing that blocks sight, and no free attacks for leaving. **It's your move, not your action**: instead of walking, from where you start, and then you act from where you land (a shot, a Shove, a Dash, another power); a foe: rolled against its Ward, pushed tier + 2 squares away (as a Shove's push: pits, walls, hazards) |

A hit (Bolt, Burst, Hex) also puts on the power's **condition** at its tier, and its
element's **rider**: **fire** burns the target's square till the end of your next turn
(5 × tier, a hazard); **cold** chills it; **kinetic** pushes it a square; **energy**
ignores its Soak; **mind** is against Resolve. **Silenced** stops all of it.

A **foe** can hold powers too (a scenario or a Departure gives them): its card has no class
stat, so a foe's power rolls its **Attack**, and its rank sets only the tier.

### How the computer uses powers

On Quick and Auto, and for foes, the computer moves as it always has ([combat.md](combat.md#foes)),
then takes the **first** of these it can, from where it ends up; if none, it uses its weapon:

1. **Mend** you, or a friend next to you, at half health or less (the most hurt first).
2. **Blink**, as your move, if you shoot and a foe is next to you: to where fewer melee
   foes could reach you next turn (within their Speed and a step) than where you stand;
   of those, where the fewest can, then where you can still shoot someone, then furthest
   from them. Then the rest of this list, and your weapon, from where you land. If
   nowhere is better, you stay and shoot.
3. **Shove with a power** (Bull rush) a foe next to you that it would drop in a pit or
   onto a hazard.
4. **Burst** where it catches two foes or more, and none of your side.
5. **Ward** a friend next to you who hasn't its condition, with a foe within 3 squares of
   them; yourself only when there's nobody to attack this turn.
6. **Hex** the foe with the best Attack that isn't hexed (or under the power's condition)
   yet, has health for three of your weapon's hits, and that you've a 30% chance or more
   to hit.
7. **Bolt**, when its expected damage (chance × damage less Soak) beats your weapon's, or
   your weapon can't reach anyone.
8. **Field** across the way of a melee foe 3 to 6 squares from you, halfway, if you shoot.

The same in the same place always makes the same choice, so the arena's numbers repeat,
and a player can read a foe.

## Races in play

A traveler's race puts on its two traits ([races.md](races.md#traits)): Lucky (+5 to every
roll) and Steady (+10 to shake off) for a Human; Plated (Armor +10) and Knightly (immune:
frightened) for the Salvaged; Early (first in the order) and Small (Dodge +5) for a
Chronomite; and so on. Lantern-eyed waits for darkness to be in the rules.

## What's checked

The rules lab's engine (`core/next/battle.c`, the same house rules as the core, so it can
replace `core/src/battle.c` at the freeze) is held to these rules by `make
test-rules-next`: reviewed battles in `tests/battle-next/` (moving, hazards, shoves, dashes,
falls, every kind of condition), each roll re-checked from the Python reference
(`tools/rules/turn.py`); the reference and the C agree on Speed, TNs, damage and shaking
off for random fighters and conditions; and random battles never crash under the
sanitizers.

## Still open

- **Phased** (through walls, untouchable), **hidden**, **spreading**, **at random**,
  **must attack**: the medium effects, with the powers that need them (Taunt, Smoke,
  Vanish, Mind spike's confusion: until then Mind spike frightens).
- **What the arena says about powers** ([arena.md](arena.md#first-findings), 1000 fights a
  scenario, the computer playing them as above). After the second pass (hexes hurt,
  Ground slam stuns, Second wind regenerates, Blink a move): a Medic beside a
  Warden lifts them from 80% to 91%; a Tinker's powers take a fight nobody wins to 9%; a
  Rogue's hexes from 49% to 69%; a Warden's four from 14% to 91% against two guards and a
  rat. **Bull rush by a pit is the strongest thing in the game** (84% alone): a fall is out
  of the fight, and whether it should be (rather than damage and a turn to climb out) is
  open, with Shove's. A **stunning Ground slam** (66% alone) may be too much for one
  charge. **Blink is a move now**: the computer uses it only to get where fewer foes can
  reach it, and in the arena's small rooms there's never such a square three squares away
  (a rat's reach is 7), so it's the player's tool there: a way past a wall, a pit or a
  line of foes, before the shot.
- Whether a fire hit should both burn the square and set the target on fire (Fireball,
  Fire wall do both now): fire is strong.
- Foes with a shove or a knockback of their own, and **teleporting** (no free attacks).
- Whether heavy armor should say so in the registry, rather than by its tier.
- Darkness, for Lantern-eyed and the dark realms.
