# Echoes

Your choices follow you. Each Departure records 2–4 key moments as **Echoes**. Later
Departures check for them and pay them off **in the story**: a door that opens, a
stranger who knows your name, a shortcut through the woods.

| Planted | Paid off |
|---|---|
| You went out of your way to save a dire wolf pup | Two Departures on, the pup is a ranger's familiar, and it knows a way through the thornwood |
| You let the bandit go | Three Departures later, a warlord rules the wastes, and he remembers you |

## Story, not rules

**Echoes change the story only.** They open and close choices, change who says what, and
send people after you; they never change a roll, a fight or a character sheet. In a party,
every player's past is in the room at once, and story choices can all be offered side by
side, where rules gifts would have to be reconciled with each other forever.

A Departure can still *give* something because of an Echo: the ranger's familiar shows
you the way, and in thanks the ranger teaches you a trick. What's given (an item, a
power, XP) is then simply yours, with no tie to the Echo
([items.md](items.md#gaining-powers)).

## Time travel

Departures jump around in time, so payoffs can go any direction:

- **Forward**: the bandit you spared is a warlord 200 years on.
- **Backward**: in an earlier era, the dire wolf pack's matriarch already knows your scent.
- **Loops**: the hermit who taught you a skill turns out to be your own retired character.

## Kinds

| Kind | Meaning |
|---|---|
| **Ally** | Someone (or something) on your side: they turn up to help at a key moment |
| **Nemesis** | Someone you wronged, or let grow, comes back stronger |
| **Debt** | Someone owes you a favor, or you owe them |
| **Mark** | A reputation, scar or curse the world reacts to |
| **Key** | Knowledge that opens a shortcut, secret or dialogue option |

## Positive and negative

Each **state** of an Echo is positive (**+**) or negative (**−**), not the Echo as a whole:
the same choice can go either way. `JACE_CUTTER: RECRUITED` is an ally; `SPARED` is a
warlord who wants you dead.

| | Positive (+) | Negative (−) |
|---|---|---|
| What | allies, favors owed to you, keys you hold, a good name | nemeses, debts you owe, a bad name, a curse |
| Where it plays | **everywhere**: solo and party Departures | **solo Departures only** |

Negative Echoes are what give a run of **solo Departures** its edge: a line of solo
stories where the bandit you let go becomes the warlord who hunts you. Party Departures
stay on the positive side, so one player's enemy never has to be weighed against another
player's friend. A state that's neither (a door you didn't open) is positive by default:
it can only add options.

## In a party

At a story choice, a party Departure offers **every party member's positive Echoes that
apply**, each as one more option, named for whose it is:

```
1. Hack through the thornwood
2. Go round by the river
3. Fern's wolf: the ranger's familiar knows a way through
```

- **At most 3 Echo options at one choice**, so a menu stays within the 9 every platform
  can show. If more apply, the order the author wrote them in decides.
- **A general payoff** ("an old ally finds you", any ally Echo) picks **one** party
  member's, not all of them: the one with the most recent such Echo, or the author's rule.
- Whoever's Echo it is, the whole party takes the path it opens.

## Reach

An Echo doesn't matter everywhere. Each has a **reach** in the registry:

| Reach | Can be paid off in |
|---|---|
| `line` | Departures on its own line ([lines.md](lines.md)) |
| `realm` | Departures in its own realm, on any line |
| `anywhere` | any Departure (rare: the Stationmaster, a curse that follows you) |

Reach is a guide for authors, and it's what keeps a long list of Echoes from turning up
where they make no sense: a wolf from the Ashmouth wastes doesn't come to the Lich's tea
party, unless that Departure's author says so.

## A long Legend, a short pass

A traveler who has played for seasons may have **100 Echoes or more**. They can't all ride
in a password: 12 bits each, 100 Echoes would add some 250 symbols to type. So the list is
kept in two places:

- **The Legend, at the Waystation.** Every Echo you've ever planted, with its state, kept
  with your traveler on the Waystation website (on your account, or as a file or QR code
  for modern builds; on the printed sheet at a table). There's no limit but the
  registry's (1,023 Echoes).
- **The Boarding Pass carries only what this Departure listens for.** Each Departure image
  lists the Echoes it has payoffs for (the compiler finds them in the script's `echo`
  checks, so authors write nothing extra: usually 2–6). When the Waystation issues a pass,
  it puts your states for just those on it, positive and negative for a solo Departure,
  positive only for a party one. The machine you play on never sees the rest, and the
  password stays as long as it is now.
- **The Travel Stamp brings changes home.** An Echo planted or changed on the trip goes on
  the receipt, as now, and the Waystation updates your Legend when the stamp lands.
- **Without a pass** (travelling on a bare Passport, which can't be stamped), the
  Passport's own **8 most recent Echoes** are what the Departure sees.

## Writing rules

1. **No good/evil scores.** Consequences cut both ways. The saved wolf also draws the
   hunters who wanted it. The spared warlord is ruthless, but might spare you in return.
2. **Every Departure works with zero Echoes.** Players play in any order. Echoes enrich;
   they never gate.
3. **Specific and general payoffs.** A specific payoff checks one exact Echo. A general one
   fires on any Echo of a kind ("an old ally finds you") and fills in the name from the
   Legend, so even early Departures feel personal.
4. **Payoffs consume or transform.** After the wolf leads you through the thornwood,
   `WOLF_PUP: SAVED` becomes `WOLF_PUP: SWORN`. Stories keep moving.
5. **The hub notices.** Waystation regulars gossip. The Stationmaster has opinions, and
   some choices move your Debt.
6. **Budget per Departure:** plant 2–4, listen for up to ~6 (specific + general).
7. **Party Departures listen for positive states only**; save the negative ones for solo
   stories.

## The registry

`registry/echoes.txt`, append-only like the item registry: an id, a kind, the Departure
that plants it, its **reach**, its states (each marked **+** or **−**) and which one is the
canon default. A sketch of the new columns (existing states keep their numbers; a mark
can be added to a state later without changing it):

```
# id  NAME          kind     departure  reach  states
4     WOLF_PUP      ally     02         line   SAVED+     LEFT*+     SWORN+
5     JACE_CUTTER   nemesis  02         realm  SPARED-    KILLED*+   RECRUITED+
8     LANTERN_COURT mark     03         realm  WELCOME*+  BANISHED-
```

## Unset Echoes and canon defaults

Every Echo in the registry has a **canon default** state. State 0 means *unset*: you never
played the Departure that plants it (a skipped season, or a Departure you skipped past on
its line; see [lines.md](lines.md)). When a Departure asks about an unset Echo, it uses the
canon default, and the hub gossip says "someone" made that choice. Your real choice
replaces the default if you later play it.

## Rewinds

Replaying a Departure (a **Rewind**, see [seasons.md](seasons.md)) replaces the Echoes it
planted with your new choices, including later transformations of them. The timeline
shifted; regulars who remember the old one may say so.

## In Quest Script

As [quest-script.md](quest-script.md) has it: `~ echo` plants or changes one, and an
`echo` condition puts a choice on the menu only when the Echo is in that state.

```
~ echo WOLF_PUP = SAVED                                     ; planted (official Departures only)

* {echo WOLF_PUP = SWORN} [Follow the wolf through the thornwood] -> shortcut
```

A general payoff (any Echo of a kind) and the party's per-player options come with party
play; they aren't in the language yet.

## What's built, and what isn't

Built: Echoes on the Passport (8, with their states), planting and checking them in Quest
Script, canon defaults, Rewinds, and Echoes on the receipt and Travel Stamp.

Not built yet: the **+** and **−** marks and reach in the registry; Departure images
listing the Echoes they listen for; the Waystation keeping the full Legend and putting the
right Echoes on a pass (a change to the pass format, versioned like the Passport); and
party menus offering each member's Echoes.
