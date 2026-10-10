; The Passport and the Boarding Pass (docs/passport-spec.md, docs/boarding.md): their
; fields, read from a password into `traveler` (and `pass`), and a Passport written from
; `traveler`. The bits and the text are password.s's.
;
; A Passport: version (4 bits, 2), then the traveler's fields. A Boarding Pass: kind (4
; bits, 8), Departure (16), ticket (32), seed (16), Rewind (1), then the same as a
; Passport from its version on. Both: zero bits to a byte, a CRC-16 of every byte, zero
; bits to a symbol (fewer than 5).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"

        .export password_decode, passport_encode, traveler, pass, password_kind
        .import pw_read, pw_write, bits_clear, bits_rewind, bits_get, bits_put, bits_crc
        .import pw_pos, pw_len, crc

VERSION = 2

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; password_decode: a typed Boarding Pass or Passport, whichever it is, read.
;   Takes:   A/X = the text (low/high), ASCII, ending in 0.
;   After:   A = PW_OK, Z set: `traveler` filled in, and password_kind = KIND_PASS
;            (`pass` filled in too) or KIND_PASSPORT. Else A = a PW_ code, Z clear (for
;            PW_LINE, pw_bad_line says which line); `traveler` and `pass` may be partly
;            filled in.
;   Changes: A, X, Y; password.s's zero page; zp_t0-zp_t3.
password_decode:
        ldy #0                      ; (A/X: the text)
        sty refused
        jsr pw_read
        beq @read
        rts
@read:  lda #4                      ; the kind
        jsr get
        bcs @short
        lda zp_pw_value
        sta password_kind
        cmp #KIND_PASS
        bne @passport
        ldx #0                      ; a pass: its own fields
@field: lda pass_fields, x
        beq @carried
        jsr get
        bcs @short
        ldy pass_fields + 1, x
        lda zp_pw_value
        sta pass, y
        lda zp_pw_value + 1
        sta pass + 1, y
        inx
        inx
        bne @field                  ; (always)
@carried:
        lda #4                      ; then the Passport it carries, from its version
        jsr get
        bcs @short
        lda zp_pw_value
@passport:
        cmp #VERSION
        beq @fields
        lda #PW_VERSION
        rts
@short: lda refused                 ; reading stopped: a rule broken, or the bits ran
        bne @wrong                  ; out
        lda #PW_LENGTH
        rts
@fields:
        jsr read_traveler
        bcs @short
        ; Zero bits to a byte; the CRC of every byte so far; and nothing after but fewer
        ; than 5 zero bits.
@pad:   lda pw_pos
        and #7
        beq @padded
        lda #1
        jsr get
        bcs @short
        lda zp_pw_value
        bne @wrong
        beq @pad                    ; (always)
@padded:
        jsr pos_bytes               ; the bytes so far
        pha
        lda #16
        jsr get
        pla
        bcs @short
        jsr bits_crc
        lda crc
        cmp zp_pw_value
        bne @wrong
        lda crc + 1
        cmp zp_pw_value + 1
        bne @wrong
        lda pw_len                  ; what's left: fewer than 5 bits, all 0
        sec
        sbc pw_pos
        tax
        lda pw_len + 1
        sbc pw_pos + 1
        bne @long
        cpx #5
        bcs @long
        txa
        beq @ok
        jsr get
        lda zp_pw_value
        bne @wrong
@ok:    jsr fields_fit              ; the numbers in range
        lda refused
        bne @wrong
        lda #PW_OK
        rts
@long:  lda #PW_LENGTH
        rts
@wrong: lda #PW_CHECKSUM
        rts

; pos_bytes: A = pw_pos / 8 (pw_pos a whole number of bytes, under 2048). Changes A.
pos_bytes:
        lda pw_pos + 1
        sta pos8 + 1
        lda pw_pos
        lsr pos8 + 1
        ror a
        lsr pos8 + 1
        ror a
        lsr pos8 + 1
        ror a
        rts

