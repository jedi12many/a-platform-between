# Conditions

*Draft for review. The numbers are starting points, to be tuned in the arena
([arena.md](arena.md)). The first build (the core effects and the small ones) is in the
rules lab: `registry/conditions.txt`, played as [turn.md](turn.md) says.*

A **condition** is something true of a combatant for a while, or for good: poisoned,
asleep, on fire, slowed, shielded, out of sync with time. Conditions are where the game's
flavor lives. A traveler crosses stone ages, space stations, haunted courts and dead
wastes; what those places *do* to them, what their gear and powers do to their foes, and
what their bodies shrug off, are all conditions. One system covers all of it:

| A condition comes from | It lasts | For example |
|---|---|---|
| **A power** | some rounds, or until shaken off | Sedate puts a foe to sleep; Stim hastes an ally |
| **Gear** | some rounds (a charge), or while worn or held | a rebreather: immune to toxic air; a stealth cloak, 1 charge |
| **A foe's attack or nature** | until it ends or is shaken off | an ash rat's bite: bleeding; a ghost: phased, always |
| **The map** | while you stand there, or after | a fire square sets you on fire; a puddle soaks you |
| **The Departure or its realm** | the whole trip, or a scene | a station with no gravity; a court where magic is dead |
| **Your race** | always | Lucky, Small, Plated, Winged ([races.md](races.md)) |
| **The story** | until the story ends it | cursed by the Lich; wanted in Ashmouth |

Race traits, a ring's protection and a spell's effect are the same thing, so there's one
rule for all of it, at the table and in the engine.

## What a condition does

Every condition is made of a few **effects** from one list, each with a number. A
condition never needs a rule of its own: that's what keeps a catalogue of eighty playable
at a table and small enough for a C64.

### The core effects

