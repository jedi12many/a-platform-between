; The dice log (docs/frames.md): rows 20-23, columns 26-39, each roll two rows, the newest
; at the bottom, bright, the one before it grey: "Wits 119" over "vs 74: pass". And its
; record for the tests, "[Wits 119 vs 74: pass]" (record_line), as the C64 version's
; transcripts have it.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export dice_roll, dice_show, dice_said, record_line, record_text
        .import text_at, number_text, chk_total, chk_tn, chk_result

TOP     = TEXT_SCREEN + (LOG_LAST - 1) * COLS + SIDE_COL    ; the newest roll's two rows
BOTTOM  = TEXT_SCREEN + LOG_LAST * COLS + SIDE_COL
UP1     = TEXT_SCREEN + DICE_TOP * COLS + SIDE_COL          ; the one before it
UP2     = TEXT_SCREEN + (DICE_TOP + 1) * COLS + SIDE_COL

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; dice_roll: the last check (rules.s: chk_total, chk_tn, chk_result) into the dice log,
; and its record: "Wits 119" over "vs 74: pass".
;   Takes:   A/X = who rolled (low/high): "Wits", "Tech"; ASCII, ending in 0.
;   Changes: A, X, Y; zp_t0-zp_t2; text.s's and number.s's zero page.
dice_roll:
        pha
        ldy chk_result
        lda word_lo, y
        sta dice_said
        lda word_hi, y
        sta dice_said + 1
        pla
        ; (on into dice_show)

; dice_show: a roll into the dice log, and its record, as the C version's apb_view_roll
; has them: who and the total over "vs", the TN and what came of it ("Ash rat 42" over
; "vs 58: graze 1"). A name too long for the top row beside the total is its last word,
; or its start; the record has it whole.
;   Takes:   A/X = who (ASCII, ending in 0, 20 at most); dice_said = what came of it
;            (ASCII, ending in 0, 12 at most); chk_total and chk_tn (16 bits each).
;   Changes: A, X, Y; zp_t0-zp_t2; text.s's and number.s's zero page.
dice_show:
        sta who
        stx who + 1
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
        lda #0                      ; the record: who, the total, "vs", the TN, the outcome
        sta length
        lda who
        ldx who + 1
        jsr append
        ldx length
        stx who_end
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
        lda #<vs
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
        lda dice_said
        ldx dice_said + 1
        jsr append
        ; The top row: who (shortened to fit) and the total.
        lda top_end                 ; room for who: the row less the space and the total
        sec
        sbc who_end
        sta zp_t2
        lda #SIDE_COLS
        sec
        sbc zp_t2
        sta room
        ldx #0                      ; who, from x to who_to
        lda who_end
        sta who_to
        cmp room
        bcc @fits
        beq @fits
        ldy #0                      ; too long: from after its last space
@space: lda line, y
        iny
        cmp #' '
        bne @not
        tya
        tax
@not:   cpy who_end
        bcc @space
        stx zp_t2                   ; still too long: its start, cut to fit
        lda who_end
        sec
        sbc zp_t2
        cmp room
        bcc @fits
        beq @fits
        ldx #0
        lda room
        sta who_to
@fits:  ldy #0
@who:   cpx who_to
        bcs @total
        lda line, x
        sta top, y
        inx
        iny
        bne @who                    ; (always)
@total: ldx who_end                 ; then the space and the total
@copy:  lda line, x
        sta top, y
        inx
        iny
        cpx top_end
        bne @copy
        lda #0
        sta top, y
        lda #SIDE_COL               ; onto the screen
        sta zp_t0
        lda #SIDE_COLS
        sta zp_t2
        lda #WHITE
        sta zp_t1
        lda #<top
        ldx #>top
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
        ; (on into record_text)

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

space:  .byte " ", 0
vs:     .byte " vs ", 0             ; (the top line's end: its space becomes a 0)
colon:  .byte ": ", 0
said_fail: .byte "fail", 0
said_cost: .byte "cost", 0
said_pass: .byte "pass", 0
said_crit: .byte "crit", 0
word_lo:        .byte <said_fail, <said_cost, <said_pass, <said_crit
word_hi:        .byte >said_fail, >said_cost, >said_pass, >said_crit

        .segment "BSS"
bracket:        .res 1              ; "[", then the line (record_text puts it)
line:           .res 56
length:         .res 1
top_end:        .res 1
who:            .res 2
who_end:        .res 1
who_to:         .res 1
room:           .res 1
top:            .res SIDE_COLS + 1      ; the top row as shown
dice_said:      .res 2              ; dice_show: what came of the roll
