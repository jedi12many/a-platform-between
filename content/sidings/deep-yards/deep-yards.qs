// The Deep Yards (docs/deep-yards.md, docs/sidings.md): the first Siding, a prototype.
// Ten floors under the Waystation, built from the yard's number: each floor picks its
// realm and its side track with `~ pick ... on floor`, and its fights are maps the VM
// builds with `fight yard depths on floor`. The same yard is the same ten floors on
// every machine; the dice are still your own.

title: The Deep Yards
id: 1000
kind: siding
realm: tl 5, ml 5
levels: 1-10
start: lift
linear: yes

var floor = 1
var realm = 0       // what this floor looks like
var way = 0         // its side track
var loot = 0        // what's in a cache

flag took_way       // this floor's side track is done

// Weakest first: the deeper the floor, the further down this list its foes come from.
yard depths
    ASH_RAT
    RUST_GUARD
    MAINT_DRONE

=== The Deep Yards

== lift
~ picture yards
At the far end of the freight lines, past the last lamp, a cage lift hangs over a shaft
that goes down further than the Waystation does. A brass plate on the gate says
YARD {yard}. Someone has scratched a number under it: 10.

The operator, a man made mostly of rust and patience, doesn't look up. "Ten floors," he
says. "Every one a different place. Come back up when you like. If you can."

+ [Step into the cage] -> landing
+ [Not today] -> not_today

== not_today
You leave the lift to someone braver. It will be here. It always is.
~ end complete

== landing
~ pick realm 6 on floor
~ pick way 4 on floor
The cage grinds down and stops. Floor {floor}.

if realm = 1
    A drowned rail city: green water to the platform edge, lamps burning underneath it.
else if realm = 2
    A marshalling yard under three moons, so cold the rails sing when you touch them.
else if realm = 3
    A jungle has eaten a depot here. Vines hang from the signal gantries like cables.
else if realm = 4
    A freight terminal made of light: every crate a hologram, every sign in a language
    that rearranges itself to be polite.
else if realm = 5
    A cathedral of bone where trains are worshipped. A choir hums the timetable.
else
    A dust world. Sand drifts over the sleepers, and the wind smells of hot iron.

Ahead, past the buffers, a stair goes down, and something is waiting by it.

+ {not took_way and way = 1} [A dark siding: something nests there] -> den
+ {not took_way and way = 2} [A wagon with its doors sealed] -> cache
+ {not took_way and way = 3} [A shrine built out of signal lamps] -> shrine
+ {not took_way and way = 4} [A brazier, and an empty bench] -> rest
+ [Take the stairs down] -> stairs
+ [Ride the cage back up] -> surface

== den
~ set took_way
Whatever lives in the siding has made a nest of torn timetables. It hasn't seen you yet.
fight yard depths on floor sneak
    won:  The nest is quiet. Under the paper, someone's old pay packet: you keep it.
          ~ heal 5
    fled: You back out of the siding and leave it to its nest.
    lost: The yard takes you. Something hauls you up the shaft by the collar, and drops
          you on the Waystation's cold floor. -> pulled_up
-> landing

== cache
~ set took_way
~ pick loot 4 on floor
The wagon's seal is old. It gives with a sigh.
if loot = 1
    Inside, wrapped in oilcloth: a sabre, rusted, but it remembers how. ~ give RUSTED_SABRE
else if loot = 2
    A medic's scanner, still blinking. ~ give MED_SCANNER
else if loot = 3
    A coat of ballistic weave, folded like a flag. ~ give BALLISTIC_WEAVE
else
    Nothing but a ticket stub, punched for a line that doesn't exist. ~ give TICKET_STUB
-> landing

== shrine
~ set took_way
The shrine's lamps turn as you come near: red, amber, green.
check FATE
    crit:    All of them turn green at once. You feel the yard let you through.
             ~ heal full
    success: Green. Something in you mends. ~ heal 10
    cost:    Amber, and a long wait while it decides. ~ heal 3
    fail:    Red. The lamps go dark, and stay dark.
-> landing

== rest
~ set took_way
You sit by the brazier a while. Nobody comes. It's the best kind of nobody.
~ heal 8
-> landing

== stairs
The stair down is guarded.
fight yard depths on floor
    won:  The way down is clear. -> deeper
    fled: You run back up to the landing. Whatever it was stays by the stairs. -> landing
    lost: The yard takes you. Something hauls you up the shaft by the collar, and drops
          you on the Waystation's cold floor. -> pulled_up

== deeper
if floor = 1
    ~ xp 10
else if floor = 2
    ~ xp 10
else if floor = 3
    ~ xp 12
else if floor = 4
    ~ xp 12
else if floor = 5
    ~ xp 14
else if floor = 6
    ~ xp 14
else if floor = 7
    ~ xp 16
else if floor = 8
    ~ xp 16
else if floor = 9
    ~ xp 18
else
    ~ xp 18
if floor = 10
    -> bottom
~ add floor 1 ~ clear took_way ~ heal 10
You go down, and catch your breath on the stair. The cage is waiting at the bottom of the stair, as if it had always known.
-> landing

== bottom
~ picture bottom
The tenth floor. There's no stair down from here, only a buffer stop, and painted on it in
letters older than the Waystation: YOU CAME A LONG WAY.

The rust-and-patience man is waiting with the cage. "Yard {yard}," he says, and writes it
in a book. "Not many get here."
~ xp 30
~ end complete

== surface
The cage rattles up through the floors you've seen. At the top, the operator nods.
"Floor {floor}. Not bad. The yard'll keep."
~ end complete

== pulled_up
You lie there a while, breathing. The yard keeps what you didn't finish.
~ end failed
