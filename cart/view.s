; The view (docs/frames.md, docs/cartridge.md "The view"): rows 0-15, the map in squares
; of 16 x 16 pixels, each a tile of 2 x 2 multicolour characters (VIEW_CHARS, screen.s),
; 20 squares across and 8 down. A square's place is all shifts: its characters' column
; is 2 x its column, their row 2 x its row.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export view_tile, view_map
        .import tiles, row_lo, row_hi

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; view_tile: a tile at a square of the view.
;   Takes:   A = the tile (0-7); X = the square's column (0-19); Y = its row (0-7).
;   Before:  $01 = $35; the tiles in (screen.s).
;   Changes: A, X, Y; zp_tile_at, zp_tile_col.
view_tile:
        asl a                       ; its record: 8 bytes
        asl a
        asl a
        pha
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
        pla
        tax
        ldy #0                      ; the top two
        jsr two
        ldy #COLS                   ; and the two under them
two:    lda tiles, x
        sta (zp_tile_at), y
        lda tiles + 4, x
        sta (zp_tile_col), y
        inx
        iny
        lda tiles, x
        sta (zp_tile_at), y
        lda tiles + 4, x
        sta (zp_tile_col), y
        inx
        rts

; ----------------------------------------------------------------------------------------
; view_map: the whole view from a map of 20 x 8 tiles, row by row.
;   Takes:   A/X = the map (low/high), 160 bytes.
;   Before:  $01 = $35; the tiles in.
;   Changes: A, X, Y; zp_tile_at, zp_tile_col; zp_t0-zp_t3 (zp_t2-zp_t3: the map's row).
view_map:
        sta zp_t2
        stx zp_t3
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
