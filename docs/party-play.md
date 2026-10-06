# Party play: votes and declarations

*Draft for review (milestone E3.7). Nothing here is built yet; party support comes after
E7 ([engine-plan.md](engine-plan.md)). This is the design the engine is being kept ready
for.*

A party is 2–4 travelers ([parties.md](parties.md)). Players sit at **seats**: one person,
on one machine (or one chair at a table), playing one or more of the travelers. Solo play
is a party with one seat.

Two things change when there's more than one seat:

- **Story choices are voted on** instead of picked.
- **Fights are declared at once**: each round, every seat says what its travelers will
  do, and then the round plays out.

Both work the same at a table, on one screen and over a network. Neither depends on
machine speed, and neither changes the story engine much. The governing rule is this:

> **The VM never sees a vote or a declaration, only what was decided.** A menu still
> returns one pick; a traveler's turn still returns one action. Votes, timers and
> declarations live in the client, so solo play, tests and party play run the same code,
> and a party's trip is still one stream of choices that replays exactly.

## Story choices

### The leader, and how the party decides

Every party has a **leader**, elected by the party, and a **way of deciding**, chosen
when it forms:

| Way of deciding | Story choices |
|---|---|
| **The leader decides** | The leader makes every story choice. Everyone else can suggest: suggestions show on every screen as they're made, but only the leader's pick counts. |
| **Democracy** | Every seat votes, and the most votes wins. The leader breaks a tie. |

Either way, the leader is one of the players, not a referee: they play their own travelers
like everyone else. The way of deciding only covers **story choices**. In a fight each
seat still declares for its own travelers, and personal moments are still each
traveler's own.

**Electing the leader.** When the party forms, every seat votes for a leader (itself
included), one vote per seat. The most votes wins; a tie goes to the seat that formed
the party. At any story menu, any seat can **call an election**, and the party votes
again before the menu's choice. The leader changes only if someone else wins outright,
so a tie keeps the current leader. Elections and the way of deciding can't change during
a fight.

**If the leader drops out**, the remaining seats elect a new one before the next choice.

### How a vote goes (democracy)

1. **The menu goes up on every screen.** Everyone reads the same scene and sees the same
   numbered options.
2. **Every seat votes.** One vote per seat, however many travelers it plays: votes are
   for people, not characters. A player running three of their own characters next to a
   friend running one doesn't get three votes.
3. **Votes show as they come in**, with who cast them ("Ada: the mountain path"). A seat
   can change its vote until the vote closes. At a table this is just talking it over.
4. **The vote closes** when every seat has voted, or when the timer runs out (if the
   party set one). A seat that hasn't voted abstains.
5. **The most votes wins.** **The leader breaks a tie**: if the leader voted for one of
   the tied options, that one wins; if not, the leader is asked to choose between them.
6. **The decision is announced** ("The party takes the mountain path, 2 votes to 1"), and
   the story goes on.

**With the leader deciding**, the menu goes up the same way, the others' suggestions show
as they come in, and the choice is made when the leader picks.

**Timers are optional, generous and set by the party** (off, 1, 5 or 30 minutes, or a
day for play-by-mail). Under democracy a timer doesn't start until the first vote is cast,
so nobody can be timed out of reading. If it runs out with no votes at all, the leader
decides. With the leader deciding, there's no timer: the story waits for the leader.

### What's on the menu

The options are the same for everyone, worked out by the host, and the conditions on
them read the party, not one traveler:

| In a condition | In a party, it means |
|---|---|
| `race RAD_DRYAD`, `class TINKER`, `has KEYCARD`, a stat or skill | **someone in the party** qualifies. The option names who: *[Ask Fen about the bark (Fern)]* |
| a flag, a variable, `visited` | the story's own memory, shared by everyone, as now |
| an Echo | **anyone's** Echo: your spared bandit can turn up in my story |

Text that reads the character (`{name}`, `if race …` in a passage) reads the
**spotlight**: the traveler the moment is about. It's whoever made the last check or was
named by the last option, and by default the party's first traveler.

