; The game (docs/cartridge.md): the Departure's depot and its music opened, the boarding
; desk, the trip (or one picked up from its trip code: trip.s), its receipt and Travel
; Stamp (receipt.s); then the desk again, for the next. The desk and the trip's end are
; asset 1's, staged between trips. The view has the platform's map at the desk, the
; story's pictures on the trip, and the Travel Stamp's QR code at its end.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export play, platform_map
        .import vm_open, vm_board, vm_run, vm_error, dep_id, desk_run, view_map
        .import log_print, keys_clear, key_wait, frames, asset_fetch, ending, music_open
        .import resuming, vm_resume, trip_apply, trip_scene, joined

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; play: trips, one after another.
;   Before:  $01 = $35; the screen set up and the split on.
;   After:   never returns.
play:
        lda #<platform_map
        ldx #>platform_map
        jsr view_map
@open:  jsr vm_open
        bcc @music
        jsr cant_board              ; no Departure to board: say why, and on a key try
        jsr press_key               ; again (another disk, perhaps)
        jmp @open
@music: jsr music_open               ; its tunes (tune.s), for every trip from here
@trip:  lda #ASSET_ENDING           ; the desk: in asset 1, with the trip's end
        jsr asset_fetch
        bcc @desk
        lda #<no_desk
        ldx #>no_desk
        jsr log_print
        jsr press_key
        jmp @trip
@desk:  lda dep_id
        ldx dep_id + 1
        jsr desk_run                ; A = 1 with a pass
        pha
        lda resuming                ; (a blank line before a new trip, as the C64 has it)
        bne @told
        lda #<newline
        ldx #>newline
        jsr log_print
@told:  pla
        ldx frames                  ; the seed, without a pass: the clock's
        ldy VIC_RASTER
        jsr vm_board
        bcc @boarded
        jsr cant_board
        jmp @trip
@boarded:
        lda resuming                ; a trip picked up: as its code says, at its menu
        beq @run
        lda #<joined                ; (asset 1 still staged: the desk's)
        ldx #>joined
        jsr trip_apply
        lda trip_scene
        ldx trip_scene + 1
        jsr vm_resume               ; (failed: vm_run says so)
@run:   jsr vm_run
        cmp #$FF
        beq @again                  ; (derailed: vm_run said so)
        lda #ASSET_ENDING           ; the end: the receipt, the Travel Stamp (receipt.s,
        jsr asset_fetch             ; run from the staging RAM)
        bcs @again
        jsr ending
@again: jsr press_key
        lda #<platform_map          ; the platform again, for the next
        ldx #>platform_map
        jsr view_map
        jmp @trip

; press_key: "(press a key)", and a key. Changes A, X, Y; text.s's zero page; zp_t0-zp_t2.
press_key:
        lda #<press
        ldx #>press
        jsr log_print
        jsr keys_clear
        jmp key_wait

; cant_board: "This Departure can't be boarded: " and why (vm_error). Changes A, X, Y;
; text.s's zero page; zp_t0-zp_t2.
cant_board:
        lda #<cant
        ldx #>cant
        jsr log_print
        lda #<vm_error
        ldx #>vm_error
        jsr log_print
        lda #<newline
        ldx #>newline
        jmp log_print

; The platform, in the view till the story has pictures: 20 x 8 tiles, row by row
; (tools/battlegfx.py: 0 floor, 1 wall, 2 pit, 3 rough, 4 cover, 5 hazard, 6 high ground,
; 7 exit).
platform_map:
        .byte 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
        .byte 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 0, 6, 1
        .byte 7, 0, 0, 4, 0, 1, 0, 0, 5, 5, 0, 0, 0, 0, 3, 0, 0, 0, 6, 1
        .byte 1, 0, 0, 4, 0, 0, 0, 0, 5, 5, 0, 2, 2, 0, 0, 0, 4, 0, 0, 1
        .byte 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 0, 0, 0, 4, 0, 0, 1
        .byte 1, 0, 3, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1
        .byte 1, 0, 3, 3, 0, 1, 0, 0, 0, 4, 0, 0, 0, 0, 5, 0, 0, 0, 0, 7
        .byte 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1

newline:        .byte 10, 0
press:          .byte "(press a key)", 10, 0
cant:           .byte "This Departure can't be boarded: ", 0
no_desk:        .byte "The boarding desk couldn't be loaded.", 10, 0
