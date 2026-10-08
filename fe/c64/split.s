; The picture on the C64 screen (docs/c64.md).
;
; A picture lives in the RAM under the KERNAL (VIC bank 3), in multicolour bitmap mode
; (tools/c64pic.py): its bitmap at $E000, its screen (two colours a cell) at $F400, the
; third colour of each of its cells at $F608 and its background at $F7E8. A raster
; interrupt shows it on rows 1-12 and the normal text screen ($0400, the ROM's
; upper/lower case characters) above and below, twice a frame:
;
;   just before row 1:  VIC bank 3, bitmap $E000, screen $F400, multicolour bitmap
;   just before row 13: VIC bank 0, screen $0400, characters $1800, hires text, black
;
; The second one also runs the KERNAL's own interrupt (keyboard, cursor, clock) once a
; frame, in place of the CIA timer it normally runs from.

        .export _split_on, _split_off, _pic_show

ROW_PIC   = 51 + 8 * 1 - 2          ; raster lines: a little before each row starts
ROW_TEXT  = 51 + 8 * 13 - 2

PIC_BACK   = $F7E8                  ; the background
PIC_CELLS  = $F608                  ; 12 rows x 40 cells' third colours
COLOR_RAM  = $D800 + 40             ; row 1

        .segment "DATA"

phase:  .byte 0                     ; 0: next is the picture's turn; 1: the text's
back:   .byte 0

        .segment "CODE"

_split_on:
        sei
        lda #$7F
        sta $DC0D                   ; no CIA 1 timer interrupts:
        lda $DC0D                   ; the raster drives the KERNAL now
        lda #<irq
        sta $0314
        lda #>irq
        sta $0315
        lda #0
        sta phase
        lda #ROW_PIC
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

_split_off:
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
        sta $DC0D                   ; the CIA 1 timer again
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
        lda #ROW_PIC
        sta $D012
        lda #0
        sta phase
        jmp $EA31                   ; the KERNAL's interrupt: keys, cursor, clock

text_screen:
        lda #$1B                    ; text mode
        sta $D011
        lda $DD00                   ; VIC bank 0
        ora #$03
        sta $DD00
        lda #$17                    ; screen $0400, upper/lower case characters
        sta $D018
        lda $D016
        and #$EF                    ; hires
        sta $D016
        lda #0
        sta $D021                   ; black
        rts
