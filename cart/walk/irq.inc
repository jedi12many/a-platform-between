; The walking engine's interrupts' way in and on (irq.s): each kind has its own handler,
; TRAMPOLINE's JMP pointed at the next one to come.

; A handler's start: A, X and Y pushed, the interrupt acknowledged (19 cycles).
.macro ENTER
        pha
        txa
        pha
        tya
        pha
        lda #$FF
        sta VIC_IRQ
.endmacro

; The next interrupt's handler: HANDLER.
.macro NEXT handler
        lda #<handler
        sta TRAMPOLINE + 1
        lda #>handler
        sta TRAMPOLINE + 2
.endmacro
