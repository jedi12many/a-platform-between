; The sprite multiplexer's interrupt side (docs/walk.md, "The figures"): the shown
; program (figures.s: PROG_A or PROG_B) carried out. At the frame's start (sprites_frame,
; from irq.s's interrupt at line 250) its first eight are set, as the VIC has them, by code
; unrolled for each program; then each event at its line: a sprite set again for the next
; figure down, once the last one it showed has ended. An event's interrupt sets every
; event due by the next line, and asks for the next one's line, or line 250 again when
; there are none. Its loads have the shown program's page patched in. No zero page.

        .include "hw.inc"
        .include "walk.inc"

        .export sprites_frame, mux_irq, irq_kind
        .import irq_out

        .segment "CODE"

; The first eight from program BASE, and its counts.
.macro APPLY base
        .repeat 8, n
        lda base + P_X + n
        sta VIC_SPR_X + 2 * n
        lda base + P_Y + n
        sta VIC_SPR_Y + 2 * n
        lda base + P_PTR + n
        sta POINTERS_A + n
        sta POINTERS_B + n
        lda base + P_COLOUR + n
        sta VIC_SPR_COLOUR + n
        .endrepeat
        lda base + P_ENABLE
        sta VIC_SPR_ENA
        lda base + P_X_HIGHS
        sta VIC_SPR_X_HIGH
        lda base + P_COUNT
        sta ev_left
        lda base + P_EVENTS + E_LINE
        sta first_line
.endmacro

; ----------------------------------------------------------------------------------------
; sprites_frame: program X (0 PROG_A, 1 PROG_B) shown: its first eight set, its page
; patched into the events' loads, and the first event's interrupt asked for.
;   Before:  in the interrupt at line 250, interrupts off.
;   Changes: A, X, Y.
sprites_frame:
        txa
        beq :+
        jmp @b
:       APPLY PROG_A
        lda #>PROG_A
        jmp @patch
@b:     APPLY PROG_B
        lda #>PROG_B
@patch: ldx #LOADS - 1
:       ldy load_at, x              ; (each load's address's high byte is in this page)
        sta mux_irq, y
        dex
        bpl :-
        lda #P_EVENTS
        sta ev_off
        lda ev_left
        beq @none
        lda #1
        sta irq_kind
        lda first_line
        sta VIC_RASTER
        rts
@none:  lda #0
        sta irq_kind
        lda #VB_LINE
        sta VIC_RASTER
        rts

; ----------------------------------------------------------------------------------------
; mux_irq: an event's interrupt (irq.s comes here when irq_kind is 1): every event due by
; the next line set, then the next one's line asked for (or line 250's).
;   Before:  A, X and Y pushed; the interrupt acknowledged.
mux_irq:
mx_one:   ldx ev_off
l1:     lda PROG_A + E_SPRITE, x    ; the sprite: x and y at 2 n
        asl a
        tay
l2:     lda PROG_A + E_X, x
        sta VIC_SPR_X, y
l3:     lda PROG_A + E_Y, x
        sta VIC_SPR_Y, y
l4:     lda PROG_A + E_SPRITE, x    ; then at n: its pointer, colour, ninth bit
        tay
l5:     lda PROG_A + E_PTR, x
        sta POINTERS_A, y
        sta POINTERS_B, y
l6:     lda PROG_A + E_COLOUR, x
        sta VIC_SPR_COLOUR, y
l7:     lda PROG_A + E_X_HIGH, x
        beq :+
        lda VIC_SPR_X_HIGH
        ora bit_of, y
        jmp :++
:       lda VIC_SPR_X_HIGH
        and not_bit, y
:       sta VIC_SPR_X_HIGH
        txa
        clc
        adc #EVENT_SIZE
        sta ev_off
        dec ev_left
        beq mx_last
        tax                         ; the next: due by the next line? Then now.
        lda VIC_RASTER
        clc
        adc #1
l8:     cmp PROG_A + E_LINE, x
        bcs mx_one
l9:     lda PROG_A + E_LINE, x
        sta VIC_RASTER
        jmp irq_out
mx_last:  lda #0
        sta irq_kind
        lda #VB_LINE
        sta VIC_RASTER
        jmp irq_out

        .segment "DATA"

; The loads that read the shown program: their addresses' high bytes, from mux_irq.
load_at:
        .byte l1 + 2 - mux_irq, l2 + 2 - mux_irq, l3 + 2 - mux_irq
        .byte l4 + 2 - mux_irq, l5 + 2 - mux_irq, l6 + 2 - mux_irq, l7 + 2 - mux_irq
        .byte l8 + 2 - mux_irq, l9 + 2 - mux_irq
LOADS = * - load_at
bit_of: .byte 1, 2, 4, 8, 16, 32, 64, 128
not_bit:
        .byte $FE, $FD, $FB, $F7, $EF, $DF, $BF, $7F

        .segment "BSS"

irq_kind:   .res 1              ; the next interrupt: 0 the frame's (line 250), 1 an event's
ev_left:    .res 1              ; events still to come this frame
ev_off:     .res 1              ; the next one's place in the program
first_line: .res 1              ; the first one's line
