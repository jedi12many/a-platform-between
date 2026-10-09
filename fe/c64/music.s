; The music player on the C64 (docs/music.md): the same player as client/music.c and
; tools/music/player.py, in 6502, which must write the same registers frame by frame
; (tests/music/check_music.py runs it on py65).
;
; It's in the main program, and runs with everything but RAM switched out ($01 = $34): its
; tunes are at $D800, its note table and the sound effects at $DE00, and its state from
; $DEF0, all under the I/O (fe/c64/split.s calls it, a frame at a time, from the raster
; interrupt, and copies its ghost registers to the SID).
;
;   music_init      A/X = the tune file's length
;   music_frame     one frame: the registers in music_ghost
;   music_command   A = 1 start, 2 change, 3 effect, 4 volume; X = its argument
;   music_find      A/X = an ASCII name (0-terminated): A = its tune, or 255
;   music_playing   A = 1 while a voice is playing
;   music_ghost     the 25 SID registers, $D400-$D418
;
; It uses the zero page at $FB-$FE and $22-$23, which its callers save.

        .setcpu "6502"

DATA     = $D800                ; the tune file
MAXLEN   = $0600                ; 1536 bytes
NOTES_LO = $DE00                ; the note table (fe/c64/split.s copies it in with the tunes)
NOTES_HI = $DE60
EFFECTS  = $DE60 + 96           ; client/sfx.c's table, 8 x 6 bytes, copied in likewise
STATE    = $DEF0

ptr      = $FB
tmp      = $FD
tmp2     = $FE
ptr2     = $22                  ; BASIC's, which is switched out; saved by the caller too

FX_NONE  = 255
STOP     = 254
NONE     = 255

; ----------------------------------------------------------------- the state
        .struct S
len_lo      .byte
len_hi      .byte
ok          .byte
count_t     .byte
count_n     .byte
count_w     .byte
count_p     .byte
ins0_lo     .byte               ; offsets of the tables
ins0_hi     .byte
steps0_lo   .byte
steps0_hi   .byte
pats0_lo    .byte
pats0_hi    .byte
tempo       .byte
volume      .byte
target      .byte
fade_count  .byte
next_tune   .byte
fx          .byte
fx_frames   .byte
fx_release  .byte
fx_pitch    .byte
fx_first    .byte
fx_at       .byte               ; the effect's offset in EFFECTS
cmds        .byte
cmd         .res 16
o_lo        .byte               ; an offset to read
o_hi        .byte
t16_lo      .byte
t16_hi      .byte
; each voice: 3 bytes a field, indexed by the voice (0-2)
stopped     .res 3
has_note    .res 3
seq_lo      .res 3
seq_hi      .res 3
loop_lo     .res 3
loop_hi     .res 3
pat_lo      .res 3
pat_hi      .res 3
transpose   .res 3
length      .res 3
instr       .res 3
ins_lo      .res 3              ; the instrument's record, as an address
ins_hi      .res 3
frames_lo   .res 3
frames_hi   .res 3
note        .res 3
slur_next   .res 3
slur        .res 3
gate        .res 3
step        .res 3
control     .res 3
pitch       .res 3
pulse_lo    .res 3
pulse_hi    .res 3
sweep_lo    .res 3
sweep_hi    .res 3
vib_count   .res 3
vib_phase   .res 3
voff_lo     .res 3
voff_hi     .res 3
vstep_lo    .res 3
vstep_hi    .res 3
        .endstruct

V = STATE                       ; V+S::field

        .export music_init, music_frame, music_command, music_find, music_playing, music_ghost

music_init    = init
music_frame   = frame
music_command = command
music_find    = find
music_playing = playing

        .segment "BSS"
ghost:
music_ghost:
        .res 25
tmp3:   .res 1
legato: .res 1
tmp3x:  .res 1
mul_a:  .res 1
mul_hi: .res 1
mul_2:  .res 1
mul_2hi: .res 1

        .segment "CODE"

; -------------------------------------------------------------------- init
init:
        sta V+S::len_lo
        stx V+S::len_hi
        lda #0
        sta V+S::ok
        sta V+S::cmds
        lda #15
        sta V+S::volume
        sta V+S::target
        lda #2
        sta V+S::tempo
        lda #FX_NONE
        sta V+S::fx
        lda #NONE
        sta V+S::next_tune
        jsr fresh
        ldx #24
        lda #0
