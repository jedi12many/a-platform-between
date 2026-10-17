; The camera and the scroller (docs/walk.md, "The camera", "The scroller"): each frame, the
; camera eases toward the leader; when it would cross into the next character, the screen
; it'll show is made over five frames, as tools/walk/walk.py's play does:
;
;   IDLE      the step found: the shown screen's first half copied into the other, shifted
;             (SHIFT_AB or SHIFT_BA); the camera held in its cell
;   HALF      the rest of it, and the new edges drawn (edge.s); still held
;   SHIFTED   the colours' copies aimed at the rows to be shown (colours.s); still held
;   SHADED    the camera into the new cell; the interrupt swaps the screens at the next
;             frame, and the frame loop, done, copies each row's colours as the raster
;             passes it (colours.s)
;   COLOURED  the frame of the swap: its interrupt copied the rest; nothing heavy; the
;             camera held in its (new) cell
;
; A frame's camera is shown from the next (the interrupt sets the registers).

        .include "hw.inc"
        .include "zp.inc"
        .include "walk.inc"

        .export camera_init, camera_step, wk_cam, wk_stage, wk_front, wk_dir
        .import wk_pos, wk_d016, wk_d011, wk_d018, wk_swap
        .import edge_base, wk_ncx, wk_ncy, edges, colour_aim, wk_w, wk_h

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; camera_init: the camera where the leader wants it, nothing under way, screen A shown.
;   Changes: A, X, Y, zp_wk_a.
camera_init:
        ldx #0                      ; its most: 16 w - 313 across, 16 h - 193 down (the
        lda wk_w                    ; screen's 40 x 25 characters on the area)
        jsr most_of
        ldx #2
        lda wk_h
        jsr most_of
        jsr target
        ldx #3
:       lda want, x
        sta wk_cam, x
        dex
        bpl :-
        lda #IDLE
        sta wk_stage
        lda #0
        sta wk_front
        jsr cells_of_cam
        jmp registers

; most[X] = 16 A - (X = 0: 313, 2: 193): (2 A - 40 or 25) x 8 + 7.
most_of:
        sta most, x
        lda #0
        sta most + 1, x
        ldy #4
:       asl most, x
        rol most + 1, x
        dey
        bne :-
        lda most, x
        sec
        sbc less, x
        sta most, x
        lda most + 1, x
        sbc less + 1, x
        sta most + 1, x
        rts

; ----------------------------------------------------------------------------------------
; camera_step: a frame's camera, and the scroller's work.
;   Before:  wk_pos is this frame's; the interrupt has shown the last frame's decision.
;   After:   wk_cam is the next frame's, and wk_d016, wk_d011, wk_d018 and wk_swap say how.
;   Changes: A, X, Y, zp_wk_*.
camera_step:
        jsr target
        ldx #0
        jsr ease
        ldx #2
        jsr ease
        jsr cells_of_cam
        lda wk_stage
        cmp #SHIFTED
        bne :+
        jmp @shifted
:       cmp #SHADED
        bne :+
        jmp @shaded
:       cmp #HALF
        bne :+
        jmp @half
:       cmp #COLOURED
        bne @idle
        lda #IDLE                   ; the swap's frame: rest
        sta wk_stage
        jmp @hold
@idle:  ldx #0                      ; the step: each axis's cell, next against now
        jsr cell_step
        sta wk_dir
        ldx #2
        jsr cell_step
        sta wk_dir + 1
        ora wk_dir
        bne :+
        jmp @commit                 ; still in its cell
:       lda wk_dir + 1              ; X = the shift + 41: across + 40 down
        beq @across
        bmi :+
        lda #40 + OFFSET_BIAS
        bne @plus
:       lda #OFFSET_BIAS - 40
        bne @plus
@across:
        lda #OFFSET_BIAS
@plus:  clc
        adc wk_dir
        sta shift_x
        tax
        lda wk_front                ; the shown screen's first half into the other
        bne :+
        jsr SHIFT_AB
        jmp :++
