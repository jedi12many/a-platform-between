# Talking, reading people, and trading

*A proposal for rules v1, not built. Seeing ([open-floors.md](open-floors.md), *Being
seen*) made Stealth and Notice an **opposed** check: the other side has a number of its
own, and it sets your TN. This page does the same for talking people round, telling when
they lie, and haggling over gear, with the skills we already have.*

Today a story's `check PERSUADE hard` rolls against a TN the writer picks (110, 120...).
A stubborn guard and a gullible clerk differ only in the word the writer chose, people
never lie, and trades are fixed choices (Vell's "padded coat for a chain coat"). With
this, a person has numbers of their own, written once, and every check against them
follows; they can lie to you; and any trader can haggle over anything in the pack.

## No new skills

The Passport stores a skill in 4 bits, and the tags as a 12-bit mask: there are 12
skills, and all 12 are used ([passport-spec.md](passport-spec.md)). So these rules pair the
skills we have:

- **Persuade** (Presence) is every way of working on someone: asking, arguing, charming,
  bluffing, lying, bargaining, and threatening.
- **Intuition** (Fate) is reading them: a lie, a bad deal, a trap in a kind offer, a
  mood. As in seeing, a traveler's **Wits** stands in for it if it's better (one of you
  just notices).

## The rule: whoever acts rolls, the other side sets the TN

Seeing's rule, again:

> **Whoever is acting rolls: d100 + their skill. The TN is set by whoever they're acting
> on: 50 + their number for it, + the modifiers below.**

| Who acts | Rolls | Against 50 + | For |
|---|---|---|---|
| A traveler persuades someone | Persuade | their **Resolve** | talking a guard down, asking a favour, a parley, a bribe they'll take |
| A traveler reads someone | Intuition (or Wits) | their **Guile** | catching a lie, seeing a bad deal or a trap for what it is |
| A traveler lies to someone | Persuade, as asking | their **Resolve**, and they read you: d100 + their **Insight** against 50 + your **Persuade** | a forged pass, a false name, "the Stationmaster sent us" |
| A trader haggles with you (you haggle back) | Persuade | their **Guile** | the rate for a visit (*Trading*, below) |

So a person has three numbers, on the 100 scale like everything else:

- **Resolve**: how hard they are to talk round, or to frighten.
- **Guile**: how well they lie, and drive a bargain.
- **Insight**: how well they read *you* (your lies). A foe's Sense is a fair start for it.

A traveler's side: they're persuaded and read through their own skills (an NPC working on
you rolls against 50 + your **Intuition**, or Wits, the better), so no traveler needs a
number they don't have.

Read as the core roll reads it, as everywhere ([rules-v0.md](rules-v0.md)):

| Result | Persuading | Reading |
|---|---|---|
| **Crit** | yes, and more: a favour, a name, a better price, a friend | you see the lie, and why |
| **Success** | yes | you see the lie |
| **Success at a cost** (within 20 under) | yes, but: they want something, they'll remember, or they're wary of you from now on (worse by a step) | something's off; you don't know what |
| **Fail** | no, and asking again is harder (+20 for this visit) | you believe them |
| **Natural 01** | no, and it goes badly: insulted, alarmed, the guard calls out | you believe them, and say so |

### Modifiers (on the TN)

| | |
|---|---|
| Their mood toward you: **friendly** / wary / **hostile** | **−20** / 0 / **+20** |
| What you ask costs them little / a lot / everything (their post, their life) | −10 / +10 / +30 |
| You have leverage (what they want, what they fear, the upper hand in a fight) | −20 |
| An Echo they remember well / badly ([echoes.md](echoes.md)) | −20 / +20 |
| You don't share a language (no Translation, a drone's protocol) | +20 |
| Asked again after a fail, this visit | +20 each time |
| A lie they could check easily | +20 |

A crit or a natural 01 still counts as it does anywhere: doubles that beat the TN are a
crit, a 01 always fails.

*For example*, Kestrel (Persuade 62) asks a rust-guard captain (Resolve 55, wary) to let
the party through: TN = 50 + 55 = 105. Kestrel needs 44 or more (57 in 100); on 24 to 43
(20 in 100), the captain lets them pass but takes their names. Showing the captain the
shift words found on floor 3 (leverage, −20) makes it TN 85: 24 or more (77 in 100).

### Threats

There's no Intimidate: a threat is Persuade, and the leverage is the threat (−20 if it's
real: you outnumber them, they've seen what you can do). It works on the spot, but people
who were frightened into it are **hostile** to you after, and a band talked out of a fight
by a threat may come back.

### A party talks as a group

As in seeing ([open-floors.md](open-floors.md), *Groups*), and as checks in a party work
([party-play.md](party-play.md)):

