; The walking engine's start and its frame loop (docs/walk.md): RUN (a BASIC line, SYS
; 2061) comes here. It takes the machine (the KERNAL and BASIC out, their interrupts off),
; writes the scroller's code (gen.s), puts the floor's look in, draws the screen where the
; camera starts, and walks: each frame, the joystick, the walk, the camera.

        .include "hw.inc"
        .include "zp.inc"
        .include "walk.inc"

        .export walk_start, wk_awake, wk_done
        .import irq, nmi, gen_all, floor, walk_step, wk_pos, wk_stick
        .import camera_init, camera_step, wk_cam, wk_front
        .import wk_frame, wk_busy, wk_pending, wk_late, wk_d016, wk_d011, wk_d018, wk_swap
        .import edge_mode, edge_base, wk_ncx, wk_ncy, draw_all, maps_build
        .import figures_init, figures_step, sprites_frame, prog_next, prog_shown
        .import __BSS_RUN__, __BSS_SIZE__

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
        lda #<irq
        sta VEC_IRQ
        lda #>irq
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
        jsr look_in                 ; (before gen_all writes over the program's top)
        jsr shapes_in
        jsr gen_all
        jsr maps_build
        ; The leader on the start's square.
        lda #0
        sta wk_pos
        sta wk_pos + 2
        lda floor + FL_START        ; x 256: a square is 16 pixels of 16
        sta wk_pos + 1
        lda floor + FL_START + 1
        sta wk_pos + 3
        jsr camera_init
        jsr figures_init
        ; The screen where the camera is: A's characters, the shadow's colours, shown.
        jsr cam_cells
        lda #<SCREEN_A
        sta edge_base
        lda #>SCREEN_A
        sta edge_base + 1
        lda #0
        sta edge_mode
        jsr draw_all
        lda #<SHADOW
        sta edge_base
        lda #>SHADOW
        sta edge_base + 1
        lda #1
        sta edge_mode
        jsr draw_all
        jsr BLAST
        jsr BLAST + SECOND_HALF
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
        tax
        jsr sprites_frame
        lda #VB_LINE
        sta VIC_RASTER
        lda wk_d011                 ; the screen on
        sta VIC_CTRL1
        lda #$FF
        sta VIC_IRQ
        lda #1
        sta VIC_IRQ_ENA
        cli
        ; fall into the loop

; ----------------------------------------------------------------------------------------
; The frame loop: each frame, once the interrupt has begun it, the joystick, the walk and
; the camera; then what it decided waits for the next frame's interrupt.
loop:   lda wk_frame
:       cmp wk_frame
        beq :-
wk_awake:
        lda #1
        sta wk_busy
        lda CIA1_PRA
        sta wk_stick
        jsr walk_step
        jsr camera_step
        jsr figures_step
wk_done:
        sei
        lda #1
        sta wk_pending
        lda #0
        sta wk_busy
        cli
        jmp loop

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
