; The view (docs/frames.md): rows 0-15, the map in tiles of 4 x 4 characters, ten squares
; by four, in the multicolour characters at VIEW_CHARS (screen.s).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export view_tile, view_map
        .import tiles, row_lo, row_hi

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; view_tile: a tile at a square of the view.
;   Takes:   A = the tile (0-7); X = the square's column (0-9); Y = its row (0-3).
;   Before:  $01 = $35; the tiles in (screen.s).
;   Changes: A, X, Y; zp_tile_at, zp_tile_col; zp_t0, zp_t1.
view_tile:
        asl a                       ; the tile's record: 32 bytes each
        asl a
        asl a
        asl a
        asl a
        sta zp_t0
        tya                         ; its top row of characters: 4 x the square's row
        asl a
        asl a
        tay
        txa                         ; its left column: 4 x the square's column
        asl a
        asl a
        clc
        adc row_lo, y
        sta zp_tile_at
        sta zp_tile_col
        lda row_hi, y
        adc #>(VIEW_SCREEN - TEXT_SCREEN)
        sta zp_tile_at + 1
        clc
        adc #>VIEW_TO_COLOUR
        sta zp_tile_col + 1
        ldx zp_t0
        lda #4
        sta zp_t1                   ; rows of characters to go
@row:   ldy #0
@cell:  lda tiles, x
        sta (zp_tile_at), y
        lda tiles + 16, x
        sta (zp_tile_col), y
        inx
        iny
        cpy #4
        bne @cell
        lda zp_tile_at              ; down a row of characters (the two pointers keep
        clc                         ; the same low byte)
        adc #COLS
        sta zp_tile_at
        sta zp_tile_col
        bcc @same
        inc zp_tile_at + 1
        inc zp_tile_col + 1
@same:  dec zp_t1
        bne @row
        rts

; ----------------------------------------------------------------------------------------
; view_map: the whole view from a map of 10 x 4 tiles, row by row.
;   Takes:   A/X = the map (low/high), 40 bytes.
;   Before:  $01 = $35; the tiles in.
;   Changes: A, X, Y; zp_src; zp_tile_at, zp_tile_col; zp_t0-zp_t3.
view_map:
        sta zp_src
        stx zp_src + 1
        lda #0
        sta zp_t3                   ; the square: 0-39
@square:
        ldy zp_t3
        lda (zp_src), y
        pha
        tya                         ; its column and row: square mod 10, square / 10
        ldy #0
@tens:  cmp #10
        bcc @split
        sbc #10
        iny
        bne @tens                   ; (always)
@split: tax
        pla
        jsr view_tile
        inc zp_t3
        lda zp_t3
        cmp #40
        bne @square
        rts
