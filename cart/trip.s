; Trip codes (docs/boarding.md, "Trip code format"; the Python reference is
; tools/passport/trip.py): a trip saved at a menu, as a password, where there's nowhere
; else to save it. Only what the trip has changed since boarding: the story's flags and
; vars, the dice, the tune, health, the rewards paid and the receipt so far; tied to the
; image and to what the trip boarded with. Code in asset 1, with the desk and the trip's
; end: vm.s stages it to save, and play.s has it staged from the desk to pick a trip up.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"
        .include "receipt.inc"

        .export trip_show, trip_decode, trip_apply, boarded, trip_scene
        .import bits_clear, bits_put, bits_get, bits_crc, pw_read, pw_close, pw_pos, pw_len
        .import crc, log_print, qr_make, qr_show, pw_trip
        .import flags, vars, health, music_now, vsp, yard
        .import flag_count, var_count, scene_count, scene_now, music_count
        .import rng, rng_seed, gain_xp, traveler, receipt, set_debt
        .import paid_count, paid_lo, paid_hi, paid_car, gives, item_in, item_out, echo_put

CODE_AT         = CAR_AT + 9        ; a car's code: a reward's place is its offset in it
HASH_AT         = DEPOT_AT + 18     ; the image's hash, in the depot's header
PAID_MAX        = 32
NO_TUNE         = 63
BITS_MOST       = 1192              ; fields at most: 255 symbols, the CRC and padding too
LINE            = 20
QR_MOST         = 114               ; the QR code holds this many symbols (qr.s)

        .segment "ENDING"

; ----------------------------------------------------------------------------------------
; trip_show: the trip as it is, at a menu, as a trip code: "Saved." and how to pick it up,
; the code's lines into the story log, and its QR code into the view (if it fits one).
;   Before:  the VM waits at a menu; $01 = $35.
;   After:   C clear; or C set: it can't be saved here (said).
;   Changes: A, X, Y; password.s's zero page; zp_qr; zp_t0-zp_t3.
trip_show:
        jsr trip_make
        bcc @made
        lda #<cant
        ldx #>cant
        jsr log_print
        sec
        rts
@made:  lda #<saved
        ldx #>saved
        jsr log_print
        lda #0                      ; its lines, 20 symbols each
        sta symbol_count            ; (also where the next line starts: log_print uses
@line:  ldx symbol_count            ; zp_t0-zp_t2)
        ldy #0
@symbol:
        lda code_text, x
        beq @end
        sta line_buf, y
        inx
        iny
        cpy #LINE
        bne @symbol
@end:   stx symbol_count
        tya
        beq @lined                  ; (nothing left)
        lda #10
        sta line_buf, y
        lda #0
        sta line_buf + 1, y
        lda #<line_buf
        ldx #>line_buf
        jsr log_print
        jmp @line
@lined: lda symbol_count            ; and its QR code, if it fits one
        cmp #QR_MOST + 1
        bcs @done
        lda #<code_text
        ldx #>code_text
        jsr qr_make
        bcs @done
        jsr qr_show
@done:  clc
        rts

; ----------------------------------------------------------------------------------------
; trip_make: the trip code, into code_text.
;   After:   C clear; or C set: nothing on the stack is the rule, or a field doesn't fit,
;            or the code would be over 255 symbols.
;   Changes: A, X, Y; password.s's zero page; zp_t0-zp_t3.
trip_make:
        lda vsp                     ; a save is made with nothing on the stack
        beq @empty
        sec
        rts
@empty: lda #0
        sta too_big
        jsr bits_clear
        lda #KIND_TRIP
        ldx #0
        ldy #4
        jsr put
        lda boarded
        ldx boarded + 1
        jsr put16
        lda HASH_AT
        ldx HASH_AT + 1
        jsr put16
        lda yard
        ldx yard + 1
        jsr put16
        lda scene_now
        ldx scene_now + 1
        ldy #12
        jsr put
        lda #0                      ; the flags, flag 0 first: byte n / 8, bit n mod 8
        sta zp_t0
        sta zp_t1
@flag:  lda zp_t0
        cmp flag_count
        lda zp_t1
        sbc flag_count + 1
        bcs @vars
        jsr flag_at
        and flags, y
        beq @put_flag
        lda #1
@put_flag:
        ldx #0
        ldy #1
        jsr put
        inc zp_t0
        bne @flag
        inc zp_t1
        bne @flag                   ; (always)
@vars:  lda #0
        sta zp_t0
@var:   lda zp_t0
        cmp var_count
        bcs @dice
        tax
        lda vars, x
        ldx #0
        ldy #8
        jsr put
        inc zp_t0
        bne @var                    ; (always)
@dice:  lda rng
        ldx rng + 1
        jsr put16
        lda music_now               ; $FF (none) as 63
        cmp #$FF
        bne @tune
        lda #NO_TUNE
