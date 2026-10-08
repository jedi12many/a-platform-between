; The battle screen's raster interrupt (fe/c64/scene.c, docs/c64.md): the sprites, more
; of them than the VIC-II's eight, and the clock, keys and sound once a frame.
;
; scene.c works out where every sprite goes in a frame (its "plan") and hands it over in
; _scene_next; the interrupt takes it at the next frame's start. Then, a frame at a time:
;
;   line 250 (under the screen): the plan's first eight sprites, one to each of the
;       VIC's, and the KERNAL's own interrupt (keyboard and clock);
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
        .export _sfx_time, _sfx_sweep, _sfx_wave, _sfx_freq

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
_sfx_time:      .res 1              ; frames until the sound effect's gate closes
_sfx_sweep:     .res 1              ; added to its pitch each frame
_sfx_wave:      .res 1              ; its waveform (gate off)
_sfx_freq:      .res 1              ; its pitch (high byte)

        .segment "OVERLAY3"

; The battle screen on: VIC bank 3, screen $E800, characters $E000, multicolour; the
; raster interrupt, and no CIA timer interrupts (the raster runs the KERNAL's).
_scene_start:
        sei
        lda #0
        sta evi
        sta _scene_pending
        sta live + EVN
        sta live + TEN
        sta _sfx_time
        sta $D015
        sta $D017
        sta $D01D
        sta $D01B
        sta $D404
        lda #$0F
        sta $D418                   ; the SID's volume up
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

; And off: the text screen, as fe/c64/split.s leaves it, and the CIA timer.
_scene_stop:
        sei
        lda #0
        sta $D01A
        sta $D015
        sta $D404
        sta $D020
        sta $D021
        lda #$FF
        sta $D019
        lda #$31
        sta $0314
        lda #$EA
        sta $0315
        lda #$81
        sta $DC0D
        lda $DD00
        ora #$03
        sta $DD00
        lda #$17
        sta $D018
        lda $D016
        and #$EF
        sta $D016
        cli
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
        lda _sfx_time               ; the sound effect: its pitch slides, its gate closes
        beq @kernal
        dec _sfx_time
        bne @slide
        lda _sfx_wave
        sta $D404
        jmp @kernal
@slide: lda _sfx_freq
        clc
        adc _sfx_sweep
        sta _sfx_freq
        sta $D401
@kernal:
        jmp $EA31                   ; the KERNAL's interrupt: keys, clock
