; A fight's setup on an open floor (docs/open-floors.md, "Where the fight is"; docs/walk.md,
; "The fight"): when a band has seen the party, the window the fight is on (16 x 8 inside
; the floor, holding the band and the leader, its middle nearest the middle between them;
; round the band if they can't both fit), its squares' terrain, where the party stands
; (fanned out round the leader) and the band's foes on it: the record a battle engine will
; take (fight_rec), and what the walk needs to show it (fight_mid, fight_px, fight_py,
; fight_band_x). Held to tools/rooms/rooms.py's fight_window and fight_places (themselves
; rooms.js's) by tests/walk/run_walk.py. It runs with seeing's checks (watch.s), in the
; frame loop's time to spare, so it uses seeing's zero page.

        .include "zp.inc"
        .include "walk.inc"

        .export fight_setup, fight_rec, fight_mid, fight_px, fight_py, fight_band_x
        .import floor, sq_row_lo, sq_row_hi, terrain, wk_w, wk_h, see_x, see_y, see_fight
        .import see_yield

WIN_W           = 16            ; the window: the battle's map
WIN_H           = 8
STANDS          = %01011001     ; terrains a traveler can stand on: open, rough, cover, high
; fight_rec: the window's square x, y; its terrain (16 x 8, a row at a time); the party's
; squares on it (4 x, y, in marching order); how many foes, then each one's x, y and kind.
REC_MAP         = 2
REC_PLACES      = REC_MAP + WIN_W * WIN_H
REC_FOES        = REC_PLACES + 2 * PARTY_SIZE

        .segment "SEEING"         ; (run from $E000: walk.cfg)

; ----------------------------------------------------------------------------------------
; fight_setup: band see_fight - 1 has seen the party, the leader on (see_x, see_y).
;   Before:  see_fight > 0.
;   After:   fight_rec, fight_mid, fight_px, fight_py, fight_band_x.
;   Changes: A, X, Y; zp_see_*.
fight_setup:
        ; The band's foes: their squares and kinds, and the band's bounds.
        ldx see_fight
        dex
        stx band
        lda #0
        sta n
        lda #$FF
        sta minx
        sta miny
        lda #0
        sta maxx
        sta maxy
        ldx #0                      ; the figure
        ldy #0                      ; its record
@fig:   cpx floor + FL_FIGURES
        beq @got
        lda floor + FL_FIG_BAND, x
        cmp band
        bne @nextf
        stx zp_see_t
        ldx n
        lda floor + FL_FIGURES + 1, y
        sta fx, x
        cmp minx
        bcs :+
        sta minx
:       cmp maxx
        bcc :+
        sta maxx
:       lda floor + FL_FIGURES + 2, y
        sta fy, x
        cmp miny
        bcs :+
        sta miny
:       cmp maxy
        bcc :+
        sta maxy
:       lda floor + FL_FIGURES + 3, y
        sta fk, x
        inc n
        ldx zp_see_t
@nextf: iny
        iny
        iny
        inx
        bne @fig                    ; (always: 80 figures at most)
@got:   jsr window
        jsr map
        jsr places
        jmp outputs

; ----------------------------------------------------------------------------------------
; The window: of every x0, y0 that holds the band's foes, the first (rows down, then
; across) with the least k = (the leader outside it: OUTSIDE) + |4 x0 + 2 W - aim x| +
; |4 y0 + 2 H - aim y|, where the aim is (in quarters) the middle between the band's
; middle and the leader if it holds the leader, else the band's middle. (rooms.py's
; fight_window.)
window:
        lda minx                    ; twice the band's middle
        clc
        adc maxx
        sta mx2
        lda miny
        clc
        adc maxy
        sta my2
        lda see_x                   ; 4 x the middle between: mx2 + 2 leader
        asl a
        sta zp_see_a
        lda #0
        rol a
        sta zp_see_a + 1
        lda zp_see_a
        clc
        adc mx2
        sta cx4
        lda zp_see_a + 1
        adc #0
        sta cx4 + 1
        lda see_y
        asl a
        clc                         ; (no carry: y < 128)
        adc my2
        sta cy4
        lda #0
        adc #0
        sta cy4 + 1
        lda mx2                     ; 4 x the band's middle
        asl a
        sta mx2_4
        lda #0
        rol a
        sta mx2_4 + 1
        lda my2
        asl a
        sta my2_4
        lda #0
        rol a
        sta my2_4 + 1
        ; The x0 that hold the band: max(0, maxx - (W - 1)) to min(minx, w - W).
        lda maxx
        sec
        sbc #WIN_W - 1
        bcs :+
        lda #0
:       sta xlo
        lda wk_w
        sec
        sbc #WIN_W
        cmp minx
        bcc :+
        lda minx
