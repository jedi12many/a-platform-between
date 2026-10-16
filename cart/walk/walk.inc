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
FL_CHARS        = 1190          ; the characters: 0 blank, then 4 a tile

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
SHIFTED         = 1             ; the back screen made; the colours next
COLOURED        = 2             ; the colours made; the swap at the next frame
SHADOW          = $9800         ; the colours, as they'll be shown (1000 bytes)
; Generated code (gen.s): a byte's copy each, unrolled, 6001 bytes a block.
SHIFT_AB        = $2000         ; screen A to B, shifted by X - 41
SHIFT_BA        = $3800         ; B to A
SHADE_UP        = $5000         ; the shadow, in place, shifted: first byte first
SHADE_DOWN      = $6800         ; last byte first
BLAST           = $8000         ; the shadow to the colour RAM, top first
OFFSET_BIAS     = 41            ; X = the shift (-41 to 41) + this
BORDER_COLOUR   = 0             ; black

; The area's characters and colours, a byte each (96 x 48), built from the squares at the
; start (edge.s), so an edge is a copy: the camera's clamp keeps every edge on the area.
CHAR_MAP        = $A000         ; to $B1FF
COLOUR_MAP      = $E000         ; to $F1FF, under the KERNAL (out)
