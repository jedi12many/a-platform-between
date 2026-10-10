; The game's main program (docs/cartridge.md): in RAM, from either start-up (start.s,
; diskstart.s). It clears its variables, puts the vectors in, the cartridge and the
; KERNAL out ($01 = $35), the graphics in, and the raster split on, then plays.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export main
        .import __BSS_RUN__, __BSS_SIZE__
        .import irq_ram, irq_kernal, nmi, asset_media
        .import screen_install, frames_clear, split_on, play

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; main: the game.
;   Takes:   A = MEDIA_CART or MEDIA_DISK; X = the disk's device.
;   Before:  the resident engine copied, interrupts off.
;   After:   never returns.
main:
        pha                         ; (the variables are about to be cleared)
        txa
        pha
        lda #<__BSS_RUN__
        sta zp_dst
        lda #>__BSS_RUN__
        sta zp_dst + 1
        lda #0
        tay
        ldx #>__BSS_SIZE__
        beq @part
@page:  sta (zp_dst), y
        iny
        bne @page
        inc zp_dst + 1
        dex
        bne @page
@part:  ldx #<__BSS_SIZE__
        beq @zeroed
@byte:  sta (zp_dst), y
        iny
        dex
        bne @byte
@zeroed:
        pla
        tax
        pla
        jsr asset_media
        ; The vectors: the 6502's own (the KERNAL out) and the KERNAL's (while it's in, for
        ; a load, or in a cartridge copy).
        lda #<irq_ram
        sta VEC_IRQ
        lda #>irq_ram
        sta VEC_IRQ + 1
        lda #<irq_kernal
        sta VEC_IRQ_KERNAL
        lda #>irq_kernal
        sta VEC_IRQ_KERNAL + 1
        lda #<nmi
        sta VEC_NMI
        sta VEC_NMI_KERNAL
        lda #>nmi
        sta VEC_NMI + 1
        sta VEC_NMI_KERNAL + 1
        lda #PORT_GAME              ; RAM to $FFFF but the I/O
        sta CPU_PORT
        jsr screen_install
        jsr frames_clear
        jsr split_on
        jmp play                    ; (it never returns)
