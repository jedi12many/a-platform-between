; The story's pictures in the view (docs/cartridge.md, "Pictures"): 160 x 96 multicolour
; bitmaps, the C64 version's (tools/c64pic.py), on the view's rows 2-13, with a black bar
; of two rows over and under them. Each is an asset (tools/cart/departure.py): its
; bitmap's 12 rows, each cell's two screen colours, each cell's colour-RAM colour, its
; background.
;
; The bars are colour-RAM pixels (%11) in black, never the background: the split changes
; the background to the frames' black while the lower bar is drawn (split.s).

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export picture_show
        .import asset_fetch, ram_copy, view_mode, picture_asset

PICTURE_ROWS    = 12
PICTURE_TOP     = 2                         ; its first row in the view
CELLS           = PICTURE_ROWS * COLS       ; 480
BITMAP_BYTES    = CELLS * 8                 ; 3840
PICTURE_SIZE    = BITMAP_BYTES + CELLS + CELLS + 1
BAR_BYTES       = PICTURE_TOP * COLS * 8    ; a bar's bitmap: 640
VIEW_CELLS      = VIEW_ROWS * COLS          ; 640

A_BITMAP        = STAGING + 2               ; the asset, staged
A_SCREEN        = A_BITMAP + BITMAP_BYTES
A_COLOURS       = A_SCREEN + CELLS
A_BACK          = A_COLOURS + CELLS

TOP_BAR         = PICTURE
PICTURE_BITMAP  = PICTURE + BAR_BYTES
LOW_BAR         = PICTURE_BITMAP + BITMAP_BYTES
PICTURE_SCREEN  = VIEW_SCREEN + PICTURE_TOP * COLS
PICTURE_COLOURS = COLOUR_RAM + PICTURE_TOP * COLS

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; picture_show: the Departure's picture N in the view. One with no picture to it (no PNG
; when the Departure was built, a disk without its file, a damaged asset) leaves the view
; as it is, as the C64 version does.
;   Takes:   A = the picture (the depot's number for it).
;   Before:  $01 = $35; the depot opened (depot.s: picture_asset).
;   After:   from the next frame, the view's mode is the bitmap's; the picture goes in a
;            frame or two, the view black till then.
;   Changes: A, X, Y; zp_src, zp_dst, zp_len; assets.s's zero page; the staging RAM.
picture_show:
        clc
        adc picture_asset
        bcs @none
        jsr asset_fetch
        bcs @none
        lda STAGING                 ; a picture: just so long
        cmp #<PICTURE_SIZE
        bne @none
        lda STAGING + 1
        cmp #>PICTURE_SIZE
        beq @picture
@none:  rts
@picture:
        ; The view black: every cell's colours black, then the bitmap's mode.
        lda #0
        ldx #0
@black: sta VIEW_SCREEN, x
        sta VIEW_SCREEN + $100, x
        sta VIEW_SCREEN + VIEW_CELLS - $100, x
        sta COLOUR_RAM, x
        sta COLOUR_RAM + $100, x
        sta COLOUR_RAM + VIEW_CELLS - $100, x
        inx
        bne @black
        lda #MEM_PICTURE
        ldx #CTRL1_BITMAP
        ldy #BLACK
        jsr view_mode
        ; The bars: every pixel %11, the colour RAM's black.
        lda #$FF
        ldx #0
@bars:  .repeat BAR_BYTES / $100, i
        sta TOP_BAR + i * $100, x
        sta LOW_BAR + i * $100, x
        .endrepeat
        cpx #<BAR_BYTES             ; (and the last part page)
        bcs @bar_done
        sta TOP_BAR + (BAR_BYTES & $FF00), x
        sta LOW_BAR + (BAR_BYTES & $FF00), x
@bar_done:
        inx
        bne @bars
        ; The picture: its bitmap, then its colours, then its background.
        lda #<A_BITMAP
        ldx #>A_BITMAP
        ldy #>PICTURE_BITMAP
        jsr copy_from
        lda #<PICTURE_BITMAP
        sta zp_dst
        lda #<BITMAP_BYTES
        sta zp_len
        lda #>BITMAP_BYTES
        sta zp_len + 1
        jsr ram_copy
        lda #<A_SCREEN
        ldx #>A_SCREEN
        ldy #>PICTURE_SCREEN
        jsr copy_from
        lda #<PICTURE_SCREEN
        sta zp_dst
        jsr copy_cells
        lda #<A_COLOURS
        ldx #>A_COLOURS
        ldy #>PICTURE_COLOURS
        jsr copy_from
        lda #<PICTURE_COLOURS
        sta zp_dst
        jsr copy_cells
        lda #MEM_PICTURE
        ldx #CTRL1_BITMAP
        ldy A_BACK
        jmp view_mode

; copy_from: a copy from A/X (low/high) to page Y (its low byte to come). Changes A.
copy_from:
        sta zp_src
        stx zp_src + 1
        sty zp_dst + 1
        rts

; copy_cells: the copy (copy_from) of a colour for each of the picture's cells. Changes
; A, X, Y; zp_src, zp_dst.
copy_cells:
        lda #<CELLS
        sta zp_len
        lda #>CELLS
        sta zp_len + 1
        jmp ram_copy
