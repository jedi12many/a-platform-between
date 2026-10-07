// Clearing flags past the first byte. cc65 2.19 once compiled the VM's CLR so that, on
// the 6502, flags 8 and up stayed set (Eighteen Minutes resets its station with them).
// The menu between setting and clearing is where the save test saves.
title: Flags
id: 902
kind: branch
realm: tl 1, ml 2
levels: 1-2
start: a

flag f0
flag f1
flag f2
flag f3
flag f4
flag f5
flag f6
flag f7
flag f8
flag f9
flag f10

== a
~ set f0 ~ set f7 ~ set f8 ~ set f9 ~ set f10
Five flags are set.
+ [Clear three] -> b

== b
~ clear f0 ~ clear f9 ~ clear f10
~ clear f1
if f0
    Flag 0 is still set.
if f1
    Flag 1 is set.
if f7
    Flag 7 is set, as it should be.
if f8
    Flag 8 is set, as it should be.
if f9
    Flag 9 is still set.
if f10
    Flag 10 is still set.
if not f2 and not f3 and not f4 and not f5 and not f6
    The rest were never set.
~ end complete
