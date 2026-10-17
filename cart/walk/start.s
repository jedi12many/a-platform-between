; The walking engine's start and its frame loop (docs/walk.md): RUN (a BASIC line, SYS
; 2061) comes here. It takes the machine (the KERNAL and BASIC out, their interrupts off),
; writes the scroller's code (gen.s), puts the floor's look in, draws the screen where the
; camera starts, and walks: each frame, the joystick, the walk, the camera.

        .include "hw.inc"
        .include "zp.inc"
        .include "walk.inc"

        .export walk_start, wk_awake, wk_joy, wk_done, frame_seen
        .import irq, nmi, gen_all, floor, walk_step, wk_pos, wk_stick
        .import camera_init, camera_step, wk_cam, wk_front
        .import wk_frame, wk_busy, wk_pending, wk_late, wk_d016, wk_d011, wk_d018, wk_swap
        .import edge_base, wk_ncx, wk_ncy, draw_all, maps_build
        .import watch_init, watch_step, watch_stick, watch_idle
        .import figures_init, figures_step, prog_next, prog_shown, view_d011, screen_b
        .import precopy, colour_row, aim_all
        .import world_irq
        .import __BSS_RUN__, __BSS_SIZE__, __HIGH_LOAD__, __HIGH_RUN__, __HIGH_SIZE__
        .import __DATA_RUN__, __DATA_SIZE__, __SQUARES_LOAD__, __SQUARES_SIZE__
        .import __SEEING_LOAD__, __SEEING_RUN__, __SEEING_SIZE__

        .assert __DATA_RUN__ + __DATA_SIZE__ <= SHIFT_AB, lderror, "the program runs past $27FF"
        .assert __SQUARES_LOAD__ + __SQUARES_SIZE__ <= SHIFT_BA, lderror, "the squares load past $3FFF"
        .assert __SEEING_LOAD__ + __SEEING_SIZE__ <= COLOUR_MAP, lderror, "seeing loads past $7BFF"

        .segment "LOADADDR"
        .word $0801

        .segment "STUB"
        .word @end, 10              ; 10 SYS 2061
        .byte $9E, "2061", 0
@end:   .word 0

