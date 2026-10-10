; A0's demonstration (docs/cartridge.md, "Milestones"): a map in the view, the traveler in
; the party frame, a roll in the dice log, and the start of The Fare in the story log,
; fetched as asset 1. It shows the framework working; the story VM (A3) replaces it.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export demo, demo_map
        .import view_map, text_at, log_print, asset_fetch

ASSET_STORY = 1

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; demo: the framed screen, filled in.
;   Before:  $01 = $35; the screen set up and the split on.
;   Changes: A, X, Y; the zero page of view.s, text.s and assets.s; zp_t0-zp_t3.
demo:
        lda #<demo_map
        ldx #>demo_map
        jsr view_map
        lda #SIDE_COL               ; the party: Kestrel, her turn, health 9 of 10 halves
        sta zp_t0
        lda #YELLOW
        sta zp_t1
        lda #SIDE_COLS - 5
        sta zp_t2
        lda #<traveler
        ldx #>traveler
        ldy #PARTY_TOP
        jsr text_at
        lda #SIDE_COL + SIDE_COLS - 5
        sta zp_t0
        lda #GREEN
        sta zp_t1
        lda #5
        sta zp_t2
        lda #<bar
        ldx #>bar
        ldy #PARTY_TOP
        jsr text_at
        lda #SIDE_COL               ; the dice log: a roll in two lines
        sta zp_t0
        lda #WHITE
        sta zp_t1
        lda #SIDE_COLS
        sta zp_t2
        lda #<roll_top
        ldx #>roll_top
        ldy #LOG_LAST - 1
        jsr text_at
        lda #CYAN
        sta zp_t1
        lda #<roll_bottom
        ldx #>roll_bottom
        ldy #LOG_LAST
        jsr text_at
        lda #ASSET_STORY            ; the story, from asset 1
        jsr asset_fetch
        bcs @none
        lda #<STAGING
        ldx #>STAGING
        jmp log_print
@none:  rts

; The map: 10 x 4 tiles, row by row (tools/battlegfx.py: 0 floor, 1 wall, 2 pit, 3 rough,
; 4 cover, 5 hazard, 6 high ground, 7 exit).
demo_map:
        .byte 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
        .byte 7, 0, 0, 4, 0, 0, 5, 0, 6, 1
        .byte 1, 0, 3, 0, 0, 2, 5, 0, 0, 1
        .byte 1, 1, 1, 1, 1, 1, 1, 1, 1, 1

traveler:       .byte ">Kestrel", 0
bar:            .byte ASCII_BAR_FULL, ASCII_BAR_FULL, ASCII_BAR_FULL, ASCII_BAR_FULL
                .byte ASCII_BAR_HALF, 0
roll_top:       .byte "Kestrel 94", 0
roll_bottom:    .byte "vs 60: hit 23", 0
