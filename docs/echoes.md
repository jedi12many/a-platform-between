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
if echo WOLF_PUP = SAVED then summon ally DIRE_WOLF; set echo WOLF_PUP = SWORN
if any echo kind ALLY then scene OLD_FRIEND_ARRIVES   ; general payoff
```

## Parties (later)

Every party member's Echoes are in play. Your spared bandit and my rescued wolf can meet
in the same fight.
