; The walking engine's raster interrupt (docs/walk.md, "A frame"), at line 250, under the
; screen's 24 rows: a frame begins. It counts it; if the frame loop has finished the last
; one (wk_pending), it shows what that one decided: the fine scroll, the screen, and on a
; coarse step the colours, copied from the shadow top first, ahead of the raster (BLAST,
; about 8,000 cycles: done by line 51, where the screen starts again, but for its last
; rows, which the raster reaches long after). If the loop is still busy, the frame is late:
; nothing changes, and wk_late counts it. It uses no zero page.

        .include "hw.inc"
        .include "walk.inc"

        .export irq, nmi
        .export wk_frame, wk_busy, wk_pending, wk_late, wk_d016, wk_d011, wk_d018, wk_swap

        .segment "CODE"

irq:    pha
        txa
        pha
        tya
        pha
        lda #$FF
        sta VIC_IRQ
        inc wk_frame
        bne :+
        inc wk_frame + 1
:       lda wk_busy
        beq @free
        inc wk_late
        jmp @out
@free:  lda wk_pending
        beq @out
        lda wk_d016
        sta VIC_CTRL2
        lda wk_d011
        sta VIC_CTRL1
        lda wk_d018
        sta VIC_MEM
        lda #0
        sta wk_pending
        lda wk_swap
        beq @out
        lda #0
        sta wk_swap
        jsr BLAST
@out:   pla
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