@tune:  ldx #0
        ldy #6
        jsr put
        lda health
        ldx #0
        ldy #8
        jsr put
        lda gives
        ldx #0
        ldy #2
        jsr put
        lda traveler + CH_DEBT
        ldx traveler + CH_DEBT + 1
        jsr put16
        lda paid_count              ; the rewards paid: car, offset in its code
        ldx #0
        ldy #6
        jsr put
        lda #0
        sta zp_t0
@paid:  lda zp_t0
        cmp paid_count
        bcs @xp
        tax
        lda paid_car, x
        ldx #0
        ldy #6
        jsr put
        ldx zp_t0
        lda paid_lo, x
        sec
        sbc #<CODE_AT
        pha
        lda paid_hi, x
        sbc #>CODE_AT
        tax
        pla
        ldy #13
        jsr put
        inc zp_t0
        bne @paid                   ; (always)
@xp:    lda receipt + R_XP
        ldx receipt + R_XP + 1
        jsr put16
        ldx #R_GAINED
        jsr put_items
        ldx #R_LOST
        jsr put_items
        lda receipt + R_ECHOES      ; the Echoes: id, state, state at boarding
        ldx #0
        ldy #4
        jsr put
        lda #0
        sta zp_t3
@echo:  lda zp_t3
        cmp receipt + R_ECHOES
        bcs @close
        asl a
        asl a
        sta zp_t2
        tax
        lda receipt + R_ECHOES + 1, x
        pha
        lda receipt + R_ECHOES + 2, x
        tax
        pla
        ldy #10
        jsr put
        ldx zp_t2
        lda receipt + R_ECHOES + 3, x
        ldx #0
        ldy #2
        jsr put
        ldx zp_t2
        lda receipt + R_ECHOES + 4, x
        ldx #0
        ldy #2
        jsr put
        inc zp_t3
        jmp @echo
@close: lda too_big
        bne @no
        lda pw_pos                  ; room for it all in 255 symbols?
        cmp #<(BITS_MOST + 1)
        lda pw_pos + 1
        sbc #>(BITS_MOST + 1)
        bcs @no
        lda #<code_text
        ldx #>code_text
        jsr pw_close
        clc
        rts
@no:    sec
        rts

; put_items: the receipt's list at receipt + X: its count (4 bits), then each id (10).
; Changes A, X, Y; zp_t2, zp_t3.
put_items:
        stx zp_t2
        lda receipt, x
        sta zp_t3
        ldx #0
        ldy #4
        jsr put
@item:  lda zp_t3
        beq @done
        dec zp_t3
        ldx zp_t2
        lda receipt + 1, x
        pha
        lda receipt + 2, x
        tax
        pla
        ldy #10
        jsr put
        inc zp_t2
        inc zp_t2
        jmp @item
@done:  rts

