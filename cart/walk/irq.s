; The walking engine's raster interrupt (docs/walk.md, "A frame"). Two kinds (mux.s's
; irq_kind): an event's, for the sprites (mux_a, mux_b), and the frame's, at line 250, under the
; screen's 24 rows: a frame begins. It counts it; if the frame loop has finished the last
; one (wk_pending), it shows what that one decided: the fine scroll, the screen, the
; sprites' program; then it sets the sprites for the frame (sprites_frame); and on a coarse
; step's swap, it copies the colours from the shadow, top first, ahead of the raster
; (BLAST, about 8,200 cycles), with interrupts on again, so the sprites' events can come
; in the middle of it. If the loop is still busy, the frame is late: nothing new is shown,
; and wk_late counts it. It uses no zero page.

        .include "hw.inc"
        .include "walk.inc"

        .export irq, nmi, irq_out
        .export wk_frame, wk_busy, wk_pending, wk_late, wk_d016, wk_d011, wk_d018, wk_swap
        .export prog_shown
        .import sprites_frame, mux_a, mux_b, irq_kind, prog_next

        .segment "CODE"

irq:    pha
        txa
        pha
        tya
        pha
        lda #$FF
        sta VIC_IRQ
        lda irq_kind
        beq @frame
        lsr a
        bcc :+
        jmp mux_a                   ; 1: program A's event
:       jmp mux_b                   ; 2: B's
@frame: inc wk_frame
        bne :+
        inc wk_frame + 1
:       lda wk_busy
        beq @free
        inc wk_late
        jmp @sprites
@free:  lda wk_pending
        beq @sprites
        lda wk_d016
        sta VIC_CTRL2
        lda wk_d011
        sta VIC_CTRL1
        lda wk_d018
        sta VIC_MEM
        lda prog_next
        sta prog_shown
        lda #0
        sta wk_pending
@sprites:
        ldx prog_shown
        jsr sprites_frame
        lda wk_swap
        beq irq_out
        lda #0
        sta wk_swap
        cli                         ; (the sprites' events may come while the colours copy)
        jsr BLAST
        jsr BLAST + SECOND_HALF
irq_out:
        pla
        tay
        pla
        tax
        pla
nmi:    rti

        .segment "BSS"

wk_frame:   .res 2              ; frames begun (the loop watches the low byte)
wk_busy:    .res 1              ; the frame loop is working on one
wk_pending: .res 1              ; it has: show what it decided at the next frame
wk_late:    .res 1              ; frames the loop was late for
wk_d016:    .res 1              ; what it decided: the registers...
wk_d011:    .res 1
wk_d018:    .res 1
wk_swap:    .res 1              ; ...and whether the colours are copied (a coarse step)
prog_shown: .res 1              ; the sprites' program shown (figures.s makes them)
