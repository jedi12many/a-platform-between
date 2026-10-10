; A trip's end (docs/boarding.md): the outcome and the receipt in the story log, as the
; C64 version prints them (client/receipt_view.c), then the Travel Stamp: its lines to
; type, and its QR code in the view to scan (qr.s, qrview.s). Code in the ending asset
; (asset 1), run from the staging RAM: play.s fetches it when a trip ends.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "receipt.inc"

        .export ending
        .import receipt, log_print, log_chars, number_text, stamp_encode, qr_make, qr_show
        .import item_lo, item_hi
        .importzp ITEM_COUNT

LINE            = 20                ; a stamp's line: 19 symbols and a check

        .segment "ENDING"

; ----------------------------------------------------------------------------------------
; ending: the receipt, and the Travel Stamp if the trip was boarded with a Boarding Pass
; (its ticket on the receipt): its lines, and its QR code in the view.
;   Before:  $01 = $35; the trip ended (vm.s: the receipt ready).
;   Changes: A, X, Y; zp_t0-zp_t3; and the zero page of what it calls.
ending: lda receipt + R_OUTCOME
        bne @failed
        lda #<complete_line
        ldx #>complete_line
        bne @said                   ; (always)
@failed:
        lda #<failed_line
        ldx #>failed_line
@said:  jsr row
        lda #<nothing
        ldx #>nothing
        jsr row
        lda #<your_receipt
        ldx #>your_receipt
        jsr row
        ldx #R_XP                   ; "  5 XP", "  50000 Debt added" ...
        lda #<xp
        ldy #>xp
        jsr amount
        ldx #R_DEBT_PAID
        lda #<debt_paid
        ldy #>debt_paid
        jsr amount
        ldx #R_DEBT_ADDED
        lda #<debt_added
        ldy #>debt_added
        jsr amount
        ldx #R_GAINED               ; "  Gained: Porter's Hook" ...
        lda #<gained
        ldy #>gained
        jsr items
        ldx #R_LOST
        lda #<lost
        ldy #>lost
        jsr items
        lda receipt + R_ECHOES      ; "  2 Echoes will follow you."
        beq @blank
        sta zp_num
        lda #0
        sta zp_num + 1
        jsr start_line
        jsr two_spaces
        jsr number_text
        jsr add
        lda receipt + R_ECHOES
        cmp #1
        bne @echoes
        lda #<one_echo
        ldx #>one_echo
        bne @follow                 ; (always)
@echoes:
        lda #<echoes
        ldx #>echoes
@follow:
        jsr add
        lda #<follow
        ldx #>follow
        jsr add
        jsr end_line
@blank: lda #<nothing
        ldx #>nothing
        jsr row
        lda receipt + R_TICKET      ; a ticket: boarded with a pass
        ora receipt + R_TICKET + 1
        ora receipt + R_TICKET + 2
        ora receipt + R_TICKET + 3
        beq @unstamped
        lda #<stamp
        ldx #>stamp
        jsr stamp_encode
        bcc @stamped
@unstamped:
        lda #<no_stamp
        ldx #>no_stamp
        jmp log_print
@stamped:
        lda #<your_stamp
        ldx #>your_stamp
        jsr log_print
        lda #<nothing
        ldx #>nothing
        jsr row
        lda #<stamp                 ; its lines, "  " and 20 symbols each
        sta zp_t2
        lda #>stamp
        sta zp_t3
@line:  ldy #0
        lda (zp_t2), y
        beq @code
        jsr start_line
        lda #' '
        jsr put
        jsr put
        ldy #0
@symbol:
        lda (zp_t2), y
        beq @lined
        jsr put
        iny
        cpy #LINE
        bne @symbol
@lined: tya
        clc
        adc zp_t2
        sta zp_t2
        bcc @row
        inc zp_t3
@row:   jsr end_line
        jmp @line
