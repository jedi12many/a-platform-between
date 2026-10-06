title: Broken Fights
id: 954
kind: official
season: 1
realm: tl 5, ml 5
levels: 1-3
start: a

map ragged                           // error: 'b' stands on map 'ragged' but isn't given a foe
    #####
    #@.a#
    #..b##                           // error: must be the same width
    #.%.#                            // error: '%' isn't a square
    a = RUST_GARD                    // error: Did you mean 'RUST_GUARD'?

map nobody                           // error: needs at least one '@'
    #.a.#
    a = ASH_RAT
    #...#                            // error: the map's rows come first

map spare                            // warning: 'q' is given a foe but isn't on map 'spare'
    @.a
    a = ASH_RAT
    q = ASH_RAT

map crowd                            // error: at most 8 in all
    @@@aaaaaa
    a = ASH_RAT

map nofoes                           // error: has no foes
    #@..#

map arena
    @..a
    a = RUST_GUARD

== a
fight arena
    won: -> b
    draw: -> b                       // error: each line starts with won:, lost: or fled:
fight arnea                          // error: Did you mean 'arena'?
fight arena surprise                 // error: write 'ambush' or 'sneak', or nothing
fight spare
-> b

== b
~ end complete
