; Asset 0: the screen's graphics (screen.s): our font (tools/c64font.py), the map's
; characters and its tiles' table (tools/battlegfx.py). Staged at $8000.

        .segment "ASSET00"
        .incbin "cart/font", 2                  ; $8000: 2 KB (past its load address)
        .incbin "battle.bgfx", 640, 2048        ; $8800: the characters
        .incbin "battle.bgfx", 8, 256           ; $9000: the tiles
