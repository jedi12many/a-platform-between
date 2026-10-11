# Echoes

Your choices follow you. Each Departure records 2–4 key moments as **Echoes** on your
Passport. Later Departures check for them and pay them off.

| Planted | Paid off |
|---|---|
| You went out of your way to save a dire wolf puppy | Next time you're in that realm, a grown dire wolf crashes into a losing fight on your side |
| You let the bandit go | Three Departures later, a warlord rules the wastes, and he remembers you |

## Time travel

Departures jump around in time, so payoffs can go any direction:

- **Forward**: the bandit you spared is a warlord 200 years on.
- **Backward**: in an earlier era, the dire wolf pack's matriarch already knows your scent.
- **Loops**: the hermit who taught you a skill turns out to be your own retired character.

## Kinds

| Kind | Meaning |
|---|---|
| **Ally** | They show up to help, usually mid-fight or at a key moment |
| **Nemesis** | Someone you wronged, or let grow, comes back stronger |
| **Debt** | Someone owes you a favor, or you owe them |
| **Mark** | A reputation, scar or curse the world reacts to |
| **Key** | Knowledge that opens a shortcut, secret or dialogue option |

## Writing rules

1. **No good/evil scores.** Consequences cut both ways. The saved wolf also draws the
   hunters who wanted it. The spared warlord is ruthless, but might spare you in return.
2. **Every Departure works with zero Echoes.** Players play in any order. Echoes enrich;
   they never gate.
3. **Specific and general payoffs.** A specific payoff checks one exact Echo. A general one
   fires on any Echo of a kind ("an old ally finds you") and fills in the name from the
   Passport, so even early Departures feel personal.
4. **Payoffs consume or transform.** After the wolf saves you, `WOLF_PUP: SAVED` becomes
   `WOLF_PUP: SWORN`. Stories keep moving and Passport slots free up.
5. **The hub notices.** Waystation regulars gossip. The Stationmaster has opinions, and
   some choices move your Debt.
6. **Budget per Departure:** plant 2–4, listen for up to ~6 (specific + general).

## In play

An Echo pays off two ways. **In the story**: a Departure checks it and writes a scene for
it ([In Quest Script](#in-quest-script)). **In play**: some states carry a **gift**, a
small piece of rules the traveler has wherever they go, in any Departure and at a table,
for as long as the Echo is in that state. The gift is written on the Echo's registry line
(below), so no Departure has to know about it.

| Kind | Its gift | For example |
|---|---|---|
| **Ally** | **Call**: a power ([items.md](items.md#powers)), 1 charge a Departure. The ally joins a fight on a square next to you and fights on your side for the rest of it, played by quick ([combat.md](combat.md#your-turn)), from its own card in the bestiary | `WOLF_PUP: SWORN`: call the dire wolf |
| **Nemesis** | none for you: the nemesis is a **foe** that grows. Its card is drawn at your level band ([bestiary.md](bestiary.md)) each time it comes, and a Departure can send it after you | `JACE_CUTTER: SPARED`: the warlord, two hundred years on |
| **Debt** owed to you | **Favour**: once a Departure, turn one failed check (not an attack) into a success at a cost: someone owes you, and pays | `KEPLER_CREW: SAVED`: the crew's engineer, on a terminal you can't crack |
| **Debt** you owe | none: the story calls it in | |
| **Mark** | **Standing**: +20 (or −20) to your checks with the people who know it, and the story can open or close doors on it | `LANTERN_COURT: BANISHED`: −20 with the Court, and its guards fight on sight |
| **Key** | none: a key opens story options, never a number | `YSOLDE_LEDGER: READ` |

- **A Call takes a power slot.** It's the "power from an Echo" of
  [items.md](items.md#gaining-powers): it takes one of the 8 slots, not a class pick. Its
  rank starts at 2 x your level, like any new power, and is raised the same way.
- **A gift follows its state.** When the wolf's Echo goes from SAVED to SWORN, the Call
  arrives; if it changes again, the gift changes with it. When the Echo leaves the 8
  active ones for your Legend, its gift goes with it.
- **The ally needs room.** A battle holds 8 fighters; a Call into a full one does nothing,
  and the charge isn't spent.
- **Every Departure starts full**, Calls and Favours too ([items.md](items.md#using-an-item)).
- **At the table**, a gift is a line on the sheet: "Call: dire wolf (1/Departure)".

The registry line names each state's gift (a sketch; the registry stays append-only, and
a state's gift can be added later without changing its number):

```
# id  NAME          kind     departure  states                          gifts
4     WOLF_PUP      ally     02         SAVED      LEFT*      SWORN     SWORN=call DIRE_WOLF
2     KEPLER_CREW   debt     01         SAVED      LOST*                SAVED=favour
8     LANTERN_COURT mark     03         WELCOME*   BANISHED             WELCOME=+20 BANISHED=-20
```

An ally's card (the dire wolf's) lives in `registry/foes.txt` with the foes: same numbers,
fighting on the other side.

## Storage

- A **global Echo registry** (`registry/echoes.txt`), append-only like the item registry.
  Each entry: an ID, a kind, the Departure that plants it, a short name, its possible
  states (e.g. SPARED / KILLED / RECRUITED) and which one is the canon default.
- The Passport holds **8 active Echoes**: ID + state, about 12 bits each.
- When slots are full, the oldest Echo moves to your **Legend**. (Rules core v0 evicts
  the oldest; preferring resolved Echoes is a later refinement.) Modern builds
  and the hub keep the full Legend; retro builds keep only active Echoes.

## Unset Echoes and canon defaults

Every Echo in the registry has a **canon default** state. State 0 on the Passport means
*unset*: you never played the Departure that plants it (a skipped season, or a Departure
you skipped past on its line; see [lines.md](lines.md)). When a
Departure asks about an unset Echo, it uses the canon default, and the hub gossip says
"someone" made that choice. Your real choice replaces the default if you later play it.

## Rewinds

Replaying a Departure (a **Rewind**, see [seasons.md](seasons.md)) replaces the Echoes it
planted with your new choices, including later transformations of them. The timeline
shifted; regulars who remember the old one may say so.

## In Quest Script

```
plant echo WOLF_PUP = SAVED
if echo WOLF_PUP = SAVED then summon ally DIRE_WOLF; set echo WOLF_PUP = SWORN   ; and the Call is yours
if any echo kind ALLY then scene OLD_FRIEND_ARRIVES   ; general payoff
```

## Parties (later)

Every party member's Echoes are in play. Your spared bandit and my rescued wolf can meet
in the same fight.
