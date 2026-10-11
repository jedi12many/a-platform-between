# Conditions

*Draft for review. The numbers are starting points, to be tuned in the arena
([arena.md](arena.md)). Nothing here is in the engine yet.*

A **condition** is something true of a combatant for a while: poisoned, asleep, on fire,
slowed, shielded. It's one system for everything that changes a fighter for a time, or for
good:

| A condition comes from | It lasts | For example |
|---|---|---|
| **Your race** | always | Lucky, Small, Plated, Winged ([races.md](races.md)) |
| **An item or a power** | some rounds, or while it's worn or held | a shield spell; a ring against fire |
| **A foe's attack** | until it ends or you shake it off | poisoned, asleep, on fire |
| **The map** | while you stand there, or after | a fire square sets you on fire |
| **The Departure, or its realm** | the whole trip, or a scene | thin air: everyone slowed; radiation |

Race traits are conditions that never end, so there's one rule for all of it, at the table
and in the engine.

## What a condition does

Every condition is made of a few **effects** from one short list, each with a number. No
condition needs a rule of its own.

| Effect | What it does |
|---|---|
| **Lose the turn** | no move, no action |
| **Damage each turn** | N damage at the start of your turn, of a damage type (Soak counts) |
| **Speed** | ± N squares of movement (to 0 at least) |
| **Dodge**, **Armor**, **Ward**, **Soak** | ± N to that defense |
| **Rolls** | ± N to your rolls: all of them, attacks only, or one skill |
| **Shake-off bonus** | + N to shaking off conditions |
| **Immune** | named conditions can't be put on you |
| **First** | you act first in the order of play |
| **Movement** | you can cross pits, or rough ground costs you 1 |

## Getting one, and losing it

- **Put on by an attack.** An attack, a power or a hazard that carries a condition puts it
  on whoever it hits (a glancing hit too). A Hex, cold's slow and fire's burn
  ([items.md](items.md#elements)) are conditions like any other.
- **Wearing off.** A condition with rounds (`3 rounds`) ends at the end of your turn when
  they run out. Count down at the end of each of your turns.
- **Shaking it off.** At the end of your turn, roll once for each condition that can be
  shaken off: **d100 + the stat it names, against its TN.** Success, it's gone. (The one
  roll the game already has; TN 100 is a normal difficulty, as in
  [rules-v0.md](rules-v0.md).)
- **Ending on a trigger.** Some end when something happens: asleep ends when you're hit.
- **The same condition twice doesn't stack.** The stronger one counts, and the longer time.
- **Immune** means it never lands; nothing to roll.

## The conditions

Starting numbers; each is a line in a registry (`registry/conditions.txt`, append-only like
the others), so a Departure, an item or a power names it and gets the same numbers
everywhere.

### Harmful

| Condition | Effects | Ends |
|---|---|---|
| **Poisoned** | 3 damage each turn (no type: Soak doesn't count) | shake off: Grit, TN 100; or 5 rounds |
| **On fire** | 5 fire damage each turn | 3 rounds; or shake off: Grace, TN 90 (you beat it out) |
| **Bleeding** | 2 damage each turn | a Medicine check, or any healing |
| **Asleep** | lose the turn; Dodge 0 | when hit; or shake off: Wits, TN 110 |
| **Paralyzed** | lose the turn; Dodge 0 | 2 rounds; or shake off: Grit, TN 120 |
| **Stunned** | lose the turn | 1 round |
| **Slowed** | Speed −2 | 2 rounds |
| **Entangled** | Speed 0 (you can still act) | shake off: Might, TN 100 |
| **Blinded** | −30 to attacks | 2 rounds; or shake off: Grit, TN 100 |
| **Frightened** | −10 to rolls; can't move closer to what frightened you | shake off: Presence, TN 100 (against Resolve) |
| **Exposed** | Armor −20 | 2 rounds |

### Helpful

| Condition | Effects | Ends |
|---|---|---|
| **Shielded** | Armor + 10 × tier | 3 rounds (the Ward shape, [items.md](items.md#shapes)) |
| **Warded** | Ward + 10 × tier | 3 rounds |
| **Hasted** | Speed +2 | 3 rounds |
| **Regenerating** | heal 3 each turn | 5 rounds |

### Of a place

A Departure can put a condition on everyone, for the whole trip or a scene, or on a square
of a battle map: a field ([items.md](items.md#elements)) or a hazard (`^`, which today does
5 damage) is a square that puts its condition on whoever enters it or starts a turn there.

| Condition | Effects | For example |
|---|---|---|
| **Thin air** | Speed −1 | a mountain realm |
| **Irradiated** | 2 energy damage each turn | the Ashmouth wastes |
| **Dark** | −20 to ranged attacks | an unlit undercroft |

### Of a race

Each race has two, always on ([races.md](races.md#traits)): **Lucky**, **Small**,
**Plated**, **Hollow**, **Winged** and the rest are conditions with no end.

## At the table

A token on the mini (or a note beside it) for each condition, with a d6 for its rounds
left. At the end of each of your turns: count down, then roll to shake off. A race's two
are printed on the character sheet.

## What it needs from the engine (later)

- **A registry** of conditions (`registry/conditions.txt`): each one's effects and numbers,
  how it ends (rounds, a shake-off stat and TN, a trigger), and what it's immune to. About
  20 to start; ids up to 255.
- **Each fighter** keeps the conditions on it and their rounds left: a few bytes, so the
  C64 and the cartridge can carry it. The battle engine applies them at the start and end
  of each turn, and the battle screen shows them by the fighter's name.
- **Foes** can carry conditions on their attacks (a column in `registry/foes.txt`), and
  their own permanent ones (a skeleton: Immune to poisoned and asleep).
- **Items and powers** name a condition, not a special rule: a ring of fire resistance is
  "while worn: Immune to on fire".
- **The arena** measures each one: how much poisoned 3 a turn is worth against a
  rust-guard, what Small does to a Rogue's chances.

## Still open

- Whether a condition can be put on by a **glancing** hit, or only a full one.
- **Resistance** short of immunity (half the rounds?), if two kinds turn out to be needed.
- Conditions in the **story** (outside a fight): poisoned between scenes, a curse for a
  whole Departure, and how a check cures them.
