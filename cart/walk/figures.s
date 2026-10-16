; The figures (docs/walk.md, "The figures"): the party in marching order on the leader's
; trail, and the floor's foes and people, as sprites, as tools/walk/walk.py's figures
; does it: each frame, those in sight, sorted down the screen, given the VIC's 8 sprites
; (a sprite reused below one it has shown), into a program the interrupt carries out
; (mux.s) from the next frame.

        .include "zp.inc"
        .include "walk.inc"

        .export figures_init, figures_step, prog_next, prog_left
        .import floor, wk_pos, wk_cam

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; figures_init: the trail at the leader's start, everyone facing right; the first frame's
; program made.
;   Before:  wk_pos and wk_cam set.
;   Changes: A, X, Y, zp_wk_*.
figures_init:
        jsr leader_px
        ldx #TRAIL - 1
        stx head
        lda zp_wk_a
        sta trail_xl + TRAIL - 1
        lda zp_wk_a + 1
        sta trail_xh + TRAIL - 1
        lda zp_wk_b
        sta trail_y + TRAIL - 1
        lda zp_wk_b + 1
        sta trail_yh + TRAIL - 1
        lda #1
        sta trail_len
        lda #0
        sta steps
        sta moved
        ldx #PARTY_SIZE - 1
:       lda zp_wk_a
        sta last_xl, x
        lda zp_wk_a + 1
        sta last_xh, x
        lda #0
        sta facing, x
        dex
        bpl :-
        ; The floor's figures: their pixels (16 times their squares), kinds, shapes and
        ; colours, worked out once.
        ldy #0
        ldx #0
@fig:   cpx floor + FL_FIGURES
        beq @built
        lda floor + FL_FIGURES + 1, y
        sta fig_sx, x
        jsr times16
        sta fig_xl, x
        lda zp_wk_t
        sta fig_xh, x
        lda floor + FL_FIGURES + 2, y
        sta fig_sy, x
        jsr times16
        sta fig_yl, x
        lda zp_wk_t
        sta fig_yh, x
        lda floor + FL_FIGURES + 3, y
        sta fig_kind, x
        asl a                       ; its shapes: 2 kind, + 1 facing left
        adc #SHAPE_POINTER
        sta fig_ptr, x
        sty zp_wk_i
        ldy fig_kind, x
        lda floor + FL_KIND_COLOUR, y
        sta fig_col, x
        ldy zp_wk_i
        iny
        iny
        iny
        inx
        jmp @fig
@built: ; Where each row's figures start (they come in order down the area): row_first[r]
        ; the first whose square's y is r or more, for r = 0 to SQUARES_Y + 1.
        ldx #0                      ; the figure
        ldy #0                      ; the row
@row:   cpx floor + FL_FIGURES
        beq :+
        tya
        cmp fig_sy, x
        bcc :+                      ; r < its row: the row starts here
        beq :+
        inx
        jmp @row
:       txa
        sta row_first, y
        iny
        cpy #SQUARES_Y + 2
        bne @row
        jmp build

; A = A x 16's low byte, zp_wk_t its high.
times16:
        sta zp_wk_t
        lda #0
        .repeat 4
        asl zp_wk_t
        rol a
        .endrepeat
        pha
        lda zp_wk_t
        sta zp_wk_mx
        pla
        sta zp_wk_t
        lda zp_wk_mx
        rts

; ----------------------------------------------------------------------------------------
; figures_step: the trail moved on if the leader has, and the next frame's program made.
;   Before:  this frame's walk and camera done (wk_pos, wk_cam the next frame's).
;   Changes: A, X, Y, zp_wk_*.
figures_step:
        lda #0
        sta moved
        jsr leader_px
        ldx head
        lda zp_wk_a
        cmp trail_xl, x
        bne @moved
        lda zp_wk_a + 1
        cmp trail_xh, x
        bne @moved
        lda zp_wk_b
        cmp trail_y, x
        bne @moved
        lda zp_wk_b + 1
        cmp trail_yh, x
        beq build
@moved: inc moved
        inc steps
        inx
        txa
        and #TRAIL - 1
        sta head
        tax
        lda zp_wk_a
        sta trail_xl, x
        lda zp_wk_a + 1
        sta trail_xh, x
        lda zp_wk_b
        sta trail_y, x
        lda zp_wk_b + 1
        sta trail_yh, x
        lda trail_len
        cmp #TRAIL
        beq build
        inc trail_len
        ; (on into build)

