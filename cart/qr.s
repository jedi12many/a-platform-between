; A QR code (ISO/IEC 18004), for the Travel Stamp at a trip's end (docs/passport-spec.md,
; "Carriers"): its text in alphanumeric mode, error correction level L, versions 1 to 4
; (21 to 33 modules square, one block of Reed-Solomon codewords each), the smallest the
; text fits; always mask 0, which any reader takes (the standard's choice of mask, by
; penalty, is an encoder's nicety). tests/cart/run_cart.py holds it to the qrcode
; library's code, module for module, and scans the screen with OpenCV.
;
; The modules are bytes at QR_MATRIX, a row at a time: bit 0 dark, bit 1 a function
; module (the finders, the timing, the alignment, the format), which the data skips.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export qr_make, qr_size, qr_row_lo, qr_row_hi

DARK            = 1
FUNCTION        = 2
SIZE_TOP        = 33                ; version 4's
FORMAT_L_MASK0  = %111011111000100  ; level L (01), mask 0, its BCH bits, masked $5412
GF_REDUCE       = $1D               ; x^8 = x^4 + x^3 + x^2 + 1 (the field's $11D)

        .segment "ENDING"

; ----------------------------------------------------------------------------------------
; qr_make: the QR code of a text.
;   Takes:   A/X = the text (low/high): digits and capitals, ending in 0, 114 at most.
;   After:   C clear: the modules at QR_MATRIX, qr_size of them a side; or C set: the
;            text doesn't fit, or has something alphanumeric mode hasn't (nothing made).
;   Changes: A, X, Y; zp_qr; zp_t0-zp_t3.
qr_make:
        sta zp_qr
        stx zp_qr + 1
        ldy #0                      ; its length, and each character's value: 0-35
@char:  lda (zp_qr), y
        beq @counted
        cmp #'0'
        bcc @refuse
        cmp #'9' + 1
        bcc @digit
        cmp #'A'
        bcc @refuse
        cmp #'Z' + 1
        bcs @refuse
        sbc #'A' - 10 - 1           ; (C clear: one less)
        jmp @value
@digit: sbc #'0' - 1                ; (C clear)
@value: sta values, y
        iny
        cpy #TEXT_TOP + 1
        bne @char
@refuse:
        sec
        rts
@counted:
        sty length
        ldx #0                      ; the version: the first it fits
@version:
        lda capacity, x
        cmp length
        bcs @fits
        inx
        cpx #4
        bne @version
        sec
        rts
@fits:  stx version
        lda sizes, x
        sta qr_size
        lda data_words, x
        sta data_count
        lda ec_words, x
        sta ec_count
        jsr rows
        jsr gf_tables
        jsr encode
        jsr correct
        jsr functions
        jsr place
        jsr mask
        clc
        rts

TEXT_TOP = 114

; ----------------------------------------------------------------------------------------
; rows: each row's place in QR_MATRIX (qr_row_lo, qr_row_hi), qr_size apart; the matrix
; clear.
; Changes A, X, Y.
rows:   lda #<QR_MATRIX
        sta zp_qr
        lda #>QR_MATRIX
        sta zp_qr + 1
        ldx #0
@row:   lda zp_qr
        sta qr_row_lo, x
        lda zp_qr + 1
        sta qr_row_hi, x
        lda #0
        ldy qr_size
@clear: dey
        sta (zp_qr), y
        bne @clear
        lda zp_qr
        clc
        adc qr_size
        sta zp_qr
        bcc @next
        inc zp_qr + 1
@next:  inx
        cpx qr_size
        bne @row
        rts

; at: zp_qr at module (X, Y): column X, row Y. Changes A.
at:     txa
        clc
        adc qr_row_lo, y
        sta zp_qr
        lda qr_row_hi, y
        adc #0
        sta zp_qr + 1
        rts

; set_function: module (X, Y) a function module, dark if A is 1. Keeps X, Y. Changes A.
set_function:
        ora #FUNCTION
        sty keep_y
        pha
        jsr at
        pla
        ldy #0
        sta (zp_qr), y
        ldy keep_y
        rts

; ----------------------------------------------------------------------------------------
; gf_tables: GF(256)'s powers of 2 (QR_EXP) and their logarithms (QR_LOG). Changes A, X.
gf_tables:
        lda #1
        ldx #0
@power: sta QR_EXP, x
        pha
        tay
        txa
        sta QR_LOG, y
        pla
        asl a
        bcc @same
        eor #GF_REDUCE
@same:  inx
        cpx #255
        bne @power
        rts

; gf_times: A x X in GF(256). After: A. Changes A, Y.
gf_times:
        cmp #0
        beq @zero
        cpx #0
        beq @none
        tay
        lda QR_LOG, y
        clc
        adc QR_LOG, x
        bcc @under
        adc #0                      ; (256 and over: less 255, one more than the byte)
        jmp @power
@under: cmp #255
        bne @power
        lda #0
@power: tay
        lda QR_EXP, y
        rts
@none:  lda #0
@zero:  rts

; ----------------------------------------------------------------------------------------
; encode: the text's bits as the data codewords (QR_CODEWORDS, data_count of them): the
; mode (0010), the length (9 bits), each pair of characters as 45a + b (11 bits) and a
; last one alone (6), up to 4 zero bits to end, zero bits to a byte, then the pad bytes
; $EC and $11 by turns. Changes A, X, Y; zp_t0-zp_t3.
encode: ldx #0
        txa
@zero:  sta QR_CODEWORDS, x
        inx
        cpx #100
        bne @zero
        sta bit_pos
        sta bit_pos + 1
        lda #%0010                  ; alphanumeric
        ldx #0
        ldy #4
        jsr put_bits
        lda length
        ldx #0
        ldy #9
        jsr put_bits
        lda #0
        sta zp_t3                   ; the character
@pair:  ldx zp_t3
        cpx length
        bcs @ended
        inx
        cpx length
        beq @last
        ldx zp_t3                   ; 45a + b: a x 32 + a x 8 + a x 4 + a + b
        lda values, x
        sta zp_t0
        lda #0
        sta zp_t1
        asl zp_t0                   ; a x 4
        rol zp_t1
        asl zp_t0
        rol zp_t1
        lda zp_t0
        sta zp_t2
        lda zp_t1
        pha
        asl zp_t0                   ; a x 8
        rol zp_t1
        lda zp_t0
        clc
        adc zp_t2
        sta zp_t2
        pla
        adc zp_t1
        pha
        asl zp_t0                   ; a x 32
        rol zp_t1
        asl zp_t0
        rol zp_t1
        lda zp_t0
        clc
        adc zp_t2
        sta zp_t2
        pla
        adc zp_t1
        sta zp_t1
        lda values, x               ; + a
        clc
        adc zp_t2
        sta zp_t2
        bcc @plus_b
        inc zp_t1
@plus_b:
        lda values + 1, x           ; + b
        clc
        adc zp_t2
        bcc @put
        inc zp_t1
@put:   ldx zp_t1
        ldy #11
        jsr put_bits
        inc zp_t3
        inc zp_t3
        jmp @pair
@last:  ldx zp_t3
        lda values, x
        ldx #0
        ldy #6
        jsr put_bits
@ended: lda data_count              ; the end: up to 4 zero bits, to a byte
        asl a
        sta zp_t0
        lda #0
        rol a
        asl zp_t0
        rol a
        asl zp_t0
        rol a
        sta zp_t1                   ; the capacity, in bits
        ldy #4
@four:  lda bit_pos
        cmp zp_t0
        lda bit_pos + 1
        sbc zp_t1
        bcs @padded
        jsr next_bit
        dey
        bne @four
@to_byte:
        lda bit_pos
        and #7
        beq @padded
        jsr next_bit
        jmp @to_byte
@padded:
        jsr bit_byte                ; the next byte
        lda #$EC
@pad:   cpx data_count
        bcs @done
        sta QR_CODEWORDS, x
        eor #$EC ^ $11              ; ($EC, $11, $EC, ...)
        inx
        bne @pad                    ; (always)
@done:  rts

; bit_byte: X = bit_pos / 8, the codeword it's in. Changes A, X.
bit_byte:
        lda bit_pos + 1
        sta byte_hi
        lda bit_pos
        lsr byte_hi
        ror a
        lsr byte_hi
        ror a
        lsr byte_hi
        ror a
        tax
        rts

; next_bit: bit_pos on one. Changes nothing else.
next_bit:
        inc bit_pos
        bne @same
        inc bit_pos + 1
@same:  rts

; put_bits: A/X (low/high) as Y bits (1-11), the first the highest, into the codewords
; at bit_pos. Changes A, X, Y; zp_t0-zp_t2.
put_bits:
        sta zp_t0
        stx zp_t1
        sty zp_t2
        lda #16                     ; up to the top of the 16
        sec
        sbc zp_t2
        tay
@up:    asl zp_t0
        rol zp_t1
        dey
        bne @up
@bit:   asl zp_t0
        rol zp_t1
        bcc @zero
        jsr bit_byte                ; its byte
        lda bit_pos
        and #7
        tay
        lda bit_mask, y
        ora QR_CODEWORDS, x
        sta QR_CODEWORDS, x
@zero:  jsr next_bit
        dec zp_t2
        bne @bit
        rts

; ----------------------------------------------------------------------------------------
; correct: the error correction codewords after the data: the remainder of the data,
; times x^n, divided by (x - 1)(x - 2)(x - 4)... (n of them, powers of 2 in GF(256)).
; Changes A, X, Y; zp_t0-zp_t2.
correct:
        ldx ec_count                ; the generator, low terms first: 0 ... 0 1
        lda #0
@clear: sta QR_GENERATOR - 1, x
        dex
        bne @clear
        ldx ec_count
        lda #1
        sta QR_GENERATOR - 1, x
        sta zp_t2                   ; root: 1, 2, 4, ...
        lda #0
        sta zp_t0                   ; i
@times: ldy #0                      ; each term times root, plus the next term
@term:  sty zp_t1
        lda QR_GENERATOR, y
        ldx zp_t2
        jsr gf_times
        ldy zp_t1
        iny
        cpy ec_count
        beq @last
        eor QR_GENERATOR, y
@last:  dey
        sta QR_GENERATOR, y
        iny
        cpy ec_count
        bne @term
        lda zp_t2                   ; root x 2
        ldx #2
        jsr gf_times
        sta zp_t2
        inc zp_t0
        lda zp_t0
        cmp ec_count
        bne @times
        ; The remainder, in the codewords after the data (zero there already).
        lda #0
        sta zp_t0                   ; the data codeword
@word:  ldx zp_t0
        lda QR_CODEWORDS, x
        ldy data_count
        eor QR_CODEWORDS, y         ; factor: the codeword plus the remainder's first
        sta zp_t2
        ldx data_count              ; the remainder up one
@shift: lda QR_CODEWORDS + 1, x
        sta QR_CODEWORDS, x
        inx
        txa
        sec
        sbc data_count
        cmp ec_count
        bne @shift
        lda #0
        sta QR_CODEWORDS - 1, x
        ldy #0                      ; plus the generator times factor
@add:   sty zp_t1
        lda QR_GENERATOR, y
        ldx zp_t2
        jsr gf_times
        sta zp_t3
        lda zp_t1
        clc
        adc data_count
        tax
        lda QR_CODEWORDS, x
        eor zp_t3
        sta QR_CODEWORDS, x
        ldy zp_t1
        iny
        cpy ec_count
        bne @add
        inc zp_t0
        lda zp_t0
        cmp data_count
        bne @word
        rts

; ----------------------------------------------------------------------------------------
; functions: the function modules: the timing lines, the three finders (and their light
; borders), the alignment pattern (from version 2), the format bits for level L and mask
; 0, and the one dark module. Changes A, X, Y; zp_t0-zp_t3.
functions:
        ldx #0                      ; timing: row 6 and column 6, dark on even modules
@timing:
        txa
        and #1
        eor #DARK
        ldy #6
        jsr set_function
        stx keep_x
        ldy keep_x
        ldx #6
        jsr set_function
        ldx keep_x
        inx
        cpx qr_size
        bne @timing
        ldx #3                      ; the finders: centred at (3, 3), (size - 4, 3),
        ldy #3                      ; (3, size - 4)
        jsr finder
        lda qr_size
        sec
        sbc #4
        tax
        ldy #3
        jsr finder
        lda qr_size
        sec
        sbc #4
        tay
        ldx #3
        jsr finder
        lda version                 ; the alignment pattern: centred at (size - 7) twice
        beq @format
        lda qr_size
        sec
        sbc #7 + 2
        sta zp_t0                   ; its top left
        lda #0
        sta zp_t3                   ; row
@a_row: lda #0
        sta zp_t2                   ; column
@a_col: ldx zp_t2                   ; dark but on the ring one from the centre
        ldy zp_t3
        lda ring5, x
        cmp ring5, y
        bcs @a_far
        lda ring5, y
@a_far: cmp #1
        beq @a_light
        lda #DARK
        bne @a_set                  ; (always)
@a_light:
        lda #0
@a_set: pha
        lda zp_t0
        clc
        adc zp_t2
        tax
        lda zp_t0
        clc
        adc zp_t3
        tay
        pla
        jsr set_function
        inc zp_t2
        lda zp_t2
        cmp #5
        bne @a_col
        inc zp_t3
        lda zp_t3
        cmp #5
        bne @a_row
@format:
        ldy #0                      ; bits 0-5 at (8, 0-5)
@f1:    lda format_bits, y
        ldx #8
        jsr set_function
        iny
        cpy #6
        bne @f1
        lda format_bits + 6         ; bit 6 at (8, 7), 7 at (8, 8), 8 at (7, 8)
        ldx #8
        ldy #7
        jsr set_function
        lda format_bits + 7
        ldy #8
        jsr set_function
        lda format_bits + 8
        ldx #7
        jsr set_function
        ldx #9                      ; bits 9-14 at (14 - i, 8)
@f2:    stx zp_t0
        lda #14
        sec
        sbc zp_t0
        tax
        ldy zp_t0
        lda format_bits, y
        ldy #8
        jsr set_function
        ldx zp_t0
        inx
        cpx #15
        bne @f2
        ldx #0                      ; again: bits 0-7 at (size - 1 - i, 8)
@f3:    stx zp_t0
        lda qr_size
        clc
        sbc zp_t0                   ; (size - 1 - i)
        tax
        ldy zp_t0
        lda format_bits, y
        ldy #8
        jsr set_function
        ldx zp_t0
        inx
        cpx #8
        bne @f3
        ldx #8                      ; bits 8-14 at (8, size - 15 + i)
@f4:    stx zp_t0
        lda qr_size
        sec
        sbc #15
        clc
        adc zp_t0
        tay
        ldx zp_t0
        lda format_bits, x
        ldx #8
        jsr set_function
        ldx zp_t0
        inx
        cpx #15
        bne @f4
        lda qr_size                 ; and the dark module, at (8, size - 8)
        sec
        sbc #8
        tay
        ldx #8
        lda #DARK
        jmp set_function

; finder: a finder pattern centred at (X, Y), with its light border, inside the code:
; dark but on the rings 2 and 4 from the centre. Changes A, X, Y; zp_t0-zp_t3.
finder: txa
        sec
        sbc #4
        sta zp_t0                   ; its left
        tya
        sec
        sbc #4
        sta zp_t1                   ; its top
        lda #0
        sta zp_t3                   ; row
@row:   lda #0
        sta zp_t2                   ; column
@col:   lda zp_t0
        clc
        adc zp_t2
        cmp qr_size                 ; inside? (off the left wraps past it)
        bcs @next
        tax
        lda zp_t1
        clc
        adc zp_t3
        cmp qr_size
        bcs @next
        tay
        stx keep_x
        ldx zp_t2
        lda ring9, x
        ldx zp_t3
        cmp ring9, x
        bcs @far
        lda ring9, x
@far:   ldx keep_x
        cmp #2
        beq @light
        cmp #4
        beq @light
        lda #DARK
        bne @set                    ; (always)
@light: lda #0
@set:   jsr set_function
@next:  inc zp_t2
        lda zp_t2
        cmp #9
        bne @col
        inc zp_t3
        lda zp_t3
        cmp #9
        bne @row
        rts

; ----------------------------------------------------------------------------------------
; place: the codewords' bits, the first the highest, into the modules that aren't
; function modules: two columns at a time from the right, up and down by turns, past
; column 6. Modules left over stay light. Changes A, X, Y; zp_t0-zp_t3.
place:  lda #0
        sta bit_pos
        sta bit_pos + 1
        lda data_count              ; the bits: 8 a codeword
        clc
        adc ec_count
        sta zp_t0
        lda #0
        asl zp_t0
        rol a
        asl zp_t0
        rol a
        asl zp_t0
        rol a
        sta zp_t1
        lda zp_t0
        sta bits_total
        lda zp_t1
        sta bits_total + 1
        ldx qr_size                 ; right: size - 1, down by 2
        dex
        stx right
@pair:  lda right
        cmp #6
        bne @column
        dec right
@column:
        lda #0
        sta vert
@vert:  lda #0
        sta side
@side:  lda right                   ; x: right, then right - 1
        sec
        sbc side
        tax
        lda right                   ; up when (right + 1) & 2 is 0
        clc
        adc #1
        and #2
        bne @down
        lda qr_size                 ; up: y = size - 1 - vert
        clc
        sbc vert
        jmp @y
@down:  lda vert
@y:     tay
        jsr at
        ldy #0
        lda (zp_qr), y
        and #FUNCTION
        bne @skip
        lda bit_pos                 ; any bits left?
        cmp bits_total
        lda bit_pos + 1
        sbc bits_total + 1
        bcs @skip
        jsr bit_byte                ; the bit: in codeword bit_pos / 8, from its top
        lda bit_pos
        and #7
        tay
        lda QR_CODEWORDS, x
        and bit_mask, y
        beq @light
        lda #DARK
@light: ldy #0
        sta (zp_qr), y
        jsr next_bit
@skip:  inc side
        lda side
        cmp #2
        bne @side
        inc vert
        lda vert
        cmp qr_size
        bne @vert
        lda right
        sec
        sbc #2
        sta right
        bcc @done                   ; (past column 0)
        beq @done                   ; (column 0 is its pair's left)
        jmp @pair
@done:  rts

; ----------------------------------------------------------------------------------------
; mask: mask 0: every module that isn't a function module, with (x + y) even, flipped.
; Changes A, X, Y.
mask:   ldy #0
@row:   ldx #0
@col:   jsr at
        txa
        sty keep_y
        clc
        adc keep_y
        and #1
        bne @next
        ldy #0
        lda (zp_qr), y
        and #FUNCTION
        bne @kept
        lda (zp_qr), y
        eor #DARK
        sta (zp_qr), y
@kept:  ldy keep_y
@next:  inx
        cpx qr_size
        bne @col
        iny
        cpy qr_size
        bne @row
        rts

; The versions 1-4 at level L: how many characters, the size, the codewords.
capacity:       .byte 25, 47, 77, 114
sizes:          .byte 21, 25, 29, 33
data_words:     .byte 19, 34, 55, 80
ec_words:       .byte 7, 10, 15, 20
bit_mask:       .byte $80, $40, $20, $10, $08, $04, $02, $01
ring9:          .byte 4, 3, 2, 1, 0, 1, 2, 3, 4     ; distance from a finder's centre
ring5:          .byte 2, 1, 0, 1, 2                 ; and the alignment pattern's
format_bits:    .repeat 15, i                       ; bit i of the format
                .byte (FORMAT_L_MASK0 >> i) & 1
                .endrepeat

        .segment "BSS"
qr_size:        .res 1
version:        .res 1              ; 0-3: versions 1-4
length:         .res 1
data_count:     .res 1
ec_count:       .res 1
values:         .res TEXT_TOP + 1   ; each character's value
bit_pos:        .res 2
bits_total:     .res 2
byte_hi:        .res 1
right:          .res 1
vert:           .res 1
side:           .res 1
keep_x:         .res 1
keep_y:         .res 1
qr_row_lo:         .res SIZE_TOP
qr_row_hi:         .res SIZE_TOP
