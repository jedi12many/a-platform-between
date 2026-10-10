; The party frame (docs/frames.md): rows 16-19, columns 26-39. For now one traveler, in
; row 16: their name, and their health as a bar of five in halves (as the C64 version's
; hal_frame_member draws it), red at a third or less.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export party_show
        .import text_at, name_text, health_max

BAR_CELLS       = 5

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; party_show: the traveler (passport.s's `traveler`) in the party frame.
;   Takes:   A = their health now.
;   Before:  $01 = $35.
;   Changes: A, X, Y; zp_t0-zp_t2; text.s's zero page.
party_show:
        sta health
        jsr health_max
        sta most
        lda #SIDE_COL + 1           ; the name, white
        sta zp_t0
        lda #WHITE
        sta zp_t1
        lda #APB_NAME
        sta zp_t2
        jsr name_text
        ldy #PARTY_TOP
        jsr text_at
        ; halves = health x 10 / most (1 at least if there's any health left)
        lda health
        sta tenfold
        lda #0
        sta tenfold + 1
        asl tenfold                 ; x 2
        rol tenfold + 1
        lda tenfold                 ; x 5: (x 2) x 4 + (x 2)
        sta twice
        lda tenfold + 1
        sta twice + 1
        asl tenfold
        rol tenfold + 1
        asl tenfold
        rol tenfold + 1
        lda tenfold
        clc
        adc twice
        sta tenfold
        lda tenfold + 1
        adc twice + 1
        sta tenfold + 1
        ldx #0                      ; / most, by taking it away
        lda most
        beq @counted
@divide:
        lda tenfold
        sec
        sbc most
        tay
        lda tenfold + 1
        sbc #0
        bcc @counted
        sta tenfold + 1
        sty tenfold
        inx
        bne @divide                 ; (10 at most)
@counted:
        txa
        bne @some
        lda health
        beq @some
        ldx #1
@some:  ldy #0                      ; the bar: full, half and empty cells
@cell:  lda #ASCII_BAR_FULL
        cpx #2
        bcs @put
        lda #ASCII_BAR_HALF
        cpx #1
        beq @put
        lda #ASCII_BAR_EMPTY
@put:   sta bar, y
        dex
        dex
        bpl @next
        ldx #0
@next:  iny
        cpy #BAR_CELLS
        bne @cell
        lda #0
        sta bar, y
        lda health                  ; its colour: red at a third or less
        asl a
        sta twice
        lda #0
        rol a
        sta twice + 1
        lda twice
        clc
        adc health
        sta twice
        lda twice + 1
        adc #0
        sta twice + 1
        lda most
        cmp twice
        lda #0
        sbc twice + 1
        lda #GREEN
        bcc @colour
        lda #RED
@colour:
        sta zp_t1
        lda #COLS - BAR_CELLS
        sta zp_t0
        lda #BAR_CELLS
        sta zp_t2
        lda #<bar
        ldx #>bar
        ldy #PARTY_TOP
        jmp text_at

        .segment "BSS"
health:         .res 1
most:           .res 1
tenfold:        .res 2
twice:          .res 2
bar:            .res BAR_CELLS + 1
