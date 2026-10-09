; The music on the C64 (docs/music.md): the main program's way in to the player
; (fe/c64/music.s), whose tunes and state are under the I/O, at $D800-$DFFF.
;
; The disk's MUSIC file (tools/music/musicc.py --c64) loads at $E000: the tune file's
; length (2 bytes), the tune file padded to 1536 bytes, then the player's note table and
; the sound effects. tune_install copies it under the I/O, after the length, and starts
; the player. Each call into the player is made with interrupts off and only RAM switched
; in ($01 = $34); the raster interrupts (fe/c64/split.s, and sprites.s in a fight) call
; tune_tick once a frame, which plays a frame and copies the registers to the SID.

        .export _tune_install, _tune_start, _tune_change, _tune_effect, _tune_find
        .export _tune_playing, _tune_silence, tune_tick
        .import music_init, music_frame, music_command, music_find, music_playing
        .import music_ghost

LOADED  = $E000                 ; where MUSIC loads
DATA    = $D800
PAGES   = 7                     ; $D800-$DEEF: tunes, notes, effects
STATE   = $DEF0                 ; the player's state, after them
SID     = $D400

        .segment "BSS"

ready:  .res 1                  ; 1 once the player has its tunes
zp:     .res 6                  ; the zero page it uses, kept for whoever it interrupted
port:   .res 1
flags:  .res 1

        .segment "CODE"

; Banking: with interrupts off, everything but RAM out. A is kept.
bank_in:
        pha
        php
        pla
        sta flags               ; the caller's interrupt flag, for bank_out
        pla
        sei
        ldy $01
        sty port
        ldy #$34
        sty $01
        rts
bank_out:
        ldy port
        sty $01
        pha
        lda flags
        pha
        plp                     ; interrupts as they were
        pla
        rts

; The MUSIC file, loaded at $E000, under the I/O; then the player starts.
_tune_install:
        jsr bank_in
        lda #<LOADED + 2
        sta $FB
        lda #>LOADED
        sta $FC
        lda #<DATA
        sta $FD
        lda #>DATA
        sta $FE
        ldx #PAGES
        ldy #0
@copy:  lda ($FB), y
        sta ($FD), y
        iny
        cpx #1
        bne @page
        cpy #<STATE             ; the last page only up to the player's state
        beq @done
@page:  cpy #0
        bne @copy
        inc $FC
        inc $FE
        dex
        bne @copy
@done:
        lda LOADED
        ldx LOADED + 1
        jsr music_init
        lda #1
        sta ready
        jmp bank_out

; Commands, for the next frame: start a tune (A), change to it (fade, then start; 255
; fades out), play sound effect A on voice 3.
_tune_start:
        ldy #1
        bne command             ; always
_tune_change:
        ldy #2
        bne command
_tune_effect:
        ldy #3
command:
        tax
        lda ready
        beq @no
        tya
        jsr bank_in
        jsr music_command
        jmp bank_out
@no:    rts

; A tune's number by its name (A/X, ASCII, 0-terminated): 255 if there's none.
_tune_find:
        ldy ready
        beq none
        jsr bank_in
        jsr music_find
        jsr bank_out
        ldx #0
        rts
none:   lda #255
        ldx #0
        rts

; 1 while a tune has a voice playing.
_tune_playing:
        lda ready
        beq @no
        jsr bank_in
        jsr music_playing
        jsr bank_out
@no:    ldx #0
        rts

; The music off for good, and the SID quiet: before the program ends.
_tune_silence:
        sei
        lda #0
        sta ready
        ldx #24
@clear: sta SID, x
        dex
        bpl @clear
        cli
        rts

; A frame of music, from a raster interrupt (so interrupts are off): the registers to
; the SID. The I/O is in when it's called; the zero page the player uses is put back.
tune_tick:
        lda ready
        beq @no
        ldx #3
@keep:  lda $FB, x
        sta zp, x
        dex
        bpl @keep
        lda $22
        sta zp + 4
        lda $23
        sta zp + 5
        lda $01
        pha
        lda #$34
        sta $01
        jsr music_frame
        pla
        sta $01
        ldx #24
@sid:   lda music_ghost, x
        sta SID, x
        dex
        bpl @sid
        ldx #3
@back:  lda zp, x
        sta $FB, x
        dex
        bpl @back
        lda zp + 4
        sta $22
        lda zp + 5
        sta $23
@no:    rts
