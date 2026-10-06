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
Passport and a Boarding Pass, play, and hand back a receipt; character creation, levelling
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

## Open questions

- How DLC ownership reaches retro disk images (proposal: the website builds personalised
  images; there's no copy protection on a C64, and we won't pretend otherwise).
