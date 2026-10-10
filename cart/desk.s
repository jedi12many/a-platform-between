; The boarding desk (docs/boarding.md; the C version is client/desk.c, and this says what
; it says): the player types their Boarding Pass, or their Passport, a line at a time, then
; a blank line. Lines the wrong length, or with a typo, are asked for again by number; then
; the traveler is shown, and the player boards or starts again.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"

        .export desk_run, name_text
        .import log_print, line_ask, menu_ask, number_text
        .import password_decode, traveler, pass, password_kind, pw_bad_line
        .import race_lo, race_hi, class_lo, class_hi
        .importzp RACE_COUNT, CLASS_COUNT   ; (8-bit numbers: "zero page" to ca65)

LINES   = 9                         ; a Boarding Pass is 9 lines at most
TYPED   = 36                        ; a typed line, spaces and dashes and all
SLOT    = TYPED + 1                 ; its room in `typed_lines`

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; desk_run: the desk, until the player boards.
;   Takes:   A/X = this Departure's number (low/high): a pass must be for it.
;   After:   `traveler` is who boards; A = 1 if they came with a Boarding Pass (`pass`
;            is it), 0 with only a Passport.
;   Changes: A, X, Y; zp_t0-zp_t3; the zero page of text.s, command.s, password.s,
;            number.s.
desk_run:
        sta departure
        stx departure + 1
start:  lda #<greeting
        ldx #>greeting
        jsr log_print
        lda #0
        sta count
@ask:   lda count                   ; "Line 3:", and the line
        cmp #LINES
        beq @typed
        clc
        adc #1
        ldx #<colon
        ldy #>colon
        jsr say_line
        ldx count
        jsr ask_line
        beq @typed                  ; a blank line: that's all of it
        inc count
        jmp @ask
@typed: lda count
        beq start
        cmp #3
        bcs lengths
        lda #<too_few
        ldx #>too_few
        jsr log_print
        jmp start

lengths:                            ; every line 20 symbols but the last, which is 2-20
        jsr wrong_length
        beq @join
        sta zp_t3                   ; the line, from 1
        cmp count
        beq @last
        ldx #<again_length
        ldy #>again_length
        bne @say                    ; (always)
@last:  ldx #<again_last
        ldy #>again_last
@say:   lda zp_t3
        jsr retype
        jmp lengths
@join:  jsr join
        lda #<joined
        ldx #>joined
        jsr password_decode
        cmp #PW_LINE
        bne @read
        lda pw_bad_line             ; a typo on a line typed: that line again
        beq @whole
        cmp count
        beq @typo
        bcc @typo
@whole: lda #PW_LINE                ; (one past what was typed: not a whole password)
        bne @wrong                  ; (always)
@typo:  ldx #<again_typo
        ldy #>again_typo
        jsr retype
        jmp lengths
@read:  cmp #PW_OK
        beq @good
@wrong: tax                         ; what's wrong, in words, then the desk again
        jsr say_wrong
        jmp start
@good:  lda password_kind
        cmp #KIND_PASS
        bne @show
        lda pass + PASS_DEPARTURE   ; a pass for this Departure?
        cmp departure
        bne @other
        lda pass + PASS_DEPARTURE + 1
        cmp departure + 1
        beq @show
@other: lda #<other_departure
        ldx #>other_departure
        jsr log_print
        jmp start
@show:  jsr show
        lda password_kind
        cmp #KIND_PASS
        beq @menu
        lda #<only_passport
        ldx #>only_passport
        jsr log_print
@menu:  lda #<board_menu
        ldx #>board_menu
        jsr log_print
        lda #2
        jsr menu_ask
        beq @board
        jmp start
@board: lda password_kind
        cmp #KIND_PASS
        beq @pass
        lda #0
        rts
@pass:  lda #1
        rts

; say_wrong: the message for a PW_ code. Takes: X = the code. Changes A, X, Y; text.s's
; zero page.
say_wrong:
        lda wrong_lo, x
        pha
        lda wrong_hi, x
        tax
        pla
        jmp log_print

; retype: "Line N <message>", and line N typed again. Takes: A = N (from 1); X/Y = the
; message (low/high). Changes A, X, Y; zp_t0-zp_t3; text.s's and command.s's zero page.
retype:
        sta zp_t3
        jsr say_line
        ldx zp_t3
        dex
        ; (on into ask_line)

