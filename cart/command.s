; The command row, row 24 (docs/frames.md): where the game waits for keys. A blinking
; cursor; "-- more --" before the story log scrolls a row off unread; menus, answered with
; a digit; lines typed, and then written into the story log, "> " and all.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export key_wait, log_more, menu_ask, line_ask, command_show, rows_shown
        .import key_get, keys_clear, text_at, log_print, ascii_screen, frames, log_ink

CURSOR_ON = $A0                     ; a reversed space: a block

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; command_show: the command row: ASCII from its start, the rest blank; the cursor after it.
;   Takes:   A/X = the text (low/high), ending in 0; Y = its colour.
;   Changes: A, X, Y; zp_text_ptr, zp_row, zp_row_next; zp_t0-zp_t2.
command_show:
        sty zp_t1
        ldy #0
        sty zp_t0
        ldy #COLS
        sty zp_t2
        ldy #INPUT_ROW
        jsr text_at
        ldy #0                      ; the cursor: after the text
@len:   lda (zp_text_ptr), y
        beq @end
        iny
        bne @len                    ; (always)
@end:   sty icol
        rts

; ----------------------------------------------------------------------------------------
; key_wait: a key, with the cursor blinking on the command row while it waits. The story
; log has been read when a key is pressed: rows_shown starts again.
;   After:   A = the key (keys.s).
;   Changes: A, X.
key_wait:
        ldx icol
        lda TEXT_SCREEN + INPUT_ROW * COLS, x
        sta under
        lda #WHITE
        sta COLOUR_RAM + INPUT_ROW * COLS, x
@wait:  lda frames                  ; on for 16 frames, off for 16
        and #$10
        beq @off
        lda #CURSOR_ON
        bne @show                   ; (always)
@off:   lda under
@show:  ldx icol
        sta TEXT_SCREEN + INPUT_ROW * COLS, x
        jsr key_get
        beq @wait
        pha
        ldx icol
        lda under
        sta TEXT_SCREEN + INPUT_ROW * COLS, x
        lda #0
        sta rows_shown
        pla
        rts

; ----------------------------------------------------------------------------------------
; log_more: before the story log scrolls (text.s, log_newline): if its top row hasn't been
; read (rows_shown rows printed over the bottom one since the last key), "-- more --" and
; a key first.
;   Changes: A, X, Y; zp_row, zp_row_next; zp_t0-zp_t2. (zp_text_ptr kept: the log's
;            string is mid-print.)
log_more:
        lda rows_shown
        cmp #LOG_ROWS - 1
        bcs @wait
        inc rows_shown
        rts
@wait:  lda zp_text_ptr
        pha
        lda zp_text_ptr + 1
        pha
        lda #<more
        ldx #>more
        ldy #YELLOW
        jsr command_show
        ldy #9                      ; in reverse
@rev:   lda TEXT_SCREEN + INPUT_ROW * COLS, y
        ora #$80
        sta TEXT_SCREEN + INPUT_ROW * COLS, y
        dey
        bpl @rev
        jsr key_wait                ; (rows_shown 0)
        lda #<nothing
        ldx #>nothing
        ldy #WHITE
        jsr command_show
        pla
        sta zp_text_ptr + 1
        pla
        sta zp_text_ptr
        rts

; ----------------------------------------------------------------------------------------
; menu_ask: a menu's answer, a digit from 1 to its count; the answer into the story log
; ("> 2").
;   Takes:   A = how many choices, 1-9 (the menu itself is printed already).
;   After:   A = the choice, 0 to count - 1.
;   Changes: A, X, Y; text.s's zero page; zp_t0-zp_t3.
menu_ask:
        clc
        adc #'1'
        sta zp_t3                   ; one past the last digit
        jsr keys_clear
        lda #<nothing
        ldx #>nothing
        ldy #WHITE
        jsr command_show
@key:   jsr key_wait
        cmp #'1'
        bcc @key
        cmp zp_t3
        bcs @key
        sta echo + 2
        lda #0
        sta echo + 3
        jsr echo_prefix
        jsr echo_line
        lda echo + 2
        sec
        sbc #'1'
        rts

; ----------------------------------------------------------------------------------------
; line_ask: a line typed on the command row ("> " and the cursor): printable ASCII, DEL
; to take one back, RETURN to end it; then into the story log, "> " and all.
;   Takes:   A/X = where it goes (low/high); Y = the most it may have (1-36).
;   After:   the line there, ending in 0; A = its length.
;   Changes: A, X, Y; zp_line; text.s's zero page; zp_t0-zp_t3.
line_ask:
        sta zp_line
        stx zp_line + 1
        sty zp_t3
        jsr keys_clear
        lda #<prompt
        ldx #>prompt
        ldy #WHITE
        jsr command_show
        ldy #0
        sty typed
@key:   jsr key_wait
        cmp #KEY_RETURN
        beq @done
        cmp #KEY_DELETE
        bne @char
        ldy typed                   ; DEL: one back
        beq @key
        dec typed
        dec icol
        ldx icol
        lda #$20
        sta TEXT_SCREEN + INPUT_ROW * COLS, x
        jmp @key
@char:  cmp #$20                    ; printable ASCII only, and room for it
        bcc @key
        cmp #$7F
        bcs @key
        ldy typed
        cpy zp_t3
        bcs @key
        sta (zp_line), y
        sta echo + 2, y
        inc typed
        jsr ascii_screen
        ldx icol
        sta TEXT_SCREEN + INPUT_ROW * COLS, x
        inc icol
        jmp @key
@done:  ldy typed
        lda #0
        sta (zp_line), y
        sta echo + 2, y
        jsr echo_prefix
        jsr echo_line
        lda typed
        rts

; echo_prefix: "> " at the start of echo. Changes A.
echo_prefix:
        lda #'>'
        sta echo
        lda #' '
        sta echo + 1
        rts

; echo_line: the command row cleared, and echo ("> ", what was given, ending in 0) into
; the story log as a row of its own. Changes A, X, Y; text.s's zero page; zp_t0-zp_t2.
echo_line:
        lda #<nothing
        ldx #>nothing
        ldy #WHITE
        jsr command_show
        lda #<echo
        ldx #>echo
        jsr log_print
        lda #<newline
        ldx #>newline
        jmp log_print

more:    .byte "-- more --", 0
prompt:  .byte "> ", 0
nothing: .byte 0
newline: .byte 10, 0

        .segment "BSS"
icol:       .res 1                  ; the cursor's column on the command row
under:      .res 1                  ; what the cursor is over
typed:      .res 1                  ; the line's length so far
rows_shown: .res 1                  ; the log's rows printed since the last key
echo:       .res 2 + 36 + 1         ; "> ", the answer, 0
