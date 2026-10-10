; The Travel Stamp (docs/boarding.md, "Travel Stamp format"; the C version is
; core/src/passport.c's apb_stamp_encode, and the Python reference that reads it
; tools/passport/stamp.py): a trip's receipt as a password for the Waystation.

        .include "zp.inc"
        .include "receipt.inc"

        .export stamp_encode
        .import receipt, bits_clear, bits_put, pw_close

STAMP_VERSION   = 1
ID_TOP          = 4                 ; an id's high byte under this: it fits 10 bits

        .segment "ENDING"

; ----------------------------------------------------------------------------------------
; stamp_encode: the receipt (reward.s) as a Travel Stamp: its version, the Departure, the
; ticket, the outcome, the XP, the Debt (added or paid), the items gained and lost, the
; Echoes; a CRC; in the Passport's alphabet and lines, no spaces.
;   Takes:   A/X = where the text goes (low/high): 84 symbols and a 0 at most.
;   After:   C clear, the text there; or C set: an id that doesn't fit its bits (no stamp).
;   Changes: A, X, Y; password.s's zero page; zp_t0-zp_t3.
stamp_encode:
        sta stamp_to
        stx stamp_to + 1
        jsr fits
        bcc @fits
        rts
@fits:  jsr bits_clear
        lda #STAMP_VERSION
        ldx #0
        ldy #4
        jsr put
        ldx #R_DEPARTURE
        jsr put16
        ldx #R_TICKET + 2           ; the ticket: its high half first
        jsr put16
        ldx #R_TICKET
        jsr put16
        lda receipt + R_OUTCOME
        beq @outcome
        lda #1
@outcome:
        ldx #0
        ldy #1
        jsr put
        ldx #R_XP
        jsr put16
        lda receipt + R_DEBT_ADDED  ; the Debt: 1 and what was added, or 0 and what was
        ora receipt + R_DEBT_ADDED + 1  ; paid
        beq @paid
        lda #1
        ldx #0
        ldy #1
        jsr put
        ldx #R_DEBT_ADDED
        jsr put16
        jmp @lists
@paid:  lda #0
        tax
        ldy #1
        jsr put
        ldx #R_DEBT_PAID
        jsr put16
@lists: ldx #R_GAINED
        jsr put_items
        ldx #R_LOST
        jsr put_items
        lda receipt + R_ECHOES      ; the Echoes: id, state, state at boarding
        ldx #0
        ldy #4
        jsr put
        lda #0
        sta zp_t3                   ; the entry
@echo:  lda zp_t3
        cmp receipt + R_ECHOES
        bcs @close
        asl a
        asl a
        sta zp_t2                   ; its offset: 4 bytes each
        tax
        lda receipt + R_ECHOES + 1, x
        pha
        lda receipt + R_ECHOES + 2, x
        tax
        pla
        ldy #10
        jsr put
        ldx zp_t2
        lda receipt + R_ECHOES + 3, x
        ldx #0
        ldy #2
        jsr put
        ldx zp_t2
        lda receipt + R_ECHOES + 4, x
        ldx #0
        ldy #2
        jsr put
        inc zp_t3
        jmp @echo
@close: lda stamp_to
        ldx stamp_to + 1
        jsr pw_close
        clc
        rts

; fits: C clear if every id on the receipt fits its 10 bits, and every list holds 8 at
; most. Changes A, X, Y.
fits:   ldx #R_GAINED
        jsr items_fit
        bcs @out
        ldx #R_LOST
        jsr items_fit
        bcs @out
        lda receipt + R_ECHOES
        cmp #RECEIPT_MAX + 1
        bcs @out
        tay
        ldx #0
@echo:  dey
        bmi @fine
        lda receipt + R_ECHOES + 2, x
        cmp #ID_TOP
        bcs @out
        inx
        inx
        inx
        inx
        bne @echo                   ; (always)
@fine:  clc
@out:   rts

; items_fit: the list at receipt + X (a count, then ids of 2 bytes): C clear if it fits.
; Changes A, X, Y.
items_fit:
        lda receipt, x
        cmp #RECEIPT_MAX + 1
        bcs @out
        tay
@item:  dey
        bmi @fine
        lda receipt + 2, x          ; an id's high byte
        cmp #ID_TOP
        bcs @out
        inx
        inx
        bne @item                   ; (always)
@fine:  clc
@out:   rts

; put_items: the list at receipt + X: its count (4 bits), then each id (10). Changes A,
; X, Y; zp_t2, zp_t3.
put_items:
        stx zp_t2
        lda receipt, x
        sta zp_t3
        ldx #0
        ldy #4
        jsr put
@item:  lda zp_t3
        beq @done
        dec zp_t3
        ldx zp_t2
        lda receipt + 1, x
        pha
        lda receipt + 2, x
        tax
        pla
        ldy #10
        jsr put
        inc zp_t2
        inc zp_t2
        jmp @item
@done:  rts

; put16: the receipt's 2 bytes at receipt + X (low, high) as 16 bits. Changes A, X, Y.
put16:  lda receipt, x
        pha
        lda receipt + 1, x
        tax
        pla
        ldy #16
        ; (on into put)

; put: A/X (low/high) as Y bits. Changes A, X, Y; zp_pw_value, zp_pw_n.
put:    sta zp_pw_value
        stx zp_pw_value + 1
        tya
        jmp bits_put

        .segment "BSS"
stamp_to:       .res 2
