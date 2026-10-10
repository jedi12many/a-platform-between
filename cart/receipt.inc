; A trip's receipt (docs/boarding.md), as reward.s keeps it: the C's apb_receipt, a byte at
; a time, little-endian. Offsets into `receipt`.

R_DEPARTURE     = 0             ; 2
R_TICKET        = 2             ; 4: the pass's, 0 without one
R_OUTCOME       = 6             ; 0 complete, 1 failed
R_XP            = 7             ; 2
R_DEBT_PAID     = 9             ; 2
R_DEBT_ADDED    = 11            ; 2
R_GAINED        = 13            ; a count, then 8 items (2 bytes each)
R_LOST          = 30            ; likewise
R_ECHOES        = 47            ; a count, then 8 x (id low, id high, state, state at
                                ; boarding)
R_SIZE          = 80
RECEIPT_MAX     = 8             ; entries a list (APB_RECEIPT_MAX)
