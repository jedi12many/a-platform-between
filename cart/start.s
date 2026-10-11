; The cartridge's start (docs/cartridge.md): from bank 0's ROML, straight after the boot
; (boot.s). It quiets the chips, copies the resident engine from bank 0's ROMH to RAM
; (RESIDENT_AT), and goes to main.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export start
        .import __RESIDENT_LOAD__, __RESIDENT_RUN__, __RESIDENT_SIZE__
        .import main

        .segment "STARTUP"

; ----------------------------------------------------------------------------------------
; start: the machine set up, the resident engine in RAM; on to main.
;   Before:  16 KB mode, bank 0, interrupts off (boot.s).
;   After:   jumps to main with A = MEDIA_CART, $01 = $37.
;   Changes: everything; zp_src, zp_dst.
start:
        lda #PORT_CART              ; the port's value first, then its direction: the
        sta CPU_PORT                ; other way round, the ROMs (and this code) would go
        lda #$2F                    ; out for a moment. Bits 0-5 out.
        sta CPU_DDR
        lda #0
        sta ef_bank
        ; The CIAs: no timers, no interrupts.
        lda #$7F
        sta CIA1_ICR
        sta CIA2_ICR
        lda CIA1_ICR
        lda CIA2_ICR
        lda #0
        sta CIA1_CRA
        sta CIA1_CRB
        sta CIA2_CRA
        sta CIA2_CRB
        lda #$FF                    ; the keyboard: rows out, columns in
        sta CIA1_DDRA
        lda #0
        sta CIA1_DDRB
        lda #%00000011              ; the VIC's bank lines out
        sta CIA2_DDRA
        ; The SID, quiet.
        ldx #$18
        lda #0
@sid:   sta SID, x
        dex
        bpl @sid
        ; The resident engine, from ROMH to RAM.
        lda #<__RESIDENT_LOAD__
        sta zp_src
        lda #>__RESIDENT_LOAD__
        sta zp_src + 1
        lda #<__RESIDENT_RUN__
        sta zp_dst
        lda #>__RESIDENT_RUN__
        sta zp_dst + 1
        ldy #0
        ldx #>__RESIDENT_SIZE__     ; whole pages
        beq @part
@page:  lda (zp_src), y
        sta (zp_dst), y
        iny
        bne @page
        inc zp_src + 1
        inc zp_dst + 1
        dex
        bne @page
@part:  ldx #<__RESIDENT_SIZE__     ; then the rest
        beq @copied
@byte:  lda (zp_src), y
        sta (zp_dst), y
        iny
        dex
        bne @byte
@copied:
        lda #MEDIA_CART
        jmp main
