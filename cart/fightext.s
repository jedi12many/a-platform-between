; What happened in a fight, in words (the C version is client/battle_text.c, and these are
; its sentences, word for word): each event the battle tells (battle.s's ev_*) as the
; story log says it, and an attack's or a getaway's roll as the dice log shows it. ASCII.
; Code in the fight's second asset (asset 3), run at EXPAND_AT.

        .include "zp.inc"
        .include "battle.inc"

        .export fight_text, fight_roll, fight_text_reset, said, said_len
        .import ev_kind, ev_actor, ev_target, ev_value, ev_roll, ev_total, ev_tn, ev_result
        .import fight_name, number_text, dice_show, dice_said, chk_total, chk_tn

SAID_MAX        = 80

        .segment "FIGHT"

; ----------------------------------------------------------------------------------------
; fight_text_reset: a new fight: no round said yet, no free attack coming. Changes A.
fight_text_reset:
        lda #$FF
        sta last_round
        lda #0
        sta free_next
        rts

; ----------------------------------------------------------------------------------------
; fight_text: the event in ev_* in words (apb_view_event), in `said` (ASCII, ending in 0).
;   After:   A = TEXT_NOTHING (nothing to say), TEXT_HEADING ("-- Round 2 --") or
;            TEXT_SENTENCE.
;   Changes: A, X, Y; zp_t0, zp_t1; zp_name; number.s's zero page.
fight_text:
        lda #0
        sta said_len
        sta said
        lda ev_actor
        sta actor
        ldx ev_kind
        cpx #EV_FREE + 1
        bcs @nothing
        lda kind_lo, x
        sta zp_t0
        lda kind_hi, x
        sta zp_t1
        jmp (zp_t0)
@nothing:
        lda #TEXT_NOTHING
        rts

t_turn: lda ev_value
        cmp last_round
        beq t_nothing
        sta last_round
        cmp #0
        beq @caught
        lda #<round
        ldx #>round
        jsr put
        lda last_round
        jsr put_number
        lda #<dashes
        ldx #>dashes
        jsr put
        lda #TEXT_HEADING
        rts
@caught:
        lda #<caught
        ldx #>caught
        jsr put
        lda #TEXT_HEADING
        rts

t_free: lda #1
        sta free_next
t_end:
t_nothing:
        lda #TEXT_NOTHING
        rts

t_move: lda #<w_move
        ldx #>w_move
        jsr subject_s
        jmp stop

t_attack:
        lda free_next
        beq @plain
        lda #<free
        ldx #>free
        jsr put
@plain: lda #0
        sta free_next
        lda #<w_attack
        ldx #>w_attack
        jsr subject_s
        jsr space
        lda ev_target
        beq @you
        jsr put_name
        jmp @colon
@you:   lda #<you_small
        ldx #>you_small
        jsr put
@colon: jsr colon
        lda ev_result
        and #3
        tax
        lda hit_lo, x
        pha
        lda hit_hi, x
        tax
        pla
        jsr put
        lda ev_result
        bne @damage
        jmp stop
@damage:
        jsr colon
        jsr put_value
        lda #<damage_text
        ldx #>damage_text
        jmp put_sentence

t_down: lda ev_target
        beq @you
        jsr put_name
        lda #<is_down
        ldx #>is_down
        jmp put_sentence
@you:   lda #<you_down
        ldx #>you_down
        jmp put_sentence

t_hazard:
        lda #<ground
        ldx #>ground
        jsr put
        lda actor
        beq @you
        jsr put_name
        jmp @hurt
@you:   lda #<you_small
        ldx #>you_small
        jsr put
@hurt:  jsr colon
        jsr put_value
        lda #<damage_text
        ldx #>damage_text
        jmp put_sentence

t_guard:
        lda #<w_stand
        ldx #>w_stand
        jsr subject_s
        lda #<guard
        ldx #>guard
        jmp put_sentence

t_wait: lda #<w_wait
        ldx #>w_wait
        jsr subject_s
        lda #<see
        ldx #>see
        jmp put_sentence

t_flee: lda ev_roll
        beq @exit
        lda actor                   ; "You try" / "Ash rat tries"
        bne @tries
        lda #<w_try
        ldx #>w_try
        jsr subject_s
        jmp @away
@tries: jsr put_name
        lda #<tries
        ldx #>tries
        jsr put
@away:  lda #<get_away
        ldx #>get_away
        jsr put
        lda ev_result
        and #3
        tax
        lda flee_lo, x
        pha
        lda flee_hi, x
        tax
        pla
        jsr put
        jmp stop
@exit:  lda #<w_take
        ldx #>w_take
        jsr subject_s
        lda #<the_exit
        ldx #>the_exit
        jmp put_sentence

t_gone: lda actor
        bne @foe
        lda #<you_out
        ldx #>you_out
        jmp put_sentence
@foe:   jsr put_name
        lda #<runs_off
        ldx #>runs_off
        jmp put_sentence

; subject_s: "You VERB" or "NAME VERBs" (the actor), the verb at A/X. Changes A, X, Y.
subject_s:
        pha
        txa
        pha
        lda actor
        bne @them
        lda #<you
        ldx #>you
        jsr put
        jsr space
        pla
        tax
        pla
        jmp put
@them:  jsr put_name
        jsr space
        pla
        tax
        pla
        jsr put
        lda #<s
        ldx #>s
        jmp put

; put_sentence: A/X, then the sentence is said. stop: "." and the same.
put_sentence:
        jsr put
        lda #TEXT_SENTENCE
        rts
stop:   lda #<dot
        ldx #>dot
        jmp put_sentence

; put_name: fighter A's name. Changes A, X, Y; zp_name.
put_name:
        jsr fight_name
        jmp put

; put_value: ev_value's digits. put_number: A's. Changes A, X, Y.
put_value:
        lda ev_value
        ldx ev_value + 1
        jmp number
put_number:
        ldx #0
number: sta zp_num
        stx zp_num + 1
        jsr number_text
        ; (on into put)

; put: ASCII at A/X (ending in 0) onto `said`. Changes A, X, Y; zp_t0, zp_t1.
put:    sta zp_t0
        stx zp_t1
        ldy #0
        ldx said_len
@char:  lda (zp_t0), y
        sta said, x
        beq @done
        cpx #SAID_MAX
        bcs @done
        inx
        iny
        bne @char
@done:  lda #0
        sta said, x
        stx said_len
        rts

space:  lda #<one_space
        ldx #>one_space
        jmp put
colon:  lda #<colon_space
        ldx #>colon_space
        jmp put

; ----------------------------------------------------------------------------------------
; fight_roll: an attack's or a getaway's roll (ev_*) into the dice log, with its record
; (apb_view_event_roll): "Ash rat 42" over "vs 58: graze 1".
;   After:   C set if the event had no roll.
;   Changes: A, X, Y; zp_t0-zp_t2; zp_name; the zero page of dice_show.
fight_roll:
        lda ev_kind
        cmp #EV_ATTACK
        beq @attack
        cmp #EV_FLEE
        bne @none
        lda ev_roll
        beq @none
        lda ev_result               ; out, or stay
        and #3
        tax
        lda away_lo, x
        sta dice_said
        lda away_hi, x
        sta dice_said + 1
        jmp @show
@none:  sec
        rts
@attack:
        lda #0                      ; "miss", or "graze 1": the blow and the damage
        sta said_len
        lda ev_result
        and #3
        tax
        lda blow_lo, x
        pha
        lda blow_hi, x
        tax
        pla
        jsr put
        lda ev_result
        beq @blow
        jsr put_value
@blow:  lda #<said
        sta dice_said
        lda #>said
        sta dice_said + 1
@show:  lda ev_total
        sta chk_total
        lda ev_total + 1
        sta chk_total + 1
        lda ev_tn
        sta chk_tn
        lda ev_tn + 1
        sta chk_tn + 1
        lda ev_actor
        jsr fight_name
        jsr dice_show
        clc
        rts

kind_lo:
        .byte <t_turn, <t_move, <t_attack, <t_down, <t_hazard, <t_guard, <t_wait
        .byte <t_flee, <t_gone, <t_end, <t_free
kind_hi:
        .byte >t_turn, >t_move, >t_attack, >t_down, >t_hazard, >t_guard, >t_wait
        .byte >t_flee, >t_gone, >t_end, >t_free

round:          .byte "-- Round ", 0
dashes:         .byte " --", 0
caught:         .byte "-- Caught off guard --", 0
free:           .byte "Free attack! ", 0
you:            .byte "You", 0
you_small:      .byte "you", 0
s:              .byte "s", 0
w_move:         .byte "move", 0
w_attack:       .byte "attack", 0
w_stand:        .byte "stand", 0
w_wait:         .byte "wait", 0
w_try:          .byte "try", 0
w_take:         .byte "take", 0
tries:          .byte " tries", 0
dot:            .byte ".", 0
one_space:      .byte " ", 0
colon_space:    .byte ": ", 0
damage_text:    .byte " damage.", 0
is_down:        .byte " is down.", 0
you_down:       .byte "You are down.", 0
ground:         .byte "The ground hurts ", 0
guard:          .byte " guard.", 0
see:            .byte " to see what happens.", 0
get_away:       .byte " to get away: ", 0
the_exit:       .byte " the exit.", 0
you_out:        .byte "You are out of the fight.", 0
runs_off:       .byte " runs off.", 0
h_miss:         .byte "a miss", 0
h_graze:        .byte "a glancing hit", 0
h_hit:          .byte "a hit", 0
h_crit:         .byte "a crit", 0
hit_lo:         .byte <h_miss, <h_graze, <h_hit, <h_crit
hit_hi:         .byte >h_miss, >h_graze, >h_hit, >h_crit
f_still:        .byte "still here", 0
f_unclean:      .byte "out, but not cleanly", 0
f_out:          .byte "out", 0
flee_lo:        .byte <f_still, <f_unclean, <f_out, <f_out
flee_hi:        .byte >f_still, >f_unclean, >f_out, >f_out
b_miss:         .byte "miss", 0
b_graze:        .byte "graze ", 0
b_hit:          .byte "hit ", 0
b_crit:         .byte "crit ", 0
blow_lo:        .byte <b_miss, <b_graze, <b_hit, <b_crit
blow_hi:        .byte >b_miss, >b_graze, >b_hit, >b_crit
a_stay:         .byte "stay", 0
away_lo:        .byte <a_stay, <f_out, <f_out, <f_out
away_hi:        .byte >a_stay, >f_out, >f_out, >f_out

        .segment "BSS"
said:           .res SAID_MAX + 2   ; the words (fight_text), or a roll's outcome
said_len:       .res 1
actor:          .res 1
last_round:     .res 1
free_next:      .res 1              ; the next attack is a free one