; The next frame's program: the figures in sight, sorted, allocated.
build:
        lda #0
        sta count
        jsr window                  ; the view's window, and the sprites' offsets
        ; The party: traveler k at the trail's entry GAP k back, if it's that long.
        ldy #0                      ; k
@party: sty party_k
        lda gap_back, y
        cmp trail_len
        bcc :+
        jmp @next_k                 ; (not yet out from behind the one before)
:       eor #$FF                    ; head - GAP k, round the trail
        sec
        adc head
        and #TRAIL - 1
        tax
        lda trail_xl, x
        sta zp_wk_a
        lda trail_xh, x
        sta zp_wk_a + 1
        lda trail_y, x
        sta zp_wk_b
        lda trail_yh, x
        sta zp_wk_b + 1
        ; Which way they face: as their x changed since last drawn.
        ldy party_k
        lda zp_wk_a
        cmp last_xl, y
        lda zp_wk_a + 1
        sbc last_xh, y
        bcc @left                   ; x < last: left
        lda zp_wk_a
        cmp last_xl, y
        bne @right
        lda zp_wk_a + 1
        cmp last_xh, y
        beq @faced
@right: lda #0
        beq @face
@left:  lda #1
@face:  sta facing, y
@faced: lda zp_wk_a
        sta last_xl, y
        lda zp_wk_a + 1
        sta last_xh, y
        ; A step's bob: up a pixel while ((steps + 4 k) & 8), if the leader moved.
        lda moved
        beq @nobob
        tya
        asl a
        asl a
        clc
        adc steps
        and #8
        beq @nobob
        lda zp_wk_b
        sec
        sbc #1
        sta zp_wk_b
        lda zp_wk_b + 1
        sbc #0
        sta zp_wk_b + 1
@nobob: lda floor + FL_PARTY, y     ; its shape: 2 kind + facing
        asl a
        ora facing, y
        sta zp_wk_t
        lda floor + FL_PARTY, y
        tay
        lda floor + FL_KIND_COLOUR, y
        tay
        jsr add_figure
        ldy party_k
@next_k:
        iny
        cpy #PARTY_SIZE
        beq :+
        jmp @party
:       lda count                   ; the party's in the list first
        sta party_n
        ; The floor's foes and people: facing the leader. Only those inside the view's
        ; window on the area are in sight.
        ldx head                    ; the leader's x + 9 (x + 8 < theirs: theirs >= this)
        lda trail_xl, x
        clc
        adc #9
        sta lead_xl
        lda trail_xh, x
        adc #0
        sta lead_xh
        ldx sq_y1                   ; the rows near the window: their figures from...
        lda row_first + 1, x
        sta fig_end                 ; ...up to those of the row past it
        ldx sq_y0
        ldy row_first, x
@floor: cpy fig_end
        bne :+
        jmp sort
:       lda fig_sx, y               ; in squares: on the window's edge columns, its pixels
        cmp sq_x0                   ; decide; between them, it's in (the rows looked at
        bcc @skip                   ; are those from sq_y0 to sq_y1, the same)
        beq @x_edge
        cmp sq_x1
        bcc @y
        bne @skip
@x_edge: lda fig_xl, y              ; x within win_x0 - win_x1?
        cmp win_x0
        lda fig_xh, y
        sbc win_x0 + 1
        bcc @skip
        lda win_x1
        cmp fig_xl, y
        lda win_x1 + 1
        sbc fig_xh, y
        bcc @skip
@y:     lda fig_sy, y
        cmp sq_y0
        beq @y_edge
        cmp sq_y1
        bne @in
@y_edge: lda fig_yl, y              ; y within win_y0 - win_y1?
        cmp win_y0
        lda fig_yh, y
        sbc win_y0 + 1
        bcc @skip
        lda win_y1
        cmp fig_yl, y
        lda win_y1 + 1
        sbc fig_yh, y
        bcs @in
@skip:  iny
        jmp @floor
