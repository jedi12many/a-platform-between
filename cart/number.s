; Numbers as text (docs/cartridge.md): a 16-bit whole number in decimal, by taking away
; powers of ten (no division).

        .include "zp.inc"

        .export number_text

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; number_text: a number's decimal digits, ASCII, with no leading zeros.
;   Takes:   zp_num = the number (0-65535).
;   After:   A/X = the digits (low/high), ending in 0 (number_buf: kept until the next).
;   Changes: A, X, Y; zp_num (to 0).
number_text:
        ldy #0                      ; digits so far
        ldx #3                      ; 10000, 1000, 100, 10
@power: lda #'0'
        sta digit
@take:  lda zp_num                  ; zp_num - the power, if it doesn't go below 0
        sec
        sbc tens_lo, x
        pha
        lda zp_num + 1
        sbc tens_hi, x
        bcc @next
        sta zp_num + 1
        pla
        sta zp_num
        inc digit
        bne @take                   ; (always)
@next:  pla
        lda digit                   ; a leading 0 isn't written
        cpy #0
        bne @write
        cmp #'0'
        beq @skip
@write: sta number_buf, y
        iny
@skip:  dex
        bpl @power
        lda zp_num                  ; the units, always
        ora #'0'
        sta number_buf, y
        lda #0
        sta number_buf + 1, y
        lda #<number_buf
        ldx #>number_buf
        rts

tens_lo:        .byte <10, <100, <1000, <10000
tens_hi:        .byte >10, >100, >1000, >10000

        .segment "BSS"
digit:          .res 1
number_buf:     .res 6
