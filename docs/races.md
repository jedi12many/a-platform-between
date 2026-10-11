# Races

*Draft for review. The numbers are starting points, to be tuned in the arena
([arena.md](arena.md)). The stat bonus is in the engine; the rest isn't yet.*

A race gives a traveler three things: **a stat bonus**, **a body** (what they can wear and
hold), and **two traits**. New races (four arms, wings, a serpent's tail) come later, once
the rules and the tools to design, draw and test them are ready; this page is the frame
they'll fit.

## The stat bonus

**+10 to one stat**, as now ([rules-v0.md](rules-v0.md#character-creation)).

## The body

Every traveler is **medium-sized**: there are no giants. Some races are **Small**, which is
a trait (below), not fewer slots.

**Everyone has the same slots**, the ones a human has:

| Worn (8) | | Held (2) |
|---|---|---|
| Hat (or helm, hood, crown) | Belt | Hands: 2. A weapon, a focus, a shield, a torch; a staff, a rifle or a greatsword takes both |
| Armor (or robe, coat) | Boots | |
| Gloves (or gauntlets) | Ring, ring | |
| | Necklace | |

**An item says which slot it takes**, and armor and robes have a **cut**: cut for a medium
body, or for a small one. Rings, a necklace, a belt fit anyone. A Small traveler needs
small-cut armor; one who finds armor made for them has found something worth keeping. A
future race with an unusual body (four arms) works the same way: its own cut, and items
made for it, so "armor crafted for it" is ordinary loot.

**The pack** holds **6** items, whatever you boarded with and whatever you find. Swapping
between your pack, your hands and your worn slots is free, on your turn or any time
([items.md](items.md#swapping)): out of time means out of the usual fuss.

**Nothing found is lost.** When the pack is full and you find something, you choose what
goes to the **lost-and-found**: the new thing, or something you're carrying. It's waiting
at the Waystation, which keeps your lost-and-found with your traveler, with no limit, and
where you swap things between it and your pack and slots between trips. A Departure brings
home at most **8 new items** (the Travel Stamp's limit). Only consumables that are used up
are gone for good.

## Traits

Every race has **two traits**, and they're **conditions that never end**
([conditions.md](conditions.md)): the same effects as a shield spell or a poison, always
on. No drawbacks, for now.

| Race | +10 | Trait | Effects | Trait | Effects |
|---|---|---|---|---|---|
| **Human** | Fate | **Lucky** | +5 to all rolls | **Steady** | +10 to shake off conditions |
| **Hollowborn** | Grit | **Hollow** (no blood, no breath) | Immune: poisoned, bleeding | **Unsleeping** (a contract doesn't rest) | Immune: asleep, paralyzed |
| **Glassfolk** | Wits | **Prismatic** (light bends around them) | Ward +10 | **Clear** (memories as light) | Immune: blinded |
| **Rad-Dryad** | Presence | **Rad-fed** (radiation is food) | Immune: irradiated, and hazards' energy damage | **Rooted** | Soak +2 |
| **Chronomite** | Grace | **Early** (a split second out of sync) | First in the order of play | **Small** | Dodge +5; small-cut armor |
| **Salvaged** | Might | **Plated** (a knight's shell) | Armor +10, with or without armor worn | **Knightly** (it believes it) | Immune: frightened |
| **Moth-folk** | Presence | **Winged** | crosses pits; rough ground costs 1 | **Lantern-eyed** | Immune: dark |

These are a first pass, matched to each race's concept in the
[world bible](world-bible.md#playable-races-first-pass). Two things to watch in the
arena: traits are worth more than the +10 (Lucky touches every roll), and some are worth
more in some places than others (Rad-fed in the Ashmouth wastes, Winged on a map of pits).

## What it needs from the engine (later)

- **The Passport**, a new version: 10 equipped slots (8 worn, 2 hands) where it has 6.
  Older Passports still read; their items go to the slots that fit them, the rest to the
  pack. ([passport-spec.md](passport-spec.md).)
- **The registry**: each item's slot and cut; each race's two traits (condition ids);
  conditions themselves ([conditions.md](conditions.md#what-it-needs-from-the-engine-later)).
- **The Waystation**: the lost-and-found kept with the traveler, and the screen to swap
  between it and the pack and slots.
- **Fights**: a traveler's conditions from their race, put on as the fight starts.

## Later

- **New races**, with new bodies: four arms, wings, a tail. Designed with the art desk and
  tested in the arena first.
- **Drawbacks**: a race with a quirk as well as a boon, if it's worth the balancing.
