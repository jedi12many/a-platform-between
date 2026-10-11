; Asset 0: the screen's graphics (screen.s): our font (tools/c64font.py), and the map's
; characters, its tiles' table and the figures' sprite shapes (tools/battlegfx.py
; --cart16: squares of 16 pixels).
; Staged at $8000.

        .segment "ASSET00"
        .incbin "cart/font", 2                  ; $8000: 2 KB (past its load address)
        .incbin "cart/tiles16", 0, 4224         ; $8800: the characters, 2 KB; $9000: the
                                                ; table (128); $9080: the figures, 2 KB
