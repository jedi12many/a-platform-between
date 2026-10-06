// Two roads to the castle, so no route warning.
title: Two Roads
id: 956
kind: branch
realm: tl 3, ml 3
levels: 1-3
start: gate

== gate
+ [The bridge] -> bridge
+ [The ford] -> ford

== bridge
The bridge holds.
+ [Cross] -> castle

== ford
Cold water to the waist.
+ [Wade] -> castle

== castle
You made it.
~ end complete
