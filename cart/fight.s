; A fight (docs/vm-spec.md's FIGHT; the C version is vm/vm.c's fight): the encounter's
; record checked and set up as a battle (battle.s), the traveler at its first start with
; their health now and the first weapon they have equipped, its foes at theirs; then the
; turns till it's over, the battle screen (tactics.s) showing them and asking for the
; traveler's. Code in the fight's second asset (asset 3), copied to EXPAND_AT and run
; there (vm.s, op_fight), the story's text having no need of it till the fight's over.

        .include "hw.inc"
        .include "mem.inc"
        .include "zp.inc"
        .include "char.inc"
        .include "battle.inc"

        .export fight, fight_name
        .import encounter_count, encounters_at, traveler, item_tier, item_arch
        .import vm_fail, log_print, name_text
        .import new_fighter, fighter_from, battle_init, battle_set_tile, battle_tile
        .import battle_add, battle_start, battle_next, battle_act, tile_cost
        .import fighters, result, scene_begin, scene_turn, scene_end
        .importzp ITEM_COUNT

EQUIP_SLOTS     = 6
FOE_FIELDS      = 18                ; a foe's numbers in the record
NAME_MAX        = 20

        .segment "FIGHT"

; ----------------------------------------------------------------------------------------
; fight: encounter A, with surprise X (SURPRISE_*), played to its end.
;   Takes:   A = the encounter (vm.s has checked it's one of the depot's); X = the
;            surprise (0-2); Y = the traveler's health now.
;   Before:  this asset staged; $01 = $35.
;   After:   C clear: A = how it went (BATTLE_WON, _LOST, _FLED), X = the traveler's
;            health (1 at least: a lost fight the story carries on from leaves 1). C set:
;            the encounter's record is bad (vm_fail has said so).
;   Changes: A, X, Y; zp_enc, zp_name; and the zero page of what it calls.
fight:  sta encounter
        stx surprise
        sty health
        jsr set_up
        bcc @play
        lda #<bad_encounter
        ldx #>bad_encounter
        jmp vm_fail                 ; (C set)
@play:  lda surprise
        jsr battle_start
        jsr scene_begin
@turn:  jsr battle_next
        cmp #NOBODY
        beq @over
        sta who
        jsr scene_turn
        lda who
        jsr battle_act
        bne @turn
        lda #<cant                  ; (the screen offers only what's allowed)
        ldx #>cant
        jsr log_print
        jmp @turn
@over:  lda result
        jsr scene_end
        ldx fighters + F_HEALTH     ; (the traveler is fighter 0)
        bne @health
        inx
@health:
        lda result
        clc
        rts

; ----------------------------------------------------------------------------------------
; set_up: the encounter's record (docs/vm-spec.md, "Encounters") checked as it's read, as
; vm.c's encounter_ok checks it, and made the battle: the map, the traveler, the foes.
; After: C set if anything in it is wrong. Changes A, X, Y; zp_enc, zp_name.
set_up: lda encounters_at           ; the record: past the ones before it
        sta zp_enc
        lda encounters_at + 1
        sta zp_enc + 1
        ldx encounter
        beq @found
@skip:  ldy #0                      ; 2 + its length on
        lda (zp_enc), y
        clc
        adc #2
        pha
        iny
        lda (zp_enc), y
        adc #0
        tay
        pla
        clc
        adc zp_enc
        sta zp_enc
        tya
        adc zp_enc + 1
        sta zp_enc + 1
        dex
        bne @skip
@found: ldy #0                      ; its end: past its length
        lda (zp_enc), y
        clc
        adc #2
        sta enc_end
        iny
        lda (zp_enc), y
        adc #0
        sta enc_end + 1
        lda enc_end
        clc
        adc zp_enc
        sta enc_end
        lda enc_end + 1
        adc zp_enc + 1
        sta enc_end + 1
        lda #2
        jsr skip
        ; The map: 1-16 across, 1-10 down; each square a tile 0-7, two to a byte.
        jsr take
        bcc @ok11
        jmp @bad
