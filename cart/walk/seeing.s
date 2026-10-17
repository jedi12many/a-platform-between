; Seeing and being seen (docs/open-floors.md, Being seen): the rules lab's core/next/seeing.c
; in 6502, held to tools/rules/seeing.py roll for roll (tests/seeing/run_seeing.py). The
; looker rolls d100 + its Notice (a band's, its Sense); whoever might be seen sets the TN:
; 50 + Stealth if sneaking or hiding, 80 if not; light, distance, cover and alertness move
; it. A party is a group: looking, its others roll first, each taking 10 off the best's TN
; or putting 10 on; sneaking, they roll Stealth against 100, putting 10 on or taking it off.
;
; Each step of the leader onto a square, every band is checked in the floor's order: the
; party looks (if a check is due), then the band looks back (if one is due). A check is
; due when the other is in range and in sight and the looker hasn't checked it before, or
; it's 4 squares nearer than at its last check; next to each other, seen without a roll.
; A line is only traced for a check that's due, so a step costs little. Every die is
; written to the log (SEE_LOG: for the tests).

        .include "zp.inc"
        .include "walk.inc"

        .export see_prepare, see_step
        .export see_light, see_n, see_notice, see_stealth, see_sneak, see_lamp
        .export see_bands, b_x, b_y, b_sense, b_stealth, b_hiding, b_spotted, b_seen, b_alert
        .export b_plast, b_blast, see_x, see_y, see_fight, see_ambush, see_log_n, see_log_full
        .import roll_d100, roll_resolve, sq_row_lo, sq_row_hi, terrain
        .importzp ROLL_FAIL, ROLL_COST, ROLL_SUCCESS, ROLL_CRIT

PARTY_MAX       = 4
BASE            = 50            ; a defense's TN: 50 + a rating
OPEN_TN         = 80            ; not sneaking, not hiding
HELPER_TN       = 100           ; a sneaking party's others roll against this
HELP            = 10
NONE            = $FF           ; a distance never checked at
BLOCKED_LINE    = $FF
DAY             = 0
DUSK            = 1
NIGHT           = 2
T_WALL          = 1             ; the battle's terrain (tools/art.py's TERRAIN)
T_COVER         = 4
; An event in the log: its kind (0 the party looks, 1 the band) + 2 if there was no roll,
; the band, the distance, what came of it (0 not yet, 1 heard, 2 spotted, 3 seen), how
; many dice; then each die: the roll, the total (2), the TN (2), the outcome.
OUT_NOT_YET     = 0
OUT_HEARD       = 1
OUT_SPOTTED     = 2
OUT_SEEN        = 3
EV_SIZE         = 5 + 6 * PARTY_MAX

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; see_prepare: what doesn't change from step to step: the party's best looker and sneak
; (the first of the highest), its sight range and each band's (Notice / 5 squares, doubled
; by day, halved at night, at least 1).
;   Before:  see_light, see_n, see_notice, see_stealth, see_bands and the bands' numbers set.
;   Changes: A, X, Y.
see_prepare:
        ldy #0                      ; the best looker
        ldx #1
@n:     cpx see_n
        bcs @n_done
        lda see_notice, x
        cmp see_notice, y
        beq :+
        bcc :+
        txa
        tay
:       inx
        bne @n                      ; (always)
@n_done:
        sty top_notice
        ldy #0                      ; the best sneak
        ldx #1
@s:     cpx see_n
        bcs @s_done
        lda see_stealth, x
        cmp see_stealth, y
        beq :+
        bcc :+
        txa
        tay
:       inx
        bne @s
@s_done:
        sty top_stealth
        ldy top_notice
        lda see_notice, y
        jsr range_of
        sta party_range
        ldx see_bands
        beq @done
@band:  dex
        lda b_sense, x
        jsr range_of
        sta b_range, x
        txa
        bne @band
@done:  rts

; A = the sight range of a rating A.
range_of:
        ldy #0                      ; A / 5
:       cmp #5
        bcc :+
        sbc #5
        iny
        bne :-                      ; (always)
:       tya
        ldy see_light
        cpy #DAY
        bne :+
        asl a
:       cpy #NIGHT
        bne :+
        lsr a
