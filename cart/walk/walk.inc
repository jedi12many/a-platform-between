; The walking engine (docs/walk.md): its memory map and its numbers. Names only: no code,
; no storage. The chips are cart/hw.inc's.

; ------------------------------------------------------------------ the area
SQUARES_X       = 48            ; the floor's nine rooms side by side
SQUARES_Y       = 24
CHARS_X         = 96            ; two characters a square, both ways
CHARS_Y         = 48
BLOCKED         = $80           ; a square's byte: its tile, and this if you can't stand there
TILE_MASK       = $1F

; The floor's asset (tools/walk/walk.py, Floor.asset), where the program has it.
FL_COLOURS      = 0             ; background, shared 1, shared 2
FL_TILES        = 3             ; how many tiles
FL_TILE_COLOUR  = 4             ; each tile's colour RAM value (32)
FL_START        = 36            ; where you start: square x, y
FL_SQUARES      = 38            ; 48 x 24
FL_PARTY        = 1190          ; the party's kinds, in marching order (4)
FL_KINDS        = 1194          ; how many kinds of figure
FL_KIND_COLOUR  = 1195          ; each kind's colour (12)
FL_FIGURES      = 1207          ; how many figures (foes, people), then each: x, y, kind
FL_CHARS        = 1304          ; the characters: 0 blank, then 4 a tile
FL_SHAPES       = 2048          ; the sprite shapes: kind k's 2 k (right), 2 k + 1 (left)

; ------------------------------------------------------------------ the screen
SCREEN_A        = $C000         ; two screens, one shown while the other's made
SCREEN_B        = $C400
WALK_CHARS      = $C800         ; the look's characters (2 KB)
MEM_A           = $02           ; $D018: screen A, characters $C800
MEM_B           = $12           ; screen B
SCREEN_SIZE     = 1000          ; 40 x 25
COLS            = 40
ROWS            = 25
CTRL1_WALK      = $10           ; $D011: the screen on, 24 rows (the fine scroll's edge
                                ; hidden), text; the fine scroll in bits 0-2
CTRL2_WALK      = $10           ; $D016: multicolour, 38 columns; the fine scroll in 0-2
VB_LINE         = 250           ; the interrupt: under the 24 rows (they end at line 246)

; ------------------------------------------------------------------ the camera
CAM_X_MAX       = 455           ; (96 - 40) x 8 + 7: the screen's 40 columns on the area
CAM_Y_MAX       = 191           ; (48 - 25) x 8 + 7
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
SHIFTED         = 2             ; the back screen made; the colours next
SHADED          = 3             ; the shadow's first half shifted
COLOURED        = 4             ; the colours made; the swap at the next frame
SHADOW          = $B200         ; the colours, as they'll be shown (1000 bytes); the
                                ; program's variables after it, from $B600 (walk.cfg)
; Generated code (gen.s): a byte's copy each, unrolled, 6002 bytes a block: its first 500
; bytes' copies and an RTS, then the rest and an RTS (a screen's shift takes two frames).
SHIFT_AB        = $2800         ; screen A to B, shifted by X - 41
SHIFT_BA        = $4000         ; B to A
SHADE_UP        = $5800         ; the shadow, in place, shifted: first byte first
SHADE_DOWN      = $7000         ; last byte first
BLAST           = $8800         ; the shadow to the colour RAM, top first
OFFSET_BIAS     = 41            ; X = the shift (-41 to 41) + this
SECOND_HALF     = 500 * 6 + 1   ; a block's second half, from its start
BORDER_COLOUR   = 0             ; black

; The area's characters and colours, a byte each (96 x 48), built from the squares at the
; start (edge.s), so an edge is a copy: the camera's clamp keeps every edge on the area.
CHAR_MAP        = $A000         ; to $B1FF
COLOUR_MAP      = $E000         ; to $F1FF, under the KERNAL (out)

; ------------------------------------------------------------------ the figures
SPRITE_SHAPES   = $D000         ; under the I/O (the VIC sees the RAM): 32 shapes
SHAPE_POINTER   = $40           ; shape s: the VIC's pointer $40 + s
POINTERS_A      = SCREEN_A + $03F8      ; each screen's sprite pointers (both are kept)
POINTERS_B      = SCREEN_B + $03F8
PARTY_SIZE      = 4
FIGURES_MAX     = 32            ; the floor's foes and people
SHOWN_MAX       = PARTY_SIZE + FIGURES_MAX
GAP             = 9             ; trail entries between travelers in marching order
TRAIL           = 32            ; the leader's trail kept (a power of 2)
SPRITE_DX       = 27            ; a figure's sprite: its square's pixel - the camera + these
SPRITE_DY       = 47
SPRITE_X_MIN    = 8             ; in sight: some of it inside the 38 x 24
SPRITE_X_MAX    = 334
SPRITE_Y_MIN    = 35
SPRITE_Y_MAX    = 246
SPRITE_LINES    = 21
REUSE           = 23            ; a sprite reused: the next figure at least this far below
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
