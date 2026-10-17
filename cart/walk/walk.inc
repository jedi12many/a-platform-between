; The walking engine (docs/walk.md): its memory map and its numbers. Names only: no code,
; no storage. The chips are cart/hw.inc's.

; ------------------------------------------------------------------ the area
SQUARES_X_MAX   = 80            ; a floor's size: any up to these (its width and height in
SQUARES_Y_MAX   = 48            ; the asset): a row of squares is a page of COLOUR_MAP
BLOCKED         = $80           ; a square's byte: its tile, and this if you can't stand there
TILE_MASK       = $1F

; The floor's asset (tools/walk/walk.py, Floor.asset), where the program has it; its
; squares (w x h, a row at a time) are a second file, squares.bin (floor.s).
FL_COLOURS      = 0             ; background, shared 1, shared 2
FL_TILES        = 3             ; how many tiles
FL_TILE_COLOUR  = 4             ; each tile's colour RAM value (32)
FL_START        = 36            ; where you start: square x, y
FL_SIZE         = 38            ; the floor's width and height, in squares
FL_PARTY        = 40            ; the party's kinds, in marching order (4)
FL_KINDS        = 44            ; how many kinds of figure
FL_KIND_COLOUR  = 45            ; each kind's colour (12)
FL_FIGURES      = 57            ; how many figures (foes, people), then each: x, y, kind
FL_CHARS        = 304           ; the characters: 0 blank, then 4 a tile
FL_HUD          = 2000          ; the HUD's sprites (border.s): their x's low bytes (8)...
HUD_X           = 0
HUD_COLOUR      = 8             ; ...their colours (8)...
HUD_HIGHS       = 16            ; ...the x's ninth bits, and which are multicolour
HUD_MULTI       = 17
FL_SHAPES       = 2048          ; the sprite shapes: kind k's 2 k (right), 2 k + 1 (left);
                                ; 24-27 the HUD's health, 31 empty

; ------------------------------------------------------------------ the screen
SCREEN_A        = $C000         ; two screens, one shown while the other's made
SCREEN_B        = $C400
WALK_CHARS      = $C800         ; the look's characters (2 KB)
MEM_A           = $02           ; $D018: screen A, characters $C800
MEM_B           = $12           ; screen B
SCREEN_SIZE     = 1000          ; 40 x 25
COLS            = 40
ROWS            = 25
CTRL1_VIEW      = $18           ; $D011 in the view: the screen on, 25 rows (so line 247's
                                ; compare doesn't shut the border), text; the fine scroll in 0-2
CTRL1_BAND      = $58           ; ...and ECM: with multicolour an invalid mode, all black
CTRL1_SHUT      = $50           ; the band at 24 rows (so line 251's compare doesn't either)
RST8            = $80           ; $D011's bit 7: the raster interrupt's line's ninth bit
CTRL2_WALK      = $10           ; $D016: multicolour, 38 columns; the fine scroll in 0-2
FIRST_VIEW      = 55            ; the view: lines 55-246, the 24 rows' (docs/walk.md, "The border")
LAST_VIEW       = 246
TOP_LINE        = 52            ; the interrupts, each two lines before the line it waits
BOTTOM_LINE     = 244           ; for (getting in takes some 80 cycles): the top's (54), the
HUD_LINE        = 264           ; bottom's (246; 245 with the fine scroll at 6, its interrupt
                                ; at 243), the HUD's pointers' (266: the low byte 10)...
