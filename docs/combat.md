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

Foes live in the shared **bestiary**, `registry/foes.txt`, one line each, so any Departure
(and any community author) can use them, and printed foe cards come from the same
numbers. A foe card prints its numbers directly, including its defense TNs, so nobody adds
at the table:

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
Dodge still counts: you dive clear. You can't aim a blast that would catch you, but it
can catch your friends.

## The battle map

A map is a grid up to **16 × 10** squares, drawn in the Quest Script as rows of
characters (it fits a 40-column screen with room for text, and copies onto squared paper):

| Square | Means |
|---|---|
| `.` | open ground |
| `#` | **wall**: blocks movement and sight |
| `O` | **pit**: can't be entered or crossed on foot; it doesn't block sight |
| `~` | **rough** (water, rubble, snow): costs 2 squares of movement |
| `+` | **cover** (crates, a low wall): costs 2 to enter; while you stand in it, +20 to your TN against ranged attacks and powers |
| `^` | **hazard** (fire, radiation): 5 damage to anyone who ends a move on it or starts a turn there; Soak counts |
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
2. **Each combatant takes a turn**: it moves up to its Speed and takes one action. On a
   traveler's turn its player chooses, seeing the board as it is then: solo or in a
   party, every character chooses on its own turn, as in *Pool of Radiance*
   ([party-play.md](party-play.md)).

### Your turn

Modelled on *Pool of Radiance*'s turn, from review (milestone E3.8). Cast and Use come
with powers and items.

Move first, up to your Speed, then take one action:

| Action | What it does |
|---|---|
| **Attack** | a foe next to you with a melee weapon, or one in sight with a ranged weapon |
| **Cast** | use a power (with the power registry, later). A power that takes time goes off at the start of your next turn, and a hit before then spoils it, so you can interrupt a foe's casting by hitting it first |
| **Use** | an item: a stim, an oil, a grenade (later) |
| **Guard** | stand ready: until your next turn, **the first foe that moves next to you takes a free attack** from you, before it can act |
| **Wait** | put your turn off until the end of the round, to see what the foes do first. Only before you've moved, and once a round |
| **Flee** | get out (see *Ending a fight*) |
| **Done** | end your turn (having just moved, or not even that) |
| **Quick** | the computer plays this character, by the rule its weapon suggests (**charge** with a melee weapon, **shoot** with a ranged one), until you take it back at the start of any of its turns. You can put the whole party on quick |

**Free attacks.** Moving away from a foe that's next to you gives that foe **a free
attack** on you as you go, before your move. A foe that steps away from you gives you
one, too. It's one free attack per foe each time someone pulls away, made with whatever
the attacker is holding. Fleeing at a cost (below) gives the same.

There is no facing: nobody has a back to stab, which keeps the map readable at 40
columns and simple at a table. And the order of play isn't re-rolled each round as it
was in *Pool of Radiance*: it's set by Grace, with nothing to roll at a table.

Foes act by a short, printed rule (on the card at the table), so a fight plays the same
at the table and on the screen:

| Rule | The foe |
|---|---|
| **Charge** | attacks the nearest traveler it can reach; otherwise moves as close to the nearest traveler as it can |
| **Shoot** | shoots the nearest traveler it can see; otherwise moves only as far as it must to get a shot (or closes in, if it can't get one) |
| **Guard** | stays put, and attacks anyone it can reach from where it stands; with nobody in reach, it stands guard (a free attack on the first traveler to come next to it) |
| **Coward** (added to any rule) | runs off when it's down to a quarter of its health |

When a foe has a choice of squares, it takes the one nearest its target, then the one
cheapest to reach, then the one nearest the top-left corner of the map.

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
heals you (a rest, a medic, `~ heal`). Back at the Waystation, everyone is whole again. A
lost fight that the story carries on from (a `lost:` branch) leaves you on 1 health.

You fight with the first weapon you have equipped (melee, ranged, or a focus for powers),
or bare-handed. Choosing a weapon mid-fight, and using items, come later. Saves are made
between fights, at story menus, not during one.

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

`core/src/battle.c` (`core/include/apb_battle.h`) plays a whole battle from a stream of
actions: the map, movement, sight, the order of play, the foes' rules and the endings.
`apb_battle_quick` plays a traveler's turn by its weapon's rule, the same planning the
foes use. `tests/battle/` holds scenarios (the worked fight, the rifle, terrain, movement,
fleeing, an ambush, a lost fight, and *Pool of Radiance* turns: guard, wait, free
attacks both ways, quick) with logs reviewed by hand; `make test-combat` plays them on the
PC and the 6502, re-checks every roll against the Python reference, and runs random
battles under the sanitizers.

On the C64, the desktop and in the browser, a fight is the battle screen with graphics
(`client/tactics.c`, [c64.md](c64.md#the-battle-screen)): the map in tiles, the fighters
as sprites, a roster, the log and a command bar, **Move Aim Guard Wait Flee Quick Done**.
Move walks a cursor over the squares the rules allow this turn (they're marked); Aim
cycles through the foes in reach from there, with the TN; Wait only before moving; Quick
plays you until T takes over.

In the terminal (`fe/term/term.c`, `client/battle_view.c`): the map is drawn two characters to
a square (`@` you, `a`, `b`, ... the foes, `x` one who's down) with a key and a roster
giving each foe's health and the TN to hit it. A turn is two short menus, **Where to?**
(stay, next to or toward a foe, to the exit, into cover, onto high ground; or instead
of moving, wait, or quick) and **Then?** (attack, with the TN; guard; flee, with its TN,
or take the exit; done; back), offering only what the rules allow from that square. On
quick, each turn asks for Enter to go on, or t to take over again. What happens is told in sentences, with
every roll: *You attack Rust-guard: 62 + 20 = 82 against 56, a hit: 22 damage.* Those
sentences are the **combat log**, which players can read back, and which recaps what
happened since a player's last turn ([party-play.md](party-play.md)).

## What this isn't (yet)

- Powers and their costs (with the power registry), opposed rolls at high level, and
  limits on stacking buffs: later, after playtests.
- Bandaging a traveler who's down, as in *Pool of Radiance*, so a fight with a party
  isn't over for whoever falls first: with party support.
- Companions and Echo allies fight with the same numbers; how they're recruited is still
  an open question in [rules-v0.md](rules-v0.md).
