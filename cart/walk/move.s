; Walking (docs/walk.md, "The rules"): the leader moved a frame by the joystick, sliding
; along what's in the way and nudged round its corners, as tools/walk/walk.py's walk.
; Positions are in sixteenths of a pixel, the top left of the leader's 16-pixel square.

        .include "zp.inc"
        .include "walk.inc"

        .export walk_step, wk_pos, wk_stick
        .import sq_row_lo, sq_row_hi

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; walk_step: a frame's walk.
;   Takes:   wk_stick (CIA 1's port A: 0 bits pushed).
;   After:   wk_pos moved.
;   Changes: A, X, Y, zp_wk_*.
walk_step:
        ldx #0                      ; across: right +1, left -1
        lda wk_stick
        and #STICK_RIGHT
        bne :+
        inx
:       lda wk_stick
        and #STICK_LEFT
        bne :+
        dex
:       stx dx
        ldx #0                      ; down +1, up -1
        lda wk_stick
        and #STICK_DOWN
        bne :+
        inx
:       lda wk_stick
        and #STICK_UP
        bne :+
        dex
:       stx dy
        lda #SPEED                  ; slower each way on a diagonal
        ldx dx
        beq :+
        ldx dy
        beq :+
        lda #SPEED_DIAG
:       sta speed
        lda dx
        beq @down
        ldx #0
        jsr step_by
@down:  lda dy
        beq @done
        ldx #2
        jsr step_by
@done:  rts

; One axis's step: A = the direction (1, or -1 as $FF), X = the axis (0, 2).
step_by:
        stx zp_wk_axis
        tay
        lda speed
        cpy #1
        beq :+
        eor #$FF                    ; the other way: -speed
        clc
        adc #1
:       sta zp_wk_d
        ; (on into slide)

; ----------------------------------------------------------------------------------------
; slide: move along an axis; blocked, and within NUDGE pixels of a way through on the
; other axis, step toward that instead.
;   Takes:   zp_wk_axis (0 or 2), zp_wk_d (the step, signed).
;   Changes: A, X, Y, zp_wk_*.
slide:
        ldx zp_wk_axis
        ldy #0                      ; mv = pos[axis] + d
        lda zp_wk_d
        bpl :+
        dey
:       clc
        adc wk_pos, x
        sta zp_wk_mv
        tya
        adc wk_pos + 1, x
        sta zp_wk_mv + 1
        ; The body's pixels: the moved axis from mv, the other from where it is.
        jsr body_moved
        jsr fits
        bcs @blocked
        ldx zp_wk_axis
        lda zp_wk_mv
        sta wk_pos, x
        lda zp_wk_mv + 1
        sta wk_pos + 1, x
        rts
@blocked:
        lda zp_wk_axis              ; the other axis
        eor #2
        tax
        stx other
        lda wk_pos, x               ; a = p, its pixel
        sta zp_wk_a
        lda wk_pos + 1, x
        sta zp_wk_a + 1
        jsr shr4_a
        lda zp_wk_a                 ; b = c = (p + 8) & ~15, the nearest square's edge
        clc
        adc #8
        and #$F0
        sta zp_wk_b
        lda zp_wk_a + 1
        adc #0
        sta zp_wk_b + 1
        sta edge + 1
        lda zp_wk_b
        sta edge
        lda zp_wk_a                 ; p - c: -8 to 7; -8 is too far
        sec
        sbc zp_wk_b
        cmp #$F8
        beq @no
        ; Would the body fit there, moved, the other axis at c?
        jsr body_moved
        ldx other
        lda edge
        ldy edge + 1
        cpx #0
        bne :+
        sta zp_wk_fx
        sty zp_wk_fx + 1
        jmp @test
:       sta zp_wk_fy
        sty zp_wk_fy + 1
@test:  jsr fits
        bcs @no
        ; gap = 16 c - pos[other]
        lda edge
        sta zp_wk_b
        lda edge + 1
        sta zp_wk_b + 1
        asl zp_wk_b
        rol zp_wk_b + 1
        asl zp_wk_b
        rol zp_wk_b + 1
        asl zp_wk_b
        rol zp_wk_b + 1
        asl zp_wk_b
        rol zp_wk_b + 1
        ldx other
        lda zp_wk_b
        sec
        sbc wk_pos, x
        sta zp_wk_b
        lda zp_wk_b + 1
        sbc wk_pos + 1, x
        sta zp_wk_b + 1             ; (a byte's worth either way: within 143)
        ; step = min(|d|, |gap|)
        lda zp_wk_d
        bpl :+
        eor #$FF
        clc
        adc #1
:       sta zp_wk_t                 ; |d|
        lda zp_wk_b + 1
        bmi @back
        lda zp_wk_b                 ; forward: +min
        cmp zp_wk_t
        bcc :+
        lda zp_wk_t
:       clc
        adc wk_pos, x
        sta wk_pos, x
        bcc @no
        inc wk_pos + 1, x
@no:    rts
@back:  lda zp_wk_b                 ; back: -min(|d|, -gap)
        eor #$FF
        clc
        adc #1
        cmp zp_wk_t
        bcc :+
        lda zp_wk_t
:       sta zp_wk_t
        lda wk_pos, x
        sec
        sbc zp_wk_t
        sta wk_pos, x
        bcs :+
        dec wk_pos + 1, x
:       rts

; fx, fy: the body's pixels, the moved axis's from mv, the other's from wk_pos.
body_moved:
        lda zp_wk_mv
        sta zp_wk_a
        lda zp_wk_mv + 1
        sta zp_wk_a + 1
        jsr shr4_a
        lda zp_wk_axis
        eor #2
        tax
        lda wk_pos, x
        sta zp_wk_b
        lda wk_pos + 1, x
        sta zp_wk_b + 1
        lsr zp_wk_b + 1
        ror zp_wk_b
        lsr zp_wk_b + 1
        ror zp_wk_b
        lsr zp_wk_b + 1
        ror zp_wk_b
        lsr zp_wk_b + 1
        ror zp_wk_b
        lda zp_wk_axis
        bne @y
        lda zp_wk_a                 ; moved across
        sta zp_wk_fx
        lda zp_wk_a + 1
        sta zp_wk_fx + 1
        lda zp_wk_b
        sta zp_wk_fy
        lda zp_wk_b + 1
        sta zp_wk_fy + 1
        rts
@y:     lda zp_wk_a                 ; moved down
        sta zp_wk_fy
        lda zp_wk_a + 1
        sta zp_wk_fy + 1
        lda zp_wk_b
        sta zp_wk_fx
        lda zp_wk_b + 1
        sta zp_wk_fx + 1
        rts

; a >>= 4 (sixteenths to pixels).
shr4_a:
        lsr zp_wk_a + 1
        ror zp_wk_a
        lsr zp_wk_a + 1
        ror zp_wk_a
        lsr zp_wk_a + 1
        ror zp_wk_a
        lsr zp_wk_a + 1
        ror zp_wk_a
        rts

; ----------------------------------------------------------------------------------------
; fits: the body at pixel (fx, fy) stands only on squares you can stand on.
;   Takes:   zp_wk_fx, zp_wk_fy.
;   After:   carry clear if it fits, set if not.
;   Changes: A, X, Y, zp_wk_ptr, zp_wk_x0-y1, zp_wk_a.
fits:
        ldx #0
        jsr squares_of              ; x0, x1
        sta zp_wk_x0
        sty zp_wk_x1
        ldx #2
        jsr squares_of
        sta zp_wk_y0
        sty zp_wk_y1
        ldx zp_wk_y0
@row:   lda sq_row_lo, x
        sta zp_wk_ptr
        lda sq_row_hi, x
        sta zp_wk_ptr + 1
        ldy zp_wk_x0
@sq:    lda (zp_wk_ptr), y
        bmi @no
        cpy zp_wk_x1
        iny
        bcc @sq
        cpx zp_wk_y1
        inx
        bcc @row
        clc
        rts
@no:    sec
        rts

; The squares under the body along an axis (X = 0: fx, 2: fy): A = (f + BODY_LO) >> 4,
; Y = (f + BODY_HI) >> 4.
squares_of:
        lda zp_wk_fx, x
        clc
        adc #BODY_HI
        sta zp_wk_a
        lda zp_wk_fx + 1, x
        adc #0
        sta zp_wk_a + 1
        jsr shr4_a
        ldy zp_wk_a
        lda zp_wk_fx, x
        clc
        adc #BODY_LO
        sta zp_wk_a
        lda zp_wk_fx + 1, x
        adc #0
        sta zp_wk_a + 1
        jsr shr4_a
        lda zp_wk_a
        rts

        .segment "BSS"

wk_pos:     .res 4              ; the leader: x, y, in sixteenths of a pixel
wk_stick:   .res 1              ; the joystick this frame
dx:         .res 1              ; its directions: -1, 0, 1
dy:         .res 1
speed:      .res 1
other:      .res 1              ; slide: the other axis...
edge:       .res 2              ; ...and the edge of a way through on it, in pixels
