; The game (docs/cartridge.md): the Departure's depot opened, the boarding desk, the trip,
; its receipt and Travel Stamp (receipt.s); then the desk again, for the next. The view
; has the platform's map at the desk, the story's pictures on the trip, and the Travel
; Stamp's QR code at its end.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export play, platform_map
        .import vm_open, vm_board, vm_run, vm_error, dep_id, desk_run, view_map
        .import log_print, keys_clear, key_wait, frames, asset_fetch, ending

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
        bcc @trip
        jsr cant_board              ; no Departure to board: say why, and on a key try
        jsr press_key               ; again (another disk, perhaps)
        jmp @open
@trip:  lda dep_id
        ldx dep_id + 1
        jsr desk_run                ; A = 1 with a pass
        pha
        lda #<newline
        ldx #>newline
        jsr log_print
        pla
        ldx frames                  ; the seed, without a pass: the clock's
        ldy VIC_RASTER
        jsr vm_board
        bcc @run
        jsr cant_board
        jmp @trip
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
