// Talk in the yards (docs/rooms.md, Talk): the people and the parleys of the explore
// prototype, played by the story VM in the native arena (tools/arena/web/story.c).
//
// The page boards the party's leader at the top of a descent, and this Departure never
// ends while they're down there: it waits at `wait`, a menu for the page and not the
// player (every label starts with @), for who's being talked to on which floor, plays
// that conversation, and comes back to wait. So it remembers the whole descent: whom you
// helped, whom you robbed. Menus of one @ label are signals to the page:
//
//     @fight   the talk ends in a fight, the foes in the room
//     @leave   the foes leave the room: it's clear, without a fight
//     @join    the lost courier follows the party
//     @gone    the one you're talking to leaves the room
//     @stay    the courier stays at the camp, and stops following
//
// Checks are rolled for the leader, by the rules.

title: Talk in the Yards
id: 1001
kind: siding
realm: tl 5, ml 5
levels: 1-10
start: wait
linear: yes

var floor = 1

flag met_vell        // the trader
flag met_pell        // the courier
flag pell_helped
flag pell_robbed
flag pell_follows
flag pell_safe       // brought to the camp
flag gift_given
flag knows_shift     // the rust-guards' shift words
flag drone_scanned

=== Talk

// ------------------------------------------------------------------ the page's menus

== wait
+ [@1]
    ~ let floor = 1
    -> who
+ [@2]
    ~ let floor = 2
    -> who
+ [@3]
    ~ let floor = 3
    -> who
+ [@4]
    ~ let floor = 4
    -> who
+ [@5]
    ~ let floor = 5
    -> who
+ [@6]
    ~ let floor = 6
    -> who
+ [@7]
    ~ let floor = 7
    -> who
+ [@8]
    ~ let floor = 8
    -> who
+ [@end] -> done

== who
+ [@trader] -> vell
+ [@courier] -> pell
+ [@ASH_RAT] -> rats
+ [@SCRAP_GUNNER] -> gunners
+ [@RUST_GUARD] -> guards
+ [@MAINT_DRONE] -> drone

== done
The yards go quiet behind you.
~ end complete

== to_fight
+ [@fight] -> wait

== to_leave
+ [@leave] -> wait

// ------------------------------------------------------------------ Vell, the trader

== vell
if not met_vell
    A camp in the middle of the room: a tarpaulin strung between two signal posts, a
    stove, and a woman sitting very still on a crate of tinned peaches. She has a
    ledger on her knee and a crossbow across it.

    "Vell," she says. "I trade. I don't fight, and I don't lend." She looks you over.
    "First time down? Then here's the first thing free: the stairs are always in the
    room furthest from where you came in. Something always sits on them."
    ~ set met_vell
else if floor = 2
    Vell's camp again, a floor deeper, as if it had always been here. The stove is
    already warm. "You're slower than me," she says. "Everybody is."
else if floor = 3
    Vell has pitched her tarpaulin under a dripping pipe and doesn't seem to mind.
    "Three down. This is where people start turning back. Or stop turning at all."
else
    Vell's camp, floor {floor}. She doesn't look up from the ledger. "Still breathing.
    Good for business."

if pell_follows
    The courier behind you sees the stove and makes a small sound, like a kettle.
    -> vell_pell
if pell_robbed and not visited vell_cold
    -> vell_cold
if pell_safe and not gift_given
    -> vell_gift
-> vell_menu

