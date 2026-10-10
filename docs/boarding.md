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
| Echoes set | Echo id, new state, and its state at boarding |

A Rewind's receipt looks like any other: the Waystation knows the ticket was a Rewind, and
when it lands, the Echoes that Departure plants are cleared from the character before the
receipt's are set (so a choice the replay never made goes back to its canon default).

A receipt is **net**: an item given and taken back in the same trip appears in neither
list, so the lists never overlap.

## Applying a receipt

Receipts are applied to the character **as they are now**, not as they boarded. Lost
items go before gained ones, so they make room in the pack. `apb_receipt_apply` in the
rules core does this, and `tools/passport/receipt.py` is its reference, checked against it
by `make test-receipts`.

| Field | Rule |
|---|---|
| XP | Added. Level-ups happen now, and their stat and skill points are spent at the Waystation. |
| Debt | Added, kept within 0..65535. |
| On a Rewind | First the Departure's own Echoes are cleared; XP and Debt paid down are halved; the 500 Debt fee is added. |
| Items gained | Into the pack; if it's full, the Waystation's lost-and-found keeps them. |
| Items lost | Removed if still carried (the pack first, then what's equipped); if already gone (sold, traded), nothing happens. |
| Echoes | Set to the receipt's state. If the Echo was changed elsewhere since boarding (it's now neither its state at boarding nor the receipt's), the receipt still wins and the character is told the timeline shifted. A full Passport pushes its oldest Echo to the Legend. |

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
   issues a **Boarding Pass**: the trip (the Departure, a one-time ticket number, the dice
   seed for the trip) and the character as they are now, in one password.
2. **Give the client the Boarding Pass.** It's the only code a player types to board: on
   a C64, line by line like a Passport (from your phone screen); a modern client fetches
   it when you sign in. The client checks the pass is for this Departure, and boards the
   character it carries.
3. **The receipt carries the ticket number.** The server accepts it only for the character
   the ticket was issued to, only once, and only within that Departure's possible rewards.

The server's secret is the ticket itself: a random 32-bit number it draws and remembers,
with the character and Departure it was issued for. A forged or borrowed receipt would
have to guess a live ticket issued to that very character. That protects receipts the way
a signature would, with nothing secret in the client.

A pass carries the character as they were when it was issued, and a receipt is a list of
changes, not a snapshot. So a pass kept back and played after another trip has landed is
no different from two trips taken at once: both receipts land, each on the character as
it is by then.

A player can still board with just their Passport, at the same prompt: the desk says so,
and that nothing earned on the trip can be stamped. (Tests do that, and so does the
browser until the website issues passes, W2.)

### Boarding Pass format

Format 2 (format 1, a short pass typed beside the Passport, is retired). The Passport
alphabet, lines and line check ([passport-spec.md](passport-spec.md)): the bits below,
zero bits to a whole byte, a CRC-16 over every byte (as the Passport's), and zero bits to
a whole symbol. Kestrel's pass for *The Fare* is 67 symbols, in four lines.

| Field | Bits | Notes |
|---|---|---|
| kind | 4 | 8: a Boarding Pass. A Passport's first four bits are its version (2), so a client can tell which it was given from the first symbol, and take either at one prompt |
| Departure | 16 | the image's id |
| ticket | 32 | random, drawn by the server |
| seed | 16 | the dice for this trip, so the server can replay an online trip and a player can't re-roll by boarding again |
| Rewind | 1 | 1: a replay of a Departure the character has played ([seasons.md](seasons.md)); the train forgets that Departure's Echoes before play |
| character | | the Passport's fields, exactly as in a Passport, from its version on |

`apb_pass_encode` / `apb_pass_decode` and `apb_password_kind` in the rules core;
`tools/passport/boarding.py` is the reference, written from this page, and issues passes
for testing until the website does. The server keeps each ticket's character as boarded
(`apb_passport_check` names that version of them).

### Reward manifests

The compiler writes, for each Departure, the most it can ever give: the XP awarded on any
route, the items it can give, the Echo states it can set, the most Debt it can pay down
or add, and the values it can set Debt to (`qsc.py build FILE.qs --manifest FILE.json`,
`tools/qsc/manifest.py`). The server refuses a receipt that claims more.

The bound is exact because each `~ xp`, `~ give` and `~ debt` pays at most once per trip
(the VM keeps track), so the most a Departure can give is what its commands add up to.
`make test-vm` checks every playthrough's receipt against its manifest.

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

### Travel Stamp format

Version 1. A receipt in the Passport alphabet, in lines of 19 symbols plus a check symbol
(the last line may be shorter), ending in a CRC-16 like a Passport. *The Fare*'s is 26
symbols; the longest possible is 84.

| Field | Bits | Notes |
|---|---|---|
| version | 4 | 1 |
| Departure | 16 | |
| ticket | 32 | from the Boarding Pass |
| outcome | 1 | 0 complete, 1 failed |
| XP | 16 | |
| Debt | 1 + 16 | 1: added, 0: paid; then the amount |
| items gained | 4 + 10 each | a count, then item ids |
| items lost | 4 + 10 each | |
| Echoes | 4 + 14 each | a count, then id (10), state (2), state at boarding (2) |
| padding | to a byte | zero |
| CRC-16 | 16 | CCITT-FALSE over the bytes so far, as in the Passport |

`apb_stamp_encode` in the rules core (clients only ever write stamps);
`tools/passport/stamp.py` decodes them for the website and names the line of a typo.

### Landing a stamp

`tools/waystation/station.py` is a prototype of what the website does with one: find its
ticket in the ledger (refused if never issued, issued to another character, or already
used), check it against the Departure's reward manifest and the character as they boarded,
then apply it to the character as they are now. `make test-term` runs the whole round trip
through the terminal.

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