; ----------------------------------------------------------------------------------------
; walk_start: the program.
;   Before:  loaded at $0801, run (the KERNAL's port, $37).
;   After:   never returns.
walk_start:
        sei
        ldx #$FF                    ; the stack from the top: the loop's $0180-$01FF, seeing's
        txs                         ; checks' below it (watch.s)
        lda #PORT_GAME              ; RAM but the I/O
        sta CPU_PORT
        lda #$7F                    ; the CIAs' interrupts off
        sta CIA1_ICR
        sta CIA2_ICR
        lda CIA1_ICR
        lda CIA2_ICR
        lda CIA2_DDRA               ; the VIC in bank 3
        ora #%00000011
        sta CIA2_DDRA
        lda CIA2_PRA
        and #%11111100
        sta CIA2_PRA
        lda #$FF                    ; the keyboard's rows out, none chosen: port A reads
        sta CIA1_DDRA               ; the joystick in port 2
        sta CIA1_PRA
        lda #CTRL1_BLANK            ; the screen off while it's set up
        sta VIC_CTRL1
        lda #0
        sta VIC_IRQ_ENA
        lda #$4C                    ; the vector: TRAMPOLINE's jmp irq (so $FFFF is $FF)
        sta TRAMPOLINE
        lda #<world_irq             ; (the first: below)
        sta TRAMPOLINE + 1
        lda #>world_irq
        sta TRAMPOLINE + 2
        lda #<TRAMPOLINE
        sta VEC_IRQ
        lda #>TRAMPOLINE
        sta VEC_IRQ + 1
        lda #<nmi
        sta VEC_NMI
        lda #>nmi
        sta VEC_NMI + 1
        ; The variables, cleared.
        lda #<__BSS_RUN__
        sta zp_wk_out
        lda #>__BSS_RUN__
        sta zp_wk_out + 1
        ldx #>(__BSS_SIZE__ + 255)
        lda #0
        tay
:       sta (zp_wk_out), y
        iny
        bne :-
        inc zp_wk_out + 1
        dex
        bne :-
        ; The interrupts' code up to $F200, seeing's to $E000 (before gen_all writes over
        ; the program's top).
        lda #<__HIGH_LOAD__
        sta zp_wk_src
        lda #>__HIGH_LOAD__
        sta zp_wk_src + 1
        lda #<__HIGH_RUN__
        sta zp_wk_dst
        lda #>__HIGH_RUN__
        sta zp_wk_dst + 1
        ldx #>(__HIGH_SIZE__ + 255)
        jsr copy_pages
        lda #<__SEEING_LOAD__
        sta zp_wk_src
        lda #>__SEEING_LOAD__
        sta zp_wk_src + 1
        lda #<__SEEING_RUN__
        sta zp_wk_dst
        lda #>__SEEING_RUN__
        sta zp_wk_dst + 1
        ldx #>(__SEEING_SIZE__ + 255)
        jsr copy_pages
        jsr maps_build              ; (the squares, the floor's size: before gen_all writes
        jsr look_in                 ; over the program's top, where the squares and HIGH
        jsr shapes_in               ; were loaded)
        jsr gen_all
        ; The leader on the start's square.
        lda #0
        sta wk_pos
        sta wk_pos + 2
        lda floor + FL_START        ; x 256: a square is 16 pixels of 16
        sta wk_pos + 1
        lda floor + FL_START + 1
        sta wk_pos + 3
        jsr camera_init
        jsr watch_init              ; (seeing's first check: before the first figures)
        jsr figures_init
        ; The screen where the camera is: A's characters, the colours, shown.
        jsr cam_cells
        lda #<SCREEN_A
        sta edge_base
        lda #>SCREEN_A
        sta edge_base + 1
        jsr draw_all
        jsr aim_all                 ; and the colours
        ldx #0
:       jsr colour_row
        inx
        cpx #ROWS
        bne :-
        lda wk_d016
        sta VIC_CTRL2
        lda wk_d018
        sta VIC_MEM
        lda #$FF                    ; the sprites: multicolour, in front, the first program
        sta VIC_SPR_MULTI
        lda #0
        sta VIC_SPR_TALL
        sta VIC_SPR_WIDE
        sta VIC_SPR_BEHIND
        lda #SPRITE_MC1
        sta VIC_SPR_MC1
        lda #SPRITE_MC2
        sta VIC_SPR_MC2
        lda prog_next
        sta prog_shown
        lda #0
        sta screen_b
        lda wk_d011
        sta view_d011
        lda #WORLD_LINE             ; the first interrupt: the world's sprites, at line 1
                                    ; (border.s)
        sta VIC_RASTER
        lda wk_d011                 ; the screen on: the band (black), till the view
        and #7
        ora #CTRL1_BAND
        sta VIC_CTRL1
        lda #$FF
        sta VIC_IRQ
        lda #1
        sta VIC_IRQ_ENA
        cli
        ; fall into the loop

; ----------------------------------------------------------------------------------------
; The frame loop: each frame, once the interrupt has begun it, the joystick, the walk and
; the camera; then what it decided waits for the next frame's interrupt (and seeing's
; checks, if some are under way, go on meanwhile: watch.s).
loop:   lda frame_seen              ; (the frame last handled, not the count now: precopy
        cmp wk_frame                ; returns once the next has begun)
        bne :+
        jsr watch_idle
        jmp loop
:       lda wk_frame
        sta frame_seen
wk_awake:
        lda #1
        sta wk_busy
        lda CIA1_PRA
wk_joy: sta wk_stick                ; (the VICE check sets A here: tests/walk/vice_walk.py)
        jsr watch_stick
        jsr walk_step
        jsr watch_step
        jsr camera_step
        jsr figures_step
wk_done:
        sei
        lda #1
        sta wk_pending
        lda #0
        sta wk_busy
        cli
        lda wk_swap                 ; a step's swap at the next bottom: its colours copied
        beq :+                      ; behind the raster meanwhile (colours.s)
        jsr precopy
:       jmp loop

; The look: its colours, and its characters at WALK_CHARS (2 KB from the floor's).
look_in:
        lda #BORDER_COLOUR
        sta VIC_BORDER
        lda floor + FL_COLOURS
        sta VIC_BACK
        lda floor + FL_COLOURS + 1
        sta VIC_MC1
        lda floor + FL_COLOURS + 2
        sta VIC_MC2
        lda #<(floor + FL_CHARS)
        sta zp_wk_src
        lda #>(floor + FL_CHARS)
        sta zp_wk_src + 1
        lda #<WALK_CHARS
        sta zp_wk_dst
        lda #>WALK_CHARS
        sta zp_wk_dst + 1
        ldx #8
        ldy #0
:       lda (zp_wk_src), y
        sta (zp_wk_dst), y
        iny
        bne :-
        inc zp_wk_src + 1
        inc zp_wk_dst + 1
        dex
        bne :-
        rts

; The sprite shapes, from the floor's to SPRITE_SHAPES, under the I/O (the RAM there
; written with the I/O out for a moment): 2 KB.
shapes_in:
        lda #<(floor + FL_SHAPES)
        sta zp_wk_src
        lda #>(floor + FL_SHAPES)
        sta zp_wk_src + 1
        lda #<SPRITE_SHAPES
        sta zp_wk_dst
        lda #>SPRITE_SHAPES
        sta zp_wk_dst + 1
        lda #PORT_ALL_RAM
        sta CPU_PORT
        ldx #8
        ldy #0
:       lda (zp_wk_src), y
        sta (zp_wk_dst), y
        iny
        bne :-
        inc zp_wk_src + 1
        inc zp_wk_dst + 1
        dex
        bne :-
        lda #0                      ; the empty shape (the asset stops at the HUD's)
        ldy #63
:       sta SPRITE_SHAPES + (BLANK_SHAPE - SHAPE_POINTER) * 64, y
        dey
        bpl :-
        lda #PORT_GAME
        sta CPU_PORT
        rts

; wk_ncx, wk_ncy: the camera's cell (the screen's top left on the area).
cam_cells:
        ldx #0
        jsr cell_of
        sta wk_ncx
        ldx #2
        jsr cell_of
        sta wk_ncy
        rts
cell_of:
        lda wk_cam + 1, x
        sta zp_wk_t
        lda wk_cam, x
        lsr zp_wk_t
        ror a
        lsr zp_wk_t
        ror a
        lsr zp_wk_t
        ror a
        rts

; copy_pages: X pages from (zp_wk_src) to (zp_wk_dst).
;   Changes: A, X, Y; zp_wk_src, zp_wk_dst.
copy_pages:
        ldy #0
:       lda (zp_wk_src), y
        sta (zp_wk_dst), y
        iny
        bne :-
        inc zp_wk_src + 1
        inc zp_wk_dst + 1
        dex
        bne :-
        rts

        .segment "BSS"

frame_seen: .res 1              ; the frame loop's last frame (wk_frame's low byte)
