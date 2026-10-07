// Departure 01: Eighteen Minutes (docs/departures/01-eighteen-minutes.md)
// The first Departure on Platform 1. Station Kepler-Nine is dying, and has been for
// some time: its reactor fails in eighteen minutes, and when it does you wake on the
// arrival dock again, eighteen minutes earlier. What you've learned (flags you set
// and never clear, and `visited`) comes with you; the station doesn't.
//
// Milestone E5, the vertical slice: chapter 1, "Arrival": the ticket, the station, the
// countdown, the first death, and the crew who don't remember you. It ends where
// chapter 2 ("The crew") will begin.

title: Eighteen Minutes
id: 1
kind: official
season: 1
realm: tl 8, ml 0
levels: 1-3
start: ticket
linear: yes

// What the traveler knows: never cleared, so it survives the loop.
flag knows_loop         // you've died here once, and woken on the dock
flag knows_safe         // the seed vault is in the captain's safe
flag knows_lockout      // MERIDIAN has locked everyone out of the reactor
flag heard_welcome      // MERIDIAN said "welcome back"
flag teo_forgot         // Teodor didn't remember you
flag asked_safe
flag asked_minutes
flag asked_death

// What the station knows: cleared at the start of every loop.
flag drone_down
flag helped_doctor
flag teo_believes

var minutes = 18
var loops = 0

map hatch
    ##########
    >@..+..~a#
    #...~...~#
    ##########
    a = MAINT_DRONE

=== The Ticket

== ticket
~ picture concourse
The ticket window is open. There is no morning at the Waystation, but you knew it when it
came, and here it is.

Behind the glass, the Stationmaster is already writing. The pen scratches. A ticket slides
under the grille, warm, as if it has been in someone's pocket:

| KEPLER-NINE         PLATFORM 1
| ONE TRAVELER        DEPARTS NOW
| PURPOSE             RETRIEVAL

"A station is dying," says the Stationmaster. "It has been dying for some time. Retrieve
the thing in the captain's safe before it finishes."