- **The best talks:** the traveler with the best Persuade (or Intuition) rolls. First,
  each of the others rolls the same check against the same TN: each success takes 10 off
  the TN, each failure puts 10 on (a cost counts neither way; a 01 counts 20 against, a
  crit 20 for). A party that keeps quiet behind its talker doesn't roll: `check PERSUADE
  vs @vell alone`.
- **`check PERSUADE vs @vell pick`**: the party picks who talks (the others still help or
  hinder, unless `alone`).
- **Reading** is as seeing: each of you may notice. The best reader rolls, the others
  helping. A lie is checked once, when it's told: you can't keep asking whether someone
  lied.

## Lies

A person can lie. In Quest Script it's marked where it's said, and the party reads it
once, there and then, as a band is checked when it comes into sight (*Quest Script*,
below). Success: the story says you don't believe it, and a choice may open (call it, play
along, ask someone else). A cost: something's off, no more. A fail: the story goes on as if
it were true, and it isn't.

A traveler's lie is a Persuade check against the person's Resolve, as asking is, *and* the
person reads it (Insight against 50 + your Persuade); the lie works only if your check
succeeds and theirs fails. (A person with no Insight to speak of believes anything you can
say convincingly.)

## Trading

### No money on a trip

The Passport carries no purse: a traveler has gear (6 equipped, 6 in the pack), Debt, and
nothing else, and a new Passport format is the only way to add coin. So on a trip, trade is
**barter: gear for gear**. That suits the world: the station's money is Debt, and down a
yard or in a realm off the line, what you're carrying is what you're worth.

### What gear is worth

An item's **worth** comes from its **tier** (1-9, in `registry/items.txt`), in whole
numbers that fit a byte:

| Tier | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| Worth | 1 | 2 | 3 | 5 | 8 | 13 | 21 | 34 | 55 |

Two items are worth a little more than the next tier up (two tier 2s, 4, for a tier 3);
that's Vell's sword and coat for the ballistic weave. Translation doesn't change worth: a
pulse rifle that's a crossbow here is still a tier 4.

### Haggling sets the rate for the visit

When you start trading with someone, your best talker haggles once: **Persuade against 50
+ their Guile**, the others helping, with the mood and the other modifiers above. The
result is the **rate** for the whole visit, so there's nothing to gain by asking again:

| Result | The rate: what you give, for what you get |
|---|---|
| **Crit** | worth for worth, and a small thing thrown in (a tier 1, a charge) |
| **Success** | worth for worth |
| **Success at a cost** | half as much again: their price is worth × 3 ÷ 2, rounded up |
| **Fail** | double: their price is worth × 2 |
| **Natural 01** | they won't trade with you this visit |

A trade is one or more of your items for one or more of theirs: what you give must be worth
at least their price for what you get. There's no change: overpay and the difference is
lost, unless they have a tier 1 thing or a charge to make it up (their choice).

*For example*, Vell (Guile 70, wary) at her camp. Kestrel haggles: TN = 50 + 70 = 120.
Kestrel rolls 51: 51 + 62 = 113, within 20 under: a cost, 3 for 2. A chain coat (tier 2,
worth 2) costs worth 3: the iron sword and the padded coat (2 + 1). With the courier saved
(friendly, −20), TN 100: 51 + 62 = 113 is a success, and the sword alone buys the coat.

### What a trader has, and wants

- **Stock**: a list of items, written in the Departure (or the siding: Vell's are per
  floor), each with how many. What they get from you goes into their stock for the rest
  of the visit, at the rate they'd sell it.
- **Wants and won'ts**: a trader can want something (double its worth to them) or refuse
  something (a stolen gun, a cursed blade). These are a scene's business, not a number.
- **Mood**: as for talking. Robbing the courier made Vell refuse to trade at all
  ([rooms.md](rooms.md), *Talk*); now that's simply her mood (hostile: +20 on the haggle),
  and talking her round first can still change it.

### At the Waystation: Debt as money

At the Waystation (the website's shop, [waystation-web.md](waystation-web.md)), the
traders deal in **Debt**, as the station does: selling gear **pays Debt down**, buying it
**adds Debt**, at a fixed rate a point of worth (say 10 Debt), with the same haggle. That
keeps the Passport as it is (Debt is already on it), and makes gear and the trip home the
same currency, which is the world's point: everything you carry could be your fare.

The catch is the trip home: gear sold for Debt is a way to buy it down. So the station
buys at **half** (and only what it hasn't seen you sell before), and Debt from trips stays
the main way down. **This needs your decision** (*Still open*).

## Quest Script

A sketch; the compiler's syntax gets settled when it's built ([quest-script.md](quest-script.md)).

```
people
    @vell     "Vell"     resolve 60  guile 70  insight 60  wary
    @captain  "the captain" resolve 55  guile 30  insight 50  wary

