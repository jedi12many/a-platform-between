; The keyboard (docs/cartridge.md, "Keys"): read by the game itself, once a frame from the
; raster interrupt, not by the KERNAL. Each key newly down goes into a buffer of 8, as
; ASCII (letters small, capitals with SHIFT), or one of the KEY_ codes in mem.inc for
; RETURN, DEL, RUN/STOP and the cursor keys; SHIFT, CTRL, C= and the function keys give
; nothing yet. The game takes them with key_get.
;
; A joystick in port 2 is read first, on port A itself (with no row selected): its
; directions as the cursor keys (and KEY_ codes for the diagonals), repeating while it's
; held (after a quarter of a second, then twelve a second), and its button as RETURN.
; While it's pushed the matrix isn't read: it pulls port A's lines low, which would read
; as keys.
;
; The matrix: a 0 written to bit r of CIA 1's port A ($DC00) selects row r; a 0 read in
; bit c of its port B ($DC01) is the key at row r, column c down. A joystick in port 1
; reads like keys (it shares port B).

        .include "hw.inc"
        .include "mem.inc"

        .export keys_scan, key_get, keys_clear

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; keys_scan: the matrix read, new keys into the buffer.
;   Before:  the I/O in; called from the interrupt (key_get is the only other user of
;            the buffer, and only moves its head).
;   Changes: A, X, Y. No zero page.
keys_scan:
        lda #$FF                    ; the joystick: 1 for each line pulled low
        sta CIA1_PRA
        lda CIA1_PRA
        eor #$FF
        and #%00011111
        beq @free
        jmp stick_read
@free:  sta stick_was
        ldx #7
@row:   lda select, x
        sta CIA1_PRA
        lda CIA1_PRB
        eor #$FF                    ; 1: down
        sta down, x
        dex
        bpl @row
        lda #$FF                    ; no row selected
        sta CIA1_PRA
        lda down + 1                ; SHIFT: left (row 1, column 7) or right (row 6, 4)
        and #%10000000
        sta shift
        lda down + 6
        and #%00010000
        ora shift
        sta shift
        ldx #7
@new:   lda was, x                  ; down now, not before
        eor #$FF
        and down, x
        beq @none
        sta bits
        txa                         ; the key's number: row x 8 + column
        asl a
        asl a
        asl a
        sta code
@bit:   lsr bits
        bcc @next
        ldy code
        lda shift
        beq @plain
        lda keymap_shift, y
        jmp @got
@plain: lda keymap, y
@got:   beq @next                   ; (a key that gives nothing)
        jsr push
@next:  inc code
        lda bits
        bne @bit
@none:  lda down, x
        sta was, x
        dex
        bpl @new
        rts

; push: key A into the buffer, unless it's full. Changes A, Y.
push:   ldy tail
        sta buffer, y
        iny
        tya
        and #7
        cmp head
        beq @full
        sta tail
@full:  rts

; stick_read: the joystick (A: its lines, 1 pushed; not 0): a new push, or one held long
; enough to repeat, into the buffer. Changes A, Y.
stick_read:
        cmp stick_was
        beq @held
        sta stick_was
        ldy #REPEAT_FIRST
        sty stick_wait
        and #STICK_FIRE
        beq @aim
        lda #KEY_RETURN
        jmp push
@aim:   ldy stick_was
        lda stick_keys, y
        beq @done
        jmp push
@held:  and #STICK_FIRE             ; the button doesn't repeat
        bne @done
        dec stick_wait
        bne @done
        ldy #REPEAT_NEXT
        sty stick_wait
        ldy stick_was
        lda stick_keys, y
        beq @done
        jmp push
@done:  rts

; ----------------------------------------------------------------------------------------
; key_get: the next key from the buffer, if there is one.
;   After:   A = the key (ASCII or a KEY_ code), Z clear; or A = 0, Z set: none.
;   Changes: A, X.
key_get:
        ldx head
        cpx tail
        beq @none
        lda buffer, x
        pha
        inx
        txa
        and #7
        sta head
        pla
        rts
@none:  lda #0
        rts

; ----------------------------------------------------------------------------------------
; keys_clear: the buffer emptied (keys pressed before a question aren't its answer).
;   Changes: A.
keys_clear:
        lda tail
        sta head
        rts

select: .byte $FE, $FD, $FB, $F7, $EF, $DF, $BF, $7F

STICK_FIRE      = %00010000
REPEAT_FIRST    = 15                ; frames
REPEAT_NEXT     = 5

; The joystick's directions (bits 0-3: up, down, left, right) as keys.
stick_keys:
        .byte 0, KEY_UP, KEY_DOWN, 0, KEY_LEFT, KEY_UP_LEFT, KEY_DOWN_LEFT, 0
        .byte KEY_RIGHT, KEY_UP_RIGHT, KEY_DOWN_RIGHT, 0, 0, 0, 0, 0

; The matrix, row by row (port A's bit), each row's eight columns (port B's bit 0-7).
keymap:
        .byte KEY_DELETE, KEY_RETURN, KEY_RIGHT, 0, 0, 0, 0, KEY_DOWN   ; DEL RET CRSR-LR F7 F1 F3 F5 CRSR-UD
        .byte "3wa4zse", 0                                              ; ... LSHIFT
        .byte "5rd6cftx"
        .byte "7yg8bhuv"
        .byte "9ij0mkon"
        .byte "+pl-.:@,"
        .byte 0, "*;", 0, 0, "=^/"                                      ; POUND * ; HOME RSHIFT = ^ /
        .byte "1", 0, 0, "2 ", 0, "q", KEY_STOP                         ; 1 <- CTRL 2 SPACE C= Q STOP
keymap_shift:
        .byte 0, KEY_RETURN, KEY_LEFT, 0, 0, 0, 0, KEY_UP
        .byte "#WA$ZSE", 0
        .byte "%RD&CFTX"
        .byte "'YG(BHUV"
        .byte ")IJ0MKON"
        .byte "+PL->[@<"
        .byte 0, "*]", 0, 0, "=^?"
        .byte "!", 0, 0, $22, " ", 0, "Q", KEY_STOP

        .segment "BSS"
down:   .res 8                      ; the matrix now (1: down)
was:    .res 8                      ; and at the last scan
shift:  .res 1
bits:   .res 1
code:   .res 1
buffer: .res 8
stick_was:      .res 1              ; the joystick at the last scan
stick_wait:     .res 1              ; frames till it repeats
head:   .res 1                      ; the next key to take
tail:   .res 1                      ; where the next key goes