@zero:  sta ghost, x
        dex
        bpl @zero
        jmp @check
@b:     rts                     ; damaged: not ok
@check:
        ; The header: "MU", 1, counts in range, and the tables all there.
        lda V+S::len_hi
        cmp #>MAXLEN
        bcc :+
        bne @b
        lda V+S::len_lo
        bne @b
:       lda V+S::len_hi
        bne :+
        lda V+S::len_lo
        cmp #8
        bcc @b
:       lda DATA
        cmp #$4D                ; "M"
        bne @b
        lda DATA + 1
        cmp #$55                ; "U"
        bne @b
        lda DATA + 2
        cmp #1
        bne @b
        lda DATA + 3
        beq @b
        cmp #33
        bcs @b
        sta V+S::count_t
        lda DATA + 4
        cmp #33
        bcs @b
        sta V+S::count_n
        lda DATA + 5
        cmp #129
        bcs @b
        sta V+S::count_w
        lda DATA + 6
        cmp #129
        bcs @b
        sta V+S::count_p
        ; ins0 = 8 + 8 T
        lda V+S::count_t
        jsr times8
        clc
        adc #8
        sta V+S::ins0_lo
        txa
        adc #0
        sta V+S::ins0_hi
        ; steps0 = ins0 + 10 N
        lda V+S::count_n
        jsr times10
        clc
        adc V+S::ins0_lo
        sta V+S::steps0_lo
        txa
        adc V+S::ins0_hi
        sta V+S::steps0_hi
        ; pats0 = steps0 + 2 W
        lda V+S::count_w
        asl a
        tay
        lda #0
        rol a
        tax
        tya
        clc
        adc V+S::steps0_lo
        sta V+S::pats0_lo
        txa
        adc V+S::steps0_hi
        sta V+S::pats0_hi
        ; the end of the tables: pats0 + 2 P <= len
        lda V+S::count_p
        asl a
        tay
        lda #0
        rol a
        tax
        tya
        clc
        adc V+S::pats0_lo
        sta tmp
        txa
        adc V+S::pats0_hi
        cmp V+S::len_hi
        bcc @good
        bne @bad
        lda V+S::len_lo
        cmp tmp
        bcc @bad
@good:  lda #1
        sta V+S::ok
@bad:   rts

; A x 8 -> A (low), X (high)
times8:
        ldx #0
        stx mul_hi
        asl a
        rol mul_hi
        asl a
        rol mul_hi
        asl a
        rol mul_hi
        ldx mul_hi
        rts

; A x 10 -> A (low), X (high)
times10:
        sta mul_a
        lda #0
        sta mul_hi
        lda mul_a
        asl a
        rol mul_hi              ; x 2
        sta mul_2
        lda mul_hi
        sta mul_2hi
        lda mul_2
        asl a
        rol mul_hi
        asl a
        rol mul_hi              ; x 8
        clc
        adc mul_2
        pha
        lda mul_hi
        adc mul_2hi
        tax
        pla
        rts


; Every voice stopped, fresh.
fresh:
        ldx #2
@v:     lda #1
        sta V+S::stopped, x
        sta V+S::length, x
        lda #0
        sta V+S::has_note, x
        sta V+S::seq_lo, x
        sta V+S::seq_hi, x
        sta V+S::loop_lo, x
        sta V+S::loop_hi, x
        sta V+S::pat_lo, x
        sta V+S::pat_hi, x
        sta V+S::transpose, x
        sta V+S::instr, x
        sta V+S::ins_lo, x
        sta V+S::ins_hi, x
        sta V+S::frames_lo, x
        sta V+S::frames_hi, x
        sta V+S::note, x
        sta V+S::slur_next, x
        sta V+S::slur, x
        sta V+S::gate, x
        sta V+S::step, x
        sta V+S::control, x
        sta V+S::pitch, x
        sta V+S::pulse_lo, x
        sta V+S::pulse_hi, x
        sta V+S::sweep_lo, x
        sta V+S::sweep_hi, x
        sta V+S::vib_count, x
        sta V+S::vib_phase, x
        sta V+S::voff_lo, x
        sta V+S::voff_hi, x
        sta V+S::vstep_lo, x
        sta V+S::vstep_hi, x
        dex
        bpl @v
        rts