; ask_line: typed line X (0-8), into its slot. After: Z set if it was blank. Changes A,
; X, Y; command.s's and text.s's zero page.
ask_line:
        lda slot_lo, x
        pha
        lda slot_hi, x
        tax
        pla
        ldy #TYPED
        jsr line_ask
        cmp #0
        rts

; ----------------------------------------------------------------------------------------
; say_line: "Line N" and a message after it, as a line of the story log.
;   Takes:   A = N (1-9); X/Y = the message after the number (low/high).
;   Changes: A, X, Y; zp_t0, zp_t1; text.s's zero page.
say_line:
        clc
        adc #'0'
        sta line_text + 5
        stx zp_t0
        sty zp_t1
        ldy #0                      ; "Line N", then the message
@copy:  lda (zp_t0), y
        sta line_text + 6, y
        beq @said
        iny
        bne @copy                   ; (always)
@said:  lda #<line_text
        ldx #>line_text
        jmp log_print

; symbols_on: the symbols on typed line X (what isn't a space or a dash). After: A = how
; many. Keeps X. Changes A, Y; zp_t0-zp_t2.
symbols_on:
        lda slot_lo, x
        sta zp_t0
        lda slot_hi, x
        sta zp_t1
        ldy #0
        sty zp_t2
@char:  lda (zp_t0), y
        beq @done
        cmp #' '
        beq @next
        cmp #'-'
        beq @next
        inc zp_t2
@next:  iny
        bne @char                   ; (always: a line is 36 at most)
@done:  lda zp_t2
        rts

; wrong_length: the first line the wrong length: every line but the last has 20 symbols,
; the last 2 to 20. After: A = that line, from 1, Z clear; or 0, Z set, if they're all
; right. Changes A, X, Y; zp_t0-zp_t2.
wrong_length:
        ldx #0
@line:  jsr symbols_on
        cmp #21
        bcs @wrong                  ; over 20
        cmp #2
        bcc @wrong                  ; under 2
        inx
        cpx count
        beq @fine                   ; the last line: 2-20 is right
        cmp #20
        beq @line
        dex
@wrong: inx                         ; (the line from 1)
        txa
        rts
@fine:  lda #0
        rts

; join: the typed lines, one after another with a space between, into `joined`.
; Changes A, X, Y; zp_t0-zp_t3.
join:
        lda #<joined
        sta zp_t2
        lda #>joined
        sta zp_t3
        ldx #0
@line:  lda slot_lo, x
        sta zp_t0
        lda slot_hi, x
        sta zp_t1
        ldy #0
@char:  lda (zp_t0), y
        beq @space
        jsr put_joined
        iny
        bne @char                   ; (always)
@space: lda #' '
        jsr put_joined
        inx
        cpx count
        bne @line
        lda #0
        ; (on into put_joined: the end)

; put_joined: A at zp_t2's pointer, which moves on. Keeps X, Y.
put_joined:
        sty join_y
        ldy #0
        sta (zp_t2), y
        ldy join_y
        inc zp_t2
        bne @same
        inc zp_t3
@same:  rts

; ----------------------------------------------------------------------------------------
; show: "Kestrel, Salvaged Warden, level 3. Debt 50000." into the story log.
;   Changes: A, X, Y; zp_t0-zp_t3; number.s's and text.s's zero page.
show:
        lda #<say_buf
        sta zp_t2
        lda #>say_buf
        sta zp_t3
        jsr name_text
        jsr say
        lda #<comma
        ldx #>comma
        jsr say
        ldx traveler + CH_RACE      ; the race's name (or ?)
        cpx #RACE_COUNT
        bcs @no_race
        lda race_lo, x
        pha
        lda race_hi, x
        tax
        pla
        jmp @race
@no_race:
        lda #<unknown
        ldx #>unknown
@race:  jsr say
        lda #' '
        jsr put_joined
        ldx traveler + CH_CLASS     ; the class's
        cpx #CLASS_COUNT
        bcs @no_class
        lda class_lo, x
        pha
        lda class_hi, x
        tax
        pla
        jmp @class
@no_class:
        lda #<unknown
        ldx #>unknown
@class: jsr say
        lda #<level
        ldx #>level
        jsr say
        lda traveler + CH_LEVEL
        sta zp_num
        lda #0
        sta zp_num + 1
        jsr number_text
        jsr say
        lda #<debt
        ldx #>debt
        jsr say
        lda traveler + CH_DEBT
        sta zp_num
        lda traveler + CH_DEBT + 1
        sta zp_num + 1
        jsr number_text
        jsr say
        lda #<full_stop
        ldx #>full_stop
        jsr say
        lda #0
        jsr put_joined
        lda #<say_buf
        ldx #>say_buf
        jmp log_print

; say: text (A/X, ending in 0) onto the sentence at zp_t2's pointer. Changes A, Y; zp_t0,
; zp_t1. Keeps X.
say:
        sta zp_t0
        stx zp_t1
        ldy #0
@char:  lda (zp_t0), y
        beq @done
        jsr put_joined
        iny
        bne @char                   ; (always)
@done:  rts

; ----------------------------------------------------------------------------------------
; name_text: the traveler's name as it reads: "Kestrel", "Moth-Folk Ana". Names are kept
; in capitals; each word's first letter stays one, the rest go small; the padding goes.
;   After:   A/X = the name (low/high), ending in 0 (name_buf: kept until the next).
;   Changes: A, X, Y.
name_text:
        ldy #8                      ; how long, without the padding
@trim:  lda traveler + CH_NAME - 1, y
        cmp #' '
        bne @long
        dey
        bne @trim
@long:  sty name_len
        ldx #0
        ldy #1                      ; 1: the next letter starts a word
@char:  cpx name_len
        beq @end
        lda traveler + CH_NAME, x
        cpy #0
        bne @first
        cmp #'A'
        bcc @first
        cmp #'Z' + 1
        bcs @first
        ora #%00100000              ; small
@first: sta name_buf, x
        ldy #0
        cmp #' '
        beq @word
        cmp #'-'
        bne @next
@word:  ldy #1
@next:  inx
        bne @char                   ; (always)
@end:   lda #0
        sta name_buf, x
        lda #<name_buf
        ldx #>name_buf
        rts

; ----------------------------------------------------------------------------------------
; Where each typed line goes.
slot_lo:
        .repeat LINES, i
        .byte <(typed_lines + i * SLOT)
        .endrepeat
slot_hi:
        .repeat LINES, i
        .byte >(typed_lines + i * SLOT)
        .endrepeat

; What the desk says (client/desk.c's words). The story log wraps them.
greeting:
        .byte "Your Boarding Pass, please, one line at a time, then a blank line. "
        .byte "(Or your Passport, to travel without one.)", 10, 0
too_few:
        .byte "A pass or a Passport is at least 3 lines. Let's start again.", 10, 0
other_departure:
        .byte "That Boarding Pass is for a different Departure. The Waystation will "
        .byte "issue one for this one.", 10, 0
only_passport:
        .byte "That's a Passport, not a Boarding Pass: nothing you earn on this trip "
        .byte "can be stamped.", 10, 0
board_menu:
        .byte "1. Board", 10, "2. Start over", 10, 0
colon:          .byte ":", 10, 0
again_length:   .byte " should have 20 letters. Type it again:", 10, 0
again_last:     .byte " is too long or too short. Type it again:", 10, 0
again_typo:     .byte " has a typo. Type it again:", 10, 0
comma:          .byte ", ", 0
level:          .byte ", level ", 0
debt:           .byte ". Debt ", 0
full_stop:      .byte ".", 10, 0
unknown:        .byte "?", 0
symbol_wrong:
        .byte "Something there isn't a letter a pass uses. Let's start again.", 10, 0
version_wrong:
        .byte "That's from a different version of the game.", 10, 0
checksum_wrong:
        .byte "Every line checks out, but the whole doesn't. Check them all.", 10, 0
whole_wrong:
        .byte "That isn't a whole pass or Passport. Let's start again.", 10, 0

; The message for each PW_ code (char.inc): OK (never), SYMBOL, LINE (a line not typed),
; LENGTH, CHECKSUM, VERSION, TOO_BIG (never).
wrong_lo:
        .byte <whole_wrong, <symbol_wrong, <whole_wrong, <whole_wrong, <checksum_wrong
        .byte <version_wrong, <whole_wrong
wrong_hi:
        .byte >whole_wrong, >symbol_wrong, >whole_wrong, >whole_wrong, >checksum_wrong
        .byte >version_wrong, >whole_wrong

line_text:      .byte "Line N"      ; then a message (say_line): in RAM, as all this is
                .res 48

        .segment "BSS"
departure:      .res 2
count:          .res 1              ; lines typed
typed_lines:    .res LINES * SLOT
joined:         .res LINES * SLOT + 1
say_buf:        .res 64
name_buf:       .res 9
name_len:       .res 1
join_y:         .res 1