### Checks in a party

A story `check` is rolled once, by one traveler, so the result is one branch, as in solo:

- **By default, the best at it rolls**: the traveler with the highest rating for that
  check (ties: the one earliest in the party). At a table: "who's got the best Stealth?
  You do it." They become the spotlight.
- **`check STEALTH everyone`**: everyone rolls and the **worst** result counts, for
  things the whole party must get right at once (sneaking past a guard, holding a rope).
- **`check PERSUADE pick`**: the party chooses who tries, like any story choice (by vote
  or by the leader).

### Personal moments

Some choices belong to each character, not the party: what you say to the Stationmaster,
which relic you take from the vault. A scene can say so:

```
== vault personal
The vault holds one thing for each of you.
+ [The lantern] ~ give LANTERN
+ [The compass] ~ give COMPASS
```

- **Each seat chooses for each of its travelers**, all at once, the way votes are cast.
  Nobody sees the others' picks until everyone has chosen.
- **The choices then run in party order**, each with that traveler in the spotlight. So
  `~ give` gives to that traveler, and a `check` is that traveler's.
- **A personal choice can't change where the story goes.** Its options can't jump
  (`->`), fight or end the Departure. Afterwards, the story carries on from the scene's
  next line for everyone, together. The compiler checks this.
- **Solo, a personal scene is an ordinary menu**, so solo Departures can use them freely.

## Fights: declaring at once

Solo, you choose at your traveler's turn, seeing everything that's happened so far. With
more than one seat, waiting for each player in turn would be slow. So:

1. **At the start of each round, every seat declares** for each of its travelers: where
   to go and what to do. Declarations are shown to the rest of the party as they come in,
   so you can plan together ("I'll get in its face, you shoot it"). A seat can change its
   declaration until the round closes.
2. **The round closes** when everyone has declared, or the timer runs out. A traveler
   with no declaration **defends** (it stays put, +20 to its TN).
3. **The round plays out in the usual order** (by Grace, [combat.md](combat.md)). Foes
   act by their printed rules, and each traveler does what was declared for it,
   **worked out at its turn**.

### Declare intentions, not squares

By the time your turn comes, things have moved: the foe you meant to stab may be down,
or across the room. So a declaration is an **intention**, worked out against the board as
it is at your turn. This is how people play at a table ("I go after the rust-guard"), and
it's what the E3.5 menus already offer:

| Where to | At your turn, you move to… |
|---|---|
| Stay here | nowhere |
| Next to foe *F* | the nearest square next to *F* you can reach; if none, as close to *F* as you can |
| Toward foe *F* | as close to *F* as you can |
| To the exit / into cover / onto high ground | the nearest one you can reach; if none, as close as you can |
| Next to ally *A* | the nearest square next to *A* you can reach (to help, or to shield them) |

| Then | At your turn |
|---|---|
| Attack *F* | if *F* is down or gone, or out of reach after your move: **the nearest foe you can attack**; if there's none, you defend |
| Help *A* against *F* | if that's no longer possible, you defend |
| Defend, Wait | as declared |
| Flee | as declared: the roll is made at your turn, against the foes next to you then |

Every "nearest" is settled the same way everywhere: fewest squares away, then cheapest to
reach, then nearest the top-left corner of the map (the rule foes already use). Hazards
are avoided when there's another square as good. So intentions resolve identically on
every machine and at the table, and the core does it (an `apb_battle_intent` call that
turns an intention into an action), not each front end.

An area attack follows its target, and **can catch an ally who has moved into the
blast**. That's the risk of throwing into a melee, and it's the rule at the table too.

### A round with two seats

Kestrel (Ada's seat, Grace 40) and Fern (Ben's seat, Grace 25) against a scrap gunner
(Grace 30) and a rust-guard (Grace 20). The order is Kestrel, the gunner, Fern, then the
rust-guard.

- **Declared.** Ada: *next to the rust-guard, attack it*. Ben: *into cover, attack the
  gunner*.
