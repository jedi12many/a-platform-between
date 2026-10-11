; The frames' text (docs/frames.md): the story log, word-wrapped at 25 columns and
; scrolling up a row at a time, and text put anywhere on the text screen (the party, the
; dice log, the command row). Text is ASCII, turned into our font's screen codes here
; (tools/c64font.py's layout).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export frames_clear, log_print, log_chars, log_newline, text_at, ascii_screen
        .export row_lo, row_hi, log_ink
        .import log_more

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; frames_clear: the text screen blank, the frames' dividing line, the log empty.
;   Before:  $01 = $35.
;   After:   the log's column 0, its ink light green.
;   Changes: A, X.
frames_clear:
        lda #$20
        ldx #0
@clear: sta TEXT_SCREEN, x
        sta TEXT_SCREEN + $100, x
        sta TEXT_SCREEN + $200, x
        sta TEXT_SCREEN + $2E8, x   ; (to the end of the 1000)
        inx
        bne @clear
        lda #LIGHT_GREEN            ; rows 16-24: 360 colours, in two halves
        ldx #179
@ink:   sta COLOUR_RAM + LOG_TOP * COLS, x
        sta COLOUR_RAM + LOG_TOP * COLS + 180, x
        dex
        cpx #$FF
        bne @ink
        ldx #LOG_LAST - LOG_TOP     ; the dividing line, rows 16-23
@line:  lda row_lo + LOG_TOP, x
        sta zp_row
        lda row_hi + LOG_TOP, x
        sta zp_row + 1
        ldy #DIVIDER_COL
        lda #GLYPH_LINE
        sta (zp_row), y
        lda zp_row + 1
        clc
        adc #>TEXT_TO_COLOUR
        sta zp_row + 1
        lda #DARK_GREY
        sta (zp_row), y
        dex
        bpl @line
        lda #0
        sta zp_log_col
        lda #LIGHT_GREEN
        sta log_ink
        rts

; ----------------------------------------------------------------------------------------
; log_print: ASCII into the story log, a word at a time: a word that doesn't fit on the
; row goes to the next (one longer than a row is cut); a space between words only where
; it fits; 10 ends the row. The log scrolls as it fills.
;   Takes:   A/X = the text (low/high), ending in 0.
;   Before:  $01 = $35; the text readable there (the staging RAM is).
;   After:   the cursor after the text (zp_log_col).
;   Changes: A, X, Y; zp_text_ptr, zp_word_len, zp_row, zp_row_next.
log_print:
        sta zp_text_ptr
        stx zp_text_ptr + 1
@next:  ldy #0
        lda (zp_text_ptr), y
        bne @something
        rts
@something:
        cmp #$20
        beq @skip                   ; spaces: the next word puts one, if it fits
        cmp #$0A
        bne @word
        jsr log_newline
@skip:  inc zp_text_ptr
        bne @next
        inc zp_text_ptr + 1
        bne @next                   ; (always)
@word:  ldy #0                      ; how long it is
@len:   lda (zp_text_ptr), y
        beq @measured
        cmp #$20
        beq @measured
        cmp #$0A
        beq @measured
        iny
        cpy #LOG_COLS
        bne @len
@measured:
        sty zp_word_len
        lda zp_log_col
        beq @put                    ; at the start of the row: it fits
        sec                         ; col + 1 + length <= LOG_COLS?
        adc zp_word_len
        cmp #LOG_COLS + 1
        bcc @space
        jsr log_newline
        jmp @put
@space: lda #$20
        jsr log_putc
@put:   ldy #0
@copy:  lda (zp_text_ptr), y
        jsr log_putc
        iny
        cpy zp_word_len
        bne @copy
        tya                         ; past the word
        clc
        adc zp_text_ptr
        sta zp_text_ptr
        bcc @next
        inc zp_text_ptr + 1
        jmp @next

; ----------------------------------------------------------------------------------------
; log_chars: ASCII into the story log a character at a time, as it was typed: a row that
; fills goes on to the next, mid-word if it must (as the C64 version echoes a line); 10
; ends the row.
;   Takes:   A/X = the text (low/high), ending in 0.
;   Before:  $01 = $35.
;   Changes: A, X, Y; zp_text_ptr, zp_row, zp_row_next; zp_t0-zp_t2.
log_chars:
        sta zp_text_ptr
        stx zp_text_ptr + 1
@next:  ldy #0
        lda (zp_text_ptr), y
        beq @done
        cmp #$0A
        beq @row
        ldx zp_log_col              ; the row full: on to the next
        cpx #LOG_COLS
        bcc @put
        pha
        jsr log_newline
        pla
@put:   jsr log_putc
        jmp @skip
@row:   jsr log_newline
@skip:  inc zp_text_ptr
        bne @next
        inc zp_text_ptr + 1
        bne @next                   ; (always)
@done:  rts

; log_putc: A (ASCII) at the log's cursor. Keeps Y; changes A, X.
log_putc:
        jsr ascii_screen
        ldx zp_log_col
        sta TEXT_SCREEN + LOG_LAST * COLS, x
        lda log_ink
        sta COLOUR_RAM + LOG_LAST * COLS, x
        inc zp_log_col
        rts

; ----------------------------------------------------------------------------------------
; log_newline: the story log up a row (columns 0-24, the characters and their colours),
; its bottom row blank, the cursor at its start; first "-- more --", if the row going off
; the top hasn't been read (command.s). tests/cart/run_cart.py reads the bottom row as
; this starts, so don't rename it.
;   Before:  $01 = $35.
;   Changes: A, X, Y; zp_row, zp_row_next; zp_t0-zp_t2.
log_newline:
        jsr log_more
        ldx #LOG_TOP
@row:   lda row_lo, x
        sta zp_row
        lda row_hi, x
        sta zp_row + 1
        lda row_lo + 1, x
        sta zp_row_next
        lda row_hi + 1, x
        sta zp_row_next + 1
        ldy #LOG_COLS - 1
@chars: lda (zp_row_next), y
        sta (zp_row), y
        dey
        bpl @chars
        lda zp_row + 1              ; the same rows of the colour RAM
        clc
        adc #>TEXT_TO_COLOUR
        sta zp_row + 1
        lda zp_row_next + 1
        clc
        adc #>TEXT_TO_COLOUR
        sta zp_row_next + 1
        ldy #LOG_COLS - 1
@inks:  lda (zp_row_next), y
        sta (zp_row), y
        dey
        bpl @inks
        inx
        cpx #LOG_LAST
        bne @row
        lda #$20
        ldy #LOG_COLS - 1
@blank: sta TEXT_SCREEN + LOG_LAST * COLS, y
        dey
        bpl @blank
        lda #0
        sta zp_log_col
        rts

; ----------------------------------------------------------------------------------------
; text_at: ASCII put on the text screen, padded with spaces to a width (and cut there).
;   Takes:   A/X = the text (low/high), ending in 0; Y = the row; zp_t0 = the column,
;            zp_t1 = the colour, zp_t2 = the width (1 or more).
;   Before:  $01 = $35 (or $37: the text may be in the cartridge).
;   Changes: A, Y; zp_text_ptr, zp_row, zp_row_next.
text_at:
        sta zp_text_ptr
        stx zp_text_ptr + 1
        lda row_lo, y
        clc
        adc zp_t0
        sta zp_row
        sta zp_row_next
        lda row_hi, y
        adc #0
        sta zp_row + 1
        clc
        adc #>TEXT_TO_COLOUR
        sta zp_row_next + 1
        ldy #0
@char:  lda (zp_text_ptr), y
        beq @pad
        jsr ascii_screen
        sta (zp_row), y
        lda zp_t1
        sta (zp_row_next), y
        iny
        cpy zp_t2
        bne @char
        rts
@pad:   lda #$20
        sta (zp_row), y
        lda zp_t1
        sta (zp_row_next), y
        iny
        cpy zp_t2
        bne @pad
        rts

; ----------------------------------------------------------------------------------------
; ascii_screen: an ASCII character's screen code in our font: @ 0, a-z 1-26, [\]^_ 27-31,
; space to ? as they are, ` 64, A-Z 65-90, {|}~ 91-94; the frames' line and bar cells
; ($10-$13) $60-$63; anything else a space.
;   Takes:   A = ASCII.
;   After:   A = the screen code.
;   Changes: A only.
ascii_screen:
        cmp #$60
        bcc @below60
        cmp #$7B
        bcs @braces
        cmp #$61
        bcc @backtick
        sbc #$60                    ; a-z (C set)
        rts
@backtick:
        lda #$40
        rts
@braces:
        cmp #$7F
        bcs @blank
        sec                         ; (the compare left C clear)
        sbc #$20                    ; {|}~
        rts
@below60:
        cmp #$40
        bcc @low
        beq @at
        cmp #$5B
        bcc @done                   ; A-Z as they are
        sbc #$40                    ; [\]^_ (C set)
        rts
@at:    lda #0
        rts
@low:   cmp #$20
        bcs @done                   ; space to ? as they are
        cmp #ASCII_LINE
        bcc @blank
        cmp #ASCII_BAR_FULL + 1
        bcs @blank
        adc #GLYPH_LINE - ASCII_LINE    ; the frames' own (C clear)
        rts
@blank: lda #$20
@done:  rts

; The rows of the text screen.
row_lo:
        .repeat 25, r
        .byte <(TEXT_SCREEN + r * COLS)
        .endrepeat
row_hi:
        .repeat 25, r
        .byte >(TEXT_SCREEN + r * COLS)
        .endrepeat

        .segment "BSS"
log_ink:        .res 1              ; the story log's colour
