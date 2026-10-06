// Fights through the VM: a win, an escape by the exit, an ambush, health carried from
// fight to fight, and healing in between.
title: Fight Tests
id: 904
kind: official
season: 1
realm: tl 5, ml 5
levels: 1-3
start: start
linear: yes

map den
    @...a
    a = ASH_RAT

map gauntlet
    >@.a
    a = RUST_GUARD

map alley
    @.......a
    a = SCRAP_GUNNER

== start
Three doors.
+ [The rat] -> rat
+ [The guard by the back door] -> guard
+ [The alley] -> alley
+ [Rest] -> rest
+ [Leave] -> done

== rat
fight den
    won:  The rat is gone. -> start
    fled: You back away from the rat. -> start
    lost: Bitten, you stagger out. -> start

== guard
fight gauntlet
    won:  The guard falls. -> start
    fled: You slip out the back door. -> start
    lost: The guard throws you out. -> start

== alley
fight alley ambush
    won:  The gunner falls. -> start
    fled: You duck back out of the alley. -> start

== rest
You rest a while. ~ heal 10
-> start

== done
~ end complete
