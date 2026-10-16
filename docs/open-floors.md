# Open floors

*A proposal (after [rooms.md](rooms.md)'s scrolling prototype, its zoom and minimap): not
built yet. For the prototype in the studio's arena first, then the C64's walking engine
([walk.md](walk.md)).*

Scrolling showed the floor works as one place. So the rooms go: a floor is **one open
area**, walked as now, with walls only where something stands (a clump of trees, rocks, a
block of houses), and fights happen **where foes see you**, on the stretch of floor you're
standing in. Gold Box games did the same: the fight is played on the ground where it
happens, and the view goes to whoever's turn it is, even if that's a foe you can't see yet.

## A floor

- **One area**, W x H squares, a solid border round it. Its size is the floor's (from the
  yard and the depth); the prototype's is 48 x 24 now and can be 80 x 40 or more. On the
  C64 a floor stays within 6 x 6 of today's rooms' worth (about 96 x 48: see
  *On the C64*).
- **Clusters, not rooms.** The generator scatters **clusters** of the look's wall (a
  stand of trees in the forest, a crag, a block of houses in the town, a pillar mass in
  the dungeon): blobs of 3 to 12 squares, spaced so no two touch, with cover, rough and
  high ground in their lee and pits and hazards in the open between. Then it checks the
  floor's walkable squares are **one region** (a flood fill from the start) and breaks
  through any cluster that walls a part off.
