// The small example from docs/quest-script.md.
title: The Lantern Test
id: 900
kind: branch
realm: tl 3, ml 9
levels: 1-3
start: gate

flag paid_toll
var lanterns = 0

=== The Gate

== gate
An iron gate, and a moth-winged guard with a lantern for a head.

+ [Pay the toll]
    ~ set paid_toll
    The guard bows. Its light dims politely.
+ {paid_toll} [Go through] -> courtyard
+ [Leave] -> leave

== courtyard
Lanterns everywhere. One of them is looking at you. There are {lanterns} now.
~ add lanterns 1
+ [Wave] -> courtyard
+ [Go back] -> gate

== leave
You walk away. Somewhere, a lantern goes out.
~ end complete
