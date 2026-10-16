; A step's colours copied behind the raster (docs/walk.md, "The scroller"): the colour RAM
; can't be doubled, so at a swap the shadow's copied in, top first, ahead of the raster
; (BLAST). But a row's colours are read once, at its bad line: in the frame before the swap,
; once the raster's past a row's bad line, that row can take its new colours already. So the
; frame loop, done with that frame and waiting, copies each row as the raster passes it;
; the swap's copy then starts at the first row not done. Both copy the shadow, so a row
; copied twice (the swap coming in the middle of one) comes out the same.
;
; A row's copy is BLAST's own code run from the row's first pair to the next row's, an RTS
; put there for the call (BLAST's pairs are LDA SHADOW+i / STA COLOUR_RAM+i, 6 bytes; the
; first half's 500, an RTS, then the second's).

        .include "hw.inc"
        .include "walk.inc"

        .export precopy, blast_rest
        .import wk_frame, view_d011

OP_LDA          = $AD
OP_RTS          = $60
FIRST_DMA       = 48            ; row 0's bad line: 48 + ys

        .segment "HIGH"

; Row R's first pair in BLAST.
.define ROW_AT(r) (BLAST + (40 * (r) < 500) * 6 * 40 * (r) + (40 * (r) >= 500) * (SECOND_HALF + 6 * (40 * (r) - 500)))

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
        cpx #ROWS - 1        ; (row 24's bad line is too near the bottom)
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
        ldx rows_done               ; row X: an RTS at the next's first pair, then its own
        lda row_lo + 1, x
        sta @put + 1
        sta restore_at + 1
        lda row_hi + 1, x
        sta @put + 2
        sta restore_at + 2
        lda #OP_RTS
@put:   sta $FFFF
        lda row_lo, x
        sta @call + 1
        lda row_hi, x
        sta @call + 2
@call:  jsr $FFFF
        cpx #12                     ; (row 12 runs over the halves' RTS)
        bne :+
        jsr BLAST + SECOND_HALF
:       jsr restore
        sei                         ; counted, if the swap hasn't come meanwhile
        lda wk_frame
        cmp frame_at
        bne :+
        inc rows_done
:       cli
        jmp @row
@out:   rts

; ----------------------------------------------------------------------------------------
; blast_rest: the swap's copy (border.s's bottom), from the first row not done: the pair
; the frame loop may have stopped with an RTS put back first.
;   Before:  in the bottom's interrupt.
;   Changes: A, X, Y.
blast_rest:
        jsr restore
        ldx rows_done
        lda row_lo, x
        sta @call + 1
        lda row_hi, x
        sta @call + 2
@call:  jsr $FFFF
        cpx #13                     ; (a row of the first half: the second's too)
        bcs :+
        jsr BLAST + SECOND_HALF
:       lda #0
        sta rows_done
        rts

; The pair an RTS was put at given its LDA back (BLAST's first pair's, an LDA, till one is).
restore:
        lda #OP_LDA
restore_at:
        sta BLAST
        rts

row_lo:
        .repeat ROWS + 1, r
        .byte <ROW_AT r
        .endrepeat
row_hi:
        .repeat ROWS + 1, r
        .byte >ROW_AT r
        .endrepeat

        .segment "BSS"

rows_done:  .res 1              ; rows of the coming swap already copied
frame_at:   .res 1
line_after: .res 1
