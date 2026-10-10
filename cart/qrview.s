; The QR code in the view (qr.s's modules): a hires bitmap, black modules on a white
; square with a quiet zone of 4 modules round them, the rest of the view black. A module
; is 4 x 4 pixels while the code is small enough (version 1), else 3 x 3; centred.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export qr_show
        .import qr_size, qr_row_lo, qr_row_hi, view_mode_hires, row_lo, row_hi

VIEW_LINES      = VIEW_ROWS * 8     ; 128
VIEW_WIDTH      = COLS * 8          ; 320
BITMAP_BYTES    = VIEW_ROWS * COLS * 8
QUIET           = 4                 ; modules of white round the code
ON_WHITE        = $01               ; a hires cell: set bits black, clear bits white

        .segment "ENDING"

; ----------------------------------------------------------------------------------------
; qr_show: the QR code made (qr_make) in the view, from the next frame: the view black,
; then the modules drawn, then the white square under them.
;   Before:  $01 = $35.
;   Changes: A, X, Y; zp_qr; zp_t0-zp_t3.
qr_show:
        lda #0                      ; the view black, in hires
        ldx #0
@black: sta VIEW_SCREEN, x
        sta VIEW_SCREEN + $100, x
        sta VIEW_SCREEN + VIEW_ROWS * COLS - $100, x
        inx
        bne @black
        lda #MEM_PICTURE
        ldx #CTRL1_BITMAP
        ldy #BLACK
        jsr view_mode_hires
        lda #<PICTURE               ; the bitmap clear
        sta zp_qr
        lda #>PICTURE
        sta zp_qr + 1
        ldx #>BITMAP_BYTES
        lda #0
        tay
@clear: sta (zp_qr), y
        iny
        bne @clear
        inc zp_qr + 1
        dex
        bne @clear
        ; A module's pixels, the code's width, and its top left.
        lda #4
        ldx qr_size
        cpx #25
        bcc @big
        lda #3
@big:   sta px
        lda #0                      ; width: size x px, added up
        sta width
        ldx qr_size
@w:     clc
        adc px
        dex
        bne @w
        sta width
        lda #<VIEW_WIDTH            ; left: (320 - width) / 2
        sec
        sbc width
        sta left
        lda #>VIEW_WIDTH
        sbc #0
        lsr a
        ror left
        sta left + 1
        lda #VIEW_LINES             ; top: (128 - width) / 2
        sec
        sbc width
        lsr a
        sta top
        ; The dark modules, a pixel row at a time.
        lda top
        sta pix_y
        lda #0
        sta my
@mrow:  lda #0
        sta py
@prow:  lda left
        sta pix_x
        lda left + 1
        sta pix_x + 1
        lda #0
        sta mx
@mcol:  ldx mx                      ; dark? (qr.s: row my, column mx)
        ldy my
        jsr module
        beq @light
        lda px
        sta zp_t3
@pixel: jsr plot
        inc pix_x
        bne @same
        inc pix_x + 1
@same:  dec zp_t3
        bne @pixel
        jmp @after
@light: lda pix_x                   ; past it
        clc
        adc px
        sta pix_x
        bcc @after
        inc pix_x + 1
@after: inc mx
        lda mx
        cmp qr_size
        bne @mcol
        inc pix_y
        inc py
        lda py
        cmp px
        bne @prow
        inc my
        lda my
        cmp qr_size
        bne @mrow
        ; The white square: the cells under the code and its quiet zone.
        lda px                      ; the zone: 4 modules
        asl a
        asl a
        sta zone
        lda top                     ; rows: (top - zone) / 8 to (top + width + zone + 7) / 8
        sec
        sbc zone
        bcs @row0
        lda #0
@row0:  lsr a
        lsr a
        lsr a
        sta row0
        lda top
        clc
        adc width
        adc zone
        adc #7
        lsr a
        lsr a
        lsr a
        cmp #VIEW_ROWS
        bcc @row1
        lda #VIEW_ROWS
@row1:  sta row1
        lda left                    ; columns, likewise (all 16 bits: under 320)
        sec
        sbc zone
        sta zp_t0
        lda left + 1
        sbc #0
        jsr cell
        sta col0
        lda left
        clc
        adc width
        sta zp_t0
        lda left + 1
        adc #0
        sta zp_t1
        lda zp_t0
        clc
        adc zone
        sta zp_t0
        lda zp_t1
        adc #0
        sta zp_t1
        lda zp_t0
        clc
        adc #7
        sta zp_t0
        lda zp_t1
        adc #0
        jsr cell
        sta col1
        ldx row0
@srow:  lda row_lo, x               ; the view's row X: the text screen's, moved up
        sta zp_qr
        lda row_hi, x
        clc
        adc #>(VIEW_SCREEN - TEXT_SCREEN)
        sta zp_qr + 1
        ldy col0
        lda #ON_WHITE
@scol:  sta (zp_qr), y
        iny
        cpy col1
        bne @scol
        inx
        cpx row1
        bne @srow
        rts

; cell: A/zp_t0 (high/low) / 8. After: A. Changes A; zp_t1.
cell:   sta zp_t1
        lda zp_t0
        lsr zp_t1
        ror a
        lsr zp_t1
        ror a
        lsr zp_t1
        ror a
        rts

; module: Z clear if module (X, Y) (column, row) of the code is dark. Changes A; zp_qr.
module: txa
        clc
        adc qr_row_lo, y
        sta zp_qr
        lda qr_row_hi, y
        adc #0
        sta zp_qr + 1
        sty keep_y
        ldy #0
        lda (zp_qr), y
        ldy keep_y
        and #1
        rts

; plot: the pixel at (pix_x, pix_y) set: in the bitmap's cell row pix_y / 8, at byte
; (pix_x & $1F8) + pix_y & 7, bit 7 - pix_x & 7. Changes A, X, Y; zp_qr.
plot:   lda pix_y
        lsr a
        lsr a
        lsr a
        tax
        lda pix_x
        and #$F8
        clc
        adc bitmap_lo, x
        sta zp_qr
        lda pix_x + 1
        adc bitmap_hi, x
        sta zp_qr + 1
        lda pix_y
        and #7
        tay
        lda pix_x
        and #7
        tax
        lda (zp_qr), y
        ora pixel_bit, x
        sta (zp_qr), y
        rts

; Each cell row's start in the bitmap (320 bytes a row), and each pixel's bit.
bitmap_lo:      .repeat VIEW_ROWS, r
                .byte <(PICTURE + r * COLS * 8)
                .endrepeat
bitmap_hi:      .repeat VIEW_ROWS, r
                .byte >(PICTURE + r * COLS * 8)
                .endrepeat
pixel_bit:      .byte $80, $40, $20, $10, $08, $04, $02, $01

        .segment "BSS"
px:             .res 1              ; a module's pixels a side
width:          .res 1
left:           .res 2
top:            .res 1
zone:           .res 1
pix_x:          .res 2
pix_y:          .res 1
mx:             .res 1
my:             .res 1
py:             .res 1
row0:           .res 1
row1:           .res 1
col0:           .res 1
col1:           .res 1
keep_y:         .res 1