- **Places on it**, set apart by distance rather than walls: the start, the stairs (the
  farthest walkable square from the start, more or less), caches, people (the trader's
  camp, the lost traveler: rooms.md's *People*) and **encounters**.
- **An encounter** is a band of foes standing together (as a room's foes were), on a
  spot at least 10 squares from the start and from each other, facing a way. The floor
  holds about one per 150 walkable squares; the stairs always have one.
- **The minimap's fog** is cleared by distance (6 squares round the party), so it's
  already right for an open floor.

## Being seen

Foes don't start a fight because you came through a door: they start it when they **see
you**. And you might see them first.

### The rule: the sneak sets the TN, the spotter rolls

One rule, whichever way round, travelers or foes:

> **Whoever is looking rolls: d100 + their Notice. The TN is set by whoever might be
> seen: 50 + their Stealth if they're sneaking (or hiding, or standing still in cover),
> or 80 (Easy) if they aren't; + the modifiers below.**

- **Notice** is a foe's **Sense**; a traveler's **Wits** or **Intuition**, whichever is
  better (one of you has a feeling).
- **Stealth** is the Stealth skill; a foe's **Stealth** number (*Foes' numbers*).
- A band of foes is one looker (its best Sense) and one TN (its best Stealth): bands
  don't straggle; parties do (*Groups*).

| Modifiers (on the TN) | |
|---|---|
| Night, or a dark floor | +20 |
| Distance: per full 4 squares past the first 4 | +10 |
| The line passes through cover, or a cluster's edge | +20 |
| Whoever might be seen is in cover | +10 |
| The looker is alert (it heard something, or a fight's been near) | −20 |
| Whoever might be seen is carrying a light, in the dark | −20 |

Read as the core roll reads it:

- **Success:** seen. If it's a band seeing you, the fight starts (*Where the fight is*);
  if you hadn't seen them, the first round is theirs (an **ambush**). If it's you seeing
  them, they're **shown** (on the view and the minimap), marked as not having seen you.
- **Success at a cost** (within 20 under): **heard**. A band turns toward you and is
  **alert** from now on; you get a mark on the minimap where the sound came from.
- **Fail:** not seen, yet.

Each side checks when the other comes into its **sight** (within its range, a clear line
between: *Lines of sight*), and again each time the gap closes by **4 squares**, so a
careful approach is a few rolls, not one a step. Adjacent, you're seen whatever the roll.

Having spotted a band that hasn't seen you, you choose: **sneak past** (S: half speed;
they keep checking, against your Stealth), **go round**, **talk** (if they parley:
rooms.md's *Talk*), or **ambush**: walk up and attack; if they still haven't seen you when
you start it, the first round is yours.

### Groups

A party is a group, and the worst of you mustn't sink it every time, yet a clumsy party
should still drag on a skilled one. So:

- **A group sets a TN** (sneaking past a band): 50 + its **best** Stealth. Each of the
  others rolls Stealth against Normal (100): each success puts 10 **on** the TN (harder to
  see you), each failure takes 10 **off**.
- **A group makes a roll** (spotting a band): the **best** of you rolls. First, each of the
  others rolls the same check against the same TN: each success takes 10 off the best's
  TN, each failure puts 10 on.
- Either way, a success at a cost counts neither way; a natural 01 counts 20 against; a
  crit 20 for. On your own, it's just your number or your roll.

*For example*, sneaking past a band with Sense 30, at night (+20), 10 squares off (+10):
TN = 50 + 70 (the best sneak) + 30 = 150. The others, Stealth 45, 30 and 25, roll against
100: 45 + 62 = 107, a success (+10); 30 + 40 = 70, a fail (−10); 25 + 81 = 106 (+10): TN
160. The band rolls d100 + 30, 130 at most: it neither sees nor hears you. Later, by day
and 4 squares off, past a band with Sense 60: TN = 50 + 70 + 10 (the same helpers) = 130.
It sees you on 71 or more (30 in 100), and hears you on 51 to 70 (20 in 100).

Every check is a roll against one number, from one short list: it plays at a table. (The
10 a helper, and the TNs, want trying in the arena.)

### Lines of sight

A line from the middle of the band's square to the middle of each traveler's
(Bresenham's, square by square, so it's the same on paper and on the C64). A **wall**
square stops it; **cover** on the way, or a square at a cluster's edge, is the +20
above. A band's **range** is its Sense / 5 squares (Sense 40: 8 squares), doubled by day
in the open, halved at night.

### Foes' numbers

Foes get two new numbers in the bestiary ([registry/foes.txt](../registry/foes.txt),
appended as columns, so no id changes): **Sense** (noticing, like Wits) and **Stealth**
(being missed). Until they're set by hand, both come from a foe's other numbers: Sense =
its attack − 10, Stealth = its Grace. An ash rat (Grace 50) is hard to spot; a
maintenance drone (attack 40) has Sense 30, 6 squares.

It plays at a table: a roll each way when you come into each other's sight, again each
time the gap closes by 4 squares, modifiers from one short list.

## Where the fight is

- **A fight's map is a window on the floor:** 16 x 8 squares by default (the battle
  engine's largest today, and the C64's view), placed to hold the band and the party with
  the most room between them, inside the floor's border. Everything outside it is off
  the map for the fight: you can't step there, and fleeing means stepping off its edge
  (back where you came from, as through a door now).
- **Bigger fights** (a boss's yard, a set piece) name their own window: 24 x 12, 32 x 16.
  The battle engine takes maps up to 16 x 10 today (`APB_MAP_W_MAX`, `APB_MAP_H_MAX`);
  these need it raised to 32 x 16, its map still a byte a square.
- **The view follows the turn**, as the Gold Box games did: on each fighter's turn the view
  centres on them (kept inside the window), easing there as it does when walking, so a
  foe's turn shows the foe even if you haven't seen it yet; a ranged shot or a power shows
  its line. On a 16 x 8 window and a 16 x 8 view, nothing moves.
- **After:** won, the band's spot is clear, and you're walking again where the fight left
  you; fled, the band stays (healed, alert); lost, the descent ends. As now.

## On the C64

- **The floor in memory** ([walk.md](walk.md)): the colour map (a 256-byte page a row of
  squares, 2 bytes a square) and the squares (a byte each); the walking engine's character
  map is dropped (a character is worked out from its square as an edge is drawn). About 72
  pages are free for maps: a floor of up to about 96 x 48 squares fits.
- **Seeing:** a band checks only when the party crosses into its range or 4 squares
  closer, so a frame does a line or two of Bresenham at most: well inside the frame loop's
  budget.
- **A fight** is the battle screen on the window's squares: the window is copied out of
  the floor as a battle map, the walking engine's screen becomes the battle screen's,
  and the view follows the turn with the same scroller.

## Building it, in order

1. **The rules:** seeing and being seen (the looker rolls, the sneak sets the TN; groups;
   the modifiers; sight lines; Sense and Stealth for foes) in the rules lab, with a Python reference and tests, as rules v1's movement was
   ([turn.md](turn.md)); reviewed cases of approaches seen and missed.
2. **Open floors** in the generator (`tools/rooms/rooms.py` and `rooms.js` alike): clusters,
   one region, places, encounters; the floor's size a parameter; `check_rooms.py` holds
   them to each other and to the rules above (every encounter reachable, the stairs
   farthest, nothing walled off).
3. **The prototype:** walking an open floor, sneaking (S), bands rolling as you approach
   (the rolls in the log), spotted bands shown, fights on their window with the view on the
   turn.
4. **The C64:** the floor in memory without the character map, floors of any size up to
   the limit, then the fight on the window.

## Still open

- **Splitting the party** to scout (one sneaks ahead): later, with the party's play.
- **Light:** a floor's light (day, dusk, night, dark) from its look and depth; a carried
  light (a lamp item) is both a help and a give-away.
- **Sound:** a fight nearby makes bands within 12 squares alert.
- **Wandering:** bands that move about the floor (a patrol's path), rather than standing.
- **What a floor of 80 x 40 plays like**: how many bands, how far apart, before it drags.