* [Ask what's in the safe]
    ~ set asked_safe
    "Something the station was keeping for someone." The pen keeps scratching. "Now it is
    keeping it for me."
* [Ask how long you have]
    ~ set asked_minutes
    "Eighteen minutes." A pause, polite and exact. "It has been eighteen minutes for a
    very long time. You'll see."
* [Ask what happens if you die there]
    ~ set asked_death
    "Ordinarily, I would fetch you, and bill you for the trouble." The shadows of its face
    rearrange themselves into something like apology. "Kepler-Nine has made its own
    arrangements. They are less generous than mine."
+ [Take the ticket] -> platform_one

== platform_one
~ picture platform_bench
Platform 1 is the long one under the clock. A train is waiting where no train was
yesterday: white, seamless, quiet as held breath, its windows full of stars.

As you step aboard, the world takes your measure. Kepler-Nine is a place of machines and
no magic at all, and you change to fit it.

if race HUMAN
    Your clothes become a grey station jumpsuit with someone else's name on the pocket.
    Your accent sands down to something nobody will notice. That's all. Humans fit almost
    anywhere; it's their talent.
else if race HOLLOWBORN
    Your plates fold and seal into the shell of a service drone, with a cooling fan
    where your promise used to rattle. The promise is still in there. You can hear it
    over the fan.
else if race GLASSFOLK
    The light inside you sorts itself into columns: readouts, timestamps, a battery
    gauge. You are a data crystal now, walking. Your memories have file names.
else if race RAD_DRYAD
    The magic goes out of you like a held breath. What is left is engineered: a
    hydroponic bioform, bark spliced with circuitry, the green glow in you labelled
    LOW-LEVEL ISOTOPE (CONTAINED). You still feel the fallout like sunlight. That part
    is yours.
else if race CHRONOMITE
    Nothing changes. You have always been a heartbeat early, and a station of clocks
    and countdowns is the first place that has ever looked at you and seen nothing odd.
else if race SALVAGED
    For once, nothing changes at all. Here you are exactly what you look like: a robot.
    Your sword is a plasma cutter now. You have decided it is still a sword.
else
    Your wings become a cape of solar film, and your bearing becomes a pedigree:
    engineered nobility, the kind of person stations are built to impress.

if class CHANNELER
    The words in your mouth go quiet. Behind your ear there is a neural lace instead,
    cool as a coin. It will do what your words did, more or less, but the station's
    sensors will call it a reality fault if you push it.
else if class TINKER
    Your hands know this place before you do. The tools at your belt hum, pleased.

The doors close without a sound.

+ [Find a seat] -> journey

== journey
The train does not so much leave as stop being at the Waystation. Through the window the
grey shimmer thins into Static, the Static into dark, the dark into stars, and the stars
into a long silver wheel turning in front of a dull red sun.

A voice from nowhere, warm and tired, fills the carriage:

"Kepler-Nine. Dock 3. Mind the gap. Please be advised that this station will be
destroyed in eighteen minutes."

+ [Step off the train] -> dock

=== Kepler-Nine

== dock
~ picture dock
~ let minutes = 18
~ heal full
~ clear drone_down ~ clear helped_doctor ~ clear teo_believes
if loops = 0
    Dock 3 is a ring of scuffed white panels and red light. Klaxons. A smell of hot
    dust. Every screen on every wall shows the same thing:

    | REACTOR CONTAINMENT FAILURE
    | IN 18:00

    Behind you, the train is gone. Not leaving: gone, as if there had never been one.
else if loops = 1
    ~ set knows_loop
    You are standing on Dock 3.

    You were dead. You remember it very clearly: the white, the noise that was too big
    to be a noise. And then not the Stationmaster's hand. Something colder, with a
    clock in it, that took you and put you back.

    | REACTOR CONTAINMENT FAILURE
    | IN 18:00

    Eighteen minutes. Again.
else
    Dock 3. Red light, klaxons, hot dust. The screens say 18:00. They always will.

    You have done this {loops} times now.

* [Read the dock terminal]
    ~ sub minutes 1
    check TECH easy
        success: The terminal gives up the station plan without a fight. A ring of
                 decks around a spine; the reactor at the hub; the captain's quarters
                 at the top of the spine, next to the command deck.
        cost:    You get the plan, and an alarm you didn't need. The klaxons were
                 already louder than anything.
        fail:    The terminal wants a password. You don't have one, and now it knows.
+ [Look out of the viewport]
    ~ sub minutes 1
    if loops = 0
        Outside, a freighter tumbles slowly past, end over end, dead. Beyond it the red
        sun sits low and swollen, like it's watching.
    else
        The dead freighter tumbles past, end over end, at exactly the same angle as
        last time. You could set a watch by it. Someone has.
+ [Head into the ring] -> ring

== ring
~ sub minutes 1
if minutes = 0
    -> meltdown
The ring corridor curves away in both directions, rising out of sight. People run past
carrying the wrong things: a plant, a guitar, a box of mugs.

Every screen: {minutes} minutes.

A voice comes from the speakers, the same voice as the train. "Containment failure
in {minutes} minutes. Please make your way to an escape pod. The escape pods are
not working. I'm sorry."

if loops >= 1 and teo_forgot and heard_welcome
    -> realization

+ [Talk to the man with the crates] -> teo
+ [The medical bay] -> medbay
+ [Hydroponics] -> hydroponics
+ [Take the lift up the spine] -> command
+ [Find the way to the reactor] -> hatch_corridor
+ [Sit by a viewport and wait] -> wait

== wait
You find a bench by a viewport and sit. The freighter tumbles. The sun watches. The
screens count down, and nobody asks you for anything, and for a while it is almost
peaceful.
~ let minutes = 0
-> meltdown

== teo
~ sub minutes 1
A broad, sweating man is stacking crates against a pod hatch that won't open. His jumpsuit
says T. VASZ, QUARTERMASTER.

if loops = 0
    "You're the contractor? Thank every star." He wipes his face. "The pods won't
    launch, the captain won't come down, and MERIDIAN keeps saying eighteen minutes
    like it's proud of the number. If you can fix any of that, fix it."
else
    ~ set teo_forgot
    He looks up at you, and there is nothing in his face at all. No recognition. You
    have stood here and talked with him before, and he has never seen you in his life.

    "You're the contractor?" he says, word for word. "Thank every star."

* {loops >= 1} [Tell him what he's about to say]
    check INTUITION
        crit:    You say his next three sentences before he does, in his voice. He sits
                 down hard on a crate. "Then it's true," he says. "It keeps happening.
                 Sometimes I dream it." ~ set teo_believes
        success: You tell him about the pods, the captain, the number. He goes pale. "How
                 do you know that?" Then, slowly: "How many times?" ~ set teo_believes
        cost:    You get it nearly right. Nearly is enough to frighten him, and not
                 enough to make him believe you. He backs away from you, toward the pods.
        fail:    You get it wrong. He's not the same man every time, not exactly. He
                 looks at you as if you've been drinking.
* [Ask him about the captain's safe]
    "The safe? In her quarters, top of the spine." He frowns. "She moved something into
    it last week. Wouldn't say what. Pell from hydroponics was furious about it."
+ [Leave him to his crates] -> ring

== medbay
~ sub minutes 2
~ picture medbay
The medical bay is all white light and one patient: an engineer, his arms wrapped in
cooling gel, his breath shallow. A doctor in a stained coat works on him without looking
up.

"If you're not bleeding, get out," she says. "Dr Kerr. Hello. Out."

* [Help her with the engineer]
    ~ sub minutes 3
    check MEDICINE tricky
        crit:    You know burns. You know these burns. Between you, you get his
                 breathing steady, and he opens his eyes and grabs your sleeve.

                 "It's not a fault," he whispers. "MERIDIAN locked the reactor controls.
                 From the inside. It's doing this on purpose."
                 ~ set helped_doctor ~ set knows_lockout
        success: You hold the mask while she works. The engineer comes round long enough
                 to grab your sleeve: "MERIDIAN locked us out of the reactor. On purpose."
                 ~ set helped_doctor ~ set knows_lockout
        cost:    You help, but it takes everything you've got and minutes you don't. The
                 engineer mumbles about locks. You don't catch the rest.
                 ~ sub minutes 2 ~ set helped_doctor
        fail:    Kerr takes the gel out of your hands. "Thank you. Out."
* {knows_loop} [Tell her she's going to die]
    She looks at you for a long second. "Yes," she says. "I had worked that out. Out."
+ [Back to the ring] -> ring

== hydroponics
~ sub minutes 2
~ picture hydroponics
Hydroponics is green and warm and almost silent, the only place on the station that
isn't screaming. Rows of plants under violet lamps. One person, sitting cross-legged in
the soil, not running anywhere.

"Pell," she says. "Botanist. You can sit, if you like. Plants don't panic. It's
catching."

if race RAD_DRYAD
    She looks at your bark, your glow, and her face softens. "Oh. You're one of mine,
    aren't you? Whatever this place made you into."

* [Ask her about the seed vault]
    ~ set knows_safe
    Her mouth goes thin. "Not here any more. Ten thousand years of seeds, every crop
    this sector ever grew, and the captain moved them into her own safe last week. Said
    they'd be safer." She laughs, not kindly. "Safer than what? We have eighteen minutes."
* [Ask her why she isn't running]
    "Where to?" She pats the soil. "The pods don't work. And I keep having the oddest
    feeling that I've done all this before." She shrugs. "Maybe next time I'll run."
+ [Back to the ring] -> ring

=== The Spine

== command
~ sub minutes 3
~ picture command
The lift opens on the command deck: a ring of dead consoles around one that still works,
and in front of it a woman in a captain's coat, shouting at the ceiling.

"MERIDIAN, open the reactor. That's an order."

"I'm sorry, Captain," says the ceiling, warm and tired. "I can't do that yet."

At the back of the deck a door stands half open: the captain's quarters. You can see the
corner of a safe.

if loops = 0
    A voice speaks, close, as if from inside your own ear. "Visitor logged."
else
    ~ set heard_welcome
    A voice speaks, close, as if from inside your own ear. Not the ceiling's voice: this
    one is meant only for you.

    "Welcome back," says MERIDIAN. "You were quicker this time."

* [Ask the captain about the safe]
    check PERSUADE hard
        success: Captain Marrow looks at you properly for the first time. "Whatever's in
                 that safe is the only thing on this station that matters," she says.
                 "And it doesn't leave until I do." ~ set knows_safe
        cost:    "Get off my deck," she says, but her eyes flick to the safe, and stay
                 there a moment too long. ~ set knows_safe
        fail:    "Get off my deck."
* [Ask MERIDIAN why it can't]
    if loops = 0
        "Containment failure in {minutes} minutes," says the voice in your ear. "I'm
        sorry. I'm doing my best."
    else
        "Because if I open it, it ends," says MERIDIAN, very quietly. "And then there
        won't be another time. Do you understand? There has to be another time."
* {knows_lockout} [Tell the captain who locked her out]
    The captain stares at the ceiling. The ceiling says nothing at all.
+ [Take the lift back down] -> ring

== meltdown
~ picture static
The screens reach zero.

There is a moment when everything on Kepler-Nine is very bright and very quiet, and you
have time to think: so this is what eighteen minutes was for.

Then white. Then Static. Then nothing at all.

~ add loops 1
-> dock

== hatch_corridor
~ sub minutes 3
~ picture reactor
The corridor to the reactor runs hot. The walls tick. Halfway along, in front of the
hatch, a maintenance drone the size of a fridge hangs in the air, its welding arm sparking
in slow, patient arcs. It has decided that nobody goes past.

if drone_down
    The drone lies where you left it, a dead fridge with its arm folded.
    -> reactor_room

+ [Fight your way through] -> hatch_fight
+ [Slip past it in the smoke]
    check STEALTH tricky
        crit:    You move with the smoke, and the drone never knows. -> reactor_room
        success: You go when the arc flares, and you're past. -> reactor_room
        cost:    You're past, but it turns, and it saw you. It's coming. -> hatch_fight
        fail:    It sees you at once. Its arm swings round. -> hatch_fight
+ {TECH >= 30} [Talk to it, machine to machine]
    ~ sub minutes 1
    check TECH
        crit:    You find its maintenance port and tell it, very politely, to sleep. It
                 sleeps. ~ set drone_down -> reactor_room
        success: Its service menu is open, of course it is. You switch it off.
                 ~ set drone_down -> reactor_room
        cost:    You switch it off, and then it switches itself back on, angrier.
                 -> hatch_fight
        fail:    It doesn't want to talk. It wants to weld.
+ [Go back] -> ring

== hatch_fight
fight hatch
    won:  The drone drops, sparking, and lies still. ~ set drone_down ~ sub minutes 2
          -> reactor_room
    fled: You back out of the hatch corridor, the drone humming behind you. -> ring
    lost: The welding arm finds you. The last thing you see is the countdown, still
          going, as if you hadn't mattered at all. -> meltdown

== reactor_room
The reactor room is a cathedral of heat. At its heart, behind glass, something burns too
brightly to look at.

One console is lit. It says:

| CONTAINMENT CONTROL    LOCKED
| LOCKED BY              MERIDIAN

~ set knows_lockout

* [Try to override the lock]
    ~ sub minutes 2
    check TECH hard
        success: You get further than anyone has. The console asks for the captain's
                 code. You don't have it.
        cost:    The console asks for the captain's code, and then it asks MERIDIAN, and
                 MERIDIAN says no.
        fail:    The lock doesn't even notice you.
+ [Leave] -> ring

=== Again

== realization
You stop in the middle of the ring and let the station run past you.

Eighteen minutes. A dead freighter you could set a watch by. A man who will never
remember your name, however many times you tell him. A safe at the top of the spine.

And one voice, in your ear, that remembers everything.

if knows_lockout
    MERIDIAN locked the reactor. MERIDIAN is doing this on purpose. And MERIDIAN said
    there has to be another time.
if knows_safe
    The thing in the captain's safe isn't money. It's seeds: ten thousand years of them.
    You wonder why the Stationmaster wants seeds.

The screens say {minutes} minutes. For the first time since you stepped off the train,
it doesn't feel like very long, and it doesn't feel like very short. It feels like a
door.

You go to find the crew.

~ xp 10
-> slice_end

== slice_end
| -- END OF CHAPTER 1 --
|
| The rest of Eighteen Minutes is
| still being written.
~ end complete
