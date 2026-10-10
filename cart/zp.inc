; The zero page, and who owns it (docs/cartridge.md, "The zero page"). A module uses only
; its own; scratch is anyone's between calls, never kept across one.

; text.s
zp_text_ptr     = $10           ; 2: the string being printed
zp_log_col      = $12           ; the story log's column (bottom row)
zp_word_len     = $13           ; the word being printed
zp_row          = $14           ; 2: a row of the screen
zp_row_next     = $16           ; 2: the row under it, or the row's colours

; view.s
zp_tile_at      = $18           ; 2: where a tile's characters go
zp_tile_col     = $1A           ; 2: and its colours

; copy.s and assets.s
zp_src          = $1C           ; 2: a copy's source...
zp_dst          = $1E           ; 2: ...its destination...
zp_len          = $20           ; 2: ...and its length

; command.s
zp_line         = $22           ; 2: the line being typed

; password.s
zp_pw_text      = $30           ; 2: the text being read or written
zp_pw_value     = $32           ; 2: a field's value
zp_pw_n         = $34           ; a field's bits
zp_pw_sum       = $35           ; a line's check, as it's added up

; number.s
zp_num          = $36           ; 2: the number being written

; scratch: arguments and loop counters
zp_t0           = $24
zp_t1           = $25
zp_t2           = $26
zp_t3           = $27
