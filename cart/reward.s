; What a trip gives and takes (the C version is vm/vm.c's give, take, award_xp, first_pay,
; receipt_item and receipt_echo, and core/src/echo.c): items into the pack and out of it,
; XP, Debt, Echoes; and the receipt of it all (docs/boarding.md), net, for the Travel
; Stamp. A reward instruction pays once a trip, however often the story passes it.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"
        .include "receipt.inc"

        .export reward_reset, first_pay, give, take, carrying, award_xp, set_debt
        .export echo_get, echo_set, rewind_echoes, receipt
        .import traveler, kind, level_max, car_index, xp_award, gain_xp, item_tier
        .import echo_dep_lo, echo_dep_hi
        .importzp ECHO_COUNT

PAID_MAX        = 32                ; reward instructions a trip remembers (the compiler's
                                    ; limit: APB_VM_REWARD_SITES)
SLOTS           = 6                 ; the pack's, and what's equipped (APB_PACK_SLOTS)
ECHO_SLOTS      = 8                 ; a traveler's Echoes (APB_ECHO_SLOTS)
ECHO_ROOM       = 15 * 3            ; the record's room for them (char.inc)
BRANCH_GIVES    = 3                 ; items a Branch Line may give a trip, tier 3 at most
BRANCH_TIER     = 3

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; reward_reset: a clean receipt, nothing paid yet.
;   Changes: A, X.
reward_reset:
        lda #0
        ldx #R_SIZE - 1
@clear: sta receipt, x
        dex
        bpl @clear
        sta paid_count
        sta gives
        rts

; ----------------------------------------------------------------------------------------
; first_pay: the reward instruction at A/X (its address in the car) reached for the first
; time this trip? Then it goes on the list.
;   After:   C clear: pay it; C set: paid before (or the list is full: nothing more is).
;   Changes: A, X, Y.
first_pay:
        sta at
        stx at + 1
        ldy #0
@paid:  cpy paid_count
        beq @new
        lda paid_lo, y
        cmp at
        bne @next
        lda paid_hi, y
        cmp at + 1
        bne @next
        lda paid_car, y
        cmp car_index
        beq @before
@next:  iny
        bne @paid                   ; (always)
@new:   cpy #PAID_MAX
        bcs @before
        lda at
        sta paid_lo, y
        lda at + 1
        sta paid_hi, y
        lda car_index
        sta paid_car, y
        inc paid_count
        clc
        rts
@before:
        sec
        rts

; ----------------------------------------------------------------------------------------
; give: item A/X (low/high; one with a tier) into the first empty pack slot; with none
; empty, the lost-and-found keeps it: it's on the receipt either way. A Branch Line gives
; tier 3 at most, 3 a trip.
;   Changes: A, X, Y; zp_t0-zp_t3.
give:   sta zp_t0
        stx zp_t1
        lda kind
        cmp #1
        bne @give
        ldx zp_t0
        lda item_tier, x
        cmp #BRANCH_TIER + 1
        bcs @out
        lda gives
        cmp #BRANCH_GIVES
        bcs @out
        inc gives
@give:  ldx #0
@slot:  lda traveler + CH_PACK + 1, x
        cmp #EMPTY_SLOT
        beq @into
        inx
        inx
        cpx #SLOTS * 2
        bne @slot
        beq @earned                 ; (always)
@into:  lda zp_t0
        sta traveler + CH_PACK, x
        lda zp_t1
        sta traveler + CH_PACK + 1, x
@earned:
        lda #R_GAINED
        ldx #R_LOST
        jmp receipt_item
@out:   rts

; take: item A/X out of the pack, or else from what's equipped: the first slot holding it.
;   Changes: A, X, Y; zp_t0-zp_t3.
take:   jsr find_item
        bcs @out
        lda #EMPTY_SLOT
        sta traveler, x
        sta traveler + 1, x
        lda #R_LOST
        ldx #R_GAINED
        jmp receipt_item
@out:   rts

; carrying: A = 1 if item A/X is in the pack or equipped, else 0.
;   Changes: A, X; zp_t0, zp_t1.
carrying:
        jsr find_item
        lda #0
        bcs @no
        lda #1
@no:    rts

; find_item: item A/X's slot, the pack's first: X = its offset in `traveler`, C clear; or
; C set. An empty slot holds item 0, as the C keeps it. Changes A, X; zp_t0, zp_t1.
find_item:
        sta zp_t0
        stx zp_t1
        ldx #CH_PACK
        jsr @look
        bcc @found
        ldx #CH_EQUIPPED