; get: bits_get, keeping X; or, once a rule is broken (`refused`), C set: reading stops
; there, as the C engine's does. Takes A; returns as bits_get.
get:
        stx get_x
        pha
        lda refused
        bne @stop
        pla
        jsr bits_get
        ldx get_x
        rts
@stop:  pla
        ldx get_x
        sec
        rts

; read_traveler: the Passport's fields after its version, into `traveler`, cleared first.
; A list longer than it can be, or an entry repeated or empty (docs/passport-spec.md,
; "What's refused"), sets `refused` where the C engine finds it, and reading stops there
; (get). C set if reading stopped. Changes A, X, Y; zp_pw_value, zp_pw_n; zp_t0-zp_t2.
read_traveler:
        ldx #CH_SIZE - 1            ; a clean record: nothing left from the last one
        lda #0
        sta refused
@clear: sta traveler, x
        dex
        cpx #$FF
        bne @clear
        ldx #0                      ; the name: 8 symbols of the name alphabet
@name:  lda #5
        jsr get
        bcs @out
        ldy zp_pw_value
        lda name_alphabet, y
        sta traveler + CH_NAME, x
        inx
        cpx #8
        bne @name
        ldx #0                      ; the fixed fields, as the table has them
@fixed: lda fixed_fields, x
        beq @lists
        jsr get
        bcs @out
        ldy fixed_fields + 1, x
        lda zp_pw_value
        sta traveler, y
        lda fixed_fields, x         ; a second byte for those over 8 bits
        cmp #9
        bcc @one
        lda zp_pw_value + 1
        sta traveler + 1, y
@one:   inx
        inx
        bne @fixed                  ; (always)
@out:   rts
@lists: ldx #15                     ; training: none, then what's there
        lda #0
@untrained:
        sta traveler + CH_TRAINING, x
        dex
        bpl @untrained
        lda #4
        jsr get
        bcs @out
        lda zp_pw_value
        ldx #SKILLS_MAX
        jsr at_most
        sta zp_t0
        beq @powers
@trained:
        lda #4                      ; a skill, once, then its training, 1 or more
        jsr get
        bcs @out
        lda zp_pw_value
        sta zp_t1
        ldx #SKILLS_MAX - 1
        jsr at_most
        tax
        lda traveler + CH_TRAINING, x
        beq @new
        jsr refuse                  ; (trained already)
@new:   lda #7
        jsr get
        bcs @out
        ldx zp_t1
        lda zp_pw_value
        bne @trains
        jsr refuse                  ; (no training)
@trains:
        sta traveler + CH_TRAINING, x
        dec zp_t0
        bne @trained
@powers:
        lda #4
        jsr get
        bcs @out
        lda zp_pw_value
        ldx #POWERS_MAX
        jsr at_most
        sta traveler + CH_POWER_COUNT
        sta zp_t0
        ldx #0
        lda zp_t0
        beq @items
@power: lda #8                      ; a power (never 0), then its rank
        jsr get
        bcs @out2
        lda zp_pw_value
        sta traveler + CH_POWERS, x
        lda #7
        jsr get
        bcs @out2
        lda zp_pw_value
        sta traveler + CH_POWERS + 1, x
        lda traveler + CH_POWERS, x
        bne @power_id
        jsr refuse                  ; (power 0)
@power_id:
        inx
        inx
        dec zp_t0
        bne @power
@items: ldy #CH_EQUIPPED
        jsr read_slots
        bcs @out2
        ldy #CH_PACK
        jsr read_slots
        bcs @out2
        lda #4                      ; Echoes, oldest first
        jsr get
        bcs @out2
        lda zp_pw_value
        ldx #ECHOES_MAX
        jsr at_most
        sta traveler + CH_ECHO_COUNT
        sta zp_t0
        beq @done
        ldx #0
