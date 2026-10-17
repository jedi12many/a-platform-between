# Open floors

*A proposal (after [rooms.md](rooms.md)'s scrolling prototype, its zoom and minimap). Built
so far: **being seen**, in the rules lab (`core/next/seeing.c`, its reference
`tools/rules/seeing.py`, `tests/seeing/`: *Being seen, built*), and the **generator**
(*A floor, from a yard*: `build_open` in `tools/rooms/rooms.py`, `buildOpen` in the
prototype's `rooms.js`). Still to build: walking an open floor in the prototype, then the
C64 ([walk.md](walk.md)).*

Scrolling showed the floor works as one place. So the rooms go: a floor is **one open
area**, walked as now, with walls only where something stands (a clump of trees, rocks, a
block of houses), and fights happen **where foes see you**, on the stretch of floor you're
standing in. Gold Box games did the same: the fight is played on the ground where it
happens, and the view goes to whoever's turn it is, even if that's a foe you can't see yet.

## A floor

- **One area**, W x H squares, a solid border round it: 48 x 24 on floors 1 and 2, 64 x
  32 on 3 to 5, 80 x 40 from 6 down. On the C64 a floor stays within 80 x 48 (*On
  the C64*).
- **Clusters, not rooms.** The generator scatters **clusters** of the look's wall (a
  stand of trees in the forest, a crag, a block of houses in the town, a pillar mass in
  the dungeon): blobs of 5 to 24 squares, spaced so no two touch (about an eighth of the floor), with cover, rough and
  high ground in their lee and pits and hazards in the open between. Then the floor's
  walkable squares are made **one region** (a flood from the start; any pocket a cluster
  closed off is filled in).
- **Places on it**, set apart by distance rather than walls: the start (on the west
  side), the stairs (the walkable square farthest from the start), caches, people (Vell's
  camp, and Pell on floors 2 and 3: rooms.md's *People*) and **bands**.
- **A band** is a few foes standing together (as a room's foes were), at a spot at least
  10 squares from the start and from each other, hiding or open. The floor holds one per
  150 walkable squares; the stairs always have one, its foes one more.
- **The minimap's fog** is cleared by distance (6 squares round the party), so it's
  already right for an open floor.

### A floor, from a yard

As rooms.md's floors are, from the yard and the floor number, by `xs` and `mix` (the
Deep Yards'): `r()` draws from a xorshift16 whose state starts at
`mix(yard XOR 0x0F10, floor × 256 + 254)`, each draw one `xs` step, "r() mod n" that
16-bit number mod n. Tiles are the battle's (0 open, 1 wall, 2 pit, 3 rough, 4 cover, 5
hazard, 6 high ground); **walkable** is anything but wall, pit and hazard, a **stand**
open, rough, cover or high ground. Squares next to each other touch 8 ways; distance
**by foot** is steps 8 ways through walkable squares, **as the crow flies** the larger
gap across or down. Ties go to the smaller y, then the smaller x. `tools/rooms/rooms.py`
(`build_open`) is a reference written from this; the prototype's `rooms.js`
(`buildOpen`) must build the same floors (`tests/rooms/check_rooms.py`).

1. **The shell:** wall round the edge, open ground inside.
2. **Clusters:** (w − 2)(h − 2) / 24 tries. Each:
   1. its centre `x = 2 + r() mod (w − 4)`, `y = 2 + r() mod (h − 4)` and size
      `s = 5 + r() mod 20`;
   2. it grows from the centre: s − 1 times, `p` = its square at `r() mod (how many it
      has)`, `d = r() mod 4` (N, E, S, W): the square that way from p joins it if it's
      inside the border and not already in it;
   3. it's **kept** only if none of its squares is a wall or touches one. Kept, its
      squares are walls; then **its lee:** `r() mod 3` times, `p` = its square at `r() mod
      (how many)`, `d = r() mod 8` (N, NE, E, SE, S, SW, W, NW), `t = r() mod 4`: the square
      that way from p, if it's open, becomes cover, cover, rough or high ground (by t).
      (Not kept, no lee and no draws for it.)
3. **Open ground:** (w − 2)(h − 2) / 96 times, `x = 1 + r() mod (w − 2)`,
   `y = 1 + r() mod (h − 2)`, `t = r() mod 5`: if (x, y) is open and touches no wall, pit
   or hazard, it becomes rough, rough, pit, hazard or cover (by t).
4. **The start:** `sy = 1 + r() mod (h − 2)`; the walkable square with the smallest x,
   then the nearest y to sy (then the smaller y).
5. **One region:** every walkable square the start can't reach on foot becomes wall.
6. **The stairs:** the open square (tile 0) farthest from the start on foot.
7. **Bands:** n = (walkable squares) / 150, at least 1.
   1. **The stairs' band:** at the stand square nearest the stairs as the crow flies but
      2 or more from them.
   2. **The others**, until there are n bands or 64 × n tries are spent: `x = 1 + r() mod
      (w − 2)`, `y = 1 + r() mod (h − 2)`; a band's spot if it's a stand square, not the
      stairs, and 10 or more from the start and from every band's spot so far, as the
      crow flies.
   3. **Each band**, in that order: **hiding** unless `r() mod 4` is 0 (open). Its danger
      `g = floor + (its distance from the start on foot) / 16`; it has
      `min(4, 1 + g / 3)` foes (one more for the stairs' band, at most 4), each a foe of
      the pool **ash rat, scrap gunner, rust-guard, maintenance drone** at `r() mod
      min(4, 1 + g / 2)`. The first stands on the spot, the rest round it as a party
      fans out (rooms.md's *The party*: breadth first, N E S W NE SE SW NW) on stand
      squares that aren't the stairs, the start or another foe's.
   4. **A parley** (rooms.md's *Talk*): band k (counting from 0) talks first if
      `mix(yard XOR 0x7A1C, floor × 64 + k) mod 3` is 0; never the stairs' band.
8. **Caches:** 1 + (walkable squares) / 600, each found in up to 64 tries of
   `x = 1 + r() mod (w − 2)`, `y = 1 + r() mod (h − 2)`: a stand square, not the stairs,
   6 or more from the start and 4 or more from every band's spot and every cache so far,
   as the crow flies. Found, its item is `r() mod 5` of **iron sword, arc pistol, chain
   coat, pulse rifle, ballistic weave**.
9. **People**, by no dice: **Vell** at the stand square whose distance on foot from the
   start is nearest 8, 6 or more from every band's spot and every foe, not a cache or the
   stairs (as the crow flies). On floors 2 and 3, **Pell** the same, nearest half the
   stairs' distance on foot, and 4 or more from Vell too.

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
| The line passes through cover | +20 |
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
160. The band rolls d100 + 30, 130 at most: only a natural 100 (a crit, whatever the
total) sees you, 1 in 100; nothing short of it is near enough to hear. Later, by day
and 4 squares off, past a band with Sense 60: TN = 50 + 70 + 10 (the same helpers) = 130.
It sees you on 71 or more (30 in 100), and hears you on 51 to 70 (20 in 100).

Every check is a roll against one number, from one short list: it plays at a table. (The
10 a helper, and the TNs, want trying in the arena.)

### Lines of sight

A line from the looker's square to the other's, the battle engine's own (Bresenham's,
square by square, `in_sight` in `core/next/battle.c`, so being seen and being shot at
agree): a **wall** on it stops it; a **cover** square on it (not either end) is the +20
above, once however many. The **distance** is the battle's: the larger of the two gaps,
across and down. A looker's **range** is its Notice / 5 squares (Notice 40: 8), doubled
by day, halved at night (rounded down; at least 1).

### Precisely (for the reference and the engine)

- **Where:** the party is where its leader stands; a band where its first foe stands.
- **Light:** day, dusk or night (a dark floor is night): +0, +10, +20 on the TN.
- **A band** is one looker (its best Sense) and sets one TN: 50 + its best Stealth if
  it's **hiding** (lying in wait: the default), 80 if it's **open** (a patrol, a camp).
- **Checks, each step:** the bands in the floor's order; for each, the party looks (if a
  check is due), then the band looks back (if one is due). A check is due when the other
  is in sight and the looker hasn't checked it before, or it's at least 4 squares nearer
  than at the looker's last check. In sight and next to each other (distance 1 or 0):
  seen, no roll.
- **The dice of a check**, in order: the helpers of a sneaking party setting its TN
  (party order, the best left out); the helpers of a party looking (party order, the
  best left out); the looker's roll. The best is the first of the highest.
- **What a result does:** the party's look: success or crit, the band is **spotted**; at a
  cost, it's **heard** (a mark, no more). The band's look: success or crit, the party is
  **seen** (the fight, an **ambush** if the band wasn't spotted first); at a cost, the
  band is **alert** for good (−20 on its later checks' TNs).

### Foes' numbers

Foes get two new numbers: **Sense** (noticing, like Wits) and **Stealth** (being
missed), in [registry/senses.txt](../registry/senses.txt) by name, read only by the rules
lab (as conditions.txt is), and folded into the bestiary's columns when rules v1 is
frozen. They were set from a foe's other numbers (Sense = its attack − 10, Stealth = its
Grace) and are for changing by hand. An ash rat (Grace 50) is hard to spot; a
maintenance drone (attack 40) has Sense 30, 6 squares.

It plays at a table: a roll each way when you come into each other's sight, again each
time the gap closes by 4 squares, modifiers from one short list.

### Being seen, built

In the rules lab, as rules v1's turn was: the engine is `core/next/seeing.c`
(`apb_seeing_step`: a step of the party's leader, every band checked as *Precisely*
says; the lines, ranges and modifiers on their own too), the reference
`tools/rules/seeing.py`, written from this page. `make test-rules-next` runs
`tests/seeing/run_seeing.py`: values worked out by hand from this page (the example
above among them); reviewed approaches (`tests/seeing/*.txt`, their logs in
`tests/seeing/expected/`: walking by day, sneaking alone, a hedge between, a band
that hears and is alert after, a lamp at night, an ambush) from the reference, the
engine and the 6502 (sim65) alike; and 400 random approaches, the engine's log the
reference's roll for roll, natively, under the sanitizers and on sim65.

`python3 tools/rules/seeing.py tests/seeing/heard.txt` prints an approach's log.

Learned on the way: **at night a band only rolls once.** Ranges are halved (Sense 50: 5
squares), and the next check comes 4 squares nearer, at 1, where you're seen without a
roll; so a band that hears you at night has no second roll for its alertness to help.
Fine as it is (night favours the sneak), or the re-check distance could shrink with the
range: for playing.

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

- **The floor in memory** (built: [walk.md](walk.md), W4): a page a row of squares, its
  colours (2 bytes a square) then the squares (a byte each), so up to 80 squares across
  (3 x 80 <= 256) and 48 down; the walking engine's character map is dropped (a character
  is worked out from its square as an edge is drawn).
- **Seeing:** a band checks only when the party crosses into its range or 4 squares
  closer, so a frame does a line or two of Bresenham at most: well inside the frame loop's
  budget.
- **A fight** is the battle screen on the window's squares: the window is copied out of
  the floor as a battle map, the walking engine's screen becomes the battle screen's,
  and the view follows the turn with the same scroller.

## Building it, in order

1. **The rules** (built: *Being seen, built*): seeing and being seen (the looker rolls,
   the sneak sets the TN; groups; the modifiers; sight lines; Sense and Stealth for foes)
   in the rules lab, with a Python reference and tests, as rules v1's movement was
   ([turn.md](turn.md)); reviewed cases of approaches seen and missed.
2. **Open floors** in the generator (built: *A floor, from a yard*): `build_open` in
   `tools/rooms/rooms.py` and `buildOpen` in `rooms.js`; `python3 tools/rooms/rooms.py open
   YARD FLOOR` draws one. `tests/rooms/check_rooms.py` holds the two to each other on 300
   floors, and each floor to this page (one region, the stairs farthest, bands 10 apart,
   every foe, cache and person on free ground that can be reached, walls 6 to 25% of
   it).
3. **The prototype** (built: *Walking an open floor, built*): walking an open floor,
   sneaking (S), bands rolling as you approach (the rolls in the log), spotted bands shown,
   fights on their window.
4. **The C64:** the floor in memory without the character map, floors of any size up to
   the limit (built: W4 in [walk.md](walk.md); `build/walk-open.prg` walks yard 48213's
   sixth, 80 x 40, to its stairs, held to `tools/walk/walk.py` frame by frame); then seeing
   in 6502 (W5), and the fight on the window (W6).

## Walking an open floor, built

In the arena's explore prototype (Explore the yards, the view **Open floor**, or V while
walking; a link: `arena/#explore=48213:warden,rogue:open`), on the rules lab's own
seeing: `core/next/seeing.c` is in the arena's WebAssembly beside the battle engine
(`ar_see_begin`, `ar_see_step` in `tools/arena/web/arena.c`), and `rooms.js` hands it the
floor `buildOpen` built, the party's Notice and Stealth (Wits or Intuition; the Stealth
skill: `rooms.json`, from the travelers' sheets) and each band's (its foes' best Sense and
Stealth, `registry/senses.txt`).

- **Walking:** each square the leader steps onto is a step of `apb_seeing_step`; every
  check goes in the log, worked out: the TN and each modifier, each helper's roll, the
  best's roll and what came of it. A band you haven't spotted is "something out there"
  and isn't drawn; spotted, it's drawn where it stands and marked red on the minimap; a
  sound you heard is a yellow mark. The minimap clears out to the party's range.
- **S** sneaks (half speed, and bands roll against 50 + the best Stealth, the others
  helping or not); **L** steps the light (day, dusk, night; a floor starts with its look's:
  forest and mountain by day, town at dusk, dungeon at night).
- **A band that sees you** talks first if it parleys (rooms.md's *Talk*), else the fight:
  an ambush, its first round, if you hadn't spotted it. **A** falls on a band you've
  spotted, within 6 squares, that hasn't seen you: the first round is yours. (The battle
  engine's surprise round, `surprise travelers` or `surprise foes` in the arena's spec.)
- **The fight** is on a 16 x 8 window of the floor (`fightWindow`): inside it, holding the
  band, its middle nearest the middle between the band and the leader (if both can't fit,
  round the band); its foes where they stood, the party fanned out round the leader. On a
  16 x 8 window and view, the view doesn't need to move.
- **After:** won, the band is gone and you walk on from where you stood; fled, you're back
  along your way, 6 squares from them if your way goes that far, the band still there,
  alert, checking again only when you come 4 nearer; lost, the descent ends.

The dice of a floor's seeing are seeded by its yard and floor, so a floor walked the same
way rolls the same. `make test-arena-web` walks floors to the stairs, walking, sneaking, at
night and falling on a band, and holds every step's checks to `tools/rules/seeing.py`'s on
the same floor, party and way, roll for roll; then the fight's window, its foes and the
first round, and walking again after.

The engine holds 24 bands at most (`APB_SEE_BANDS_MAX`): an 80 x 40 floor has up to
19.

## Still open

- **Splitting the party** to scout (one sneaks ahead): later, with the party's play.
- **Light:** a floor's light (day, dusk, night, dark) from its look and depth; a carried
  light (a lamp item) is both a help and a give-away.
- **Sound:** a fight nearby makes bands within 12 squares alert.
- **Wandering:** bands that move about the floor (a patrol's path), rather than standing.
- **What a floor of 80 x 40 plays like**: how many bands, how far apart, before it drags.
