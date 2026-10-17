# Talking, reading people, and trading

*A proposal for rules v1, not built. Seeing ([open-floors.md](open-floors.md), *Being
seen*) made Stealth and Notice an **opposed** check: the other side has a number of its
own, and it sets your TN. This page does the same for talking people round, telling when
they lie, and haggling over gear, with the skills we already have; and how gear changes
hands at the Waystation: tokens, the station's traders, and the Exchange, where travelers
sell their collectibles to each other.*

Today a story's `check PERSUADE hard` rolls against a TN the writer picks (110, 120...).
A stubborn guard and a gullible clerk differ only in the word the writer chose, people
never lie, and trades are fixed choices (Vell's "padded coat for a chain coat"). With
this, a person has numbers of their own, written once, and every check against them
follows; they can lie to you; and any trader can haggle over anything in the pack.

**Gear never buys Debt down.** Debt is your fare home, and it's paid in tickets: the
jobs you do. Nothing here turns gear, or anything else, into Debt paid, so going home is
never something you can farm or buy ([world-bible.md](world-bible.md), *The endgame*).

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
**barter only: gear for gear**. That suits the world: down a yard or in a realm off the
line, what you're carrying is what you're worth, and the station's money means nothing
there. A trip's receipt and Travel Stamp stay as they are: items given and taken, never
money.

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

## At the Waystation: tokens

At home, between trains, the station has a money of its own: **tokens**, brass, stamped
with the Waystation's clock. Tokens buy and sell gear and collectibles at the Waystation,
and nothing else.

- **They're the Waystation's, not the Passport's.** A traveler's tokens are kept in the
  station's ledger, with their lost-and-found (on the player's account,
  [waystation-web.md](waystation-web.md)), never on a Passport, a Boarding Pass or a
  Travel Stamp. No format changes, and no client ever sees a token: a C64 player spends
  them on the website like everyone else, between trips.
- **They never touch Debt.** Tokens can't pay a fare, and Debt can't be turned into
  tokens. They can't be bought with real money either: they're earned by selling gear
  and collectibles, and those are earned on trips.
- **A traveler's own.** Each traveler has their own purse, as they have their own
  lost-and-found. A player's travelers can pass gear to each other through the
  lost-and-found, but tokens stay with the traveler who earned them (or the roster would
  be one purse, and a new traveler a rich one).

### The station's traders

The Waystation's traders (the website's shop) buy and sell at fixed token prices from an
item's worth (*What gear is worth*):

| | Tokens |
|---|---|
| They sell an item at | worth × 10 |
| They buy one from you at | worth × 5 |

They're people like any others, with Resolve, Guile and Insight: your traveler haggles once
a visit, and the rate applies to their prices (a fail: double what they sell at, and they
buy at half of half). Their stock is the season's ([seasons.md](seasons.md)): the gear a
station's realms are known for, refreshed as Departures come out, and what travelers have
sold them.

Selling to the station is how a traveler turns gear into tokens; half is the price of
having a buyer whenever you want one. The station doesn't deal in collectibles: one is
worth what another traveler will pay for it, at the Exchange.

### Collectibles

Some things found on trips are worth having for themselves, not for what they do: a
**collectible**. The bell from the clock tower that was stolen on schedule, a ticket punched
in a realm that's since faded, a rust-guard's shift badge, a pressed flower from 1,000,000
BC. They're rare, and travelers trade them.

- **No rules.** A collectible has no tier, no damage, nothing on a sheet: it can't make a
  traveler stronger, so it can be traded freely without unbalancing anything.
- **Kept at the Waystation**, in the traveler's **collection** (a cabinet in their room),
  not on the Passport: they don't take a pack slot, and the Passport's format doesn't
  change. A trip that finds one gives it like any item (`~ give`; the Travel Stamp's 8 new
  items count it), and it goes straight to the collection when the stamp lands.