:       cmp #0
        bne :+
        lda #1
:       rts

; ----------------------------------------------------------------------------------------
; see_step: the leader has stepped onto (see_x, see_y): every band checked.
;   After:   see_fight = 1 + the band that has seen the party (and it stops there), or 0;
;            see_ambush = 1 if that band hadn't been spotted. The bands' states, and the
;            log (SEE_LOG, see_log_n events; see_log_full if they didn't all fit).
;   Changes: A, X, Y; zp_see_*.
see_step:
        lda #<SEE_LOG
        sta zp_see_log
        lda #>SEE_LOG
        sta zp_see_log + 1
        lda #0
        sta see_log_n
        sta see_log_full
        sta see_fight
        sta see_ambush
        sta band
@band:  ldx band
        cpx see_bands
        bcc :+
        rts
:       lda see_x                   ; the distance: the larger gap
        sec
        sbc b_x, x
        bcs :+
        eor #$FF
        adc #1
:       sta dist
        lda see_y
        sec
        sbc b_y, x
        bcs :+
        eor #$FF
        adc #1
:       cmp dist
        bcc :+
        sta dist
:       ; Which looks are due (the line traced only if one is).
        lda #0
        sta party_due
        lda b_spotted, x
        bne @band_due
        ldy b_plast, x
        lda party_range
        jsr due
        sta party_due
@band_due:
        ldy b_blast, x
        lda b_range, x
        jsr due
        sta band_due
        ora party_due
        beq @seen
        jsr sight
        sta line
        cmp #BLOCKED_LINE
        beq @seen
        lda party_due               ; the party looks
        beq @back
        ldx band
        lda dist
        cmp #2
        bcs :+
        lda #1                      ; next to them: spotted, no roll
        sta b_spotted, x
        lda #0 + 2
        ldy #OUT_SPOTTED
        jsr event_auto
        jmp @back
:       sta b_plast, x
        jsr party_looks
@back:  lda band_due                ; the band looks back
        beq @seen
        ldx band
        lda dist
        cmp #2
        bcs :+
        lda #1
        sta b_seen, x
        lda #1 + 2
        ldy #OUT_SEEN
        jsr event_auto
        jmp @seen
:       sta b_blast, x
        jsr band_looks
@seen:  ldx band
        lda b_seen, x
        beq @next
        inx
        stx see_fight
        dex
        lda b_spotted, x
        eor #1
        sta see_ambush
        rts
@next:  inc band
        jmp @band

; A = 1 if a check is due, else 0: A = the looker's range, Y = its last distance (NONE if
; it never looked). Due: in range, and next to them, never checked, or 4 nearer than at
; the last (dist + 4 <= last). Keeps X.
due:
        cmp dist
        bcc @no                     ; out of range
        lda dist
        cmp #2
        bcc @yes
        cpy #NONE
        beq @yes
        tya
        sec
        sbc #4
        bcc @no
        cmp dist
        bcs @yes
@no:    lda #0
        rts
@yes:   lda #1
        rts

; ----------------------------------------------------------------------------------------
; The line from the leader to band X's square (the battle engine's Bresenham): A =
; BLOCKED_LINE if a wall is on it, 1 if a cover square is (not either end), else 0.
sight:
        lda see_x
        sta lx
        lda see_y
        sta ly
        lda b_x, x
        sta tx
        lda b_y, x
        sta ty
        lda #0
        sta cover
        lda #1                      ; dx, sx
        ldy tx
        cpy lx
        bcs :+
        lda #$FF
:       sta sx
        lda tx
        sec
        sbc lx
        bcs :+
        eor #$FF
        adc #1
:       sta dx
        lda #1                      ; dy, sy
        ldy ty
        cpy ly
        bcs :+
        lda #$FF
:       sta sy
        lda ty
        sec
        sbc ly
        bcs :+
        eor #$FF
        adc #1
:       sta dy
        lda dx                      ; err = dx - dy
        sec
        sbc dy
        sta zp_see_err
        lda #0
        sbc #0
        sta zp_see_err + 1
@step:  lda lx
        cmp tx
        bne :+
        lda ly
        cmp ty
        bne :+
        lda cover                   ; there
        rts
