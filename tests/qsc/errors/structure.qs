title: Structure
id: 951
kind: branch
realm: tl 3, ml 3
levels: 1-3
start: a

flag ok
flag never                                      // warning: flag 'never' is declared but never used

== a
Some text.
if ok
    + [Hidden] -> a                             // error: choices go at the end of a scene
else
    Not hidden.
+ [Go] -> b
After the choices.                              // error: only choices can come after
+ [This label is far too long to fit on one C64 line] -> a  // error: the most is 37

== b
else                                            // error: 'else' without an 'if'
{ok} at the start.                              // error: a line can't start with '{'
	Tabbed.                                     // error: a tab in the indentation
check TECH
    sucess: Nope.                               // error: Did you mean 'success'?
+ [Back] -> a
+ [Both] -> a                                   // error: not both
    A body too.

== stuck        // error: the player would be stuck // warning: can never be reached
Nothing to do here.
~ set ok