== vell_menu
+ {not pell_robbed} [What have you got?] -> vell_trade
+ [What's on this floor?] -> vell_rumour
* {not met_pell and floor = 1} [Seen anyone else down here?]
    "A courier went down ahead of you. Young, fast, no sense. Has a satchel of
    letters for people who aren't down here." She shrugs. "Floor two, maybe."
+ [Move on] -> wait

== vell_cold
"A courier came through," Vell says, not looking at you. "Said someone took a gun
off them at the point of a knife." She closes the ledger. "I don't trade with that."

+ [Talk her round]
    check PERSUADE hard
        success: She looks at you a long time. "Once," she says. "Don't make me sorry."
                 ~ clear pell_robbed
                 -> vell_menu
        cost:    "Words are cheap. Trade's not." But she opens the ledger again.
                 ~ clear pell_robbed
                 -> vell_menu
        fail:    "No." The crossbow hasn't moved, but it feels closer.
+ [Leave it] -> wait

== vell_trade
"Gear for gear," Vell says. "Mine's better. Yours is here."

* {has PADDED_COAT} [Padded coat for a chain coat]
    She weighs the coat in one hand, sniffs it, and throws a chain coat at you.
    ~ take PADDED_COAT ~ give CHAIN_COAT
* {has SCRAP_PISTOL} [Scrap pistol for an arc pistol]
    "This thing's held together with hope." She takes it anyway.
    ~ take SCRAP_PISTOL ~ give ARC_PISTOL
* {has RUSTED_SABRE} [Rusted sabre for an iron sword]
    ~ take RUSTED_SABRE ~ give IRON_SWORD
    "Rust is a kind of history," she says, and hangs it on a nail.
* {has IRON_SWORD and has CHAIN_COAT} [Sword and coat for ballistic weave]
    She whistles. From under the peaches comes a roll of ballistic weave, the good kind.
    ~ take IRON_SWORD ~ take CHAIN_COAT ~ give BALLISTIC_WEAVE
+ [Nothing for now] -> vell_menu

== vell_rumour
if floor = 1
    "Rats on the first floors. They bite, they run, they come back. Shout at them; they
    hate shouting."
else if floor = 2
    "Gunners. Scrap-built and proud of it. Most of them would rather be paid than
    shoot, if you've got something that goes bang."
else if floor = 3
    "The rust-guards are still on shift. A hundred years and nobody told them. They
    answer to the shift words, if you can find out what they are."
else
    "Drones, down here. Old maintenance units. They don't hate you; they think you're
    a fault. Hold still and they'll try to fix you."
-> vell_menu

== vell_pell
"Oh, you found the courier." Vell stands up for the first time. "Sit. Eat. Nobody
eats down here unless I say so." The courier sits, and eats, and is asleep before the
tin is empty.

"Kind of you," Vell says to you, which sounds like it costs her.
~ clear pell_follows ~ set pell_safe ~ set gift_given
~ xp 20
The courier wakes long enough to press something into your hands: their own coat,
patched at both elbows, chain sewn into the lining. "For the cold," they say, and are
gone again.
~ give CHAIN_COAT
-> pell_stays

== pell_stays
+ [@stay] -> vell_menu

== vell_gift
"Your courier went back up," Vell says. "Left this for you. Said you'd know why."
It's an iron sword, wrapped in letters.
~ set gift_given
~ give IRON_SWORD
-> vell_menu

=== Pell

// ------------------------------------------------------------------ Pell, the courier

== pell
if not met_pell
    Against the wall, half behind a fallen locker, someone in a courier's jacket is
    trying to look like part of the locker. They're young, scratched, and holding a
    satchel of letters as if it were the last warm thing in the yards.

    "Don't," they say. "I'm Pell. I'm just lost. The stairs moved."
    ~ set met_pell
else
    Pell is still here, still holding the satchel. "You came back," they say, not sure
    yet if that's good.
-> pell_menu

== pell_menu
* [Ask about the letters]
    "Letters for people in the yards. Down here. Somebody has to." Pell looks at the
    satchel. "Nobody told me there'd be rats."
+ [Show Pell the way up]
    check SURVIVAL
        success: You walk Pell through it: the furthest door, the cage at the top,
                 the way the yards turn. They repeat it back twice. Then they go.
                 ~ set pell_helped ~ xp 10
                 -> pell_gone
        cost:    You explain, badly. Pell nods as if they understood and heads off in
                 roughly the right direction.
                 ~ set pell_helped
                 -> pell_gone
        fail:    You try. The yards don't stay where you say they are. Pell looks
                 more lost than before.
+ [Come with us. There's a camp.]
    Pell gets up so fast the satchel spills. "Yes. Please. I'll be quiet."
    ~ set pell_follows
    -> pell_join
+ {has ARC_PISTOL or has SCRAP_PISTOL} [Give them your spare sidearm]
    if has ARC_PISTOL
        ~ take ARC_PISTOL
    else
        ~ take SCRAP_PISTOL
    Pell holds it like a letter they're afraid to open. "I'll give it back," they
    say. "When I'm not lost."
    ~ set pell_helped ~ xp 10
    -> pell_gone
+ [That satchel. Hand it over.]
    check PRESENCE
        success: Pell looks at your hands, then your face, and empties the satchel at
                 your feet: letters, and under them an arc pistol, never fired. Then
                 they run.
        cost:    Pell throws the satchel at you and runs. Letters everywhere, and in
                 them an arc pistol.
        fail:    Pell bolts before you finish the sentence, and leaves the satchel
                 behind in the hurry. There's a pistol in it.
    ~ give ARC_PISTOL ~ set pell_robbed
    -> pell_gone
+ [Leave them be] -> wait

== pell_join
+ [@join] -> wait

== pell_gone
+ [@gone] -> wait

=== Parleys

// ------------------------------------------------------------------ parleys

== rats
Ash rats, a whole family of them, the size of dogs and the colour of a cold fire.
They've seen you. They're deciding whether you're food.
if pell_robbed
    One of them has a letter in its mouth. You know whose.

+ [Shout them down]
    check PRESENCE
        success: You roar. The rats scatter into the pipes and don't come back.
                 -> to_leave
        cost:    They back off, slowly, hissing, and then they're gone.
                 -> to_leave
        fail:    Your shout cracks in the middle. The rats take it as an invitation.
                 -> to_fight
+ [Edge round them quietly]
    check STEALTH tricky
        success: You keep to the walls. By the time they look up, there's nothing there
                 to look at, and they wander off.
                 -> to_leave
        fail:    A loose plate rings under your boot. Every head turns.
                 -> to_fight
+ [Fight] -> to_fight

== gunners
Scrap gunners: bolted-together barrels, bolted-together faces, every one of them aimed
at you. "Toll," says the biggest. "Or a hole. You pick."

+ {has SCRAP_PISTOL} [Pay the toll with a scrap pistol]
    The big one turns your pistol over and grins. "Family." They step aside.
    ~ take SCRAP_PISTOL
    -> to_leave
+ {has ARC_PISTOL} [Pay with an arc pistol]
    That shuts them all up. "Energy weapon," one says, reverently. They let you through.
    ~ take ARC_PISTOL
    -> to_leave
+ [Talk them out of it]
    check PERSUADE tricky
        success: "A toll on the way down? Who's coming down? Charge them on the way up."
                 They think about it, nod, and go to wait by the stairs up.
                 -> to_leave
        cost:    They argue among themselves long enough that you could leave, so they
                 let you. One of them shoots the ceiling anyway, on principle.
                 -> to_leave
        fail:    "Hole it is."
                 -> to_fight
+ [Fight] -> to_fight

== guards
Rust-guards at their posts, the way they've stood for a hundred years. One lifts a
lantern. "Shift words," it grinds. "Or leave the yard."

* [Look at the guard post]
    check LORE
        success: Painted on the post, under the rust: a rota, and beside today's
                 shift, two words. You mouth them.
                 ~ set knows_shift
        cost:    A rota, half eaten by rust. You get one word, and guess the other.
                 ~ set knows_shift
        fail:    Rust. And under the rust, more rust.
+ {knows_shift} [Say the shift words]
    The lantern dips. "Pass, worker." They turn back to the wall, and stay there.
    -> to_leave
+ [Bluff: "Inspection."]
    check PERSUADE hard
        success: "Inspection," the guard repeats, and stands even straighter. They
                 file out to be inspected somewhere else.
                 -> to_leave
        fail:    "There has not been an inspection in one hundred and four years."
                 -> to_fight
+ [Fight] -> to_fight

== drone
A maintenance drone drifts out of the dark, scanning. Its light finds you and stays.
"FAULT," it says. "FAULT. FAULT."

* [Read its maintenance plate]
    check TECH
        success: An old model. There's a reset port under the plate, and the plate is
                 loose.
                 ~ set drone_scanned
        fail:    The plate says DO NOT. The rest is scratched off.
+ {drone_scanned} [Reset it]
    check TECH easy
        success: You find the port and hold the switch. The drone hums, forgets you,
                 and floats off to fix a pipe.
                 -> to_leave
        fail:    It catches you at it. "FAULT," it says, and means it.
                 -> to_fight
+ [Hold very still]
    check GRIT tricky
        success: You stand still while it scans you top to bottom. "NO FAULT," it
                 decides at last, and drifts away.
                 -> to_leave
        fail:    You flinch. "FAULT FOUND."
                 -> to_fight
+ [Fight] -> to_fight
