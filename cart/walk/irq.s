; The walking engine's raster interrupts (docs/walk.md, "A frame" and "The border"): a
; frame's are border.s's bottom, HUD, world and top, and the sprites' events between (mux.s).
; The vector is TRAMPOLINE's JMP, so that its high byte, $FFFF, the byte the idle VIC shows,
; is $FF: black; each handler points the JMP at the next (irq.inc). They use no zero page
; but mux.s's.

        .include "hw.inc"
        .include "walk.inc"

        .export irq, nmi, irq_out
        .export wk_frame, wk_busy, wk_pending, wk_late, wk_d016, wk_d011, wk_d018, wk_swap
        .export prog_shown
        .import bottom_irq

        .segment "HIGH"

irq = bottom_irq                    ; (the harness's name for the way in)

; Every handler's end (they're entered by irq.inc's ENTER).
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
