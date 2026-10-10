; The Story VM (docs/vm-spec.md; the C version is vm/vm.c, and this plays the same): a
; trip boarded, and the Departure's code run an instruction at a time. The depot and the
; cars are depot.s's, their strings expand.s's, the rewards and the receipt reward.s's.
; Every operand is checked as it's used: a bad image stops the VM ("The train has
; derailed"), never reads or writes outside its buffers.
;
; A fight (FIGHT) is fight.s's, in the fight's two assets (2 and 3), fetched and run when
; it comes. Not yet: the Deep Yards' FIGHT_YARD and PICK stop the VM.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"
        .include "receipt.inc"

        .export vm_board, vm_run, vm_fail, vm_error, vm_health, vars, yard, failed
        .export cue_scene
        .import scene_enter, kind, dep_id, flag_count, var_count, var_init, start_scene
        .import picture_count, music_count, music_at, car_index, car_title, code_len
        .import code_end, string_count
        .import expand, out_char, out_text, out_end
        .import reward_reset, first_pay, give, take, carrying, award_xp, set_debt
        .import echo_get, echo_set, rewind_echoes, receipt
        .import traveler, pass, rng_seed, check, skill_rating, health_max, chk_result
        .import dice_roll, record_line, party_show, log_print, menu_ask, key_wait, keys_clear
        .import picture_show, number_text, skill_lo, skill_hi, item_tier, echo_default
        .import encounter_count, asset_fetch, fight, view_map, platform_map, ram_copy
        .import __FIGHT_RUN__, __FIGHT_SIZE__
        .importzp ITEM_COUNT, ECHO_COUNT
        .importzp SKILL_COUNT

CODE_AT         = CAR_AT + 9
STACK_MAX       = 16
MENU_MAX        = 9
LABEL_MAX       = 38                ; a label or a title, and its 0 (vm.c)
LABEL_ROOM      = 44                ; a menu line: "9. ", the label, a newline, a 0
SKILL_BASE      = 16                ; RATING 16 + n is skill n
STAT_COUNT      = 6
STEPS_MAX       = 20000             ; instructions without a menu: a runaway
ERROR_MAX       = 30                ; vm.c's message length
SCENE_FIGHT     = 0                 ; cue_scene
SCENE_WON       = 1
SCENE_LOST      = 2
SCENE_BACK      = 3
SCENE_CUED      = $F0               ; music_cued: SCENE_CUED + a fight's tune

; The opcodes vm.s looks at (tools/qsc/opcodes.py).
OP_SWITCH4      = $04
OP_EQ           = $30
OP_LT           = $32
OP_LE           = $33
OP_GE           = $35
OP_AND          = $36
OP_SUB          = $44
OP_LAST         = $4D

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; vm_board: a trip begins (apb_vm_board, apb_vm_board_pass): the traveler (`traveler`) at
; full health, the story's flags clear and its vars as they start, a clean receipt, the
; dice from the seed; the first scene entered. With a pass: its seed and its ticket, and
; on a Rewind, this Departure's Echoes forgotten.
;   Takes:   A = 1 with a Boarding Pass (`pass`), 0 with a Passport; X/Y = the seed when
;            there's no pass (low/high).
;   Before:  vm_open has the depot.
;   After:   C clear; or C set: the VM has failed (vm_error says why).
;   Changes: A, X, Y; zp_ip; and the zero page of what it calls.
vm_board:
        sta with_pass
        stx seed
        sty seed + 1
        lda #0
        sta failed
        sta vsp
        sta menu_count
        ldx #63
@flags: sta flags, x
        dex
        bpl @flags
        jsr reward_reset
        ldy var_count               ; the vars' start values, from the depot
        beq @vars_set
        lda var_init
        sta zp_t0
        lda var_init + 1
        sta zp_t1
        dey
@vars:  lda (zp_t0), y
        sta vars, y
        dey
        cpy #$FF
        bne @vars
@vars_set:
        jsr health_max
        sta health
        lda dep_id
        sta receipt + R_DEPARTURE
        lda dep_id + 1
        sta receipt + R_DEPARTURE + 1
        lda traveler + CH_DEBT
        sta boarded_debt
        lda traveler + CH_DEBT + 1
        sta boarded_debt + 1
        lda with_pass
        beq @dice
        lda pass + PASS_DEPARTURE   ; a pass: for this Departure
        cmp dep_id
        bne @other
        lda pass + PASS_DEPARTURE + 1
        cmp dep_id + 1
        beq @pass
@other: lda #<msg_other
        ldx #>msg_other
        jmp vm_fail
@pass:  lda pass + PASS_SEED
        sta seed
        lda pass + PASS_SEED + 1
        sta seed + 1
        ldx #3
@ticket:
        lda pass + PASS_TICKET, x
        sta receipt + R_TICKET, x
        dex
        bpl @ticket
        lda pass + PASS_REWIND
        beq @dice
        lda dep_id                  ; a Rewind: as if for the first time
        ldx dep_id + 1
        jsr rewind_echoes
