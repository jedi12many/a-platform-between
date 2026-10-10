; The rules a trip needs (docs/rules-v0.md; the C version is core/src/rules.c and rng.c,
; and this gives the same numbers): the dice, a check, a skill's rating, the most health,
; and XP.

        .include "zp.inc"
        .include "char.inc"

        .export rng_seed, rng_next, d100, check, resolve, skill_rating, health_max
        .export xp_award, gain_xp
        .export rng, chk_roll, chk_total, chk_tn, chk_result
        .import traveler, skill_stat
        .importzp SKILL_COUNT

RATING_MAX      = 100
COST_MARGIN     = 20
LEVEL_MAX       = 100
XP_PER_LEVEL    = 100
FAIL            = 0
COST            = 1
SUCCESS         = 2
CRIT            = 3

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; rng_seed: the dice from a seed (0 would lock them: it's $ACE1 instead).
;   Takes:   A/X = the seed (low/high).
;   Changes: A.
rng_seed:
        sta rng
        stx rng + 1
        ora rng + 1
        bne @done
        lda #$E1
        sta rng
        lda #$AC
        sta rng + 1
@done:  rts

; ----------------------------------------------------------------------------------------
; rng_next: the next number from xorshift16 (7, 9, 8): x ^= x << 7; x ^= x >> 9;
; x ^= x << 8.
;   After:   A/X = it (low/high), and rng.
;   Changes: A, X.
rng_next:
        lda rng + 1                 ; x << 7: high = high bit 0 to 7, low bit 1-7 to 0-6
        lsr a                       ; (C = high's bit 0)
        lda rng
        ror a                       ; A = high bit 0, then low >> 1: the new high
        tax
        lda #0
        ror a                       ; A = low bit 0 at bit 7: the new low
        eor rng
        sta rng
        txa
        eor rng + 1
        sta rng + 1
        lsr a                       ; x >> 9: high >> 1, into low
        eor rng
        sta rng
        eor rng + 1                 ; x << 8: low into high
        sta rng + 1
        tax
        lda rng
        rts

; ----------------------------------------------------------------------------------------
; d100: 1-100, each as likely: the top 7 bits, 100-127 rolled again.
;   After:   A = the roll.
;   Changes: A, X.
d100:
        jsr rng_next
        txa
        lsr a
        cmp #100
        bcs d100
        adc #1                      ; (C clear)
        rts

; ----------------------------------------------------------------------------------------
; check: d100 + a rating against a target number (apb_check, with no bonus).
;   Takes:   A = the rating (0-255); X = the TN (0-255).
;   After:   A = chk_result: FAIL 0, COST 1, SUCCESS 2, CRIT 3; chk_roll, chk_total,
;            chk_tn (16-bit) as rolled.
;   Changes: A, X.
check:
        sta zp_rule
        stx chk_tn
        lda #0
        sta chk_tn + 1
        jsr d100
        sta chk_roll
        clc
        adc zp_rule
        sta chk_total
        lda #0
        adc #0
        sta chk_total + 1
        ; (on into resolve)

; ----------------------------------------------------------------------------------------
; resolve: a roll's outcome (apb_resolve): a 1 fails and 100 crits, whatever the total;
; over the TN, a success (a crit when the roll is a multiple of 11); within 20 of it, a
; success at a cost; else a fail.
;   Takes:   chk_roll; chk_total and chk_tn (16 bits each).
;   After:   A = chk_result.
;   Changes: A; zp_rule.
resolve:
        lda chk_roll
        cmp #2
        bcc @fail
        cmp #100
        bcs @crit
        lda chk_tn                  ; total > tn?
        cmp chk_total
        lda chk_tn + 1
        sbc chk_total + 1
        bcs @not_over               ; (tn >= total)
        lda chk_roll                ; success; a crit when the roll is a multiple of 11
@eleven:
        cmp #11
        bcc @rest
        sbc #11
        jmp @eleven
@rest:  cmp #0
        beq @crit
        lda #SUCCESS
        bne @done                   ; (always)
@not_over:                          ; total > tn - 20: at a cost
        lda chk_tn
        sec
        sbc #COST_MARGIN
        sta zp_rule
        lda chk_tn + 1
        sbc #0
        sta zp_rule + 1
        bmi @cost                   ; (tn - 20 below 0: any total is over it)
        lda zp_rule
        cmp chk_total
        lda zp_rule + 1
        sbc chk_total + 1
        bcc @cost                   ; (tn - 20 < total)
@fail:  lda #FAIL
        beq @done                   ; (always)
@cost:  lda #COST
        bne @done                   ; (always)
@crit:  lda #CRIT
@done:  sta chk_result
        rts

; ----------------------------------------------------------------------------------------
; skill_rating: a skill's rating: its stat / 2 + its training, 100 at most (apb_skill).
;   Takes:   A = the skill (0 to SKILL_COUNT - 1; any other: 0).
;   After:   A = the rating.
;   Changes: A, X, Y.
skill_rating:
        cmp #SKILL_COUNT
        bcc @skill
        lda #0
        rts
@skill: tax
        ldy skill_stat, x
        lda traveler + CH_STATS, y
        lsr a
        clc
        adc traveler + CH_TRAINING, x
        bcs @max                    ; (over 255)
        cmp #RATING_MAX + 1
        bcc @done
@max:   lda #RATING_MAX
@done:  rts

; ----------------------------------------------------------------------------------------
; health_max: 10 + Grit / 4 + 2 per level (apb_health_max; 8 bits, as the C keeps it).
;   After:   A = it.
;   Changes: A.
health_max:
        lda traveler + CH_STATS + 2     ; Grit
        lsr a
        lsr a
        clc
        adc #10
        adc traveler + CH_LEVEL
        adc traveler + CH_LEVEL
        rts

; ----------------------------------------------------------------------------------------
; xp_award: the XP a reward gives at the traveler's level (apb_xp_award): all of it up to
; the Departure's level band, a tenth less for each level over, none from 10 over.
;   Takes:   A = the base (0-255); X = the band's top level.
;   After:   zp_rule = the award (16 bits).
;   Changes: A, X, Y.
xp_award:
        sta zp_rule
        lda #0
        sta zp_rule + 1
        stx xp_band
        lda traveler + CH_LEVEL
        cmp xp_band
        beq @all
        bcc @all
        sec
        sbc xp_band                 ; over
        cmp #10
        bcc @part
        lda #0
        sta zp_rule
        rts
@part:  eor #$FF                    ; 10 - over: 1-9
        sec
        adc #10
        tay
        lda zp_rule                 ; base x (10 - over) ...
        sta xp_base
        lda #0
        sta zp_rule
@times: lda zp_rule
        clc
        adc xp_base
        sta zp_rule
        bcc @next
        inc zp_rule + 1
@next:  dey
        bne @times
        ldx #0                      ; ... / 10, by taking tens away
@tens:  lda zp_rule
        sec
        sbc #10
        tay
        lda zp_rule + 1
        sbc #0
        bcc @tenths
        sta zp_rule + 1
        sty zp_rule
        inx
        bne @tens                   ; (under 230: always)
@tenths:
        stx zp_rule
        lda #0
        sta zp_rule + 1
@all:   rts

; ----------------------------------------------------------------------------------------
; gain_xp: XP to the traveler, levelling up for every 100 (apb_gain_xp): each level, a
; stat point and 1 + Wits / 20 skill points (each to 255 at most). At level 100, XP is 0.
;   Takes:   zp_rule = the XP (16 bits).
;   Changes: A, X; zp_rule.
gain_xp:
        lda traveler + CH_LEVEL
        cmp #LEVEL_MAX
        bcs @top
        lda zp_rule                 ; amount + xp, to 65535 at most
        clc
        adc traveler + CH_XP
        sta zp_rule
        bcc @level
        inc zp_rule + 1
        bne @level
        lda #$FF
        sta zp_rule
        sta zp_rule + 1
@level: lda zp_rule + 1             ; 100 or more, and under level 100: a level
        bne @up
        lda zp_rule
        cmp #XP_PER_LEVEL
        bcc @rest
@up:    lda traveler + CH_LEVEL
        cmp #LEVEL_MAX
        bcs @rest
        lda zp_rule
        sec
        sbc #XP_PER_LEVEL
        sta zp_rule
        bcs @nb
        dec zp_rule + 1
@nb:    inc traveler + CH_LEVEL
        inc traveler + CH_STAT_POINTS
        bne @skills
        dec traveler + CH_STAT_POINTS   ; (255 at most)
@skills:
        lda traveler + CH_STATS + 3     ; 1 + Wits / 20
        ldx #0
@twenties:
        cmp #20
        bcc @points
        sbc #20
        inx
        bne @twenties               ; (always)
@points:
        inx
        txa
        clc
        adc traveler + CH_SKILL_POINTS
        bcc @keep
        lda #$FF
@keep:  sta traveler + CH_SKILL_POINTS
        jmp @level
@rest:  lda traveler + CH_LEVEL
        cmp #LEVEL_MAX
        bcs @top
        lda zp_rule
        sta traveler + CH_XP
        rts
@top:   lda #0
        sta traveler + CH_XP
        rts

        .segment "BSS"
rng:            .res 2
chk_roll:       .res 1
chk_total:      .res 2
chk_tn:         .res 2
chk_result:     .res 1
xp_band:        .res 1
xp_base:        .res 1
