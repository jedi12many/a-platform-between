; The Ultimax boot (docs/cartridge.md, "The EasyFlash").
;
; At power-on the EasyFlash is in Ultimax mode: bank 0's ROMH at $E000-$FFFF, so the
; 6502's reset vector is ours, and almost nothing else is mapped. This takes the machine
; to 16 KB mode, where bank 0's ROML at $8000 has the start (main.s). The switch can't run
; from ROMH, which moves to $A000 the moment the mode changes, so it's copied to the
; EasyFlash's RAM and run there.

        .include "hw.inc"
        .include "mem.inc"

        .import start

        .segment "BOOT"

; ----------------------------------------------------------------------------------------
; reset: where the 6502 starts.
;   Before:  power-on or reset, Ultimax mode, bank 0.
;   After:   16 KB mode, bank 0, the stack empty, interrupts off; on to start.
;   Changes: A, X, S; EF_BOOT and on (the switch). No zero page.
reset:
        sei
        cld
        ldx #$FF
        txs
        ldx #switch_end - switch - 1
@copy:  lda switch, x
        sta EF_BOOT, x
        dex
        bpl @copy
        jmp EF_BOOT

; Copied to EF_BOOT: bank 0, 16 KB mode, and on to the start in ROML. No branches in it,
; so it runs the same anywhere.
switch:
        lda #0
        sta EF_BANK
        lda #EF_16K
        sta EF_CONTROL
        jmp start
switch_end:

; ----------------------------------------------------------------------------------------
; nmi_boot, irq_boot: nothing, before the game's own are in.
nmi_boot:
irq_boot:
        rti

        .segment "VECTORS"
        .word nmi_boot, reset, irq_boot