@ok11:
        sta enc_w
        jsr take
        bcc @ok10
        jmp @bad
@ok10:
        sta enc_h
        lda enc_w
        bne @ok9
        jmp @bad
@ok9:
        cmp #MAP_W_MAX + 1
        bcc @ok8
        jmp @bad
@ok8:
        lda enc_h
        bne @ok7
        jmp @bad
@ok7:
        cmp #MAP_H_MAX + 1
        bcc @ok6
        jmp @bad
@ok6:
        lda enc_w
        ldx enc_h
        jsr battle_init
        lda #0
        sta nibble
        sta sq_y
@row:   lda #0
        sta sq_x
@col:   lda nibble                  ; high nibble first
        eor #1
        sta nibble
        beq @low
        jsr take
        bcc @ok5
        jmp @bad
@ok5:
        sta tile_byte
        lsr a
        lsr a
        lsr a
        lsr a
        jmp @tile
@low:   lda tile_byte
        and #$0F
@tile:  cmp #TILE_COUNT
        bcs @bad
        ldx sq_x
        ldy sq_y
        jsr battle_set_tile
        inc sq_x
        lda sq_x
        cmp enc_w
        bcc @col
        inc sq_y
        lda sq_y
        cmp enc_h
        bcc @row
        ; The starts: 1-4, the traveler at the first.
        jsr take
        bcs @bad
        sta starts
        beq @bad
        cmp #5
        bcs @bad
        lda #0                      ; the traveler, with their weapon and their health now
        tax
        jsr weapon_of
        jsr fighter_from
        lda health
        sta new_fighter + 4
        jsr take
        bcs @bad
        sta new_fighter + 2
        jsr take
        bcs @bad
        sta new_fighter + 3
        jsr battle_add
        cmp #NOBODY
        beq @bad
        ldx starts                  ; the others (a party, later): on ground in the map
@other: dex
        beq @foes
        stx sq_x
        jsr take
        bcs @bad
        pha
        jsr take
        tay
        pla
        bcs @bad
        tax
        jsr battle_tile             ; (a wall outside the map)
        jsr tile_cost
        beq @bad
        ldx sq_x
        jmp @other
@bad:   sec
        rts
@foes:  ; The foes: 1 to 8 less the starts, 18 numbers each; then their names.
        jsr take
        bcs @bad
        sta foes
        beq @bad
        lda #FIGHTERS_MAX + 1
        sec
        sbc starts
        cmp foes
        bcc @bad
        beq @bad
        lda zp_enc
        sta foes_at
        lda zp_enc + 1
        sta foes_at + 1
        ldx foes
@past:  lda #FOE_FIELDS
        jsr skip
        dex
        bne @past
        ldx #1                      ; each name: 1-20 printable characters