@dice:  lda seed
        ldx seed + 1
        sta yard
        stx yard + 1
        jsr rng_seed
        lda #$FF
        sta music_now
        sta music_cued
        sta car_index
        sta last_picture
        lda start_scene
        ldx start_scene + 1
        jmp scene_enter

; vm_health: the traveler's health now. After: A. Changes A.
vm_health:
        lda health
        rts

; ----------------------------------------------------------------------------------------
; vm_fail: the VM stops, the first time with why: WHAT, then (with a car loaded) " CAR:PC"
; (vm.c's fail), into vm_error.
;   Takes:   A/X = what (ASCII, ending in 0).
;   After:   C set.
;   Changes: A, X, Y; zp_t0, zp_t1; number.s's zero page.
vm_fail:
        ldy failed
        bne @once
        inc failed
        sta zp_t0
        stx zp_t1
        ldy #0
@what:  lda (zp_t0), y
        beq @said
        sta vm_error, y
        iny
        cpy #ERROR_MAX
        bne @what
@said:  sty error_n
        lda car_index
        cmp #$FF
        beq @end
        lda #' '
        jsr error_char
        lda car_index
        ldx #0
        jsr error_number
        lda #':'
        jsr error_char
        lda zp_ip                   ; pc: how far into the code
        sec
        sbc #<CODE_AT
        pha
        lda zp_ip + 1
        sbc #>CODE_AT
        tax
        pla
        jsr error_number
@end:   ldy error_n
        lda #0
        sta vm_error, y
@once:  sec
        rts

; error_number: A/X (low/high) in digits onto vm_error. Changes A, X, Y; zp_t0, zp_t1.
error_number:
        sta zp_num
        stx zp_num + 1
        jsr number_text
        sta zp_t0
        stx zp_t1
        ldy #0
@digit: lda (zp_t0), y
        beq @done
        jsr error_char
        iny
        bne @digit
@done:  rts

; error_char: A onto vm_error. Keeps Y. Changes X.
error_char:
        ldx error_n
        sta vm_error, x
        inc error_n
        rts

; ----------------------------------------------------------------------------------------
; vm_run: play until the Departure ends, or the VM fails. A failure is said in the story
; log: "The train has derailed: ...".
;   Before:  vm_board.
;   After:   A = 0: it ended complete; 1: it ended failed (the receipt says how, either
;            way); $FF: the VM failed.
;   Changes: A, X, Y; zp_ip; and the zero page of what it calls.
vm_run:
        lda #0
        sta steps
        sta steps + 1
        sta ended
next:   lda failed
        bne @failed
        lda ended
        beq @step
        lda receipt + R_OUTCOME
        rts
@failed:
        lda #<derailed              ; (a blank line first, as the C64's hal_error has it)
        ldx #>derailed
        jsr log_print
        lda #<vm_error
        ldx #>vm_error
        jsr log_print
        lda #<newline
        ldx #>newline
        jsr log_print
        lda #$FF
        rts
@step:  inc steps                   ; a runaway image can't hang the machine
        bne @counted
        inc steps + 1
@counted:
        lda steps
        cmp #<(STEPS_MAX + 1)
        lda steps + 1
        sbc #>(STEPS_MAX + 1)
        bcc @in_time
        lda #<msg_runaway
        ldx #>msg_runaway
        jsr vm_fail
        jmp next
@in_time:
        lda zp_ip                   ; inside the code?
        cmp code_end
        lda zp_ip + 1
        sbc code_end + 1
        bcc @inside
        lda #<msg_off_code
        ldx #>msg_off_code
        jsr vm_fail
        jmp next
@inside:
        lda zp_ip
        sta op_at
        lda zp_ip + 1
        sta op_at + 1
        ldy #0
        lda (zp_ip), y
        cmp #OP_LAST + 1
        bcc @known
        jsr op_bad
        jmp next
@known: sta opcode
        cmp #OP_SWITCH4             ; SWITCH4's table inside the code too
        bne @fits
        lda zp_ip
        clc
        adc #9
        tay
        lda zp_ip + 1
        adc #0
        tax
        cpy code_end
        sbc code_end + 1
        bcc @fits
        bne @long
        cpy code_end
        beq @fits
@long:  lda #<msg_bad_instruction
        ldx #>msg_bad_instruction
        jsr vm_fail
        jmp next
@fits:  jsr fetch8                  ; (past the opcode)
        jsr run_op
        jmp next

; run_op: the instruction `opcode`, by its handler's address (less one) on the stack.
run_op: lda opcode
        asl a
        tax
        lda op_table + 1, x
        pha
        lda op_table, x
        pha
        rts

; fetch8: the next byte of code. After: A, flags as A. Changes A, Y.
fetch8: ldy #0
        lda (zp_ip), y
        inc zp_ip
        bne @same
        inc zp_ip + 1
@same:  cmp #0
        rts

; fetch16: the next two. After: A/X (low/high), and `operand`. Changes A, X, Y.
fetch16:
        jsr fetch8
        sta operand
        jsr fetch8
        sta operand + 1
        tax
        lda operand
        rts

; jump_to: on from pc A/X (low/high), if it's inside the code; else the VM fails ("bad
; jump"). Changes A, X, Y.
jump_to:
        tay
        cmp code_len
        txa
        sbc code_len + 1
        bcs @bad
        tya
        clc
        adc #<CODE_AT
        sta zp_ip
        txa
        adc #>CODE_AT
        sta zp_ip + 1
        rts
@bad:   lda #<msg_bad_jump
        ldx #>msg_bad_jump
        jmp vm_fail

; push: A/X (low/high) onto the expression stack (the VM fails if it's full). Changes A,
; X, Y.
push:   ldy vsp
        cpy #STACK_MAX
        bcs @full
        sta stack_lo, y
        txa
        sta stack_hi, y
        inc vsp
        rts
@full:  lda #<msg_overflow
        ldx #>msg_overflow
        jmp vm_fail

; push_bool: 1 if Z is clear, else 0. Changes A, X, Y.
push_bool:
        beq @zero
        lda #1
@zero:  ldx #0
        jmp push

; pop: the top of the stack. After: A/X (low/high), and `popped`; 0 if it was empty (and
; the VM fails). Changes A, X, Y.
pop:    ldy vsp
        beq @empty
        dey
        sty vsp
        lda stack_lo, y
        sta popped
        ldx stack_hi, y
        stx popped + 1
        rts
@empty: lda #<msg_underflow
        ldx #>msg_underflow
        jsr vm_fail
        lda #0
        sta popped
        sta popped + 1
        tax
        rts

; ----------------------------------------------------------------------------------------
; The instructions (docs/vm-spec.md). Each is entered with zp_ip past its opcode and op_at
; at it, and returns to vm_run's loop: nothing in A, X, Y is kept.

op_bad: lda op_at                   ; not an instruction (pc at it, as vm.c says)
        sta zp_ip
        lda op_at + 1
        sta zp_ip + 1
op_halt:                            ; HALT_ERR
        lda #<msg_bad_op
        ldx #>msg_bad_op
        jmp vm_fail

op_jmp: jsr fetch16
        jmp jump_to

op_jz:  jsr fetch16
        cmp code_len
        txa
        sbc code_len + 1
        bcc @in
        lda #<msg_bad_jump
        ldx #>msg_bad_jump
        jmp vm_fail
@in:    jsr pop
        ora popped + 1
        bne @not
        lda operand
        ldx operand + 1
        jmp jump_to
@not:   rts

op_goto:
        jsr fetch16
        jmp scene_enter

op_switch4:
        jsr pop                     ; 0-3
        cpx #0
        bne @bad
        cmp #4
        bcs @bad
        asl a                       ; its target
        tay
        lda (zp_ip), y
        pha
        iny
        lda (zp_ip), y
        tax
        pla
        jmp jump_to
@bad:   lda #<msg_bad_switch
        ldx #>msg_bad_switch
        jmp vm_fail

op_end: jsr fetch8                  ; 0 complete, else failed
        beq @outcome
        lda #1
@outcome:
        sta receipt + R_OUTCOME
        lda traveler + CH_DEBT      ; Debt paid, or added
        cmp boarded_debt
        lda traveler + CH_DEBT + 1
        sbc boarded_debt + 1
        bcs @added
        lda boarded_debt
        sec
        sbc traveler + CH_DEBT
        sta receipt + R_DEBT_PAID
        lda boarded_debt + 1
        sbc traveler + CH_DEBT + 1
        sta receipt + R_DEBT_PAID + 1
        jmp @shown
@added: lda traveler + CH_DEBT
        sec
        sbc boarded_debt
        sta receipt + R_DEBT_ADDED
        lda traveler + CH_DEBT + 1
        sbc boarded_debt + 1
        sta receipt + R_DEBT_ADDED + 1
@shown: inc ended
        jmp show_party

op_text:
        jsr fetch16
        pha
        lda #<EXPAND_AT
        sta zp_out
        lda #>EXPAND_AT
        sta zp_out + 1
        lda #<(EXPAND_AT + EXPAND_MAX)
        sta out_end
        lda #>(EXPAND_AT + EXPAND_MAX)
        sta out_end + 1
        pla
        jsr expand
        bcc @good
        lda #<msg_bad_string
        ldx #>msg_bad_string
        jmp vm_fail
@good:  jsr out_zero
        lda #<EXPAND_AT
        ldx #>EXPAND_AT
        jsr log_print
        lda #<paragraph             ; the paragraph's end, and a blank line
        ldx #>paragraph
        jmp log_print

; out_zero: a 0 after the expanded text. Changes A, Y.
out_zero:
        ldy #0
        tya
        sta (zp_out), y
        rts

op_picture:
        jsr fetch8
        cmp picture_count
        bcc @good
        lda #<msg_bad_picture
        ldx #>msg_bad_picture
        jmp vm_fail
@good:  pha
        ldx #'0' - 1                ; its record, "[picture picNN]" (as the C64 version
@tens:  inx                         ; names its file)
        sec
        sbc #10
        bcs @tens
        adc #'0' + 10
        stx picture_name + 3
        sta picture_name + 4
        lda #<picture_record
        ldx #>picture_record
        jsr record_line
        pla                         ; and in the view
        sta last_picture
        jmp picture_show

op_music:
        jsr fetch8
        cmp #$FF
        beq @good
        cmp music_count
        bcc @good
        lda #<msg_bad_music
        ldx #>msg_bad_music
        jmp vm_fail
@good:  sta music_now
        ; (on into cue_music)

; cue_music: the tune `music_now` cued, unless it's the one cued last (client/cue.c). A5
; plays it; for now, its record: "[music NAME]", or "[music off]". Changes A, X, Y;
; zp_t0, zp_t1.
cue_music:
        lda music_now
        cmp music_cued
        bne @cue
        rts
@cue:   sta music_cued
        cmp #$FF
        bne @named
        ldy #0
@off:   lda off, y                  ; "off]"
        sta music_name, y
        iny
        cmp #0
        bne @off
        beq @send                   ; (always)
@named: lda music_at                ; its name: the list's entry `music_now`
        sta zp_t0
        lda music_at + 1
        sta zp_t1
        ldx music_now
        beq @here
@skip:  ldy #0
        lda (zp_t0), y
        sec                         ; (the length, and the byte that says it)
        adc zp_t0
        sta zp_t0
        bcc @next
        inc zp_t1
@next:  dex
        bne @skip
@here:  ldy #0
        lda (zp_t0), y
        tax                         ; (1-20: vm_open checked)
@char:  iny
        lda (zp_t0), y
        sta music_name - 1, y
        dex
        bne @char
        lda #']'
        sta music_name, y
        lda #0
        sta music_name + 1, y
@send:  lda #<music_record
        ldx #>music_record
        jmp record_line

; cue_scene: a fight's tune (client/cue.c's apb_cue_scene, apb_cue_back): A = SCENE_FIGHT,
; SCENE_WON or SCENE_LOST cues "battle", "won" or "lost"; SCENE_BACK the story's tune
; again. For now, only the record. Changes A, X, Y; zp_t0, zp_t1.
cue_scene:
        cmp #SCENE_BACK
        bcc @fight
        jmp cue_music
