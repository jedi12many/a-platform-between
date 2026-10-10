; The battle screen (docs/frames.md; the C version is client/tactics.c, and this asks and
; tells the same): the map in the view, a square a tile of 16 x 16 pixels, centred; each
; fighter a figure, one sprite of the VIC's eight (a fight has eight fighters at most, so
; nothing is multiplexed); the cursor in the map's own characters (the square's tile with
; a bracket at each corner, in the cursor's colour). Under it the story's frames go on:
; what happens in the story log (fightext.s's words), each roll in the dice log, the
; traveler's health in the party frame, and the command bar on the command row, as in the
; Gold Box games: Move, Aim, Guard, Wait, Flee, Quick, Done. Keys: the cursor keys or the
; joystick (port 2), or the digits as a keypad, to move; RETURN, space or fire to choose;
; DEL or RUN/STOP to go back; a command's first letter for it. Every prompt is also a
; record (record_line), as the C64 version's are, so the tests read a fight in words.
; Code in the fight's asset (asset 2).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"
        .include "battle.inc"

        .export scene_begin, scene_turn, scene_end
        .import event_hook, fighters, fighter_count, map_w, map_h, cost_to
        .import ev_kind, ev_actor, ev_target, ev_x, ev_y, ev_result
        .import act_x, act_y, act_kind, act_target, battle_tile, battle_reach, battle_quick
        .import battle_can_attack, can_who, can_target, can_x, can_y, battle_tn, chk_tn
        .import fight_text, fight_roll, fight_text_reset, fight_name, said, said_len
        .import view_square, view_set, view_ink, view_mode, frames, traveler
        .import log_print, record_line, command_show, key_wait, number_text
        .import party_show, party_state, cue_scene

VIEW_PLAIN      = 0                 ; view.s's view_set
VIEW_MARKED     = 1
VIEW_CURSOR     = 2
MEMBER_READY    = 0                 ; party.s's party_state
MEMBER_TURN     = 1
MEMBER_DOWN     = 2
SCENE_FIGHT     = 0                 ; vm.s's cue_scene
SCENE_WON       = 1
SCENE_LOST      = 2
SCENE_BACK      = 3
FIRE            = KEY_RETURN        ; the keys as the screen takes them (key)
BACK            = KEY_STOP
COMMANDS        = 7
LIGHT_GREY      = 15
CURSOR_MOVE     = YELLOW | 8        ; the cursor's colour (multicolour)
CURSOR_AIM      = RED | 8
LOOK_NAMES      = 21                ; a foe's look's name: a length, then 20
RECORD_MAX      = 60                ; a prompt, as a record

        .segment "BATTLE"

; ----------------------------------------------------------------------------------------
; scene_begin: the fight on the screen (hal_battle_begin): its tune, the map, the figures,
; the party; "-- A fight! --". From here the battle's events come to scene_event.
;   Before:  the battle set up and started (fight.s); $01 = $35.
;   Changes: A, X, Y; zp_t0-zp_t3; and the zero page of what it calls.
scene_begin:
        lda #SCENE_FIGHT
        jsr cue_scene
        lda #<scene_event
        sta event_hook
        lda #>scene_event
        sta event_hook + 1
        lda #MEM_VIEW
        ldx #CTRL1_TEXT
        ldy #BLACK
        jsr view_mode
        lda #0
        sta VIC_SPR_ENA
        sta VIC_SPR_BEHIND
        sta VIC_SPR_TALL
        sta VIC_SPR_WIDE
        sta on_quick
        sta marks
        sta cur_on
        sta vy
        lda #$FF
        sta VIC_SPR_MULTI
        sta whose
        lda #BLACK                  ; the figures' shared colours: tools/battlegfx.py's dark
        sta VIC_SPR_MC1             ; grey is black here, the outline a figure has no
                                    ; second sprite for
        lda #LIGHT_GREY
        sta VIC_SPR_MC2
        jsr fight_text_reset
        lda #SQUARES_ACROSS         ; the map in the middle of the view
        sec
        sbc map_w
        lsr a
        sta ox
        lda #0
        ldx map_h
        cpx #SQUARES_DOWN + 1
        bcs @tall
        lda #SQUARES_DOWN
        sec
        sbc map_h
        lsr a
@tall:  sta oy
        ldx #0                      ; each one's look, and where it's shown
@who:   cpx fighter_count
        bcs @looked
        stx who
        jsr look_of
        ldx who
        sta looks, x
        lda fighters + F_X, x
        sta shown_x, x
        lda fighters + F_Y, x
        sta shown_y, x
        inx
        bne @who                    ; (always)
@looked:
        ldx shown_x
        ldy shown_y
        jsr show_square
        jsr draw_map
        jsr place_all
        jsr draw_party
        lda #<a_fight
        ldx #>a_fight
        jmp say

; look_of: fighter X's look: the traveler's race's (or a stranger's), a foe's by its name in
; the looks' table (or a stranger's). After: A. Changes A, X, Y; zp_t0-zp_t3; zp_name.
look_of:
        txa
        bne @foe
        lda traveler + CH_RACE
        cmp #STRANGER
        bcc @race
        lda #STRANGER
