; Seeing on the floor (docs/open-floors.md, Being seen; docs/walk.md, "Seeing"): the
; floor's bands and the party's numbers put into seeing.s, every band checked at the start
; and each time the leader's square changes (the square under its middle), and a band that
; sees the party stops the walk (the fight comes next: W6). A floor without bands (the
; rooms' floors) has nothing to do.
;
; A step's checks can take more than a frame's time to spare (a line traced and dice rolled
; for each band due), so they run as a task of their own, on their own stack ($0100-$017F),
; in the frame loop's wait: see_yield hands back as soon as a frame begins. What they found
; is shown SEE_SHOWN frames after the step, whenever they finished: the bands spotted
; appear, and a band that saw the party lets go of the joystick from the next frame. (If
; they haven't finished by then, see_late counts it and they're shown when they do: the
; tests fail it.) While they're under way, the leader's further steps wait; then the square
; it's on is the next step.

        .include "zp.inc"
        .include "walk.inc"

        .export watch_init, watch_step, watch_stick, watch_idle, see_yield, b_shown, see_late
        .export wk_seen, wk_begin, shown_fight
        .import floor, wk_pos, wk_stick, wk_frame, frame_seen, roll_seed
        .import see_prepare, see_step, see_light, see_n, see_notice, see_stealth, see_sneak
        .import see_lamp, see_bands, b_x, b_y, b_sense, b_stealth, b_hiding, b_spotted, b_seen
        .import b_alert, b_plast, b_blast, see_x, see_y, see_fight

NONE            = $FF

        .segment "SEEING"         ; (run from $E000: walk.cfg)

; ----------------------------------------------------------------------------------------
; watch_init: seeing set up from the floor's asset, and the start's checks made (and shown)
; there and then.
;   Before:  wk_pos on the start's square; no interrupts yet.
;   Changes: A, X, Y; zp_see_*.
watch_init:
        ldx #PARTY_SIZE - 1         ; the party: Notice and Stealth, nobody sneaking, no light
:       lda floor + FL_NOTICE, x
        sta see_notice, x
        lda floor + FL_STEALTH, x
        sta see_stealth, x
        dex
        bpl :-
        lda #PARTY_SIZE
        sta see_n
        lda #0
        sta see_sneak
        sta see_lamp
        sta see_late
        sta task_on
        sta task_wait
        sta shown_fight
        lda floor + FL_LIGHT
        sta see_light
        lda floor + FL_BANDS        ; the bands, as they stand: none spotted, nothing seen
        sta see_bands
        ldx #0
        ldy #0
@band:  cpx see_bands
        beq @set
        lda floor + FL_BANDS + 1, y
        sta b_x, x
        lda floor + FL_BANDS + 2, y
        sta b_y, x
        lda floor + FL_BANDS + 3, y
        sta b_sense, x
        lda floor + FL_BANDS + 4, y
        sta b_stealth, x
        lda floor + FL_BANDS + 5, y
        sta b_hiding, x
        lda #0
        sta b_spotted, x
        sta b_seen, x
        sta b_alert, x
        lda #NONE
        sta b_plast, x
        sta b_blast, x
        tya
        clc
        adc #5
        tay
        inx
        bne @band                   ; (always)
@set:   lda floor + FL_SEED
        ldx floor + FL_SEED + 1
        jsr roll_seed
        jsr see_prepare
        jsr square_of
        lda see_bands
        beq :+
        jsr checks                  ; (task_on 0: see_yield never hands back)
        jmp show
:       rts

; ----------------------------------------------------------------------------------------
; watch_step: after the frame's walk: the checks under way shown when their time comes;
; then, if none are, and the leader's square has changed (and no band has seen the
; party), its checks begun.
;   Changes: A, X, Y.
watch_step:
        lda see_bands
        beq @done
        lda task_wait               ; checks under way: shown SEE_SHOWN frames on
        beq @idle
        dec task_wait
        bne @done
        lda task_on
        beq :+
        inc see_late                ; (not finished in time: shown when they are)
        inc task_wait
        rts
:       jsr show
@idle:  lda shown_fight
        bne @done
        lda see_x
        pha
        lda see_y
        pha
        jsr square_of
        pla
        cmp see_y
        bne @moved
        pla
        cmp see_x
        bne wk_begin
@done:  rts
@moved: pla
wk_begin:                           ; (the harness notes the frame each step's checks begin)
        lda #SEE_SHOWN              ; the task begun: its stack fresh, checks its way in
        sta task_wait
        lda #>(task - 1)
        sta TASK_STACK
        lda #<(task - 1)
        sta TASK_STACK - 1
        lda #<(TASK_STACK - 2)
        sta task_sp
        lda #1
        sta task_on
        rts

; What the checks found, shown: each band seen or spotted drawn, and a band that has seen
; the party.
show:   ldx see_bands
        dex
:       lda b_spotted, x
        ora b_seen, x
        sta b_shown, x
        dex
        bpl :-
        lda see_fight
        sta shown_fight
        rts

; The task: the step's checks; then back to the loop for good.
task:   jsr checks
        lda #0
        sta task_on
        ldx main_sp
        txs
        rts                         ; (out of watch_idle)

checks: jsr see_step
wk_seen:                            ; (the harness reads each step's log here)
        rts

; see_x, see_y = the leader's square: the one under its middle, (wk_pos + 8 pixels) / 16.
square_of:
        lda wk_pos
        clc
        adc #$80
        lda wk_pos + 1
        adc #0
        sta see_x
        lda wk_pos + 2
        clc
        adc #$80
        lda wk_pos + 3
        adc #0
        sta see_y
        rts

; ----------------------------------------------------------------------------------------
; watch_idle: the frame loop, waiting: the checks under way go on, on their stack, until a
; frame begins (see_yield) or they're done.
;   Changes: A, X, Y.
watch_idle:
        lda task_on
        beq @none
        tsx
        stx main_sp
        ldx task_sp
        txs
        ldx task_x
        ldy task_y
@none:  rts                         ; (into the task, where it left off)

; see_yield: from inside the checks (seeing.s): if a frame has begun, back to the loop (out
; of watch_idle); it comes back here when the loop next waits.
;   Changes: A, the flags.
see_yield:
        lda task_on
        beq @on                     ; (the start's checks: no loop yet)
        lda frame_seen
        cmp wk_frame
        bne @hand
@on:    rts
@hand:  stx task_x
        sty task_y
        tsx
        stx task_sp
        ldx main_sp
        txs
        rts

; ----------------------------------------------------------------------------------------
; watch_stick: once the checks shown have a band that has seen the party, the joystick's
; let go: the party stands.
;   Changes: A.
watch_stick:
        lda shown_fight
        beq :+
        lda #$FF
        sta wk_stick
:       rts

        .segment "BSS"

b_shown:        .res SEE_BANDS_MAX      ; each band as shown: spotted or seen (figures.s)
shown_fight:    .res 1                  ; and see_fight, as shown
see_late:       .res 1                  ; checks not finished when they were to be shown
task_on:        .res 1                  ; checks under way (the task not finished)
task_wait:      .res 1                  ; frames until they're shown (0: none under way)
task_sp:        .res 1                  ; the task's stack pointer, while the loop runs
task_x:         .res 1                  ; and its X and Y
task_y:         .res 1
main_sp:        .res 1                  ; the loop's, while the task runs
