# The Deep Yards

*Milestone E7: a prototype of the first Siding ([sidings.md](sidings.md)).*

Beneath the Waystation, the rail yards go down further than they should. A descent is ten
floors, each with its own realm, its own way through and its own fight. A **yard** is
one seed: the same yard number builds the same ten floors on every machine, whatever the
player does on the way down. Seeds can be shared ("yard 48213, floor 9 is nasty").

The Deep Yards is written in Quest Script like any Departure
(`content/sidings/deep-yards/deep-yards.qs`). Three things in the language make it
procedural, and the rest is ordinary story:

| Quest Script | Does |
|---|---|
| `kind: siding` | a Siding: it asks for a yard number when boarding without a Boarding Pass, and can't change Debt or plant Echoes |
| `~ pick room 4 on floor` | sets `room` to 1..4, decided by the yard and the floor, never by what came before |
| `yard depths` and `fight yard depths on floor` | a battle map and foes, generated from the yard and the floor, from a pool of foes the Departure lists |
| `{yard}` | the yard's number, in text |

## The yard

A trip's **yard** is its dice seed, a whole number from 0 to 65535:
- the Boarding Pass's seed;
- or, travelling without a pass, a number the player types at the desk (blank picks one).

It is kept with the trip and in saves.

The dice for checks and fights still roll from the same seed, so a check made on floor 2
doesn't change floor 3. Picks and maps never touch the dice; they come from the yard by
the mixing function below. So two players in yard 48213 see the same floors, and roll
their own luck on them.

### Mixing

All arithmetic is on 16-bit whole numbers, wrapping as unsigned. `xs` is the core's
xorshift16 (`core/src/rng.c`): `x ^= x << 7; x ^= x >> 9; x ^= x << 8`.

```
mix(yard, key):
    x = yard
    if x = 0: x = 0xACE1
    repeat 3 times:
        x = xs(x)
        x = (x × 0x9E37 + key) mod 65536
        if x = 0: x = 0xACE1
    return xs(x)
```

The multiply and add matter: xorshift alone is linear, so two picks whose keys differ
only in their salt would always differ by the same bits, and a floor's picks would come
in fixed pairs (the first version did exactly that: every wagon held the same thing).

A **pick** of 1..n, keyed by a variable's value k (0 when there's no `on`), at the pick's
**salt** s (0..254, numbered by the compiler in the order the picks appear in the
script), is `1 + mix(yard, k × 256 + s) mod n`.

## A floor's battle map

`fight yard POOL on FLOOR` builds a map for floor f (the variable's value, 1..255; 0 counts as 1) from
the yard and the pool. A generator draws numbers r() from a xorshift16 whose state starts
at `mix(yard, f × 256 + 255)` (salt 255 is never a pick's); each r() is one `xs` step,
returning the new state. "r() mod n" means the 16-bit result mod n.

1. **The room.** 12 × 8 squares: walls (1) all round the edge, open ground (0) inside.
2. **The way out.** `ey = 1 + r() mod 6`. The exit (7) is at (0, ey) and the traveler
   starts at (1, ey). Row `ey` is never built on, so there's always a straight run back.
3. **Terrain.** `6 + f / 2` times (whole division):
   `x = 3 + r() mod 8`, `y = 1 + r() mod 6`, `t = r() mod 8`, in that order.
   - If `y = ey`, place nothing.
   - Otherwise put tile `[3, 3, 4, 4, 6, 2, 1, 5][t]` at (x, y): rough, rough, cover,
     cover, high ground, pit, wall, hazard. Below floor 4, hazard becomes rough.
4. **Where you can get to.** Flood from the start through squares that aren't wall (1) or
   pit (2), one step in any of the eight directions. Every foe stands on a square
   reached this way.
5. **Foes.** `n = 1 + (f − 1) / 4`, at most 4: floors 1–4 have one, 5–8 two, 9–12
   three, and below that four. For each foe in turn:
   - **Kind:** `kind = r() mod L`, where `L = min(pool size, 1 + f / 3)`. The pool lists
     foes weakest first, so deeper floors reach further down it.
   - **Square:** up to 32 tries of `x = 7 + r() mod 4`, `y = 1 + r() mod 6`, taking the
     first square that is reached (step 4), is open, rough, cover or high ground (0, 3,
     4, 6), and has no foe on it already. If all 32 miss, take the first such square
     scanning x from 10 down to 1, and y from 1 to 6 within each x.
   - **Stats:** the pool foe's, but with health `+ (f − 1)` (at most 255) and attack
     `+ (f − 1)` (at most 200).
6. **The record.** It's an encounter record exactly as in the depot ([vm-spec.md](vm-spec.md),
   *Encounters*): 12, 8, the squares two to a byte, one start, the foes in the order
   placed, and their names from the pool.

The pool is an ordinary encounter record in the depot: the foes as the bestiary has them,
standing in a row on a one-row map (so the record is valid, and checked like any other).
The VM builds each floor's map into the free space after the depot (at most 210 bytes;
the compiler keeps the depot small enough). It checks the map like any record from an
image, and plays it with the battle engine. Saves don't store it: a resumed trip builds
it again, the same.

On the C64 the generator is in the LOAD overlay. A floor's map is built, then the BATTLE
overlay comes in to play it.

`tools/yards/yard.py` is a reference written from this page. `make test-yards` checks the
C generator (`core/src/yard.c`) against it on thousands of yards and floors, natively and
on sim65. It also checks that every map's foes can be reached, and that every map plays to
an end under the sanitizers.

## The descent

`content/sidings/deep-yards/deep-yards.qs`, ten floors:

- **Each floor:**
  - picks a realm, which is the floor's look and feel;
  - offers two of four ways on (a fight, a cache, a shrine with a check, a place to rest),
    picked by the yard;
  - always ends in a fight at the stairs.
- **XP:** each floor cleared pays XP, once.
- **Ways out:** climb back up at any landing and keep what you've earned. Lose a fight
  and you're pulled back to the Waystation, the trip failed, as the rules say for death.
- **Rewards:** Sidings pay no Debt and plant no Echoes (`kind: siding` refuses both).

## Tests

- **The generator:** `make test-yards` compares the C generator with the Python
  reference on 3,360 maps (natively, and a sample on sim65), and checks that picks are
  even and independent.
- **Playthroughs:** twelve VM playthroughs (`tests/vm/cases.txt`, `yards-*`) run every
  instruction of the descent, on PC and 6502, each saved and resumed at every menu.
  - They found the routes by a random search; `SEED+LEVEL` sends the harness's traveler
    down as a veteran, so some reach the bottom.
  - The 6502 test program has no room for the whole engine, so the yards' 6502 build
    leaves out the boarding desk (`build/harness-yards.sim`), and the other build leaves
    out the yards.
  - 150 damaged copies of the yards' image are played under the sanitizers.
- **On the C64:** `make test-c64` plays a descent from the `.d64`, and `make test-modern`
  plays the same yard on the desktop and in the browser, to the same transcript.

Building it found two mistakes, fixed before anything shipped:
- **The first mixing function was linear:** pure xorshift, so every wagon on a floor
  held the same thing for the same side track.
- **The first foe numbers were too steep:** even a level-10 veteran died around floor
  6. Now a level-1 traveler reaches the bottom about one time in ten.

## Not yet

- **Translation per floor.** The realm is text for now. A floor's realm should
  Translate your gear (`apb_translate`), and that needs the VM to carry a realm.
- **Daily yards** with leaderboards (W2 issues the passes that carry them).
- **Party yards.**
