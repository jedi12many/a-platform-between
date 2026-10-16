; Drawing the screen's characters from the floor (docs/walk.md, "The scroller"), a row or a
; column at a time; after a step, only the new edges (a column, a row, or both); at the
; start, every row. (The colours are copied a row at a time from the colour map: colours.s.)
;
; The screen's (column c, row r) shows the area's character (wk_ncx + c, wk_ncy + r): the
; square's tile's quarter (1 + 4 tile + 2 (row & 1) + (column & 1)), its colour the tile's.
; The camera keeps every column and row on the area (CAM_X_MAX, CAM_Y_MAX), so the maps
; are copied straight, never checked.

        .include "zp.inc"
        .include "walk.inc"

        .export edge_base, wk_ncx, wk_ncy, edges, draw_all, maps_build, map_lo, map_hi
        .import floor, sq_row_lo, sq_row_hi, wk_dir

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; edges: the new edges for the step under way (camera.s's wk_dir): a column on the side
; it moved to, a row on the side it moved to.
;   Takes:   edge_base (the screen), wk_ncx, wk_ncy, and wk_dir (camera.s).
;   Changes: A, X, Y, zp_wk_out, zp_wk_ptr.
edges:
        lda wk_dir
        beq @rows
        bmi :+
        lda #COLS - 1
        jsr draw_col
        jmp @rows
:       lda #0
        jsr draw_col
@rows:  lda wk_dir + 1
        beq @done
        bmi :+
        lda #ROWS - 1
        jmp draw_row
:       lda #0
        jmp draw_row
@done:  rts

; ----------------------------------------------------------------------------------------
; maps_build: CHAR_MAP and COLOUR_MAP from the floor's squares, each square's four
; characters (1 + 4 tile, + 1 right, + 2 below), and its colour twice (its two columns) on
; its row's page.
;   Changes: A, X, Y, zp_wk_ptr, zp_wk_out, zp_wk_src, zp_wk_mx, zp_wk_my, zp_wk_t.
maps_build:
        lda #0
        sta zp_wk_my                ; the square's row
@row:   ldx zp_wk_my
        lda sq_row_lo, x
        sta zp_wk_ptr
        lda sq_row_hi, x
        sta zp_wk_ptr + 1
        txa                         ; its characters' first row: 2 y
        asl a
        tax
        lda map_lo, x
        sta zp_wk_out
        lda map_hi, x
        sta zp_wk_out + 1
        lda #0                      ; its colours: the colour map's page y
        sta zp_wk_src
        lda zp_wk_my
        clc
        adc #>COLOUR_MAP
        sta zp_wk_src + 1
        lda #0
        sta zp_wk_mx                ; the square
@sq:    ldy zp_wk_mx
        lda (zp_wk_ptr), y
        and #TILE_MASK
        tax
        asl a
        asl a
        sta zp_wk_t                 ; 4 tile
        tya
        asl a
        tay                         ; its left character
        lda zp_wk_t
        clc
        adc #1
        sta (zp_wk_out), y
        adc #1
        iny
        sta (zp_wk_out), y
        lda floor + FL_TILE_COLOUR, x
        sta (zp_wk_src), y
        dey
        sta (zp_wk_src), y
        tya                         ; the row below: + 96
        clc
        adc #CHARS_X
        tay
        lda zp_wk_t
        adc #3
        sta (zp_wk_out), y
        adc #1
        iny
        sta (zp_wk_out), y
        inc zp_wk_mx
        lda zp_wk_mx
        cmp #SQUARES_X
        bne @sq
        inc zp_wk_my
        lda zp_wk_my
        cmp #SQUARES_Y
        bne @row
        rts

; ----------------------------------------------------------------------------------------
; draw_all: every row.
;   Takes and changes: as edges.
draw_all:
        lda #0
@row:   pha
        jsr draw_row
        pla
        clc
        adc #1
        cmp #ROWS
        bne @row
        rts

; Row A of the screen: 40 bytes of the map's row wk_ncy + A, from column wk_ncx.
draw_row:
        tax
        jsr row_out
        txa
        clc
        adc wk_ncy
        jsr map_at
        ldy #COLS - 1
:       lda (zp_wk_ptr), y
        sta (zp_wk_out), y
        dey
        bpl :-
        rts

; Column A of the screen: 25 bytes down the map's column wk_ncx + A.
draw_col:
        sta col
        lda wk_ncy
        jsr map_at
        ldx #0
        jsr row_out
        ldy col
        ldx #ROWS
@cell:  lda (zp_wk_ptr), y
        sta (zp_wk_out), y
        lda zp_wk_ptr               ; the map's next row
        clc
        adc #CHARS_X
        sta zp_wk_ptr
        bcc :+
        inc zp_wk_ptr + 1
        clc
:       lda zp_wk_out               ; the screen's
        adc #COLS
        sta zp_wk_out
        bcc :+
        inc zp_wk_out + 1
:       dex
        bne @cell
        rts

; zp_wk_ptr = the characters' map's row A, at column wk_ncx.
map_at:
        tay
        lda map_lo, y
        clc
        adc wk_ncx
        sta zp_wk_ptr
        lda map_hi, y
        adc #0
        sta zp_wk_ptr + 1
        rts

; zp_wk_out = edge_base + 40 X.
row_out:
        lda edge_base
        clc
        adc row40_lo, x
        sta zp_wk_out
        lda edge_base + 1
        adc row40_hi, x
        sta zp_wk_out + 1
        rts

        .segment "DATA"

map_lo:
        .repeat CHARS_Y, i
        .byte <(CHAR_MAP + i * CHARS_X)
        .endrepeat
map_hi:
        .repeat CHARS_Y, i
        .byte >(CHAR_MAP + i * CHARS_X)
        .endrepeat
row40_lo:
        .repeat ROWS, i
        .byte <(i * COLS)
        .endrepeat
row40_hi:
        .repeat ROWS, i
        .byte >(i * COLS)
        .endrepeat

        .segment "BSS"

edge_base:  .res 2              ; the screen drawn into
wk_ncx:     .res 1              ; the area's character at its top left
wk_ncy:     .res 1
col:        .res 1
row:        .res 1