@fight: tax
        ora #SCENE_CUED
        cmp music_cued
        beq @same
        sta music_cued
        lda scene_lo, x
        pha
        lda scene_hi, x
        tax
        pla
        jmp record_line
@same:  rts

op_pause:
        lda #<press
        ldx #>press
        jsr log_print
        jsr keys_clear
        jmp key_wait

op_chapter:
        lda car_title
        and car_title + 1
        cmp #$FF
        bne @title
        rts
@title: lda #<EXPAND_AT             ; "~ Title ~", and a blank line
        sta zp_out
        lda #>EXPAND_AT
        sta zp_out + 1
        lda #<(EXPAND_AT + 2 + LABEL_MAX)
        sta out_end
        lda #>(EXPAND_AT + 2 + LABEL_MAX)
        sta out_end + 1
        lda #'~'
        jsr out_char
        lda #' '
        jsr out_char
        lda car_title
        ldx car_title + 1
        jsr expand
        bcc @good
        lda #<msg_bad_title
        ldx #>msg_bad_title
        jmp vm_fail
@good:  lda #<(EXPAND_AT + EXPAND_MAX)
        sta out_end
        lda #>(EXPAND_AT + EXPAND_MAX)
        sta out_end + 1
        lda #<chapter_end
        ldx #>chapter_end
        jsr out_text
        jsr out_zero
        lda #<EXPAND_AT
        ldx #>EXPAND_AT
        jmp log_print

