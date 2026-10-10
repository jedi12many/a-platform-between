; Passwords (docs/passport-spec.md, "The password"): the text a player types, and the bits
; it carries. One alphabet of 32 (0-9, then A-Z without I, L, O, U), five bits a symbol;
; lines of 19 data symbols and a check symbol, the last line shorter (2 symbols at
; least); a CRC-16/CCITT-FALSE over the bytes. passport.s reads and writes the fields.
;
; The bits live in pw_buffer (256 bytes: 2048 bits), most significant bit first, with a
; position (pw_pos) for reading or writing and a length (pw_len), both counted in bits.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"

        .export pw_read, pw_write, bits_clear, bits_rewind, bits_get, bits_put, bits_crc
        .export pw_buffer, pw_pos, pw_len, pw_bad_line, crc
        .export symbols

MAX_SYMBOLS = 163                   ; the longest Boarding Pass (every list full); more is
                                    ; the wrong length
PASSPORT_LONGEST = 149              ; and the longest Passport (docs/passport-spec.md)
LINE        = 20                    ; symbols a line: 19 data, 1 check

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; pw_read: a typed password's bits, its line checks checked. Forgiving, as the spec says:
; small letters are capitals, spaces, dashes and line breaks are skipped, O reads as 0, and
; I and L as 1. Symbols are counted in lines of 20 however they were typed.
;   Takes:   A/X = the text (low/high), ASCII, ending in 0 (any length).
;   After:   A = PW_OK, the bits in pw_buffer (pw_len of them, pw_pos 0), Z set; or
;            PW_SYMBOL, PW_LENGTH, or PW_LINE (pw_bad_line: the line, from 1), Z clear.
;   Changes: A, X, Y; zp_pw_text, zp_pw_value, zp_pw_n, zp_pw_sum; zp_t0-zp_t3.
pw_read:
        sta zp_pw_text
        stx zp_pw_text + 1
        lda #0
        sta count
        sta pw_bad_line
@char:  ldy #0
        lda (zp_pw_text), y
        bne @more
        jmp @lines
@more:  inc zp_pw_text
        bne @inc
        inc zp_pw_text + 1
@inc:   cmp #' '
        beq @char
        cmp #'-'
        beq @char
        cmp #10
        beq @char
        cmp #13
        beq @char
        cmp #9
        beq @char
        cmp #'a'                    ; small letters as capitals
        bcc @caps
        cmp #'z' + 1
        bcs @caps
        and #%11011111
@caps:  cmp #'O'
        bne @not_o
        lda #'0'
@not_o: cmp #'I'
        beq @one
        cmp #'L'
        bne @look
@one:   lda #'1'
@look:  ldx #31
@find:  cmp symbols, x
        beq @found
        dex
        bpl @find
        lda #PW_SYMBOL
        rts
@found: txa
        ldx count
        cpx #MAX_SYMBOLS
        bcs @long
        cpx #PASSPORT_LONGEST       ; past a Passport's longest: only a pass, whose first
        bcc @keep                   ; symbol's top 4 bits say so
        pha
        lda values
        lsr a
        cmp #KIND_PASS
        bne @too_long
        pla
        jmp @keep
@too_long:
        pla
@long:  lda #PW_LENGTH
        rts
@keep:  sta values, x
        inc count
        jmp @char
        ; Now line by line: each line's check, then its data into the bits.
@lines: jsr bits_clear
        lda #0
        sta zp_t0                   ; the line's first symbol
@line:  lda zp_t0
        cmp count
        bne @some
        lda count                   ; the end: there must have been something
        bne @done
        lda #PW_LENGTH
        rts
@done:  jsr bits_rewind
        lda #PW_OK
        rts
