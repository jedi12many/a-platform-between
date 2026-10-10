; A car's strings, expanded (docs/vm-spec.md, "Text encoding"; the C version is vm/vm.c's
; expand): their byte pairs unpacked from the depot's pair table, their inserts (the
; traveler's name, race, class, Debt and level; a var; the yard) written out. Every byte is
; checked as it's read: a string that runs off its car, a pair that isn't in the table or
; nests too deep, a byte that isn't text, and the string is refused.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"

        .export expand, out_char, out_text, out_end
        .import string_count, offsets_at, strings_at, car_end, pair_count, pairs_at
        .import var_count, vars, yard, traveler, name_text, number_text
        .import race_lo, race_hi, class_lo, class_hi
        .importzp RACE_COUNT, CLASS_COUNT

BPE_DEPTH       = 16                ; pairs inside pairs, at most
TXT_NAME        = $01
TXT_RACE        = $02
TXT_CLASS       = $03
TXT_DEBT        = $04
TXT_VAR         = $05               ; then the var's number + 1
TXT_LEVEL       = $06
TXT_YARD        = $07
TXT_NEWLINE     = $0A

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; expand: string A/X (low/high) of the loaded car, onto zp_out up to out_end (what doesn't
; fit is dropped). No 0 at the end: the caller ends it.
;   Before:  a car loaded (depot.s).
;   After:   C clear, zp_out past the text; or C set: a bad string.
;   Changes: A, X, Y; zp_str, zp_out; zp_t0, zp_t1; number.s's zero page.
expand: sta zp_t0
        stx zp_t1
        cmp string_count            ; one of the car's?
        txa
        sbc string_count + 1
        bcc :+
        jmp @bad
:
        asl zp_t0                   ; its offset: at offsets_at + 2 x id
        rol zp_t1
        lda zp_t0
        clc
        adc offsets_at
        sta zp_t0
        lda zp_t1
        adc offsets_at + 1
        sta zp_t1
        ldy #0
        lda (zp_t0), y
        clc
        adc strings_at
        sta zp_str
        iny
        lda (zp_t0), y
        adc strings_at + 1
        sta zp_str + 1
        bcc :+                      ; (past $FFFF)
        jmp @bad
:
        lda #0
        sta want_var
@byte:  lda zp_str                  ; inside the car?
        cmp car_end
        lda zp_str + 1
        sbc car_end + 1
        bcs @bad
        ldy #0
        lda (zp_str), y
        inc zp_str
        bne @got
        inc zp_str + 1
@got:   cmp #0
        beq @end
        sta stack_byte              ; the pair stack: this byte, at depth 0
        lda #0
        sta stack_depth
        lda #1
        sta depth_n
@pop:   ldx depth_n
        beq @byte
        dex
        stx depth_n
        lda stack_byte, x
        bpl @plain
        and #$7F                    ; a pair: its second byte under its first
        cmp pair_count
        bcs @bad
        ldy stack_depth, x
        cpy #BPE_DEPTH
        bcs @bad
        iny
        sty depth
        asl a                       ; at pairs_at + 2 x pair
        clc
        adc pairs_at
        sta zp_t0
        lda pairs_at + 1
        adc #0
        sta zp_t1
        ldy #1
        lda (zp_t0), y
        sta stack_byte, x
        lda depth
        sta stack_depth, x
        inx
        dey
        lda (zp_t0), y
        sta stack_byte, x
        lda depth
        sta stack_depth, x
        inx
        stx depth_n
        jmp @pop
@plain: jsr plain
        bcs @bad
        jmp @pop
@end:   lda want_var                ; (a var's number never came)
        bne @bad
        clc
        rts
@bad:   sec
        rts

; plain: one byte of text, or an insert. After: C set if it's bad. Changes A, X, Y;
; zp_t0, zp_t1; number.s's zero page. Keeps depth_n and the stack.
plain:  ldx want_var
        beq @not_var
        ldx #0                      ; the var: its number + 1
        stx want_var
        cmp #1
        bcs :+
        jmp @bad
:
        sbc #1
        cmp var_count
        bcc :+
        jmp @bad
:
        tax
        lda vars, x
        ldx #0
        jmp out_number
@not_var:
        cmp #TXT_VAR
        bne @not_var_mark
        sta want_var
        clc
        rts
@not_var_mark:
        cmp #TXT_NAME
        bne @not_name
        jsr name_text
        jmp out_text
@not_name:
        cmp #TXT_RACE
        bne @not_race
        ldx traveler + CH_RACE
        cpx #RACE_COUNT
        bcs @nothing
        lda race_lo, x
        pha
        lda race_hi, x
        tax
        pla
        jmp out_text
@not_race:
        cmp #TXT_CLASS
        bne @not_class
        ldx traveler + CH_CLASS
        cpx #CLASS_COUNT
        bcs @nothing
        lda class_lo, x
        pha
        lda class_hi, x
        tax
        pla
        jmp out_text
@not_class:
        cmp #TXT_DEBT
        bne @not_debt
        lda traveler + CH_DEBT
        ldx traveler + CH_DEBT + 1
        jmp out_number
@not_debt:
        cmp #TXT_LEVEL
        bne @not_level
        lda traveler + CH_LEVEL
        ldx #0
        jmp out_number
@not_level:
        cmp #TXT_YARD
        bne @not_yard
        lda yard
        ldx yard + 1
        jmp out_number
@not_yard:
        cmp #TXT_NEWLINE
        beq @text
        cmp #$20
        bcc @bad
        cmp #$7F
        bcs @bad
@text:  jsr out_char
@nothing:
        clc
        rts
@bad:   sec
        rts

; out_number: A/X (low/high) in digits onto zp_out. After: C clear. Changes A, X, Y;
; zp_t0, zp_t1; number.s's zero page.
out_number:
        sta zp_num
        stx zp_num + 1
        jsr number_text
        ; (on into out_text)

; out_text: ASCII (A/X, ending in 0) onto zp_out. After: C clear. Changes A, Y; zp_t0,
; zp_t1.
out_text:
        sta zp_t0
        stx zp_t1
        ldy #0
@char:  lda (zp_t0), y
        beq @done
        jsr out_char
        iny
        bne @char
@done:  clc
        rts

; out_char: A onto zp_out, if it's before out_end. Keeps X, Y.
out_char:
        pha
        lda zp_out
        cmp out_end
        lda zp_out + 1
        sbc out_end + 1
        bcs @full
        sty keep_y
        ldy #0
        pla
        sta (zp_out), y
        ldy keep_y
        inc zp_out
        bne @same
        inc zp_out + 1
@same:  rts
@full:  pla
        rts

        .segment "BSS"
out_end:        .res 2              ; the room ends here
want_var:       .res 1              ; a var's number is next
depth_n:        .res 1              ; entries on the pair stack
depth:          .res 1
keep_y:         .res 1
stack_byte:     .res BPE_DEPTH + 2
stack_depth:    .res BPE_DEPTH + 2