op_menu_clear:
        lda #0
        sta menu_count
        rts

op_option:
        jsr fetch16                 ; its label: one of the car's strings
        sta new_label
        stx new_label + 1
        jsr fetch16                 ; where it goes: inside the code
        ldy menu_count
        cpy #MENU_MAX
        bcs @bad
        cmp code_len
        txa
        sbc code_len + 1
        bcs @bad
        lda new_label
        cmp string_count
        lda new_label + 1
        sbc string_count + 1
        bcs @bad
        lda new_label
        sta menu_label_lo, y
        lda new_label + 1
        sta menu_label_hi, y
        lda operand
        sta menu_target_lo, y
        lda operand + 1
        sta menu_target_hi, y
        inc menu_count
        rts
@bad:   lda #<msg_bad_option
        ldx #>msg_bad_option
        jmp vm_fail

op_menu:
        lda menu_count
        bne @labels
        lda #<msg_empty_menu
        ldx #>msg_empty_menu
        jmp vm_fail
@labels:                            ; every label expanded before any is shown: "N.
        lda #0                      ; label", a line each, at EXPAND_AT + 44N
        sta option
        lda #<EXPAND_AT
        sta line_at
        lda #>EXPAND_AT
        sta line_at + 1
@label: lda line_at
        sta zp_out
        clc
        adc #3 + LABEL_MAX - 1
        sta out_end
        lda line_at + 1
        sta zp_out + 1
        adc #0
        sta out_end + 1
        lda option
        clc
        adc #'1'
        jsr out_char
        lda #'.'
        jsr out_char
        lda #' '
        jsr out_char
        ldx option
        lda menu_label_lo, x
        pha
        lda menu_label_hi, x
        tax
        pla
        jsr expand
        bcc @good
        lda #<msg_bad_label
        ldx #>msg_bad_label
        jmp vm_fail