:       sta xhi
        lda maxy
        sec
        sbc #WIN_H - 1
        bcs :+
        lda #0
:       sta ylo
        lda wk_h
        sec
        sbc #WIN_H
        cmp miny
        bcc :+
        lda miny
:       sta yhi
        lda #0                      ; none yet (none at all: 0, 0)
        sta wx
        sta wy
        lda xlo                     ; (a band wider than the window: none)
        cmp xhi
        bcc :+
        beq :+
        rts
:       lda ylo
        cmp yhi
        bcc :+
        beq :+
        rts
:       ; k's parts are each one axis's: so each x0's (and each y0's) are worked out once:
        ; whether the window holds the leader that way, and its term aimed either way
        ; (each within 32: the band inside the window). The leader inside both ways is
        ; ranked first, then the terms' sum: OUTSIDE's order, in a byte.
        ldx #0
        lda #2 * WIN_W
        ldy see_x
        jsr axis
        ldx #2
        lda #2 * WIN_H
        ldy see_y
        jsr axis
        lda #$FF
        sta best + 1
        lda ylo
        sta y0
@row:   jsr see_yield
        lda xlo
        sta x0
@cand:  lda y0                      ; X = x0's entry, Y = y0's
        sec
        sbc ylo
        tay
        lda x0
        sec
        sbc xlo
        tax
        lda in_x, x
        and in_y, y
        beq @out
        lda #0                      ; inside: rank 0, the middle between
        sta zp_see_a + 1
        lda term_in_x, x
        clc
        adc term_in_y, y
        jmp @k
@out:   lda #1                      ; outside: rank 1, the band's middle
        sta zp_see_a + 1
        lda term_out_x, x
        clc
        adc term_out_y, y
@k:     sta zp_see_a
        lda zp_see_a + 1            ; k < best: this one
        cmp best + 1
        bcc @take
        bne @next
        lda zp_see_a
        cmp best
        bcs @next
@take:  lda zp_see_a
        sta best
        lda zp_see_a + 1
        sta best + 1
        lda x0
        sta wx
        lda y0
        sta wy
@next:  lda x0
        cmp xhi
        inc x0
        bcc @cand
        lda y0
        cmp yhi
        inc y0
        bcc @row
@done:  rts

; One axis's parts (X = 0 across, 2 down; A = 2 W or 2 H; Y = the leader that way): for
; each window start v from lo to hi, whether it holds the leader (in_), |4 v + A - 4 x the
; middle between| (term_in_) and |4 v + A - 4 x the band's middle| (term_out_).
axis:   sta zp_see_t                ; 2 W
        sty zp_see_rate             ; the leader
        lda xlo, x                  ; (xlo, xhi, ylo, yhi: X = 2 picks the y's)
        sta x0
        lda #0
        sta y0                      ; (the entry)
@v:     lda x0                      ; holds the leader: v <= it < v + W
        ldy #0
        cmp zp_see_rate
        beq :+
        bcs @not
:       lda zp_see_rate
        sec
        sbc x0
        cmp side, x
        bcs @not
        iny
@not:   tya
        ldy y0
        cpx #0
        bne :+
        sta in_x, y
        jmp :++
:       sta in_y, y
:       lda x0                      ; 4 v + 2 W, 16 bits
        sta zp_see_row
        lda #0
        sta zp_see_row + 1
        asl zp_see_row
        rol zp_see_row + 1
        asl zp_see_row
        rol zp_see_row + 1
        lda zp_see_row
        clc
        adc zp_see_t
        sta zp_see_row
        bcc :+
        inc zp_see_row + 1
:       lda cx4, x                  ; |.. - the middle between|
        ldy cx4 + 1, x
        jsr absdiff
        ldy y0
        cpx #0
        bne :+
        sta term_in_x, y
        jmp :++
:       sta term_in_y, y
:       lda mx2_4, x                ; |.. - the band's middle|
        ldy mx2_4 + 1, x
        jsr absdiff
        ldy y0
        cpx #0
        bne :+
        sta term_out_x, y
        jmp :++
:       sta term_out_y, y
:       inc y0
        lda x0
        cmp xhi, x
        inc x0
        bcs :+
        jmp @v
:       rts

; A = |zp_see_row - Y:A|'s low byte (it's within 255 here). Keeps X.
absdiff:
        sta zp_see_a
        sty zp_see_a + 1
        lda zp_see_row
        sec
        sbc zp_see_a
        sta zp_see_a
        lda zp_see_row + 1
        sbc zp_see_a + 1
        bpl :+
        lda zp_see_a
        eor #$FF
        clc
        adc #1
        rts
:       lda zp_see_a
        rts

