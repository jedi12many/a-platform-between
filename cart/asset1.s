; Asset 1: A0's story text (demo.s), the start of The Fare (content/s1/00-the-fare).
; Staged at $8000, ASCII, ending in 0.

        .segment "ASSET01"
        .byte "~ The Static ~", 10, 10
        .byte "You are sitting on a wooden bench, and you are breathing, and both of "
        .byte "those things are wrong.", 10, 10
        .byte "The bench stands on a railway platform under a roof of green iron and "
        .byte "cracked glass. Beyond the glass there is no sky, only a slow grey shimmer.", 10
        .byte 0
