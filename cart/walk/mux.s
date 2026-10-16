; The sprite multiplexer's interrupt side (docs/walk.md, "The figures"): the shown
; program (figures.s: PROG_A or PROG_B) carried out. At the frame's start (sprites_frame,
; from irq.s's interrupt at line 250) its first eight are set, as the VIC has them, by code
; unrolled for each program; then each event at its line: a sprite set again for the next
; figure down, once the last one it showed has ended. An event's interrupt sets every
; event due by the next line, and asks for the next one's line, or line 250 again when
; there are none: a copy of its code for each program. No zero page.

        .include "hw.inc"
        .include "zp.inc"
        .include "walk.inc"

        .export world_frame, first_event, mux_a, mux_b, irq_kind, bottom_line
        .import irq_out, bottom, prog_shown, view_d011, screen_b, top_spare
        .import top_near0, top_far_0

        .segment "HIGH"

; The first eight from program BASE: where, their colours, on or not, their x's ninth bits;
; their pointers, the shown screen's, those crossing the view's top (Y under 54: shown
; from above 55) empty, with their own put in the top's slots; and its events' count.
.macro APPLY base
        .repeat 8, n
        lda base + P_X + n
        sta VIC_SPR_X + 2 * n
        lda base + P_Y + n
        sta VIC_SPR_Y + 2 * n
        cmp #FIRST_VIEW - 1
        lda base + P_PTR + n
        bcs :+
        ldx #n
        jsr crossing
        lda #BLANK_SHAPE
:       ldy #n
        sta (zp_wk_irq), y
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
; world_frame: the shown program's first eight sprites, after the HUD (border.s's world
; interrupt); the top's slots filled: the crossing figures' pointers first, the rest
; writing to top_spare.
;   Before:  in an interrupt, interrupts off.
;   Changes: A, X, Y, zp_wk_irq.
world_frame:
        lda #$FF                    ; multicolour again (the HUD's health isn't)
        sta VIC_SPR_MULTI
        ; The slots to fill: the near ones, or the far when ys is 6.
        lda view_d011
        and #7
        cmp #6
        beq @far
        lda #<top_near0
        ldx #>top_near0
        bne @set                    ; (always)
@far:   lda #<top_far_0
        ldx #>top_far_0
@set:   sta slot
        stx slot + 1
        lda #0
        sta slots_used
        ; The shown screen's pointers.
        lda #<POINTERS_A
        ldx #>POINTERS_A
        bit screen_b
        bpl :+
        lda #<POINTERS_B
        ldx #>POINTERS_B
:       sta zp_wk_irq
        stx zp_wk_irq + 1
        lda prog_shown
        beq :+
        jmp @b
:       APPLY PROG_A
        jmp @rest
@b:     APPLY PROG_B
@rest:  ; The slots not used: written to top_spare (those used last time, the rest are;
        ; all of them when the other set was used last time: the near and the far).
        lda slot
        cmp slot_was
        beq :+
        sta slot_was
        lda #8
        sta slots_were
:       lda slots_used              ; (this frame's crossing: next time's count)
        sta slots_now
        ldy slots_used
:       cpy slots_were
        bcs @done
        jsr slot_at
        ldy #3
        lda #<top_spare
        sta (zp_wk_slot), y
        iny
        lda #>top_spare
        sta (zp_wk_slot), y
        inc slots_used
        ldy slots_used
        jmp :-
@done:  lda slots_now
        sta slots_were
        lda prog_shown
        asl a
        clc
        adc #KIND_A
        sta ev_kind
        lda #P_EVENTS
        sta ev_off
        rts

; Sprite X crosses the view's top: the next slot writes A (its own pointer) to the shown
; screen's entry for it.
;   Changes: Y, zp_wk_slot (X kept).
crossing:
        pha
        ldy slots_used
        jsr slot_at
        pla
        ldy #1                      ; the immediate
        sta (zp_wk_slot), y
        txa
        clc
        adc zp_wk_irq               ; (a table's 8 are within a page)
        ldy #3
        sta (zp_wk_slot), y
        lda zp_wk_irq + 1
        iny
        sta (zp_wk_slot), y
        inc slots_used
        rts

; zp_wk_slot: slot Y of those being filled (each 5 bytes).
slot_at:
        lda slot
        clc
        adc five, y
        sta zp_wk_slot
        lda slot + 1
        adc #0
        sta zp_wk_slot + 1
        rts

five:   .byte 0, 5, 10, 15, 20, 25, 30, 35

; ----------------------------------------------------------------------------------------
; first_event: from the top's interrupt: the first event's line asked for (and come to now
; if it's due by the next), or the bottom's when there are none.
;   Before:  A, X and Y pushed; interrupts off.
first_event:
        ldx ev_left
        beq @none
        lda ev_kind
        sta irq_kind
        lda VIC_RASTER
        clc
        adc #1
        cmp first_line
        bcc :+
        lda ev_kind                 ; due now
        cmp #KIND_A
        bne @nb
        jmp mux_a
@nb:    jmp mux_b
:       lda first_line
        sta VIC_RASTER
        jmp irq_out
@none:  jmp to_bottom

; The bottom's interrupt asked for: at BOTTOM_LINE, a line sooner when ys is 6; if the
; raster's already there, the bottom now.
to_bottom:
        lda #KIND_BOTTOM
        sta irq_kind
        jsr bottom_line
        sta VIC_RASTER
        sec
        sbc #1
        cmp VIC_RASTER
        bcs :+
        jmp bottom                  ; (missed it: now)
:       jmp irq_out

bottom_line:
        lda view_d011
        and #7
        cmp #6
        bne :+
        lda #BOTTOM_LINE - 1
        rts
:       lda #BOTTOM_LINE
        rts

; ----------------------------------------------------------------------------------------
; mux_a, mux_b: an event's interrupt, program A's or B's (irq.s comes here when irq_kind is
; KIND_A or KIND_B): every event due by the next line set, then the next one's line asked
; for (or the bottom's).
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
last:   jmp to_bottom
.endmacro

mux_a:  MUX PROG_A
mux_b:  MUX PROG_B

bit_of: .byte 1, 2, 4, 8, 16, 32, 64, 128
not_bit:
        .byte $FE, $FD, $FB, $F7, $EF, $DF, $BF, $7F

        .segment "BSS"

irq_kind:   .res 1              ; the next interrupt (KIND_*: irq.s)
ev_kind:    .res 1              ; the events': KIND_A or KIND_B
slot:       .res 2              ; world_frame: the top's slots being filled...
slots_used: .res 1              ; ...how many so far
slots_now:  .res 1
slots_were: .res 1              ; how many written to a table last frame (top_spare beyond)
slot_was:   .res 1              ; and which slots they were (their low byte)

ev_left:    .res 1              ; events still to come this frame
ev_off:     .res 1              ; the next one's place in the program
first_line: .res 1              ; the first one's line