@name:  lda zp_enc
        sta name_lo, x
        lda zp_enc + 1
        sta name_hi, x
        jsr take                    ; (take changes Y: the count's kept apart)
        bcs @bad
        sta name_left
        tay
        beq @bad
        cmp #NAME_MAX + 1
        bcs @bad
@char:  jsr take
        bcs @bad
        cmp #$20
        bcc @bad
        cmp #$7F
        bcs @bad
        dec name_left
        bne @char
        inx
        cpx foes
        bcc @name
        beq @name
        lda zp_enc                  ; and nothing after
        cmp enc_end
        bne @bad
        lda zp_enc + 1
        cmp enc_end + 1
        bne @bad
        lda foes_at                 ; now each foe, into the battle
        sta zp_enc
        lda foes_at + 1
        sta zp_enc + 1
        lda #0
        sta foe_n
@foe:   ldx #FIELDS - 1
        lda #0
@clear: sta new_fighter, x
        dex
        bpl @clear
        lda #SIDE_FOE
        sta new_fighter
        ldy #0
@field: lda (zp_enc), y
        cmp most, y                 ; each number's range
        beq @in
        bcc @in
        cpy #15                     ; (a weakness: 0-4, or 255 for none)
        beq @ok4
        jmp @bad
@ok4:
        cmp #$FF
        beq @ok3
        jmp @bad
@ok3:
@in:    ldx field_of, y
        sta new_fighter, x
        iny
        cpy #FOE_FIELDS
        bne @field
        lda new_fighter + 4         ; some health; its most, the same
        bne @ok2
        jmp @bad
@ok2:
        sta new_fighter + 5
        jsr battle_add
        cmp #NOBODY
        bne @ok1
        jmp @bad
@ok1:
        lda #FOE_FIELDS
        jsr skip
        inc foe_n
        lda foe_n
        cmp foes
        bne @foe
        clc
        rts

; take: the record's next byte. After: A, C clear; or C set: it's ended. Changes A, Y.
take:   lda zp_enc
        cmp enc_end
        lda zp_enc + 1
        sbc enc_end + 1
        bcs @end
        ldy #0
        lda (zp_enc), y
        inc zp_enc
        bne @end                    ; (C clear)
        inc zp_enc + 1
        clc
@end:   rts

; skip: A bytes on (the reads after it check the end). Changes A.
skip:   clc
        adc zp_enc
        sta zp_enc
        bcc @same
        inc zp_enc + 1
@same:  rts

; weapon_of: the first weapon the traveler has equipped, a melee or ranged weapon or a
; focus (one of the registry's, with a tier), or 0: bare hands. After: A/X = it (low/high).
; Changes A, X, Y.
weapon_of:
        ldy #0
@slot:  lda traveler + CH_EQUIPPED + 1, y
        bne @next
        ldx traveler + CH_EQUIPPED, y
        beq @next
        cpx #ITEM_COUNT
        bcs @next
        lda item_tier, x
        beq @next
        lda item_arch, x
        cmp #ARCH_MELEE
        beq @this
        cmp #ARCH_RANGED
        beq @this
        cmp #ARCH_FOCUS
        bne @next
@this:  txa
        ldx #0
        rts
@next:  iny
        iny
        cpy #EQUIP_SLOTS * 2
        bne @slot
        lda #0
        tax
        rts

; ----------------------------------------------------------------------------------------
; fight_name: fighter A's name as the battle screen says it: the traveler's ("Kestrel"),
; or a foe's from the record ("Ash rat").
;   After:   A/X = it (low/high), ending in 0 (`said_name`: kept till the next).
;   Changes: A, X, Y; zp_name.
fight_name:
        tax
        bne @foe
        jmp name_text
@foe:   lda name_lo, x
        sta zp_name
        lda name_hi, x
        sta zp_name + 1
        ldy #0
        lda (zp_name), y
        tax                         ; its length (1-20: set_up checked)
@char:  iny
        lda (zp_name), y
        sta said_name - 1, y
        dex
        bne @char
        lda #0
        sta said_name, y
        lda #<said_name
        ldx #>said_name
        rts

; A foe's numbers in the record, in order: their most (all but the weakness: 0-4, or 255)
; and the apb_fighter field each goes to (x, y, health, grace, dodge, armor, ward, soak,
; speed, attack, damage, damage type, ranged, power, area, weakness, behavior, coward).
most:   .byte MAP_W_MAX - 1, MAP_H_MAX - 1, 255, 255, 255, 255, 255, 255, 255, 255, 255
        .byte 4, 1, 1, 4, 4, 2, 1
field_of:
        .byte 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 14, 18, 16, 17, 19, 20, 21, 22

bad_encounter:  .byte "bad encounter", 0
cant:           .byte "You can't do that.", 10, 0

        .segment "BSS"
encounter:      .res 1
surprise:       .res 1
health:         .res 1
who:            .res 1
enc_end:        .res 2
enc_w:          .res 1
enc_h:          .res 1
sq_x:           .res 1
sq_y:           .res 1
nibble:         .res 1
tile_byte:      .res 1
starts:         .res 1
foes:           .res 1
foes_at:        .res 2
foe_n:          .res 1
name_left:      .res 1
name_lo:        .res FIGHTERS_MAX       ; each foe's name in the record (1 on)
name_hi:        .res FIGHTERS_MAX
said_name:      .res NAME_MAX + 1