== gate
+ [Talk your way past]
    check PERSUADE vs @captain          // TN 50 + Resolve 55, + mood and the rest
        success: "Go on, then." -> beyond
        cost:    He waves you through, and writes your names down. ~ set named -> beyond
        fail:    "Back the way you came."
+ {has SHIFT_WORDS} [Say the shift words]
    check PERSUADE vs @captain leverage
        ...

== camp
Vell taps the ledger. "Couriers come through here all the time."
lie @vell                                // the party reads it: Intuition against 50 + Guile
    seen: She hasn't seen one in a week. You'd bet on it.  ~ set vell_lied
    off:  Something in the way she said it.

trade @vell                              // haggle once (Persuade against 50 + Guile), then trade
    CHAIN_COAT
    ARC_PISTOL 2
    BALLISTIC_WEAVE
    wants SCRAP_PISTOL                   // worth double to her
    refuses PULSE_RIFLE
    done: -> vell_menu

~ mood @vell friendly
```

- **`people`** declares who's in the Departure and their numbers (and their mood to
  start); a foe in a parley has its numbers from the registry (below).
- **`check SKILL vs @who`**: the skill says which of their numbers sets the TN (Persuade:
  Resolve; Intuition or Wits: Guile; anything else, a number written after it). The
  modifiers are words after it (`leverage`, `costly`, `lie`...), and `alone` / `pick` for
  a party.
- **`lie @who`**: the party reads it once (`seen:`, `off:`, and the story goes on).
- **`trade @who`**: the haggle, then the trade screen: their stock and your pack, what each
  is worth at the visit's rate, until you're done.
- **`~ mood @who`**: friendly, wary or hostile; kept for the trip (an Echo, if it should
  outlast it).

Rewards stay bounded ([boarding.md](boarding.md), the reward manifest): what a trade can
give is the trader's stock, known when the Departure's compiled, and a trade only gives what
it takes worth for.

## Foes' and people's numbers

Like Sense and Stealth (`registry/senses.txt`), a foe's Resolve, Guile and Insight go in a
file of their own, read by the rules lab first and folded into `foes.txt` when rules v1 is
frozen. Set at first from the foe's other numbers and changed by hand:

| Foe | Resolve | Guile | Insight | |
|---|---|---|---|---|
| RUST_GUARD | 70 | 10 | 35 | on shift a hundred years: won't be talked off it, but answers to the shift words |
| SCRAP_GUNNER | 30 | 50 | 40 | would rather be paid than shoot |
| ASH_RAT | 20 | 0 | 20 | can't be reasoned with, can be shouted off (a threat) |
| MAINT_DRONE | 90 | 0 | 50 | doesn't argue; a drone's protocol (+20 without the right language), a fault to be fixed |

People are written in their Departure (`people`): Vell (resolve 60, guile 70, insight
60), the courier Pell (resolve 25, guile 15, insight 30).

## At the table

A person's card has three numbers and a mood. The GM says who you're working on; you roll
d100 + Persuade against 50 + theirs, ± the mood. Haggling is one roll and one line of the
rate table. Worth is the tier table, on the back of the character sheet.

## Building it, in order

As seeing was:

1. **The rules lab:** `tools/rules/social.py` (the reference: a check against a person,
   a party's help, a lie read, a haggle and a trade at a rate), and `core/next/social.c`
   held to it; reviewed cases in `tests/social/` (talked round, refused, a cost; a lie
   seen and missed; a haggle at each rate; a trade overpaid), the same on sim65.
2. **The numbers:** the foes' file, and Vell's and Pell's in the yards' talk.
3. **Quest Script and the VM:** `people`, `check ... vs @who`, `lie`, `trade`, `~ mood`;
   the trade screen in the clients (the terminal first).
4. **The explore prototype:** Vell's camp as a `trade`, the parleys as `check ... vs @foe`,
   in `content/sidings/yards-talk/`.
5. **The C64:** with rules v1 in 6502, after the battle.

## Still open

- **Debt as the station's money**: trading gear for Debt at the Waystation, at what rate,
  and whether selling can buy a ticket home (*At the Waystation*). The alternative is
  barter everywhere, the station's traders included.
- **Worth beyond tier**: a unique item (MERIDIAN's core) or a quest item: worth set by
  hand, or not for trade at all.
- **NPCs working on you**: when a person persuades a traveler (a con, a temptation),
  whether the player is ever bound by the roll, or only told how it feels. (Proposal: told,
  never bound; your choices are yours.)
- **Mood across trips**: kept as an Echo for people who should remember, or reset each
  trip.
- **How it plays**: the TNs (a wary person at 50 + Resolve; mood ±20; helpers ±10) want
  trying in the arena's explore prototype with Vell and the parleys, as seeing's did.
