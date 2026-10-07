// Departure 00: The Fare
// The first of the Arrivals (docs/lines.md). The character has just been made at the
// Waystation website.
// They wake at the Waystation, remember how they died (written for their race
// and class), meet the Stationmaster, and learn what they owe.
//
// Off the concourse, the Lost Property office holds the Fare's one fight (E3.6), with a
// porter's hook for anyone who gets past the rats: fight them, creep past them, or leave
// them be. It's its own chapter so every chapter stays small enough for the C64.

title: The Fare
id: 0
kind: official
season: 1
realm: tl 5, ml 5
levels: 1-1
start: static
linear: yes                  // a prologue: one road, on purpose

flag read_board
flag tried_to_leave
flag fen_told_you
flag asked_who
flag asked_refuse
flag got_hook
var fen_rapport = 0

// The Lost Property office: the Fare's one fight, and never the only way through.
map lost_property
    #########
    >..+..~.#
    #@.+..a.#
    #..~~.+b#
    #########
    a = ASH_RAT
    b = ASH_RAT

=== The Static

== static
~ picture static
Static.

Not the sound. The feeling: every part of you tuned to the wrong channel at
once.

Then a hand. It reaches through the end of everything, takes hold of
whatever is left of you, and pulls.

+ [Let it] -> bench
+ [Fight it] -> bench_fought

== bench_fought
You fight. It is like fighting the tide with your teeth. The hand doesn't
mind; it has done this before.
-> bench

== bench
~ picture platform_bench
You are sitting on a wooden bench, and you are breathing, and both of those
things are wrong.

The bench stands on a railway platform under a roof of green iron and
cracked glass. Beyond the glass there is no sky, only a slow grey shimmer,
like rain that has forgotten which way is down. A sign hangs from the
ironwork:

| ARRIVALS -- ALL LINES

You remember dying. You remember it very clearly.

+ [Remember it] -> memory_body

== memory_body
It comes back in pieces. First, the body it happened to.

if race HUMAN
    Flesh and bone. Ordinary, right up until the end. You were human, and
    stubbornly, luckily alive for longer than anyone expected.
else if race HOLLOWBORN
    Plate and rivets, and inside them nothing at all but a promise someone
    made a long time ago. Nothing in you could bleed, so you were the one
    who stayed standing.
else if race GLASSFOLK
    Crystal, clear as a held breath, every facet lit with a memory. You
    remembered everything. Almost everything.
else if race RAD_DRYAD
    Bark and leaf, green against the glow of a ruined sky. The fallout that
    killed the world was the sun you grew in.
else if race CHRONOMITE
    Small and quick, and always a heartbeat ahead of everyone. You saw your
    death coming a moment before it came. It didn't help.
else if race SALVAGED
    Iron joints, old code, and a vow you took from a book you found in a
    scrapyard. You were a knight. You are still technically correct about
    that.
else
    Soft grey wings and a hunger for light you were raised to call manners.
    You flew toward the brightest thing in the room. That was the problem.

Then what you were doing, when it happened.

+ [Remember the rest] -> memory_end

== memory_end
if class WARDEN
    You were holding a door. Behind it, people you had promised to protect.
    In front of it, something that did not care about promises. You held
    it for a long time. Long enough.
else if class ROGUE
    You were running, and the thing in your pack was worth more than you
    were. The floor gave way. You remember thinking: at least they'll never
    find it.
else if class TINKER
    You had the panel open and your hands inside it, and you were one wire
    away. You still think you could have done it. You were one wire away.
else if class CHANNELER
    You spoke, and the world bent, and then it bent back. The words are
    still in your mouth. You can taste them.
else
    Someone was bleeding, and you were the only one who knew how to stop
    it. You stopped it. You didn't notice what was happening to you.

if race SALVAGED
    Somewhere in your memory banks, a log entry is still open: CAUSE OF
    DEATH, followed by nothing.

That was the end. You are sure of it.

The bench creaks. Somewhere down the platform, a train whistle sounds,
mournful and far away.

+ [Stand up] -> concourse

=== The Buffer Stop

