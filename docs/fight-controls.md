# A fight's controls on the C64 (rules v1)

*A spec, for when rules v1 ([turn.md](turn.md)) is frozen and ported to the game. Until
then the C64, the cartridge and the modern front end keep v0's command bar, **Move Aim
Guard Wait Flee Quick Done** ([combat.md](combat.md)), and nothing here is built.*

Rules v1 gives a turn about twice as many choices as v0: Shove, Dash, up to four powers
(one of them, Blink, a move), the pack. The arena shows them all as buttons
([arena.md](arena.md#the-native-arena)); the C64's fight has one command row of 40
columns ([frames.md](frames.md)). This page is how they fit: a short row of verbs, the
rest in lists, and only what the rules allow from where you stand.

## The screen

As [frames.md](frames.md) has it, unchanged: the map in the view (rows 0-15), the story
log (rows 16-23, columns 0-24), the party (16-19, columns 26-39), the dice log (20-23,
columns 26-39), and the command row (24). A list, or a fighter's card, opens **in the
story log's place** (8 lines of 25 columns) and closes back to the log; the log loses
nothing, as it's redrawn.

## The command row

Six verbs, at most 40 columns:

```
 Move  Attack  Power  Other  Quick  Done
```

| Verb | Key | What it does |
|---|---|---|
| **Move** | M, or the arrows | walk the cursor over the squares lit this turn; fire or RETURN sets it (as v0's Move) |
| **Attack** | A | cycle the foes in reach from the square set, each with its TN (v0's Aim); fire strikes |
| **Power** | P, or 1-4 straight to one | the list of powers (below) |
| **Other** | O | the list of the rarer actions (below) |
| **Quick** | Q | the computer plays the turn ([turn.md](turn.md#how-the-computer-uses-powers)); T takes over again |
| **Done** | RETURN | end the turn where you stand |

A verb with nothing to offer is drawn dim and skipped by the joystick: Attack with nobody
in reach, Power with no charges left and no power at will. Its key says why in the story
log ("Nobody in reach from here."), as the arena's buttons do.

## The lists

A list is numbered, a line each, with what it costs or what it needs; up and down (or
the number) picks, fire or RETURN takes, the left arrow or DEL goes back. Only what the
rules allow from the square set is in it.

**Power** (P):

```
 1 Bull rush       2/2
 2 Ground slam     1/1
 3 Shield wall     2/2
 4 Second wind     1/1
```

Charges as left/full; `--` for at will. Then, as the power's target says: one target goes
off at once; several, aim as Attack does (with the TN); a square (a burst, a field), the
cursor over the squares it can reach, the blast or the line drawn under it. **Blink** is
listed as `(move)` and only before you've walked: its square becomes the turn's move, and
the row comes back to choose the action from there ([turn.md](turn.md#powers-in-play)).

**Other** (O):

```
 S Shove     G Guard
 D Dash      W Wait
 F Flee      K Pack
```

Shove (a foe next to the square set, with the TN), Dash (the cursor again, a second
move), Guard, Wait (only before moving, once a round), Flee (with its TN, or the exit),
Pack (below). Each also has its key straight from the row, so S, D, G, W, F and K never
need the list.

## The pack

K opens the pack in the story log's place: what's in your hands and on your body, then
the pack's items, numbered. A number holds or wears it; swapping is free
([items.md](items.md#swapping)), so the turn goes on after.

## Looking

V, then the cursor over a fighter: its card in the story log's place, while V is held or
until a key.

```
 Rust-guard 1      20/20
 Attack 45  Armor 20
 Ward 10    Dodge 4
 Soak 2     Speed 4
 6 kinetic, melee
 weak to energy
 HEX SLOW
```

Conditions are their tags from `registry/conditions.txt` (3-4 letters), as on the map; a
traveler's card ends with its powers and charges. The party frame keeps each traveler's
health, and a tag for the worst condition on them.

## Keys and the joystick

The same keys as the arena's, so playtesters learn the game's controls there: A, S, D,
G, W, F, Q, 1-4, RETURN for End turn; the arena's P (Pack) is K here, since P opens
Power (the arena should follow when it's brought in line). The joystick alone plays a
whole fight: left and right along the row, fire to choose, up and down in a list, the
cursor in the eight directions, and pulling back past the top of a list (or a second fire
on an empty square) to go back.

## What's checked, when it's built

`make test-cart` drives fights from `tests/cart/*.choices`, keys and `joy` lines, as it
drives v0's today: each list's lines, what's dimmed and why, a Blink then a shot, a
power's square picked by the cursor, the pack mid-turn, and the transcript the same as
the C64 version's. The arena's button bar is to be grouped the same way (Power and Other
as lists) before then, so the playtests try the menus as well as the rules.

## Open

- Whether a party's turn (up to four travelers) wants a key to look at the next traveler's
  options without ending this one's.
- Whether the dice log should show a power's area (Area 1) and rider, or the card does.
- Room: the menus are small beside rules v1 itself, which is near the 6502 test harness's
  62 KB already; the port splits the battle across the cartridge's 8 KB assets as v0's is
  ([cartridge.md](cartridge.md)), and is planned before the freeze.