@race:  rts
@foe:   jsr fight_name
        sta zp_t0
        stx zp_t1
        ldx #0
        lda #<look_names
        sta zp_t2
        lda #>look_names
        sta zp_t3
@look:  ldy #0                      ; this one: the same length, the same letters
        lda (zp_t2), y
        beq @next
        tay
@same:  lda (zp_t2), y
        dey
        cmp (zp_t0), y
        bne @next
        cpy #0
        bne @same
        lda (zp_t2), y            ; (and the name ends there)
        tay
        lda (zp_t0), y
        bne @next
        txa
        clc
        adc #FOE_LOOKS
        rts
@next:  lda zp_t2
        clc
        adc #LOOK_NAMES
        sta zp_t2
        bcc @on
        inc zp_t3
@on:    inx
        cpx #FOE_LOOKS
        bne @look
        lda #STRANGER
        rts

; ----------------------------------------------------------------------------------------
; The map.

; visible: is map row Y shown? C set if not. Changes A.
visible:
        cpy vy
        bcc @not
        tya
        sec
        sbc vy
        cmp #SQUARES_DOWN
        rts                         ; (C set: under the view)
@not:   sec
        rts

; draw_square: map square X, Y as it should look now (the cursor on it, or the reach dot,
; or plain), if it's shown. Changes A, X, Y.
draw_square:
        jsr visible
        bcs @out
        stx sq_x
        sty sq_y
        lda #VIEW_PLAIN
        sta view_set
        lda #0
        sta view_ink
        lda cur_on
        beq @mark
        cpx cur_x
        bne @mark
        cpy cur_y
        bne @mark
        lda #VIEW_CURSOR
        sta view_set
        lda cur_ink
        sta view_ink
        bne @draw                   ; (always)
@mark:  lda marks
        beq @draw
        tya                         ; reachable this turn: cost_to's not $FF
        asl a
        asl a
        asl a
        asl a
        ora sq_x
        tax
        lda cost_to, x
        cmp #$FF
        beq @draw
        lda #VIEW_MARKED
        sta view_set
@draw:  ldx sq_x
        ldy sq_y
        jsr battle_tile
        pha
        lda sq_x
        clc
        adc ox
        tax
        lda sq_y
        sec
        sbc vy
        clc
        adc oy
        tay
        pla
        jmp view_square
@out:   rts

; draw_map: the whole view: the map's squares, blank round them. Changes A, X, Y.
draw_map:
        lda #0
        sta view_row
@row:   lda #0
        sta view_col
@col:   lda view_col                ; the map's square here, if there is one
        sec
        sbc ox
        tax
        cpx map_w
        bcs @blank
        lda view_row
        sec
        sbc oy
        bcc @blank
        clc
        adc vy
        tay
        cpy map_h
        bcs @blank
        jsr draw_square
        jmp @next
@blank: lda #VIEW_PLAIN
        sta view_set
        lda #$FF
        ldx view_col
        ldy view_row
        jsr view_square
@next:  inc view_col
        lda view_col
        cmp #SQUARES_ACROSS
        bne @col
        inc view_row
        lda view_row
        cmp #SQUARES_DOWN
        bne @row
        rts

; show_square: keep map row Y on the screen, a square in from the edge where the map
; allows (only a map taller than the view scrolls). Changes A, X, Y.
show_square:
        lda map_h
        cmp #SQUARES_DOWN + 1
        bcc @done
        lda vy
        sta new_vy
        tya                         ; above: a square over it
        cmp new_vy
        beq @above
        bcs @below
@above: tya
        beq @top
        sec
        sbc #1
@top:   sta new_vy
@below: tya                         ; below: a square under it
        clc
        adc #2
        sec
        sbc #SQUARES_DOWN
        bcc @fit
        cmp new_vy
        bcc @fit
        sta new_vy
@fit:   lda map_h                   ; and never past the map's foot
        sec
        sbc #SQUARES_DOWN
        cmp new_vy
        bcs @moved
        sta new_vy
@moved: lda new_vy
        cmp vy
        beq @done
        sta vy
        jsr draw_map
        jmp place_all
@done:  rts

; show_marks: the reach dots on (A = 1) or off, and the map again. Changes A, X, Y.
show_marks:
        sta marks
        jmp draw_map

; cursor: the cursor onto map square X, Y in colour A (off the square it was on). Changes
; A, X, Y.
cursor: sta cur_ink
        stx new_x
        sty new_y
        jsr cursor_off
        lda new_x
        sta cur_x
        lda new_y
        sta cur_y
        lda #1
        sta cur_on
        ldx cur_x
        ldy cur_y
        jmp draw_square

