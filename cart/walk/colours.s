; A step's colours (docs/walk.md, "The scroller"): the colour RAM can't be doubled, so at a
; swap each row's colours come straight from the colour map (COLOUR_ROWS, gen.s), a row a
; call, aimed beforehand at the map's rows the screen will show (colour_aim). A row's
; colours are read once, at its bad line: in the frame before the swap, once the raster's
; past a row's bad line, that row can take its new colours already. So the frame loop,
; done with that frame and waiting, copies each row as the raster passes it; the swap's
; copy (the bottom's interrupt) then the rows not done, top first, ahead of the raster.
; Both copy from the map, so a row copied twice (the swap coming in the middle of one)
; comes out the same.

        .include "hw.inc"
        .include "walk.inc"

        .export precopy, blast_rest, colour_row, colour_aim, aim_all
        .import wk_frame, view_d011, wk_ncx, wk_ncy

FIRST_DMA       = 48            ; row 0's bad line: 48 + ys

; Row X's colours: its code, Y the screen's first column on the area. (A macro: the loop's
; copy and the interrupt's each have their own call.)
.macro ROW_COPY
        .local call
        lda row_lo, x
        sta call + 1
        lda row_hi, x
        sta call + 2
        ldy wk_ncx
call:   jsr $FFFF
.endmacro

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; colour_aim: each row's copy aimed at its row of squares' page in the colour map: row r
; shows the area's row of characters wk_ncy + r, of squares (wk_ncy + r) / 2. Only the
; rows whose page has changed are aimed again (none after a step across; every other row
; after a step down or up); aim_all forgets them all first (the start's).
;   Before:  no copy under way (the loop's, between steps).
;   Changes: A, X, Y.
aim_all:
        lda #$FF
        ldx #ROWS - 1
:       sta aimed, x
        dex
        bpl :-
colour_aim:
        ldx #0
@row:   txa
        clc
        adc wk_ncy
        lsr a
        clc
        adc #>COLOUR_MAP
        cmp aimed, x
        beq @next
        sta aimed, x
        ldy aim_lo, x
        sty @call + 1
        ldy aim_hi, x
        sty @call + 2
@call:  jsr $FFFF
@next:  inx
        cpx #ROWS
        bne @row
        rts

aim_lo:
        .repeat ROWS, r
        .byte <(AIM_ROWS + AIM_CODE * r)
        .endrepeat
aim_hi:
        .repeat ROWS, r
        .byte >(AIM_ROWS + AIM_CODE * r)
        .endrepeat

        .segment "HIGH"

; ----------------------------------------------------------------------------------------
; colour_row: row X of the colour RAM, the map's at the screen's cell (wk_ncx, wk_ncy).
;   Before:  the copies aimed (colour_aim) at wk_ncy.
;   Changes: A, Y.
colour_row:
        ROW_COPY
        rts

; ----------------------------------------------------------------------------------------
; precopy: from the frame loop, done with a frame whose step swaps at the next bottom
; (wk_swap): the rows the raster's past copied, till the bottom (or a line before it).
;   Changes: A, X, Y.
precopy:
        lda wk_frame
        sta frame_at
        lda #0
        sta rows_done
@row:   ldx rows_done
        cpx #ROWS - 1               ; (row 24's bad line is too near the bottom)
        bcs @out
        txa                         ; the line after its bad line: 48 + ys + 8 r + 1
        asl a
        asl a
        asl a
        adc #FIRST_DMA + 1
        sta line_after
        lda view_d011
        and #7
        clc
        adc line_after
        sta line_after
@wait:  lda wk_frame                ; the swap's come (or begun): the rest is its
        cmp frame_at
        bne @out
        lda VIC_CTRL1
        bmi @out                    ; (past line 255)
        lda VIC_RASTER
        cmp #BOTTOM_LINE - 1
        bcs @out                    ; (too near the bottom's interrupt)
        cmp line_after
        bcc @wait
        jsr colour_row
        sei                         ; counted, if the swap hasn't come meanwhile
        lda wk_frame
        cmp frame_at
        bne :+
        inc rows_done
:       cli
        jmp @row
@out:   rts

; ----------------------------------------------------------------------------------------
; blast_rest: the swap's copy (border.s's bottom), from the first row not done (the one the
; frame loop may be in the middle of, again), top first.
;   Before:  in the bottom's interrupt.
;   Changes: A, X, Y.
blast_rest:
        ldx rows_done
rest_row:
        ROW_COPY
        inx
        cpx #ROWS
        bcc rest_row
        lda #0
        sta rows_done
        rts

row_lo:
        .repeat ROWS, r
        .byte <(COLOUR_ROWS + ROW_CODE * r)
        .endrepeat
row_hi:
        .repeat ROWS, r
        .byte >(COLOUR_ROWS + ROW_CODE * r)
        .endrepeat

        .segment "BSS"

rows_done:  .res 1              ; rows of the coming swap already copied
frame_at:   .res 1
line_after: .res 1
aimed:      .res ROWS           ; each row's copy: the colour map's page it's aimed at