@code:  lda #<stamp                 ; and its code, to scan
        ldx #>stamp
        jsr qr_make
        bcs @done
        jsr qr_show
        lda #<scan
        ldx #>scan
        jmp log_print
@done:  rts

; amount: "  N WHAT" for the receipt's 2 bytes at receipt + X, unless they're 0.
;   Takes:   X = the offset; A/Y = WHAT (low/high). Changes A, X, Y; zp_t0, zp_t1.
amount: sta what
        sty what + 1
        lda receipt, x
        sta zp_num
        lda receipt + 1, x
        sta zp_num + 1
        ora zp_num
        beq @none
        jsr start_line
        jsr two_spaces
        jsr number_text
        jsr add
        lda what
        ldx what + 1
        jsr add
        jmp end_line
@none:  rts

; items: "  WHAT item" for each item on the list at receipt + X.
;   Takes:   X = the list's offset; A/Y = WHAT (low/high). Changes A, X, Y; zp_t0, zp_t1.
items:  sta what
        sty what + 1
        stx list
        lda #0
        sta entry
@item:  ldx list
        lda entry
        cmp receipt, x
        bcs @done
        jsr start_line
        lda what
        ldx what + 1
        jsr add
        lda entry                   ; the item's name, or ? past the registry's
        asl a
        clc
        adc list
        tax
        lda receipt + 2, x
        bne @unknown
        lda receipt + 1, x
        cmp #ITEM_COUNT
        bcs @unknown
        tax
        lda item_lo, x
        pha
        lda item_hi, x
        tax
        pla
        jmp @name
@unknown:
        lda #<unknown
        ldx #>unknown
@name:  jsr add
        jsr end_line
        inc entry
        jmp @item
@done:  rts

; row: a line of text as it is, into the log (leading spaces and all), and its end.
; Takes A/X. Changes A, X, Y; zp_t0, zp_t1.
row:    pha
        jsr start_line
        pla
        jsr add
        ; (on into end_line)

; end_line: the line built (start_line, add, put) into the story log, a character at a
; time, and a newline. Changes A, X, Y.
end_line:
        lda #10
        jsr put
        lda #0
        ldx built
        sta line, x
        lda #<line
        ldx #>line
        jmp log_chars

; start_line: an empty line. Changes nothing but `built`. Keeps A, X, Y.
start_line:
        pha
        lda #0
        sta built
        pla
        rts

; two_spaces: "  " onto the line. Changes A, X.
two_spaces:
        lda #' '
        jsr put
        ; (on into put)

; put: A onto the line. Changes X.
put:    ldx built
        sta line, x
        inc built
        rts

; add: ASCII (A/X, ending in 0) onto the line. Changes A, X, Y; zp_t0, zp_t1.
add:    sta zp_t0
        stx zp_t1
        ldy #0
@char:  lda (zp_t0), y
        beq @done
        jsr put
        iny
        bne @char
@done:  rts

complete_line:  .byte "~ Departure complete ~", 0
failed_line:    .byte "~ Departure failed ~", 0
nothing:        .byte 0
your_receipt:   .byte "Your receipt:", 0
xp:             .byte " XP", 0
debt_paid:      .byte " Debt paid", 0
debt_added:     .byte " Debt added", 0
gained:         .byte "  Gained: ", 0
lost:           .byte "  Lost: ", 0
one_echo:       .byte " Echo", 0
echoes:         .byte " Echoes", 0
follow:         .byte " will follow you.", 0
unknown:        .byte "?", 0
your_stamp:     .byte "Your Travel Stamp. Type it in at the Waystation to have this trip "
                .byte "stamped into your Passport:", 10, 0
no_stamp:       .byte "You travelled without a Boarding Pass, so this trip can't be "
                .byte "stamped.", 10, 0
scan:           .byte "Or scan the code above.", 10, 0

        .segment "BSS"
what:           .res 2
list:           .res 1
entry:          .res 1
built:          .res 1
line:           .res 48
stamp:          .res 84 + 1         ; the longest stamp, and its 0