@echo:  lda #10                     ; an Echo (never 0), then its state
        jsr get
        bcs @out2
        lda zp_pw_value
        sta traveler + CH_ECHOES, x
        lda zp_pw_value + 1
        sta traveler + CH_ECHOES + 1, x
        lda #2
        jsr get
        bcs @out2
        lda zp_pw_value
        sta traveler + CH_ECHOES + 2, x
        lda traveler + CH_ECHOES, x
        ora traveler + CH_ECHOES + 1, x
        bne @echo_id
        jsr refuse                  ; (Echo 0)
@echo_id:
        inx
        inx
        inx
        dec zp_t0
        bne @echo
@done:  clc
@out2:  rts

; fields_fit: the numbers in range (apb's fields_fit), checked after the checksum: level
; 1-100, XP under 100, the stats, the training and the powers' ranks 100 at most;
; `refused` if not. After: C
; clear. Changes A, X.
fields_fit:
        lda traveler + CH_LEVEL
        beq @refuse
        cmp #LEVEL_TOP + 1
        bcs @refuse
        lda traveler + CH_XP
        cmp #XP_PER_LEVEL
        bcs @refuse
        ldx #5
@stat:  lda traveler + CH_STATS, x
        cmp #RATING_TOP + 1
        bcs @refuse
        dex
        bpl @stat
        ldx #SKILLS_MAX - 1
@skill: lda traveler + CH_TRAINING, x
        cmp #RATING_TOP + 1
        bcs @refuse
        dex
        bpl @skill
        ldx #POWERS_MAX * 2 - 1     ; (the ranks: every second byte)
@rank:  lda traveler + CH_POWERS, x
        cmp #RATING_TOP + 1
        bcs @refuse
        dex
        dex
        bpl @rank
        clc
        rts
@refuse:
        jsr refuse
        clc
        rts

; at_most: A over X? Then `refused`. Keeps A, X; after, the flags are A's (as a load
; leaves them).
at_most:
        stx most
        cmp most
        beq @fine
        bcc @fine
        jsr refuse
@fine:  ora #0
        rts

; refuse: `refused` set. Keeps A, X, Y.
refuse: pha
        lda #1
        sta refused
        pla
        rts

; read_slots: an item list (equipped or pack) into its 8 slots at `traveler` + Y: all
; empty, then each slot (3 bits) and item (10). C set if the bits ran out. Changes A, X,
; Y; zp_t0-zp_t2.
read_slots:
        sty zp_t2
        ldx #15
        lda #EMPTY_SLOT
@empty: sta traveler, y
        iny
        dex
        bpl @empty
        lda #3
        jsr get
        bcs @out
        lda zp_pw_value
        ldx #ITEMS_MAX
        jsr at_most
        sta zp_t0
        beq @done
@slot:  lda #3                      ; a slot (one of 6, empty till now), then its item
        jsr get                     ; (never 0)
        bcs @out
        lda zp_pw_value
        ldx #ITEMS_MAX - 1
        jsr at_most
        asl a
        clc
        adc zp_t2
        sta zp_t1
        tay
        lda traveler + 1, y
        cmp #EMPTY_SLOT
        beq @free
        jsr refuse                  ; (taken already)
@free:  lda #10
        jsr get
        bcs @out
        ldy zp_t1
        lda zp_pw_value
        ora zp_pw_value + 1
        bne @item
        jsr refuse                  ; (item 0)
@item:  lda zp_pw_value
        sta traveler, y
        lda zp_pw_value + 1
        sta traveler + 1, y
        dec zp_t0
        bne @slot
@done:  clc
@out:   rts

; ----------------------------------------------------------------------------------------
; passport_encode: `traveler` as a Passport password.
;   Takes:   A/X = where the text goes (low/high): up to 215 symbols and a 0.
;   After:   A = PW_OK, Z set, the text there (no spaces: lines of 20 are for showing);
;            or A = PW_TOO_BIG, Z clear: a field doesn't fit its bits (nothing written).
;   Changes: A, X, Y; password.s's zero page; zp_t0-zp_t3.
passport_encode:
        sta zp_t2
        stx zp_t3
        lda #0
        sta too_big
        jsr bits_clear
        lda #VERSION
        ldx #4
        jsr put_a
        ldx #0                      ; the name: each letter's place in the name alphabet
