; The scroller's copying code (docs/walk.md, "The scroller"), generated at the start: each
; block copies the screen's 1000 bytes a byte at a time, unrolled, 8 or 9 cycles a byte:
;
;   SHIFT_AB, SHIFT_BA  LDA from+i-41,X / STA to+i: one screen into the other, shifted by
;                       X - 41 (the camera's step: a column, a row, or both)
;   SHADE_UP, SHADE_DOWN  the same, the shadow into itself: first byte first (a shift
;                       forward), or last first (back), so nothing's read after it's written
;   BLAST               LDA SHADOW+i / STA COLOUR_RAM+i: the colours shown, top first
;
; Each ends with an RTS: 6001 bytes.

        .include "hw.inc"
        .include "zp.inc"
        .include "walk.inc"

        .export gen_all

OP_LDA_X        = $BD
OP_LDA          = $AD
OP_STA          = $8D
OP_RTS          = $60

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; gen_all: every block written.
;   Changes: A, X, Y, zp_wk_out, zp_wk_src, zp_wk_dst, zp_wk_n, zp_wk_t, zp_wk_i.
gen_all:
        ldx #0
@next:  lda blocks, x               ; out, from, to, the load's opcode, the step
        sta zp_wk_out
        lda blocks + 1, x
        sta zp_wk_out + 1
        lda blocks + 2, x
        sta zp_wk_src
        lda blocks + 3, x
        sta zp_wk_src + 1
        lda blocks + 4, x
        sta zp_wk_dst
        lda blocks + 5, x
        sta zp_wk_dst + 1
        lda blocks + 6, x
        sta zp_wk_t
        lda blocks + 7, x
        sta zp_wk_i
        txa
        pha
        jsr gen_block
        pla
        clc
        adc #8
        tax
        cpx #blocks_end - blocks
        bne @next
        rts

; One block: out, its first load's and store's addresses, the load's opcode, the step (1
; or $FF), all set; 1000 pairs and an RTS.
gen_block:
        lda #<SCREEN_SIZE
        sta zp_wk_n
        lda #>SCREEN_SIZE
        sta zp_wk_n + 1
@pair:  ldy #0
        lda zp_wk_t
        sta (zp_wk_out), y
        iny
        lda zp_wk_src
        sta (zp_wk_out), y
        iny
        lda zp_wk_src + 1
        sta (zp_wk_out), y
        iny
        lda #OP_STA
        sta (zp_wk_out), y
        iny
        lda zp_wk_dst
        sta (zp_wk_out), y
        iny
        lda zp_wk_dst + 1
        sta (zp_wk_out), y
        lda zp_wk_out               ; out += 6
        clc
        adc #6
        sta zp_wk_out
        bcc :+
        inc zp_wk_out + 1
:       lda zp_wk_i                 ; from and to: + 1, or - 1
        bmi @down
        inc zp_wk_src
        bne :+
        inc zp_wk_src + 1
:       inc zp_wk_dst
        bne @count
        inc zp_wk_dst + 1
        jmp @count
@down:  lda zp_wk_src
        bne :+
        dec zp_wk_src + 1
:       dec zp_wk_src
        lda zp_wk_dst
        bne :+
        dec zp_wk_dst + 1
:       dec zp_wk_dst
@count: lda zp_wk_n
        bne :+
        dec zp_wk_n + 1
:       dec zp_wk_n
        lda zp_wk_n
        ora zp_wk_n + 1
        bne @pair
        ldy #0
        lda #OP_RTS
        sta (zp_wk_out), y
        rts

        .segment "DATA"

LAST            = SCREEN_SIZE - 1
blocks:
        .word SHIFT_AB, SCREEN_A - OFFSET_BIAS, SCREEN_B
        .byte OP_LDA_X, 1
        .word SHIFT_BA, SCREEN_B - OFFSET_BIAS, SCREEN_A
        .byte OP_LDA_X, 1
        .word SHADE_UP, SHADOW - OFFSET_BIAS, SHADOW
        .byte OP_LDA_X, 1
        .word SHADE_DOWN, SHADOW - OFFSET_BIAS + LAST, SHADOW + LAST
        .byte OP_LDA_X, $FF
        .word BLAST, SHADOW, COLOUR_RAM
        .byte OP_LDA, 1
blocks_end:
