# Items and powers

*Draft for review. Every number here is a starting point for playtests, as in
[combat.md](combat.md). Nothing here is in the engine yet.*

Items and powers are where a traveler's choices show in a fight: the sword swung every
round, the wand that throws fire for as long as you like, the staff with two ice walls in
it for the whole trip, and the shotgun that stays a shotgun in 1300 AD. One small set of
rules covers all of it, the same on a C64 and at a kitchen table, with no spell lists.

## Carrying

A traveler has **6 equipped items**, ready to use, and **6 in the pack**. On a trip,
anything given when the pack is full waits in the lost-and-found at the Waystation. (The
Passport already stores both lists: [passport-spec.md](passport-spec.md).)

### Slots

The equipped six are **typed**, by the traveler's **body**, which comes from their race:

| Slot | Holds | Most races | Four-armed races |
|---|---|---|---|
| **Hands** | weapons, foci, shields | 2 | 4 |
| **Body** | armor | 1 | 1 |
| **Kit** | everything else: tools, charms, grenades, belts | 3 | 1 |

An item takes **1 hand**, or **2** if the registry says so (a staff, a rifle, a
greatsword, a chainsaw). Two daggers fill two hands; a four-armed traveler can hold four,
or a rifle and two daggers. The six slots always add up to six, so the Passport doesn't
change: a body only says how the six are typed.

### Swapping

Out of time means out of the usual fuss: **on your turn you can swap any equipped item
with any item in your pack, as often as you like, and it costs nothing.** Pull a wand from
the pack and use it this turn; change your armor mid-fight. Your slots must add up when
your turn ends, and whatever is equipped then is what defends you until your next turn.

## Using an item

Every usable item has an **at-will** use, a **charged** use, or both:

- **At will**: as often as you like, one use as your turn's action. A sword's swing, a
  basic wand's fire bolt, a pistol's shot.
- **Charged**: a bigger effect with a few **charges**, ticked off as you use them. An ice
  wall, a shield, a heal, a grenade.

> **Every Departure starts full.** Charges, like health, reset at the start of each
> Departure. A Departure may grant a rest (a night at the inn, a safe room) that
> refills them; a dungeon doesn't.

An item with **1 charge that's gone when it's used** is a consumable: a grenade, a
scroll, a potion. It leaves your sheet (and goes on the receipt as lost).

| Item | Hands | At will | Charged |
|---|---|---|---|
| Sword | 1 | strike | none |
| Basic wand (fire) | 1 | **Bolt** + fire | none |
| Staff of winter | 2 | **Bolt** + cold | **Field** + cold, 2 charges |
| Holy symbol | 1 | none | **Mend**, 3 charges; **Ward**, 2 charges |
| Riot shield | 1 | +Armor while held | **Ward** on an ally, 1 charge |
| Frag grenade | kit | none | **Burst** + kinetic, 1 charge, used up |
| Sawn-off shotgun | 2 | **Bolt** + kinetic, Area 1 | none |

