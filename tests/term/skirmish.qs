// The terminal's recorded fight (make test-term): a map with terrain and two foes, so
// the battle screen shows every kind of square and every menu.
title: Skirmish
id: 905
kind: official
season: 1
realm: tl 5, ml 5
levels: 1-3
start: start
linear: yes

map yard
    ....#....>
    .@..+..=.a
    ..~.^..#..
    ....O....b
    a = SCRAP_GUNNER
    b = ASH_RAT

== start
The yard is quiet. Then it isn't.
+ [Fight] -> yard
+ [Walk away] -> done

== yard
fight yard
    won:  The yard is quiet again. -> done
    fled: You run for it. -> done
    lost: You come to by the gate. -> done

== done
~ end complete
