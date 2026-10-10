# The Waystation on the web

The Waystation is where travelers live between trains, so that's what the website is:
the station. The game clients (PC, C64, Amiga, tabletop, ...) are the trains. You build and
look after your character at the station, then board a train with your Passport, play a
Departure, and come back with a receipt.

## What happens where

| At the Waystation (browser) | On a train (a client) |
|---|---|
| Build a character (its first trip is the Arrivals, [lines.md](lines.md)) | Enter a Passport (type it, scan it, or sign in) |
| Spend stat and skill points from levelling up | Play Departures |
| Buy seasons and Departures | Hand back a receipt (or a Travel Stamp) |
| Download clients, and disk images for retro machines | |
| Shop, trade, the lost-and-found | |
| Meet other travelers, form parties for co-op | |
| Print tabletop character sheets | |
| Apply receipts and Travel Stamps to your character | |

This is the rule we already had ("stat and skill points are spent only at the
Waystation", [boarding.md](boarding.md)), made literal.

## One rules core everywhere

The rules core (`core/`) and the Story VM (`vm/`) compile to WebAssembly, so the website
checks characters and applies receipts with exactly the code a C64 runs. The Waystation's
own story moments (the Stationmaster, Fen at the Buffer Stop, the departure board) are
written in Quest Script and played by the same VM in the browser.

## Receipts the server can trust

Every trip starts with a **Boarding Pass** from the website, carrying a random ticket
number only the server knows it issued, and every receipt has to match one: right character, used once, within the
Departure's possible rewards. Online clients also send the choices and dice seed, and the
server replays the Departure with the same VM to confirm the result. See *Boarding
passes* in [boarding.md](boarding.md).

## Retro machines

The website builds a disk image (`.d64` for the C64, and so on) holding the client and the
Departures you own, to load in an emulator or onto real hardware through an SD-card
drive. Characters travel by Passport password or Travel Stamp, as before.

## The website is required

Every player uses the Waystation website, including C64 players: they'll have a phone or
another computer nearby. That keeps the clients simple. A client only needs to take a
Boarding Pass (which carries the Passport), play, and hand back a receipt; character creation, levelling
up and everything else happens at the station.

A modern client can still play a Departure without a connection once boarded; its receipt
waits until it can reach the Waystation.

## Build order

| Step | What | Needs a server? |
|---|---|---|
| **W1** | A static site: the character creator, Passport decoding and editing (spending points), the tabletop sheet printer. The rules core runs in the browser as WebAssembly. (Travel Stamps are applied without a server only on trust; Boarding Passes need W2, which remembers the tickets it issued.) | No |
| **W2** | Accounts, Boarding Passes, a store for seasons and Departures, downloads and disk images, receipts from modern clients and Travel Stamps from retro ones, replay verification | Yes |
| **W3** | Trading, the lost-and-found, meeting travelers, parties and co-op lobbies | Yes |

W1 can come early: it needs only what already exists, plus a WebAssembly build. W2 and
W3 are the online Waystation (roadmap phase 4).

## W1: what's built

`make waystation` builds `build/waystation/`, a static site with no server. Serve it
(`python3 -m http.server -d build/waystation`) and open it. It has four pages:

- **Make a traveler:** name, race, class, a third tagged skill, and stats bought or
  rolled (one set and three re-rolls; the last set stands, and the numbers go where
  you like). A preview shows the result, then it issues the Passport.
- **Your Passport:** type or paste one in. Spend the points from levelling up
  (+1 to a stat; +1 training to a skill, +2 if tagged, at the skill's cost), and take
  the new Passport with you.
- **Tabletop sheet:** every number a table needs, ready to print.
- **Travel Stamp:** land a stamp on the Passport: XP and levels, Debt, items (to the
  lost-and-found if the pack is full) and Echoes, or a Rewind. There's no ticket
  ledger yet, so stamps are taken on trust. W2 checks them.

**How it works**

- **Rules:** every rule is the rules core's own. `waystation/ws.c` puts it on a small
  JSON interface, compiled to WebAssembly with Emscripten. The core gained what the
  site needed, a Travel Stamp decoder (`apb_stamp_decode`), tested against
  `tools/passport/stamp.py` on PC and 6502.
- **Names:** these come from the registry (`waystation/registry_json.py`).
- **Pages:** `waystation/site/`; the platform page around it, `site/`.

`make test-waystation` (`tests/waystation/check_site.py`) plays the site in headless
Chromium and checks it against the Python references, which were written from the docs
rather than from the C:

- a traveler made in the browser has the reference's Passport, and boards The Fare in
  the terminal with a Boarding Pass;
- the Travel Stamp the trip ends with lands in the browser as the reference lands it,
  and so does the same stamp as a Rewind;
- points spent and stats rolled follow the rules;
- typos are refused, naming the line.

## Your travelers

A player keeps their travelers: each one's Passport, with a note of their own ("off to
Dock 3"), so nobody has to copy twenty-letter lines around.

- **Making a traveler** at the Waystation: *Save to your travelers*, with a note, on
  *Your Passport*. Spending points there changes the Passport; *Save the new Passport*
  keeps it.
- **Landing a Travel Stamp:** *Whose Passport* lists them; choose one and their Passport is
  read (and a stamp waiting with them is filled in). The stamped Passport replaces theirs,
  and the old one is kept (the last five), in case a stamp was landed by mistake.
- **Boarding a train** in the browser: under the screen, *Your travelers* and *Type their
  Passport* types it in, a line at a time, when the desk asks for it. A trip that ends in
  a Travel Stamp keeps the stamp with that traveler, to land at the Waystation.
- **The platform page** (`site/index.html`) lists them: notes to edit, Passports to copy,
  a mark on anyone with a stamp to land, and *Remove*.

**Signing in.** The site is the platform page with the Waystation and the train in a frame
under it (`make site`, `build/site/`). Published on claude.ai, the platform page is signed
in as whoever opens it, and keeps their travelers in its private store, in their own place
(`data/users/<their id>/<traveler>`, which nobody else, the page's owner included, can
read). It asks claude.ai for that (the page's `user` and `db` capabilities); the Waystation
and the train ask the platform page (`waystation/site/travelers.js`, by message). A player
needs to be one the page is shared with, as a Contributor or above, to save. Anywhere else
(signed out, or the pages served on their own) the travelers are kept in this browser
instead, and the first time a player signs in, the ones kept in the browser move to
their account.

`make test-waystation` checks it too: a traveler saved with a note is kept over a reload,
chosen to land a stamp, and replaced by the stamped Passport; and on the site, signed in
(claude.ai's store stood in for in the browser), a traveler saved in the Waystation's frame
is kept in the player's own place, shown on the platform, and boards the train from the
list.

## Open questions

- How DLC ownership reaches retro disk images (proposal: the website builds personalised
  images; there's no copy protection on a C64, and we won't pretend otherwise).