@look:  lda #SLOTS
        sta left
@slot:  lda traveler + 1, x
        cmp #EMPTY_SLOT
        bne @item
        lda zp_t0                   ; empty: item 0
        ora zp_t1
        beq @found
        bne @next                   ; (always)
@item:  cmp zp_t1
        bne @next
        lda traveler, x
        cmp zp_t0
        beq @found
@next:  inx
        inx
        dec left
        bne @slot
        sec
        rts
@found: clc
        rts

; receipt_item: item zp_t0/zp_t1 onto the receipt's list at A (R_GAINED or R_LOST), unless
; it's on the other list, at X: an item given back after it was taken, or taken back after
; it was given, cancels out (that list's last entry takes its place). 8 a list at most.
;   Changes: A, X, Y; zp_t2, zp_t3.
receipt_item:
        sta zp_t2
        stx zp_t3
        ldy receipt, x              ; the other list's count
        beq @add
@look:  dey                         ; its entry y: at X + 1 + 2y
        tya
        asl a
        sec
        adc zp_t3
        tax
        lda receipt, x
        cmp zp_t0
        bne @not
        lda receipt + 1, x
        cmp zp_t1
        beq @cancel
@not:   tya
        bne @look
@add:   ldx zp_t2
        lda receipt, x
        cmp #RECEIPT_MAX
        bcs @full
        inc receipt, x
        asl a
        sec
        adc zp_t2
        tax
        lda zp_t0
        sta receipt, x
        lda zp_t1
        sta receipt + 1, x
@full:  rts
@cancel:
        stx zp_t2                   ; (where it was)
        ldx zp_t3
        dec receipt, x              ; the last entry: at X + 1 + 2 x (count - 1)
        lda receipt, x
        asl a
        sec
        adc zp_t3
        tax
        lda receipt, x
        ldy receipt + 1, x
        ldx zp_t2
        sta receipt, x
        tya
        sta receipt + 1, x
        rts

; ----------------------------------------------------------------------------------------
; award_xp: XP from a reward of A: on a Branch Line, all of it up to the level band and
; none past it; else as the rules scale it (apb_xp_award). Onto the receipt, and the
; traveler (who may level up).
;   Changes: A, X, Y; zp_rule.
award_xp:
        ldx kind
        cpx #1
        bne @scaled
        ldx traveler + CH_LEVEL
        cpx level_max
        beq @all
        bcc @all
        lda #0
@all:   sta zp_rule
        lda #0
        sta zp_rule + 1
        beq @award                  ; (always)
@scaled:
        ldx level_max
        jsr xp_award
@award: lda zp_rule
        clc
        adc receipt + R_XP
        sta receipt + R_XP
        lda zp_rule + 1
        adc receipt + R_XP + 1
        sta receipt + R_XP + 1
        jmp gain_xp

; ----------------------------------------------------------------------------------------
; set_debt: the traveler's Debt: set (Y = 0), added to (1, to 65535 at most), paid down
; (2, to 0 at least).
;   Takes:   A/X = the amount (low/high); Y = how.
;   Changes: A, X.
set_debt:
        cpy #1
        beq @add
        bcs @pay
        sta traveler + CH_DEBT
        stx traveler + CH_DEBT + 1
        rts
@add:   clc
        adc traveler + CH_DEBT
        sta traveler + CH_DEBT
        txa
        adc traveler + CH_DEBT + 1
        sta traveler + CH_DEBT + 1
        bcc @done
        lda #$FF
        sta traveler + CH_DEBT
        sta traveler + CH_DEBT + 1
@done:  rts
@pay:   sta at
        stx at + 1
        lda traveler + CH_DEBT
        sec
        sbc at
        tax
        lda traveler + CH_DEBT + 1
        sbc at + 1
        bcs @paid
        lda #0
        tax
@paid:  stx traveler + CH_DEBT
        sta traveler + CH_DEBT + 1
        rts

; ----------------------------------------------------------------------------------------
; echo_get: Echo A/X's state on the traveler (apb_echo_get): 0 if it isn't set.
;   After:   A = the state; X = its entry's offset in CH_ECHOES and C clear, or C set.
;   Changes: A, X, Y; zp_t0, zp_t1.
echo_get:
        sta zp_t0
        stx zp_t1
        ; (on into echo_look)

; echo_look: as echo_get, for Echo zp_t0/zp_t1. Changes A, X, Y.
echo_look:
        ldx #0
        ldy #0
@echo:  cpy traveler + CH_ECHO_COUNT
        bcs @none
        lda traveler + CH_ECHOES, x
        cmp zp_t0
        bne @next
        lda traveler + CH_ECHOES + 1, x
        cmp zp_t1
        bne @next
        lda traveler + CH_ECHOES + 2, x
        clc
        rts
@next:  inx
        inx
        inx
        iny
        bne @echo                   ; (always)
@none:  lda #0
        sec
        rts

; echo_set: Echo A/X to state Y (1-3), with the receipt told first (its state at boarding
; kept from the first change): its entry if it has one, else a new one at the end, the
; oldest going if all 8 are taken (apb_echo_set).
;   Changes: A, X, Y; zp_t0-zp_t3.
echo_set:
        sty zp_t2
        jsr echo_get                ; (zp_t0/zp_t1: the Echo)
        sta zp_t3                   ; its state at boarding, if this is the first change
        jsr receipt_echo
        jsr echo_look
        bcs @new
        lda zp_t2
        sta traveler + CH_ECHOES + 2, x
        rts
@new:   lda traveler + CH_ECHO_COUNT
        cmp #ECHO_SLOTS
        bcc @room
        ldx #0
        jsr echo_remove
@room:  lda traveler + CH_ECHO_COUNT
        asl a
        adc traveler + CH_ECHO_COUNT
        tax
        lda zp_t0
        sta traveler + CH_ECHOES, x
        lda zp_t1
        sta traveler + CH_ECHOES + 1, x
        lda zp_t2
        sta traveler + CH_ECHOES + 2, x
        inc traveler + CH_ECHO_COUNT
        rts

; receipt_echo: Echo zp_t0/zp_t1 going to state zp_t2, onto the receipt: its entry's
; state, or a new entry (8 at most) with zp_t3, its state at boarding. Changes A, X, Y.
receipt_echo:
        ldx #0
        ldy #0
@look:  cpy receipt + R_ECHOES
        bcs @add
        lda receipt + R_ECHOES + 1, x
        cmp zp_t0
        bne @next
        lda receipt + R_ECHOES + 2, x
        cmp zp_t1
        bne @next
        lda zp_t2
        sta receipt + R_ECHOES + 3, x
        rts
@next:  inx
        inx
        inx
        inx
        iny
        bne @look                   ; (always)
@add:   cpy #RECEIPT_MAX
        bcs @full
        lda zp_t0
        sta receipt + R_ECHOES + 1, x
        lda zp_t1
        sta receipt + R_ECHOES + 2, x
        lda zp_t2
        sta receipt + R_ECHOES + 3, x
        lda zp_t3
        sta receipt + R_ECHOES + 4, x
        inc receipt + R_ECHOES
@full:  rts

; echo_remove: the Echo entry at offset X out, the ones after it up a place. Changes A, X.
echo_remove:
@move:  lda traveler + CH_ECHOES + 3, x
        sta traveler + CH_ECHOES, x
        inx
        cpx #ECHO_ROOM - 3
        bcc @move
        dec traveler + CH_ECHO_COUNT
        rts

; rewind_echoes: the traveler's Echoes from Departure A/X, gone (apb_rewind_echoes): a
; Rewind plays it as if for the first time.
;   Changes: A, X, Y.
rewind_echoes:
        sta at
        stx at + 1
        ldx #0
        ldy #0
@echo:  cpy traveler + CH_ECHO_COUNT
        bcs @done
        lda traveler + CH_ECHOES + 1, x     ; one of the registry's Echoes?
        bne @next
        lda traveler + CH_ECHOES, x
        beq @next
        cmp #<ECHO_COUNT
        bcs @next
        sty keep_y
        tay
        lda echo_dep_lo, y
        cmp at
        bne @not
        lda echo_dep_hi, y
        cmp at + 1
        bne @not
        ldy keep_y                  ; this Departure's: out (and look at x again)
        txa
        pha
        jsr echo_remove
        pla
        tax
        jmp @echo
@not:   ldy keep_y
@next:  inx
        inx
        inx
        iny
        bne @echo                   ; (always)
@done:  rts

        .segment "BSS"
receipt:        .res R_SIZE
paid_count:     .res 1
paid_lo:        .res PAID_MAX
paid_hi:        .res PAID_MAX
paid_car:       .res PAID_MAX
gives:          .res 1
at:             .res 2
left:           .res 1
keep_y:         .res 1
