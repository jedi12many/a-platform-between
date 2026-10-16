; The border opened (docs/walk.md, "The border"): the view's 24 rows (lines 55-246) as
; they were, black above and below them, and the HUD in the bottom border, lines 268-288.
;
; The VIC shuts the border when the raster meets the bottom compare (line 247 at 24 rows,
; 251 at 25), and opens it at the top compare (51 at 25 rows, 55 at 24) if the screen's on:
; it's at 25 rows (RSEL) at 247 and at 24 at 251, so it never shuts; and at 25 at 51, so
; it opens (if it was shut, as at the start). Then outside the view the screen is blacked out by an invalid mode (ECM with
; multicolour: every pixel black), switched on between line 246's last pixel and line 247's
; first, off between 54's and 55's; and the sprites still showing there (figures crossing
; the view's edges) are given an empty shape, their pointers written between the VIC's
; fetches of them. A frame's interrupts, in order:
;
;   bottom (244) the band below the view; the frame begun (irq.s: what the loop decided
;                shown); the HUD's sprites set but their pointers; the colours (a step's)
;   hud    (264) the HUD's pointers, in line 266: it shows on 268-288; the band at 25 rows
;   world  (1)   the world's first eight sprites (mux.s), their pointers empty
;   top    (52)  the band above the view: the pointers, then the view on at 55
;   events       the sprites reused down the screen (mux.s), then bottom again
;
; The writes that must fall between two lines' pixels: a raster's line is 63 cycles, its
; pixels shown from cycle 17 to 55 (the 38 columns), the sprites' pointers and data fetched
; from cycle 58 to the next line's 10 (sprite n at 58 + 2n, or 1 + 2 (n - 3) for 3-7). A
; write that's due is waited for by polling the raster: `cmp VIC_RASTER / bne` reads it every
; 7 cycles, so it's seen at cycle r = 0-6 of the line it changes (11-17 if the sprites 3-7
; are fetched at its start: the CPU stops while they are). The VIC also stops the CPU on a
; bad line from cycle 12 to 54, and three cycles before a sprite's fetch; a write in an
; instruction stopped there comes out when it starts again (by cycle 14 of the next line, at
; the latest). The fine scroll decides which lines are bad: line 48 + ys + 8 k.

        .include "hw.inc"
        .include "walk.inc"

        .export bottom, hud_irq, world_irq, top_irq, top_spare, screen_b, view_d011
        .export top_near0, top_far_0
        .import wk_frame, wk_busy, wk_pending, wk_late, wk_d016, wk_d011, wk_d018, wk_swap
        .import prog_next, prog_shown, irq_kind, irq_out, world_frame, floor
        .import first_event, blast_rest

        .segment "HIGH"

; The 8 pointers of a screen's table, with A.
.macro POINTERS table
        .repeat 8, n
        sta table + n
        .endrepeat
.endmacro


; The top's pointer writes: eight slots of `lda #pointer / sta table + n`, those not
; wanted writing to top_spare; world_frame fills them, the crossing figures' first. Slot k
; is at NAMEk (the pointer at + 1, the address at + 3).
.macro SLOTS name
        .repeat 8, k
        .ident(.sprintf("%s%d", .string(name), k)):
        lda #BLANK_SHAPE
        sta top_spare
        .endrepeat
.endmacro

.macro HUD_POINTERS table
        .repeat 4, k
        lda #SHAPE_POINTER + 2 * k
        sta table + 2 * k
        lda #HUD_SHAPES + k
        sta table + 2 * k + 1
        .endrepeat
.endmacro

; The bottom's three ways (ys 0-5, 6, 7), each with the shown screen's pointers.
.macro BOTTOM5 table
        lda #LAST_VIEW
