; The view (docs/frames.md, docs/cartridge.md "The view"): rows 0-15, the map in squares
; of 16 x 16 pixels, each a tile of 2 x 2 multicolour characters (VIEW_CHARS, screen.s),
; 20 squares across and 8 down. A square's place is all shifts: its characters' column
; is 2 x its column, their row 2 x its row.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

VIEW_PLAIN      = 0                 ; view_set
VIEW_MARKED     = 1
VIEW_CURSOR     = 2

        .export view_tile, view_square, view_map, view_set, view_ink
        .import tiles, row_lo, row_hi, view_mode

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; view_tile: a tile at a square of the view.
;   Takes:   A = the tile (0-7); X = the square's column (0-19); Y = its row (0-7).
;   Before:  $01 = $35; the tiles in (screen.s).
;   Changes: A, X, Y; zp_tile_at, zp_tile_col.
view_tile:
        pha
        lda #VIEW_PLAIN
        sta view_set
        lda #0
        sta view_ink
        pla
        ; (on into view_square)

; view_square: a tile at a square of the view, as view_set says: plain, with the reach
; dot, or with the cursor; in its own colours, or with view_ink for all four characters
; (the cursor's colour, multicolour). Tile $FF: the square blank, black.
;   Takes:   A = the tile (0-7, or $FF); X = the square's column (0-19); Y = its row (0-7);
;            view_set, view_ink.
;   Before:  $01 = $35; the tiles in (screen.s).
;   Changes: A, X, Y; zp_tile_at, zp_tile_col.
view_square:
        sta square_tile
        tya                         ; its top row of characters: 2 x the square's row
        asl a
        tay
        txa                         ; its left column: 2 x the square's column
        asl a
        clc
        adc row_lo, y
        sta zp_tile_at
        sta zp_tile_col             ; (the colours' low byte is the same)
        lda row_hi, y
        adc #>(VIEW_SCREEN - TEXT_SCREEN)
        sta zp_tile_at + 1
        clc
        adc #>VIEW_TO_COLOUR
        sta zp_tile_col + 1
        ldx #0                      ; its four characters and colours
        lda square_tile
        cmp #$FF
        bne @tile
@blank: lda #0
        sta cells, x
        sta inks, x
        inx
        cpx #4
        bne @blank
        beq @put                    ; (always)
@tile:  asl a                       ; its record: 8 bytes
        asl a
        asl a
        tay
@ink:   lda tiles + 4, y            ; the colours
        sta inks, x
        lda view_ink
        beq @own
        sta inks, x
@own:   iny
        inx
        cpx #4
        bne @ink
        lda square_tile             ; the characters: plain, or the 4 marked or cursor ones
        asl a
        asl a
        ldx view_set
        cpx #VIEW_PLAIN
        bne @set
        asl a
        tay
        jmp @chars
@set:   clc
        adc set_at, x
        tay
@chars: ldx #0
@char:  lda tiles, y
        sta cells, x
        iny
        inx
        cpx #4
        bne @char
@put:   ldy #0                      ; the top two, and the two under them
        ldx #0
        jsr two
        ldy #COLS
two:    lda cells, x
        sta (zp_tile_at), y
        lda inks, x
        sta (zp_tile_col), y
        inx
        iny
        lda cells, x
        sta (zp_tile_at), y
        lda inks, x
        sta (zp_tile_col), y
        inx
        rts

; ----------------------------------------------------------------------------------------
; view_map: the whole view from a map of 20 x 8 tiles, row by row.
;   Takes:   A/X = the map (low/high), 160 bytes.
;   Before:  $01 = $35; the tiles in.
;   After:   the view shows the map's characters, from the next frame.
;   Changes: A, X, Y; zp_tile_at, zp_tile_col; zp_t0-zp_t3 (zp_t2-zp_t3: the map's row).
view_map:
        sta zp_t2
        stx zp_t3
        lda #MEM_VIEW
        ldx #CTRL1_TEXT
        ldy #BLACK
        jsr view_mode
        lda #0
        sta zp_t1                   ; the row
@row:   lda #0
        sta zp_t0                   ; the column
@square:
        ldy zp_t0
        lda (zp_t2), y
        ldx zp_t0
        ldy zp_t1
        jsr view_tile
        inc zp_t0
        lda zp_t0
        cmp #SQUARES_ACROSS
        bne @square
        lda zp_t2                   ; on to the map's next row
        clc
        adc #SQUARES_ACROSS
        sta zp_t2
        bcc @next
        inc zp_t3
@next:  inc zp_t1
        lda zp_t1
        cmp #SQUARES_DOWN
        bne @row
        rts

; Where the marked and the cursor's characters start in the tiles' table (view_set 1, 2).
set_at: .byte 0, TILES_MARKED, TILES_CURSOR

        .segment "BSS"
view_set:       .res 1              ; view_square: VIEW_PLAIN, _MARKED or _CURSOR
view_ink:       .res 1              ; and 0, or the colour for all four
square_tile:    .res 1
cells:          .res 4
inks:           .res 4
