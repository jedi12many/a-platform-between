; Copying RAM to RAM (docs/cartridge.md): an asset on from the staging RAM to where it
; lives, under the I/O too.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export mem_copy

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; mem_copy: copy zp_len bytes from zp_src to zp_dst, upwards (so a copy down onto
; itself is safe), with RAM everywhere: a destination at $D000-$DFFF reaches the RAM under
; the I/O.
;   Takes:   zp_src, zp_dst, zp_len.
;   Before:  $01 = $35.
;   After:   $01 = $35; interrupts as they were.
;   Changes: A, X, Y; zp_src, zp_dst (their high bytes move on). Interrupts are off
;            while it copies (the I/O, the raster's registers with it, is out): 2 KB
;            takes about half a frame, so copy before the split is on, or in pieces.
mem_copy:
        php
        sei
        lda #PORT_ALL_RAM
        sta CPU_PORT
        ldy #0
        ldx zp_len + 1              ; whole pages
        beq @part
@page:  lda (zp_src), y
        sta (zp_dst), y
        iny
        bne @page
        inc zp_src + 1
        inc zp_dst + 1
        dex
        bne @page
@part:  ldx zp_len                  ; then the rest
        beq @done
@byte:  lda (zp_src), y
        sta (zp_dst), y
        iny
        dex
        bne @byte
@done:  lda #PORT_GAME
        sta CPU_PORT
        plp
        rts
