title: Branch Limits
id: 953
kind: branch
realm: tl 3, ml 3
levels: 1-3
start: a

== a
~ echo WOLF_PUP = SAVED                         // error: can't change Echoes
~ debt - 100                                    // error: can't change Debt
~ give PULSE_RIFLE                              // error: tier 3 or lower
~ give RUSTED_SABRE
+ {echo WOLF_PUP = SAVD} [Whistle] -> a         // error: Did you mean 'SAVED'?
+ {echo WOLF_PUP = SAVED} [Whistle] -> a
+ [Text] -> a
~ end complete                                  // error: only choices can come after
