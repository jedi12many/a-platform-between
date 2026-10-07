title: The Only Road
id: 955
kind: official
season: 1
realm: tl 5, ml 5
levels: 1-3
start: gate
linear: yes

map gatehouse
    @..a
    a = RUST_GUARD

== gate
The guard won't move.
fight gatehouse                      // warning: every road to the end goes through this fight
    won: -> through
    fled: -> through

== through
~ end complete
