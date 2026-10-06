# Party play: story choices and fights

*Draft for review (milestone E3.7). Nothing here is built yet; party support comes after
E7 ([engine-plan.md](engine-plan.md)). This is the design the engine is being kept ready
for.*

A party is 2–4 travelers ([parties.md](parties.md)). Players sit at **seats**: one person,
on one machine (or one chair at a table), playing one or more of the travelers. Solo play
is a party with one seat.

Party play changes two things:

- **Story choices**, between fights, are made by the party: by its elected leader, or by
  a vote.
- **Fights** are played the way *Pool of Radiance* played them: each character takes its
  own turn, in order, and its player chooses what it does then. A **combat log** tells
  everyone what happened, so nobody has to watch every turn.

Both work the same at a table, on one screen and over a network, and neither depends on
machine speed. The governing rule:

> **The VM never sees a vote, only what was decided.** A menu still returns one pick;
> a traveler's turn still returns one action. Leaders, votes and timers live in the
> client, so solo play, tests and party play run the same code, and a party's trip is
> still one stream of choices that replays exactly.

## Story choices

### The leader, and how the party decides

Every party has a **leader**, elected by the party, and a **way of deciding**, chosen
when it forms:

| Way of deciding | Story choices |
|---|---|
| **The leader decides** | The leader makes every story choice. Everyone else can suggest: suggestions show on every screen as they're made, but only the leader's pick counts. |
| **Democracy** | Every character gets a vote, and the most votes wins. The leader breaks a tie. |

**One vote per character.** A player who brings two characters casts two votes. The
votes belong to the travelers who'll live with the result. (A player can split their
votes.)

Either way, the leader is one of the players, not a referee: they play their own travelers
like everyone else. The way of deciding only covers **story choices**. In a fight every
character's player chooses for it on its turn, and personal moments are still each
traveler's own.

**Electing the leader.** When the party forms, every character votes for a leader (one
of the players), so again a player with two characters has two votes. The most votes
wins; a tie goes to the player who formed the party. At any story menu, any player can
**call an election**, and the party votes again before the menu's choice. The leader
changes only if someone else wins outright, so a tie keeps the current leader. Nobody
can call an election during a fight.

**If the leader drops out**, the rest elect a new one before the next choice.

### How a vote goes (democracy)

1. **The menu goes up on every screen.** Everyone reads the same scene and sees the same
   numbered options.
2. **Every character votes**, through its player.
3. **Votes show as they come in**, with who cast them ("Kestrel: the mountain path"). A
   player can change a vote until the vote closes. At a table this is just talking it
   over.
4. **The vote closes** when every character has voted, or when the timer runs out (if the
   party set one). A character that hasn't voted abstains.
5. **The most votes wins.** **The leader breaks a tie**: if the leader voted for one of
   the tied options, that one wins; if not, the leader is asked to choose between them.
6. **The decision is announced** ("The party takes the mountain path, 3 votes to 1"), and
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

- **The best at it rolls.** The traveler with the highest rating for that check makes
  it (ties: the one earliest in the party), with no choosing. The party's best lockpick
  picks the lock. At a table: "who's got the best Stealth? You do it." They become the
  spotlight.
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

- **Each character chooses**, through its player, all at once. Nobody sees the others'
  picks until everyone has chosen.
- **The choices then run in party order**, each with that traveler in the spotlight. So
  `~ give` gives to that traveler, and a `check` is that traveler's.
- **A personal choice can't change where the story goes.** Its options can't jump
  (`->`), fight or end the Departure. Afterwards, the story carries on from the scene's
  next line for everyone, together. The compiler checks this.
- **Solo, a personal scene is an ordinary menu**, so solo Departures can use them freely.

## Fights: every character on its turn

Fights play like *Pool of Radiance*, solo or in a party:

1. **The order of play** is set once per fight, by Grace ([combat.md](combat.md)).
2. **On a character's turn, its player chooses** what it does, seeing the board as it is
   then. Nobody declares in advance. Foes act by their printed rules on their turns.
3. **Everyone sees every turn as it happens**, and the **combat log** keeps all of it.

The actions are in [combat.md](combat.md) (*Your turn*): move, attack, cast, guard,
wait, flee, and **quick**, which hands the character to the computer.

### The combat log

Everything that happens in a fight is written to the log as a plain sentence with its
numbers, as the terminal already prints it (E3.5): *Scrap gunner attacks Fern: 66 + 40 =
106 against 78, a crit: 12 damage.* The log is what lets players step away between
their turns:

- **At the start of each character's turn**, if its player wasn't the one who acted
  last, the screen opens with **"Since your last turn"**: the log since that player last
  chose. Then the map and the menu. A player who watched it all can skip the recap with
  one key.
- **Any player can read back** through the whole fight's log at any time, even when it
  isn't their turn.
- **The story log works the same way.** If you missed some story text (a player off
  making tea while the others read on), it's there to read back.
- **Over the network, nothing extra is sent**: every machine plays every turn itself and
  writes its own log, and the logs are the same everywhere because the rules are.
- **On a C64**, the log is a ring of the last 40 or so lines (about 1.5 KB). That's plenty
  for one round, and a recap never needs more than a round.

### Timers and absent players

- **Turn timers are optional**, like vote timers. When one runs out, the character goes
  **quick** for that turn (the computer plays it by its rule), and the log says so.
- **A player who drops out** has their characters go quick until they come back.
- **Quick is always the player's choice too.** A player can put a character on quick
  ("handle the routine stuff") and take it back at the start of any of its turns, as in
  *Pool of Radiance*. A solo player can put the whole party on quick.

## Over the network

The host is authoritative ([engine-plan.md](engine-plan.md)). Only these messages travel,
each a few bytes:

| From | Message | Means |
|---|---|---|
| host → all | `PARTY rule leader` | how the party decides (the leader decides, or democracy) and who leads, at boarding and after every election |
| player → host | `ELECT traveler player` | a traveler's vote in a leader election, or the call for one |
| player → host | `VOTE menu traveler pick` | a traveler's vote, a suggestion (the leader deciding), or a change (`pick` 0 withdraws it); with the leader deciding, the leader's `VOTE` decides |
| host → all | `TALLY menu votes…` | the votes so far, to show |
| host → all | `DECIDED menu pick` | the result: every machine plays it |
| player → host | `PERSONAL menu traveler pick` | a personal choice |
| player → host | `TURN traveler action` | what a character does on its turn |
| host → all | `ACTED turn traveler action` | the turn, decided: every machine plays it |

- **`menu` counts the menus of the trip** (1, 2, 3…), and `turn` the turns of the fight,
  so a late message for something already decided is ignored, not applied to the next
  one.
- **An action is 4 bytes**, the battle engine's own: where to move, what to do, to whom.
  A quick turn is sent as the action the computer chose, so a replay never depends on
  who was at the keyboard.
- **The dice are the host's seed**, sent once when the party boards. After that every
  machine rolls the same dice from the same choices, so nothing else needs sending.
- **A player who reconnects** is sent the choices so far, and replays them to catch up.
  A trip of a few hundred choices replays in moments, even on a C64. Then they read the
  log.

## At the table

The same, with talk instead of messages. The table elects a leader first. The Conductor
(the person running the Departure) reads the scene and the options, and the table talks
it over; then the leader calls it, or hands go up (one per character) and the leader
settles a tie. In a fight the Conductor works down the initiative list and each player
says what their character does when it's their turn. Personal moments are written on
scraps of paper and revealed together.

## What it changes in the engine

| Piece | Change |
|---|---|
| VM, menus | none: `hal_menu` returns the decided pick |
| VM, fights | none: at a traveler's turn, `hal_battle_turn` returns its action, chosen by its player or, on quick, by the computer |
| Rules core | the *Pool of Radiance* actions (guard, wait, free attacks on leaving a foe's reach, quick) in `combat.md`: milestone E3.8 |
| VM, party | (with party support) several travelers, the spotlight, party conditions and checks, `personal` menus |
| Quest Script | `check X everyone`, `check X pick`, `== scene personal` |
| Clients | elections, voting, timers, the recap and the logs, on the HAL, shared by every front end like the boarding desk |
| Tests | a recorded party trip is still one choice list. Votes and timers get tests of their own: a script of votes and timeouts in, the decisions out |

## Settled in review

- An elected leader. The party chooses **the leader decides**, or **democracy** with the
  leader breaking ties.
- **One vote per character**, in story votes and in leader elections.
- **Fights are played turn by turn**, each character choosing on its own turn, solo or in
  a party, like *Pool of Radiance*, with a combat log and a recap for whoever wasn't
  watching. (This replaces an earlier draft where everyone declared at the start of a
  round.)
- **Story checks: the best at it rolls.**