@good:  lda #10
        ldy #0
        sta (zp_out), y
        iny
        lda #0
        sta (zp_out), y
        jsr next_line
        inc option
        lda option
        cmp menu_count
        bne @label
        jsr show_party
        lda #0                      ; and shown
        sta option
        lda #<EXPAND_AT
        sta line_at
        lda #>EXPAND_AT
        sta line_at + 1
@show:  lda line_at
        ldx line_at + 1
        jsr log_print
        jsr next_line
        inc option
        lda option
        cmp menu_count
        bne @show
        lda #0                      ; a menu: the runaway count starts again
        sta steps
        sta steps + 1
        lda menu_count
        jsr menu_ask
        tax
        lda menu_target_lo, x
        pha
        lda menu_target_hi, x
        tax
        pla
        jmp jump_to

; next_line: line_at on to the next menu line's room. Changes A.
next_line:
        lda line_at
        clc
        adc #LABEL_ROOM
        sta line_at
        bcc @same
        inc line_at + 1
@same:  rts

op_push8:
        jsr fetch8
        ldx #0
        jmp push

op_push16:
        jsr fetch16
        jmp push

op_flag:
        jsr fetch16
        jsr flag_bit                ; X = its byte, A = its bit
        bcs @out
        and flags, x
        jmp push_bool
@out:   rts

op_var: jsr fetch8
        jsr var_index
        bcs @out
        lda vars, x
        ldx #0
        jmp push
@out:   rts

op_has: jsr fetch16
        jsr carrying
        ldx #0
        jmp push

op_echo:
        jsr fetch16
        jsr fetch8                  ; the default
        sta target
        lda operand
        ldx operand + 1
        jsr echo_get
        cmp #0                      ; unset: the default
        bne @push
        lda target
@push:  ldx #0
        jmp push

op_rating:
        jsr fetch8
        jsr rating_value
        bcs @out
        ldx #0
        jmp push
@out:   rts

op_level:
        lda traveler + CH_LEVEL
        ldx #0
        jmp push

op_race:
        lda traveler + CH_RACE
        ldx #0
        jmp push

op_class:
        lda traveler + CH_CLASS
        ldx #0
        jmp push

; EQ NE LT LE GT GE AND OR: b popped, then a; a ? b pushed (signed, 16 bits).
op_compare:
        jsr pop
        sta b_lo
        stx b_hi
        jsr pop
        sta a_lo
        stx a_hi
        lda opcode
        cmp #OP_AND
        bcs @logic
        cmp #OP_LT
        bcs @order
        lda a_lo                    ; EQ, NE: 1 in A if they're equal
        cmp b_lo
        bne @differ
        lda a_hi
        cmp b_hi
        bne @differ
        lda #1
        bne @eq                     ; (always)
@differ:
        lda #0
@eq:    ldx opcode
        cpx #OP_EQ
        beq @push
        eor #1
@push:  cmp #0
        jmp push_bool
@order: cmp #OP_LT                  ; LT: a < b, GE: not; GT: b < a, LE: not
        beq @ab
        cmp #OP_GE
        beq @ab
        lda b_lo
        cmp a_lo
        lda b_hi
        sbc a_hi
        jmp @less
@ab:    lda a_lo
        cmp b_lo
        lda a_hi
        sbc b_hi
@less:  bvc @signed                 ; less: N xor V
        eor #$80
@signed:
        and #$80
        ldx opcode
        cpx #OP_LE
        beq @not
        cpx #OP_GE
        bne @push
@not:   eor #$80
        jmp @push
@logic: lda a_lo
        ora a_hi
        beq @a
        lda #1
@a:     sta a_lo
        lda b_lo
        ora b_hi
        beq @b
        lda #1
@b:     ldx opcode
        cpx #OP_AND
        bne @or
        and a_lo
        jmp push_bool