; ----------------------------------------------------------------- commands
command:
        ldy V+S::cmds
        cpy #16
        bcs @full
        sta V+S::cmd, y
        txa
        sta V+S::cmd + 1, y
        iny
        iny
        sty V+S::cmds
@full:  rts

playing:
        lda V+S::stopped
        and V+S::stopped + 1
        and V+S::stopped + 2
        eor #1
        rts

; A/X = an ASCII name: A = its tune, or 255.
find:
        sta ptr
        stx ptr + 1
        lda V+S::ok
        beq @none
        ; the names: after the pattern offsets
        lda V+S::count_p
        asl a
        sta V+S::o_lo
        lda #0
        rol a
        sta V+S::o_hi
        lda V+S::o_lo
        clc
        adc V+S::pats0_lo
        sta V+S::o_lo
        lda V+S::o_hi
        adc V+S::pats0_hi
        sta V+S::o_hi
        lda #0
        sta tmp2                ; the tune
@tune:  lda tmp2
        cmp V+S::count_t
        bcs @none
        jsr getb                ; its length
        bcs @none
        sta tmp
        ; compare: name[0..len-1] and name[len] = 0
        ldy #0
@char:  cpy tmp
        beq @end
        jsr getb
        bcs @none
        cmp (ptr), y
        bne @skip
        iny
        bne @char
@end:   lda (ptr), y
        bne @skip2
        lda tmp2
        rts
@skip:  iny                     ; past this name's other letters
@skip2: cpy tmp
        beq @next
        jsr getb
        bcs @none
        iny
        jmp @skip2
@next:  inc tmp2
        jmp @tune
@none:  lda #NONE
        rts

; The byte at offset o (then o + 1), carry clear; carry set past the file's end.
getb:
        lda V+S::o_hi
        cmp V+S::len_hi
        bcc @in
        bne @out
        lda V+S::o_lo
        cmp V+S::len_lo
        bcs @out
@in:    lda V+S::o_lo
        clc
        adc #<DATA
        sta ptr2
        lda V+S::o_hi
        adc #>DATA
        sta ptr2 + 1
        sty tmp3
        ldy #0
        lda (ptr2), y
        ldy tmp3
        inc V+S::o_lo
        bne :+
        inc V+S::o_hi
:       clc
        rts
@out:   sec
        rts

; ------------------------------------------------------------------- a frame
frame:
        ; Commands, in the order they came.
        ldy #0
@cmd:   cpy V+S::cmds
        bcs @cmds_done
        lda V+S::cmd + 1, y
        sta tmp
        lda V+S::cmd, y
        sty tmp2
        cmp #1
        bne :+
        lda tmp
        jsr start
        jmp @cmd_next
:       cmp #2
        bne :+
        lda tmp
        cmp #NONE
        bne @to
        lda #STOP
@to:    sta V+S::next_tune
        lda #0
        sta V+S::target
        sta V+S::fade_count
        jmp @cmd_next
:       cmp #3
        bne :+
        lda tmp
        cmp #8
        bcs @cmd_next
        sta V+S::fx
        asl a                   ; x 6
        sta tmp
        asl a
        clc
        adc tmp
        sta V+S::fx_at
        tax
        lda EFFECTS + 5, x
        sta V+S::fx_frames
        lda EFFECTS + 1, x
        sta V+S::fx_pitch
        lda #12
        sta V+S::fx_release
        lda #1
        sta V+S::fx_first
        jmp @cmd_next
:       cmp #4
        bne @cmd_next
        lda tmp
        and #15
        sta V+S::volume
        sta V+S::target
@cmd_next:
        ldy tmp2
        iny
        iny
        jmp @cmd
@cmds_done:
        lda #0
        sta V+S::cmds
        ; Fading.
        lda V+S::volume
        cmp V+S::target
        beq @faded
        inc V+S::fade_count
        lda V+S::fade_count
        cmp #2
        bcc @faded
        lda #0
        sta V+S::fade_count
        lda V+S::target
        cmp V+S::volume
        bcc @down
        inc V+S::volume
        jmp @faded
