// The small script from tools/qsc/test_build.py: a once-only choice behind a flag,
// and a check whose crit falls back to its success branch.
title: Tiny
id: 901
kind: branch
realm: tl 1, ml 2
levels: 1-2
start: a

flag f

== a
Hi {name}.
* {f} [Go] -> b
+ [Stay]
    ~ set f

== b
check TECH hard
    success: Yes.
~ end complete
