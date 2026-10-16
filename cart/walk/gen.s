; The scroller's copying code (docs/walk.md, "The scroller"), generated at the start, a
; byte's copy each, unrolled:
;
;   SHIFT_AB, SHIFT_BA  LDA from+i-41,X / STA to+i: one screen into the other, shifted by
;                       X - 41 (the camera's step: a column, a row, or both), 8 or 9 cycles
;                       a byte; an RTS half way (after 500 copies: SECOND_HALF is where the
;                       rest start) and at the end: 6002 bytes
;   COLOUR_ROWS         a row of the colour RAM each: LDA map+c,Y / STA COLOUR_RAM+i, 40 of
;                       them and an RTS (ROW_CODE bytes), 8 cycles a byte: Y the screen's
;                       first column on the area, map the page of its row of squares (the
;                       colour map's: walk.inc), written in by...
;   AIM_ROWS            ...a row's 40 STA row+6c+2 and an RTS (AIM_CODE bytes): A the page

        .include "hw.inc"
        .include "zp.inc"
        .include "walk.inc"

        .export gen_all

OP_LDA_X        = $BD
OP_LDA_Y        = $B9
OP_STA          = $8D
OP_RTS          = $60

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; gen_all: every block written, and the colours' rows.
;   Changes: A, X, Y, zp_wk_out, zp_wk_src, zp_wk_dst, zp_wk_n, zp_wk_i.
gen_all:
        ldx #0
@next:  lda blocks, x               ; out, from, to
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
        txa
        pha
        jsr gen_block
        pla
        clc
        adc #6
        tax
        cpx #blocks_end - blocks
        bne @next
        ; (on into gen_rows)

; The colours' rows, one after another from COLOUR_ROWS: row r's 40 copies to COLOUR_RAM +
; 40 r on, and an RTS; and their aims, from AIM_ROWS: row r's 40 high bytes, and an RTS.
gen_rows:
        lda #<COLOUR_ROWS
        sta zp_wk_out
        lda #>COLOUR_ROWS
        sta zp_wk_out + 1
        lda #<AIM_ROWS
        sta zp_wk_src
        lda #>AIM_ROWS
        sta zp_wk_src + 1
        lda #<COLOUR_RAM
        sta zp_wk_dst
        lda #>COLOUR_RAM
        sta zp_wk_dst + 1
        lda #ROWS
        sta zp_wk_i
@row:   lda #0
        sta zp_wk_n                 ; the column
@pair:  ldy #0                      ; LDA map+c,Y (its page aimed later)
        lda #OP_LDA_Y
        sta (zp_wk_out), y
        iny
        lda zp_wk_n
        sta (zp_wk_out), y
        iny
        lda #0
        sta (zp_wk_out), y
        iny                         ; STA COLOUR_RAM+i
        lda #OP_STA
        sta (zp_wk_out), y
        iny
        lda zp_wk_dst
        sta (zp_wk_out), y
        iny
        lda zp_wk_dst + 1
        sta (zp_wk_out), y
        ldy #0                      ; its aim: STA at the load's high byte
        lda #OP_STA
        sta (zp_wk_src), y
        iny
        lda zp_wk_out
        clc
        adc #2
        sta (zp_wk_src), y
        iny
        lda zp_wk_out + 1
        adc #0
        sta (zp_wk_src), y
        lda zp_wk_src               ; aim += 3
        clc
        adc #3
        sta zp_wk_src
        bcc :+
        inc zp_wk_src + 1
:       lda zp_wk_out               ; out += 6
        clc
        adc #6
        sta zp_wk_out
        bcc :+
        inc zp_wk_out + 1
:       inc zp_wk_dst
        bne :+
        inc zp_wk_dst + 1
:       inc zp_wk_n
        lda zp_wk_n
        cmp #COLS
        bne @pair
        ldy #0                      ; the RTSes
        lda #OP_RTS
        sta (zp_wk_out), y
        sta (zp_wk_src), y
        inc zp_wk_out
        bne :+
        inc zp_wk_out + 1
:       inc zp_wk_src
        bne :+
        inc zp_wk_src + 1
:       dec zp_wk_i
        bne @row
        rts

; One block: out, and its first load's and store's addresses, set; 1000 pairs and an RTS.
gen_block:
        lda #<SCREEN_SIZE
        sta zp_wk_n
        lda #>SCREEN_SIZE
        sta zp_wk_n + 1
@pair:  ldy #0
        lda #OP_LDA_X
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
:       inc zp_wk_src               ; from and to: the next byte's
        bne :+
        inc zp_wk_src + 1
:       inc zp_wk_dst
        bne :+
        inc zp_wk_dst + 1
:       lda zp_wk_n
        bne :+
        dec zp_wk_n + 1
:       dec zp_wk_n
        lda zp_wk_n                 ; half way: an RTS between the halves
        cmp #<(SCREEN_SIZE / 2)
        bne :+
        lda zp_wk_n + 1
        cmp #>(SCREEN_SIZE / 2)
        bne :+
        ldy #0
        lda #OP_RTS
        sta (zp_wk_out), y
        inc zp_wk_out
        bne :+
        inc zp_wk_out + 1
:       lda zp_wk_n
        ora zp_wk_n + 1
        bne @pair
        ldy #0
        lda #OP_RTS
        sta (zp_wk_out), y
        rts

        .segment "DATA"

blocks:
        .word SHIFT_AB, SCREEN_A - OFFSET_BIAS, SCREEN_B
        .word SHIFT_BA, SCREEN_B - OFFSET_BIAS, SCREEN_A
blocks_end:
