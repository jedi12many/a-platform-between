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

### The check

When the party comes into a band's **sight** (within its range, a clear line between: see
*Lines of sight*), the band rolls to notice the party:

> **The band's Notice: d100 + its Sense, against TN = 80 (walking up) or 50 + the party's
> Stealth (sneaking), + whatever's against it.**

It's the core roll ([rules-v0.md](rules-v0.md)): Easy (80) if you're just walking; if
you're **sneaking** (a toggle: S; half speed), the TN is your Stealth as a defense, the
way Dodge and Armor make a Defense TN ([combat.md](combat.md)). The party's Stealth is its
**worst**: the clumsiest one gives you away (a party can split later; not yet).

| Against the band (raises the TN) | |
|---|---|
| Night, or a dark floor | +20 |
| Distance: per full 4 squares past the first 4 | +10 |
| The line passes through cover, or a cluster's edge | +20 |
| The party in cover | +10 |
| **For** the band (lowers the TN) | |
| The band is alert (it heard something, or a fight's been near) | −20 |
| The party's carrying a light, in the dark | −20 |

Results, as the core roll reads them:

- **Success:** they've seen you. The fight starts (*Where the fight is*). If you hadn't
  seen them, they act first: the first round is theirs (an **ambush**).
- **Success at a cost** (within 20 under): they **heard** something. The band turns
  toward you and is **alert** from now on (−20 next time).
- **Fail:** they didn't. They check again only when you come **4 squares closer** than
  their last check, so a careful approach is a few rolls, not one a step. Adjacent, they
  see you whatever the roll.

### You seeing them

At the same moment, the party rolls to **spot** the band: the leader's **Wits** (or
Intuition, whichever is better: one of you has a feeling), against TN = 50 + the band's
**Stealth**, with the same modifiers turned round. If you spot them first:

- They're **shown** (on the view and the minimap), marked as not having seen you.
- You choose: **sneak past** (keep sneaking: they keep checking), **go round**, **talk**
  (if they parley: rooms.md's *Talk*), or **ambush**: walk up and attack; if they still
  haven't seen you when you start it, the first round is yours.

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

It plays at a table: one roll a band when you come into its sight, another each time you
come 4 squares closer, modifiers from a short list.

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

1. **The rules:** being seen (the check, its modifiers, sight lines, Sense and Stealth for
   foes) in the rules lab, with a Python reference and tests, as rules v1's movement was
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
