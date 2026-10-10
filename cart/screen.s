; The screen set up (docs/cartridge.md, "The screen"): the VIC in bank 3, our font, the
; map's tiles and their characters in, from asset 0, and the colours.
;
; Asset 0 (cart/asset0.s): the font (2 KB), the map's characters (2 KB) and the tiles'
; table (96 bytes: 8 tiles of 4 characters and 4 colours, then each one's 4 characters
; with the reach dot; tools/battlegfx.py --cart16).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export screen_install, tiles
        .import asset_fetch, mem_copy

ASSET_SCREEN    = 0
A0_FONT         = STAGING
A0_CHARS        = STAGING + $0800
A0_TILES        = STAGING + $1000

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; screen_install: the VIC's bank, its colours, and asset 0's graphics where they go.
;   Before:  $01 = $35; interrupts off (the copies are long).
;   After:   C set if asset 0 couldn't be had (the border red); else C clear.
;   Changes: A, X, Y; zp_src, zp_dst, zp_len; the staging RAM.
screen_install:
        lda CIA2_DDRA               ; the VIC in bank 3 (the serial lines as they are)
        ora #%00000011
        sta CIA2_DDRA
        lda CIA2_PRA
        and #%11111100
        ora #VIC_BANK3
        sta CIA2_PRA
        lda #BLACK
        sta VIC_BORDER
        sta VIC_BACK
        lda #DARK_GREY              ; the map's shared colours (tools/battlegfx.py)
        sta VIC_MC1
        lda #GREY
        sta VIC_MC2
        lda #ASSET_SCREEN
        jsr asset_fetch
        bcc @staged
        lda #RED
        sta VIC_BORDER
        rts
@staged:
        lda #<A0_FONT               ; the font, under the I/O
        ldx #>A0_FONT
        ldy #>FONT
        jsr copy_2k
        lda #<A0_CHARS              ; the map's characters
        ldx #>A0_CHARS
        ldy #>VIEW_CHARS
        jsr copy_2k
        ldx #TILES_SIZE - 1         ; the tiles' table
@tiles: lda A0_TILES, x
        sta tiles, x
        dex
        bpl @tiles
        clc
        rts

; copy_2k: 2 KB from A/X (low/high) to page Y. Changes A, X, Y; zp_src, zp_dst, zp_len.
copy_2k:
        sta zp_src
        stx zp_src + 1
        lda #0
        sta zp_dst
        sty zp_dst + 1
        sta zp_len
        lda #$08
        sta zp_len + 1
        jmp mem_copy

        .segment "BSS"
tiles:  .res TILES_SIZE             ; 8 tiles: 4 characters, then 4 colours; then the
                                    ; marked characters, 4 a tile
