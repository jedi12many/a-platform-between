# The bestiary

*Draft for review. The numbers are starting points, to be tuned in the arena
([arena.md](arena.md)), not yet applied to the registry.*

Foes live in `registry/foes.txt`, one line each, shared by every Departure; a foe card at
the table prints the same numbers ([combat.md](combat.md#whos-in-a-fight)). This page is
how to make one: what a foe of a given level looks like, what its role changes, and how
many make a fight. A Departure copies a foe's numbers when it's compiled, so tuning a foe
here never changes a Departure that has shipped.

## What a foe is measured against

A traveler, as the arena's quick builder makes one (a sensible build, not the best), with
gear a tier up every 5 levels:

| Level | Health | Attack | TN to hit them (weapons) | TN (powers) | Weapon damage |
|---|---|---|---|---|---|
| 1 | 29 | 62 | 64-74 | 64 | 5 |
| 5 | 37 | 72-78 | 74-84 | 64 | 10 |
| 10 | 47 | 85-91 | 84-94 | 64 | 15 |
| 20 | 68 | 92-102 | 104-114 | 64-70 | 25 |
| 40 | 110 | 92-102 | 148-154 | 68-70 | 45 |
| 100 | 235 | 100 | 150-160 | 70 | 45 |

Two things stand out, and the foes have to be built round them until the rules change:
travelers have **no Ward** of their own (only what items and powers give), so a foe's
powers hit far more easily than its weapons; and past level 40, **gear has topped out**
(tier 9) while health keeps rising.

## A standard foe

A **standard** foe of level *L* is a fair fight for one traveler of level *L*: the
traveler should win about **4 times in 5**, with something like a third of their health
left. The Fare's rust-guard against a new Warden is the model (82% in the arena).

| Level | Health | Attack | Damage | Armor | Ward | Soak | Grace |
|---|---|---|---|---|---|---|---|
| 1 | 20 | 45 | 6 | 20 | 10 | 1 | 20-50 |
| 5 | 40 | 55 | 8 | 30 | 15 | 2 | 20-50 |
| 10 | 60 | 65 | 10 | 40 | 20 | 3 | 30-60 |
| 20 | 100 | 85 | 14 | 60 | 30 | 4 | 30-60 |
| 40 | 180 | 120 | 22 | 80 | 40 | 6 | 40-70 |
| 70 | 280 | 130 | 30 | 90 | 60 | 8 | 40-70 |
| 100 | 380 | 140 | 38 | 90 | 80 | 10 | 50-80 |

The reasoning, so it can be redone when the rules move:

- **Health**: three or four of a same-level traveler's hits.
- **Attack**: hits the band's Warden a little over half the time (attack ≈ their TN − 40).
- **Damage**: about a fifth of a same-level traveler's health a hit.
- **Ward**: **never 0**: half its Armor for a thing of flesh or metal, but **equal to its
  Armor for a brute** (see below); its Armor or more for anything magical. A foe that really has no defense against powers says so with a
  **weakness** instead (printed, and fair).
- **Speed**: 4, as a traveler's; Grace sets its place in the order and its Dodge (÷ 5).

## Roles

A role changes the standard foe's numbers, and its behaviour on the card:

| Role | Changes | Behaviour | Like |
|---|---|---|---|
| **Brute** | health × 1.5, Armor +20, Grace −10 | charge | rust-guard |
| **Skirmisher** | health × 0.75, Grace +20, Speed +2 | charge, coward | |
| **Shooter** | health × 0.75, Armor −10, ranged | shoot | scrap gunner |
| **Caster** | health × 0.6, Ward = Armor + 20, power reach (against Ward), Area 1 at level 5 and up | shoot | |
| **Guardian** | Armor +30, Soak × 2 | guard | maintenance drone |
| **Swarm** | health × 0.3, damage × 0.5, Grace +20 | charge, coward | ash rat |
| **Boss** | health × 4, attack +10, Soak × 2 | by its card | |

## How many make a fight

Count each foe's **threat**: a standard foe of the party's level is 1; a brute 1.5; a
swarm member 0.3; a boss 4; a foe 5 levels above the party counts double, 5 below half.

| Threat for each traveler | Feels like |
|---|---|
| ½ | a warm-up |
| 1 | a fair fight: the party usually wins, and feels it |
| 1½ | hard: someone goes down, the party might run |
| 2 or more | a wall, unless the story gives a way round it |

The arena checks a fight before a Departure ships: `fights 1000` of the party's level
against the encounter, and the win rate should match what the story wants.

## The bestiary today, measured

The four foes in the registry, against this page and the arena's findings. **Applied**:

| Foe | Role, level | Was | Now |
|---|---|---|---|
| Rust-guard | brute, 1 | Ward 0 | Ward 10 |
| Scrap gunner | shooter, 1 | damage 4, Ward 0 | damage 6, Ward 5 |
| Ash rat | swarm, 1 | Ward 0 | Ward 5 |
| Maintenance drone | guardian, 1 | Ward 0 | Ward 15 |

What the arena says after (a new traveler of each class, 1000 fights):

| | Warden | Rogue | Tinker | Channeler | Medic |
|---|---|---|---|---|---|
| Rust-guard, before | 82% | 88% | 79% | 99% | 79% |
| Rust-guard, after | 82% | 88% | 79% | **96%** | 79% |
| Scrap gunner, before | 100% | 100% | 100% | 100% | 100% |
| Scrap gunner, after | 98% | 99% | 98% | 98% | 98% |

The fixes help less than hoped, and the arena says why:

- **Ward at half the Armor is still easier to beat.** Against Ward 10 a power needs 64,
  a weapon against Armor 20 needs 74. Tried at **Ward 20** (equal to its Armor), the
  Channeler wins **87%**, level with the Rogue's 88%. **Decided: a brute's Ward equals its
  Armor** (the rust-guard's goes to 20). It goes into the registry after the first round
  of playtesting, so testers' notes on scenarios A-02 and A-03 are about the numbers they
  played; those two scenarios change with it, under new codes.
- **Distance is half of it.** On an open floor anyone who shoots gets free rounds while a
  melee foe crosses it. Started next to the rust-guard, the Channeler wins 83%, as a
  Warden does. That's the battle map doing its job; a Departure's map decides it.
- **A weakness opens Armor only.** A Rogue shooting energy at the rust-guard (weak to
  energy) wins 99%. That's what a weakness is for.
- **A lone shooter is meant to be weak.** Even at the shooter's full numbers (Armor 10,
  attack 45) a new traveler beats one gunner 97-98% of the time; but **two gunners beat a
  new Warden 73% of the time**. Shooters come in groups.

The VM's fight tests (`tests/vm/fights.qs`) changed with the gunner's damage (each hit 2
more); The Fare's and Eighteen Minutes' routes didn't, as their travelers fight with
weapons, but their images (and The Fare's trip code) did.

## Still open

- Travelers have no Ward of their own. A base Ward (from Presence, as Dodge comes from
  Grace?) would make foes' powers fairer, and the Caster role less of a hammer.
- Levels past 40: gear stops at tier 9, so foes there mostly grow in health. Higher tiers,
  legendary items or powers may have to carry the late game.
- The arena should take a foe card inline (not only a registry name), so a new foe can be
  tried before it's in the registry.