:       jsr SHIFT_BA
:       lda #HALF
        sta wk_stage
        jmp @hold
@half:  ldx shift_x                 ; the rest
        lda wk_front
        bne :+
        jsr SHIFT_AB + SECOND_HALF
        jmp :++
:       jsr SHIFT_BA + SECOND_HALF
:       lda #SHIFTED
        sta wk_stage
@hold:  ldx #0                      ; held in the cell it's in
        lda cell
        jsr clamp
        ldx #2
        lda cell + 1
        jsr clamp
        jmp @commit
@shifted:
        lda wk_front                ; the new edges, into the screen being made
        bne :+
        lda #<SCREEN_B
        ldx #>SCREEN_B
        jmp @edges
:       lda #<SCREEN_A
        ldx #>SCREEN_A
@edges: sta edge_base
        stx edge_base + 1
        jsr new_cells
        jsr edges
        jsr colour_aim              ; the colours' copies aimed at the new rows (those whose
        lda #SHADED                 ; row of squares changed: none, a step across; every
        sta wk_stage                ; other one, a step down or up)
        jmp @hold
@shaded:
        lda #COLOURED
        sta wk_stage
        lda #1                      ; the swap, and the colours, at the next frame
        sta wk_swap
        lda wk_front
        eor #1
        sta wk_front
        ldx #0                      ; into the new cell
        lda wk_ncx
        jsr clamp
        ldx #2
        lda wk_ncy
        jsr clamp
@commit:
        ldx #3
:       lda next, x
        sta wk_cam, x
        dex
        bpl :-
        ; fall into registers

; The registers for wk_cam: the fine scroll, 7 - (cam & 7) each way, and the screen.
registers:
        lda wk_cam
        and #7
        eor #7
        ora #CTRL2_WALK
        sta wk_d016
        lda wk_cam + 2
        and #7
        eor #7
        ora #CTRL1_VIEW
        sta wk_d011
        lda #MEM_A
        ldx wk_front
        beq :+
        lda #MEM_B
:       sta wk_d018
        rts

; want: where the leader wants the camera: their middle in the view's, kept on the area.
target:
        ldx #0
        jsr target_axis
        ldx #2
        ; (on into target_axis)
; X = 0 across, 2 down: want = (pos >> 4) + 8 - half the view, within 0 and the most.
target_axis:
        lda wk_pos, x
        sta zp_wk_a
        lda wk_pos + 1, x
        sta zp_wk_a + 1
        ldy #4
:       lsr zp_wk_a + 1
        ror zp_wk_a
        dey
        bne :-
        lda zp_wk_a                 ; - (half - 8)
        sec
        sbc half_less_8, x
        sta zp_wk_a
        lda zp_wk_a + 1
        sbc half_less_8 + 1, x
        sta zp_wk_a + 1
        bcs :+                      ; below 0: 0
        lda #0
        sta zp_wk_a
        sta zp_wk_a + 1
:       lda most, x                 ; over the most: the most
        cmp zp_wk_a
        lda most + 1, x
        sbc zp_wk_a + 1
        bcs :+
        lda most, x
        sta zp_wk_a
        lda most + 1, x
        sta zp_wk_a + 1
:       lda zp_wk_a
        sta want, x
        lda zp_wk_a + 1
        sta want + 1, x
        rts

; next[X] = the camera eased toward want: an eighth of the way, at least 1, at most 2.
ease:
        lda want, x                 ; a = want - cam
        sec
        sbc wk_cam, x
        sta zp_wk_a
        lda want + 1, x
        sbc wk_cam + 1, x
        sta zp_wk_a + 1
        ora zp_wk_a
        bne :+
        lda wk_cam, x               ; there: stay
        sta next, x
        lda wk_cam + 1, x
        sta next + 1, x
        rts
:       lda zp_wk_a + 1
        sta zp_wk_t                 ; (its sign)
        bpl :+
        lda #0                      ; |a|
        sec
        sbc zp_wk_a
        sta zp_wk_a
        lda #0
        sbc zp_wk_a + 1
        sta zp_wk_a + 1
