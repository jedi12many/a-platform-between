; The assets, from the cartridge or the disk (docs/cartridge.md, "Assets"): the one
; module that knows which the game came on.
;
; Everything the game has besides the resident engine (fonts, tiles, pictures, sprites,
; the story's chapters, code for one moment) is in assets of 8 KB, numbered from 0. The
; game asks for one with asset_fetch, and it's staged in RAM at $8000-$9FFF, where the
; game reads it (or copies it on, copy.s).
;
;   On the cartridge, asset n is bank 1 + n/2's ROML (n even) or ROMH (n odd), copied to
;   the staging RAM with the cartridge in: $8000-$BFFF reads the ROM, a write goes to the
;   RAM under it. Interrupts stay on.
;   On a disk (an SD2IEC, a 1541), asset n is the file "ANN" (NN in hex), loaded there
;   with the KERNAL from the device the game was loaded from.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export asset_fetch, asset_media, media, staged

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; asset_media: say what the game came on (the start-ups do, once).
;   Takes:   A = MEDIA_CART or MEDIA_DISK; X = the disk's device (disks only).
;   After:   no asset staged.
;   Changes: A.
asset_media:
        sta media
        stx device
        lda #$FF
        sta staged
        rts

; ----------------------------------------------------------------------------------------
; asset_fetch: an asset into the staging RAM, $8000-$9FFF, unless it's there already.
;   Takes:   A = the asset, 0-125.
;   Before:  $01 = $35 (the game's).
;   After:   C clear: it's staged (and `staged` says which); C set: it couldn't be had
;            (a disk error), and nothing is staged. $01 = $35, the bank as it was.
;   Changes: A, X, Y; zp_src, zp_dst; on a disk, the KERNAL's zero page ($90-$FF).
asset_fetch:
        cmp staged
        bne @get
        clc
        rts
@get:   ldx media
        beq @cart
        jmp disk_fetch
@cart:  tay                         ; Y = the asset
        sta staged
        lda #0
        sta zp_src
        sta zp_dst
        lda #>STAGING
        sta zp_dst + 1
        tya                         ; ROML ($8000) or ROMH ($A000)
        and #1
        beq @low
        lda #$A0
        bne @chip                   ; (always)
@low:   lda #$80
@chip:  sta zp_src + 1
        lda ef_bank
        pha
        tya                         ; the bank: 1 + asset / 2
        lsr a
        clc
        adc #1
        sta ef_bank
        sta EF_BANK
        lda #PORT_CART
        sta CPU_PORT
        ldx #STAGING_PAGES
        ldy #0
@copy:  lda (zp_src), y
        sta (zp_dst), y
        iny
        bne @copy
        inc zp_src + 1
        inc zp_dst + 1
        dex
        bne @copy
        lda #PORT_GAME
        sta CPU_PORT
        pla
        sta ef_bank
        sta EF_BANK
        clc
        rts

; disk_fetch: asset_fetch's disk half. A = the asset; as asset_fetch.
disk_fetch:
        tay
        lsr a                       ; its name: "A", then two hex digits
        lsr a
        lsr a
        lsr a
        tax
        lda hex, x
        sta name + 1
        tya
        and #$0F
        tax
        lda hex, x
        sta name + 2
        lda #$FF
        sta staged
        tya
        pha
        lda #PORT_KERNAL
        sta CPU_PORT
        lda #3
        ldx #<name
        ldy #>name
        jsr KERNAL_SETNAM
        lda #1                      ; logical file 1, our device, secondary address 0:
        ldx device                  ; load where we say
        ldy #0
        jsr KERNAL_SETLFS
        lda #0                      ; load (not verify)
        ldx #<STAGING
        ldy #>STAGING
        jsr KERNAL_LOAD             ; C set: an error
        lda #PORT_GAME
        sta CPU_PORT
        pla
        bcs @failed
        sta staged
        rts                         ; (C clear)
@failed:
        rts                         ; (C set; nothing staged)

hex:    .byte "0123456789ABCDEF"
name:   .byte "A00"

        .segment "BSS"
media:  .res 1                      ; MEDIA_CART or MEDIA_DISK
device: .res 1                      ; the disk's device
staged: .res 1                      ; the asset staged, or $FF