; put16: A/X as 16 bits. put: A/X (low/high) as Y bits (too_big set if it doesn't fit).
; Changes A, X, Y; zp_pw_value, zp_pw_n.
put16:  ldy #16
put:    sta zp_pw_value
        stx zp_pw_value + 1
        tya
        jsr bits_put
        bcc @fits
        inc too_big
@fits:  rts

; flag_at: flag zp_t0/zp_t1's place: Y = its byte, A = its bit. Changes A, X, Y.
flag_at:
        lda zp_t1
        lsr a
        lda zp_t0
        ror a
        lsr a
        lsr a
        tay
        lda zp_t0
        and #7
        tax
        lda bit_of, x
        rts

; ----------------------------------------------------------------------------------------
; trip_decode: a typed trip code, read into the trip's state as the code says: the flags,
; vars, seed (yard), dice (trip_dice), tune, health, gives, rewards paid, and the receipt's
; XP, items and Echoes; the scene into trip_scene, the Debt into trip_debt. Refused as the
; reference refuses (docs/passport-spec.md, "What's refused").
;   Takes:   A/X = the text (low/high), ASCII, ending in 0.
;   Before:  the depot is open; `boarded` is what boarded the trip (the desk sets it).
;   After:   A = PW_OK, Z set; or a PW_ code, Z clear (PW_LINE: pw_bad_line), and
;            PW_OTHER_IMAGE, PW_OTHER_PASS for a code that isn't this trip's. What it read
;            is in the trip's state either way: vm_board starts it again.
;   Changes: A, X, Y; password.s's zero page; zp_t0-zp_t3.
trip_decode:
        ldy #1                      ; (a trip code's longest: 255 symbols)
        sty pw_trip
        jsr pw_read
        ldy #0
        sty pw_trip
        cmp #PW_OK
        beq @read
        rts
@read:  tsx                         ; (where to come back to if it's refused part way)
        stx bail_sp
        lda #4
        jsr need
        cmp #KIND_TRIP
        beq @kind
        lda #PW_VERSION
        rts
@kind:  jsr need16
        sta trip_boarded
        stx trip_boarded + 1
        jsr need16
        sta trip_image
        stx trip_image + 1
        jsr need16
        sta yard
        stx yard + 1
        lda #12
        jsr need
        sta trip_scene
        stx trip_scene + 1
        ldx #63                     ; the flags: clear, then each as the code has it
        lda #0
@clear: sta flags, x
        dex
        bpl @clear
        sta zp_t0
        sta zp_t1
@flag:  lda zp_t0
        cmp flag_count
        lda zp_t1
        sbc flag_count + 1
        bcs @vars
        lda #1
        jsr need
        beq @next_flag
        jsr flag_at
        ora flags, y
        sta flags, y
@next_flag:
        inc zp_t0
        bne @flag
        inc zp_t1
        bne @flag                   ; (always)
@vars:  lda #0
        sta zp_t0
@var:   lda zp_t0
        cmp var_count
        bcs @dice
        lda #8
        jsr need
        ldx zp_t0
        sta vars, x
        inc zp_t0
        bne @var                    ; (always)
@dice:  jsr need16
        sta trip_dice
        stx trip_dice + 1
        lda #6
        jsr need
        cmp #NO_TUNE
        bne @tune
        lda #$FF
@tune:  sta music_now
        lda #8
        jsr need
        sta health
        lda #2
        jsr need
        sta gives
        jsr need16
        sta trip_debt
        stx trip_debt + 1
        lda #6                      ; the rewards paid
        jsr need
        cmp #PAID_MAX + 1
        bcc @paid_fit
        jmp wrong
@paid_fit:
        sta paid_count
        lda #0
        sta zp_t0
@paid:  lda zp_t0
        cmp paid_count
        bcs @xp
        lda #6
        jsr need
        ldy zp_t0
        sta paid_car, y
        lda #13
        jsr need
        clc                         ; (13 bits: no carry out of the high byte)
        adc #<CODE_AT
        ldy zp_t0
        sta paid_lo, y
        txa
        adc #>CODE_AT
        sta paid_hi, y
        inc zp_t0
        bne @paid                   ; (always)
@xp:    jsr need16
        sta receipt + R_XP
        stx receipt + R_XP + 1
        ldx #R_GAINED
        jsr need_items
        ldx #R_LOST
        jsr need_items
        lda #4                      ; the Echoes
        jsr need
        cmp #RECEIPT_MAX + 1
        bcc @echoes_fit
        jmp wrong
@echoes_fit:
        sta receipt + R_ECHOES
        lda #0
        sta zp_t3
@echo:  lda zp_t3
        cmp receipt + R_ECHOES
        bcs closing
        asl a
        asl a
        sta zp_t2
        lda #10
        jsr need
        ldy zp_t2
        sta receipt + R_ECHOES + 1, y
        txa
        sta receipt + R_ECHOES + 2, y
        lda #2
        jsr need
        ldy zp_t2
        sta receipt + R_ECHOES + 3, y
        lda #2
        jsr need
        ldy zp_t2
        sta receipt + R_ECHOES + 4, y
        inc zp_t3
        bne @echo                   ; (always)

; The end of a code: zero bits to a byte, the CRC of every byte so far, and nothing after
; but fewer than 5 zero bits; then what's checked against the image and the pass.
closing:
@pad:   lda pw_pos
        and #7
        beq @padded
        lda #1
        jsr need
        beq @pad
        jmp wrong
@padded:
        lda pw_pos + 1              ; the bytes so far: pw_pos / 8
        sta zp_t1
        lda pw_pos
        lsr zp_t1
        ror a
        lsr zp_t1
        ror a
        lsr zp_t1
        ror a
        pha
        jsr need16
        pla
        jsr bits_crc
        lda crc
        cmp zp_pw_value
        bne wrong
        lda crc + 1
        cmp zp_pw_value + 1
        bne wrong
        lda pw_len                  ; what's left: fewer than 5 bits, all 0
        sec
        sbc pw_pos
        tax
        lda pw_len + 1
        sbc pw_pos + 1
        bne short
        cpx #5
        bcs short
        txa
        beq @fits
        jsr need
        bne wrong
@fits:  lda trip_image              ; this image's?
        cmp HASH_AT
        bne @image
        lda trip_image + 1
        cmp HASH_AT + 1
        bne @image
        lda trip_boarded            ; this pass's?
        cmp boarded
        bne @pass
        lda trip_boarded + 1
        cmp boarded + 1
        bne @pass
        lda trip_scene              ; a scene and a tune the image has; dice not 0
        cmp scene_count
        lda trip_scene + 1
        sbc scene_count + 1
        bcs wrong
        lda trip_dice
        ora trip_dice + 1
        beq wrong
        lda music_now
        cmp #$FF
        beq @ok
        cmp music_count
        bcs wrong
@ok:    lda #PW_OK
        rts
@image: lda #PW_OTHER_IMAGE
        rts
@pass:  lda #PW_OTHER_PASS
        rts

; short, wrong: trip_decode refused, from wherever it had got to: PW_LENGTH (the bits ran
; out, or too many are left), PW_CHECKSUM. After: A, Z clear.
short:  lda #PW_LENGTH
        bne bail                    ; (always)
wrong:  lda #PW_CHECKSUM
bail:   ldx bail_sp
        txs
        cmp #0
        rts

; need16: the next 16 bits. need: the next A bits. After: A/X = them (low/high), and
; zp_pw_value, Z as A; if the bits run out, trip_decode is over (short). Changes A, X, Y;
; zp_pw_n.
need16: lda #16
need:   jsr bits_get
        bcs short
        ldx zp_pw_value + 1
        lda zp_pw_value
        rts

; need_items: the receipt's list at receipt + X: a count (4 bits, 8 at most: else
; trip_decode is over, wrong), then each id (10). Changes A, X, Y; zp_t2, zp_t3.
need_items:
        stx zp_t2
        lda #4
        jsr need
        cmp #RECEIPT_MAX + 1
        bcs wrong
        ldx zp_t2
        sta receipt, x
        sta zp_t3
@item:  lda zp_t3
        beq @done
        dec zp_t3
        lda #10
        jsr need
        ldy zp_t2
        sta receipt + 1, y
        txa
        sta receipt + 2, y
        inc zp_t2
        inc zp_t2
        jmp @item
@done:  rts

; ----------------------------------------------------------------------------------------
; trip_apply: the trip picked up: the code (decoded again, into the trip's state that
; vm_board has just started), the dice, and the traveler as the trip has made them: their
; Debt the code's, the receipt's items lost taken and items gained put in the pack, its
; XP gained, its Echoes set (docs/boarding.md, "Trip code format").
;   Takes:   A/X = the code's text (low/high), as the desk read it.
;   Before:  vm_board, resuming; the code read at the desk.
;   After:   trip_scene: the scene to go on in (vm_resume).
;   Changes: A, X, Y; password.s's zero page; zp_rule; zp_t0-zp_t3.
trip_apply:
        jsr trip_decode
        lda trip_dice
        ldx trip_dice + 1
        jsr rng_seed
        lda trip_debt
        ldx trip_debt + 1
        ldy #0
        jsr set_debt
        lda receipt + R_LOST        ; the items lost, out
        sta left
        ldx #R_LOST
        stx at
@lost:  dec left
        bmi @gained
        ldx at
        lda receipt + 1, x
        pha
        lda receipt + 2, x
        tax
        pla
        jsr item_out
        inc at
        inc at
        bne @lost                   ; (always)
@gained:
        lda receipt + R_GAINED      ; the items gained, in
        sta left
        ldx #R_GAINED
        stx at
@gain:  dec left
        bmi @xp
        ldx at
        lda receipt + 1, x
        pha
        lda receipt + 2, x
        tax
        pla
        jsr item_in
        inc at
        inc at
        bne @gain                   ; (always)
@xp:    lda receipt + R_XP
        sta zp_rule
        lda receipt + R_XP + 1
        sta zp_rule + 1
        jsr gain_xp
        lda receipt + R_ECHOES      ; the Echoes, as they are now
        sta left
        ldx #0
        stx at
@echo:  dec left
        bmi @done
        ldx at
        ldy receipt + R_ECHOES + 3, x
        beq @next                   ; (a state of 0: nothing to set)
        lda receipt + R_ECHOES + 1, x
        pha
        lda receipt + R_ECHOES + 2, x
        tax
        pla
        jsr echo_put
@next:  lda at
        clc
        adc #4
        sta at
        bne @echo                   ; (always: 32 at most)
@done:  rts

; ----------------------------------------------------------------------------------------
bit_of: .byte 1, 2, 4, 8, 16, 32, 64, 128

saved:  .byte "Saved. To pick this trip up again, board with the same pass, or "
        .byte "Passport, and give this code:", 10, 0
cant:   .byte "The trip can't be saved here.", 10, 0

        .segment "BSS"
boarded:        .res 2              ; the CRC-16 of what boarded the trip (the desk's)
trip_scene:     .res 2
trip_dice:      .res 2
trip_debt:      .res 2
trip_boarded:   .res 2
trip_image:     .res 2
bail_sp:        .res 1              ; trip_decode's stack pointer, to come back from a refusal
too_big:        .res 1
symbol_count:   .res 1
left:           .res 1
at:             .res 1
line_buf:       .res LINE + 2
code_text:      .res 256
