# A Platform Between

Design docs live in `docs/`; the rules core lives in `core/`.

## Commands

- `make test`: native tests (gcc/clang, `-Werror`).
- `make test-6502`: the same tests on the sim65 6502 simulator. Needs cc65
  (`apt-get install cc65`).
- `make crosscheck`: the demo's native and 6502 output must be byte-identical.
- `make c64`: build `build/demo.prg` and the C64 disks, `build/the-fare.d64` and
  `build/eighteen-minutes.d64` (`LOAD"APB",8` in VICE; see `docs/c64.md`).
- `make test-python`: the Python Passport reference (`tools/passport/`) must decode the
  C engine's password; the registry and Quest Script parser tests must pass.
- `make check-registry`: the generated C registry must match `registry/*.txt`.
- `make check-content`: every `.qs` file in `content/` must compile to an image the
  verifier accepts.
- `make test-vm`: Story VM playthroughs (`tests/vm/cases.txt`) must match their expected
  transcripts natively and on sim65, and damaged images must never crash the VM under
  AddressSanitizer/UBSan. After a deliberate change, `python3 tests/vm/run_tests.py
  --update` rewrites the expected transcripts: read the diff before committing it.
  Together, the playthroughs of *The Fare* must run every instruction in it, and so must
  those of *Eighteen Minutes* (`COVERED` in `run_tests.py`): a passage no case reaches
  fails the test, so a new route needs a new case. `@name` in a case
  boards a traveler from `tests/vm/travelers.txt`; every check is re-rolled from the
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
  `python3 tests/battle/run_battles.py --update` rewrites the logs: read the diff.
- `make test-c64`: the C64 program from the `.d64` must play The Fare and Eighteen
  Minutes on a 6502 emulator
  (py65: `pip install py65`; the disk's pictures need Pillow) with the KERNAL answered
  in Python (`tests/c64/run_c64.py`): transcripts match `tests/c64/*.expected`, the
  Travel Stamp is the terminal's, a save survives switching off, the C stack stays
  under 384 bytes; and no overlay may use another's code or data
  (`fe/c64/check_overlays.py`). `--shots DIR` saves pictures of the screen to look at.

Run all twelve before pushing; CI runs them too. `make play` plays The Fare in a terminal;
`make play-e18` plays chapter 1 of Eighteen Minutes. The 6502 test harness holds a 4 KB
car, so keep each chapter of a covered Departure under that (`qsc.py build` prints the
sizes).

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
`fe/c64/` is the Commodore 64 (`docs/c64.md`).
Characters are never made in a client; they're made at the Waystation website
(`docs/waystation-web.md`). For tests,
`python3 tools/passport/passport.py new NAME RACE CLASS M,G,G,W,P,F TAG [ITEM] [ECHO=STATE...]`
makes one,
and `python3 tools/passport/boarding.py issue "PASSPORT" DEPARTURE TICKET SEED` issues it a
Boarding Pass. `tools/waystation/station.py` is a prototype of the website's side: it issues
passes into a ticket ledger and lands Travel Stamps against it and the reward manifest.