@in:    ldx count                   ; in sight: into the list, its sprite's x and y...
        lda fig_xl, y
        clc
        adc off_x
        sta list_xl, x
        lda fig_xh, y
        adc off_x + 1
        sta list_xh, x
        lda fig_yl, y
        clc
        adc off_y
        sta list_y, x
        lda fig_col, y              ; ...its colour...
        sta list_col, x
        lda fig_xl, y               ; ...its shape: facing left if theirs > the leader's
        cmp lead_xl                 ; x + 8 (carry set: so)
        lda fig_xh, y
        sbc lead_xh
        lda fig_ptr, y
        adc #0
        sta list_ptr, x
        inc count
        iny
        jmp @floor

; The view's window on the area: the pixels a figure's square can be at and be in sight
; (SPRITE_X_MIN - SPRITE_DX to SPRITE_X_MAX - SPRITE_DX from the camera, and the same
; down), each kept at 0 or more: a figure inside it is in sight, add_figure's tests
; passed.
window:
        lda #SPRITE_DX              ; and the sprites' offsets: SPRITE_DX - the camera...
        sec
        sbc wk_cam
        sta off_x
        lda #0
        sbc wk_cam + 1
        sta off_x + 1
        lda #SPRITE_DY              ; ...and SPRITE_DY - the camera
        sec
        sbc wk_cam + 2
        sta off_y
        lda #0
        sbc wk_cam + 3
        sta off_y + 1
        ldx #0
        jsr window_axis
        ldx #2
        jsr window_axis
        ldx #0                      ; and in squares (>> 4): a byte each
        jsr window_squares
        ldx #2
window_squares:
        lda win_x0 + 1, x
        sta zp_wk_t
        lda win_x0, x
        .repeat 4
        lsr zp_wk_t
        ror a
        .endrepeat
        sta sq_x0, x
        lda win_x1 + 1, x
        sta zp_wk_t
        lda win_x1, x
        .repeat 4
        lsr zp_wk_t
        ror a
        .endrepeat
        sta sq_x1, x
        rts
window_axis:
        lda wk_cam, x
        clc
        adc lims, x                 ; the far edge
        sta win_x1, x
        lda wk_cam + 1, x
        adc lims + 1, x
        sta win_x1 + 1, x
        lda wk_cam, x               ; the near edge
        sec
        sbc nears, x
        sta win_x0, x
        lda wk_cam + 1, x
        sbc #0
        sta win_x0 + 1, x
        bcs :+
        lda #0
        sta win_x0, x
        sta win_x0 + 1, x
:       rts

; One figure: at the area's pixel (a, b), shape zp_wk_t, colour Y. In sight, it's added
; to the list: its sprite's x (2 bytes), y, pointer and colour.
add_figure:
        sty zp_wk_i
        lda zp_wk_a                 ; x + SPRITE_DX - cam
        clc
        adc off_x
        sta zp_wk_a
        lda zp_wk_a + 1
        adc off_x + 1
        sta zp_wk_a + 1
        bmi @out                    ; (well off to the left)
        lda zp_wk_a                 ; < SPRITE_X_MIN, > SPRITE_X_MAX: out of sight
        cmp #<SPRITE_X_MIN
        lda zp_wk_a + 1
        sbc #>SPRITE_X_MIN
        bcc @out
        lda #<SPRITE_X_MAX
        cmp zp_wk_a
        lda #>SPRITE_X_MAX
        sbc zp_wk_a + 1
        bcc @out
        lda zp_wk_b                 ; y + SPRITE_DY - cam
        clc
        adc off_y
        sta zp_wk_b
        lda zp_wk_b + 1
        adc off_y + 1
        bne @out                    ; (off the bottom, or above the top: negative)
        lda zp_wk_b
        cmp #SPRITE_Y_MIN
        bcc @out
        cmp #SPRITE_Y_MAX + 1
        bcs @out
        ldx count
        sta list_y, x
        lda zp_wk_a
        sta list_xl, x
        lda zp_wk_a + 1
        sta list_xh, x
        lda zp_wk_t
        clc
        adc #SHAPE_POINTER
        sta list_ptr, x
        lda zp_wk_i
        sta list_col, x
        inc count
@out:   rts

