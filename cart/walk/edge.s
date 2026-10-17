; Drawing the screen's characters from the floor (docs/walk.md, "The scroller"), a row or a
; column at a time; after a step, only the new edges (a column, a row, or both); at the
; start, every row. (The colours are copied a row at a time from the colour map: colours.s.)
;
; The screen's (column c, row r) shows the area's character (wk_ncx + c, wk_ncy + r): the
; square's tile's quarter (1 + 4 tile + 2 (row & 1) + (column & 1)), its colour the tile's.
; The camera keeps every column and row on the area (its most: camera.s), so nothing is
; checked.

        .include "zp.inc"
        .include "walk.inc"

        .export edge_base, wk_ncx, wk_ncy, edges, draw_all, maps_build, wk_w, wk_h
        .import floor, squares, sq_row_lo, sq_row_hi, wk_dir

        .segment "CODE"

; ----------------------------------------------------------------------------------------
; edges: the new edges for the step under way (camera.s's wk_dir): a column on the side
; it moved to, a row on the side it moved to.
;   Takes:   edge_base (the screen), wk_ncx, wk_ncy, and wk_dir (camera.s).
;   Changes: A, X, Y, zp_wk_out, zp_wk_ptr, zp_wk_t, zp_wk_mx.
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
; maps_build: the floor's size (wk_w, wk_h), and each row of its squares on its page of
; COLOUR_MAP: the square's colour twice (its two columns of characters) from the page's
; start, the squares themselves from 2 w (sq_row_lo, sq_row_hi).
;   Before:  the squares where the program loaded them (floor.s), not yet written over.
;   Changes: A, X, Y, zp_wk_ptr, zp_wk_out, zp_wk_src, zp_wk_mx, zp_wk_my.
maps_build:
        lda floor + FL_SIZE
        sta wk_w
        lda floor + FL_SIZE + 1
        sta wk_h
        lda #<squares
        sta zp_wk_src
        lda #>squares
        sta zp_wk_src + 1
        lda #0
        sta zp_wk_out
        sta zp_wk_my                ; the square's row
@row:   ldx zp_wk_my
        txa                         ; its page
        clc
        adc #>COLOUR_MAP
        sta zp_wk_out + 1
        sta zp_wk_ptr + 1
        sta sq_row_hi, x
        lda wk_w
        asl a
        sta zp_wk_ptr               ; its squares from 2 w
        sta sq_row_lo, x
        lda #0
        sta zp_wk_mx                ; the square
@sq:    ldy zp_wk_mx
        lda (zp_wk_src), y
        sta (zp_wk_ptr), y
        and #TILE_MASK
        tax
        tya                         ; its colours: 2 x and 2 x + 1
        asl a
        tay
        lda floor + FL_TILE_COLOUR, x
        sta (zp_wk_out), y
        iny
        sta (zp_wk_out), y
        inc zp_wk_mx
        lda zp_wk_mx
        cmp wk_w
        bne @sq
        clc                         ; the next row of the squares' file
        adc zp_wk_src
        sta zp_wk_src
        bcc :+
        inc zp_wk_src + 1
:       inc zp_wk_my
        lda zp_wk_my
        cmp wk_h
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

; Row A of the screen: the area's row of characters wk_ncy + A, from column wk_ncx, worked
; out from its squares: square t's quarter is 1 + 4 t + 2 (a lower half) + 1 (a right).
; (4 t is below 128, so the carry's clear for the adds.)
draw_row:
        tax
        lda edge_base               ; where it goes: the screen's row, X the column
        clc
        adc row40_lo, x
        sta @o1 + 1
        sta @o2 + 1
        sta @o3 + 1
        lda edge_base + 1
        adc row40_hi, x
        sta @o1 + 2
        sta @o2 + 2
        sta @o3 + 2
        txa
        clc
        adc wk_ncy                  ; the area's row of characters
        lsr a                       ; its row of squares; the carry, a lower half
        tay
        lda #1
        bcc :+
        lda #3
:       sta zp_wk_t                 ; 1 + 2 (a lower half)
        lda sq_row_lo, y
        sta zp_wk_ptr
        lda sq_row_hi, y
        sta zp_wk_ptr + 1
        ldx #0                      ; the screen's column
        lda wk_ncx
        lsr a
        tay                         ; the square
        bcc @pair                   ; on a square's left half: pairs from here
        lda (zp_wk_ptr), y          ; else the first's a right half
        and #TILE_MASK
        asl a
        asl a
        adc zp_wk_t
        adc #1
@o1:    sta $FFFF, x
        inx
        iny
@pair:  lda (zp_wk_ptr), y
        and #TILE_MASK
        asl a
        asl a
        adc zp_wk_t
@o2:    sta $FFFF, x
        inx
        cpx #COLS
        beq @done
        adc #1
@o3:    sta $FFFF, x
        inx
        iny
        cpx #COLS
        bne @pair
@done:  rts

; Column A of the screen: 25 characters down the area's column wk_ncx + A, from row wk_ncy,
; worked out from its squares, a square at a time (its upper and lower halves from one
; read; a row of squares is a page, the next is the page after).
draw_col:
        tax
        clc
        adc wk_ncx                  ; the area's column of characters
        lsr a
        sta zp_wk_mx                ; its square
        lda #1
        adc #0
        sta zp_wk_t                 ; 1 + 1 (a right half)
        txa                         ; where it goes: the screen's column
        clc
        adc edge_base
        sta zp_wk_out
        lda edge_base + 1
        adc #0
        sta zp_wk_out + 1
        lda wk_ncy
        lsr a                       ; the first row of squares; the carry, a lower half
        tax
        lda sq_row_lo, x
        sta zp_wk_ptr
        lda sq_row_hi, x
        sta zp_wk_ptr + 1
        ldx #ROWS                   ; the characters left
        bcc @pair
        ldy zp_wk_mx                ; it starts on a lower half: that alone first
        lda (zp_wk_ptr), y
        and #TILE_MASK
        asl a
        asl a
        adc zp_wk_t
        adc #2
        ldy #0
        sta (zp_wk_out), y
        inc zp_wk_ptr + 1
        lda zp_wk_out
        clc
        adc #COLS
        sta zp_wk_out
        bcc :+
        inc zp_wk_out + 1
:       dex
@pair:  ldy zp_wk_mx                ; a square's upper half, then (if there's room) its lower
        lda (zp_wk_ptr), y
        and #TILE_MASK
        asl a
        asl a
        adc zp_wk_t
        ldy #0
        sta (zp_wk_out), y
        dex
        beq @done
        adc #2
        ldy #COLS
        sta (zp_wk_out), y
        inc zp_wk_ptr + 1
        lda zp_wk_out
        clc
        adc #2 * COLS
        sta zp_wk_out
        bcc :+
        inc zp_wk_out + 1
:       dex
        bne @pair
@done:  rts

        .segment "DATA"

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
wk_w:       .res 1              ; the floor's size, in squares
wk_h:       .res 1
wk_ncx:     .res 1              ; the area's character at its top left
wk_ncy:     .res 1
