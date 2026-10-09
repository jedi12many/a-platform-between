; The battle screen's raster interrupt (fe/c64/scene.c, docs/c64.md): the sprites, more
; of them than the VIC-II's eight, and the clock, keys and music once a frame.
;
; scene.c works out where every sprite goes in a frame (its "plan") and hands it over in
; _scene_next; the interrupt takes it at the next frame's start. Then, a frame at a time:
;
;   line 250 (under the screen): the plan's first eight sprites, one to each of the
;       VIC's, a frame of music (fe/c64/tune.s, sound effects and all), and the
;       KERNAL's own interrupt (keyboard and clock);
;   on down the screen: each time one of the eight has finished drawing its sprite,
;       the next sprite that was planned for it: its shape, colour and place. scene.c
;       plans no sprite closer under the one before it than this has time for.
;
; The plan, bytes (scene.c's scene_plan, the same):
;
;   0   the first eight: x (low bits) 8, y 8, shape pointer 8, colour 8;
;   32  their x high bits ($D010), multicolour ($D01C), switched on ($D015);
;   35  how many more (events), up to 16; then for each, in 16s:
;   36  the raster line to set it on, the VIC sprite (0-7), the same times 2, x (low
;       bits), y, shape pointer, colour, and $D010 and $D01C as they are after it.

        .export _scene_start, _scene_stop, _scene_wait, _hal_scene_log
        .export _scene_next, _scene_pending
        .import tune_tick, irq_on
        .importzp ptr1, ptr2

FRAME_LINE = 250
SPRPTR     = $EBF8                  ; the screen's at $E800: its sprite pointers
PLAN       = 180

TX   = 0
TY   = 8
TP   = 16
TC   = 24
TMSB = 32
TMC  = 33
TEN  = 34
EVN  = 35
EL   = 36
ES   = 52
ES2  = 68
EX   = 84
EY   = 100
EP   = 116
EC   = 132
EM   = 148
EMC  = 164

        .segment "BSS"              ; the main program's: the overlay has no room

_scene_next:    .res PLAN           ; scene.c writes the next plan here...
_scene_pending: .res 1              ; ...and sets this; the interrupt takes it, and clears it
live:           .res PLAN           ; the plan being shown
evi:            .res 1              ; the next event
frames:         .res 1              ; counts up a frame at a time
count:          .res 1

        .segment "OVERLAY3"

; The battle screen on: VIC bank 3, screen $E800, characters $E000, multicolour; the
; raster interrupt, and no CIA timer interrupts (the raster runs the KERNAL's). The
; story's text screen ($F800) is kept at $FC00 meanwhile: the sprite shapes ($EC00) run
; over its first rows.
_scene_start:
        sei
        jsr keep_text
        lda #0
        sta evi
        sta _scene_pending
        sta live + EVN
        sta live + TEN
        sta $D015
        sta $D017
        sta $D01D
        sta $D01B
        lda #$7F
        sta $DC0D
        lda $DC0D
        lda #<irq
        sta $0314
        lda #>irq
        sta $0315
        lda #FRAME_LINE
        sta $D012
        lda $D011
        and #$7F
        sta $D011
        lda $DD00
        and #$FC
        sta $DD00
        lda #$A8
        sta $D018
        lda $D016
        ora #$10
        sta $D016
        lda #$FF
        sta $D019
        lda #$01
        sta $D01A
        cli
        rts

; And off: the story's text screen back, as fe/c64/split.s shows it, with its interrupt.
_scene_stop:
        sei
        jsr text_back
        lda #0
        sta $D01A
        sta $D015
        sta $D020
        sta $D021
        lda #$FF
        sta $D019
        lda #$E4                    ; screen $F800, characters $D000 (bank 3 still)
        sta $D018
        lda $D016
        and #$EF
        sta $D016
        jmp irq_on                  ; (which lets interrupts in again)

; The text screen to $FC00 and back, with the KERNAL's ROM out (interrupts are off).
keep_text:
        lda #$F8
        ldx #$FC
        bne move_text               ; always
text_back:
        lda #$FC
        ldx #$F8
move_text:
        sta ptr2 + 1
        stx ptr1 + 1
        lda #0
        sta ptr1
        sta ptr2
        lda $01
        pha
        lda #$35
        sta $01
        ldx #4                      ; 1000 bytes: 3 pages and 232 (not the 6502's
        ldy #0                      ; vectors at $FFFA, in the RAM at $FC00 + 1018)
@copy:  lda (ptr2), y
        sta (ptr1), y
        iny
        cpx #1
        bne @page
        cpy #232
        beq @done
@page:  cpy #0
        bne @copy
        inc ptr1 + 1
        inc ptr2 + 1
        dex
        bne @copy
@done:  pla
        sta $01
        rts

; Wait until the plan handed over is up, then A frames more. tests/c64/run_c64.py has no
; interrupts and skips this, so don't rename it.
_scene_wait:
        sta count
@sync:  lda _scene_pending
        bne @sync
@more:  lda count
        beq @done
        lda frames
@tick:  cmp frames
        beq @tick
        dec count
        jmp @more
@done:  rts

; A line for the tests' record (client/apb_scene.h): shown nowhere. tests/c64/run_c64.py
; reads it here, so don't rename it.
_hal_scene_log:
        rts

irq:
        lda $D019
        sta $D019                   ; this one's dealt with
        ldx evi
        cpx live + EVN
        bcs frame
event:
        ldy live + ES, x            ; the shape first: it's what shows if we're late
        lda live + EP, x
        sta SPRPTR, y
        lda live + EC, x
        sta $D027, y
        ldy live + ES2, x
        lda live + EX, x
        sta $D000, y
        lda live + EY, x
        sta $D001, y
        lda live + EM, x
        sta $D010
        lda live + EMC, x
        sta $D01C
        inx
        cpx live + EVN
        bcs @last
        lda live + EL, x            ; the next one's line: nearly here, wait for it
        sec
        sbc #3
        cmp $D012
        bcs @later
@spin:  lda $D012
        cmp live + EL, x
        bcc @spin
        jmp event
@later: lda live + EL, x
        sta $D012
        stx evi
        jmp $EA81                   ; restore the registers, return
@last:  stx evi
        lda #FRAME_LINE
        sta $D012
        jmp $EA81

frame:
        lda _scene_pending
        beq @same
        ldx #PLAN - 1
@copy:  lda _scene_next, x
        sta live, x
        dex
        cpx #$FF
        bne @copy
        lda #0
        sta _scene_pending
@same:  ldx #7
@top:   lda live + TP, x
        sta SPRPTR, x
        lda live + TC, x
        sta $D027, x
        txa
        asl a
        tay
        lda live + TX, x
        sta $D000, y
        lda live + TY, x
        sta $D001, y
        dex
        bpl @top
        lda live + TMSB
        sta $D010
        lda live + TMC
        sta $D01C
        lda live + TEN
        sta $D015
        ldx #0
        stx evi
        lda #FRAME_LINE
        ldy live + EVN
        beq @set
        lda live + EL
@set:   sta $D012
        inc frames
        jsr tune_tick               ; a frame of music
        jmp $EA31                   ; the KERNAL's interrupt: keys, clock