- **Rare, and numbered.** Each kind (in the registry, with the items, as an archetype of its
  own: `curio`) has a **rarity**, and copies are numbered as they land: *No. 14 of 50*. A
  Departure gives one on a hard road (a crit, a hidden way, a choice few make), and the
  reward manifest still bounds it. Some come only in a season, and are never made again.
- **Some are part of the story:** an Echo's keepsake, a Legend's relic
  ([echoes.md](echoes.md)). These are shown in the collection but never sold.

### The Exchange

A board in the concourse where travelers sell to each other, by asking price, with the
owner away. It's for **collectibles**; whether gear goes on it too is open (*Still open*):

- **Listing:** a traveler puts something from their collection (or, if gear's allowed,
  their lost-and-found or pack) up for a price in tokens. It **leaves their traveler** at once, held by the station: it's on no Passport
  issued after that, can't be carried, and can't be listed twice. Taken down, it goes back
  to their lost-and-found.
- **Buying:** another traveler pays the price and the item is theirs, in their
  collection (or lost-and-found), at once; the seller's purse gets the tokens **while they're away**, less
  a fee to the station (1 token in 10: tokens leave the game, so they keep their worth),
  and a note waiting for them: *Sold: the clock-tower bell, No. 14 of 50, to Wren, 45
  tokens.*
- **No haggling:** a listing's price is its price. (Haggling is for people the rules play;
  a player's price is the player's.)
- **Expiry:** a listing nobody buys comes down after a while (a season's week, say), back to
  where it came from, so the board stays alive.
- **Not while travelling:** a traveler with a ticket out (a Boarding Pass issued, its
  stamp not landed) can't list, buy or take down: the trip might use the item up or trade
  it away, and the stamp lands on the traveler as they are when it comes back
  ([boarding.md](boarding.md), *Landing a stamp*). So nothing on the Exchange is ever also
  on a train.

Why it holds: since W2 every Boarding Pass is issued by the Waystation from the traveler as
its ledger has them, and stamps land against its tickets, so an old Passport with a sold
item on it boards nobody (an old code is a keepsake, not a traveler). Before that (W1,
stamps on trust) there's no Exchange.

### Trading between travelers

Two travelers trading directly (friends at the bar) is the Exchange with a price of
nothing, offered to one traveler; or a swap, both offers on the table and both accepting.
Collectibles, always; gear, as the Exchange decides. Inside a party on a trip, gear passes
freely, as it does between your own slots.

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
6. **The Waystation** (W3, [waystation-web.md](waystation-web.md)): tokens in the
   station's ledger, collections, the station's traders, the Exchange, trading between
   travelers; collectibles in the registry (`curio`), with a rarity each. It
   needs W2's accounts and ticket ledger first.

## Still open

- **The token prices**: worth × 10 to buy, × 5 to sell, and the Exchange's fee of 1 in 10
  want trying once there's loot to sell; so does what a trip's loot is worth in tokens.
- **Gear on the Exchange**, or collectibles only. Collectibles only keeps the market from
  outfitting a new traveler with an old one's loot; gear too makes the market busier, and
  wants a limit: gear only up to a tier the buyer's level allows ([turn.md](turn.md),
  *Levels and gear*), the same limit at the station's traders.
- **Things that can't be sold**: a unique or quest item (MERIDIAN's core, the ticket stub),
  a story keepsake: kept, never listed.
- **How rare is rare**: how many of a collectible a season makes, and whether a numbered run
  can sell out for good.
- **Worth beyond tier**: an item worth more than its tier (a rare one, a set): worth set by
  hand in the registry.
- **NPCs working on you**: when a person persuades a traveler (a con, a temptation),
  whether the player is ever bound by the roll, or only told how it feels. (Proposal: told,
  never bound; your choices are yours.)
- **Mood across trips**: kept as an Echo for people who should remember, or reset each
  trip.
- **How it plays**: the TNs (a wary person at 50 + Resolve; mood ±20; helpers ±10) want
  trying in the arena's explore prototype with Vell and the parleys, as seeing's did.
