// Rewards pay once per trip: the bell scene can be rung again and again, but its XP,
// item and Debt are paid only the first time (docs/quest-script.md, Commands).
title: Loop
id: 902
kind: official
season: 1
realm: tl 5, ml 5
levels: 1-5
start: bell
linear: yes

== bell
You ring the bell.
~ xp 10
~ give TICKET_STUB
~ debt + 100
+ [Ring it again] -> bell
+ [Leave] -> done

== done
~ end complete
