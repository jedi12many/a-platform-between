; The cartridge's memory map and the framed screen's layout (docs/cartridge.md,
; docs/frames.md). Names only: no code, no storage.

; ------------------------------------------------------------------ RAM
RESIDENT_AT     = $1000         ; the engine, copied here at the start
STAGING         = $8000         ; an asset (8 KB) is staged here (assets.s)
STAGING_PAGES   = $20
MEDIA_CART      = 0             ; what the game came on (assets.s)
MEDIA_DISK      = 1

; The story (vm.s): the Departure's depot and its car (one chapter), copied from their
; assets, and a string as it's expanded.
CAR_AT          = $A000         ; 6 KB and 16 (a car is 6144 at most)
CAR_MAX         = 6144
DEPOT_AT        = $B800         ; 2 KB
DEPOT_MAX       = 2048
EXPAND_AT       = $0400         ; to $0FFF
EXPAND_MAX      = $0BFF
; At a trip's end, the same room is the QR code's (qr.s): its modules, a byte each (33 x
; 33 at most), the Galois field's tables, the codewords, the generator.
QR_MATRIX       = EXPAND_AT             ; 1089
QR_EXP          = EXPAND_AT + $0500     ; 256
QR_LOG          = EXPAND_AT + $0600     ; 256
QR_CODEWORDS    = EXPAND_AT + $0700     ; 100
QR_GENERATOR    = EXPAND_AT + $0780     ; 21
ASSET_ENDING    = 1             ; code: a trip's end (receipt.s, stamp.s, qr.s), run here
ASSET_BATTLE    = 2             ; code: a fight's rules and screen (combat.s, battle.s,
                                ; tactics.s), run here
ASSET_FIGHT     = 3             ; code: the fight itself (fight.s, fightext.s), copied to
                                ; EXPAND_AT and run there, beside asset 2
ASSET_DEPOT     = 4             ; the Departure's assets: its depot, then its cars (and
ASSET_CAR0      = 5             ; its pictures: the depot says where)

; ------------------------------------------------------------------ VIC bank 3
TEXT_SCREEN     = $C000         ; the frames (and the status row)
VIEW_SCREEN     = $C400         ; the view: the map's characters, or a picture's colours
VIEW_CHARS      = $C800         ; the map's tiles (tools/battlegfx.py)
FONT            = $D000         ; our font (tools/c64font.py), under the I/O
SPRITE_SHAPES   = $D800         ; under the colour RAM: 32 shapes
SPRITE_POINTERS = VIEW_SCREEN + $03F8   ; the view's screen's: the sprites are only there
PICTURE         = $E000         ; a multicolour bitmap, under the KERNAL
VIC_BANK3       = %00           ; CIA2_PRA's bits 0-1

; $D018: screen and characters
MEM_FRAMES      = $04           ; screen $C000, characters $D000
MEM_VIEW        = $12           ; screen $C400, characters $C800
MEM_PICTURE     = $18           ; screen $C400, bitmap $E000

; The colour RAM is this far above the text screen, and above the view's screen.
TEXT_TO_COLOUR  = COLOUR_RAM - TEXT_SCREEN      ; $1800
VIEW_TO_COLOUR  = COLOUR_RAM - VIEW_SCREEN      ; $1400

; ------------------------------------------------------------------ the frames
COLS            = 40
VIEW_ROWS       = 16            ; rows 0-15

; The view's squares (view.s): 16 x 16 pixels, 2 x 2 characters, 20 across, 8 down.
SQUARE          = 16
SQUARES_ACROSS  = 20
SQUARES_DOWN    = 8
TILE_RECORD     = 8             ; a tile in the table: 4 characters, then 4 colours
TILES_SIZE      = 8 * TILE_RECORD + 2 * 8 * 4   ; and each tile's 4 with the reach dot,
                                            ; then each one's 4 with the cursor
TILES_MARKED    = 8 * TILE_RECORD       ; (where they start in the table)
TILES_CURSOR    = TILES_MARKED + 8 * 4
; The figures (tools/battlegfx.py --cart16): 16 looks, each a body and its fallen body,
; sprite shapes 2n and 2n + 1 at SPRITE_SHAPES (the VIC's pointer SHAPE_POINTER + 2n).
LOOKS           = 16
SHAPE_POINTER   = (SPRITE_SHAPES - $C000) / 64
STRANGER        = 7                     ; the look of one with no look of its own
FOE_LOOKS       = 8                     ; foe k's is FOE_LOOKS + k
; A figure (24 x 21 sprite) on its square: centred across, its feet near the square's
; foot and its head over the square above. Its last line must be over the view's last
; three (raster 176 at most: split.s's timing); with these, the bottom row's is 176.
FIGURE_DX       = -4
FIGURE_DY       = -7
SPRITE_LEFT     = 24            ; the screen's left and top in the VIC's sprite places
SPRITE_TOP      = 50
LOG_TOP         = 16            ; the story log: rows 16-23, columns 0-24
LOG_ROWS        = 8
LOG_LAST        = LOG_TOP + LOG_ROWS - 1
LOG_COLS        = 25
DIVIDER_COL     = 25
SIDE_COL        = 26            ; the party (rows 16-19) and the dice log (rows 20-23)
SIDE_COLS       = 14
PARTY_TOP       = 16
DICE_TOP        = 20
INPUT_ROW       = 24            ; the command row
APB_NAME        = 8             ; a name in the party frame

; The frames' own characters in our font, and the ASCII codes that print them.
GLYPH_LINE      = $60
ASCII_LINE      = $10           ; the line between the frames
ASCII_BAR_EMPTY = $11           ; a health bar's cells
ASCII_BAR_HALF  = $12
ASCII_BAR_FULL  = $13

; ------------------------------------------------------------------ keys (keys.s)
KEY_UP          = 1             ; the cursor keys
KEY_DOWN        = 2
KEY_LEFT        = 3
KEY_RIGHT       = 4
KEY_UP_LEFT     = 5             ; the joystick's diagonals (and, in a fight, the digits')
KEY_UP_RIGHT    = 6
KEY_DOWN_LEFT   = 7
KEY_DOWN_RIGHT  = 9
KEY_DELETE      = 8             ; INST/DEL
KEY_RETURN      = 13
KEY_STOP        = 27            ; RUN/STOP

; ------------------------------------------------------------------ colours
BLACK           = 0
WHITE           = 1
RED             = 2
CYAN            = 3
GREEN           = 5
BLUE            = 6
YELLOW          = 7
DARK_GREY       = 11
GREY            = 12
LIGHT_GREEN     = 13

; ------------------------------------------------------------------ the EasyFlash's RAM
ef_bank         = EF_RAM        ; the bank in now ($DE00 can't be read)
EF_BOOT         = EF_RAM + $10  ; the boot's mode switch runs here
