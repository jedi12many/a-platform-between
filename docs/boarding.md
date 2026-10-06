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

## Boarding passes

Receipts must only count for the character that earned them, once. The keys that make
that true live on the server, never in a client: anyone can read a C64 disk, and a key a
player holds is a key a player can share.

1. **Board at the Waystation website.** Pick the character and the Departure; the server
   issues a **Boarding Pass**: a short code (about 16-20 characters) holding the
   character, the Departure, a one-time ticket number and a hash of the character as
   boarded, signed with a key only the server has.
2. **Give the client your Passport and the Boarding Pass.** On a C64 you type both (from
   your phone screen); a modern client fetches them when you sign in.
3. **The receipt carries the ticket number.** The server accepts it only for the character
   the ticket was issued to, only once, and only within that Departure's possible rewards.

### Reward manifests

The compiler writes, for each Departure, the most it can ever give: the XP awarded on any
route, the items it can give, the Echo states it can set, the most Debt it can pay down.
The server refuses a receipt that claims more.

### What's protected

| Threat | Modern client, online | C64 and tabletop |
|---|---|---|
| Sharing a receipt with another player | Blocked: tied to the ticket and character | Blocked, the same way |
| Applying a receipt twice | Blocked: one use per ticket | Blocked, the same way |
| Claiming rewards the Departure can't give | Blocked: reward manifest | Blocked, the same way |
| Claiming an outcome the Departure *could* give, without earning it | Blocked: the receipt comes with its choices and dice seed, and the server replays it | Possible: a C64 can't keep a secret |

The last row is the honest limit. A determined cheater on a C64 can claim the best ending
of a Departure they boarded, which they could have earned by replaying it anyway. Things
that matter more (leaderboards, trading rare items, organized play) count only verified
receipts.

## Carriers

| Where | How the receipt travels |
|---|---|
| Modern client | Sent to the Waystation as soon as the Departure ends, with the choices and seed that produced it, so the server can replay and verify it. |
| Retro | A **Travel Stamp**: a short password holding the ticket number and the receipt (about 25-35 characters for a typical Departure), with a check code against typos. Enter it at the Waystation website. |
| Tabletop | The Conductor's receipt, entered at the Waystation; Boarding Passes are issued for tabletop sessions too. |

## Engine notes

- The VM plays a working copy of the boarding snapshot, and records every change it makes
  into the receipt as it goes (`GIVE`, `TAKE`, `XP`, `DEBT`, `ECHO_SET`). At `END` it hands
  the receipt to the front end. It never writes a Passport itself.
- Applying receipts is rules-core code (`core/`), so every platform, the hub and the
  Passport Office merge the same way.
- The VM takes the Boarding Pass alongside the Passport and copies its ticket number into
  the receipt.
- The Travel Stamp and Boarding Pass formats are specified with milestone E2, alongside
  the Passport; the reward manifest with the compiler.
