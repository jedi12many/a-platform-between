; The floor (docs/walk.md, "The floor's asset"): tools/walk/walk.py's, built into the
; program; and where each row of its squares starts.

        .include "walk.inc"

        .export floor, sq_row_lo, sq_row_hi

        .segment "DATA"

floor:  .incbin "walk/floor.bin"

; Row y of the squares: floor + FL_SQUARES + 48 y.
sq_row_lo:
        .repeat SQUARES_Y, i
        .byte <(floor + FL_SQUARES + i * SQUARES_X)
        .endrepeat
sq_row_hi:
        .repeat SQUARES_Y, i
        .byte >(floor + FL_SQUARES + i * SQUARES_X)
        .endrepeat