; cursor_off: the cursor gone. Changes A, X, Y.
cursor_off:
        lda cur_on
        beq @off
        lda #0
        sta cur_on
        ldx cur_x
        ldy cur_y
        jmp draw_square
@off:   rts

; ----------------------------------------------------------------------------------------
; The figures: fighter n is sprite n.

; place: fighter X's figure where it's shown, in its own colour; gone, or off the view,
; none. Changes A, X, Y.
place:  stx fig
        lda fighters + F_STATE, x
        cmp #GONE
        beq hide
        ldy shown_y, x
        jsr visible
        bcs hide
        lda shown_x, x
        jsr square_xy
        ldx fig
        ldy looks, x
        lda look_colours, y
        sta fig_ink
        ; (on into figure)

; figure: fighter `fig` at fig_x, fig_y (the VIC's places) in fig_ink; its fallen shape if
; it's down. Changes A, X, Y.
figure: ldx fig
        lda looks, x                ; its shape: 2 x its look, and 1 more fallen
        asl a
        adc #SHAPE_POINTER          ; (C clear: looks are under 128)
        ldy fighters + F_STATE, x
        cpy #DOWN
        bne @up
        adc #1
@up:    sta SPRITE_POINTERS, x
        lda fig_ink
        sta VIC_SPR_COLOUR, x
        txa
        asl a
        tay
        lda fig_x
        sta VIC_SPR_X, y
        lda fig_y
        sta VIC_SPR_Y, y
        lda sprite_bit, x
        ora VIC_SPR_ENA
        sta VIC_SPR_ENA
        lda fig_x + 1
        beq @low
        lda sprite_bit, x
        ora VIC_SPR_X_HIGH
        bne @high                   ; (always)
@low:   lda sprite_bit, x
        eor #$FF
        and VIC_SPR_X_HIGH
@high:  sta VIC_SPR_X_HIGH
        rts

; hide: fighter `fig`'s figure off. Changes A, X.
hide:   ldx fig
        lda sprite_bit, x
        eor #$FF
        and VIC_SPR_ENA
        sta VIC_SPR_ENA
        rts

; place_all: every figure. Changes A, X, Y.
place_all:
        ldx #0
@each:  cpx fighter_count
        bcs @done
        stx fig_n
        jsr place
        ldx fig_n
        inx
        bne @each                   ; (always)
@done:  rts

; square_xy: where a figure on shown square A (column), Y (row) goes: fig_x, fig_y, the
; VIC's places, centred across, standing on it (FIGURE_DX, FIGURE_DY). Changes A.
square_xy:
        clc
        adc ox
        sta fig_x                   ; x 16, 16 bits
        lda #0
        sta fig_x + 1
        asl fig_x
        asl fig_x
        asl fig_x
        asl fig_x
        rol fig_x + 1
        lda fig_x
        clc
        adc #<(SPRITE_LEFT + FIGURE_DX)
        sta fig_x
        bcc @row
        inc fig_x + 1
@row:   tya
        sec
        sbc vy
        clc
        adc oy
        asl a
        asl a
        asl a
        asl a
        clc
        adc #SPRITE_TOP + FIGURE_DY
        sta fig_y
        rts

; nudge: fig_x, fig_y moved by A across, X down (each -16 to 16). Changes A.
nudge:  sta nudge_x
        clc
        adc fig_x
        sta fig_x
        lda nudge_x                 ; (C kept)
        bmi @left
        bcc @down
        inc fig_x + 1
        bcs @down                   ; (always)
@left:  bcs @down                   ; (a negative with a carry: no borrow)
        dec fig_x + 1
@down:  txa
        clc
        adc fig_y
        sta fig_y
        rts

; frames_wait: A frames go by (the figures move, the cursor shows). Changes A.
frames_wait:
        sta wait_n
@frame: lda frames
@same:  cmp frames
        beq @same
        dec wait_n
        bne @frame
        rts

; ----------------------------------------------------------------------------------------
; walk: fighter A's figure from where it's shown to X, Y, a square at a time, each step
; the neighbour nearest the goal that isn't a wall or a pit (the rules have said the move
; is allowed; this is how it looks), in three slides of two frames. Changes A, X, Y.
walk:   sta walker
        stx goal_x
        sty goal_y
        lda #20
        sta walk_n
@step:  ldx walker
        lda shown_x, x
        cmp goal_x
        bne @on
        lda shown_y, x
        cmp goal_y
        beq @there
@on:    dec walk_n
        beq @there
        jsr next_step
        ldy step_y
        jsr show_square
        lda #1
        sta slide
