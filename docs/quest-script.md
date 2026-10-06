# Quest Script reference (v0)

Quest Script is the language Departures are written in, both ours and the community's
Branch Lines. It is plain text, and it's meant to read like a story with a few marks in
the margin.

> **Status:** v0 draft (milestone E0). Nothing is final until the compiler exists (E1).
> Features marked *(official only)* are refused in Branch Lines.

## A whole Departure, small

```
title: The Lantern Test
id: 900
kind: branch
realm: tl 3, ml 9
levels: 1-3
start: gate

flag paid_toll
var lanterns = 0

=== The Gate

== gate
An iron gate, and a moth-winged guard with a lantern for a head.

+ [Pay the toll]
    ~ set paid_toll
    The guard bows. Its light dims politely.
+ {paid_toll} [Go through] -> courtyard
+ [Leave] -> leave

== courtyard
Lanterns everywhere. One of them is looking at you.
~ add lanterns 1
+ [Wave] -> courtyard
+ [Go back] -> gate

== leave
You walk away. Somewhere, a lantern goes out.
~ end complete
```

## Files and layout

A Departure is one or more `.qs` files (UTF-8 text). The **header** comes first, then
**declarations**, then **chapters** and **scenes**.

- `//` starts a comment, to the end of the line.
- Indentation is how blocks are grouped (choices, `if`, `check`). Use 4 spaces. Tabs are
  an error, because they look the same as spaces but aren't.
- Names (scenes, flags, variables) are `lower_case_with_underscores`. Game words (stats,
  races, items, Echoes) are `UPPER_CASE`.
- Keywords (`if`, `else`, `check`, `flag`, `var`, ...) are lower case, so prose that
  starts with "If" or "Check" is just prose.
- Blank lines inside an indented block don't end it; the block ends at the first line
  that is indented less.

## The header

`key: value` lines at the top of the file.

| Key | Required | Meaning |
|---|---|---|
| `title` | yes | Shown on the departure board. |
| `id` | yes | A number. Official Departures use 0–899; Branch Lines get theirs from the Workshop. |
| `kind` | yes | `official` or `branch`. |
| `season` | official only | Which season this belongs to. |
| `realm` | yes | `tl N, ml N`: the realm's Tech and Magic Levels, 0–9. Drives Translation. |
| `levels` | yes | The level band, for example `2-5`. |
| `start` | yes | The scene the Departure begins in. |

## Declarations

Every flag and variable is declared before it's used. That way a typo is an error, not a
silent bug.

```
flag met_fen                 // true or false, starts false
var loops = 0                // a whole number, 0..255, with a starting value
```

A Departure can have up to 512 flags and 128 variables.

## Chapters and scenes

```
=== The Static               // a chapter: a title, shown when it starts
== bench                     // a scene: a name you can jump to
```

- A **scene** is a place or a moment. When the player arrives, its text is shown, its
  commands run, and then its **choices** are offered as a numbered menu.
- A **chapter** groups scenes. On small machines a chapter is loaded from disk as one
  piece (a "car"), so the compiler will tell you if a chapter gets too big.
- Scene names must be unique in the whole Departure. You can jump to any scene from any
  chapter; the engine loads chapters as needed.

## Text

Lines of plain text are what the player reads.

- Consecutive lines join into one paragraph. A blank line starts a new paragraph.
- The engine wraps text to the screen, so break your source lines wherever you like.
- Text is ASCII. Curly quotes, apostrophes, `—` and `…` are converted for you
  (`"`, `'`, `--`, `...`). Other characters are an error, because the old machines can't
  show them.
- A line can't *start* with `*`, `+`, `~`, `->`, `==`, `if`, `else`, `check` or a
  `{`; those mean something. Start the line with `\` to print it as text anyway.

### Inserting values

| Write | You get |
|---|---|
| `{name}` | The character's name |
| `{race}` | Their race, e.g. *Salvaged* |
| `{class}` | Their class, e.g. *Warden* |
| `{debt}` | Their Debt |
| `{level}` | Their level |
| `{loops}` | The value of a variable you declared |

## Choices

```
+ [Head for the bridge] -> bridge
* [Search the dead technician]
    You find a keycard.
    ~ give KEYCARD
