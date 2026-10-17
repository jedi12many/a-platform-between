; What cart/walk/seeing.s takes from the walking engine, for its tests on their own
; (tests/seeing/run_seeing.py): a map's rows and the tiles' terrain, set by the harness.

        .include "walk.inc"

        .export sq_row_lo, sq_row_hi, terrain, see_entry

        .segment "CODE"

; The harness's way in: a JMP to each routine (at $1000, $1003), so their addresses are known.
        .import see_prepare, see_step
see_entry:
        jmp see_prepare
        jmp see_step

        .segment "BSS"

sq_row_lo:  .res SQUARES_Y_MAX
sq_row_hi:  .res SQUARES_Y_MAX
terrain:    .res 32