== concourse
~ picture concourse
if not visited concourse
    The platform opens into a great hall. Iron arches, a tiled floor worn into
    paths by more feet than you can imagine, and above it all a departure
    board, its letters flipping and clattering though no one is watching.

    Across the hall, warm light spills from a doorway under a painted sign: a
    rail track ending in a cheerful red barrier. THE BUFFER STOP.
else
    The great hall. The board clatters. The Buffer Stop glows.

* [Read the departure board]
    ~ set read_board
    The letters settle long enough to read:

    | KEPLER-NINE    PLAT 1  DELAYED 18 MIN
    | ASHMOUTH       PLAT 2  LAST TRAIN
    | LANTERN COURTS PLAT 3  DRESS: FORMAL

    Then they flip again, into places you have never heard of, and some you
    have heard of and know to be gone.
+ {not tried_to_leave} [Walk back to the platform edge] -> platform_edge
+ [Go into the Buffer Stop] -> bar
+ {not got_hook} [Try the door marked LOST PROPERTY] -> lost_property

== platform_edge
~ set tried_to_leave
The platform ends where the glass roof ends, and past it there is only the
grey shimmer. You reach into it.

check FATE
    crit:    Your hand goes in and comes back with a ticket stub, warm, with
             no destination printed on it. You keep it.
             ~ give TICKET_STUB
    success: Your hand goes in and comes back wet with something that isn't
             water. It's cold, and it's a little like being forgotten.
    cost:    Your hand goes in, and for a moment you can't remember your own
             face. It comes back. Most of it.
    fail:    Your hand goes in, and the shimmer pulls, and for a long moment
             you are back in the static. Then something hauls you out by the
             collar and sets you down on the tiles.

Nobody leaves the Waystation that way. You understand that now.
-> concourse

== bar
~ picture buffer_stop
The Buffer Stop is warm, and crowded, and wrong in a dozen small ways
that add up to cozy. A knight in rusted plate is arguing with a cloud of
moths. Something made of glass is drinking something made of light.

Behind the bar, a tree is wiping down glasses. Its bark glows faintly
green, and the rag in its twig-hand keeps catching fire, and it keeps
patting it out without looking.

In the corner booth, alone, sits a tall figure in a velvet coat. A brass
ledger lies closed on the table in front of it. It is watching you the
way a stationmaster watches a clock.

* [Talk to the bartender]
    "Fen," says the tree, before you can ask. "Bartender. Rad-Dryad, same as
    some of you, different as most. Drink?"
    if race RAD_DRYAD
        Fen looks at your bark, then at the poisoned glow in it, and smiles
        like family. "Oh, you poor seedling. First one's on the house."
        ~ add fen_rapport 1
    else if race SALVAGED
        "Oil, I suppose," says Fen. "No. Don't tell me. Something with a
        little rust in it, for courage."
+ {not fen_told_you} [Ask Fen where you are]
    check PERSUADE
        crit:    Fen leans in and lowers its voice. "You're at the
                 Waystation, love. You're dead. Everyone here is. The one in
                 the corner pulled you out, and you'll owe for it. Don't sign
                 anything you haven't read twice."
                 ~ set fen_told_you ~ add fen_rapport 2
        success: "The Waystation," says Fen. "You died. He pulled you out.
                 He'll explain the rest; he always does." A nod toward the
                 corner.
                 ~ set fen_told_you ~ add fen_rapport 1
        cost:    "The Waystation." Fen's rag bursts into flame. "And you're
                 asking the bartender instead of the man you owe. Bold."
                 ~ set fen_told_you
        fail:    Fen just points at the corner booth with a burning twig.
+ [Go to the corner booth] -> stationmaster

== stationmaster
~ picture stationmaster
The figure in the velvet coat rises as you approach. It is very tall. Its
face is a polite arrangement of shadow, and its voice is warm, and patient,
and has never once been surprised.

"Please, sit. You'll want to sit for this part."

It opens the brass ledger and turns it toward you. On the page, in a
careful hand, someone has begun to write your name, and stopped halfway.

"We're a little behind on the paperwork," says the Stationmaster. "Would you
mind?"

+ [Say your name] -> say_name

== say_name
"{name}," you say, and the ink finishes the word on its own.

"Of course," says the Stationmaster. "{class}. {race}. Yes, that all
matches."

Below your name, a number writes itself into the ledger, digit by digit. It
is a large number.
~ debt = 50000