| Effect | What it does |
|---|---|
| **Lose the turn** | no move, no action |
| **Damage each turn** | N damage at the start of your turn, of a damage type (Soak counts), or of none (it doesn't) |
| **Heal each turn** | N health back at the start of your turn |
| **Speed** | ± N squares of movement (0 at least) |
| **Dodge**, **Armor**, **Ward**, **Soak** | ± N to that defense |
| **Rolls** | ± N to your rolls: all, attacks only, one skill, or one kind (ranged, melee, powers) |
| **Shake-off** | ± N to shaking off conditions |
| **Immune** | named conditions (or a damage type) can't touch you |
| **First** / **Last** | you act first, or last, in the order of play |
| **Movement** | you cross pits, or rough ground costs 1, or you pass through walls |

### More effects

These make the catalogue below possible. Each is small on its own; together they're the
cost of the flavor, so they're marked by how much they ask of the engine (and the table).

| Effect | What it does | Cost | Used by |
|---|---|---|---|
| **Barrier** | the next N damage is taken off before your health; it ends when used up | small | force field, stoneskin, a ward of bone |
| **Vulnerable** | double damage of a type | small | soaked (to energy), brittle (to kinetic) |
| **Thorns** | whoever hits you in melee takes N | small | electrified, a coat of spines, burning |
| **No powers** | you can't use powers | small | silenced, a dead-magic zone |
| **No healing** | healing does nothing (or half) | small | cursed, diseased |
| **Then** | when it ends, another begins | small | stim → exhausted; frozen → soaked |
| **Gear off** | items of a Tech Level (or Magic Level) and up don't work | medium | shorted (an EMP), a null-tech zone |
| **Must attack** / **Can't attack** | a named fighter: you must attack it if you can, or you can't | medium | taunted, charmed |
| **Hidden** | you can't be attacked from more than 1 square away | medium | invisible, cloaked, in the fog |
| **Untouchable** | weapons don't touch you (powers do), and you can't attack with one | medium | phased, a ghost |
| **Spreads** | at the end of your turn, it spreads to one fighter next to you | medium | nanites, plague, wildfire |
| **At random** | you move and attack at random | medium | confused, berserk with fear |
| **Rewind** | at the start of your turn, your health goes back to what it was at the start of your last | medium | rewound (the setting's own) |
| **Changes sides** | you fight for the other side | large | dominated, hacked |

The core list and the small ones are the first build; the medium ones come with the powers
and gear that need them; **changes sides** waits until it's clearly worth it.

## Getting one, and losing it

- **Put on by an attack.** An attack, a power or a hazard that carries a condition puts it
  on whoever it hits. (Whether a glancing hit does too is still open.)
- **Some must be resisted first.** A condition put on by a power may name a defense:
  the attack's roll beats the target's Ward (or Resolve, for the mind), as any power's
  does. A hit is a hit; there's no second roll.
- **Wearing off.** A condition with rounds ends at the end of your turn when they run out;
  count them down at the end of each of your turns.
- **Shaking it off.** At the end of your turn, roll once for each condition that can be
  shaken off: **d100 + the stat it names, against its TN.** Success, it's gone. (The one
  roll the game already has; TN 100 is a normal difficulty, as in
  [rules-v0.md](rules-v0.md).)
- **Ending on a trigger.** Some end when something happens: asleep ends when you're hit,
  soaked when you're set on fire (and the fire goes out), hidden when you attack.
- **The same condition twice doesn't stack.** The stronger counts, and the longer time.
- **Opposites cancel.** Hasted and slowed, on fire and soaked, blessed and cursed: put one
  on and its opposite ends. (Each condition names its opposite, if it has one.)
- **Immune** means it never lands: nothing to roll.

## One condition, many names

Conditions **Translate**, as gear and powers do ([translation.md](translation.md)): the
numbers are fixed, and the realm names them. The registry keeps one name; each Departure's
realm decides what it's called in the text.

| Condition | Stone and iron (TL 2) | Spacefaring (TL 8) | High magic (ML 7) |
|---|---|---|---|
| **Poisoned** | venom | nanotoxin | rot-hex |
| **Paralyzed** | hamstrung | neural lock | held |
| **On fire** | burning | plasma burn | spirit-flame |
| **Shielded** | braced | kinetic barrier | aegis |
| **Hidden** | in the shadows | cloaked | unseen |
| **Shorted** | (no effect: nothing to short) | EMP'd | (no effect) |
| **Silenced** | (no effect) | (no effect) | silenced |

A condition that makes no sense in a realm (an EMP among flint axes) does nothing there,
the way a relic does when nothing fits it.

## The catalogue

A first catalogue, in families. Numbers are starting points; each will be a line in the
registry (`registry/conditions.txt`, append-only like the others), and a power, an item, a
foe or a Departure names it by its id.

### The body

| Condition | Effects | Ends | From |
|---|---|---|---|
| **Poisoned** | 3 damage each turn (no type) | shake off: Grit, TN 100; or 5 rounds | venom, a toxin dart, a bad meal |
| **Bleeding** | 2 damage each turn | any healing, or a Medicine check | blades, claws, a bite |
| **Diseased** | −10 to rolls; no healing over half your health | a Medicine check, or the story | plague rats, a spore cloud |
| **Nanite swarm** | 3 energy damage each turn; spreads | shake off: Wits, TN 110 (you reprogram them) | a nanite grenade, a hive drone |
| **Exhausted** | Speed −2, −10 to rolls | 3 rounds | what a stim leaves behind |
| **Stimmed** | Speed +2, +10 to attacks; then exhausted | 3 rounds | a combat stim |
| **Drunk** | −10 to rolls, +10 to shake off frightened | 5 rounds | the Buffer Stop's best |

### The mind

| Condition | Effects | Ends | From |
|---|---|---|---|
| **Frightened** | −10 to rolls; can't move closer to what frightened it | shake off: Presence, TN 100 | a roar, a horror, Intimidate |
| **Confused** | moves and attacks at random | 2 rounds; or shake off: Wits, TN 100 | mind spike, a strobe, a bad teleport |
| **Taunted** | must attack the taunter | 2 rounds | Taunt (a Warden's) |
| **Charmed** | can't attack the charmer | 3 rounds, or when the charmer hits it | a siren's song, a pheromone |
| **Berserk** | +20 to melee, Dodge 0, must attack the nearest fighter | 3 rounds | rage, a war-drug, a curse |
| **Asleep** | lose the turn; Dodge 0 | when hit; or shake off: Wits, TN 110 | Sedate, a lullaby, gas |
| **Inspired** | +10 to rolls, +10 to shake off frightened | 3 rounds | a war cry, a banner, a speech |
| **Focused** | +20 to the next attack | your next attack | taking aim, a targeting scope |
| **Dominated** | fights for the other side | 1 round; shake off: Presence, TN 120 | (later: the large effect) |

### Movement and control

| Condition | Effects | Ends | From |
|---|---|---|---|
| **Slowed** | Speed −2 | 2 rounds | cold, a snare, tar |
| **Hasted** | Speed +2 | 3 rounds | a spell, a stim, a time-skip |
| **Entangled** | Speed 0 (can still act) | shake off: Might, TN 100 | a net, vines, sticky foam |
| **Knocked down** | Dodge 0; standing up costs half your move | when you stand | a shove, a blast, a shockwave |
| **Stunned** | lose the turn | 1 round | a stun baton, a concussion |
| **Paralyzed** | lose the turn; Dodge 0 | 2 rounds; or shake off: Grit, TN 120 | a neural lock, a ghoul's touch |
| **Frozen** | lose the turn; Armor +10; then soaked | 1 round | Ice wall's heart, a cryo blast |
| **Weightless** | crosses pits; −10 to melee | while it lasts | zero gravity, a levitation spell |
| **Heavy** | Speed −1; −10 to ranged | while it lasts | heavy gravity, lead boots, a curse |
| **Phased** | untouchable; passes through walls | 2 rounds | a phase shifter, a ghost's nature |
| **Displaced** | the first attack on you each round takes −20 | 3 rounds | Blink, a holo-decoy, a mirage |

### The senses

| Condition | Effects | Ends | From |
|---|---|---|---|
| **Blinded** | −30 to attacks | 2 rounds; or shake off: Grit, TN 100 | a flashbang, sand, a curse |
| **Hidden** | can't be attacked from more than 1 square away | when you attack, or 3 rounds | a stealth cloak, Vanish, smoke |
| **Marked** | Dodge −10 and Armor −10 against everyone | 3 rounds | a targeting laser, a hunter's mark |
| **Deafened** | −10 to rolls that need hearing; immune to songs and roars | 3 rounds | a blast, earplugs (worn) |
| **Darksighted** | ignores dark | while worn, or always | goggles, a race's eyes |

### Tech

| Condition | Effects | Ends | From |
|---|---|---|---|
| **Shorted** | gear of Tech Level 5 and up doesn't work; constructs lose the turn | 2 rounds | an EMP, a lightning strike |
| **Overheated** | can't use energy weapons | 1 round | firing too long, a heat ray |
| **Jammed** | can't use ranged weapons | until a Tech check (your action) | a misfire, a gunner's bad luck |
| **Overcharged** | +5 damage with energy weapons; takes 2 energy damage each turn | 3 rounds | a capacitor surge |
| **Hacked** | a construct: fights for the other side | (later: the large effect) | a Tinker's hack |
| **Sealed** | immune: vacuum, toxic air, smoke, drowning | while worn | a space suit, a rebreather |

### Magic

| Condition | Effects | Ends | From |
|---|---|---|---|
| **Silenced** | no powers | 2 rounds | a null rune, an anti-magic field |
| **Cursed** | −10 to rolls; no healing over half | the story, or a Lore check at a shrine | the Lich, a broken oath |
| **Blessed** | +10 to rolls, +10 to shake off | 3 rounds | a holy symbol, a prayer |
| **Warded** | Ward + 10 × tier | 3 rounds | Shield (a Channeler's), a ward-charm |
| **Haunted** | frightened at the start of each round you're alone | the story | a ghost that's taken an interest |
| **Mana-burned** | 3 damage each time you use a power | 3 rounds | a wild-magic realm, a feedback hex |

### The elements

| Condition | Effects | Ends | From |
|---|---|---|---|
| **On fire** | 5 fire damage each turn; thorns 2 | 3 rounds; or shake off: Grace, TN 90; or soaked | fire, Fireball, a burning square |
| **Soaked** | immune: on fire; vulnerable to energy | 3 rounds | water, rain, a burst pipe |
| **Chilled** | Speed −1 | 2 rounds | cold, Ice shard |
| **Electrified** | thorns 3 (energy) | 2 rounds | lightning, a shock coil |
| **Corroded** | Armor −10 | until repaired (a Tech check) | acid, a rust-guard's spit |
| **Brittle** | vulnerable to kinetic | 2 rounds | flash-freezing, a glass curse |

### Protection

| Condition | Effects | Ends | From |
|---|---|---|---|
| **Shielded** | Armor + 10 × tier | 3 rounds | the Ward shape, a riot shield's charge |
| **Barrier** | the next 5 × tier damage is absorbed | when used up | Force field, a ward of bone |
| **Stoneskin** | Soak + tier | 3 rounds | a spell, a dermal plating stim |
| **Regenerating** | heal 3 each turn | 5 rounds | a troll's blood, a med-nanite cloud |
| **Reflective** | Ward +20; a power that misses you hits its caster | 2 rounds | a mirror charm, a deflector |
| **In cover** | +20 to TN against ranged and powers | while there | a cover square (`+`) |

### Time: the setting's own

The Waystation sits outside time, and its travelers are a little out of step with it. These
are the conditions no other game has.

| Condition | Effects | Ends | From |
|---|---|---|---|
| **Early** | acts first in the order of play | always (a Chronomite) | a race, a time-skip charm |
| **Desynced** | acts last; Dodge +10 (you're not quite there) | 3 rounds | a time-skip gone wrong, a Chronomite's trick |
| **Rewound** | rewind: health goes back to what it was at the start of your last turn | 2 rounds | Rewind (a power), a broken clock |
| **Time-locked** | lose the turn; can't be harmed | 1 round | Stop (a power): on a foe, a pause; on a friend, a shelter |
| **Aged** | −10 to Grace rolls, Speed −1 | the story | a time-thief's touch, a slow realm |
| **Unanchored** | your gear Translates badly: each item counts one tier lower | the scene | a high-Dissonance moment |
| **Déjà vu** | +20 to your first roll each round | 2 rounds | a moment you've lived before (an Echo scene) |

### Places and realms

A Departure can put a condition on everyone for the whole trip or a scene, and a battle
map's squares can carry one: a field ([items.md](items.md#elements)) or a hazard (`^`) is
a square that puts its condition on whoever enters it or starts a turn there.

| Condition | Effects | Where |
|---|---|---|
| **Thin air** | Speed −1 | a mountain realm, a high station |
| **Zero-g** | weightless, for everyone without mag boots | a station with its gravity off |
| **Heavy gravity** | heavy | a collapsed-star mine |
| **Vacuum** | 5 damage each turn (no type), unless sealed | a breached hull |
| **Toxic air** | poisoned at the start of each scene, unless sealed | the Ashmouth fumes |
| **Irradiated** | 2 energy damage each turn | the Ashmouth wastes |
| **Dark** | −20 to ranged attacks | an unlit undercroft |
| **Fog** | hidden beyond 3 squares, for everyone | a moor, a steam vent |
| **Underwater** | Speed halved; immune to on fire; ranged −20 | a drowned district |
| **Bitter cold** | 2 cold damage each turn unless warm (a coat, a fire) | the ice sheet |
| **Dead magic** | silenced, for everyone (the realm's ML is 0) | a null-court, a lead vault |
| **Null tech** | shorted, for everyone, for good | a realm where machines refuse to work |
| **Sanctified** | blessed, for those its god favors | a temple's floor |

### Races

Each race has two, always on ([races.md](races.md#traits)): Lucky, Steady, Hollow,
Unsleeping, Prismatic, Clear, Rad-fed, Rooted, Early, Small, Plated, Knightly, Winged,
Lantern-eyed. Races to come can draw on the whole catalogue: Darksighted, Sealed (a
creature that doesn't breathe), Weightless (a floater), Regenerating (a troll-blooded),
immune to frightened and charmed (a hive mind).

## Where they come from

### Powers

Most powers either do damage or put on a condition; many do both. The class lists in
[items.md](items.md#power-lists) name theirs:

| Class | Power: condition |
|---|---|
| Warden | Shield wall: shielded. Shove: knocked down (a crit). Taunt: taunted. Ground slam: stunned |
| Rogue | Blink: displaced. Smoke: a field of fog (hidden). Dirty trick: blinded, 1 round. Snare: slowed; entangled from tier 3. Vanish: hidden |
| Tinker | Force field: barrier. Barricade: in cover. Shock mine: stunned. Scan: marked |
| Channeler | Ice wall: chilled; frozen from tier 5. Fire wall, Fireball: on fire. Shield: warded. Mind spike: confused |
| Medic | Patch up: ends bleeding. Adrenaline: hasted. Stim: stimmed, then exhausted. Sedate: asleep |

And new ones the catalogue opens up: **Rewind** and **Stop** (time), **Silence**, **Bless**,
**Curse**, **EMP** (shorted), **Hack** (later), **Phase** (phased), **Mark** (marked),
**Inspire** (inspired). A power's tier sets its condition's numbers or rounds.

### Gear

An item can carry a condition **while worn or held** (always on), **as a charge** (once,
then ticked off), or **on its hits** (a weapon that puts it on):

| Item | Condition |
|---|---|
| Rebreather (hat) | sealed |
| Mag boots (boots) | immune: weightless, knocked down |
| Insulated gloves (gloves) | immune: electrified, shorted (your own gear) |
| Ring of free action (ring) | immune: slowed, entangled, paralyzed |
| Amulet of the hearth (necklace) | immune: frightened |
| Night goggles (hat) | darksighted |
| Stealth cloak (armor) | hidden, 1 charge |
| Jetpack (belt... or armor) | weightless, 3 charges |
| Combat stim (pack, used up) | stimmed |
| Venom blade (hand) | its hits: poisoned |
| Stun baton (hand) | its hits: stunned (a crit only) |
| Flamethrower (hands) | its hits: on fire |
| Shock coil armor (armor) | electrified, always |

So a traveler builds a defense out of gear (sealed, immune to fire, free action) as much as
out of Armor, and finding the right ring before the plague city is a real reward.

### Foes

A foe's card can carry conditions on its attack, and of its own nature:

| Foe | Its attack | Its nature |
|---|---|---|
| Ash rat | bleeding | (swarm) |
| Rust-guard | corroded | immune: poisoned, bleeding |
| Scrap gunner | (a crit) knocked down | |
| Maintenance drone | stunned | immune: poisoned, frightened; vulnerable: shorted |
| A ghost | frightened | phased, always |
| A skeleton | | immune: poisoned, asleep, frightened |
| A plague cultist | diseased | immune: diseased |

### The story

A Departure can put a condition on a traveler for the rest of the trip, and take it off:
cursed by the Lich until you burn her ledger; haunted until you lay the ghost; drunk after
the Buffer Stop. (These are the story's, not the Passport's: they end with the Departure.)

### Dissonance

Forcing an item ([translation.md](translation.md#dissonance)) raises Dissonance; its
thresholds can be conditions too, so a realm's reaction is something you feel in a fight:
at 5 your forced gear is **jammed** on a failed roll; at 7 you're **marked** wherever the
realm's hunters are; at the very top, **unanchored**.

## Limits

- **On a fighter**: its race's two, plus **4 others** at a time. A fifth replaces the one
  with the fewest rounds left. That keeps a fighter's state to a few bytes on a C64, and
  four tokens on a mini at the table.
- **In the registry**: up to 255 conditions (an id is a byte).
- **On screen**: the battle screen shows a fighter's conditions as short tags by its name
  (`PSN`, `FIRE`, `SLOW`); the story text says what happened in words.

## At the table

A token on the mini (or a note beside it) for each condition, with a d6 for its rounds
left. At the end of each of your turns: count down, then roll to shake off. A race's two
are printed on the character sheet; so is anything your gear gives you while worn.

## What it needs from the engine (later)

- **A registry** of conditions (`registry/conditions.txt`): each one's effects and
  numbers, how it ends (rounds, a shake-off stat and TN, a trigger), its opposite, what it
  becomes when it ends, and what it's immune to.
- **Each fighter** keeps its conditions and their rounds left; the battle engine applies
  them at the start and end of each turn, and the battle screen shows them.
- **Foes**, **items** and **powers** name conditions in the registry: on a hit, while worn,
  as a charge, or of their nature.
- **Departures** name a realm's conditions in their header, and a map's squares and a
  scene's commands put them on and take them off.
- **Translation names** for conditions, by realm.
- **The arena** measures each: what poisoned 3 a turn is worth, what Small does for a Rogue.

## Still open

- Whether a **glancing** hit puts its condition on.
- **Resistance** short of immunity (half the rounds?), if it's needed.
- Conditions **between scenes** (poisoned on the road, cured by a check) beyond the story's
  own.
