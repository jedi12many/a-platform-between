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

; rules.s
zp_rule         = $38           ; 2: a rule's working number

; vm.s
zp_ip           = $3A           ; 2: the next byte of the running code (CAR_AT + 9 + pc)
zp_str          = $3C           ; 2: the string being expanded
zp_out          = $3E           ; 2: where its text goes

; qr.s, qrview.s (at a trip's end)
zp_qr           = $40           ; 2: a module's place in the QR code, or the view's bitmap

; fight.s, fightext.s (in a fight)
zp_enc          = $42           ; 2: the encounter's record (in the depot)
zp_name         = $44           ; 2: a foe's name

; the music player (fe/c64/music.s for the cartridge): only it, from the raster
; interrupt, or with interrupts off
zp_music        = $46           ; 6

; scratch: arguments and loop counters
zp_t0           = $24
zp_t1           = $25
zp_t2           = $26
zp_t3           = $27

; The walking engine (cart/walk/, docs/walk.md): its own program, so this is its alone.
; The interrupt uses none of it.
zp_wk_ptr       = $50           ; 2: a row of the squares, or of a screen being drawn
zp_wk_out       = $52           ; 2: where generated code or an edge's cells go
zp_wk_src       = $54           ; 2: an address being written into generated code
zp_wk_dst       = $56           ; 2: and the other one
zp_wk_n         = $58           ; 2: a count
zp_wk_fx        = $5A           ; 2: fits: the body's pixel x...
zp_wk_fy        = $5C           ; 2: ...and y
zp_wk_mv        = $5E           ; 2: slide: where the moved axis would be
zp_wk_a         = $60           ; 2: 16-bit working values
zp_wk_b         = $62           ; 2
zp_wk_mx        = $64           ; an edge's character column on the area
zp_wk_my        = $65           ; and row
zp_wk_i         = $66           ; a loop's counter
zp_wk_d         = $67           ; slide: the step, signed
zp_wk_axis      = $68           ; slide: the axis, 0 (x) or 2 (y)
zp_wk_x0        = $69           ; fits: the squares under the body
zp_wk_x1        = $6A
zp_wk_y0        = $6B
zp_wk_y1        = $6C
zp_wk_t         = $6D           ; scratch
