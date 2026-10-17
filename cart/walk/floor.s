; The floor (docs/walk.md, "The floor's asset"): tools/walk/walk.py's, built into the
; program, and its squares (a file of their own: the floor's size is the asset's); and
; where each row of its squares is once maps_build (edge.s) has put them on their pages.

        .include "walk.inc"

        .export floor, squares, sq_row_lo, sq_row_hi

        .segment "DATA"

floor:  .incbin "walk/floor.bin"

; The squares, w x h, a row at a time: loaded past $27FF (the program's top, which gen.s
; writes over), so copied onto their pages first thing (maps_build).
        .segment "SQUARES"

squares: .incbin "walk/squares.bin"

        .segment "BSS"

; Row y of the squares: COLOUR_MAP's page y, from 2 w (maps_build).
sq_row_lo:  .res SQUARES_Y_MAX
sq_row_hi:  .res SQUARES_Y_MAX