@some:  inc pw_bad_line             ; (the line's number, from 1)
        lda count                   ; its length: 20, or what's left
        sec
        sbc zp_t0
        cmp #LINE
        bcc @short
        lda #LINE
@short: cmp #2
        bcs @long_enough
        lda #PW_LENGTH
        rts
@long_enough:
        sta zp_t1                   ; the line's symbols
        dec zp_t1                   ; its data: all but the last
        lda #0
        sta zp_pw_sum
        sta zp_t2                   ; i
@sum:   lda zp_t0                   ; sum += value[i] x (2i + 1)
        clc
        adc zp_t2
        tax
        lda zp_t2
        asl a
        tay
        iny                         ; Y = 2i + 1
@times: lda zp_pw_sum
        clc
        adc values, x
        sta zp_pw_sum
        dey
        bne @times
        inc zp_t2
        lda zp_t2
        cmp zp_t1
        bne @sum
        lda zp_t0                   ; the check symbol
        clc
        adc zp_t1
        tax
        lda zp_pw_sum
        and #31
        cmp values, x
        beq @right
        lda #PW_LINE
        rts
@right: lda #0                      ; the data into the bits
        sta zp_t2
@data:  lda zp_t0
        clc
        adc zp_t2
        tax
        lda values, x
        sta zp_pw_value
        lda #0
        sta zp_pw_value + 1
        lda #5
        jsr bits_put
        inc zp_t2
        lda zp_t2
        cmp zp_t1
        bne @data
        lda zp_t0                   ; on to the next line
        clc
        adc zp_t1
        adc #1
        sta zp_t0
        jmp @line

; ----------------------------------------------------------------------------------------
; pw_write: the bits (pw_len of them, a multiple of 5) as password text: their symbols,
; each 19 followed by the line's check symbol, and the last line's too. No spaces.
;   Takes:   A/X = where the text goes (low/high).
;   After:   the text there, ending in 0; pw_pos at the end.
;   Changes: A, X, Y; zp_pw_text, zp_pw_value, zp_pw_n, zp_pw_sum; zp_t2.
pw_write:
        sta zp_pw_text
        stx zp_pw_text + 1
        jsr bits_rewind
@line:  jsr at_end
        bcs @end
        lda #0
        sta zp_pw_sum
        sta zp_t2                   ; i
@sym:   lda #5
        jsr bits_get
        lda zp_t2                   ; sum += value x (2i + 1)
        asl a
        tay
        iny
@times: lda zp_pw_sum
        clc
        adc zp_pw_value
        sta zp_pw_sum
        dey
        bne @times
        ldx zp_pw_value
        lda symbols, x
        jsr put_char
        inc zp_t2
        lda zp_t2
        cmp #LINE - 1
        beq @check
        jsr at_end
        bcc @sym
@check: lda zp_pw_sum
        and #31
        tax
        lda symbols, x
        jsr put_char
        jmp @line
@end:   lda #0
        tay
        sta (zp_pw_text), y
        rts

; put_char: A at the text, and on one. Changes Y.
put_char:
        ldy #0
        sta (zp_pw_text), y
        inc zp_pw_text
        bne @same
        inc zp_pw_text + 1
@same:  rts

; at_end: C set if pw_pos has reached pw_len. Changes A.
at_end:
        lda pw_pos + 1
        cmp pw_len + 1
        bne @done
        lda pw_pos
        cmp pw_len
@done:  rts

; ----------------------------------------------------------------------------------------
; bits_clear: no bits: the buffer zeroed, pw_pos and pw_len 0.
;   Changes: A, X.
bits_clear:
        lda #0
        tax
@zero:  sta pw_buffer, x
        inx
        bne @zero
        sta pw_len
        sta pw_len + 1
        ; (on into bits_rewind)

; bits_rewind: pw_pos back to the first bit. Changes A.
bits_rewind:
        lda #0
        sta pw_pos
        sta pw_pos + 1
        rts

; ----------------------------------------------------------------------------------------
; bits_get: the next bits, read at pw_pos, which moves on past them.
;   Takes:   A = how many, 1-16.
;   After:   C clear: zp_pw_value = them (the last read in its lowest bit); C set: there
;            weren't that many left (pw_pos as it was).
;   Changes: A, X, Y; zp_pw_value, zp_pw_n.
bits_get:
        sta zp_pw_n
        clc                         ; pw_pos + n <= pw_len?
        adc pw_pos
        tax
        lda pw_pos + 1
        adc #0
        cmp pw_len + 1
        bcc @room
        bne @short
        cpx pw_len
        beq @room
        bcs @short
@room:  lda #0
        sta zp_pw_value
        sta zp_pw_value + 1
        ldx zp_pw_n
@bit:   jsr bit_at
        and pw_buffer, y            ; C = the bit
        cmp #1
        rol zp_pw_value
        rol zp_pw_value + 1
        inc pw_pos
        bne @next
        inc pw_pos + 1
@next:  dex
        bne @bit
        clc
        rts
@short: sec
        rts

; ----------------------------------------------------------------------------------------
; bits_put: a value as bits, at pw_pos, which moves on past them (and pw_len with it).
;   Takes:   A = how many bits, 1-16; zp_pw_value = the value.
;   After:   C clear; or C set: the value doesn't fit in that many bits (nothing put).
;   Changes: A, X, Y; zp_pw_value (shifted away), zp_pw_n.
bits_put:
        sta zp_pw_n
        lda #16                     ; up to the top: what falls out must be 0
        sec
        sbc zp_pw_n
        tax
        beq @put
@up:    asl zp_pw_value
        rol zp_pw_value + 1
        bcs @too_big
        dex
        bne @up
@put:   ldx zp_pw_n
@bit:   asl zp_pw_value
        rol zp_pw_value + 1
        bcc @zero
        jsr bit_at
        ora pw_buffer, y
        sta pw_buffer, y
@zero:  inc pw_pos
        bne @next
        inc pw_pos + 1
@next:  dex
        bne @bit
        lda pw_pos                  ; the length: as far as has been put
        sta pw_len
        lda pw_pos + 1
        sta pw_len + 1
        clc
        rts
@too_big:
        sec
        rts

; bit_at: pw_pos as a place in pw_buffer: Y = its byte, A = its bit's mask. Keeps X.
bit_at:
        lda pw_pos + 1              ; pw_pos / 8: the high byte's bits on top
        asl a
        asl a
        asl a
        asl a
        asl a
        sta bit_byte
        lda pw_pos
        lsr a
        lsr a
        lsr a
        ora bit_byte
        tay
        stx bit_x
        lda pw_pos
        and #7
        tax
        lda masks, x
        ldx bit_x
        rts

masks:  .byte $80, $40, $20, $10, $08, $04, $02, $01

; ----------------------------------------------------------------------------------------
; bits_crc: the CRC-16/CCITT-FALSE (polynomial $1021, from $FFFF) of pw_buffer's first
; bytes.
;   Takes:   A = how many bytes (1-255).
;   After:   crc (low, high).
;   Changes: A, X, Y.
bits_crc:
        sta bit_byte
        lda #$FF
        sta crc
        sta crc + 1
        ldy #0
@byte:  lda pw_buffer, y
        eor crc + 1
        sta crc + 1
        ldx #8
@bit:   asl crc
        rol crc + 1
        bcc @next
        lda crc + 1
        eor #$10
        sta crc + 1
        lda crc
        eor #$21
        sta crc
@next:  dex
        bne @bit
        iny
        cpy bit_byte
        bne @byte
        rts

; The alphabet: a symbol's value is its place.
symbols:
        .byte "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

        .segment "BSS"
pw_buffer:      .res 256            ; the bits
pw_pos:         .res 2              ; the next bit to read or write
pw_len:         .res 2              ; how many there are
pw_bad_line:    .res 1              ; the line a PW_LINE is on, from 1
crc:            .res 2
values:         .res MAX_SYMBOLS    ; the symbols read, as values
count:          .res 1              ; how many
bit_byte:       .res 1
bit_x:          .res 1
