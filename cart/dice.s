; The dice log (docs/frames.md): rows 20-23, columns 26-39, each roll two rows, the newest
; at the bottom, bright, the one before it grey: "Wits 119" over "vs 74: pass". And its
; record for the tests, "[Wits 119 vs 74: pass]" (record_line), as the C64 version's
; transcripts have it.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export dice_roll, record_line, record_text
        .import text_at, number_text, chk_total, chk_tn, chk_result

TOP     = TEXT_SCREEN + (LOG_LAST - 1) * COLS + SIDE_COL    ; the newest roll's two rows
BOTTOM  = TEXT_SCREEN + LOG_LAST * COLS + SIDE_COL
UP1     = TEXT_SCREEN + DICE_TOP * COLS + SIDE_COL          ; the one before it
UP2     = TEXT_SCREEN + (DICE_TOP + 1) * COLS + SIDE_COL

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; dice_roll: the last check (rules.s: chk_total, chk_tn, chk_result) into the dice log,
; and its record.
;   Takes:   A/X = who rolled (low/high): "Wits", "Tech"; ASCII, ending in 0, under 10.
;   Changes: A, X, Y; zp_t0-zp_t2; text.s's and number.s's zero page.
dice_roll:
        pha
        txa
        pha
        ldx #SIDE_COLS - 1          ; the last roll up, grey
@up:    lda TOP, x
        sta UP1, x
        lda BOTTOM, x
        sta UP2, x
        lda #GREY
        sta UP1 + TEXT_TO_COLOUR, x
        sta UP2 + TEXT_TO_COLOUR, x
        dex
        bpl @up
        lda #0                      ; the top line: who, and the total
        sta length
        pla
        tax
        pla
        jsr append
        lda #<space
        ldx #>space
        jsr append
        lda chk_total
        sta zp_num
        lda chk_total + 1
        sta zp_num + 1
        jsr number_text
        jsr append
        ldx length
        stx top_end
        lda #<vs                    ; the bottom: the TN and the outcome
        ldx #>vs
        jsr append
        lda chk_tn
        sta zp_num
        lda chk_tn + 1
        sta zp_num + 1
        jsr number_text
        jsr append
        lda #<colon
        ldx #>colon
        jsr append
        ldx chk_result
        lda word_lo, x
        pha
        lda word_hi, x
        tax
        pla
        jsr append
        lda #SIDE_COL               ; onto the screen
        sta zp_t0
        lda #SIDE_COLS
        sta zp_t2
        lda #WHITE
        sta zp_t1
        ldx top_end
        lda #0
        sta line, x                 ; (the top line ends where the bottom starts)
        lda #<line
        ldx #>line
        ldy #LOG_LAST - 1
        jsr text_at
        lda #CYAN
        sta zp_t1
        lda top_end
        clc
        adc #<(line + 1)
        pha
        lda #>(line + 1)
        adc #0
        tax
        pla
        ldy #LOG_LAST
        jsr text_at
        ldx top_end                 ; the record: "[" top " " bottom "]"
        lda #' '
        sta line, x
        lda #<bracket
        ldx #>bracket
        jsr record_text
        rts

; append: ASCII (A/X, ending in 0) onto `line` at `length`. Changes A, Y; zp_t0, zp_t1.
append:
        sta zp_t0
        stx zp_t1
        ldy #0
        ldx length
@char:  lda (zp_t0), y
        sta line, x
        beq @done
        inx
        iny
        bne @char                   ; (always)
@done:  stx length
        rts

; ----------------------------------------------------------------------------------------
; record_text: "[", `line`, "]" as a record (record_line). Changes A, X, Y.
record_text:
        lda #'['
        sta bracket
        ldx length
        lda #']'
        sta line, x
        lda #0
        sta line + 1, x
        lda #<bracket
        ldx #>bracket
        ; (on into record_line)

; record_line: the tests' record of what the story log doesn't show (a roll, a picture, a
; tune): tests/cart/run_cart.py reads A/X (ASCII, ending in 0) here, so don't rename it.
; Changes nothing.
record_line:
        rts

space:  .byte " ", 0
vs:     .byte " vs ", 0             ; (the top line's end: its space becomes a 0)
colon:  .byte ": ", 0
fail:   .byte "fail", 0
cost:   .byte "cost", 0
pass:   .byte "pass", 0
crit:   .byte "crit", 0
word_lo:        .byte <fail, <cost, <pass, <crit
word_hi:        .byte >fail, >cost, >pass, >crit

        .segment "BSS"
bracket:        .res 1              ; "[", then the line (record_text puts it)
line:           .res 48
length:         .res 1
top_end:        .res 1