:       cmp VIC_RASTER              ; seen at 246's cycle r (0-6; 11-17)
        bne :-
        lda #BLANK_SHAPE            ; r + 4
        POINTERS table              ; n's written at r + 8 + 4 n: 7's by 53, before any
        .repeat 8                   ; sprite's fetch for 247 stops the CPU (from 55)
        nop
        .endrepeat
        bit $00                     ; r + 55
        stx VIC_CTRL1               ; written at r + 59: cycle 59-65 (to 247's 2), or 70-76
        jmp bottom_below                  ; (247's 7-13); stopped for the sprites, by 247's 14
.endmacro

.macro BOTTOM6 table
        lda #LAST_VIEW - 1
:       cmp VIC_RASTER              ; 245's cycle r
        bne :-
        lda #BLANK_SHAPE
        POINTERS table
        lda #LAST_VIEW
:       cmp VIC_RASTER              ; 246's cycle r
        bne :-
        nop                         ; r + 4
        nop                         ; r + 6
        nop                         ; r + 8: the write's first cycle at r + 9 (9-15): the
        stx VIC_CTRL1               ; VIC stops it from 12 to 54; written at 56-58 (or by
        jmp bottom_below                  ; 247's 14, stopped again for the sprites)
.endmacro

.macro BOTTOM7 table
        lda #LAST_VIEW
:       cmp VIC_RASTER
        bne :-
        lda #BLANK_SHAPE
        POINTERS table
        stx VIC_CTRL1               ; (in 246, by its cycle 57)
        jmp bottom_below
.endmacro

; ----------------------------------------------------------------------------------------
; bottom: the band under the view, the frame begun, the HUD set up. Its interrupt comes at
; BOTTOM_LINE (243 when ys is 6), or mux.s comes here if the last event ran past it.
;   Before:  A, X and Y pushed; the interrupt acknowledged; interrupts off.
bottom:
        lda view_d011
        and #7
        cmp #6
        bne :+
        jmp @six
:       cmp #7
        bne :+
        jmp @seven
:       lda view_d011               ; ys 0-5: line 246's pointers, 247 black
        ora #CTRL1_BAND
        tax
        bit screen_b                ; (the screen's chosen before: no time for it after)
        bmi @b5
        BOTTOM5 POINTERS_A
@b5:    BOTTOM5 POINTERS_B
@six:   lda view_d011               ; ys 6: line 246 is bad (row 24's first): the pointers
        ora #CTRL1_BAND             ; in 245 (the figures crossing lose 246), the band's
        tax                         ; write let stop through 246's bad line
        bit screen_b
        bmi @b6
        BOTTOM6 POINTERS_A
@b6:    BOTTOM6 POINTERS_B
@seven: lda view_d011               ; ys 7: 247 would be bad (row 24's first): the fine
        and #$F8                    ; scroll made 5 in 246, so it isn't: the VIC idles from
        ora #5                      ; 247, and the idle byte ($FFFF, the interrupt's
        tax                         ; vector's high byte, $FF) is black
        bit screen_b
        bmi @b7
        BOTTOM7 POINTERS_A
@b7:    BOTTOM7 POINTERS_B
bottom_below:
        ; The frame begun: counted; and if the loop is done with the last one, what it
        ; decided shown: the fine scroll, the screen, the sprites' program.
        inc wk_frame
        bne :+
        inc wk_frame + 1
:       lda wk_busy
        beq @free
        inc wk_late
        jmp @hud
@free:  lda wk_pending
        beq @hud
        lda wk_d016
        sta VIC_CTRL2
        lda wk_d011
        sta view_d011
        lda #MEM_A                  ; (not $D018 read back: its bit 0 reads as 1)
        bit screen_b
        bpl :+
        lda #MEM_B
:       cmp wk_d018
        beq @same
        lda wk_d018
        sta mem_next
        lda #BLANK_SHAPE            ; the other screen's pointers empty first (the figures
        bit screen_b                ; crossing show to 266)
        bmi @to_a
        POINTERS POINTERS_B
        lda #$80
        bne @swap
@to_a:  POINTERS POINTERS_A
        lda #0
@swap:  sta screen_b
        lda mem_next
        sta VIC_MEM
@same:  lda prog_next
        sta prog_shown
        lda #0
        sta wk_pending
@hud:   ; By line 251 (its compare), 24 rows; the band; the next interrupt the HUD's.
        lda #LAST_VIEW + 2
:       cmp VIC_RASTER              ; (248 or later)
        bcs :-
        lda view_d011
        and #7
        ora #CTRL1_SHUT | RST8
        sta VIC_CTRL1
        lda #<HUD_LINE
        sta VIC_RASTER
        lda #KIND_HUD
        sta irq_kind
        ; The HUD's sprites: where they go, their colours, multicolour (the portraits) or
        ; not, all on, at HUD_Y (every sprite's last figure began by 245, so it isn't
        ; started again). Their pointers come at 266.
        lda #HUD_Y
        .repeat 8, n
        sta VIC_SPR_Y + 2 * n
        .endrepeat
        .repeat 8, n
        lda floor + FL_HUD + HUD_X + n
        sta VIC_SPR_X + 2 * n
        lda floor + FL_HUD + HUD_COLOUR + n
        sta VIC_SPR_COLOUR + n
        .endrepeat
        lda floor + FL_HUD + HUD_HIGHS
        sta VIC_SPR_X_HIGH
        lda floor + FL_HUD + HUD_MULTI
        sta VIC_SPR_MULTI
        lda #$FF
        sta VIC_SPR_ENA
        ; A step's swap: the colours, top first, ahead of the raster, the other
        ; interrupts let in.
        lda wk_swap
        beq @out
        lda #0
        sta wk_swap
        cli
        jsr blast_rest              ; (from the first row the frame loop hasn't: colours.s)
@out:   jmp irq_out

; ----------------------------------------------------------------------------------------
; hud_irq: the HUD's pointers, in line 266: after the VIC's last fetch of the figures'
; (for 266, by its cycle 10; the last figure's sprite starts by 245), before its first of
; the HUD's (for 268, at 267's end). Sprite 2 k is traveler k's portrait (kind k's shape,
; facing right), 2 k + 1 their health.
hud_irq:
        lda #<(HUD_LINE + 2)
:       cmp VIC_RASTER              ; 266's cycle r (0-6, or 11-17)
        bne :-
        bit screen_b
        bmi @b
        HUD_POINTERS POINTERS_A     ; sprite n's at r + 11 + 6 n: by 266's cycle 70
        jmp @next
@b:     HUD_POINTERS POINTERS_B
@next:  lda view_d011                ; the band at 25 rows again (line 251's compare is past):
        and #7                      ; the border's top compare is line 51's then (55's at
        ora #CTRL1_BAND             ; 24), and it must open there; and the next interrupt the
        sta VIC_CTRL1               ; world's, at line 1 (its ninth bit off)
        lda #WORLD_LINE
        sta VIC_RASTER
        lda #KIND_WORLD
        sta irq_kind
        jmp irq_out


; ----------------------------------------------------------------------------------------
; world_irq: at line 1, the world's first eight sprites (mux.s): after line 311, so that no
; Y meets a line's low byte till its own, and their Ys written by 11 (the HUD's); and the
; next interrupt the top's.
world_irq:
        jsr world_frame
        lda #TOP_LINE
        sta VIC_RASTER
        lda #KIND_TOP
        sta irq_kind
        jmp irq_out

; ----------------------------------------------------------------------------------------
; top_irq: the band above the view: the pointers of the figures crossing its top (empty
; till now: world_frame put their own in the top's slots), written between the VIC's
; fetches for 54 and for 55, so they show from 55; and the view on at 55. Then the sprites'
; events (mux.s). Lines 48 + ys on are row 0's, black till then.
top_irq:
        lda view_d011
        and #7
        cmp #6
        bne :+
        jmp top_six
:       ldx view_d011               ; ys 0-5 and 7 (7: row 0 starts at 55, a bad line,
        lda #FIRST_VIEW - 1         ; which stops the CPU from its cycle 12: the write's by
:       cmp VIC_RASTER              ; then)
        bne :-                      ; (54's cycle r)
        SLOTS top_near              ; slot k written at r + 8 + 6 k: the 6th (k 5) by 54's
        nop                         ; 55 even when r is 17 (the sprites 3-7 fetched at 54's
        nop                         ; start; at 55 the CPU stops for 0-2's)
        stx VIC_CTRL1               ; written at r + 58: cycle 58-64 (55's 1), or 69-75 (55's
        jmp first_event             ; 6-12); stopped for the sprites, by 55's 16
top_six:
        ldx view_d011               ; ys 6: 54 is bad (row 0's first): the view on, let
        lda #FIRST_VIEW - 1         ; stop through it; the pointers in 55 (the figures
:       cmp VIC_RASTER              ; crossing lose it)
        bne :-
        nop
        nop
        nop
        stx VIC_CTRL1               ; first cycle at r + 9 (9-15): written at 56-58
        lda #FIRST_VIEW
:       cmp VIC_RASTER
        bne :-
        jsr top_far
        jmp first_event             ; (mux.s: the events, or bottom's line)

; The top's other slots, as a call (ys 6).
top_far:
        SLOTS top_far_
        rts

        .segment "BSS"

screen_b:   .res 1              ; $80 when screen B is shown, 0 when A
view_d011:  .res 1              ; $D011 in the view this frame: CTRL1_VIEW and the fine scroll
mem_next:   .res 1
top_spare:  .res 1              ; where an unused top slot writes
