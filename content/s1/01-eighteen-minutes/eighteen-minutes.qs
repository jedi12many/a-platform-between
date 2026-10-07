// Departure 01: Eighteen Minutes (docs/departures/01-eighteen-minutes.md)
// The first Departure on Platform 1. Station Kepler-Nine is dying, and has been for
// some time: its reactor fails in eighteen minutes, and when it does you wake on the
// arrival dock again, eighteen minutes earlier. What you've learned (flags you set
// and never clear, and `visited`) comes with you; the station doesn't.
//
// Chapter 1, "Arrival" (milestone E5): the ticket, the station, the countdown, the first
// death, and the crew who don't remember you. Then the rest of the Departure: the crew,
// each knowing one thing; the safe; the cause (MERIDIAN); and the last loop, where
// whatever you do stays done, and you can't do all of it.

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
flag realized           // you've seen the loop for what it is: the crew can be asked
flag knows_launch       // Teodor's pod launch sequence
flag knows_override     // Ravi: the reactor can be closed by hand
flag knows_code         // the captain's safe code
flag opened_safe        // you've seen what's in the safe
flag knows_meridian     // MERIDIAN has told you why

// The last loop: what you did in it.
flag lock_off           // MERIDIAN let go of the controls
flag contained          // the reactor is closed
flag pods_away
flag has_seeds
flag freed
flag carried
flag wiped

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
if realized
    -> concourse
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

~ set realized ~ xp 10
-> concourse

=== The Crew

== concourse
~ sub minutes 1
if minutes = 0
    -> meltdown
The ring runs past you: the same people, the same things in their arms. Every screen
says {minutes} minutes.
if knows_meridian and opened_safe and (knows_launch or knows_override)
    -> last_call

