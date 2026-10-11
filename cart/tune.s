; The music (docs/cartridge.md, "Music"; docs/music.md): the game's way in to the player,
; fe/c64/music.s, the C64 version's own, assembled for the cartridge (-D MUSIC_CART). Its
; tunes, note table, sound effects and state are at MUSIC_AT, in plain RAM. The Departure's
; music asset is copied there when the depot opens (tune_install); the raster interrupt
; plays a frame of it, under the screen, and copies the registers to the SID (tune_tick).
; The story and the fights cue tunes (tune_cue) and sound effects (tune_effect) as
; client/cue.c and fe/c64/c64.c do. The interrupt uses the player too, so a call into it
; from the game is made with interrupts off, if it's short (a command is queued for the
; next frame), or else with the interrupt told to leave the player be (tune_busy): it
; skips that frame's music rather than hold up the split.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export music_open, tune_install, tune_silence, tune_tick, tune_cue, tune_effect
        .export tune_find, tune_ready, tune_ticked
        .export MUSIC_AT                ; (for tests/music/: where the tunes go)
        .import music_init, music_frame, music_command, music_find, music_playing
        .import music_ghost, ram_copy, asset_fetch, music_asset

CMD_START       = 1                 ; music_command's
CMD_CHANGE      = 2
CMD_EFFECT      = 3
NONE            = $FF
SID_REGS        = 25

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; music_open: the Departure's music, if it has any (depot.s: music_asset), fetched and
; installed; else silence.
;   Before:  vm_open has opened the depot; $01 = $35.
;   Changes: A, X, Y; zp_src, zp_dst, zp_len; assets.s's zero page; the staging RAM.
music_open:
        lda music_asset
        cmp #$FF
        beq @none
        jsr asset_fetch
        bcs @none
        jmp tune_install
@none:  jmp tune_silence

; tune_install: the staged music asset (tools/cart/departure.py: the tune file's length,
; 2 bytes, then the file padded to 1536 bytes, the note table and the sound effects)
; copied to MUSIC_AT, and the player started on it, silent till a tune is cued.
;   Before:  the asset staged; $01 = $35.
;   After:   C clear; or C set: its length is more than a tune file can be (the music
;            stays off).
;   Changes: A, X, Y; zp_src, zp_dst, zp_len.
tune_install:
        jsr tune_silence
        lda STAGING + 1             ; the length: 1536 at most
        cmp #>MUSIC_FILE_MAX
        bcc @fits
        bne @long
        lda STAGING
        cmp #<MUSIC_FILE_MAX + 1
        bcs @long
@fits:  lda #<(STAGING + 2)         ; (the interrupt plays nothing while it's copied)
        sta zp_src
        lda #>(STAGING + 2)
        sta zp_src + 1
        lda #<MUSIC_AT
        sta zp_dst
        lda #>MUSIC_AT
        sta zp_dst + 1
        lda #<MUSIC_COPY
        sta zp_len
        lda #>MUSIC_COPY
        sta zp_len + 1
        jsr ram_copy
        lda STAGING                 ; (with the player off: the interrupt plays nothing)
        ldx STAGING + 1
        jsr music_init
        lda #NONE
        sta tune_now
        lda #1
        sta tune_ready
        clc
        rts
@long:  sec
        rts

; tune_silence: the music off, and the SID quiet. Changes A, X.
tune_silence:
        php
        sei
        lda #0
        sta tune_ready
        ldx #SID_REGS - 1
@quiet: sta SID, x
        dex
        bpl @quiet
        plp
        rts

; ----------------------------------------------------------------------------------------
; tune_tick: a frame of music, from the raster interrupt (split.s, under the screen): the
; player's registers to the SID. (None while the game is in the player.) Changes A, X, Y;
; zp_music.
tune_tick:
        lda tune_ready
        beq tick_off
        lda tune_busy               ; the game is in the player: not this frame
        bne tick_off
        jsr music_frame
tune_ticked:                        ; (tests/cart/run_cart.py reads the frame's registers here)
        ldx #SID_REGS - 1
tick_sid:
        lda music_ghost, x
        sta SID, x
        dex
        bpl tick_sid
tick_off:
        rts

; ----------------------------------------------------------------------------------------
; tune_cue: tune A to play (client/cue.c's play, fe/c64/c64.c's plat_tune_cue): nothing if
; it's the one cued last; from silence, at once; else after the one playing fades. $FF
; fades out.
;   Changes: A, X, Y.
tune_cue:
        cmp tune_now
        beq @same
        sta tune_now
        ldx tune_ready
        beq @same
        php
        sei
        tax
        ldy #CMD_CHANGE
        cpx #NONE
        beq @send
        jsr music_playing
        cmp #0
        bne @send
        ldy #CMD_START
@send:  tya
        ldx tune_now
        jsr music_command
        plp
@same:  rts

; tune_effect: sound effect A (client/sfx.c's: APB_SFX_*), on the third voice. Changes A,
; X, Y.
tune_effect:
        ldx tune_ready
        beq @off
        php
        sei
        tax
        lda #CMD_EFFECT
        jsr music_command
        plp
@off:   rts

; tune_find: the tune named A/X (ASCII, ending in 0) in the Departure's music. After: A =
; it, or $FF (none, or no music). Changes A, X, Y.
tune_find:
        ldy tune_ready
        beq @none
        inc tune_busy               ; (a search takes a while: the interrupt goes on)
        jsr music_find
        dec tune_busy
        rts
@none:  lda #NONE
        rts

        .segment "BSS"
tune_ready:     .res 1              ; 1: the player has its tunes
tune_busy:      .res 1              ; not 0: the game is in the player, the interrupt keeps out
tune_now:       .res 1              ; the tune cued last ($FF: none, or silence)
