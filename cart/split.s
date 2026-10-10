; The raster split (docs/cartridge.md, "The screen"): the view over the frames, every
; frame, from the raster interrupt.
;
;   line 250, under the screen: the view's registers ($D018, $D016, $D011, $D021: the
;       map's multicolour characters, or a picture's bitmap and its background), for the
;       next frame's rows 0-15; then the keyboard (keys.s);
;   line 176: the frames' background (black) while the view's last two rows are drawn:
;       a picture's are a black bar of colour-RAM pixels, which the background doesn't
;       touch, and the map's background is black already; then wait for line 178, the view's last line, and change to the frames' (our
;       font, hires, text) after its last character is drawn and before line 179 fetches
;       row 16's: in that gap, wherever in it they land, the changes can't be seen.
;
; The 6502's IRQ vector (in RAM) comes to irq_ram; while the KERNAL is in (a load, a
; cartridge copy), the KERNAL's comes to irq_kernal through $0314, with A, X and Y already
; on the stack. The interrupt uses no zero page and changes no bank.

        .include "hw.inc"
        .include "mem.inc"

        .export irq_ram, irq_kernal, nmi, split_on, frames
        .export view_mode, view_mode_hires
        .import keys_scan

FRAME_LINE  = 250
SPLIT_IRQ   = 176
SPLIT_LINE  = 178

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; split_on: the raster interrupt on, the view as the map's characters.
;   Before:  interrupts off; the screen set up (screen.s).
;   After:   interrupts on; from the next frame, the split.
;   Changes: A.
split_on:
        lda #MEM_VIEW
        sta view_mem
        lda #CTRL2_MULTI
        sta view_ctrl2
        lda #CTRL1_TEXT
        sta view_ctrl1
        lda #BLACK
        sta view_back
        lda #0
        sta phase
        lda #FRAME_LINE
        sta VIC_RASTER
        lda #CTRL1_TEXT             ; the screen on (and the raster's bit 8 clear)
        sta VIC_CTRL1
        lda #$FF
        sta VIC_IRQ
        lda #$01
        sta VIC_IRQ_ENA
        cli
        rts

; ----------------------------------------------------------------------------------------
; view_mode: what the view shows from the next frame, in multicolour: the map's characters
; (MEM_VIEW, CTRL1_TEXT, BLACK) or a picture's bitmap (MEM_PICTURE, CTRL1_BITMAP, its
; background). view_mode_hires: the same in hires (a QR code: qrview.s).
;   Takes:   A = its $D018, X = its $D011, Y = its background.
;   Changes: nothing else.
view_mode:
        php                         ; (all five for the same frame)
        sei
        pha
        lda #CTRL2_MULTI
        bne mode                    ; (always)
view_mode_hires:
        php
        sei
        pha
        lda #CTRL2_HIRES
mode:   sta view_ctrl2
        pla
        sta view_mem
        stx view_ctrl1
        sty view_back
        plp
        rts

; ----------------------------------------------------------------------------------------
; irq_ram, irq_kernal: the raster interrupt.
;   Before:  the interrupt (irq_ram: nothing pushed yet; irq_kernal: A, X, Y pushed).
;   After:   the next one's line set; RTI.
;   Changes: nothing the interrupted code sees.
irq_ram:
        pha
        txa
        pha
        tya
        pha
irq_kernal:
        lda VIC_IRQ
        sta VIC_IRQ                 ; dealt with
        lda phase
        bne split
        ; Line 250: the view, from the top of the next frame.
        lda view_mem
        sta VIC_MEM
        lda view_ctrl2
        sta VIC_CTRL2
        lda view_ctrl1
        sta VIC_CTRL1
        lda view_back
        sta VIC_BACK
        inc frames
        lda #SPLIT_IRQ
        sta VIC_RASTER
        lda #1
        sta phase
        jsr keys_scan
        jmp done

; Line 176: wait for line 178, then for the end of its characters. Line 178's character
; reads end at its cycle 55, and line 179 (a bad line) stops the 6502 from cycle 12 to
; fetch row 16: the three writes must come between. The wait sees line 178 at the read
; of cpx, its cycle r (0-6, as the 7-cycle loop happens to fall); from there to the
; first write is 56 cycles, so the writes land at cycles 56-62, 60-66 and 64-70 (line
; 179's 1-7). Count again after changing anything here.
split:
        lda #BLACK                  ; (line 176: under the view's black bar)
        sta VIC_BACK
        ldx #SPLIT_LINE
@wait:  cpx VIC_RASTER              ; 4 (reads at its last cycle: r)
        bne @wait                   ; 2 falling through: r + 2
        ldx #8                      ; 2: r + 4
@delay: dex                         ; 8 x (2 + 3), less 1: r + 43
        bne @delay
        bit $00                     ; 3: r + 46
        lda #MEM_FRAMES             ; 2: r + 48
        ldx #CTRL2_HIRES            ; 2: r + 50
        ldy #CTRL1_TEXT             ; 2: r + 52
        sta VIC_MEM                 ; writes at r + 56
        stx VIC_CTRL2               ; r + 60
        sty VIC_CTRL1               ; r + 64
        lda #FRAME_LINE
        sta VIC_RASTER
        lda #0
        sta phase
done:   pla
        tay
        pla
        tax
        pla
nmi:                                ; (RESTORE: nothing)
        rti

        .segment "BSS"
phase:      .res 1                  ; 0: the next interrupt is line 250's; 1: the split's
frames:     .res 1                  ; counts up, a frame at a time
view_mem:   .res 1                  ; the view's $D018, $D016, $D011 and $D021
view_ctrl2: .res 1
view_ctrl1: .res 1
view_back:  .res 1