@or:    ora a_lo
        jmp push_bool

op_not: jsr pop
        ora popped + 1
        beq @one
        lda #0
        beq @push                   ; (always)
@one:   lda #1
@push:  ldx #0
        jmp push

op_check:
        jsr fetch8                  ; the rating
        sta rating
        jsr fetch8                  ; the TN
        sta target
        lda rating
        jsr rating_value
        bcs @out
        ldx target
        jsr check
        lda rating                  ; who rolled: a stat's name or a skill's
        cmp #STAT_COUNT
        bcs @skill
        tax
        lda stat_lo, x
        pha
        lda stat_hi, x
        tax
        pla
        jmp @roll
@skill: sbc #SKILL_BASE             ; (C set)
        tax
        lda skill_lo, x
        pha
        lda skill_hi, x
        tax
        pla
@roll:  jsr dice_roll
        lda chk_result
        ldx #0
        jmp push
@out:   rts

op_fight:                           ; FIGHT: the encounter, the surprise (0-2)
        jsr fetch8
        sta encounter
        jsr fetch8
        cmp #3
        bcs @bad
        tax
        lda encounter
        cmp encounter_count
        bcc @good
@bad:   lda #<msg_bad_fight
        ldx #>msg_bad_fight
        jmp vm_fail
@good:  stx surprise
        lda #ASSET_FIGHT            ; the fight's code: its second part copied to EXPAND_AT
        jsr asset_fetch             ; (the story's text doesn't need it till the fight's
        bcs @no_fight               ; over), its first staged, and both run where they are
        lda #<STAGING
        sta zp_src
        lda #>STAGING
        sta zp_src + 1
        lda #<__FIGHT_RUN__
        sta zp_dst
        lda #>__FIGHT_RUN__
        sta zp_dst + 1
        lda #<__FIGHT_SIZE__
        sta zp_len
        lda #>__FIGHT_SIZE__
        sta zp_len + 1
        jsr ram_copy                ; (plain RAM: the interrupt goes on)
        lda #ASSET_BATTLE
        jsr asset_fetch
        bcc @staged
@no_fight:
        lda #<msg_no_fight
        ldx #>msg_no_fight
        jmp vm_fail
@staged:
        lda encounter
        ldx surprise
        ldy health
        jsr fight
        bcs @out                    ; (a bad encounter: vm_fail has said so)
        stx health
        sec                         ; 0 won, 1 lost, 2 fled
        sbc #1
        ldx #0
        jsr push
        lda #SCENE_BACK             ; the story's tune again, and its view
        jsr cue_scene
        lda last_picture
        cmp #$FF
        beq @map
        jsr picture_show
        jmp @party
@map:   lda #<platform_map
        ldx #>platform_map
        jsr view_map
@party: lda health
        jmp party_show
@out:   rts

op_yard:                            ; FIGHT_YARD, PICK: the Deep Yards, not yet
        lda #<msg_no_yards
        ldx #>msg_no_yards
        jmp vm_fail

op_set: jsr fetch16
        jsr flag_bit
        bcs @out
        ora flags, x
        sta flags, x
@out:   rts

op_clr: jsr fetch16
        jsr flag_bit
        bcs @out
        eor #$FF
        and flags, x
        sta flags, x
@out:   rts

op_let: jsr fetch8
        jsr var_index
        bcs @out
        stx which_var
        jsr pop                     ; 0-255, clamped
        cpx #0
        beq @set
        txa
        bmi @zero
        lda #255
        bne @set                    ; (always)
@zero:  lda #0
@set:   ldx which_var
        sta vars, x
@out:   rts

op_add:
op_sub: jsr fetch8
        sta which_var
        jsr fetch8                  ; n
        sta target
        lda which_var
        jsr var_index
        bcs @out
        lda opcode
        cmp #OP_SUB
        beq @sub
        lda vars, x                 ; to 255 at most
        clc
        adc target
        bcc @set
        lda #255
        bne @set                    ; (always)
@sub:   lda vars, x                 ; to 0 at least
        sec
        sbc target
        bcs @set
        lda #0
@set:   sta vars, x
@out:   rts

op_give:
        jsr fetch16
        jsr item_ok                 ; one of the registry's, with a tier
        bcs @out
        lda item_tier, y
        beq @bad
        jsr pay_here
        bcs @out
        lda operand
        ldx operand + 1
        jmp give
@bad:   lda #<msg_bad_item
        ldx #>msg_bad_item
        jmp vm_fail
@out:   rts

op_take:
        jsr fetch16
        jsr item_ok
        bcs @out
        lda operand
        ldx operand + 1
        jmp take
@out:   rts

op_xp:  jsr fetch8
        sta target
        jsr pay_here
        bcs @out
        lda target
        jmp award_xp
@out:   rts

