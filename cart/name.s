; The traveler's name as the game says it (client/view.c's apb_view_name): for the story,
; the party frame, the fights and the boarding desk.

        .include "char.inc"

        .export name_text
        .import traveler

        .segment "RESIDENT"

; name_text: the traveler's name as it reads: "Kestrel", "Moth-Folk Ana". Names are kept
; in capitals; each word's first letter stays one, the rest go small; the padding goes.
;   After:   A/X = the name (low/high), ending in 0 (name_buf: kept until the next).
;   Changes: A, X, Y.
name_text:
        ldy #8                      ; how long, without the padding
@trim:  lda traveler + CH_NAME - 1, y
        cmp #' '
        bne @long
        dey
        bne @trim
@long:  sty name_len
        ldx #0
        ldy #1                      ; 1: the next letter starts a word
@char:  cpx name_len
        beq @end
        lda traveler + CH_NAME, x
        cpy #0
        bne @first
        cmp #'A'
        bcc @first
        cmp #'Z' + 1
        bcs @first
        ora #%00100000              ; small
@first: sta name_buf, x
        ldy #0
        cmp #' '
        beq @word
        cmp #'-'
        bne @next
@word:  ldy #1
@next:  inx
        bne @char                   ; (always)
@end:   lda #0
        sta name_buf, x
        lda #<name_buf
        ldx #>name_buf
        rts

        .segment "BSS"
name_buf:       .res 9
name_len:       .res 1