; ----------------------------------------------------------------------------------------
; The list sorted down the screen (by y; those level keep their order), into order[]: the
; party's (the first party_n) sorted into porder[], then merged with the floor's, which
; came in order down (the party first where they're level).
sort:
        ldx #0
@each:  cpx party_n
        beq merge
        ; insert x after the last of porder[0..x) whose y is no more than its own
        stx zp_wk_i
        ldy zp_wk_i
@shift: dey
        bmi @put
        lda porder, y
        tax
        lda list_y, x
        ldx zp_wk_i
        cmp list_y, x
        beq @put                    ; (level: keep the earlier first)
        bcc @put
        lda porder, y               ; theirs is lower: move it along
        sta porder + 1, y
        jmp @shift
@put:   iny
        lda zp_wk_i
        sta porder, y
        ldx zp_wk_i
        inx
        jmp @each

merge:  ldx #0                      ; X: the next of porder[]
        stx out_k
        ldy party_n                 ; Y: the next of the floor's
@m:     cpx party_n
        beq @floors
        cpy count
        beq @partys
        stx zp_wk_i
        lda porder, x
        tax
        lda list_y, x               ; the party's no lower: it first
        cmp list_y, y
        beq @p
        bcc @p
        tya                         ; the floor's
        ldx out_k
        sta order, x
        inc out_k
        iny
        ldx zp_wk_i
        jmp @m
@p:     txa
        ldx out_k
        sta order, x
        inc out_k
        ldx zp_wk_i
        inx
        jmp @m
@floors: cpy count                  ; the rest of the floor's
        beq @done
        tya
        ldx out_k
        sta order, x
        inc out_k
        iny
        jmp @floors
@partys: cpx party_n                ; or of the party's
        beq @done
        lda porder, x
        ldy out_k
        sta order, y
        inc out_k
        inx
        jmp @partys
@done:  ; (on into allocate)

; ----------------------------------------------------------------------------------------
; The sprites shared out (walk.py's allocate): each figure, down the screen, takes the next
; sprite in turn (0-7, then round again: always one free soonest), if it's free by its top
; line. So the first eight take sprites 0-7, set at the frame's start; each one after
; reuses a sprite, an event on the line the last figure it showed ends (they come in that
; order). Into the program not shown (PROG_A or PROG_B): a copy of the code for each.
allocate:
        lda prog_next
        eor #1
        sta prog_next
        beq alloc_a
        jmp alloc_b

.macro ALLOC base
        .local first, rest, out, next, done
        lda #0
        sta left
        sta enable
        sta highs
        sta events
        sta turn
        ldy #0                      ; i: the figure, in order
first:  cpy count
        bne :+
        jmp done
:       cpy #8                      ; past the first eight: a sprite reused
        bcc :+
        jmp rest
:       tya                         ; sprite i
        tax
        lda order, y
        tay
        lda list_xl, y
        sta base + P_X, x
        lda list_y, y
        sta base + P_Y, x
        sta last_y, x
        clc
        adc #REUSE
        bcc :+
        lda #$FF                    ; (past the screen: never free again this frame)
:       sta free, x
        lda list_ptr, y
        sta base + P_PTR, x
        lda list_col, y
        sta base + P_COLOUR, x
        lda bit_of, x
        ora enable
        sta enable
        lda list_xh, y
        beq :+
        lda bit_of, x
        ora highs
        sta highs
:       inx
        txa
        tay
        jmp first
rest:   sty zp_wk_i                ; (turn is 0: the first eight came round to it)
        lda order, y
        tay                         ; the figure
        ldx turn
        stx slot
        lda free, x
        cmp list_y, y               ; free by its top line?
        beq :+
        bcs out
:       lda events
        cmp #EVENTS_MAX
        bcs out
        asl a                       ; its record: P_EVENTS + 8 n
        asl a
        asl a
        adc #P_EVENTS
        tax
        stx zp_wk_t
        ldx slot
        lda last_y, x
        clc
        adc #SPRITE_LINES
        ldx zp_wk_t
        sta base + E_LINE, x
        lda slot
        sta base + E_SPRITE, x
        lda list_xl, y
        sta base + E_X, x
        lda list_xh, y
        sta base + E_X_HIGH, x
        lda list_y, y
        sta base + E_Y, x
        lda list_ptr, y
        sta base + E_PTR, x
        lda list_col, y
        sta base + E_COLOUR, x
        inc events
        ldx slot
        lda list_y, y
        sta last_y, x
        clc
        adc #REUSE
        bcc :+
        lda #$FF
:       sta free, x
        inx                         ; the next in turn
        txa
        and #7
        sta turn
        jmp next
out:    inc left
next:   ldy zp_wk_i
        iny
        jmp first
done:   lda enable
        sta base + P_ENABLE
        lda highs
        sta base + P_X_HIGHS
        lda events
        sta base + P_COUNT
        rts
.endmacro

alloc_a: ALLOC PROG_A
alloc_b: ALLOC PROG_B

; The leader's pixel: a = x, b = y (2 bytes each).
leader_px:
        lda wk_pos
        sta zp_wk_a
        lda wk_pos + 1
        sta zp_wk_a + 1
        lda wk_pos + 2
        sta zp_wk_b
        lda wk_pos + 3
        sta zp_wk_b + 1
        ldx #4
:       lsr zp_wk_a + 1
        ror zp_wk_a
        lsr zp_wk_b + 1
        ror zp_wk_b
        dex
        bne :-
        rts

        .segment "DATA"

nears:  .word SPRITE_DX - SPRITE_X_MIN, SPRITE_DY - SPRITE_Y_MIN
lims:   .word SPRITE_X_MAX - SPRITE_DX, SPRITE_Y_MAX - SPRITE_DY
gap_back:
        .repeat PARTY_SIZE, k
        .byte GAP * k
        .endrepeat
bit_of: .byte 1, 2, 4, 8, 16, 32, 64, 128

        .segment "BSS"

prog_next:  .res 1              ; the program last made: 0 PROG_A, 1 PROG_B
prog_left:  .res 1              ; figures left out (the program last made)
left = prog_left

head:       .res 1              ; the trail: the newest entry
trail_len:  .res 1
trail_xl:   .res TRAIL
trail_xh:   .res TRAIL
trail_y:    .res TRAIL
trail_yh:   .res TRAIL
steps:      .res 1              ; frames the leader has moved
moved:      .res 1              ; this one?
last_xl:    .res PARTY_SIZE     ; where each traveler was last drawn
last_xh:    .res PARTY_SIZE
facing:     .res PARTY_SIZE     ; 0 right, 1 left
party_k:    .res 1
off_x:      .res 2              ; this frame's SPRITE_DX - the camera's x
off_y:      .res 2              ; and SPRITE_DY - its y
row_first:  .res SQUARES_Y + 2  ; each row's first figure (they're in order down)
fig_end:    .res 1              ; the figure past the rows in sight
win_x0:     .res 2              ; the view's window on the area (window): x0, y0...
win_y0:     .res 2
win_x1:     .res 2              ; ...x1, y1
win_y1:     .res 2
sq_x0:      .res 4              ; the same in squares (a byte each, kept 2 apart like the
sq_y0 = sq_x0 + 2               ; pixels, so window_squares indexes them alike): x0, y0...
sq_x1:      .res 4              ; ...x1, y1
sq_y1 = sq_x1 + 2
lead_xl:    .res 1              ; the leader's x + 9, the foes facing it
lead_xh:    .res 1
fig_xl:     .res FIGURES_MAX    ; the floor's figures: their pixels, and kinds
fig_xh:     .res FIGURES_MAX
fig_yl:     .res FIGURES_MAX
fig_yh:     .res FIGURES_MAX
fig_kind:   .res FIGURES_MAX
fig_ptr:    .res FIGURES_MAX    ; their first shape's pointer, and colour
fig_col:    .res FIGURES_MAX
fig_sx:     .res FIGURES_MAX    ; and their squares
fig_sy:     .res FIGURES_MAX
count:      .res 1              ; the list: figures in sight
list_xl:    .res SHOWN_MAX
list_xh:    .res SHOWN_MAX
list_y:     .res SHOWN_MAX
list_ptr:   .res SHOWN_MAX
list_col:   .res SHOWN_MAX
order:      .res SHOWN_MAX
porder:     .res PARTY_SIZE     ; the party's, sorted
party_n:    .res 1              ; how many of the list are the party's
out_k:      .res 1              ; merge: the next of order[]
free:       .res 8              ; the sprites: the line each is free from
last_y:     .res 8              ; and the top of the last figure each showed
slot:       .res 1
turn:       .res 1              ; the next sprite in turn
enable:     .res 1              ; the program being made: its sprites on...
highs:      .res 1              ; ...their x's ninth bits...
events:     .res 1              ; ...how many events