WORLD_LINE      = 1             ; ...and the world's sprites again, the next picture's first
                                ; (not before: a Y of 33-55 would meet lines 289-311's low
                                ; byte and show in the top border; and by 11, the HUD's)
HUD_Y           = 11            ; the HUD's sprites' Y: line 267's low byte, shown from 268
                                ; (their pointers written in 266: no sprite's fetched at its end)
EVENT_LAST      = 238           ; no sprite reused after this line (the bottom's interrupt
                                ; comes at 243 or 244)
TRAMPOLINE      = $FF00         ; the interrupt's way in: jmp irq, so $FFFF (its vector's high
                                ; byte, the idle VIC's byte) is $FF, all black

; ------------------------------------------------------------------ the camera
; Its most, across and down, is the floor's (camera_init): (2 w - 40) x 8 + 7 and (2 h -
; 25) x 8 + 7, the screen's 40 x 25 characters on the area.
HALF_VIEW_X     = 152           ; half the 38 columns, in pixels
HALF_VIEW_Y     = 96            ; half the 24 rows

; ------------------------------------------------------------------ walking
SPEED           = 23            ; sixteenths of a pixel a frame: 1.44 pixels, 4.5 squares a second
SPEED_DIAG      = 16            ; each way, on a diagonal
BODY_LO         = 3             ; the body: pixels 3-12 of its 16-pixel square
BODY_HI         = 12
NUDGE           = 7             ; round a corner: within 7 pixels of the way through
STICK_UP        = $01           ; CIA 1's port A: port 2's joystick, 0 when pushed
STICK_DOWN      = $02
STICK_LEFT      = $04
STICK_RIGHT     = $08

; ------------------------------------------------------------------ the scroller
IDLE            = 0             ; nothing under way
HALF            = 1             ; the back screen's top half made
SHIFTED         = 2             ; the back screen made
SHADED          = 3             ; held: the colours next
COLOURED        = 4             ; the swap at the next frame; its colours copied as the
                                ; raster passes each row, the rest at the swap
; Generated code (gen.s), a byte's copy each, unrolled.
SHIFT_AB        = $2800         ; screen A to B, shifted by X - 41: 6002 bytes, its first
SHIFT_BA        = $4000         ; 500 bytes' copies and an RTS, then the rest and an RTS
OFFSET_BIAS     = 41            ; X = the shift (-41 to 41) + this
SECOND_HALF     = 500 * 6 + 1   ; a block's second half, from its start
COLOUR_ROWS     = $5800         ; the colour RAM's rows from the colour map, a row a call
ROW_CODE        = 40 * 6 + 1    ; (to $6F88)
AIM_ROWS        = $7000         ; each row's copy aimed at its row of the colour map, a row a
AIM_CODE        = 40 * 3 + 1    ; call (to $7BD0)
BORDER_COLOUR   = 0             ; black

; The area, a page a row of squares (edge.s, maps_build): its colours from the page's
; start, a byte a column of characters (a square's two columns and two rows have its
; colour), so a row of the colour RAM is a straight copy; then, from 2 w, the squares
; themselves. (The characters aren't kept: an edge's are worked out from its squares.)
COLOUR_MAP      = $7C00         ; to $ABFF at most (48 rows)

; ------------------------------------------------------------------ seeing
SEE_BANDS_MAX   = 24            ; a floor's bands (seeing.s)
SEE_LOG         = $AC00         ; each step's checks, every die (for the tests): to $B1FF
SEE_LOG_SIZE    = $0600

; ------------------------------------------------------------------ the figures
SPRITE_SHAPES   = $D000         ; under the I/O (the VIC sees the RAM): 32 shapes
SHAPE_POINTER   = $40           ; shape s: the VIC's pointer $40 + s
POINTERS_A      = SCREEN_A + $03F8      ; each screen's sprite pointers (both are kept)
POINTERS_B      = SCREEN_B + $03F8
PARTY_SIZE      = 4
FIGURES_MAX     = 80            ; the floor's foes and people
SHOWN_MAX       = PARTY_SIZE + FIGURES_MAX
GAP             = 9             ; trail entries between travelers in marching order
TRAIL           = 32            ; the leader's trail kept (a power of 2)
SPRITE_DX       = 27            ; a figure's sprite: its square's pixel - the camera + these
SPRITE_DY       = 47
SPRITE_X_MIN    = 8             ; in sight: some of it inside the 38 x 24
SPRITE_X_MAX    = 334
SPRITE_Y_MIN    = 35
SPRITE_Y_MAX    = 245           ; (a sprite's last line 266, before the HUD's pointers)
SPRITE_LINES    = 21
REUSE           = 23            ; a sprite reused: the next figure at least this far below
BLANK_SHAPE     = SHAPE_POINTER + 31    ; an empty shape: the sprites in the border bands
HUD_SHAPES      = SHAPE_POINTER + 24    ; the HUD's four (health), after the kinds' 24
SPRITE_MC1      = 0             ; black: the outline drawn in
SPRITE_MC2      = 15            ; light grey
; A program for the sprites (figures.s makes it, mux.s carries it out): a page each, two
; of them (one shown, one being made). The first eight sprites as the VIC has them (8 x's,
; 8 y's, 8 pointers, 8 colours), then the events, 8 bytes each (line, sprite, x, x's
; ninth bit, y, pointer, colour, a spare), and at the end which sprites are on, their x's
; ninth bits, how many events.
PROG_A          = $BE00
PROG_B          = $BF00
P_X             = 0
P_Y             = 8
P_PTR           = 16
P_COLOUR        = 24
P_EVENTS        = 32
EVENTS_MAX      = 26
EVENT_SIZE      = 8
E_LINE          = 0
E_SPRITE        = 1
E_X             = 2
E_X_HIGH        = 3
E_Y             = 4
E_PTR           = 5
E_COLOUR        = 6
P_ENABLE        = 250
P_X_HIGHS       = 251
P_COUNT         = 252
