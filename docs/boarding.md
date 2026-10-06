# Boarding and receipts

A character can be in more than one game at once: a slow co-op Departure that runs for
weeks, a solo Departure in the evening, a session at the table. None of them may cost the
character progress made in another. So a Departure never hands back a whole new
character. It hands back a **receipt**: only what changed.

## Boarding: play the character as they boarded

When a character boards a Departure, the Departure takes a **snapshot** and plays that
version for its whole length. A co-op party stays fair (nobody's character jumps ten
levels mid-campaign because they played solo in between), and a Departure's level band
means what it says.

In the fiction: the Waystation stands outside time, so riding two trains at once is
simply how travelers work. The snapshot is "the version of you that boarded that train".

## The receipt

What a Departure hands back when it ends:

| Field | Notes |
|---|---|
| Departure id, outcome | complete or failed |
| Boarding checksum | of the snapshot, so a receipt can be matched to its boarding |
| XP gained | already faded for the level band, as of boarding |
| Debt change | signed: paid down, or added (a failed Departure, a death) |
| Items gained | |
| Items lost | taken, used up, or given away in the story |
| Echoes set | Echo id and new state |
| Echoes cleared | by a Rewind |

## Applying a receipt

Receipts are applied to the character **as they are now**, not as they boarded:

| Field | Rule |
|---|---|
| XP | Added. Level-ups happen now, and their stat and skill points are spent at the Waystation. |
| Debt | Added, kept within 0..65535. |
| Items gained | Into the pack; if it's full, the Waystation's lost-and-found keeps them. |
| Items lost | Removed if still carried; if already gone (sold, traded), nothing happens. |
| Echoes | Set to the receipt's state. If the Echo was changed elsewhere since boarding, the receipt still wins and the character is told the timeline shifted. |

Nothing else changes in a Departure. Stat and skill points are spent only at the
Waystation, and name, race and class only change in the character creator, so they can
never clash.

### The one clash

The same Echo changed in two games at once: a solo Rewind of Departure 02 while a co-op
game also plays Departure 02. The receipt applied last wins, and the Waystation's
regulars notice ("Didn't you leave that pup? I could swear..."). It's a story beat, not lost
data.

## Carriers

| Where | How the receipt travels |
|---|---|
| Modern, online | Sent to the web Waystation as soon as the Departure ends, with the choices and seed that produced it, so the server can replay and verify it; each receipt applies once. |
| Modern, offline | Applied to the saved character on that machine. |
| Retro | A **Travel Stamp**: a short password holding only the receipt (about 20–30 characters for a typical Departure, versus 55+ for a Passport). Enter it into whatever your Passport is now, on any platform. |
| Tabletop | The Conductor writes out the receipt; the Passport Office turns it into a Travel Stamp, flagged tabletop. |

Applying the same stamp twice can only be prevented online. Offline we accept it, the
same way we accept cheating in single-player: it's your character.

## Engine notes

- The VM plays a working copy of the boarding snapshot, and records every change it makes
  into the receipt as it goes (`GIVE`, `TAKE`, `XP`, `DEBT`, `ECHO_SET`). At `END` it hands
  the receipt to the front end. It never writes a Passport itself.
- Applying receipts is rules-core code (`core/`), so every platform, the hub and the
  Passport Office merge the same way.
- The Travel Stamp format is specified with milestone E2, alongside the Passport.