; ----------------------------------------------------------------------------------------
; The window's terrain into the record, and which of its squares a foe is on.
map:    lda wx
        sta fight_rec
        lda wy
        sta fight_rec + 1
        ldx #WIN_W * WIN_H - 1
        lda #0
:       sta foe_at, x
        sta seen, x
        dex
        bpl :-
        lda #0
        sta zp_see_t                ; the window's row
        ldx #0                      ; the record's square
@row:   jsr see_yield
        lda wy
        clc
        adc zp_see_t
        tay
        lda sq_row_lo, y
        clc
        adc wx
        sta zp_see_row
        lda sq_row_hi, y
        adc #0
        sta zp_see_row + 1
        ldy #0
@sq:    lda (zp_see_row), y
        and #TILE_MASK
        stx zp_see_rate             ; (scratch here)
        tax
        lda terrain, x
        ldx zp_see_rate
        sta fight_rec + REC_MAP, x
        inx
        iny
        cpy #WIN_W
        bne @sq
        inc zp_see_t
        lda zp_see_t
        cmp #WIN_H
        bne @row
        ; The foes, on the window: in the record, and marked.
        lda n
        sta fight_rec + REC_FOES
        ldx #0
        ldy #0
@foe:   cpx n
        beq @done
        lda fx, x
        sec
        sbc wx
        sta fx, x
        sta fight_rec + REC_FOES + 1, y
        lda fy, x
        sec
        sbc wy
        sta fy, x
        sta fight_rec + REC_FOES + 2, y
        lda fk, x
        sta fight_rec + REC_FOES + 3, y
        stx zp_see_t
        lda fy, x                   ; foe_at[16 y + x]
        asl a
        asl a
        asl a
        asl a
        ora fx, x
        tax
        inc foe_at, x
        ldx zp_see_t
        iny
        iny
        iny
        inx
        bne @foe                    ; (always)
@done:  rts

; ----------------------------------------------------------------------------------------
; Where the party stands (rooms.py's fight_places): fanned out round the leader (kept
; inside the window), breadth first, N E S W NE SE SW NW, on squares that can be stood on
; with no foe; the leader's own left out if it can't be (or a foe's on it); the last place
; again if there aren't four.
places: lda see_x                   ; the leader, kept inside
        sec
        sbc wx
        bcs :+
        lda #0
:       cmp #WIN_W
        bcc :+
        lda #WIN_W - 1
:       sta lx
        lda see_y
        sec
        sbc wy
        bcs :+
        lda #0
:       cmp #WIN_H
        bcc :+
        lda #WIN_H - 1
:       sta ly
        asl a                       ; its square
        asl a
        asl a
        asl a
        ora lx
        sta fan
        sta queue
        tax
        inc seen, x
        lda #1
        sta nfan
        sta qtail
        lda #0
        sta qhead
@pop:   jsr see_yield
        lda nfan                    ; while there's more to look from and fewer than 5
        cmp #PARTY_SIZE + 1
        bcs @fanned
        ldx qhead
        cpx qtail
        beq @fanned
        lda queue, x
        inc qhead
        sta from
        lda #0
        sta dir
@way:   lda nfan
        cmp #PARTY_SIZE + 1
        bcs @fanned
        lda from                    ; the square that way, if on the window
        and #WIN_W - 1
        ldx dir
        clc
        adc fan_dx, x
        cmp #WIN_W
        bcs @skip                   ; (off either side: -1 is 255)
        sta zp_see_t
        lda from
        lsr a
        lsr a
        lsr a
        lsr a
        clc
        adc fan_dy, x
        cmp #WIN_H
        bcs @skip
        asl a
        asl a
        asl a
        asl a
        ora zp_see_t
        tax
        lda seen, x
        bne @skip
        inc seen, x
        lda foe_at, x
        bne @skip
        jsr stands
        beq @skip
        txa
        ldy nfan
        sta fan, y
        inc nfan
        ldy qtail
        sta queue, y
        inc qtail
@skip:  inc dir
        lda dir
        cmp #8
        bne @way
        jmp @pop
@fanned:
        ldx fan                     ; the leader's own: left out if it can't be stood on
        lda nfan
        cmp #2
        bcc @keep
        lda foe_at, x
        bne @drop
        jsr stands
        bne @keep
@drop:  ldx #0
:       lda fan + 1, x
        sta fan, x
        inx
        cpx #PARTY_SIZE
        bne :-
        dec nfan
@keep:  ldx #0                      ; into the record: the last again if there aren't 4
        ldy #0
@place: txa
        cmp nfan
        bcc :+
        ldx nfan
        dex
:       lda fan, x
        and #WIN_W - 1
        sta fight_rec + REC_PLACES, y
        lda fan, x
        lsr a
        lsr a
        lsr a
        lsr a
        sta fight_rec + REC_PLACES + 1, y
        iny
        iny
        tya
        lsr a
        tax
        cpx #PARTY_SIZE
        bne @place
        rts

; Z clear if square X of the window (16 y + x) can be stood on. Keeps X, Y.
stands: lda fight_rec + REC_MAP, x
        sty zp_see_t
        tay
        lda stand_bit, y
        ldy zp_see_t
        and #STANDS
        rts

; ----------------------------------------------------------------------------------------
; What the walk shows: the camera's aim (the window's middle, less 8: as a leader's pixel
; is to its middle), the travelers' places in pixels, the band's middle across (x 16).
outputs:
        lda wx                      ; 16 x0 + W x 8 - 8
        ldy #WIN_W * 8 - 8
        ldx #0
        jsr pixel
        lda wy
        ldy #WIN_H * 8 - 8
        ldx #2
        jsr pixel
        ldx #0
@trav:  stx zp_see_t
        txa
        asl a
        tay
        lda fight_rec + REC_PLACES, y
        clc
        adc wx
        jsr sixteen
        ldx zp_see_t
        sta fight_px, x
        lda zp_see_a + 1
        sta fight_px + PARTY_SIZE, x
        lda fight_rec + REC_PLACES + 1, y
        clc
        adc wy
        jsr sixteen
        ldx zp_see_t
        sta fight_py, x
        lda zp_see_a + 1
        sta fight_py + PARTY_SIZE, x
        inx
        cpx #PARTY_SIZE
        bne @trav
        lda mx2                     ; (minx + maxx) x 8
        sta fight_band_x
        lda #0
        .repeat 3
        asl fight_band_x
        rol a
        .endrepeat
        sta fight_band_x + 1
        rts

; fight_mid[X] (16 bits) = 16 A + Y.
pixel:  jsr sixteen
        sty zp_see_t
        clc
        adc zp_see_t
        sta fight_mid, x
        lda zp_see_a + 1
        adc #0
        sta fight_mid + 1, x
        rts

; A = 16 A's low byte, zp_see_a + 1 its high. Keeps X, Y.
sixteen:
        sta zp_see_a
        lda #0
        sta zp_see_a + 1
        .repeat 4
        asl zp_see_a
        rol zp_see_a + 1
        .endrepeat
        lda zp_see_a
        rts

side:       .byte WIN_W, 0, WIN_H                    ; (by X: 0 across, 2 down)
fan_dx:     .byte 0, 1, 0, $FF, 1, 1, $FF, $FF          ; N E S W NE SE SW NW
fan_dy:     .byte $FF, 0, 1, 0, $FF, 1, 1, $FF
stand_bit:  .byte $01, $02, $04, $08, $10, $20, $40, $80

        .segment "BSS"

fight_rec:      .res REC_FOES + 1 + 3 * FIGHT_FOES_MAX
fight_mid:      .res 4                  ; the camera's aim: x, y (pixels, as a leader's)
fight_px:       .res 2 * PARTY_SIZE     ; each traveler's place: x's low bytes, then highs
fight_py:       .res 2 * PARTY_SIZE     ; and y's
fight_band_x:   .res 2                  ; the band's middle across, x 16 (pixels)
band:           .res 1
n:              .res 1                  ; the band's foes
fx:             .res FIGHT_FOES_MAX
fy:             .res FIGHT_FOES_MAX
fk:             .res FIGHT_FOES_MAX
minx:           .res 1
maxx:           .res 1
miny:           .res 1
maxy:           .res 1
mx2:            .res 1
my2:            .res 1
cx4:            .res 2              ; 4 x the middle between, across (cy4: down)
cy4:            .res 2
mx2_4:          .res 2              ; 4 x the band's middle, across (my2_4: down)
my2_4:          .res 2
xlo:            .res 1              ; the window's starts that hold the band (ylo, yhi: down)
xhi:            .res 1
ylo:            .res 1
yhi:            .res 1
in_x:           .res WIN_W          ; each x0: holds the leader across; its two terms
term_in_x:      .res WIN_W
term_out_x:     .res WIN_W
in_y:           .res WIN_H
term_in_y:      .res WIN_H
term_out_y:     .res WIN_H
x0:             .res 1
y0:             .res 1
wx:             .res 1
wy:             .res 1
best:           .res 2
lx:             .res 1
ly:             .res 1
foe_at:         .res WIN_W * WIN_H
seen:           .res WIN_W * WIN_H
queue:          .res WIN_W * WIN_H
qhead:          .res 1
qtail:          .res 1
from:           .res 1
dir:            .res 1
fan:            .res PARTY_SIZE + 1
nfan:           .res 1
