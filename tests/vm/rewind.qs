// A Rewind forgets the Echoes its Departure plants. This test Departure takes id 2, The
// Last Train Out of Ashmouth's, because the registry says Departure 2 plants WOLF_PUP.
// A traveler whose pup is already SWORN sees the grown wolf; on a Rewind, the pup again.
title: Rewind Test
id: 2
kind: official
season: 1
realm: tl 6, ml 1
levels: 1-5
start: ash
linear: yes

== ash
if echo WOLF_PUP = SWORN
    A grown dire wolf pads out of the ash and sits by your boot.
else
    A pup whimpers in the ash.
+ [Pick it up] -> done

== done
~ echo WOLF_PUP = SAVED
~ xp 10
~ end complete