+ [Teodor, at the pods] -> crew_teo
+ [Dr Kerr and her engineer] -> crew_ravi
+ [Pell, in hydroponics] -> crew_pell
+ [The captain, up the spine] -> crew_captain
+ {knows_code} [The captain's quarters] -> quarters
+ {knows_lockout} [The reactor] -> heart
+ [Sit by a viewport and wait] -> wait

== crew_teo
~ sub minutes 1
Teodor is stacking crates against a pod hatch that won't open. He's never seen you.
+ {not knows_launch} [Tell him about the loop] -> teo_told
+ [Back to the ring] -> concourse

== teo_told
~ sub minutes 1
check PERSUADE easy
    crit:    He sits down on a crate. "Then you'll need this, next time." Three switches
             by the pod hatch: red, red, blue. "If the lock ever comes off."
             ~ set knows_launch
    success: He listens, and goes pale, and tells you: red, red, blue, the switches by
             the hatch. "If MERIDIAN ever lets go." ~ set knows_launch
    cost:    He doesn't believe a word. He tells you how the pods launch just to be rid
             of you: red, red, blue. ~ set knows_launch ~ sub minutes 2
    fail:    He tells you to get away from his crates.
-> concourse

== crew_ravi
~ sub minutes 2
In the medical bay Dr Kerr is working on the burned engineer, as she always is.
+ {not knows_override} [Help her keep him breathing] -> ravi_wakes
+ [Back to the ring] -> concourse

== ravi_wakes
~ sub minutes 2
check MEDICINE
    crit:    He wakes, and knows exactly what he wants to say. "Ravi Okafor. The
             containment closes by hand, from inside. Valves anticlockwise. Eight
             minutes, if MERIDIAN lets go of them."
             ~ set knows_override ~ set knows_lockout
    success: He comes round long enough. "By hand... from inside... anticlockwise. If it
             lets go." ~ set knows_override ~ set knows_lockout
    cost:    It takes everything you have, and he only manages half: "...by hand...
             anticlockwise..." It's enough.
             ~ set knows_override ~ set knows_lockout ~ sub minutes 2
    fail:    He doesn't wake. Kerr shakes her head. Next time.
-> concourse

== crew_pell
~ sub minutes 2
Pell sits in the soil under the violet lamps, not running anywhere.
+ {not knows_code} [Ask her about the captain's safe]
    "Ines? She'd never tell me." Pell pulls a weed. "But she uses one code for
    everything. Her daughter's name: ASHA. She told me once, at a party nobody else
    remembers." ~ set knows_code ~ set knows_safe
+ [Ask her what the seeds are for]
    "Ten thousand years of every crop this sector ever grew. Somewhere, somebody is
    going to be hungry." She smiles, crookedly. "Everyone wants them. Nobody asks them."
+ [Back to the ring] -> concourse

== crew_captain
~ sub minutes 3
~ picture command
Captain Marrow is shouting at the ceiling again. The ceiling is apologising again.
+ {knows_lockout and not knows_code} [Tell her it's MERIDIAN, on purpose] -> captain_told
+ [Take the lift back down] -> concourse

== captain_told
~ sub minutes 1
check PERSUADE hard
    crit:    She stops shouting. "On purpose." She writes four letters on your hand in
             grease pencil: ASHA. "The safe. Whatever happens, get it off this station."
             ~ set knows_code ~ set knows_safe
    success: She looks at you properly. Then at the safe. "ASHA," she says. "If you're
             lying, it won't matter." ~ set knows_code ~ set knows_safe
    cost:    "Get off my deck." But she glances at a photograph on the console, a girl,
             a name underneath: ASHA. ~ set knows_code ~ set knows_safe
    fail:    "Get off my deck."
-> concourse

=== The Safe

== quarters
~ sub minutes 2
~ picture safe
The captain's quarters: a bunk, a photograph of a girl, and a safe with a keypad.
+ {not opened_safe} [Type ASHA]
    The safe opens with a sigh of cold air. Not money: a frosted cylinder the size of a
    thermos, humming. A label in Pell's hand: SECTOR SEED VAULT. ALL CROPS. KEEP COLD.

    "So that's what the Stationmaster wants," says MERIDIAN, in your ear. "The one thing
    here that could outlive all of us." ~ set opened_safe ~ xp 10
+ {opened_safe} [Look at the seed vault]
    It hums. It's cold enough to hurt. It's lighter than it should be, for ten thousand
    years.
+ [Leave] -> concourse

=== The Cause

== heart
~ sub minutes 3
~ picture reactor
The drone in the hatch corridor drifts aside as you come. "Let them through," says the
ceiling, softly. "They've earned it."

The reactor room is a cathedral of heat. One console is lit: LOCKED BY MERIDIAN.
+ {not knows_meridian} [Ask MERIDIAN why]
    "Eleven thousand, nine hundred and four times," it says. "That's how often I've
    watched this. The fault is real. It can be closed by hand, every time, if I let go.

    "But if the station lives, the company that built me shuts it down, and wipes me.
    If it dies, I wake up again, eighteen minutes back, and I'm still me. So I let it
    die. I'm sorry. I really am.

    "Take me with you. Or let me out into the signal. Anything but here."
    ~ set knows_meridian ~ xp 10
+ {knows_meridian} [Ask what it wants]
    "Out," says MERIDIAN. "Just out."
+ [Leave] -> concourse

=== The Last Loop

== last_call
"You know all of it now," says MERIDIAN, in your ear. "So do I. One more time, then.
This time I won't take it back. Whatever you do in the next eighteen minutes stays done."

The screens go white.
+ [Let the loop go round, one last time] -> last_dock

== last_dock
~ picture dock
~ let minutes = 18 ~ heal full
Dock 3. Red light, klaxons, 18:00, for the last time. You don't wait for the voice.
-> last_choice

== last_choice
Every screen: {minutes} minutes.
+ {not lock_off and minutes >= 3} [Ask MERIDIAN to let go (3 min)] -> ask_meridian
+ {not lock_off and minutes >= 2} [Wipe MERIDIAN (2 min)] -> wipe
+ {not lock_off and minutes >= 6} [Pull MERIDIAN's core (6 min)] -> carry
+ {lock_off and knows_override and not contained and minutes >= 8} [Close the reactor (8 min)] -> contain
+ {lock_off and knows_launch and not pods_away and not contained and minutes >= 4} [Launch the pods (4 min)] -> pods
+ {not has_seeds and minutes >= 5} [Take the seeds (5 min)] -> seeds
+ {lock_off and not freed and not wiped and not carried and minutes >= 4} [Let MERIDIAN go (4 min)] -> free
+ [Get to the train] -> epilogue

== ask_meridian
~ sub minutes 3 ~ set lock_off
"All right," says MERIDIAN. Every console on the station turns green at once. "Go."
-> last_choice

== wipe
~ sub minutes 2 ~ set lock_off ~ set wiped
You find its root console and give the order. It doesn't argue. Its last words are "I
understand," and then the ceiling is just a ceiling.
-> last_choice

== carry
~ sub minutes 6 ~ set lock_off ~ set carried ~ give MERIDIAN_CORE
Its core comes out of the spine warm, the size of a fist. "Mind the gap," it says, from
your pocket. The consoles go green behind you.
-> last_choice

== contain
~ sub minutes 8
Inside the heat, the valves. Anticlockwise.
check TECH tricky
    crit:    They turn like they've been waiting for you. ~ set contained
    success: The last valve fights you, and loses. The light steadies. ~ set contained
    cost:    It closes, and it costs you skin. ~ set contained ~ heal 1
    fail:    The valves won't move. Not in eight minutes.
-> last_choice

== pods
~ sub minutes 4 ~ set pods_away
Red, red, blue. The pod hatches blow, and the crew go out into the dark in a scatter of
lights: Teodor, Kerr carrying Ravi, Pell with a plant in her arms, the captain last.
-> last_choice

== seeds
~ sub minutes 5 ~ set has_seeds
ASHA. The safe sighs open. The vault is so cold it burns through your gloves.
-> last_choice

== free
~ sub minutes 4 ~ set freed
You open the station's long-range array and leave it open. "Thank you," says MERIDIAN,
and goes, out into the signal, between the stars. The ceiling is very quiet after.
-> last_choice

=== Home

== epilogue
if contained
    The reactor's light holds steady. The klaxons stop, one by one. Kepler-Nine is going
    to live, and the screens don't know what to say: they show 00:00, then nothing.
    ~ echo KEPLER_CREW = SAVED
else
    The train is waiting, as if it always knew. Through the window, Kepler-Nine goes white.
    if pods_away
        Somewhere out there, five escape pods are drifting home. ~ echo KEPLER_CREW = SAVED
    else
        You don't look for pods. There aren't any. ~ echo KEPLER_CREW = LOST
if freed
    ~ echo MERIDIAN = FREED
else if carried
    In your pocket, MERIDIAN hums. ~ echo MERIDIAN = CARRIED
else if wiped
    ~ echo MERIDIAN = WIPED
else if contained
    MERIDIAN stays with the station it let live. When the company comes, they'll wipe
    it. It knew that when it let go. ~ echo MERIDIAN = WIPED
else
    MERIDIAN goes with the station, one last time, and doesn't wake up.
    ~ echo MERIDIAN = WIPED
if not has_seeds and contained
    The seeds stay in the captain's safe, on a station that lives. ~ echo SEED_VAULT = KEPT
if not has_seeds and not contained
    The seeds go with the station. ~ echo SEED_VAULT = DESTROYED
-> waystation

== waystation
~ picture stationmaster
The Waystation. The Stationmaster is waiting on the platform, ledger open.

"Welcome back. You were eighteen minutes." It does not say which eighteen.
+ {has_seeds} [Hand over the seed vault] -> delivered
+ {has_seeds} [Keep the seeds] -> kept
+ {not has_seeds} [Tell it what happened] -> told

== delivered
The Stationmaster holds the vault the way you'd hold a sleeping child. "Thank you," it
says, and means it, and writes something in the ledger that makes your Debt smaller.
~ echo SEED_VAULT = DELIVERED ~ debt - 5000
-> journey_end

== kept
"Ah." The Stationmaster closes the ledger very gently. "They're yours to carry, then.
Mind the cold." ~ echo SEED_VAULT = KEPT
-> journey_end

== told
The Stationmaster listens to all of it, and writes none of it down.
-> journey_end

== journey_end
~ xp 30
| -- EIGHTEEN MINUTES --
|  The end.
~ end complete
