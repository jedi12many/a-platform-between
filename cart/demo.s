; The demonstration (docs/cartridge.md, "Milestones"): a map in the view, a roll in the
; dice log; the boarding desk (A2), and whoever boards in the party frame; then the start
; of The Fare in the story log, fetched as asset 1, with its first menu and "-- more --"
; (A1). It shows the framework working; the story VM (A3) replaces it.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"

        .export demo, demo_map
        .import view_map, text_at, log_print, asset_fetch, menu_ask, desk_run, name_text
        .import story_static, story_choices, story_fought, story_bench, story_name
        .import story_again

ASSET_STORY = 1

        .segment "RESIDENT"

; ----------------------------------------------------------------------------------------
; demo: the framed screen, filled in, then the story, round and round.
;   Before:  $01 = $35; the screen set up and the split on.
;   After:   never returns.
demo:
        lda #<demo_map
        ldx #>demo_map
        jsr view_map
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
        bcc @board
@stuck: jmp @stuck                  ; (no story to tell: the border is red)
@board: lda #0                      ; the desk: The Fare is Departure 0
        tax
        jsr desk_run
        lda #SIDE_COL               ; the party: who boarded, their turn
        sta zp_t0
        lda #YELLOW
        sta zp_t1
        lda #1
        sta zp_t2
        lda #<turn
        ldx #>turn
        ldy #PARTY_TOP
        jsr text_at
        inc zp_t0
        lda #APB_NAME
        sta zp_t2
        jsr name_text
        ldy #PARTY_TOP
        jsr text_at
@story: lda #<story_static
        ldx #>story_static
        jsr log_print
        lda #<story_choices
        ldx #>story_choices
        jsr log_print
        lda #2
        jsr menu_ask
        beq @let
        lda #<story_fought
        ldx #>story_fought
        jsr log_print
@let:   lda #<story_bench
        ldx #>story_bench
        jsr log_print
        lda #<story_name
        ldx #>story_name
        jsr log_print
        jsr name_text
        jsr log_print
        lda #<story_again
        ldx #>story_again
        jsr log_print
        lda #1
        jsr menu_ask
        jmp @story

; The map: 20 x 8 tiles, row by row (tools/battlegfx.py: 0 floor, 1 wall, 2 pit, 3 rough,
; 4 cover, 5 hazard, 6 high ground, 7 exit).
demo_map:
        .byte 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1
        .byte 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 0, 6, 1
        .byte 7, 0, 0, 4, 0, 1, 0, 0, 5, 5, 0, 0, 0, 0, 3, 0, 0, 0, 6, 1
        .byte 1, 0, 0, 4, 0, 0, 0, 0, 5, 5, 0, 2, 2, 0, 0, 0, 4, 0, 0, 1
        .byte 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 0, 0, 0, 4, 0, 0, 1
        .byte 1, 0, 3, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1
        .byte 1, 0, 3, 3, 0, 1, 0, 0, 0, 4, 0, 0, 0, 0, 5, 0, 0, 0, 0, 7
        .byte 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1

turn:           .byte ">", 0
roll_top:       .byte "Kestrel 94", 0
roll_bottom:    .byte "vs 60: hit 23", 0