"{debt}," says the Stationmaster, kindly. "Your fare."

+ [Listen] -> the_terms

== the_terms
"You were dead. Now you are not. That is a service, and services are
billed." The Stationmaster folds its long hands. "Work off your fare, and
I will put you back exactly where I found you, at exactly the moment I
found you, with one small change."

"You'll survive."

* [Ask who it is]
    ~ set asked_who
    "I keep the station," it says. "I keep the ledger. I keep the trains
    running on time, which is harder than you'd think, given that most of
    them run through it."
* [Ask what happens if you refuse]
    ~ set asked_refuse
    "Then you are free to go." It gestures at the shimmer beyond the glass
    roof. "I'd only point out that the last place you were going, you have
    already been."
    if tried_to_leave
        It glances at your hand. "Ah. You've tried the edge. Then you know."
* {fen_rapport >= 2} [Ask what Fen meant about signing]
    The shadows of its face rearrange into something like amusement. "Fen
    is a good bartender and a better friend. Read twice, by all means." It
    turns the ledger a little further toward you. "There is nothing on this
    page you didn't already agree to, the moment you let go."
+ [Accept the terms] -> accepted

== accepted
"Splendid." The Stationmaster closes the ledger. Somewhere far away, a
whistle answers.

"Your first ticket will be at the window in the morning. There is no
morning here, of course, but you'll know it when it comes. Fen will find you
a bed."

"Welcome back to the living, {name}."

~ xp 5
~ end complete

=== Lost Property

// A side room off the concourse: a fight worth having, and two roads round it.
== lost_property
if not visited lost_property
    Between a shuttered newsstand and a clock with no hands there is a narrow
    door: LOST PROPERTY. It opens onto a little office drifted with luggage
    nobody will ever come back for. Steamer trunks, hatboxes, a birdcage with
    a sleeping cloud in it.

    On the counter lies a porter's hook, long and brass and well kept, the
    only thing in the room that looks like it is waiting for someone.
else
    The Lost Property office. The hook is still on the counter.

Something shifts in the luggage. Two pairs of eyes, red as banked coals: ash
rats, nesting in a trunk, and they don't like visitors.

+ [Drive them out] -> lp_fight
+ [Creep in for the hook] -> lp_creep
+ [Leave them to it] -> concourse

== lp_creep
You keep low, and keep to the shadows of the trunks.

check STEALTH
    crit:    The rats never stir. You lift the hook from the counter and are
             out of the door before the dust settles. -> lp_hook
    success: A floorboard thinks about creaking and decides not to. You have
             the hook, and the rats have their nest. -> lp_hook
    cost:    You're halfway across when a hatbox slides. The rats turn, but
             you're closer than they would like. -> lp_jump
    fail:    A suitcase gives way under your foot with a noise like a
             gunshot, and the rats come out of the trunk all at once. -> lp_ambush

== lp_fight
fight lost_property
    won:  The last rat bolts into a hole behind the trunks, trailing sparks. -> lp_hook
    fled: You slam the door on them and lean on it until the scrabbling stops. -> concourse
    lost: The world goes grey at the edges. When it comes back, you are lying on the
          tiles of the great hall, and something has wrapped your bites in a clean bar
          towel. ~ heal 10 -> concourse

== lp_jump
fight lost_property sneak
    won:  The rats scatter into the luggage and stay there. -> lp_hook
    fled: You back out and pull the door to. -> concourse
    lost: You wake on the tiles of the great hall, bitten, with a bar towel wrapped
          round the worst of it. ~ heal 10 -> concourse

== lp_ambush
fight lost_property ambush
    won:  The rats scatter into the luggage and stay there. -> lp_hook
    fled: You stumble out and kick the door shut behind you. -> concourse
    lost: You wake on the tiles of the great hall, bitten, with a bar towel wrapped
          round the worst of it. ~ heal 10 -> concourse

== lp_hook
~ set got_hook
The porter's hook is heavier than it looks, and fits your hand as if it
had been made for it. A paper tag hangs from the handle: UNCLAIMED. Then,
as you watch, the word fades, and in the same careful hand as the
Stationmaster's ledger, your name writes itself in its place.
~ give PORTERS_HOOK
-> concourse