@slide: ldx walker
        stx fig
        lda shown_x, x
        ldy shown_y, x
        jsr square_xy
        ldy looks, x
        lda look_colours, y
        sta fig_ink
        ldx walker                  ; a third of the way, two thirds, there
        lda step_x
        sec
        sbc shown_x, x
        jsr thirds
        pha
        lda step_y
        sec
        sbc shown_y, x
        jsr thirds
        tax
        pla
        jsr nudge
        jsr figure
        lda #2
        jsr frames_wait
        inc slide
        lda slide
        cmp #4
        bne @slide
        ldx walker
        lda step_x
        sta shown_x, x
        lda step_y
        sta shown_y, x
        jmp @step
@there: ldx walker
        lda goal_x
        sta shown_x, x
        lda goal_y
        sta shown_y, x
        jmp place

; thirds: a step of A (-1, 0 or 1 squares), slide `slide` (1-3) of the way, in pixels.
; Changes A.
thirds: cmp #0
        beq @none
        bmi @back
        ldy slide
        lda third, y
@none:  rts
@back:  ldy slide
        lda third, y
        eor #$FF
        clc
        adc #1
        rts

; next_step: the neighbour of fighter `walker`'s shown square nearest goal_x, goal_y that
; isn't a wall or a pit (the first of the nearest, in the keys' order), in step_x, step_y.
; Changes A, X, Y.
next_step:
        lda goal_x
        sta step_x
        lda goal_y
        sta step_y
        lda #$FF
        sta best
        ldx walker
        lda shown_x, x
        sta from_x
        lda shown_y, x
        sta from_y
        lda #0
        sta dir_n
@dir:   ldx dir_n
        ldy dirs, x
        lda from_x
        clc
        adc dir_dx, y
        sta try_x
        cmp map_w
        bcs @next
        lda from_y
        clc
        adc dir_dy, y
        sta try_y
        cmp map_h
        bcs @next
        tay
        ldx try_x
        jsr battle_tile
        cmp #TILE_WALL
        beq @next
        cmp #TILE_PIT
        beq @next
        lda try_x                   ; how far from the goal
        sec
        sbc goal_x
        bcs @dx
        eor #$FF
        adc #1
@dx:    sta far
        lda try_y
        sec
        sbc goal_y
        bcs @dy
        eor #$FF
        adc #1
@dy:    cmp far
        bcc @most
        lda far
@most:  cmp best
        bcs @next
        sta best
        lda try_x
        sta step_x
        lda try_y
        sta step_y
@next:  inc dir_n
        lda dir_n
        cmp #8
        bne @dir
        rts

; ----------------------------------------------------------------------------------------
; blow: the attack in ev_* as it looks: a lunge a quarter of the way to the target (a shot
; or a power: a pause); then a miss, or the target flashing white. Changes A, X, Y.
blow:   ldx ev_actor
        ldy shown_y, x
        jsr show_square
        ldx ev_actor
        lda fighters + F_RANGED, x
        bne @pause
        stx fig                     ; the lunge
        lda shown_x, x
        ldy shown_y, x
        jsr square_xy
        ldx fig
        ldy looks, x
        lda look_colours, y
        sta fig_ink
        ldy ev_target
        lda shown_x, y
        sec
        sbc shown_x, x
        jsr quarter
        pha
        ldy ev_target
        lda shown_y, y
        sec
        sbc shown_y, x
        jsr quarter
        tax
        pla
        jsr nudge
        jsr figure
        lda #4
        jsr frames_wait
        ldx ev_actor
        jsr place
        jmp @hit
@pause: lda #4
        jsr frames_wait
@hit:   lda ev_result
        bne @flash
        lda #4
        jmp frames_wait
@flash: ldx ev_target
        lda #WHITE
        ; (on into flash)

; flash: fighter X's figure in colour A and back, three times. Changes A, X, Y.
flash:  sta flash_ink
        stx flasher
        ldy shown_y, x
        jsr visible
        bcs @done
        lda #3
        sta flash_n
@once:  ldx flasher
        stx fig
        lda shown_x, x
        ldy shown_y, x
        jsr square_xy
        lda flash_ink
        sta fig_ink
        jsr figure
        lda #3
        jsr frames_wait
        ldx flasher
        jsr place
        lda #3
        jsr frames_wait
        dec flash_n
        bne @once
@done:  rts

; quarter: a difference of A squares, a quarter of the way: 4 pixels its way (or none).
; Changes A.
quarter:
        cmp #0
        beq @none
        bmi @back
        lda #4
@none:  rts
@back:  lda #$FC
        rts

