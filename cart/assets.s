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
;
; And on a disk, the player's Boarding Pass may be beside the game, as the file PASS
; (pass_file).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export asset_fetch, asset_media, media, staged, pass_file

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

; ----------------------------------------------------------------------------------------
; pass_file: the file PASS from the game's disk, as text (docs/passport-spec.md,
; "Carriers"): read a byte at a time (never LOADed: a long file would run on past the
; buffer), at most Y bytes. Printable ASCII is kept, PETSCII's capitals ($C1-$DA) become
; ASCII's; anything else (a load address, a control byte) a space, which the decoder
; ignores.
;   Takes:   A/X = where the text goes (low/high); Y = the most it may have (1-255).
;   Before:  $01 = $35.
;   After:   C clear: the text there, ending in 0 (maybe nothing but spaces); or C set: no
;            file (a cartridge, no disk, no PASS, a drive error). $01 = $35.
;   Changes: A, X, Y; zp_dst; on a disk, the KERNAL's zero page ($90-$FF).
pass_file:
        sta zp_dst
        stx zp_dst + 1
        sty file_room
        lda media
        bne @disk
        sec
        rts
@disk:  lda #PORT_KERNAL
        sta CPU_PORT
        lda #PASS_NAME_LEN
        ldx #<pass_name
        ldy #>pass_name
        jsr KERNAL_SETNAM
        lda #PASS_FILE              ; logical file 2, our device, a data channel
        ldx device
        ldy #PASS_FILE
        jsr KERNAL_SETLFS
        jsr KERNAL_OPEN
        bcs @none
        ldx #PASS_FILE
        jsr KERNAL_CHKIN
        bcs @close
        ldy #0
        sty file_len
@byte:  jsr KERNAL_CHRIN
        sta file_byte
        jsr KERNAL_READST
        sta file_status
        and #%10111111              ; anything but the end of the file: an error (no
        bne @close                  ; file there): as if there were none
        lda file_byte
        cmp #$C1                    ; PETSCII capitals
        bcc @ascii
        cmp #$DB
        bcs @space
        and #%01111111
        bne @put                    ; (always)
@ascii: cmp #$20                    ; printable ASCII, else a space
        bcc @space
        cmp #$7F
        bcc @put
@space: lda #' '
@put:   ldy file_len
        cpy file_room
        bcs @full
        sta (zp_dst), y
        inc file_len
@full:  lda file_status             ; to the end of the file
        beq @byte
        jsr finish
        ldy file_len
        lda #0
        sta (zp_dst), y
        clc
        rts
@close: jsr finish
@none:  lda #PORT_GAME
        sta CPU_PORT
        sec
        rts

; finish: the file closed, the keyboard and screen the KERNAL's channels again, $01 the
; game's. Changes A, X, Y.
finish: jsr KERNAL_CLRCHN
        lda #PASS_FILE
        jsr KERNAL_CLOSE
        lda #PORT_GAME
        sta CPU_PORT
        rts

PASS_FILE       = 2
PASS_NAME_LEN   = 8
pass_name:      .byte "PASS,P,R"

hex:    .byte "0123456789ABCDEF"
name:   .byte "A00"

        .segment "BSS"
media:  .res 1                      ; MEDIA_CART or MEDIA_DISK
device: .res 1                      ; the disk's device
staged: .res 1                      ; the asset staged, or $FF
file_room:      .res 1              ; pass_file: room for the text
file_len:       .res 1              ; how much there is
file_status:    .res 1              ; the KERNAL's status after the last byte
file_byte:      .res 1
