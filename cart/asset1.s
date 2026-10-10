; Asset 1: the demonstration's text (demo.s), from the start of The Fare
; (content/s1/00-the-fare). Staged at $8000; ASCII, each ending in 0.

        .export story_static, story_choices, story_fought, story_bench, story_name
        .export story_again

        .segment "ASSET01"
story_static:
        .byte "~ The Static ~", 10, 10
        .byte "Static.", 10, 10
        .byte "Not the sound. The feeling: every part of you tuned to the wrong channel "
        .byte "at once.", 10, 10
        .byte "Then a hand. It reaches through the end of everything, takes hold of "
        .byte "whatever is left of you, and pulls.", 10, 10, 0
story_choices:
        .byte "1. Let it", 10, "2. Fight it", 10, 0
story_fought:
        .byte "You fight. It is like fighting the tide with your teeth. The hand doesn't "
        .byte "mind; it has done this before.", 10, 10, 0
story_bench:
        .byte "You are sitting on a wooden bench, and you are breathing, and both of "
        .byte "those things are wrong.", 10, 10
        .byte "The bench stands on a railway platform under a roof of green iron and "
        .byte "cracked glass. Beyond the glass there is no sky, only a slow grey shimmer, "
        .byte "like rain that has forgotten which way is down.", 10, 10, 0
story_name:
        .byte "A ledger lies open on the bench beside you, and a name is written in it "
        .byte "already, in a careful hand:", 0
story_again:
        .byte 10, "1. Start again", 10, 0
