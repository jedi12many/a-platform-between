title: Bad Yard
id: 991
kind: siding
season: 1                       // error: 'season:' is only for official Departures
realm: tl 5, ml 5
levels: 1-3
start: down

var floor = 1
var room = 0

yard pit
    ASH_RAT RATT                // error: there's no foe called 'RATT'

yard empty                      // error: yard 'empty' has no foes

map hall
    @.a
    a = ASH_RAT

== down
~ pick room                     // error: '~ pick' is written
~ pick room 0                   // error: the number to pick from 0 is out of range
~ pick nothing 3                // error: there's no variable called 'nothing'
~ debt + 5                      // error: Sidings can't change Debt
~ echo MERIDIAN = FREED         // error: Sidings can't change Echoes
fight yard hall on floor        // error: there's no yard called 'hall'
fight yard pit floor            // error: a fight in the Deep Yards is written like
fight yard pit on depth         // error: there's no variable called 'depth'
fight pit                       // error: 'pit' is a yard
+ [Leave] -> out

== out
~ end complete
