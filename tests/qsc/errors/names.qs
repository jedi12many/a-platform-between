title: Names
id: 950
kind: branch
realm: tl 3, ml 3
levels: 1-3
start: bridge

flag alarm
var loops = 0

== bridge
You stand on the bridge. ~ set alrm             // error: no flag called 'alrm'. Declare it
Your name is {nme}.                             // error: Did you mean 'name'?
~ gve PULSE_RIFLE                               // error: Did you mean 'give'?
~ give PULSE_RIFL                               // error: no item called 'PULSE_RIFL'
~ set loops                                     // error: 'loops' is a variable, not a flag: '~ let loops = 1'
+ {MIHGT >= 5} [Lift it] -> bridge              // error: Did you mean 'MIGHT'?
+ {alarm} [Run] -> brige                        // error: no scene called 'brige'. Did you mean 'bridge'?
+ {loops > 1} [Wait] -> bridge
+ [Give it] -> bridge