:       lsr zp_wk_a + 1             ; |a| >> 3, kept to 1-2
        ror zp_wk_a
        lsr zp_wk_a + 1
        ror zp_wk_a
        lsr zp_wk_a + 1
        ror zp_wk_a
        lda zp_wk_a + 1
        bne @two
        lda zp_wk_a
        beq @one
        cmp #2
        bcc @one
@two:   lda #2
        bne @step
@one:   lda #1
@step:  ldy zp_wk_t
        bmi @back
        clc
        adc wk_cam, x
        sta next, x
        lda wk_cam + 1, x
        adc #0
        sta next + 1, x
        rts
@back:  sta zp_wk_t
        lda wk_cam, x
        sec
        sbc zp_wk_t
        sta next, x
        lda wk_cam + 1, x
        sbc #0
        sta next + 1, x
        rts

; cell: the camera's character cell now (cam >> 3), across and down.
cells_of_cam:
        ldx #0
        jsr cam_cell
        sta cell
        ldx #2
        jsr cam_cell
        sta cell + 1
        rts

; A = wk_cam[X] >> 3 (it's under 2048).
cam_cell:
        lda wk_cam + 1, x
        sta zp_wk_a + 1
        lda wk_cam, x
        ldy #3
:       lsr zp_wk_a + 1
        ror a
        dey
        bne :-
        rts

; A = next[X]'s cell - cam[X]'s: -1, 0 or 1 (it moves 2 pixels at most).
cell_step:
        lda next, x
        sta zp_wk_a
        lda next + 1, x
        sta zp_wk_a + 1
        ldy #3
:       lsr zp_wk_a + 1
        ror zp_wk_a
        dey
        bne :-
        lda zp_wk_a
        sec
        cpx #0
        bne :+
        sbc cell
        rts
:       sbc cell + 1
        rts

; The cells the screen will show after this step: wk_ncx, wk_ncy.
new_cells:
        lda cell
        clc
        adc wk_dir
        sta wk_ncx
        lda cell + 1
        clc
        adc wk_dir + 1
        sta wk_ncy
        rts

; next[X] kept within cell A's eight pixels.
clamp:
        sta zp_wk_a                 ; a = 8 cell
        lda #0
        sta zp_wk_a + 1
        asl zp_wk_a
        rol zp_wk_a + 1
        asl zp_wk_a
        rol zp_wk_a + 1
        asl zp_wk_a
        rol zp_wk_a + 1
        lda next, x                 ; below it: its first pixel
        cmp zp_wk_a
        lda next + 1, x
        sbc zp_wk_a + 1
        bcs :+
        lda zp_wk_a
        sta next, x
        lda zp_wk_a + 1
        sta next + 1, x
        rts
:       lda zp_wk_a                 ; past it: its last
        ora #7
        sta zp_wk_a
        cmp next, x
        lda zp_wk_a + 1
        sbc next + 1, x
        bcs :+
        lda zp_wk_a
        sta next, x
        lda zp_wk_a + 1
        sta next + 1, x
:       rts

        .segment "DATA"

half_less_8:
        .word HALF_VIEW_X - 8, HALF_VIEW_Y - 8
less:   .word 313, 193              ; (40 x 8 - 7, 25 x 8 - 7)

        .segment "BSS"

wk_cam:     .res 4              ; the camera: x, y, the area's pixel at the view's top left
most:       .res 4              ; its most, across and down: the floor's (camera_init)
wk_stage:   .res 1              ; IDLE, HALF, SHIFTED, SHADED or COLOURED
wk_front:   .res 1              ; the screen shown: 0 A, 1 B
want:       .res 4              ; where the leader wants it
next:       .res 4              ; where it'll be next frame
cell:       .res 2              ; its character cell now, across and down
wk_dir:     .res 2              ; the step under way: -1, 0 or 1 each way
shift_x:    .res 1              ; and its X for the copying code
