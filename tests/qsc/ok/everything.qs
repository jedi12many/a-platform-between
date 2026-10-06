// Uses every v0 feature once, so the parser's shape is pinned down by test_qsc.py.
title: Everything
id: 7
kind: official
season: 1
realm: tl 5, ml 5
levels: 1-4
start: hall

flag alarm
flag knows_code
var loops = 2

=== One

== hall
~ picture hall
\+ This line starts with a plus and is plain text.

First line of a paragraph,
second line of the same paragraph.

A new paragraph for {name} the {race} {class}, level {level}, owing {debt}.
| FIXED LINE ONE
| FIXED  LINE TWO
Back to prose. ~ set alarm ~ add loops 1

if (MIGHT >= 50 or TECH > 30) and not alarm
    Strong or clever, and quiet.
else if echo WOLF_PUP != SAVED and has PULSE_RIFLE
    Armed, and alone.

else if race SALVAGED or class WARDEN or level >= 3 or loops = 2
    Something else.
else
    Nothing at all.

check TECH vs 145
    crit:    Doubles!
             ~ set knows_code
    success: In. -> vault
    cost:    In, loudly. ~ set alarm -> vault
    fail:    Locked.

* [Once only]
    Gone after this.
+ {visited vault} [Been there] -> vault
+ [Leave] -> vault

=== Two

== vault
Inside. ~ echo WOLF_PUP = SWORN ~ give PULSE_RIFLE ~ take PULSE_RIFLE
~ xp 10 ~ debt - 500 ~ let loops = 0 ~ sub loops 1 ~ clear alarm ~ pause
~ end complete