op_debt:
        jsr fetch8                  ; how: set, add, pay
        sta target
        jsr fetch16                 ; how much
        lda kind                    ; official Departures only
        bne @bad
        lda target
        cmp #3
        bcs @bad
        jsr pay_here
        bcs @out
        lda operand
        ldx operand + 1
        ldy target
        jmp set_debt
@bad:   lda #<msg_bad_debt
        ldx #>msg_bad_debt
        jmp vm_fail
@out:   rts

op_heal:
        jsr fetch8
        sta target
        jsr health_max
        sta most
        lda target
        cmp #255                    ; 255: all of it
        beq @full
        clc
        adc health
        bcs @full
        cmp most
        bcc @set
@full:  lda most
@set:   sta health
        rts

op_echo_set:
        jsr fetch16                 ; the Echo
        jsr fetch8                  ; its state: 1-3
        sta target
        lda kind                    ; official Departures only
        bne @bad
        lda operand + 1             ; one of the registry's, with a default
        bne @bad
        lda operand
        cmp #<ECHO_COUNT
        bcs @bad
        tax
        lda echo_default, x
        beq @bad
        lda target
        beq @bad
        cmp #4
        bcs @bad
        tay
        lda operand
        ldx operand + 1
        jmp echo_set
@bad:   lda #<msg_bad_echo
        ldx #>msg_bad_echo
        jmp vm_fail

; ----------------------------------------------------------------------------------------
; Helpers for the instructions.

; show_party: the traveler in the party frame, at the health they have now (party.s).
show_party:
        lda health
        jmp party_show

; pay_here: the running instruction's reward, the first time it's reached this trip? C
; clear: pay it. Changes A, X, Y.
pay_here:
        lda op_at
        ldx op_at + 1
        jmp first_pay

; var_index: var A, checked. After: X = A, C clear; or C set (the VM has failed).
var_index:
        cmp var_count
        bcs @bad
        tax
        rts
@bad:   lda #<msg_bad_var
        ldx #>msg_bad_var
        jmp vm_fail

; flag_bit: flag A/X, checked. After: X = its byte in `flags`, A = its bit, C clear; or C
; set (the VM has failed). Changes A, X, Y.
flag_bit:
        tay
        cmp flag_count
        txa
        sbc flag_count + 1
        bcs @bad
        stx flag_hi                 ; its byte: flag / 8 (512 at most: 9 bits)
        tya
        lsr flag_hi
        ror a
        lsr a
        lsr a
        tax
        tya
        and #7
        tay
        lda bits, y
        clc
        rts
@bad:   lda #<msg_bad_flag
        ldx #>msg_bad_flag
        jmp vm_fail

; rating_value: rating A (a stat 0-5, a skill 16-27), checked. After: A = its value, C
; clear; or C set (the VM has failed). Changes A, X, Y.
rating_value:
        cmp #STAT_COUNT
        bcs @skill
        tax
        lda traveler + CH_STATS, x
        clc
        rts
@skill: cmp #SKILL_BASE
        bcc @bad
        cmp #SKILL_BASE + SKILL_COUNT
        bcs @bad
        sbc #SKILL_BASE - 1         ; (C clear: one more comes off)
        jsr skill_rating
        clc
        rts
@bad:   lda #<msg_bad_rating
        ldx #>msg_bad_rating
        jmp vm_fail

; item_ok: item `operand` one of the registry's. After: Y = it (under 256), C clear; or C
; set (the VM has failed). Changes A, X, Y.
item_ok:
        lda operand
        cmp #<ITEM_COUNT
        lda operand + 1
        sbc #>ITEM_COUNT
        bcs @bad
        ldy operand
        rts
@bad:   lda #<msg_bad_item
        ldx #>msg_bad_item
        jmp vm_fail

; ----------------------------------------------------------------------------------------
; The handlers, by opcode (less one: RTS adds it). op_bad: not an instruction.
op_table:
        .word op_halt - 1, op_jmp - 1, op_jz - 1, op_goto - 1                   ; $00
        .word op_switch4 - 1, op_end - 1, op_bad - 1, op_bad - 1
        .word op_bad - 1, op_bad - 1, op_bad - 1, op_bad - 1
        .word op_bad - 1, op_bad - 1, op_bad - 1, op_bad - 1
        .word op_text - 1, op_picture - 1, op_pause - 1, op_chapter - 1         ; $10
        .word op_music - 1, op_bad - 1, op_bad - 1, op_bad - 1
        .word op_menu_clear - 1, op_option - 1, op_menu - 1, op_bad - 1
        .word op_bad - 1, op_bad - 1, op_bad - 1, op_bad - 1
        .word op_push8 - 1, op_push16 - 1, op_flag - 1, op_var - 1              ; $20
        .word op_has - 1, op_echo - 1, op_rating - 1, op_level - 1
        .word op_race - 1, op_class - 1, op_bad - 1, op_bad - 1
        .word op_bad - 1, op_bad - 1, op_bad - 1, op_bad - 1
        .word op_compare - 1, op_compare - 1, op_compare - 1, op_compare - 1    ; $30
        .word op_compare - 1, op_compare - 1, op_compare - 1, op_compare - 1
        .word op_not - 1, op_check - 1, op_fight - 1, op_yard - 1
        .word op_bad - 1, op_bad - 1, op_bad - 1, op_bad - 1
        .word op_set - 1, op_clr - 1, op_let - 1, op_add - 1                   ; $40
        .word op_sub - 1, op_yard - 1, op_bad - 1, op_bad - 1
        .word op_give - 1, op_take - 1, op_xp - 1, op_debt - 1
        .word op_echo_set - 1, op_heal - 1
        .assert * - op_table = (OP_LAST + 1) * 2, error, "an opcode without a handler"

