# The Waystation on the web

The Waystation is where travelers live between trains, so that's what the website is:
the station. The game clients (PC, C64, Amiga, tabletop, ...) are the trains. You build and
look after your character at the station, then board a train with your Passport, play a
Departure, and come back with a receipt.

## What happens where

| At the Waystation (browser) | On a train (a client) |
|---|---|
| Build a character | Enter a Passport (type it, scan it, or sign in) |
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

The VM is deterministic and its only input is a list of choices. So an online client can
send its receipt **with the choices and the dice seed that produced it**, and the server
replays the Departure with the same VM to confirm the receipt. That gives verified
characters for co-op, trading and leaderboards without trusting the client. Travel
Stamps from retro machines and the tabletop stay *unverified* unless stamped at an
organized-play event ([tabletop.md](tabletop.md)).

## Retro machines

The website builds a disk image (`.d64` for the C64, and so on) holding the client and the
Departures you own, to load in an emulator or onto real hardware through an SD-card
drive. Characters travel by Passport password or Travel Stamp, as before.

## Offline still works

Some players will never open a browser, and a C64 has no network by default. Every
client keeps a small offline path:

- enter a Passport password;
- a plain character creator, for starting with no website at all;
- Travel Stamps on the way out, to apply later (at the website, or in another client).

The website is the front door, not the only door.

## Build order

| Step | What | Needs a server? |
|---|---|---|
| **W1** | A static site: the character creator, Passport decoding and editing (spending points), the tabletop sheet printer, applying Travel Stamps. The rules core runs in the browser as WebAssembly. | No |
| **W2** | Accounts, a store for seasons and Departures, downloads and disk images, receipt sync from modern clients, replay verification | Yes |
| **W3** | Trading, the lost-and-found, meeting travelers, parties and co-op lobbies | Yes |

W1 can come early: it needs only what already exists, plus a WebAssembly build. W2 and
W3 are the online Waystation (roadmap phase 4).

## Open questions

- Is a modern client (Steam) allowed to work fully offline, with the website optional?
  (Proposal: yes, with a local Waystation-lite for spending points.)
- How DLC ownership reaches retro disk images (proposal: the website builds personalised
  images; there's no copy protection on a C64, and we won't pretend otherwise).