:       lda lx                      ; not the leader's own square: what's on it
        cmp see_x
        bne @look
        lda ly
        cmp see_y
        beq @move
@look:  ldx lx
        ldy ly
        jsr terrain_at
        cmp #T_WALL
        bne :+
        lda #BLOCKED_LINE
        rts
:       cmp #T_COVER
        bne @move
        lda #1
        sta cover
@move:  lda zp_see_err              ; e2 = 2 err
        asl a
        sta zp_see_a
        lda zp_see_err + 1
        rol a
        sta zp_see_a + 1
        ; e2 > -dy: e2 + dy > 0
        lda zp_see_a
        clc
        adc dy
        tax
        lda zp_see_a + 1
        adc #0
        bmi @no_x
        bne @x
        cpx #0
        beq @no_x
@x:     lda zp_see_err              ; err -= dy; x += sx
        sec
        sbc dy
        sta zp_see_err
        lda zp_see_err + 1
        sbc #0
        sta zp_see_err + 1
        lda lx
        clc
        adc sx
        sta lx
@no_x:  ; e2 < dx: e2 - dx < 0
        lda zp_see_a
        sec
        sbc dx
        lda zp_see_a + 1
        sbc #0
        bpl @step
        lda zp_see_err              ; err += dx; y += sy
        clc
        adc dx
        sta zp_see_err
        lda zp_see_err + 1
        adc #0
        sta zp_see_err + 1
        lda ly
        clc
        adc sy
        sta ly
        jmp @step

; A = the terrain at square (X, Y).
terrain_at:
        lda sq_row_lo, y
        sta zp_see_row
        lda sq_row_hi, y
        sta zp_see_row + 1
        txa
        tay
        lda (zp_see_row), y
        and #TILE_MASK
        tax
        lda terrain, x
        rts

; ----------------------------------------------------------------------------------------
; The party looks at the band (band, dist, line).
party_looks:
        ldx band
        lda #0
        sta ev_n
        sta ev_off
        lda b_hiding, x             ; the TN: 50 + its Stealth hiding, 80 if open
        beq :+
        lda b_stealth, x
        clc
        adc #BASE
        jmp :++
:       lda #OPEN_TN
:       sta zp_see_tn
        lda #0
        sta zp_see_tn + 1
        ldy b_y, x                  ; is it in cover?
        lda b_x, x
        tax
        jsr terrain_at
        ldy #0
        cmp #T_COVER
        bne :+
        iny
:       sty in_cover
        lda #0
        sta alert
        sta lamp_now
        jsr add_mods
        lda #0                      ; the others, in party order, the best left out
        sta who
@help:  lda who
        cmp see_n
        bcs @best
        cmp top_notice
        beq @skip
        tax
        lda see_notice, x
        jsr roll_die
        jsr helper_shift            ; and the TN moved
@skip:  inc who
        jmp @help
@best:  ldx top_notice
        lda see_notice, x
        jsr roll_die
        ldx band
        ldy #OUT_NOT_YET
        cmp #ROLL_SUCCESS
        bcc :+
        lda #1
        sta b_spotted, x
        ldy #OUT_SPOTTED
        bne @end                    ; (always)
:       cmp #ROLL_COST
        bne @end
        ldy #OUT_HEARD
@end:   lda #0
        jmp event_end

; The band looks back at the party.
band_looks:
        lda #0
        sta ev_n
        sta ev_off
        sta shift
        sta shift + 1
        lda see_sneak
        beq @open
        lda #HELPER_TN              ; sneaking: the others roll Stealth against 100
        sta zp_see_tn
        lda #0
        sta zp_see_tn + 1
        sta who
@help:  lda who
        cmp see_n
        bcs @base
        cmp top_stealth
        beq @skip
        tax
        lda see_stealth, x
        jsr roll_die
        lda #1
        jsr shift_of                ; A = the shift, zp_see_t its sign
        clc
        adc shift
        sta shift
        lda zp_see_t                ; (its sign, from shift_of)
        adc shift + 1
        sta shift + 1
@skip:  inc who
        jmp @help
@base:  ldx top_stealth
        lda see_stealth, x
        clc
        adc #BASE
        jmp @tn