```

- `+` is a choice that stays on the menu. `*` disappears once it has been picked.
- The label goes in `[ ]`. Keep it under 37 characters so it fits a C64 line.
- `-> scene` after the label goes straight there.
- Otherwise, the indented lines under the choice run, and then **the scene's menu comes
  back** (without repeating the scene's text). End the block with `-> scene` to go
  somewhere else instead.
- A menu holds at most 9 choices, so every choice has a single-key number.
- A condition in `{ }` before the label hides the choice unless it's true:

```
+ {has KEYCARD} [Open the locker] -> locker
* {echo WOLF_PUP = SWORN} [Whistle for the wolf] -> wolf_arrives
```

Every scene must give the player a way forward: at least one choice, a `->`, or an
`~ end`. The compiler reports scenes that would trap the player.

## Going places

```
-> bridge            // go to a scene (shows its text again, even if it's this one)
```

## Conditions

Used in `{ }` on choices and after `if`.

| Condition | True when |
|---|---|
| `met_fen` | the flag is set |
| `loops >= 3` | comparing a variable: `=` `!=` `<` `<=` `>` `>=` |
| `has KEYCARD` | the character is carrying the item |
| `echo WOLF_PUP = SAVED` | that Echo is in that state (`!=` works too) |
| `MIGHT >= 5` | comparing a stat: `MIGHT` `GRACE` `GRIT` `WITS` `PRESENCE` `FATE` |
| `level >= 3` | comparing the character's level |
| `race SALVAGED` | the character is that race |
| `class WARDEN` | the character is that class |
| `visited bar` | the player has been to that scene before |

Combine them with `and`, `or`, `not` and parentheses:
`{has KEYCARD and not alarm}`.

**Echoes you haven't earned.** If the character never played the Departure that plants
an Echo (a skipped season, say), `echo` uses that Echo's *canon default* from the
registry, so your condition always gets a sensible answer.

**`visited` in a scene's own text** is false the first time through, so this works:

```
== bar
if not visited bar
    You've never seen a bar like it.
else
    The bar. Fen nods.
```

## If

```
if class WARDEN
    You were holding the line when it happened.
else if class ROGUE
    You were running, with something that wasn't yours.
else
    You were busy. Death didn't care.
```

`if` blocks can hold text, commands, choices' worth of logic, `->` and other `if`s.

## Checks

A check rolls 2d6 + a stat (+ a bonus, − a difficulty) using the game's rules, then runs
the branch for the result:

```
check WITS + 1 vs 2
    crit:    You find a keycard and the override code.
             ~ give KEYCARD ~ set knows_code
    success: You find a keycard. ~ give KEYCARD
    cost:    You find a keycard, but the alarm sees you.
             ~ give KEYCARD ~ set alarm
    fail:    Nothing. The voice says: "Seventeen minutes."
```

| Result | Total |
|---|---|
| `crit` | 12 or more |
| `success` | 9–11 |
| `cost` | 6–8: it works, but at a price |
| `fail` | 5 or less |

- `+ N` and `vs N` are optional.
- A branch can be on the same line after the colon, or indented below it.
- Leave a branch out and nothing happens for that result, except that a missing `crit`
  uses your `success` branch.

## Commands

Commands start with `~`. Several can share a line: `~ give KEYCARD ~ set alarm`.

### Story memory

| Command | Does |
|---|---|
| `~ set alarm` / `~ clear alarm` | set or clear a flag |
| `~ let loops = 3` | set a variable |
| `~ add loops 1` / `~ sub loops 1` | add or subtract (stops at 0 and 255) |
| `~ echo WOLF_PUP = SAVED` | plant or change an Echo *(official only)* |

### The character

| Command | Does |
|---|---|
| `~ give KEYCARD` / `~ take KEYCARD` | add or remove an item |
| `~ xp 10` | award experience |
| `~ debt - 500` / `~ debt + 500` / `~ debt = 50000` | change Debt *(official only)* |
| `~ race SALVAGED` / `~ class WARDEN` | set race or class *(official only)* |
| `~ stat MIGHT + 1` / `~ stat MIGHT = 5` | change a stat *(official only)* |
| `~ ask_name` | ask the player to type a name *(official only)* |

### Presentation

| Command | Does |
|---|---|
| `~ picture platform_bench` | show a picture (ignored where there's no picture) |
| `~ pause` | wait for a key before continuing |

### Ending

| Command | Does |
|---|---|
| `~ end complete` | the Departure succeeded: rewards are kept |
| `~ end failed` | the Departure failed: the character returns to the Waystation |

## Branch Lines: what's different

Community Departures (`kind: branch`) use the same language, with these limits so they
can't damage anyone's character or the main story:

- No `~ echo`, `~ debt`, `~ race`, `~ class`, `~ stat` or `~ ask_name`.
- `echo` *conditions* are allowed: your Branch Line can react to a player's choices in the
  main story; it just can't change them.
- `~ give` only works for items of tier 3 or lower, a limited number per Departure.
- `~ xp` stops counting once the character is above your `levels` band.
- Your flags and variables are kept in the player's **Branch Line ledger** when the
  Departure ends. (Reading them back from a sequel is planned, not in v0.)

## Limits (v0)

| Thing | Limit | Why |
|---|---|---|
| Choices per menu | 9 | one key each |
| Choice label | 37 characters | fits a C64 line |
| Flags / variables | 512 / 128 | memory on the C64 |
| Chapter size (compiled) | 16 KB | one chapter in C64 memory at a time |
| Scenes per Departure | 1024 | |

The compiler tells you when you hit one, and where.

## Not in v0

Planned, not yet designed: fights (`fight`, milestone E3), random tables, reusable
"tunnel" scenes that return to where they were called from, and text styles.