- **The round.**
  1. Kestrel moves next to the rust-guard and attacks it. She drops it.
  2. The gunner shoots Fern, who is still in the open: her turn hasn't come.
  3. Fern moves into the nearest cover (+20 to her TN against shots from now on) and
     shoots the gunner.
  4. The rust-guard is down, so it doesn't act.
- **Had Kestrel dropped the gunner instead**, Fern would still move into cover, then
  shoot the nearest foe she could. If there were none, she'd defend.

## Over the network

The host is authoritative ([engine-plan.md](engine-plan.md)). Only these messages travel,
each a few bytes:

| From | Message | Means |
|---|---|---|
| host → all | `PARTY rule leader` | how the party decides (the leader decides, or democracy) and who leads, at boarding and after every election |
| seat → host | `ELECT seat` | a vote in a leader election, or the call for one |
| seat → host | `VOTE menu pick` | a vote, a suggestion (the leader deciding), or a change (`pick` 0 withdraws it); with the leader deciding, the leader's `VOTE` decides |
| host → all | `TALLY menu votes…` | the votes so far, to show |
| host → all | `DECIDED menu pick` | the vote's result: every machine plays it |
| seat → host | `PERSONAL menu traveler pick` | a personal choice |
| seat → host | `DECLARE round traveler intention` | a declaration, or a changed one |
| host → all | `ROUND round intentions…` | the round's declarations, closed: every machine plays the round |

- **`menu` counts the menus of the trip** (1, 2, 3…), so a late vote for a menu that has
  already closed is ignored, not applied to the next one.
- **An intention is 4 bytes**: where (stay, next to, toward, exit, cover, high ground),
  whom, what (attack, help, defend, wait, flee) and whom.
- **The dice are the host's seed**, sent once when the party boards. After that every
  machine rolls the same dice from the same choices, so nothing else needs sending.
- **A seat that drops out** abstains from votes, and its travelers defend in fights. When
  it reconnects, the host sends the choices so far and it replays to catch up (a trip of
  a few hundred choices replays in moments, even on a C64).

## At the table

The same, with talk instead of messages. The table elects a leader first. The Conductor
(the person running the Departure) reads the scene and the options, and the table talks
it over; then the leader calls it, or hands go up and the leader settles a tie. At a
fight, everyone says what their character does, the Conductor writes it on the
initiative list, and works down it. When a target has fallen, it's "nearest foe you can
reach"; nobody re-declares mid-round. Personal moments are written on scraps of paper
and revealed together.

## What it changes in the engine

| Piece | Change |
|---|---|
| VM, menus | none: `hal_menu` returns the decided pick |
| VM, fights | none: at a traveler's turn, `hal_battle_turn` returns the action the client worked out from its intention |
| Rules core | `apb_battle_intent(who, intention, &action)`: the "nearest" rules above, moved out of the terminal front end (where E3.5 put them) so every client and the table agree |
| VM, party | (with party support) several travelers, the spotlight, party conditions and checks, `personal` menus |
| Quest Script | `check X everyone`, `check X pick`, `== scene personal` |
| Clients | elections, voting, declaring and timers, on the HAL, shared by every front end like the boarding desk |
| Tests | a recorded party trip is still one choice list. Votes and timers get tests of their own: a script of votes and timeouts in, the decisions out |

## Questions for review

These are recommendations, not settled. Each one's alternative is noted. (Settled in
review: an elected leader, and the party chooses "the leader decides" or democracy with
the leader breaking ties.)

1. **One vote per seat, not per traveler.** The alternative is one per traveler, which
   favors whoever brings the most characters.
2. **Solo fights stay "choose at your turn".** The alternative is declaring at round
   start even solo, so that solo and party play the same. That costs solo play
   information for no gain.
3. **Declarations are visible to the party as they're made.** The alternative is hiding
   them until the round closes, like personal choices. Visible is how a table plays, and
   it makes Help possible.
4. **Story checks: the best at it rolls by default.** The alternative is a vote for who
   rolls every time, which is slower.
