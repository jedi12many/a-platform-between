// A Siding with a yard (docs/deep-yards.md): picks, a pool of foes, and fights on maps
// built for each floor.
title: Little Yard
id: 990
kind: siding
realm: tl 5, ml 5
levels: 1-3
start: down

var floor = 1
var room = 0
var mood = 0

yard pit
    ASH_RAT
    RUST_GUARD, MAINT_DRONE

== down
Yard {yard}, floor {floor}.
~ pick room 3 on floor ~ pick mood 2
if room = 1
    A quiet room.
+ [Fight] -> brawl
+ [Leave] -> out

== brawl
fight yard pit on floor ambush
    won:  Won. ~ add floor 1 -> down
    fled: Fled. -> down
    lost: Lost. -> out

== out
~ xp 5
~ end complete