The registry gives each item its uses: [Registry](#registry) below.

## Effects: shape and element

There's no spell list. Every effect, from a wand, a power, a grenade or a holy symbol, is a
**shape** and an **element**, at the item's **tier** (1-9). Translation renames it for
the realm; the numbers never change ([translation.md](translation.md)).

### Shapes

| Shape | Roll | What it does |
|---|---|---|
| **Bolt** | attack, against Ward | one target in sight; damage **5 × tier**, as a weapon's |
| **Burst** | attack, against Ward | Area 1 (Area 2 from tier 6): every combatant in it, rolled once, as in [combat.md](combat.md#area-attacks); damage 5 × tier |
| **Ward** | none | you or an ally in sight: **+10 × tier** to Ward, or to Armor (the item says which), for 3 rounds |
| **Field** | none | a line of up to **tier + 2** squares in sight, each touching the last, for 3 rounds: what the squares become depends on the element (below) |
| **Mend** | none | you or an ally next to you: heal **5 × tier** |
| **Hex** | attack, against Ward | one target in sight: **−10 × tier** to its attacks for 3 rounds, and the element's rider |
| **Shift** | against Ward if unwilling | move yourself, or one target in sight, up to **tier + 2** squares in a straight line; not through walls |
| **Sense** | none | outside fights: + 10 × tier to one check to find, read or understand something |

The attack roll is the item's skill: **Channel** for a focus (wand, staff, holy symbol),
**Ranged** for a gun or a thrown grenade, **Melee** for a weapon. Margin, crits and
glancing hits work as for any attack.

### Elements

The five damage types the game already has. Each adds one small **rider**, so a fire
bolt and an ice shard feel different without either needing a page of rules:

| Element | Bolt, Burst, Hex rider | A Field of it becomes |
|---|---|---|
| **fire** | the target's square burns (a fire square) until the end of the next round | **fire**: hurts anyone who enters it or starts a turn in it, 5 × tier, once a turn; Soak counts |
| **cold** | the target's Speed −2 on its next turn | **ice**: rough ground (costs 2 to enter) |
| **kinetic** | the target is pushed 1 square away from you | **stone**: wall (blocks movement and sight) |
| **energy** | ignores the target's Soak | **lightning**: as fire, energy damage |
| **mind** | against Resolve instead of Ward | **mist**: cover (+20 to TN against ranged attacks and powers) |

A **field** goes only on open ground or rough ground, never on a combatant, and goes back
to what it was after 3 rounds (the end of its maker's third turn after making it). Foes
can walk through a fire wall; they just pay for it. At the table, put a d6 on each square,
showing the rounds left.

## Powers

A power is an effect a traveler *is*, not one they carry: a mage's own fire, psionics,
nanites, a mutation. It's written the same way as an item's use, a shape and an element,
at will or with charges, and it Translates the same way. Its **tier is 1 + rank ÷ 20**
(rank 0-19 is tier 1; rank 100 is tier 6), and its attack roll adds the **rank** as an
item adds its skill.

A traveler holds up to **8 powers** (the Passport already stores them). How they're
gained and raised is the next thing to design.

## Out of Time

*For Ash, who brought a shotgun and a chainsaw to 1300 AD.*

**Out of Time** is a high-level power. It **anchors** items: an anchored item never
Translates. It keeps its true form, and the **+1 tier** of Force It, in every realm, for
as long as it's anchored.

- You can anchor **1 item, +1 for every 25 ranks** (up to 5 at rank 100). Choose them at
  the Waystation; they stay anchored.
- An anchored item adds no Dissonance for being there. It still adds **1 each time it's
  used where the locals can see** (as Force It does), so a boomstick in a castle still
  brings the realm's hunters, sooner or later. That's the point.

A **fused** item (a chainsaw where a hand was) is equipped for good: it can't be taken,
dropped or swapped, and it fills its hand slot always. Fused is a property of the item;
the registry says so.

## Registry

Each item's line in `registry/items.txt` gains its hands and uses (a sketch of the
format: the registry stays append-only, and new columns get defaults so old items keep
working):

```
# id  NAME           archetype tier damage TL ML hands at-will        charged             "Shown as"
9     FIRE_WAND      focus     2    fire   2  5  1     bolt           -                   "Fire wand"
10    WINTER_STAFF   focus     2    cold   2  6  2     bolt           field x2            "Staff of winter"
11    HOLY_SYMBOL    focus     2    mind   3  4  1     -              mend x3, ward x2    "Holy symbol"
12    FRAG_GRENADE   tool      3    kinetic 6 0  kit   -              burst x1 used       "Frag grenade"
13    BOOMSTICK      ranged    3    kinetic 4 0  2     bolt area1     -                   "Boomstick"
14    CHAINSAW_HAND  melee     3    kinetic 6 0  1     strike         - fused             "Chainsaw hand"
```

The element is the item's damage type, already in the registry. A race's line gains its
body (`hands 2` or `hands 4`).

## A worked fight

Sable (Moth-folk Channeler, level 2: Channel 60, Grace 50) holds a **staff of winter**
(tier 2, both hands) and has a **frag grenade** in her kit. A rust-guard (Speed 4) and two
ash rats come at her across the scrapyard.

1. **Ice wall.** Sable spends a charge (1 left): a Field of cold, 4 squares long, across
   the rust-guard's path. Those squares are ice (rough) for 3 rounds; the guard has to
   go round or wade through at half speed.
2. **Ice shard.** An ash rat closes. Sable throws an ice shard (at will): d100 + 60
   against the rat's TN against powers, 50 + Dodge 10 + Ward 0 = **60**. She rolls 42:
   102, 42 over, so **10 + 4 = 14** cold damage. The rat had 6. Down.
3. **Grenade.** The guard and the other rat are next to each other. Sable throws the
   grenade from her kit: Burst + kinetic, tier 3, Area 1, rolled with Ranged. One roll
   against both TNs; each hit takes 15 + margin, and is pushed a square. The grenade is
   used up.
4. **A swap.** The guard is through the ice and next to her. Sable swaps the staff into
   her pack and a sword and shield out of it (free: it's her turn), and fights.
5. Next Departure, the staff has both its charges again. The grenade is on the receipt as
   lost.

## What this needs from the engine (later)

- **Charges** live in the trip's state (and its save and trip code: [boarding.md](boarding.md#trip-code-format)),
  not in the Passport: every Departure starts full.
- **Fields** are temporary squares on the battle map, each with its rounds left. The
  battle engine already has squares and turns (`core/src/battle.c`); a field is a square
  that changes back.
- **Choosing**: the fight's Attack becomes "use an item" (any equipped item's at-will or
  charged use), and the pack is swapped from the same screen.
- **The registry** gains the new columns, and races their body.

## Still open

- How powers are gained and raised (classes, level-ups, Echoes, story).
- **Attunement** (two legendary items): later.
- **Resonance** (effects stronger or weaker by the realm's Tech and Magic Levels): left
  out for now; we'll see whether it's needed once this plays.