@open:  lda #OPEN_TN
@tn:    clc
        adc shift
        sta zp_see_tn
        lda #0
        adc shift + 1
        sta zp_see_tn + 1
        ldx see_x                   ; is the leader in cover?
        ldy see_y
        jsr terrain_at
        ldy #0
        cmp #T_COVER
        bne :+
        iny
:       sty in_cover
        ldx band
        lda b_alert, x
        sta alert
        lda see_lamp
        sta lamp_now
        jsr add_mods
        ldx band
        lda b_sense, x
        jsr roll_die
        ldx band
        ldy #OUT_NOT_YET
        cmp #ROLL_SUCCESS
        bcc :+
        lda #1
        sta b_seen, x
        ldy #OUT_SEEN
        bne @end                    ; (always)
:       cmp #ROLL_COST
        bne @end
        lda #1
        sta b_alert, x
        ldy #OUT_HEARD
@end:   lda #1
        jmp event_end

; The TN's modifiers onto zp_see_tn: dusk +10, night +20; 10 a full 4 squares past 4
; (8 or more away); cover on the line +20; in cover +10; an alert looker -20; a light
; carried at night -20.
add_mods:
        ldx see_light
        lda light_mod, x
        jsr add_tn
        lda dist
        cmp #8
        bcc :+
        sec                         ; 10 x ((d - 4) / 4)
        sbc #4
        lsr a
        lsr a
        sta zp_see_t
        asl a
        asl a
        adc zp_see_t                ; x 5
        asl a                       ; x 10
        jsr add_tn
:       lda line
        beq :+
        lda #20
        jsr add_tn
:       lda in_cover
        beq :+
        lda #10
        jsr add_tn
:       lda alert
        beq :+
        jsr sub20
:       lda lamp_now
        beq :+
        lda see_light
        cmp #NIGHT
        bne :+
        jsr sub20
:       rts

add_tn: clc
        adc zp_see_tn
        sta zp_see_tn
        bcc :+
        inc zp_see_tn + 1
:       rts

sub20:  lda zp_see_tn
        sec
        sbc #20
        sta zp_see_tn
        bcs :+
        dec zp_see_tn + 1
:       rts

light_mod:
        .byte 0, 10, 20             ; day, dusk, night

; A die: d100 + rating A against zp_see_tn, into the event's dice. A = its outcome (and
; die_roll, die_out).
roll_die:
        sta zp_see_rate
        jsr roll_d100
        sta die_roll
        clc
        adc zp_see_rate
        sta zp_see_a
        lda #0
        adc #0
        sta zp_see_a + 1
        lda die_roll
        jsr roll_resolve
        sta die_out
        ldx ev_off                  ; the die: roll, total, TN, outcome
        lda die_roll
        sta ev_dice, x
        lda zp_see_a
        sta ev_dice + 1, x
        lda zp_see_a + 1
        sta ev_dice + 2, x
        lda zp_see_tn
        sta ev_dice + 3, x
        lda zp_see_tn + 1
        sta ev_dice + 4, x
        lda die_out
        sta ev_dice + 5, x
        txa
        clc
        adc #6
        sta ev_off
        inc ev_n
        lda die_out
        rts

; A looking party's helper: the TN moved by what its die did.
helper_shift:
        lda #0
        jsr shift_of
        clc
        adc zp_see_tn
        sta zp_see_tn
        lda zp_see_t
        adc zp_see_tn + 1
        sta zp_see_tn + 1
        rts

; A = what one of a group's others does to the TN, from its die (die_roll, die_out):
; looking (A = 0), a success takes 10 off (a crit 20), a fail puts 10 on (a natural 01,
; 20), a success at a cost nothing; sneaking (A = 1), the other way round. zp_see_t = its
; sign byte ($00 or $FF).
shift_of:
        sta zp_see_t
        lda die_roll
        cmp #2
        bcs :+
        lda #2 * HELP               ; a natural 01
        bne @signed                 ; (always)
:       lda die_out
        cmp #ROLL_FAIL
        bne :+
        lda #HELP
        bne @signed
:       cmp #ROLL_COST
        bne :+
        lda #0
        beq @signed
:       cmp #ROLL_CRIT
        bne :+
        lda #<(-2 * HELP)
        bne @signed
