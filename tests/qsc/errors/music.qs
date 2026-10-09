// ~ music: names checked against music.music beside this file.
title: Music
id: 957
kind: branch
realm: tl 3, ml 3
levels: 1-3
start: platform

== platform
The lamps hum. ~ music night_train
~ music night_trian                             // error: no tune called 'night_trian' in music.music. Did you mean 'night_train'?
~ music off
~ music                                         // error: music NAME' or '~ music off
~ music Night                                   // error: tune name 'Night' should be lower_case_with_underscores
~ music a_name_that_is_far_too_long             // error: is too long: 20 letters at most
~ end complete