@down:  dec V+S::volume
@faded: lda V+S::volume
        ora V+S::target
        bne @voices
        lda V+S::next_tune
        cmp #NONE
        beq @voices
        cmp #STOP
        bne @new
        jsr fresh
        lda #NONE
        sta V+S::next_tune
        jmp @voices
@new:   jsr start
@voices:
        ldx #0
@voice: jsr voice_frame
        jsr write_voice
        inx
        cpx #3
        bne @voice
        lda V+S::fx
        cmp #FX_NONE
        beq :+
        jsr effect_frame
:       lda #0
        sta ghost + 21
        sta ghost + 22
        sta ghost + 23
        lda V+S::volume
        sta ghost + 24
        rts

; ----------------------------------------------------------------- start(A)
start:
        pha
        jsr fresh
        lda #15
        sta V+S::volume
        sta V+S::target
        lda #NONE
        sta V+S::next_tune
        pla
        ldx V+S::ok
        beq @out
        cmp V+S::count_t
        bcs @out
        jsr times8
        clc
        adc #<(DATA + 8)
        sta ptr
        txa
        adc #>(DATA + 8)
        sta ptr + 1
        ldy #0
        lda (ptr), y
        sta V+S::tempo
        cmp #2
        bcc @out
        cmp #32
        bcs @out
        ldx #0
@v:     txa
        asl a
        tay
        iny
        iny
        lda (ptr), y            ; this voice's sequence (in the table: always there)
        sta V+S::seq_lo, x
        iny
        lda (ptr), y
        sta V+S::seq_hi, x
        lda #0
        sta V+S::stopped, x
        jsr set_instrument      ; instrument 0
        lda ptr
        pha
        lda ptr + 1
        pha
        jsr next_pattern
        bcc :+
        lda #1
        sta V+S::stopped, x
:       pla
        sta ptr + 1
        pla
        sta ptr
        inx
        cpx #3
        bne @v
@out:   rts

; On through voice X's sequence to its next pattern: carry set if the voice stops.
next_pattern:
        lda #64                 ; 63 steps at most
        sta tmp
@next:  dec tmp
        bne :+
        jmp @stop
:       lda V+S::seq_lo, x
        sta V+S::o_lo
        lda V+S::seq_hi, x
        sta V+S::o_hi
        jsr getb
        bcs @stop
        pha
        lda V+S::o_lo
        sta V+S::seq_lo, x
        lda V+S::o_hi
        sta V+S::seq_hi, x
        pla
        cmp #$FE
        bne :+
        lda V+S::seq_lo, x
        sta V+S::loop_lo, x
        lda V+S::seq_hi, x
        sta V+S::loop_hi, x
        jmp @next
:       cmp #$FF
        bne :+
        lda V+S::loop_lo, x
        ora V+S::loop_hi, x
        beq @stop
        lda V+S::loop_lo, x
        sta V+S::seq_lo, x
        lda V+S::loop_hi, x
        sta V+S::seq_hi, x
        jmp @next
:       cmp #$C0
        bcs @stop
        cmp #$80
        bcc @pattern
        sec
        sbc #$A0
        sta V+S::transpose, x
        jmp @next
@pattern:
        cmp V+S::count_p
        bcs @stop
        asl a                   ; its offset, from the table
        clc
        adc V+S::pats0_lo
        sta ptr2
        lda #0
        adc V+S::pats0_hi
        sta ptr2 + 1
        lda ptr2
        clc
        adc #<DATA
        sta ptr2
        lda ptr2 + 1
        adc #>DATA
        sta ptr2 + 1
        ldy #0
        lda (ptr2), y
        sta V+S::pat_lo, x
        iny
        lda (ptr2), y
        sta V+S::pat_hi, x
        clc
        rts
@stop:  sec
        rts

; ------------------------------------------------------------ voice X's frame
voice_frame:
        lda V+S::stopped, x
        beq :+
        rts
:       lda V+S::frames_lo, x
        ora V+S::frames_hi, x
        beq @fetch
        lda V+S::frames_lo, x
        bne :+
        dec V+S::frames_hi, x
:       dec V+S::frames_lo, x
        lda V+S::frames_lo, x
        ora V+S::frames_hi, x
        bne @counted
@fetch: jsr fetch
        bcc @counted
        lda #1
        sta V+S::stopped, x
        lda #0
        sta V+S::gate, x
        rts
