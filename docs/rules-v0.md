# Rules v0

A first proposal. Everything here is open for change.

## Hard constraints

- Whole numbers only. Every stored value fits in a byte (0–255); most are far smaller.
- One deterministic random-number generator, identical on every platform, so a given seed
  produces the same fight on the C64 and on Windows.
- Small numbers on purpose (bounded accuracy): a level-1 goblin should still matter a
  little at level 15.

## Stats

Six stats, rated 1–9 at creation (typical 3–5), cap 12.

| Stat | Covers |
|---|---|
| **Might** | Melee, carrying, forcing doors |
| **Grace** | Ranged, dodging, stealth, fine work |
| **Grit** | Health, resisting poison and fear |
| **Wits** | Tech, lore, noticing things |
| **Presence** | Talking, leading, intimidating, channeling |
| **Fate** | Luck, timing, how the multiverse treats you |

## The core roll

**2d6 + stat + skill bonus** (if any) vs. the situation.

| Total | Result |
|---|---|
| 12+ | Full success, with something extra |
| 9–11 | Success |
| 6–8 | Success at a cost, or partial |
| 5 or less | Failure, and things move |

2d6 gives a bell curve that's easy on 8-bit math, and the "success at a cost" band keeps
stories moving rather than stalling on misses.

## Classes

Classes describe what you *do*, not what genre you're in, so they translate cleanly.

| Class | Does | Key stats |
|---|---|---|
| **Warden** | Stands in front, protects, takes hits | Might, Grit |
| **Rogue** | Sneaks, steals, strikes first | Grace, Fate |
| **Tinker** | Builds, repairs, hacks, jury-rigs (gadgets translate to charms and traps) | Wits |
| **Channeler** | Spells, psionics, nanites: whatever the realm calls it | Presence |
| **Medic** | Heals, cures, keeps you going | Wits, Grit |

## Levels and perks

- Levels 1–20. Each level: +1 to a stat (cap 12) *or* a skill, plus health.
- A **perk** every level: where the weird specialization lives (Fallout-style).
- Departures have a **level band** (e.g. 1–5, 4–8) and soft-scale if you arrive over it.

## Health and death

- Health = Grit × 3 + level × 2, roughly. Tuned in playtest.
- At 0 health you are pulled back to the Waystation. The Departure can be retried; your
  Debt goes up significantly. No permadeath.

## Inventory

- 6 equipped slots + 6 pack slots. Hard limit; forces choices and keeps the Passport small.
- Up to 2 **attuned** legendary items.

## Combat style (proposal)

Turn-based, small grid or zones, solo hero plus optional companions/allies (Echo allies
join here). Turn-based is the easiest to keep identical across five platforms.

## Open questions

- 2d6 vs. d20: 2d6 proposed above; revisit after paper playtests.
- Companions: recruitable per Departure only, or carried on the Passport?
- How fast does Debt go down per Departure? (Target: ~8–12 Departures to go home.)
