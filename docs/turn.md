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
2. **Move**, up to your Speed.
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
  **must attack**: the medium effects, with the powers that need them.
- Foes with a shove or a knockback of their own, and **teleporting** (no free attacks).
- Whether heavy armor should say so in the registry, rather than by its tier.
- Darkness, for Lantern-eyed and the dark realms.
