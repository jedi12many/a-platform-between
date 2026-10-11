; The picture on the C64 screen (docs/c64.md).
;
; A picture lives in the RAM under the KERNAL (VIC bank 3), in multicolour bitmap mode
; (tools/c64pic.py): its bitmap at $E000, its screen (two colours a cell) at $F400, the
; third colour of each of its cells at $F608 and its background at $F7E8. The text
; screen is in bank 3 too: at $F800, in our font at $D000 (tools/c64font.py, under the
; I/O, which only the VIC sees there). A raster interrupt shows the picture on rows 1-12
; and the text above and below, twice a frame:
;
;   just before row 1:  bitmap $E000, screen $F400, multicolour bitmap
;   just before row 13: screen $F800, characters $D000, hires text, black
;
; The second one also plays a frame of music (fe/c64/tune.s) and runs the KERNAL's own
; interrupt (keyboard, cursor, clock), once a frame, in place of the CIA timer it
; normally runs from. Without a picture, only the second one runs. The interrupt is on
; from the start (irq_on) to the end (irq_off), but for fights, when the battle screen
; has its own (fe/c64/sprites.s), which gives it back with irq_on.

        .export _split_on, _split_off, _pic_show, _text_screen, _font_install, _text_scroll
        .export _irq_on, irq_on, _irq_off, _split_picture, _hal_scene_log
        .export _scroll_last, _scroll_left, _scroll_right
        .import tune_tick
        .importzp ptr1, ptr2, ptr3, ptr4, tmp1

ROW_PIC   = 51 + 8 * 1 - 2          ; raster lines: a little before each row starts
ROW_TEXT  = 51 + 8 * 13 - 2

PIC_BACK   = $F7E8                  ; the background
PIC_CELLS  = $F608                  ; 12 rows x 40 cells' third colours
COLOR_RAM  = $D800 + 40             ; row 1

        .segment "DATA"

phase:  .byte 0                     ; 0: next is the picture's turn; 1: the text's
back:   .byte 0
_split_picture:                     ; (tests/c64/run_c64.py reads it)
picture: .byte 0                    ; 1 while a picture shows
_scroll_last:  .byte 24             ; text_scroll: the row under the last to scroll,
_scroll_left:  .byte 0              ; the first column,
_scroll_right: .byte 40             ; and the one after the last

        .segment "CODE"

; The raster interrupt on, with no picture: the text's turn, once a frame.
_irq_on:
irq_on:
        sei
        lda #$7F
        sta $DC0D                   ; no CIA 1 timer interrupts:
        lda $DC0D                   ; the raster drives the KERNAL now
        lda #<irq
        sta $0314
        lda #>irq
        sta $0315
        lda #0
        sta picture
        lda #1
        sta phase
        lda #ROW_TEXT
        sta $D012
        lda $D011
        and #$7F
        sta $D011
        lda #$FF
        sta $D019
        lda #$01
        sta $D01A
        cli
        rts

; And off, for good: the CIA timer runs the KERNAL again.
_irq_off:
        sei
        lda #0
        sta $D01A
        lda #$FF
        sta $D019
        lda #$31
        sta $0314
        lda #$EA
        sta $0315
        lda #$81
        sta $DC0D
        jsr text_screen
        cli
        rts

; A picture on rows 1-12, from the next frame.
_split_on:
        sei
        lda #1
        sta picture
        lda #0
        sta phase
        lda #ROW_PIC
        sta $D012
        cli
        rts

; Text all the way down.
_split_off:
        sei
        lda #0
        sta picture
        lda #1
        sta phase
        lda #ROW_TEXT
        sta $D012
        jsr text_screen
        cli
        rts

; Copy the picture's colours out from under the KERNAL: switch the ROM out (and keep
; interrupts off while it's out, as their vectors live there), copy, switch it back.
_pic_show:
        sei
        lda $01
        pha
        and #$F8
        ora #$05                    ; $35: RAM everywhere but I/O (so the KERNAL's out)
        sta $01
        ldx #0
