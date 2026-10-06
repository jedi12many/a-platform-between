# A Platform Between

Design docs live in `docs/`; the rules core lives in `core/`.

## Commands

- `make test`: native tests (gcc/clang, `-Werror`).
- `make test-6502`: the same tests on the sim65 6502 simulator. Needs cc65
  (`apt-get install cc65`).
- `make crosscheck`: the demo's native and 6502 output must be byte-identical.
- `make c64`: build `build/demo.prg` for the Commodore 64.
- `make test-python`: the Python Passport reference (`tools/passport/`) must decode the
  C engine's password; the registry and Quest Script parser tests must pass.
- `make check-registry`: the generated C registry must match `registry/*.txt`.
- `make check-content`: every `.qs` file in `content/` must compile cleanly.

Run all seven before pushing; CI runs them too.

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
- Golden values in tests (dice, passwords) must be derived independently, not copied from
  the code's own output. Use `tools/passport/passport.py` for passwords.
- Rules must stay playable at a table by hand (see `docs/tabletop.md`).

## Registries

Races, classes, skills, items and Echoes live in `registry/*.txt`, the single source of
truth (see `registry/README.md`). After editing them, run `make registry` to regenerate
`core/include/apb_registry.h` and `core/src/registry.c`; never edit those two by hand.
Python tools read the registry through `tools/registry/registry.py`.

The registry is append-only. Never reuse, renumber or reorder an id or an Echo's states;
Passports in the wild depend on them.

## Quest Script compiler

`tools/qsc/` (Python): `qsc.py check FILE.qs` parses and checks a Departure. The language
is defined in `docs/quest-script.md`; keep the two in step. Parser tests live in
`tests/qsc/`: files in `ok/` must be clean, and files in `errors/` mark each expected
message on its line with `// error: ...` or `// warning: ...`. Error messages are for
authors, not programmers: say what's wrong in plain words, and suggest the fix.