@name:  lda traveler + CH_NAME, x
        cmp #'a'
        bcc @caps
        cmp #'z' + 1
        bcs @caps
        and #%11011111
@caps:  ldy #31
@find:  cmp name_alphabet, y
        beq @found
        dey
        bne @find                   ; (not there: 0, a space)
@found: tya
        stx zp_t0
        ldx #5
        jsr put_a
        ldx zp_t0
        inx
        cpx #8
        bne @name
        ldx #0                      ; the fixed fields
@fixed: lda fixed_fields, x
        beq @lists
        stx zp_t0
        ldy fixed_fields + 1, x
        lda traveler, y
        sta zp_pw_value
        lda #0
        sta zp_pw_value + 1
        lda fixed_fields, x
        cmp #9
        bcc @one
        lda traveler + 1, y
        sta zp_pw_value + 1
@one:   lda fixed_fields, x
        jsr put
        ldx zp_t0
        inx
        inx
        bne @fixed                  ; (always)
@lists: ldx #15                     ; training: how many, then each, in skill order
        ldy #0
@count: lda traveler + CH_TRAINING, x
        beq @untrained
        iny
@untrained:
        dex
        bpl @count
        tya
        ldx #4
        jsr put_a
        lda #0
        sta zp_t0                   ; the skill
@skill: ldx zp_t0
        lda traveler + CH_TRAINING, x
        beq @next_skill
        txa
        ldx #4
        jsr put_a
        ldx zp_t0
        lda traveler + CH_TRAINING, x
        ldx #7
        jsr put_a
@next_skill:
        inc zp_t0
        lda zp_t0
        cmp #16
        bne @skill
        lda traveler + CH_POWER_COUNT       ; powers
        sta zp_t1
        ldx #4
        jsr put_a
        lda #0
        sta zp_t0
@power: lda zp_t1
        beq @items
        ldx zp_t0
        lda traveler + CH_POWERS, x
        ldx #8
        jsr put_a
        ldx zp_t0
        lda traveler + CH_POWERS + 1, x
        ldx #7
        jsr put_a
        inc zp_t0
        inc zp_t0
        dec zp_t1
        jmp @power
@items: ldy #CH_EQUIPPED
        jsr write_slots
        ldy #CH_PACK
        jsr write_slots
        lda traveler + CH_ECHO_COUNT        ; Echoes
        sta zp_t1
        ldx #4
        jsr put_a
        lda #0
        sta zp_t0
@echo:  lda zp_t1
        beq @end
        ldx zp_t0
        lda traveler + CH_ECHOES, x
        sta zp_pw_value
        lda traveler + CH_ECHOES + 1, x
        sta zp_pw_value + 1
        lda #10
        jsr put
        ldx zp_t0
        lda traveler + CH_ECHOES + 2, x
        ldx #2
        jsr put_a
        lda zp_t0
        clc
        adc #3
        sta zp_t0
        dec zp_t1
        jmp @echo
@end:   lda too_big                 ; did everything fit?
        beq @fits
        lda #PW_TOO_BIG
        rts
@fits:  lda pw_pos                  ; zero bits to a byte
        and #7
        beq @whole
        lda #0
        ldx #1
        jsr put_a
        jmp @fits
@whole: jsr pos_bytes               ; the CRC of the bytes
        jsr bits_crc
        lda crc
        sta zp_pw_value
        lda crc + 1
        sta zp_pw_value + 1
        lda #16
        jsr put
@five:  lda pw_pos                  ; zero bits to a symbol: pw_pos a multiple of 5
        sta zp_t0
        lda pw_pos + 1
        sta zp_t1
@mod5:  lda zp_t1                   ; (take 5s away; 2048 bits at most: quick enough)
        bne @take
        lda zp_t0
        cmp #5
        bcc @rest
@take:  lda zp_t0
        sec
        sbc #5
        sta zp_t0
        bcs @mod5
        dec zp_t1
        jmp @mod5
