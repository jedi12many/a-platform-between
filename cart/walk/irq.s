; The walking engine's raster interrupts (docs/walk.md, "A frame" and "The border"): a
; frame's are border.s's bottom, HUD, world and top, and the sprites' events between (mux.s);
; irq_kind says which comes next. The vector is TRAMPOLINE's jmp, so that its high byte,
; $FFFF, the byte the idle VIC shows, is $FF: black. They use no zero page but mux.s's.

        .include "hw.inc"
        .include "walk.inc"

        .export irq, nmi, irq_out
        .export wk_frame, wk_busy, wk_pending, wk_late, wk_d016, wk_d011, wk_d018, wk_swap
        .export prog_shown
        .import mux_a, mux_b, irq_kind, bottom, hud_irq, world_irq, top_irq

        .segment "HIGH"

irq:    pha
        txa
        pha
        tya
        pha
        lda #$FF
        sta VIC_IRQ
        ldx irq_kind
        lda kinds + 1, x
        pha
        lda kinds, x
        pha
        rts                         ; (to the kind's code)
irq_out:
        pla
        tay
        pla
        tax
        pla
nmi:    rti

kinds:  .word bottom - 1, mux_a - 1, mux_b - 1, hud_irq - 1, world_irq - 1, top_irq - 1

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
