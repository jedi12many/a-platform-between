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
2. **Your move action**: walk up to your Speed; or, instead of walking, **Blink** (a
   power that shifts you to a square: see *Powers in play*). You can stay put.
3. **Your standard action**: one of the actions below (Attack, a power, Shove, Dash,
   Guard, Wait, Flee, or Done). Swapping gear is free, any time on your turn
   ([items.md](items.md#swapping)).

   Steps 2 and 3 come **in either order**: an Attack, a power, a Shove or Guard can come
   first, from where you stand, and then you move (shoot, then step back). Dash, Wait and
   Flee can't: each ends the turn.
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

**A turn is one move action and one standard action, in either order; swapping gear is
free.** That's all a player has to track, at the table or on the C64. Act first (an
Attack, a power, a Shove or Guard, from where you stand), and the move is still yours;
move first, and your action ends the turn. Dash, Wait and Flee can't come first: each
ends the turn. The computer's fighters move first.

| Kind | What it is |
|---|---|
| **Move action** | walk up to your Speed (standing up, if you're knocked down, takes half of it), or **Blink** |
| **Standard action** | **Attack**; **a power** (but Blink, which is a move); **Shove**; **Dash** (a second move, in place of acting); **Guard**; **Wait** (only before you've moved, once a round); **Flee**; **Done** |
| **Free** | **swap gear** from your pack ([items.md](items.md#swapping)), any time on your turn |

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

**Shaking one off.** At the end of your turn: **d100 + your shake-off bonuses + your roll
bonuses, against the condition's number, less the level gap**: 2 for each level you're
above whoever put it on (2 more for each below; a hazard of the map's is level 0). A
success or a crit ends it; a cost doesn't. Two fighters of the same level shake each
other's off as easily at level 1 as at 50; a level makes the defense against conditions,
and no stat does (the Human's Steady: +10 to shake off).

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
- **Its TN** is 50 + Dodge + **Ward**, + 20 in cover, as any power's is; a **hex**'s, or
  any **mind** power's, is **50**, + 20 in cover; and, as every roll's, less the level gap
  (*Levels and gear*): a condition is resisted by level, not by a stat.

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
ignores its Soak; **mind** is against 50, not Ward. **Silenced** stops all of it.

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

## Levels and gear

**The level gap.** Every roll against a fighter (an attack, a power, a shove) has its TN
lowered by **2 for each level the roller is above them**, and raised by 2 for each level
below; shaking off a condition, the same against whoever put it on. A level 5 traveler
against level 1 rust-guards: 8 easier to hit them, 8 harder for them to hit back. Two of a
level cancel out, at level 1 or at 100, so the numbers stay small (a byte, on the C64) and
the bestiary's foes needn't chase the travelers ([bestiary.md](bestiary.md)). Every foe's
card has its level.

**Gear steps more gently.** A weapon of tier T deals **2 + 3T** (5, 8, 11, 14...), and
armor of tier T is **Armor 5 + 5T** (10, 15, 20...), where rules v0 had 5T and 10T: the
first tier is the same, and each tier after it adds 3 damage and 5 Armor, not 5 and 10.
(Powers keep their 5 × tier: a power's rank grows with the level already.)

Why: in v0 a tier of gear was worth about eight levels. A Warden against two rust-guards
won 12% at level 1, 30% at level 4, then 80% at level 5, where the quick builder's sword
and coat go up a tier: four levels of nothing, then a cliff. Now: 12%, 52% at level 4
(R-16), 80% at level 5 with the new gear (R-17), and every level counts on the way.

| A Warden vs two rust-guards | Level 1 | 3 | 4 | 5 | 7 | 9 | 12 |
|---|---|---|---|---|---|---|---|
| Rules v0's levels and gear | 12% | 23% | 30% | 80% | 88% | 93% | 100% |
| Rules v1 (gentler gear, the level gap) | 12% | 33% | 52% | 80% | 93% | 98% | 100% |

(First built as a bonus of 2 a level for travelers, which came out the same against these
level 1 foes but grew past a byte at high levels: a level 100 traveler's TN would have
been about 318. The gap keeps every number as small as two equals make it.)

## After a fight

**If one traveler is standing, everyone survives.** When a fight ends with any traveler
still on their feet (won, or fled with anyone out), the whole party comes through it:
every traveler, those who went down too, is **back at full health**, and their conditions
end (a race's traits stay). Only when **every** traveler is down is the fight lost, as
[combat.md](combat.md#ending-a-fight) has it: back to the Waystation, Debt up, and the
story's `lost:` branch.

For now, every fight survived ends at full health: there's no health carried from fight
to fight, no rests and no bandaging to keep track of, at the table or on the C64. A power's
charges still last the Departure. Whether health should carry over again (with rests and
healing between fights) comes back with longer Departures; it's in *To revisit*.

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

## To revisit

Decided for now, to come back to after more playtests:

- **Pits and cliffs are a higher level's challenge.** A shove or a bull rush into a pit is
  out of the fight, and it's the strongest thing in the game (R-02, R-11: Bull rush alone
  84%); it stays, because shoving things off is fun. Later, hazards may have levels, and a
  pit or a cliff on a map be for higher-level fights (or a fall be damage and a turn to
  climb out, at low levels).
- **Ground slam or Shockwave.** A stun for everyone round you, for one charge, may be too
  strong: on an open floor a new Warden's slam alone takes two rust-guards and a rat from
  4% to 29%. Shockwave is the alternative being tried: the same burst, but **staggered**
  (−20 × tier to each one's next attack) instead of stunned: 17%. With all four powers,
  R-13 (Ground slam) is 39% and R-14 (Shockwave) 27%. By a pit, the push into it is what
  wins, and the two come out the same (66%).

- **How much a level is worth.** 2 a level, the same scale as a power's rank. Measured
  at 3× and 5× too (as Resist, before the gap): a level 6 Warden's hexers needed 62, 68 or
  80 to land, but R-15 hardly moved (38%, 38%, 40%): what their hexes cost him is their
  damage and the slow, not how often they land. Stats may add to Ward later, if it
  doesn't make Grace and the like worth more than the rest.
- **Class against class.** At every level the standard foe is fair on average (80%), but
  on the arena's open floor a Channeler wins 93-98% and a Warden 55-82%: shooters get free
  rounds while a melee foe crosses ([bestiary.md](bestiary.md)). **Decided, for now:** left
  as it is; a Departure's map decides it (cover, corners, close quarters).

- **Health between fights.** For now, full after every fight survived (*After a fight*).
  Longer Departures may want it to carry over, with rests, healing items and the Medic's
  mends mattering between fights as well as in them.

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
