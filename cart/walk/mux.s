; The sprite multiplexer's interrupt side (docs/walk.md, "The figures"): the shown
; program (figures.s: PROG_A or PROG_B) carried out. At the frame's start (sprites_frame,
; from irq.s's interrupt at line 250) its first eight are set, as the VIC has them, by code
; unrolled for each program; then each event at its line: a sprite set again for the next
; figure down, once the last one it showed has ended. An event's interrupt sets every
; event due by the next line, and asks for the next one's line, or line 250 again when
; there are none: a copy of its code for each program. No zero page.

        .include "hw.inc"
        .include "walk.inc"

        .export sprites_frame, mux_a, mux_b, irq_kind
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
; sprites_frame: program X (0 PROG_A, 1 PROG_B) shown: its first eight set, and the first
; event's interrupt asked for (irq_kind 1 + X: its copy of the events' code).
;   Before:  in the interrupt at line 250, interrupts off.
;   Changes: A, X, Y.
sprites_frame:
        txa
        beq :+
        jmp @b
:       APPLY PROG_A
        lda #1
        jmp @kind
@b:     APPLY PROG_B
        lda #2
@kind:  ldx #P_EVENTS
        stx ev_off
        ldx ev_left
        beq @none
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
; mux_a, mux_b: an event's interrupt, program A's or B's (irq.s comes here when irq_kind is
; 1 or 2): every event due by the next line set, then the next one's line asked for (or
; line 250's).
;   Before:  A, X and Y pushed; the interrupt acknowledged.
.macro MUX base
        .local one, last
one:    ldx ev_off
        lda base + E_SPRITE, x      ; the sprite: x and y at 2 n
        asl a
        tay
        lda base + E_X, x
        sta VIC_SPR_X, y
        lda base + E_Y, x
        sta VIC_SPR_Y, y
        lda base + E_SPRITE, x      ; then at n: its pointer, colour, ninth bit
        tay
        lda base + E_PTR, x
        sta POINTERS_A, y
        sta POINTERS_B, y
        lda base + E_COLOUR, x
        sta VIC_SPR_COLOUR, y
        lda base + E_X_HIGH, x
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
        beq last
        tax                         ; the next: due by the next line? Then now.
        lda VIC_RASTER
        clc
        adc #1
        cmp base + E_LINE, x
        bcs one
        lda base + E_LINE, x
        sta VIC_RASTER
        jmp irq_out
last:   lda #0
        sta irq_kind
        lda #VB_LINE
        sta VIC_RASTER
        jmp irq_out
.endmacro

mux_a:  MUX PROG_A
mux_b:  MUX PROG_B

        .segment "DATA"

bit_of: .byte 1, 2, 4, 8, 16, 32, 64, 128
not_bit:
        .byte $FE, $FD, $FB, $F7, $EF, $DF, $BF, $7F

        .segment "BSS"

irq_kind:   .res 1              ; the next interrupt: 0 the frame's (line 250), 1 an event's
                                ; in program A, 2 in B
ev_left:    .res 1              ; events still to come this frame
ev_off:     .res 1              ; the next one's place in the program
first_line: .res 1              ; the first one's line
