; A traveler, as the game keeps one in RAM (passport.s fills it from a Passport or a
; Boarding Pass, and writes a Passport from it). Offsets into the record; its fields are
; the Passport's (docs/passport-spec.md), one byte each unless it says.

CH_NAME         = 0             ; 8: ASCII capitals and the name alphabet's -'.!? and
                                ; space, padded with spaces
CH_RACE         = 8
CH_CLASS        = 9
CH_LEVEL        = 10
CH_XP           = 11
CH_STATS        = 12            ; 6: Might, Grace, Grit, Wits, Presence, Fate
CH_STAT_POINTS  = 18
CH_SKILL_POINTS = 19
CH_DEBT         = 20            ; 2: low, high
CH_FLAGS        = 22
CH_TAGS         = 23            ; 2: a bit a skill, low byte first (12 bits)
CH_TRAINING     = 25            ; 16: a skill's training, 0 if untrained (a Passport's
                                ; skill field has 4 bits, so 16 places)
CH_POWER_COUNT  = 41
CH_POWERS       = 42            ; 15 x (id, rank), in slot order
CH_EQUIPPED     = 72            ; 8 slots x (item low, item high): $FFFF if empty
CH_PACK         = 88            ; likewise
CH_ECHO_COUNT   = 104
CH_ECHOES       = 105           ; 15 x (id low, id high, state), oldest first
CH_SIZE         = 150

EMPTY_SLOT      = $FF           ; an equipped or pack slot's high byte when it's empty

; A Boarding Pass's own fields (passport.s's `pass`), before the traveler it carries.
PASS_DEPARTURE  = 0             ; 2
PASS_TICKET     = 2             ; 4: low byte first
PASS_SEED       = 6             ; 2
PASS_REWIND     = 8             ; 1: 0 or 1
PASS_SIZE       = 9

; What passport.s says of a password.
PW_OK           = 0
PW_SYMBOL       = 1             ; something that isn't one of the alphabet's
PW_LINE         = 2             ; a line's check symbol is wrong (pw_bad_line says which)
PW_LENGTH       = 3             ; too short, or too long, or a line under 2 symbols
PW_CHECKSUM     = 4             ; every line right, the whole not
PW_VERSION      = 5             ; neither a Passport (2) nor a pass (8)
PW_TOO_BIG      = 6             ; (encoding) a field that doesn't fit its bits

KIND_PASSPORT   = 2             ; a password's first 4 bits
KIND_PASS       = 8
