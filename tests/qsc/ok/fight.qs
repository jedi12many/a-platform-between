// A fight with every outcome, an ambush, two of the same foe, and a way around it.
title: Fight Test
id: 903
kind: official
season: 1
realm: tl 5, ml 2
levels: 1-3
start: yard

flag sneaked

map scrapyard
    #########
    #@.~~.a.#
    #@..+.^b>
    #==...a.#
    #########
    a = RUST_GUARD
    b = SCRAP_GUNNER

=== The Yard

== yard
Two rust-guards and a gunner stand between you and the gate.
+ [Fight your way through] -> brawl
+ [Go round by the fence] -> fence

== brawl
fight scrapyard
    won: The last of them clatters to the ground. -> gate
    fled: You back out through the gap in the fence. -> fence
    lost: Something drags you clear of the scrap. -> waystation

== fence
~ set sneaked
The fence is longer than it looks, but nobody sees you.
fight scrapyard sneak
    won: -> gate
-> gate

== waystation
You wake on the bench again, lighter in the purse.
~ end failed

== gate
The gate swings open.
~ end complete