; ----------------------------------------------------------------------------------------
; scene_event: what the battle tells (battle.s's battle_event, through event_hook), shown
; (hal_battle_event): the words, a move walked, a blow struck, a figure fallen or gone,
; the roll, the party. Keeps X, Y (the battle's).
scene_event:
        txa
        pha
        tya
        pha
        jsr fight_text
        sta told
        lda ev_kind
        cmp #EV_TURN
        bne @move
        lda ev_actor
        sta whose
        jmp @said
@move:  cmp #EV_MOVE
        bne @attack
        jsr say_said
        lda ev_actor
        ldx ev_x
        ldy ev_y
        jsr walk
        jmp @done
@attack:
        cmp #EV_ATTACK
        bne @down
        jsr blow
        jmp @said
@down:  cmp #EV_DOWN
        bne @hazard
        ldx ev_target
        jsr place
        jmp @said
@hazard:
        cmp #EV_HAZARD
        bne @gone
        ldx ev_actor
        lda #RED
        jsr flash
        jmp @said
@gone:  cmp #EV_GONE
        bne @said
        ldx ev_actor
        jsr place
@said:  lda told
        beq @roll
        jsr say_said
@roll:  jsr fight_roll
        jsr draw_party
@done:  pla
        tay
        pla
        tax
        rts

; draw_party: the traveler in the party frame: their health, their turn, or down.
; Changes A, X, Y; and the zero page of party_show.
draw_party:
        ldx #MEMBER_READY
        lda whose
        bne @state
        ldx #MEMBER_TURN
@state: lda fighters + F_STATE
        beq @in
        ldx #MEMBER_DOWN
@in:    stx party_state
        lda fighters + F_HEALTH
        jmp party_show

; say_said: `said` into the story log, a line of its own. say: A/X's. Changes A, X, Y; and
; text.s's zero page.
say_said:
        ldx said_len
        lda #10
        sta said, x
        lda #0
        sta said + 1, x
        lda #<said
        ldx #>said
say:    pha
        txa
        pha
        lda zp_log_col              ; (on a row of its own)
        beq @row
        lda #<newline
        ldx #>newline
        jsr log_print
@row:   pla
        tax
        pla
        jmp log_print

; ----------------------------------------------------------------------------------------
; The command row.

; prompt: A/X on the command row in colour Y, and as a record: "[...]". Changes A, X, Y;
; zp_t0-zp_t2; text.s's zero page.
prompt: sta zp_t0
        stx zp_t1
        tya
        pha
        ldy #0
@copy:  lda (zp_t0), y
        sta record + 1, y
        beq @end
        iny
        cpy #RECORD_MAX
        bne @copy
@end:   pla
        tay
        lda #<(record + 1)
        ldx #>(record + 1)
        jsr command_show
        ; (on into log_record)

; log_record: what's in record + 1 (ending in 0) as a record: "[...]". Changes A, X, Y.
log_record:
        lda #'['
        sta record
        ldy #0
@end:   iny
        lda record, y
        bne @end
        lda #']'
        sta record, y
        lda #0
        sta record + 1, y
        lda #<record
        ldx #>record
        jmp record_line

; draw_bar: the commands on the command row, `chosen` in white. Changes A, X, Y; zp_t0-
; zp_t2; text.s's zero page.
draw_bar:
        lda #<bar
        ldx #>bar
        ldy #CYAN
        jsr command_show
        ldx chosen
        lda bar_to, x
        sta zp_t0
        lda bar_from, x
        tax
        lda #WHITE
@white: sta COLOUR_RAM + INPUT_ROW * COLS, x
        inx
        cpx zp_t0
        bne @white
        rts

; clear_bar: the command row blank. Changes A, X, Y; zp_t0-zp_t2; text.s's zero page.
clear_bar:
        lda #<nothing
        ldx #>nothing
        ldy #WHITE
        jmp command_show

; key: a key (key_wait), as the screen takes it: the digits as a keypad's directions (5
; fire), letters as capitals, RETURN and space as fire, DEL and RUN/STOP as back. After:
; A. Changes A, X.
key:    jsr key_wait
        cmp #'1'
        bcc @fire
        cmp #'9' + 1
        bcs @letter
        sbc #'1' - 1                ; (C clear: less 1 more)
        tax
        lda digit_key, x
        rts
@letter:
        cmp #'a'
        bcc @fire
        cmp #'z' + 1
        bcs @fire
        sbc #'a' - 'A' - 1          ; (C clear)
        rts
@fire:  cmp #' '
        bne @back
        lda #FIRE
        rts
@back:  cmp #KEY_DELETE
        bne @done
        lda #BACK
@done:  rts

; is_dir: is key A a direction? C clear if so (X = it), set if not. Changes X.
is_dir: tax
        beq @no
        cpx #KEY_DOWN_RIGHT + 1
        bcs @no
        cpx #KEY_DELETE
        beq @no
        clc
        rts
@no:    sec
        rts

; ----------------------------------------------------------------------------------------
; scene_turn: the traveler's turn (hal_battle_turn): the squares they can reach marked,
; the command bar; Move (a square), Aim (a foe in reach from there), Guard, Wait (only
; before moving, once a round), Flee, Quick (the computer plays them from now, till T),
; Done. The action into act_x, act_y, act_kind, act_target for battle_act.
;   Takes:   A = the traveler (the fighter whose turn it is).
;   Changes: A, X, Y; zp_t0-zp_t3; and the zero page of what it calls.
scene_turn:
        sta turn_who
        tax
        sta whose
        lda fighters + F_X, x
        sta here_x
        sta to_x
        sta shown_x, x
        lda fighters + F_Y, x
        sta here_y
        sta to_y
        sta shown_y, x
        lda fighters + F_WAITED, x
        sta waited
        jsr draw_party
        ldy here_y
        jsr show_square
        lda on_quick
        beq @choose
        lda #<on_quick_text
        ldx #>on_quick_text
        ldy #YELLOW
        jsr prompt
        jsr key
        cmp #'T'
        beq @take_over
        lda turn_who
        jsr battle_quick
        jmp clear_bar
@take_over:
        lda #0
        sta on_quick
@choose:
        lda turn_who
        jsr battle_reach
        lda #1
        jsr show_marks
@ask:   ldx to_x
        ldy to_y
        lda #CURSOR_MOVE
        jsr cursor
        jsr draw_bar
        lda turn_who                ; "[Kestrel: choose.]"
        jsr fight_name
        sta zp_t0
        stx zp_t1
        ldy #0
@name:  lda (zp_t0), y
        beq @named
        sta record + 1, y
        iny
        bne @name                   ; (always)
@named: ldx #0
@more:  lda choose, x
        sta record + 1, y
        beq @logged
        inx
        iny
        bne @more                   ; (always)
@logged:
        jsr log_record
        jsr key
        cmp #KEY_LEFT
        bne @right
        dec chosen
        bpl @ask
        lda #COMMANDS - 1
        sta chosen
        bne @ask                    ; (always)
@right: cmp #KEY_RIGHT
        bne @fire
        inc chosen
        lda chosen
        cmp #COMMANDS
        bcc @ask
        lda #0
        sta chosen
        beq @ask                    ; (always)
@fire:  cmp #FIRE
        bne @which
        ldx chosen
        lda command_keys, x
@which: sta pressed
        ldx #COMMANDS - 1           ; a command's letter: it's chosen
@find:  cmp command_keys, x
        bne @not
        stx chosen
@not:   dex
        bpl @find
        jsr draw_bar
        lda pressed
        cmp #'M'
        bne @aim
        jsr choose_square
        jmp @ask
@aim:   cmp #'A'
        bne @guard
        jsr choose_target
        cmp #NOBODY
        bne @attack
        jmp @ask
@attack:
        tay
        lda #ACT_ATTACK
        jmp act
@guard: ldy #0
        cmp #'G'
        bne @wait
        lda #ACT_GUARD
        jmp act
@wait:  cmp #'W'
        bne @flee
        lda to_x                    ; only before moving, once a round
        cmp here_x
        bne @no_wait
        lda to_y
        cmp here_y
        bne @no_wait
        lda waited
        bne @no_wait
        lda #ACT_WAIT
        jmp act
@no_wait:
        lda #<only_wait
        ldx #>only_wait
        ldy #RED
        jsr prompt
        lda #25
        jsr frames_wait
        jmp @ask
@flee:  cmp #'F'
        bne @quick
        lda #ACT_FLEE
        jmp act
@quick: cmp #'Q'
        bne @done
        lda #1
        sta on_quick
        lda #ACT_DONE
        jsr act
        lda turn_who
        jmp battle_quick
@done:  cmp #'D'
        beq @end_turn
        jmp @ask
@end_turn:
        lda #ACT_DONE
        ; (on into act)

; act: the action: A (ACT_*), with target Y, from to_x, to_y; the marks, the cursor and the
; bar gone. Changes A, X, Y; and the zero page of what it calls.
act:    sta act_kind
        sty act_target
        lda to_x
        sta act_x
        lda to_y
        sta act_y
        lda #0
        jsr show_marks
        jsr cursor_off
        jmp clear_bar

; choose_square: Move: the figure follows a cursor over the squares it can reach; fire to
; stop there (to_x, to_y), back to stay where it was. Changes A, X, Y.
choose_square:
        lda #<move_text
        ldx #>move_text
        ldy #YELLOW
        jsr command_show
        lda #<move_record
        ldx #>move_record
        jsr record_line
        lda to_x
        sta pick_x
        lda to_y
        sta pick_y
@show:  ldy pick_y
        jsr show_square
        ldx turn_who
        lda pick_x
        sta shown_x, x
        lda pick_y
        sta shown_y, x
        jsr place
        ldx pick_x
        ldy pick_y
        lda #CURSOR_MOVE
        jsr cursor
        jsr key
        cmp #FIRE
        bne @back
        lda pick_x
        sta to_x
        lda pick_y
        sta to_y
        rts
@back:  cmp #BACK
        bne @dir
        ldx turn_who
        lda to_x
        sta shown_x, x
        lda to_y
        sta shown_y, x
        jmp place
@dir:   jsr is_dir
        bcs @show
        lda pick_x                  ; one square that way, if they can reach it
        clc
        adc dir_dx, x
        sta try_x
        cmp map_w
        bcs @show
        lda pick_y
        clc
        adc dir_dy, x
        sta try_y
        cmp map_h
        bcs @show
        asl a
        asl a
        asl a
        asl a
        ora try_x
        tax
        lda cost_to, x
        cmp #$FF
        beq @show
        lda try_x
        sta pick_x
        lda try_y
        sta pick_y
        jmp @show

; choose_target: Aim: the cursor goes round the foes in reach from to_x, to_y; fire to
; attack. After: A = the target, or NOBODY. Changes A, X, Y.
choose_target:
        lda #0
        sta n_targets
        lda #1
        sta pick
@find:  ldx pick
        cpx fighter_count
        bcs @found
        lda fighters + F_STATE, x
        bne @next
        lda turn_who
        sta can_who
        stx can_target
        lda to_x
        sta can_x
        lda to_y
        sta can_y
        jsr battle_can_attack
        beq @next
        ldx n_targets
        lda pick
        sta targets, x
        inc n_targets
@next:  inc pick
        jmp @find
@found: lda n_targets
        bne @some
        lda #<nobody_text
        ldx #>nobody_text
        ldy #RED
        jsr prompt
        lda #NOBODY
        rts
@some:  lda #0
        sta aim_at
@aim:   ldx aim_at
        lda targets, x
        sta pick
        tax
        ldy shown_y, x
        jsr show_square
        ldx pick
        ldy shown_y, x
        lda shown_x, x
        tax
        lda #CURSOR_AIM
        jsr cursor
        jsr aim_text                ; "Aim: Ash rat, TN 60"
        lda #<(record + 1)
        ldx #>(record + 1)
        ldy #YELLOW
        jsr command_show
        jsr log_record
        jsr key
        cmp #FIRE
        bne @back
        lda pick
        rts
@back:  cmp #BACK
        bne @dir
        lda #NOBODY
        rts
@dir:   jsr is_dir
        bcs @aim
        cpx #KEY_LEFT               ; left, up and the diagonals left and up: the one
        beq @before                 ; before; the rest, the one after
        cpx #KEY_UP
        beq @before
        cpx #KEY_UP_LEFT
        beq @before
        cpx #KEY_DOWN_LEFT
        beq @before
        inc aim_at
        lda aim_at
        cmp n_targets
        bcc @aim
        lda #0
        sta aim_at
        beq @aim                    ; (always)
@before:
        dec aim_at
        bpl @aim
        ldx n_targets
        dex
        stx aim_at
        jmp @aim

; aim_text: "Aim: NAME, TN n" (foe `pick`, from turn_who) in record + 1. Changes A, X, Y;
; zp_t0, zp_t1; zp_name; number.s's zero page.
aim_text:
        ldy #0
@aim:   lda aim, y
        sta record + 1, y
        beq @name
        iny
        bne @aim                    ; (always)
@name:  sty rec_n
        lda pick
        jsr fight_name
        jsr rec_put
        lda #<comma_tn
        ldx #>comma_tn
        jsr rec_put
        ldx turn_who
        ldy pick
        jsr battle_tn
        lda chk_tn
        sta zp_num
        lda chk_tn + 1
        sta zp_num + 1
        jsr number_text
        ; (on into rec_put)

; rec_put: A/X (ending in 0) onto record + 1 at rec_n. Changes A, X, Y; zp_t0, zp_t1.
rec_put:
        sta zp_t0
        stx zp_t1
        ldy #0
        ldx rec_n
@char:  lda (zp_t0), y
        sta record + 1, x
        beq @done
        inx
        iny
        cpx #RECORD_MAX
        bcc @char
        lda #0
        sta record + 1, x
@done:  stx rec_n
        rts

; ----------------------------------------------------------------------------------------
; scene_end: the fight over (hal_battle_end): its tune, how it went, a key; the figures
; gone. The story's tune and view come back in vm.s.
;   Takes:   A = how it went (BATTLE_WON, _LOST, _FLED).
;   Changes: A, X, Y; and the zero page of what it calls.
scene_end:
        sta ended
        jsr cursor_off
        jsr clear_bar
        lda ended                   ; won, lost: their tunes; fled: the story's
        cmp #BATTLE_FLED
        bne @tune
        lda #SCENE_BACK
@tune:  jsr cue_scene
        ldx ended
        lda ending_lo, x
        pha
        lda ending_hi, x
        tax
        pla
        jsr say
        lda #<press_text
        ldx #>press_text
        ldy #YELLOW
        jsr prompt
        jsr key
        jsr clear_bar
        lda #0
        sta VIC_SPR_ENA
        sta party_state
        rts

; ----------------------------------------------------------------------------------------
a_fight:        .byte "-- A fight! --", 10, 0
newline:        .byte 10, 0
nothing:        .byte 0
bar:            .byte "Move Aim Guard Wait Flee Quick Done", 0
bar_from:       .byte 0, 5, 9, 15, 20, 25, 31
bar_to:         .byte 4, 8, 14, 19, 24, 30, 35
command_keys:   .byte "MAGWFQD"
choose:         .byte ": choose.", 0
on_quick_text:  .byte "On quick: T takes over.", 0
only_wait:      .byte "You can only wait before you move.", 0
move_text:      .byte "Move: the arrows, then fire.", 0
move_record:    .byte "[Move]", 0
nobody_text:    .byte "Nobody in reach from there.", 0
aim:            .byte "Aim: ", 0
comma_tn:       .byte ", TN ", 0
press_text:     .byte "Press a key.", 0
won:            .byte "You won the fight.", 10, 0
lost:           .byte "You lost the fight.", 10, 0
fled:           .byte "You got away.", 10, 0
ending_lo:      .byte <nothing, <won, <lost, <fled
ending_hi:      .byte >nothing, >won, >lost, >fled
sprite_bit:     .byte $01, $02, $04, $08, $10, $20, $40, $80
third:          .byte 0, 5, 10, 16      ; a slide's way across a square, in pixels
; The keypad's digits 1-9 as keys (5: fire), and each direction key's step (KEY_ codes).
digit_key:      .byte KEY_DOWN_LEFT, KEY_DOWN, KEY_DOWN_RIGHT, KEY_LEFT, FIRE, KEY_RIGHT
                .byte KEY_UP_LEFT, KEY_UP, KEY_UP_RIGHT
dir_dx:         .byte 0, 0, 0, $FF, 1, $FF, 1, $FF, 0, 1
dir_dy:         .byte 0, $FF, 1, 0, 0, $FF, $FF, 1, 0, 1
dirs:           .byte KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_UP_LEFT, KEY_UP_RIGHT
                .byte KEY_DOWN_LEFT, KEY_DOWN_RIGHT
; Each look's colour, then the foes' looks' names (tools/battlegfx.py --cart16).
look_colours:   .incbin "cart/tiles16", 4224, LOOKS
look_names:     .incbin "cart/tiles16", 4224 + LOOKS, FOE_LOOKS * LOOK_NAMES

        .segment "BSS"
looks:          .res FIGHTERS_MAX   ; each fighter's look
shown_x:        .res FIGHTERS_MAX   ; where each figure is shown
shown_y:        .res FIGHTERS_MAX
ox:             .res 1              ; the map's place in the view, in squares
oy:             .res 1
vy:             .res 1              ; the map's top row shown (a tall map scrolls)
new_vy:         .res 1
marks:          .res 1              ; the reach dots are shown
cur_on:         .res 1              ; the cursor: shown, where, its colour
cur_x:          .res 1
cur_y:          .res 1
cur_ink:        .res 1
new_x:          .res 1
new_y:          .res 1
on_quick:       .res 1              ; the computer is playing the traveler
whose:          .res 1              ; whose turn it is
chosen:         .res 1              ; the command chosen on the bar
pressed:        .res 1
told:           .res 1
ended:          .res 1
who:            .res 1
turn_who:       .res 1
here_x:         .res 1              ; this turn: where they stand, where they'll move to
here_y:         .res 1
to_x:           .res 1
to_y:           .res 1
waited:         .res 1
pick:           .res 1
pick_x:         .res 1
pick_y:         .res 1
try_x:          .res 1
try_y:          .res 1
targets:        .res FIGHTERS_MAX
n_targets:      .res 1
aim_at:         .res 1
sq_x:           .res 1
sq_y:           .res 1
view_col:       .res 1
view_row:       .res 1
fig:            .res 1              ; a figure: whose, where (the VIC's places), its colour
fig_n:          .res 1
fig_x:          .res 2
fig_y:          .res 1
fig_ink:        .res 1
walker:         .res 1
walk_n:         .res 1
goal_x:         .res 1
goal_y:         .res 1
step_x:         .res 1
step_y:         .res 1
from_x:         .res 1
from_y:         .res 1
slide:          .res 1
best:           .res 1
far:            .res 1
dir_n:          .res 1
flasher:        .res 1
flash_ink:      .res 1
flash_n:        .res 1
wait_n:         .res 1
nudge_x:        .res 1
rec_n:          .res 1
record:         .res RECORD_MAX + 3 ; "[", a prompt, "]"