@cells: lda PIC_CELLS, x
        sta COLOR_RAM, x
        lda PIC_CELLS + 240, x
        sta COLOR_RAM + 240, x
        inx
        cpx #240
        bne @cells
        lda PIC_BACK
        sta back
        pla
        sta $01
        cli
        rts

irq:
        lda #$FF
        sta $D019                   ; this one's dealt with
        lda phase
        bne @text
        lda $DD00                   ; the picture: VIC bank 3 (keep the serial bits)
        and #$FC
        sta $DD00
        lda #$3B                    ; bitmap mode (25 rows, the screen on)
        sta $D011
        lda #$D8                    ; screen $F400, bitmap $E000
        sta $D018
        lda $D016
        ora #$10                    ; multicolour
        sta $D016
        lda back
        sta $D021
        lda #ROW_TEXT
        sta $D012
        inc phase
        jmp $EA81                   ; done: restore the registers, return
@text:
        jsr text_screen
        lda picture
        beq @alone
        lda #ROW_PIC
        sta $D012
        lda #0
        sta phase
@alone: jsr tune_tick               ; a frame of music
        jmp $EA31                   ; the KERNAL's interrupt: keys, cursor, clock

_text_screen:
text_screen:
        lda #$1B                    ; text mode
        sta $D011
        lda $DD00                   ; VIC bank 3 (keep the serial bits)
        and #$FC
        sta $DD00
        lda #$E4                    ; screen $F800, characters $D000
        sta $D018
        lda $D016
        and #$EF                    ; hires
        sta $D016
        lda #0
        sta $D021                   ; black
        rts

; Our font, loaded at $E000, to $D000: under the I/O, so with everything but RAM switched
; out for the copy (and interrupts off, as their vectors are in the ROM).
_font_install:
        sei
        lda $01
        pha
        lda #$34
        sta $01
        lda #$00
        sta ptr1
        sta ptr2
        lda #$E0
        sta ptr1 + 1
        lda #$D0
        sta ptr2 + 1
        ldx #8                      ; 8 pages: 2 KB
        ldy #0
@copy:  lda (ptr1), y
        sta (ptr2), y
        iny
        bne @copy
        inc ptr1 + 1
        inc ptr2 + 1
        dex
        bne @copy
        pla
        sta $01
        cli
        rts

; A line for the tests' record (client/apb_scene.h): shown nowhere. tests/c64/run_c64.py
; reads it here (A/X: the text), so don't rename it. Changes nothing.
_hal_scene_log:
        rts

; Scroll a frame up a row (docs/frames.md): rows A to _scroll_last - 1 each take the row
; under them, columns _scroll_left to _scroll_right - 1: the screen, from under the
; KERNAL (so with the ROM out), and its colours. A row at a time, with interrupts let in
; between, so the raster split never misses a frame. Changes A, X, Y, ptr1-ptr4, tmp1.
_text_scroll:
        sta tmp1                    ; the row being filled
@row:   lda tmp1
        cmp _scroll_last
        bcs @done
        tax
        lda rows_lo, x              ; ptr1: this row; ptr2: the one under it
        sta ptr1
        sta ptr3
        lda rows_lo + 1, x
        sta ptr2
        sta ptr4
        lda rows_hi, x
        sta ptr1 + 1
        sec
        sbc #$20                    ; colour RAM is $2000 below the screen
        sta ptr3 + 1
        lda rows_hi + 1, x
        sta ptr2 + 1
        sec
        sbc #$20
        sta ptr4 + 1
        sei
        lda $01
        pha
        lda #$35                    ; RAM under the KERNAL, the I/O for colours
        sta $01
        ldy _scroll_right
@copy:  dey
        lda (ptr2), y
        sta (ptr1), y
        lda (ptr4), y
        sta (ptr3), y
        cpy _scroll_left
        bne @copy
        pla
        sta $01
        cli
        inc tmp1
        jmp @row
@done:  rts

        .segment "RODATA"
rows_lo:
        .repeat 25, r
        .byte <($F800 + r * 40)
        .endrepeat
rows_hi:
        .repeat 25, r
        .byte >($F800 + r * 40)
        .endrepeat