:       lda #<-HELP
@signed:
        ldx zp_see_t                ; sneaking: the other way round
        beq :+
        eor #$FF
        clc
        adc #1
:       ldx #0                      ; its sign byte
        cmp #$80
        bcc :+
        dex
:       stx zp_see_t
        rts

; An event with no roll: A = its kind (+ 2), Y = what came of it.
event_auto:
        sta ev_kind
        lda #0
        sta ev_n
        tya
        jmp write_event

; The event's end: A = its kind (0 the party's look, 1 the band's), Y = what came of it.
event_end:
        sta ev_kind
        tya
; Into the log: kind, band, distance, outcome A, the dice.
write_event:
        sta ev_out
        lda zp_see_log + 1          ; room for it?
        cmp #>(SEE_LOG + SEE_LOG_SIZE - EV_SIZE)
        bcc :+
        lda #1
        sta see_log_full
        rts
:       ldy #0
        lda ev_kind
        sta (zp_see_log), y
        iny
        lda band
        sta (zp_see_log), y
        iny
        lda dist
        sta (zp_see_log), y
        iny
        lda ev_out
        sta (zp_see_log), y
        iny
        lda ev_n
        sta (zp_see_log), y
        iny
        asl a                       ; 6 a die
        sta zp_see_t
        asl a
        adc zp_see_t
        beq @done
        sta zp_see_t
        ldx #0
:       lda ev_dice, x
        sta (zp_see_log), y
        iny
        inx
        cpx zp_see_t
        bne :-
@done:  tya
        clc
        adc zp_see_log
        sta zp_see_log
        bcc :+
        inc zp_see_log + 1
:       inc see_log_n
        rts

        .segment "BSS"

see_light:  .res 1              ; DAY, DUSK or NIGHT
see_n:      .res 1              ; the party: how many (1-4)...
see_notice: .res PARTY_MAX      ; ...each one's Notice (Wits or Intuition) and Stealth
see_stealth: .res PARTY_MAX
see_sneak:  .res 1              ; sneaking
see_lamp:   .res 1              ; carrying a light
see_bands:  .res 1              ; the bands: how many, and each one's...
b_x:        .res SEE_BANDS_MAX  ; ...square (its first foe's)
b_y:        .res SEE_BANDS_MAX
b_sense:    .res SEE_BANDS_MAX  ; best Sense, best Stealth, hiding
b_stealth:  .res SEE_BANDS_MAX
b_hiding:   .res SEE_BANDS_MAX
b_spotted:  .res SEE_BANDS_MAX  ; the party has spotted it
b_seen:     .res SEE_BANDS_MAX  ; it has seen the party
b_alert:    .res SEE_BANDS_MAX
b_plast:    .res SEE_BANDS_MAX  ; the distance at the party's last look at it (NONE)...
b_blast:    .res SEE_BANDS_MAX  ; ...and at its last look at the party
b_range:    .res SEE_BANDS_MAX  ; its sight range (see_prepare)
see_x:      .res 1              ; the leader's square
see_y:      .res 1
see_fight:  .res 1              ; 1 + the band that saw the party, or 0
see_ambush: .res 1              ; and it hadn't been spotted
see_log_n:  .res 1              ; the log's events this step
see_log_full: .res 1
top_notice: .res 1              ; the party's best looker and sneak (see_prepare)
top_stealth: .res 1
party_range: .res 1
band:       .res 1              ; the band being checked
dist:       .res 1
party_due:  .res 1
band_due:   .res 1
line:       .res 1
in_cover:   .res 1
alert:      .res 1
lamp_now:   .res 1
who:        .res 1
shift:      .res 2
lx:         .res 1              ; a line: where it is, where it's going, its steps
ly:         .res 1
tx:         .res 1
ty:         .res 1
dx:         .res 1
dy:         .res 1
sx:         .res 1
sy:         .res 1
cover:      .res 1
ev_kind:    .res 1              ; the event being made
ev_out:     .res 1
ev_n:       .res 1
ev_dice:    .res 6 * PARTY_MAX
ev_off:     .res 1              ; the next die's place in ev_dice
die_roll:   .res 1              ; the last die: its roll and outcome
die_out:    .res 1