@rest:  lda zp_t0
        beq @text
        lda #0
        ldx #1
        jsr put_a
        jmp @five
@text:  lda zp_t2
        ldx zp_t3
        jsr pw_write
        lda #PW_OK
        rts

; write_slots: an item list's filled slots, of the 8 at `traveler` + Y: how many (3 bits),
; then each slot (3) and item (10). Changes A, X, Y; zp_t0, zp_t1, zp_t2 (kept: it's
; passport_encode's).
write_slots:
        lda zp_t2
        pha
        sty zp_t1
        ldx #0                      ; how many
        lda #0
        sta zp_t0
@count: lda traveler + 1, y
        cmp #EMPTY_SLOT
        beq @empty
        inc zp_t0
@empty: iny
        iny
        inx
        cpx #8
        bne @count
        lda zp_t0
        ldx #3
        jsr put_a
        lda #0
        sta zp_t0                   ; the slot
@slot:  lda zp_t0
        asl a
        clc
        adc zp_t1
        tay
        lda traveler + 1, y
        cmp #EMPTY_SLOT
        beq @next
        sta zp_pw_value + 1
        lda traveler, y
        sta zp_pw_value
        lda zp_t0
        ldx #3
        jsr put_a_keep              ; (keeps zp_pw_value's item for next)
        lda #10
        jsr put
@next:  inc zp_t0
        lda zp_t0
        cmp #8
        bne @slot
        pla
        sta zp_t2
        rts

; put_a: A as X bits. put: zp_pw_value as A bits. A value that doesn't fit sets too_big.
; put_a_keep: as put_a, but zp_pw_value kept as it was. Change A, X, Y.
put_a_keep:
        ldy zp_pw_value
        sty keep
        ldy zp_pw_value + 1
        sty keep + 1
        jsr put_a
        lda keep
        sta zp_pw_value
        lda keep + 1
        sta zp_pw_value + 1
        rts
put_a:
        sta zp_pw_value
        lda #0
        sta zp_pw_value + 1
        txa
put:
        jsr bits_put
        bcc @fits
        inc too_big
@fits:  rts

; The fixed fields after the name: (bits, place in `traveler`), to a 0. Over 8 bits, the
; value's high byte is the next place.
; What a Passport may hold (docs/passport-spec.md).
SKILLS_MAX      = 12
POWERS_MAX      = 8
ITEMS_MAX       = 6
ECHOES_MAX      = 8
LEVEL_TOP       = 100
XP_PER_LEVEL    = 100
RATING_TOP      = 100

fixed_fields:
        .byte 5, CH_RACE, 4, CH_CLASS, 7, CH_LEVEL, 7, CH_XP
        .byte 7, CH_STATS, 7, CH_STATS + 1, 7, CH_STATS + 2
        .byte 7, CH_STATS + 3, 7, CH_STATS + 4, 7, CH_STATS + 5
        .byte 8, CH_STAT_POINTS, 8, CH_SKILL_POINTS, 16, CH_DEBT, 7, CH_FLAGS
        .byte 12, CH_TAGS
        .byte 0

; A pass's own fields: (bits, place in `pass`), to a 0. The ticket's 32 are two 16s.
pass_fields:
        .byte 16, PASS_DEPARTURE, 16, PASS_TICKET + 2, 16, PASS_TICKET, 16, PASS_SEED
        .byte 1, PASS_REWIND
        .byte 0

; The name alphabet: a letter's value is its place.
name_alphabet:
        .byte " ABCDEFGHIJKLMNOPQRSTUVWXYZ-'.!?"

        .segment "BSS"
traveler:       .res CH_SIZE
pass:           .res PASS_SIZE + 1  ; (+1: the Rewind bit is put as a 16-bit value's low)
password_kind:  .res 1
too_big:        .res 1
get_x:          .res 1
refused:        .res 1              ; read_traveler: a character no game has
most:           .res 1
keep:           .res 2
pos8:           .res 2
