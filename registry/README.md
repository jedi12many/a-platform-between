# The registry

Everything the game refers to by number lives here, in plain text: races, classes,
skills, items and Echoes. These files are the single source of truth. The C engine's
tables, the Passport tools and the Quest Script compiler are all generated from or read
straight from them, so they can never disagree.

| File | What |
|---|---|
| `races.txt` | Playable races and the stat each one raises |
| `classes.txt` | Classes, the stat each one raises, and the two skills it tags |
| `skills.txt` | Skills and the stat that governs each |
| `items.txt` | Every item: archetype, tier, damage type, native Tech and Magic Levels |
| `echoes.txt` | Every Echo: kind, the Departure that plants it, its states and canon default |
| `foes.txt` | The bestiary: every foe a battle map can hold, with its numbers ([combat.md](../docs/combat.md)) |

Foes are read by the Quest Script compiler and the Python tools, not the C engine: an
image carries a copy of each foe's numbers, so a later change here never changes a
Departure that has shipped. The bestiary is the easiest place to contribute: one line per
foe, in the same 100-point scale as everything else.

## Editing

1. Edit the text file. One entry per line; `#` starts a comment; names shown to players go
   in quotes.
2. Run `make registry` to regenerate the C code.
3. Run the checks (`make test`, `make test-6502`, `make test-python`, ...).

Mistakes are reported with the file and line, for example:

```
registry/items.txt line 9: archetype 'blaster' isn't one of: melee, ranged, armor, tool, focus, vehicle
```

## Append only

Passports in the wild store these ids, so once an entry has shipped:

- never change its id, or reuse a retired one;
- never reorder an Echo's states (new states may be added at the end, up to 3);
- add new entries at the end, with higher ids.

Races, classes and skills must have consecutive ids from 0. Items and Echoes may skip ids.

## Limits

Set by the Passport format: at most 32 races, 16 classes and 12 skills; item and Echo ids
1–1023; 3 states per Echo. Foe ids are 1–1023.