bits:           .byte 1, 2, 4, 8, 16, 32, 64, 128

; The stats' names, for a check's roll (the skills' are the registry's).
might:          .byte "Might", 0
grace:          .byte "Grace", 0
grit:           .byte "Grit", 0
wits:           .byte "Wits", 0
presence:       .byte "Presence", 0
fate:           .byte "Fate", 0
stat_lo:        .byte <might, <grace, <grit, <wits, <presence, <fate
stat_hi:        .byte >might, >grace, >grit, >wits, >presence, >fate

paragraph:      .byte 10, 10, 0
newline:        .byte 10, 0
press:          .byte "(press a key)", 10, 0
chapter_end:    .byte " ~", 10, 10, 0
derailed:       .byte 10, "The train has derailed: ", 0
off:            .byte "off]", 0

; The records (RAM: filled in as they're used).
picture_record: .byte "[picture "
picture_name:   .byte "pic00]", 0
music_record:   .byte "[music "
music_name:     .res 20 + 2         ; the name, "]", 0

; What goes wrong (vm.c's words).
msg_other:          .byte "pass is for another Departure", 0
msg_runaway:        .byte "runaway: no menu or end", 0
msg_off_code:       .byte "ran off the code", 0
msg_bad_op:         .byte "bad opcode", 0
msg_bad_instruction: .byte "bad instruction", 0
msg_bad_jump:       .byte "bad jump", 0
msg_bad_switch:     .byte "bad switch", 0
msg_bad_string:     .byte "bad string", 0
msg_bad_picture:    .byte "bad picture", 0
msg_bad_music:      .byte "bad music", 0
msg_bad_title:      .byte "bad title", 0
msg_bad_option:     .byte "bad option", 0
msg_empty_menu:     .byte "empty menu", 0
msg_bad_label:      .byte "bad label", 0
msg_bad_flag:       .byte "bad flag", 0
msg_bad_var:        .byte "bad var", 0
msg_bad_rating:     .byte "bad rating", 0
msg_bad_item:       .byte "bad item", 0
msg_bad_debt:       .byte "bad debt", 0
msg_bad_echo:       .byte "bad echo", 0
msg_overflow:       .byte "stack overflow", 0
msg_underflow:      .byte "stack underflow", 0
scene_battle:       .byte "[music battle]", 0
scene_won:          .byte "[music won]", 0
scene_lost:         .byte "[music lost]", 0
scene_lo:           .byte <scene_battle, <scene_won, <scene_lost
scene_hi:           .byte >scene_battle, >scene_won, >scene_lost
msg_no_yards:       .byte "no yards yet", 0
msg_bad_fight:      .byte "bad fight", 0
msg_no_fight:       .byte "can't load the fight", 0

        .segment "BSS"
vm_error:       .res ERROR_MAX + 14 ; why the VM failed, and where
error_n:        .res 1
failed:         .res 1
ended:          .res 1
with_pass:      .res 1
seed:           .res 2
yard:           .res 2              ; the trip's seed: the Deep Yards' floors come from it
health:         .res 1
boarded_debt:   .res 2
steps:          .res 2              ; instructions since the last menu
op_at:          .res 2              ; where the running instruction starts
opcode:         .res 1
operand:        .res 2
popped:         .res 2
flags:          .res 64
vars:           .res 128
stack_lo:       .res STACK_MAX
stack_hi:       .res STACK_MAX
vsp:            .res 1
menu_count:     .res 1
menu_label_lo:  .res MENU_MAX
menu_label_hi:  .res MENU_MAX
menu_target_lo: .res MENU_MAX
menu_target_hi: .res MENU_MAX
new_label:      .res 2
option:         .res 1
line_at:        .res 2
a_lo:           .res 1
a_hi:           .res 1
b_lo:           .res 1
b_hi:           .res 1
rating:         .res 1
target:         .res 1
most:           .res 1
which_var:      .res 1
flag_hi:        .res 1
music_now:      .res 1              ; the tune the story has on ($FF: none)
music_cued:     .res 1              ; the one cued last
last_picture:   .res 1              ; the picture in the view, or $FF (a fight puts it back)
encounter:      .res 1
surprise:       .res 1
