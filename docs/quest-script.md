# Quest Script reference (v0)

Quest Script is the language Departures are written in, both ours and the community's
Branch Lines. It is plain text, and it's meant to read like a story with a few marks in
the margin.

> **Status:** v0. Check a script with `python3 tools/qsc/qsc.py check FILE.qs`; compile it
> with `python3 tools/qsc/qsc.py build FILE.qs -o FILE.apd`.
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
- Indentation is how blocks are grouped (choices, `if`, `check`): a block is everything
  indented deeper than the line that opens it. 4 spaces is the habit; continuation lines
  under a `check` result can line up with its text. Tabs are an error, because they look
  the same as spaces but aren't.
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
| `linear` | no | `yes` if the Departure is deliberately one road (a prologue, say): turns off the "only one road to victory" warning. |

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
- **Fixed lines.** A line starting with `|` is printed on its own line, exactly as written
  (spaces included), instead of joining the paragraph. Use it for signs, departure boards,
  verse and lists. Keep `|` lines to 38 characters so they fit a 40-column screen.

```
The letters settle long enough to read:

| KEPLER-NINE    PLAT 1  DELAYED 18 MIN
| ASHMOUTH       PLAT 2  LAST TRAIN
```

- A line can't *start* with `*`, `+`, `~`, `->`, `==`, `|`, `if`, `else`, `check` or a
  `{`; those mean something. Start the line with `\` to print it as text anyway.
- Any text line can end with commands or a jump: `You find a keycard. ~ give KEYCARD`, or
  `You run. -> corridor`.

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

- Choices come last in a scene, after its text: they're its menu. A choice can't go
  inside an `if`; put the condition on the choice instead (`+ {met_fen} [...]`).
- `+` is a choice that stays on the menu. `*` disappears once it has been picked.
- The label goes in `[ ]`. Keep it to 37 characters so it fits a C64 line. Labels are
  plain text: `{name}` and friends aren't inserted there.
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
| `MIGHT >= 50` | comparing a stat (0–100) |
| `TECH >= 40` | comparing a skill's rating (0–100) |
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

A check rolls d100 + a stat or skill against a target number (TN), using the game's rules,
then runs the branch for the result:

```
check TECH tricky
    crit:    You find a keycard and the override code.
             ~ give KEYCARD ~ set knows_code
    success: You find a keycard. ~ give KEYCARD
    cost:    You find a keycard, but the alarm sees you.
             ~ give KEYCARD ~ set alarm
    fail:    Nothing. The voice says: "Seventeen minutes."
```

- Check any **stat** (`MIGHT` `GRACE` `GRIT` `WITS` `PRESENCE` `FATE`) or **skill**
  (`MELEE` `ATHLETICS` `RANGED` `STEALTH` `ENDURANCE` `SURVIVAL` `TECH` `MEDICINE` `LORE`
  `PERSUADE` `CHANNEL` `INTUITION`). Prefer skills; they're what players invest in.
- Set the TN with a word, or a number after `vs`:

| Write | TN |
|---|---|
| `easy` | 80 |
| `routine` | 90 |
| *(nothing)* or `normal` | 100 |
| `tricky` | 110 |
| `hard` | 120 |
| `very_hard` | 130 |
| `vs 145` | 145 |

  For example `check STEALTH hard`, or `check MIGHT vs 140` to force the golem's door.

| Result | Roll |
|---|---|
| `crit` | a natural 100, or doubles (11, 22 …) that beat the TN |
| `success` | d100 + rating beats the TN |
| `cost` | within 20 under the TN: it works, but at a price |
| `fail` | lower than that, or a natural 01 |

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

Stories never create or rebuild characters. Name, race, class and stats come from the
character creator, before the first Departure (see [rules-v0.md](rules-v0.md)). Stories
can *read* all of them, in conditions and with `{name}`, `{race}` and `{class}`.

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

## Writing roadblocks and many roads

Every Departure needs **more than one road to victory**, and is built for preparation,
not balance (see *Roadblocks and many roads* in [rules-v0.md](rules-v0.md)). Plan the
roads before the prose: for each chapter, list the ways through (fight, sneak, talk,
solve, go around) and make sure at least two reach the ending.

A roadblock can be an enemy, a puzzle, a locked way, a hazard or a gatekeeper. An enemy
roadblock looks like this:

```
== vault_door
The door is guarded by an iron golem. The floor in front of it is scattered with
dented armor, none of it recent, all of it empty.

* [Size it up]
    check LORE
        success: Iron through and through. Lightning would find every rivet.
                 ~ set knows_golem
        cost:    Iron. Heavy. You'd want something sharper than steel.
        fail:    It's big. That's all you can tell.
+ {has ADAMANT_OIL} [Oil your blade and fight] -> golem_fight
+ {CHANNEL >= 40 and knows_golem} [Call the lightning] -> golem_lightning
+ [Fight it anyway] -> golem_fight
+ [Find another way] -> service_tunnels
```

A puzzle roadblock lets the player solve it, the character solve it, or neither:

```
== orrery_lock
Seven brass planets on seven rails. The door opens when they align, and the
inscription says only: THE LAST SHALL LEAD THE FIRST.

+ [Turn the planets yourself] -> orrery_solve        // the player's answer
+ [Let your hands work it out]
    check TECH tricky
        success: The rails click home, one by one. ~ set orrery_open
        cost:    It opens, and the eighth planet you didn't see falls on your foot.
                 ~ set orrery_open
        fail:    The planets spin back to where they started.
+ {has STAR_CHART} [Follow the star chart] -> orrery_open_scene
+ {orrery_open} [Go through] -> observatory
+ [Take the stairs instead] -> bell_tower
```

Rules for every roadblock:

- **Telegraph it.** The player should be able to see it's dangerous before committing.
- **Offer a way to learn more**: a check that reveals defenses or weaknesses.
- **Show the answers the player has**, gated on items, skills, powers or flags, and let
  the rest stay hidden.
- **Always offer the other road.** The compiler will warn about a scene with a fight
  and no exit that avoids it.
- **Don't make the puzzle the only key.** A puzzle can always be passed by thinking, by a
  check, by an item, or by going around.
- **The other road must lead somewhere real**: another route to an ending, not a dead end.
- **Leave it standing.** A roadblock the player skipped is still there on a Rewind or a
  later visit.

### Compiler help

The compiler maps every route from the start to each `~ end complete` and warns when
every route to an ending passes through the same scene ("only one road to victory"), or
when no route reaches an ending at all. Mark a deliberately linear Departure with
`linear: yes` in the header.

Planned with encounters (E3): a warning when a fight has no way to leave without
passing it.

## Branch Lines: what's different

Community Departures (`kind: branch`) use the same language, with these limits so they
can't damage anyone's character or the main story:

- No `~ echo` or `~ debt`.
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

Planned, not yet designed: encounters (`fight`, milestone E3), which hand off to the battle
map and come back with a result, for example:

```
== mountain_path
The switchbacks narrow to a ledge. Snow, wind, and then the rocks start moving.
fight ROCK_TROLLS ambush            // starting positions: the party strung out
    won:  The last troll topples into the gorge. -> castle_gate
    fled: You scramble back down to the treeline. -> forest_road
    lost: -> waystation_return
```

Also planned: party voting options (vote, leader, personal choices), random tables, reusable
"tunnel" scenes that return to where they were called from, and text styles.