@counted:
        ; The gate shuts a frame early.
        lda V+S::frames_hi, x
        bne @hard
        lda V+S::frames_lo, x
        cmp #1
        bne @hard
        lda V+S::slur, x
        bne @hard
        lda V+S::has_note, x
        beq @hard
        lda #0
        sta V+S::gate, x
@hard:  lda V+S::has_note, x
        bne :+
        rts
:       lda V+S::ins_lo, x
        sta ptr
        lda V+S::ins_hi, x
        sta ptr + 1
        ; The waveform table.
        lda V+S::step, x
        cmp V+S::count_w
        bcs @steps_done
        jsr step_at
        lda (ptr2), y
        cmp #$FF
        bne @apply
        iny
        lda (ptr2), y
        sta V+S::step, x
        cmp V+S::count_w
        bcs @steps_done
        jsr step_at
        lda (ptr2), y
        cmp #$FF
        beq @steps_done
@apply: sta V+S::control, x
        iny
        lda (ptr2), y
        sta V+S::pitch, x
        inc V+S::step, x
@steps_done:
        ; The pulse width.
        ldy #4
        lda (ptr), y
        beq @pulse_done
        lda V+S::pulse_lo, x
        clc
        adc V+S::sweep_lo, x
        sta V+S::pulse_lo, x
        lda V+S::pulse_hi, x
        adc V+S::sweep_hi, x
        sta V+S::pulse_hi, x
        ; past the high limit (x 16)?
        ldy #6
        jsr limit               ; t16 = limit x 16
        lda V+S::pulse_hi, x
        bmi @low                ; negative: under any limit
        cmp V+S::t16_hi
        bcc @low
        bne @over
        lda V+S::pulse_lo, x
        cmp V+S::t16_lo
        beq @low
        bcc @low
@over:  jsr clamp_turn
        jmp @pulse_done
@low:   ldy #5
        jsr limit
        lda V+S::pulse_hi, x
        bmi @under
        cmp V+S::t16_hi
        bcc @under
        bne @pulse_done
        lda V+S::pulse_lo, x
        cmp V+S::t16_lo
        bcs @pulse_done
@under: jsr clamp_turn
@pulse_done:
        ; Vibrato.
        ldy #8
        lda (ptr), y
        beq @vib_done
        lda V+S::vib_count, x
        cmp #255
        beq :+
        inc V+S::vib_count, x
:       ldy #7
        lda (ptr), y
        cmp V+S::vib_count, x
        bcs @vib_done           ; count <= delay
        ldy #9
        lda (ptr), y            ; speed
        sta tmp
        lda V+S::vib_phase, x
        cmp tmp
        bcc @up                 ; phase < speed
        lda tmp
        asl a
        clc
        adc tmp
        sta tmp2                ; 3 speed
        lda V+S::vib_phase, x
        cmp tmp2
        bcs @up                 ; phase >= 3 speed
        lda V+S::voff_lo, x
        sec
        sbc V+S::vstep_lo, x
        sta V+S::voff_lo, x
        lda V+S::voff_hi, x
        sbc V+S::vstep_hi, x
        sta V+S::voff_hi, x
        jmp @phase
@up:    lda V+S::voff_lo, x
        clc
        adc V+S::vstep_lo, x
        sta V+S::voff_lo, x
        lda V+S::voff_hi, x
        adc V+S::vstep_hi, x
        sta V+S::voff_hi, x
@phase: inc V+S::vib_phase, x
        lda tmp
        asl a
        asl a                   ; 4 speed (speed <= 63)
        cmp V+S::vib_phase, x
        beq :+
        bcs @vib_done
:       lda #0
        sta V+S::vib_phase, x
@vib_done:
        rts

; ptr2 = the waveform step in A; Y = 0
step_at:
        asl a
        clc
        adc V+S::steps0_lo
        sta ptr2
        lda #0
        adc V+S::steps0_hi
        sta ptr2 + 1
        lda ptr2
        clc
        adc #<DATA
        sta ptr2
        lda ptr2 + 1
        adc #>DATA
        sta ptr2 + 1
        ldy #0
        rts

; t16 = the instrument's byte Y x 16
limit:
        lda (ptr), y
        sta V+S::t16_lo
        lda #0
        sta V+S::t16_hi
        ldy #4
