; The disk's assets (disk.cfg): each file ANN starts with its load address, $8000, the
; staging RAM (cart/assets.s), as a C64 program file does.

        .segment "A00ADDR"
        .word $8000
        .segment "A01ADDR"
        .word $8000
