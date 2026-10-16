# A Platform Between

Design docs live in `docs/`; the rules core lives in `core/`.

**The game is being rebuilt in 100% 6502 assembly** (`cart/`, `docs/cartridge.md`): a 1 MB
EasyFlash cartridge for a Kung Fu Flash, and the same game on a disk for an SD2IEC. The C
engine (`core/`, `vm/`, `fe/`) stays as the working reference, and the Python references
(`tools/`) and the Waystation website are the specification the assembly is tested
against. For `cart/`:

- ca65 only. One job per file; a routine's header says what it takes (registers, zero
  page), what it gives back, what must be true before, and what it changes (A, X, Y,
  zero page).
- The zero page is allocated in `cart/zp.inc` (and the table in `docs/cartridge.md`); a
  module uses only its own, or scratch between calls. Chips in `cart/hw.inc`, the memory
  map and the screen's layout in `cart/mem.inc`: no bare addresses in code.
- A branch whose target may drift out of reach is written as the opposite branch over a
  `jmp`.
- Only `cart/assets.s` (and the start-ups) knows the medium: no `$DE00`, `$DE02` or
  KERNAL call anywhere else. Everything but the resident engine is an 8 KB asset, fetched
  into the staging RAM at $8000; nothing runs from the cartridge.
- Saves are passwords (the Passport's alphabet and lines); no disk or flash writes.
- Timing that matters (the raster split) is counted in the code's comments, and `make
  test-cart` holds it to the cycle.

## Commands

- `make test`: native tests (gcc/clang, `-Werror`).
- `make test-6502`: the same tests on the sim65 6502 simulator. Needs cc65
  (`apt-get install cc65`).
- `make crosscheck`: the demo's native and 6502 output must be byte-identical.
- `make c64`: build `build/demo.prg` and the C64 disks, `build/the-fare.d64`,
  `build/eighteen-minutes.d64` and `build/deep-yards.d64` (`LOAD"APB",8` in VICE; see
  `docs/c64.md`).
- `make test-python`: the Python Passport reference (`tools/passport/`) must decode the
  C engine's password; trip codes (`tools/passport/trip.py`) must round-trip and refuse
  damage (`tests/passport/test_trip.py`); the registry and Quest Script parser tests must pass; and every
  picture in `content/` must come through the C64's rules unchanged
  (`tools/test_pictures.py`; needs Pillow and numpy).
- `make check-registry`: the generated C registry must match `registry/*.txt`.
- `make check-content`: every `.qs` file in `content/` must compile to an image the
  verifier accepts.
- `make test-vm`: Story VM playthroughs (`tests/vm/cases.txt`) must match their expected
  transcripts natively and on sim65, and damaged images must never crash the VM under
  AddressSanitizer/UBSan. After a deliberate change, `python3 tests/vm/run_tests.py
  --update` rewrites the expected transcripts: read the diff before committing it.
  Together, the playthroughs of *The Fare* must run every instruction in it, and so must
  those of *Eighteen Minutes* and *the Deep Yards* (`COVERED` in `run_tests.py`): a
  passage no case reaches fails the test, so a new route needs a new case. `@name` in a
  case boards a traveler from `tests/vm/travelers.txt`; every check is re-rolled from the
  rules and that traveler's Passport. Every receipt must fit its reward manifest. Each
  playthrough is also saved at every menu and resumed, and must come out the same.
- `make test-term`: the terminal front end's recorded playthrough must match
  `tests/term/fare-edge.expected`, with nothing over 40 columns; and the round trip
  (`tests/term/check_roundtrip.py`) must work: passes issued, trips played in the terminal,
  Travel Stamps landed on the Passport.
- `make test-receipts`: applying receipts (`core/src/receipt.c`) must agree with the
  Python reference (`tools/passport/receipt.py`) on hand-worked and random cases,
  natively and on sim65.
- `make test-combat`: the combat rules (`core/src/combat.c`, `docs/combat.md`) must agree
  with the Python reference (`tools/rules/combat.py`) on random attacks and character
  sheets, natively and on sim65; and the battle scenarios (`tests/battle/*.txt`, the engine
  in `core/src/battle.c`) must match their reviewed logs on both, with every roll
  re-checked, and random battles must never crash under the sanitizers.
  `python3 tests/battle/run_battles.py --update` rewrites the logs: read the diff. And the
  arena's fights (`tools/arena/`) must be the battle runner's, blow for blow, and its quick
  builder's characters must keep the rules (`tests/arena/check_arena.py`).
- `make test-c64`: the C64 program from the `.d64` must play The Fare, Eighteen Minutes
  and the Deep Yards on a 6502 emulator
  (py65: `pip install py65`; the disk's pictures need Pillow) with the KERNAL answered
  in Python (`tests/c64/run_c64.py`; the story log is read row by row, and rolls and a
  fight's prompts from `hal_scene_log`; in a fight, a key a line): transcripts match
  `tests/c64/*.expected`, the
  Travel Stamp is the terminal's, a save survives switching off, the C stack stays
  under 384 bytes; the music plays (the harness keeps the I/O apart from the RAM under it,
  and fires the raster interrupt), its cues in the transcripts as `[music NAME]`; and no
  overlay may use another's code or data
  (`fe/c64/check_overlays.py`). `--shots DIR` saves pictures of the screen to look at,
  the battle screen drawn as the VIC-II would (`tools/vic.py`).
- `make test-modern`: the modern front end (`fe/modern/`, `docs/modern.md`) must play the
  C64's test routes as the C64 does (`tests/modern/check_modern.py`), on the desktop
  (SDL2, `build/apb-modern`) and in a browser (`build/web/`, headless Chromium through
  Playwright), music cues and all, and a save must survive a restart on both; the fight's
  sound effects (`apb-modern --sounds DIR`) must sound, fade, and have the SID's pitches;
  each tune (`--music DEPARTURE DIR`) must sound, unclipped; the browser's music must play
  through Web Audio. Needs `libsdl2-dev`,
  `emscripten`, and Node with Playwright.
- `make test-yards`: the Deep Yards' generator (`core/src/yard.c`, `docs/deep-yards.md`)
  must build the same maps as the reference written from the doc (`tools/yards/yard.py`),
  natively and on sim65; every map valid with every foe reachable; picks even and
  independent.
- `make test-waystation`: the Waystation website (`waystation/`, W1 in
  `docs/waystation-web.md`), in headless Chromium: a traveler made there has the Python
  reference's Passport and boards The Fare in the terminal; Travel Stamps land, points
  are spent and stats rolled as the references say (`tests/waystation/check_site.py`);
  travelers are kept with notes, chosen to land a stamp, and, on the site signed in (a
  stand-in for claude.ai's store), kept on the player's account and boarded from the list.
  And the site's tabs (Platform, Waystation, Rules, Art desk, Arena) each open their place,
  the art desk saving by download there, and a link (`#arena:scenario=R-15`) opens one.
  Playtesters' feedback (the arena's Give feedback) arrives as issues labelled `playtest`,
  the scenario's code (`R-13`) in the title; the site is published to GitHub Pages by hand
  (Actions → Publish playtest).
- `make test-music`: the music players (`docs/music.md`) must write the same SID registers
  frame by frame: the Python reference (`tools/music/player.py`), the C player
  (`client/music.c`, under the sanitizers) and the C64's 6502 player (`fe/c64/music.s`, on
  py65), for every tune in `content/` and `tests/music/` under scripts of commands, and for
  damaged files; and the same 6502 player as the cartridge has it (`-D MUSIC_CART`, from
  `build/apb.crt`), for every tune and script. `tools/music/musicc.py build NAME.music -o FILE` compiles a tune file.

- `make test-cart`: the cartridge (`build/apb.crt`) and its disk (`build/apb-disk.d64`)
  boot on a 6502 emulator that plays an EasyFlash, or the KERNAL's loads and file reads
  (`tests/cart/run_cart.py`): keys typed on the emulated keyboard from
  `tests/cart/*.choices` must give `tests/cart/*.expected` on both (`--update` rewrites
  it: read the diff), and the story the C64 version tells (`--c64`: The Fare's
  `tests/c64/fare-edge.expected`, and the desk's route and the fight's played by
  `build/the-fare.d64`), word for word and roll for roll, receipt and Travel Stamp and
  all (the fight's battle screen on keys and the joystick, its prompts as records); a
  disk with a `PASS` file boards without typing, and one with a typo in it says so and asks;
  a trip saved at a menu (`S`) shows a trip code, `tools/passport/trip.py`'s of the C64's
  own save there, its QR code scanned back, and switched off (`[switch off]` in the
  choices) and boarded again with that code goes on as the C64's does; every raster
  split's writes land in the gap between the view's last line and row 16's fetch, to the
  cycle; the graphics are the tools'; the view (the story's pictures as
  `tools/c64pic.py` converts them; at a trip's end the Travel Stamp's QR code, the
  `qrcode` library's module for module, and scanned back off the screen by OpenCV) and
  the frames are right; no figure's sprite reaches the split; the music plays (each cue
  sends its tune, a frame every frame, the first tune `tools/music/player.py`'s register
  for register, the fights' sound effects); paragraphs wrap at 25;
  nothing scrolls off unread. `--shot FILE` draws the screen (`--shot-at RECORD FILE`
  when that record comes: `build/cart-fight-shot.png`). `tests/cart/test_ending.py`: Travel Stamps of random receipts read
  back through `tools/passport/stamp.py`, and QR codes of every version 1-4 match
  `qrcode` and scan. `tests/cart/test_damage.py`: damaged Departures (and fights' encounters)
  stop the story VM cleanly, never run wild. And `tests/cart/test_passwords.py`: the cartridge's Passports
  and Boarding Passes must decode, encode and refuse as the Python reference does, and
  `tests/cart/test_trips.py` its trip codes as `tools/passport/trip.py` does. And
  `tests/cart/test_battle.py`: the fight's rules (`cart/combat.s`, `cart/battle.s`) must
  play `tests/battle/*.txt` to their reviewed logs, make fighters and roll as
  `tools/rules/combat.py` says, and play random battles event for event as `build/battle`. The
  cartridge plays The Fare from `content/` (`tools/cart/departure.py` makes its assets).
  Needs `pip install qrcode opencv-python-headless`. And the walking engine (`cart/walk/`,
  `docs/walk.md`, `make walk`: Plan B's scrolling floor, its own program for now):
  `tests/walk/run_walk.py` walks yard 48213's first floor to its stairs (and yard 7602's
  eighth, a crowd, `build/walk-crowd.prg`) and holds every frame to `tools/walk/walk.py`,
  leader, camera and scroller, every row as the VIC reads it at its bad line, and every
  sprite (the party, foes and people, multiplexed) as the VIC starts it, and the HUD in
  the opened bottom border; no frame late. `tests/walk/vice_walk.py` runs both on x64sc,
  VICE's cycle-exact C64, and holds its pictures to the harness's pixel for pixel (without
  x64sc and xvfb-run it says so and passes).

- `make test-art`: the art desk (`tools/artdesk/`, `docs/art.md`) in headless Chromium, on
  a copy of `content/art/`: the art keeps its rules (`tools/art.py`) and the battle
  graphics build from it; every file opened and saved untouched comes back byte for byte;
  each edit (a dot, an undo, a colour, a new scenery tile, a box, a fill, flips, art pasted
  as text, trimmed or squeezed) lands exactly as worked out from the file's text; the
  server writes nothing that breaks a rule, and nothing but the art files
  (`tests/artdesk/check_artdesk.py`).

Run all eighteen before pushing. CI is paused for now: it runs only by hand (Actions → CI
→ Run workflow), not on pull requests. `make play` plays The Fare in a terminal;
`make play-e18` plays Eighteen Minutes; `make play-yards` the Deep Yards.
`make arena MATCHUP=arena/FILE.txt` fights a matchup a thousand times on the battle engine,
both sides on quick, and reports win rates, rounds and health; the site's Arena tab has
the scenarios to play by hand now (`PLAYING` in `tools/arena/scenarios.py`; `docs/arena.md`;
`python3 tools/arena/arena.py "Warden 3" vs RUST_GUARD --sweep level 1-10`): use it to
balance the rules.
`make studio` serves the studio: the art desk (http://localhost:8064/) and the native arena
(http://localhost:8064/arena/, `docs/arena.md`, by rules v1; with the prototype of exploring rooms
overhead, `docs/rooms.md`, its floors built by `tools/rooms/rooms.py` and `tools/arena/web/rooms.js`
alike, and its people's talk a Quest Script, `content/sidings/yards-talk/`, played by the story VM
as WebAssembly, `tools/arena/web/story.c`; `make test-arena-web` plays it
in headless Chromium).

**Rules v1 is in the rules lab** (`docs/turn.md`): movement (Speed 5-7, paths, hazards on
every step, Shove, Dash, pushes and falls, flying) and conditions (`registry/conditions.txt`,
read by `registry.load_conditions()`; its C table is generated into `build/next/`). Its
engine is `core/next/battle.c`, the same house rules as the core: builds that want it put
`-Icore/next` first (`NEXT_INC`, `NEXT_SRC` in the Makefile). The arena plays it
(`arena.py --rules next`, `build/arena-next`, the modern arena); the game (C64, cartridge,
story VM) stays on v0 in `core/src/battle.c` until v1 is frozen and ported. `make
test-rules-next`: reviewed battles in `tests/battle-next/` (the same on sim65; `--update`
rewrites the logs: read the diff), every roll and damage re-worked by `tools/rules/turn.py`
and `combat.py`, the engine and `turn.py` agreeing on random fighters, random battles under
the sanitizers. And seeing and being seen (`docs/open-floors.md`: `core/next/seeing.c`, its
reference `tools/rules/seeing.py`, foes' Sense and Stealth in `registry/senses.txt`):
`tests/seeing/run_seeing.py` holds reviewed approaches (`tests/seeing/*.txt`) to their logs
on the engine, the reference and sim65 (`--update` rewrites them from the reference: read
the diff), and random approaches roll for roll. `make artdesk` serves the art desk alone: figures, effects and tiles,
drawn under the C64's rules and saved to `content/art/` (`docs/art.md`).
`make modern` builds the desktop game (`./build/apb-modern build/modern/the-fare`); `make
web` builds the browser one (serve `build/web/`); `make waystation` builds the website
(serve `build/waystation/`); `make site` builds the whole site: tabs for the platform (the
player's travelers and the train), the Waystation, the rules (`docs/rules.md`'s pages, by
`tools/rules/rules_site.py`), the art desk (Save downloads there) and the arena (serve
`build/site/`; it's what's published). The 6502 test harness holds a 4 KB car, so keep each chapter of a covered Departure under that
(`qsc.py build` prints the sizes). It has no room for the whole engine: `build/harness.sim`
leaves out the Deep Yards, and `build/harness-yards.sim` the boarding desk, so the yards'
cases board the built-in traveler (`SEED+LEVEL` makes it a veteran).

## Rules-core house rules

The core must build with cc65 for the 6502 and give identical results everywhere.

- Whole numbers only. No floating point.
- C89-style: declarations at the top of blocks, no designated initializers, no `inline`.
- Pass structs by pointer, never by value.
- A function's locals must stay well under 256 bytes on the 6502; use `static` for big
  buffers (cc65 errors with "Too many local variables").
- Don't use `toupper`/`tolower` or character arithmetic on text: cc65 translates literals
  to PETSCII on the C64. Compare against literal tables instead (see `core/src/names.c`).
- cc65 2.19's optimizer has bugs. If a test passes natively but fails on sim65, suspect
  the compiler, rewrite the expression, and leave a comment (see `core/src/translate.c`).
- On the C64 the game is a main program plus overlays (`docs/c64.md`). Before calling
  into an overlay, ask for it with `APB_NEED(...)`; an overlay must never call another.
  Code that's only for one moment (loading, boarding, fights) can go in an overlay
  (`C64_PASS`, `C64_BATTLE` in the Makefile, or a `#pragma code-name` block in `vm.c`).
- Shared client text (`client/*view.c`) is ASCII on every compiler: those files include
  cc65's `ascii_charmap.h`.
- Golden values in tests (dice, passwords) must be derived independently, not copied from
  the code's own output. Use `tools/passport/passport.py` for passwords.
- Rules must stay playable at a table by hand (see `docs/tabletop.md`).

## Art

The battle screen's figures, effects and map tiles are text grids in `content/art/`
(`docs/art.md`), read through `tools/art.py`, built by `tools/battlegfx.py`; edit them with
the art desk or by hand, never in `battlegfx.py`. A new race or foe needs a figure there.
The tiles come in **looks** (forest, mountain, town, dungeon: `tiles32-LOOK.txt`,
`tiles16-LOOK.txt`, the same eight terrain tiles redrawn, then variants like `open2` and
scenery; `docs/art.md`, Looks): the explore prototype draws them, a tiles16 look holds at
most 21 tiles (the cartridge's characters).

## Registries

Races, classes, skills, items, Echoes and foes live in `registry/*.txt`, the single source of
truth (see `registry/README.md`). After editing them, run `make registry` to regenerate
`core/include/apb_registry.h` and `core/src/registry.c`; never edit those two by hand.
Python tools read the registry through `tools/registry/registry.py`.

The registry is append-only. Never reuse, renumber or reorder an id or an Echo's states;
Passports in the wild depend on them.

## Quest Script compiler

`tools/qsc/` (Python): `qsc.py check FILE.qs` parses and checks a Departure;
`qsc.py build FILE.qs -o FILE.apd` compiles it (`--split DIR` for C64-style files);
`qsc.py dump FILE.apd` verifies and disassembles an image. The language is defined in
`docs/quest-script.md` and the image format in `docs/vm-spec.md`; keep code and docs in
step. Opcodes live in `tools/qsc/opcodes.py`. Parser tests live in
`tests/qsc/`: files in `ok/` must be clean, and files in `errors/` mark each expected
message on its line with `// error: ...` or `// warning: ...`. `test_build.py` checks the
code generator against bytecode assembled by hand from the spec, round-trips every
string, and damages images to prove the verifier refuses them without crashing. Error messages are for
authors, not programmers: say what's wrong in plain words, and suggest the fix.

## Story VM

`vm/` (C, same house rules as `core/`): loads an image through the HAL, verifies it,
plays it, and fills in a receipt (`docs/boarding.md`). Game text is always ASCII; file
names and error messages are C strings in the platform's own character set. Never trust
the image: every operand is checked when it's used, not only at load.

## Clients

`client/` holds client code shared by every front end, on the HAL: the boarding desk
(`desk.c`), where a player types their Passport. Front ends live in `fe/`: `fe/term/` is
the terminal (`build/apb`), which plays an `.apd` or a directory of split files;
`fe/c64/` is the Commodore 64 (`docs/c64.md`); `fe/modern/` is the desktop and browser
(`docs/modern.md`), plain C99, one screen for both. `waystation/` is the website, where
characters are made: its rules are the core's, as WebAssembly (`waystation/ws.c`).
Characters are never made in a client; they're made at the Waystation website
(`docs/waystation-web.md`, `waystation/`). For tests,
`python3 tools/passport/passport.py new NAME RACE CLASS M,G,G,W,P,F TAG [ITEM] [ECHO=STATE...]`
makes one,
and `python3 tools/passport/boarding.py issue "PASSPORT" DEPARTURE TICKET SEED` issues it a
Boarding Pass, which carries the Passport: the one code a player types to board. `tools/waystation/station.py` is a prototype of the website's side: it issues
passes into a ticket ledger and lands Travel Stamps against it and the reward manifest.
