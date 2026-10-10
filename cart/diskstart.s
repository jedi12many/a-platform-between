; The disk's start (docs/cartridge.md): LOAD"APB",8 and RUN, from an SD2IEC or a 1541.
; The program loads at $0801 with the resident engine in it, after this; this copies the
; engine to RESIDENT_AT (downwards from its end: the two overlap) and goes to main. The
; KERNAL stays as it is, for loading the assets (assets.s).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export disk_start
        .import __RESIDENT_LOAD__, __RESIDENT_RUN__, __RESIDENT_SIZE__
        .import main

        .segment "LOADADDR"
        .word $0801

        .segment "EXEHDR"
        .word @next, 10             ; 10 SYS2061
        .byte $9E, "2061", 0
@next:  .word 0

        .segment "STARTUP"

; ----------------------------------------------------------------------------------------
; disk_start: the resident engine in RAM; on to main.
;   Before:  BASIC's RUN.
;   After:   jumps to main with A = MEDIA_DISK, X = the device, $01 = $37.
;   Changes: everything; zp_src, zp_dst.
disk_start:
        sei
        cld
        ldx #$FF
        txs
        ; The CIAs' interrupts off (their timers stay: the KERNAL's loads use them).
        lda #$7F
        sta CIA1_ICR
        sta CIA2_ICR
        lda CIA1_ICR
        lda CIA2_ICR
        ldx #$18                    ; the SID, quiet
        lda #0
@sid:   sta SID, x
        dex
        bpl @sid
        ; The resident engine, the last page first: it moves up, over where it was.
        lda #<(__RESIDENT_LOAD__ + __RESIDENT_SIZE__ - 1)
        sta zp_src
        lda #>(__RESIDENT_LOAD__ + __RESIDENT_SIZE__ - 1)
        sta zp_src + 1
        lda #<(__RESIDENT_RUN__ + __RESIDENT_SIZE__ - 1)
        sta zp_dst
        lda #>(__RESIDENT_RUN__ + __RESIDENT_SIZE__ - 1)
        sta zp_dst + 1
        lda #<__RESIDENT_SIZE__
        sta zp_len
        lda #>__RESIDENT_SIZE__
        sta zp_len + 1
        ldy #0
@byte:  lda (zp_src), y
        sta (zp_dst), y
        lda zp_src                  ; both pointers down one
        bne @src
        dec zp_src + 1
@src:   dec zp_src
        lda zp_dst
        bne @dst
        dec zp_dst + 1
@dst:   dec zp_dst
        lda zp_len                  ; and the count
        bne @count
        dec zp_len + 1
@count: dec zp_len
        lda zp_len
        ora zp_len + 1
        bne @byte
        ldx KERNAL_DEVICE
        lda #MEDIA_DISK
        jmp main