:       asl V+S::t16_lo
        rol V+S::t16_hi
        dey
        bne :-
        rts

; pulse = t16, and the sweep turns round
clamp_turn:
        lda V+S::t16_lo
        sta V+S::pulse_lo, x
        lda V+S::t16_hi
        sta V+S::pulse_hi, x
        lda #0
        sec
        sbc V+S::sweep_lo, x
        sta V+S::sweep_lo, x
        lda #0
        sbc V+S::sweep_hi, x
        sta V+S::sweep_hi, x
        rts

; ---------------------------------------------------- voice X's next event
; Carry set: the voice stops.
fetch:
        lda #0
        sta tmp2                ; a count, to 256: a pattern that never ends stops
@loop:  dec tmp2
        bne :+
        jmp fetch_stop
:       lda V+S::pat_lo, x
        sta V+S::o_lo
        lda V+S::pat_hi, x
        sta V+S::o_hi
        jsr getb
        bcc :+
        jmp fetch_stop
:       pha
        lda V+S::o_lo
        sta V+S::pat_lo, x
        lda V+S::o_hi
        sta V+S::pat_hi, x
        pla
        cmp #$FF
        bne :+
        lda tmp2
        pha
        jsr next_pattern
        pla
        sta tmp2
        bcc @loop
        jmp fetch_stop
:       cmp #$E0
        bne :+
        lda #1
        sta V+S::slur_next, x
        jmp @loop
:       cmp #$C0
        bcc :+
        cmp #$E0
        bcs fetch_far
        and #$1F
        cmp V+S::count_n
        bcs fetch_far
        sta V+S::instr, x
        jsr set_instrument
        jmp @loop
:       cmp #$80
        bcc :+
        and #$3F
        clc
        adc #1
        sta V+S::length, x
        jmp @loop
:       cmp #$62
        bcc :+
fetch_far:
        jmp fetch_stop
:       ; A segment: a note, a rest or a tie.
        sta tmp
        lda V+S::slur, x
        sta legato
        lda V+S::slur_next, x
        sta V+S::slur, x
        lda #0
        sta V+S::slur_next, x
        jsr set_frames
        lda tmp
        cmp #$60
        bne :+
        lda #0
        sta V+S::gate, x
        clc
        rts
:       bcc @note
        clc                     ; a tie
        rts
@note:  clc
        adc V+S::transpose, x
        ldy V+S::transpose, x
        bpl @pos
        bcs @ok                 ; negative transpose: no borrow means >= 0
        lda #0
        beq @ok
@pos:   bcs @top
@ok:    cmp #96
        bcc :+
@top:   lda #95
:       sta V+S::note, x
        lda V+S::count_n
        beq fetch_stop
        lda legato
        and V+S::has_note, x
        bne @vib
        lda #1
        sta V+S::has_note, x
        sta V+S::gate, x
        lda V+S::ins_lo, x
        sta ptr
        lda V+S::ins_hi, x
        sta ptr + 1
        ldy #2
        lda (ptr), y
        sta V+S::step, x
        iny
        lda (ptr), y            ; pulse = start x 16
        sta V+S::pulse_lo, x
        lda #0
        sta V+S::pulse_hi, x
        ldy #4
:       asl V+S::pulse_lo, x
        rol V+S::pulse_hi, x
        dey
        bne :-
        ldy #4
        lda (ptr), y
        sta V+S::sweep_lo, x
        lda #0
        sta V+S::sweep_hi, x
        lda V+S::sweep_lo, x
        bpl :+
        dec V+S::sweep_hi, x
:       lda #0
        sta V+S::vib_count, x
        sta V+S::vib_phase, x
        sta V+S::voff_lo, x
        sta V+S::voff_hi, x
@vib:   jsr vib_step
        clc
        rts
fetch_stop:
        sec
        rts


; Voice X's instrument record, as an address: DATA + ins0 + 10 x its instrument
set_instrument:
        stx tmp3x
        lda V+S::instr, x
        jsr times10
        clc
        adc V+S::ins0_lo
        sta mul_a
        txa
        adc V+S::ins0_hi
        ldx tmp3x
        sta V+S::ins_hi, x
        lda mul_a
        clc
        adc #<DATA
        sta V+S::ins_lo, x
        lda V+S::ins_hi, x
        adc #>DATA
        sta V+S::ins_hi, x
        rts

