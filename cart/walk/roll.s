; The dice, and a roll's outcome (docs/rules-v0.md's core roll; the C version's
; core/src/rng.c and rules.c, as cart/rules.s has them for the cartridge), for the walking
; engine's seeing: its TNs can be anything from below 0 to some 400, so they're signed.

        .include "zp.inc"

        .export roll_seed, roll_next, roll_d100, roll_resolve, roll_rng
        .export ROLL_FAIL, ROLL_COST, ROLL_SUCCESS, ROLL_CRIT

ROLL_FAIL       = 0
ROLL_COST       = 1
ROLL_SUCCESS    = 2
ROLL_CRIT       = 3
COST_MARGIN     = 20

        .segment "SEEING"         ; (run from $E000 in the walk: walk.cfg)

; ----------------------------------------------------------------------------------------
; roll_seed: the dice from a seed (0 would lock them: it's $ACE1 instead).
;   Takes:   A/X = the seed (low/high).
;   Changes: A.
roll_seed:
        sta roll_rng
        stx roll_rng + 1
        ora roll_rng + 1
        bne :+
        lda #$E1
        sta roll_rng
        lda #$AC
        sta roll_rng + 1
:       rts

; ----------------------------------------------------------------------------------------
; roll_next: the next number from xorshift16 (7, 9, 8): x ^= x << 7; x ^= x >> 9;
; x ^= x << 8.
;   After:   A/X = it (low/high), and roll_rng.
;   Changes: A, X.
roll_next:
        lda roll_rng + 1            ; x << 7: high = high bit 0 to 7, low bit 1-7 to 0-6
        lsr a
        lda roll_rng
        ror a
        tax
        lda #0
        ror a
        eor roll_rng
        sta roll_rng
        txa
        eor roll_rng + 1
        sta roll_rng + 1
        lsr a                       ; x >> 9: high >> 1, into low
        eor roll_rng
        sta roll_rng
        eor roll_rng + 1            ; x << 8: low into high
        sta roll_rng + 1
        tax
        lda roll_rng
        rts

; ----------------------------------------------------------------------------------------
; roll_d100: 1-100, each as likely: the top 7 bits, 100-127 rolled again.
;   After:   A = the roll.
;   Changes: A, X.
roll_d100:
        jsr roll_next
        txa
        lsr a
        cmp #100
        bcs roll_d100
        adc #1                      ; (C clear)
        rts

; ----------------------------------------------------------------------------------------
; roll_resolve: a roll's outcome (apb_resolve): a 1 fails and 100 crits, whatever the
; total; over the TN, a success (a crit when the roll is a multiple of 11); within 20 of
; it, a success at a cost; else a fail.
;   Takes:   A = the roll (1-100); zp_see_a = the total (16 bits, 0-355);
;            zp_see_tn = the TN (16 bits, signed).
;   After:   A = ROLL_FAIL, ROLL_COST, ROLL_SUCCESS or ROLL_CRIT.
;   Changes: A, X; zp_see_t.
roll_resolve:
        cmp #2
        bcc @fail
        cmp #100
        bcs @crit
        sta zp_see_t
        sec                         ; X/A = total - TN: signed (-600 to 400)
        lda zp_see_a
        sbc zp_see_tn
        tax
        lda zp_see_a + 1
        sbc zp_see_tn + 1
        bmi @below                  ; (negative: total <= TN - 1)
        bne @over                   ; (256 or more)
        cpx #0
        beq @cost                   ; (0: total = TN, not over it)
@over:  lda zp_see_t                ; a success; a crit when the roll is a multiple of 11
:       cmp #11
        bcc :+
        sbc #11
        bcs :-                      ; (always: C set after a subtract that didn't borrow)
:       cmp #0
        beq @crit
        lda #ROLL_SUCCESS
        rts
@below: cmp #$FF                    ; total - TN in -19..-1: within 20, at a cost
        bne @fail
        cpx #<-19
        bcs @cost
@fail:  lda #ROLL_FAIL
        rts
@cost:  lda #ROLL_COST
        rts
@crit:  lda #ROLL_CRIT
        rts

        .segment "BSS"

roll_rng:   .res 2              ; the dice: xorshift16's state