; frames = length x tempo
set_frames:
        lda #0
        sta V+S::frames_lo, x
        sta V+S::frames_hi, x
        ldy V+S::tempo
:       lda V+S::frames_lo, x
        clc
        adc V+S::length, x
        sta V+S::frames_lo, x
        bcc :+
        inc V+S::frames_hi, x
:       dey
        bne :--
        rts

; The vibrato's step: (the next semitone - this note) >> depth
vib_step:
        lda V+S::ins_lo, x
        sta ptr
        lda V+S::ins_hi, x
        sta ptr + 1
        lda #0
        sta V+S::vstep_lo, x
        sta V+S::vstep_hi, x
        ldy #8
        lda (ptr), y
        beq @done
        sta tmp
        ldy V+S::note, x
        cpy #95
        beq @done               ; no note above: no step
        lda NOTES_LO + 1, y
        sec
        sbc NOTES_LO, y
        sta V+S::vstep_lo, x
        lda NOTES_HI + 1, y
        sbc NOTES_HI, y
        sta V+S::vstep_hi, x
:       lsr V+S::vstep_hi, x
        ror V+S::vstep_lo, x
        dec tmp
        bne :-
@done:  rts

; ------------------------------------------------- voice X's registers, ghost
write_voice:
        cpx #2
        bne :+
        lda V+S::fx
        cmp #FX_NONE
        beq :+
        rts
:       txa
        asl a
        asl a
        asl a
        stx tmp
        sec
        sbc tmp                 ; 7 x
        tay
        lda V+S::has_note, x
        bne :+
        lda ghost + 4, y
        and #$FE
        sta ghost + 4, y
        rts
:       sty tmp2
        ; the note: the step's fixed note, or the note + its offset
        lda V+S::pitch, x
        bpl @rel
        and #$7F
        cmp #96
        bcc @n
        lda #95
        bcs @n
@rel:   cmp #$40
        bcc @plus
        ora #$80                ; a signed 7-bit offset: negative
        clc
        adc V+S::note, x
        bcs @n                  ; no borrow: >= 0
        lda #0
        beq @n
@plus:  clc
        adc V+S::note, x
        cmp #96
        bcc @n
        lda #95
@n:     tay
        lda NOTES_LO, y
        clc
        adc V+S::voff_lo, x
        sta tmp
        lda NOTES_HI, y
        adc V+S::voff_hi, x
        ldy tmp2
        sta ghost + 1, y
        lda tmp
        sta ghost, y
        lda V+S::pulse_lo, x
        sta ghost + 2, y
        lda V+S::pulse_hi, x
        and #$0F
        sta ghost + 3, y
        lda V+S::control, x
        and #$FE
        ora V+S::gate, x
        sta ghost + 4, y
        lda V+S::ins_lo, x
        sta ptr
        lda V+S::ins_hi, x
        sta ptr + 1
        sty tmp2
        ldy #0
        lda (ptr), y
        ldy tmp2
        sta ghost + 5, y
        sty tmp2
        ldy #1
        lda (ptr), y
        ldy tmp2
        sta ghost + 6, y
        rts

; ------------------------------------------------------- the effect, voice 3
effect_frame:
        ldy V+S::fx_at
        lda V+S::fx_first
        bne @first
        lda V+S::fx_frames
        beq @release
        dec V+S::fx_frames
        beq @regs
        lda V+S::fx_pitch
        clc
        adc EFFECTS + 2, y
        sta V+S::fx_pitch
        jmp @regs
@release:
        dec V+S::fx_release
        bne @regs
        lda #FX_NONE
        sta V+S::fx
        lda #0
        sta V+S::gate + 2
        ldx #2
        jmp write_voice
@first: lda #0
        sta V+S::fx_first
@regs:  lda #0
        sta ghost + 14
        sta ghost + 16
        lda V+S::fx_pitch
        sta ghost + 15
        lda #8
        sta ghost + 17
        lda EFFECTS, y
        and #$FE
        ldx V+S::fx_frames
        beq :+
        ora #1
:       sta ghost + 18
        lda EFFECTS + 3, y
        sta ghost + 19
        lda EFFECTS + 4, y
        sta ghost + 20
        rts
