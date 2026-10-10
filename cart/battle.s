; The battle (docs/combat.md; the C version is core/src/battle.c, and this plays the same,
; event for event): a map, its fighters, the order of play, moving and sight, attacks and
; free attacks, guarding and waiting, fleeing, the foes' rules (and quick, which plays a
; traveler by them), and the endings. Everything follows the order of play, the actions
; and the dice, so a battle replays exactly. Code in the fight's asset (asset 2), run
; where it's staged; its state is in the resident engine's RAM.
;
; What happens is told a step at a time through battle_event (ev_kind and the rest), which
; the battle screen hears (event_hook), and tests/cart/test_battle.py reads.

        .include "zp.inc"
        .include "battle.inc"

        .export battle_init, battle_set_tile, battle_tile, battle_add, battle_start
        .export battle_next, battle_act, battle_quick, battle_can_reach, battle_reach
        .export battle_can_attack, battle_tn, battle_event, event_hook
        .export fighters, map_w, map_h, fighter_count, result, round_no, map_tiles, cost_to
        .export ev_kind, ev_actor, ev_target, ev_x, ev_y, ev_value, ev_roll, ev_total
        .export ev_tn, ev_result, act_x, act_y, act_kind, act_target
        .import new_fighter, hit_tn, damage, dmg, flee_tn, tile_cost, tile_blocks
        .import d100, check, resolve, chk_roll, chk_total, chk_tn, chk_result

        .segment "BATTLE"

; ----------------------------------------------------------------------------------------
; battle_init: an empty battle on a map of open ground, w x h (16 x 10 at most), that
; nobody hears till event_hook is set.
;   Takes:   A = w; X = h.
;   Changes: A, X.
battle_init:
        pha
        lda #<no_event
        sta event_hook
        lda #>no_event
        sta event_hook + 1
        pla
        cmp #MAP_W_MAX + 1
        bcc @w
        lda #MAP_W_MAX
@w:     sta map_w
        txa
        cmp #MAP_H_MAX + 1
        bcc @h
        lda #MAP_H_MAX
@h:     sta map_h
        lda #TILE_OPEN
        ldx #MAP_W_MAX * MAP_H_MAX - 1
@clear: sta map_tiles, x
        dex
        cpx #$FF
        bne @clear
        lda #0
        sta fighter_count
        sta round_no
        sta next_at
        sta begun
        sta surprise
        sta result
        rts

; square: X, Y (column, row) as an index into the map's rows of 16. After: A. Changes A.
square: tya
        asl a
        asl a
        asl a
        asl a
        stx sq_x
        ora sq_x
        rts

; battle_set_tile: square X, Y (inside the map) is tile A. Changes A, X, Y.
battle_set_tile:
        cpx map_w
        bcs @out
        cpy map_h
        bcs @out
        pha
        jsr square
        tax
        pla
        sta map_tiles, x
@out:   rts

; battle_tile: the tile at X, Y; a wall outside the map. After: A. Changes A, X.
battle_tile:
        cpx map_w
        bcs @wall
        cpy map_h
        bcs @wall
        jsr square
        tax
        lda map_tiles, x
        rts
@wall:  lda #TILE_WALL
        rts

; ----------------------------------------------------------------------------------------
; battle_add: the fighter in new_fighter (combat.s; apb_fighter's order) into the battle,
; in the fight, guarding and waiting not; its health no more than its most.
;   After:   A = its number; or NOBODY: the battle is full, or its square can't hold it
;            (outside the map, a wall or a pit, or someone there).
;   Changes: A, X, Y.
battle_add:
        lda fighter_count
        cmp #FIGHTERS_MAX
        bcs @no
        ldx new_fighter + 2         ; its square
        cpx map_w
        bcs @no
        ldy new_fighter + 3
        cpy map_h
        bcs @no
        jsr battle_tile
        jsr tile_cost
        beq @no
        ldx new_fighter + 2
        ldy new_fighter + 3
        jsr who_at
        cmp #NOBODY
        bne @no
        ldx fighter_count           ; field k to row k
        ldy #0
@field: lda new_fighter, y
        sta fighters, x
        txa
        clc
        adc #FIGHTERS_MAX
        tax
        iny
        cpy #FIELDS
        bne @field
        ldx fighter_count
        lda #IN_FIGHT
        sta fighters + F_STATE, x
        lda #0
        sta fighters + F_GUARDING, x
        sta fighters + F_WAITED, x
        lda fighters + F_HEALTH_MAX, x
        cmp fighters + F_HEALTH, x
        bcs @health
        sta fighters + F_HEALTH, x
@health:
        inc fighter_count
        txa
        rts
@no:    lda #NOBODY
        rts

; who_at: the fighter in the fight at X, Y. After: A = it, or NOBODY. Keeps X, Y.
who_at: stx at_x
        sty at_y
        ldx #0
@who:   cpx fighter_count
        bcs @nobody
        lda fighters + F_STATE, x
        bne @next
        lda fighters + F_X, x
        cmp at_x
        bne @next
        lda fighters + F_Y, x
        cmp at_y
        bne @next
        txa
        jmp @done
@next:  inx
        bne @who                    ; (always)
@nobody:
        lda #NOBODY
@done:  ldx at_x
        ldy at_y
        rts

; ----------------------------------------------------------------------------------------
; battle_start: the order of play, and the first round: highest Grace first, travelers
; before foes on a tie, then the order they joined (an insertion sort). On a surprise, a
; round 0 first, the side's who sprang it.
;   Takes:   A = SURPRISE_*.
;   Changes: A, X, Y.
battle_start:
        sta surprise
        ldx #0
@id:    txa
        sta base, x
        inx
        cpx fighter_count
        bcc @id
        ldx #1
@sort:  cpx fighter_count
        bcs @sorted
        stx sort_i
@back:  ldy base - 1, x             ; p: before; q: this one
        sty sort_p
        ldy base, x
        sty sort_q
        lda fighters + F_GRACE, y   ; q first if its Grace is higher, or the same and q's
        ldy sort_p                  ; a traveler and p a foe
        cmp fighters + F_GRACE, y
        beq @tie
        bcs @swap
        bcc @stay                   ; (always)
@tie:   ldy sort_q
        lda fighters + F_SIDE, y
        ldy sort_p
        cmp fighters + F_SIDE, y
        bcs @stay
@swap:  lda sort_p
        sta base, x
        lda sort_q
        sta base - 1, x
        dex
        bne @back
@stay:  ldx sort_i
        inx
        jmp @sort
@sorted:
        jsr base_order
        ldx #1                      ; round 1, or 0 for a surprise
        lda surprise
        beq @round
        dex
@round: stx round_no
        lda #0
        sta next_at
        sta begun
        sta result
        rts

; base_order: this round's order, the order of play. Changes A, X.
base_order:
        ldx #FIGHTERS_MAX - 1
@copy:  lda base, x
        sta order, x
        dex
        bpl @copy
        rts

; ----------------------------------------------------------------------------------------
; dist: how far X, Y is from dist_x, dist_y: the most of the two differences (a diagonal
; step is 1). After: A. Changes A.
dist:   txa
        sec
        sbc dist_x
        bcs @dx
        eor #$FF
        adc #1
@dx:    sta dist_dx
        tya
        sec
        sbc dist_y
        bcs @dy
        eor #$FF
        adc #1
@dy:    cmp dist_dx
        bcs @done
        lda dist_dx
@done:  rts

; dist_to: how far fighter X is from fighter Y. After: A. Changes A; keeps X, Y.
dist_to:
        stx dt_a
        sty dt_b
        lda fighters + F_X, y
        sta dist_x
        lda fighters + F_Y, y
        sta dist_y
        lda fighters + F_Y, x
        tay
        lda fighters + F_X, x
        tax
        jsr dist
        ldx dt_a
        ldy dt_b
        rts

; ----------------------------------------------------------------------------------------
; reach: what it costs fighter A to reach each square this turn, up to its Speed, in
; cost_to ($FF: it can't): the cheapest way, a cost at a time from 0 (a square costs 1, 2
; for rough ground and cover; walls and pits can't be entered, nor anyone's square). The
; same as battle.c's passes to a standstill, in fewer steps.
;   Changes: A, X, Y.
reach:  sta reach_who
        tax
        lda fighters + F_SPEED, x
        sta reach_speed
        lda #$FF                    ; nobody can get anywhere; and who's where
        ldx #MAP_W_MAX * MAP_H_MAX - 1
@clear: sta cost_to, x
        sta occupied, x
        dex
        cpx #$FF
        bne @clear
        ldy #0
@who:   cpy fighter_count
        bcs @placed
        lda fighters + F_STATE, y
        bne @gone
        ldx fighters + F_X, y
        sty reach_i
        lda fighters + F_Y, y
        tay
        jsr square
        tax
        lda reach_i
        sta occupied, x
        ldy reach_i
@gone:  iny
        bne @who                    ; (always)
@placed:
        ldy reach_who               ; its own square: 0
        ldx fighters + F_X, y
        lda fighters + F_Y, y
        tay
        jsr square
        tax
        lda #0
        sta cost_to, x
        sta reach_level
@level: lda #0                      ; every square at this cost: on to its neighbours
        sta reach_y
@row:   lda #0
        sta reach_x
@col:   ldx reach_x
        ldy reach_y
        jsr square
        tax
        lda cost_to, x
        cmp reach_level
        bne @next
        jsr relax
@next:  inc reach_x
        lda reach_x
        cmp map_w
        bcc @col
        inc reach_y
        lda reach_y
        cmp map_h
        bcc @row
        inc reach_level
        lda reach_level
        cmp reach_speed
        bcc @level
        rts

; relax: from square reach_x, reach_y (at cost reach_level), each of the 8 around it: its
; cost, if this way is cheaper and within the Speed. Changes A, X, Y.
relax:  ldx #7
@dir:   stx relax_d
        lda reach_x
        clc
        adc step_x, x
        cmp map_w                   ; (off the left wraps past it)
        bcs @next
        sta relax_nx
        lda reach_y
        clc
        adc step_y, x
        cmp map_h
        bcs @next
        tay
        ldx relax_nx
        jsr square
        tax
        lda occupied, x             ; someone there
        cmp #NOBODY
        bne @next
        stx relax_sq
        lda map_tiles, x
        jsr tile_cost
        beq @next                   ; a wall, a pit
        clc
        adc reach_level
        cmp reach_speed
        beq @fits
        bcs @next
@fits:  ldx relax_sq
        cmp cost_to, x
        bcs @next
        sta cost_to, x
@next:  ldx relax_d
        dex
        bpl @dir
        rts

; battle_can_reach: can fighter A get to X, Y this turn? After: A = 1 or 0. Changes A, X,
; Y.
battle_can_reach:
        cmp fighter_count
        bcs @no
        cpx map_w
        bcs @no
        cpy map_h
        bcs @no
        stx can_x
        sty can_y
        jsr reach
        ldx can_x
        ldy can_y
        jsr square
        tax
        lda cost_to, x
        cmp #$FF
        beq @no
        lda #1
        rts
@no:    lda #0
        rts

; battle_reach: every square fighter A can reach this turn, in cost_to (not $FF), in one
; pass: for the battle screen's marks. Changes A, X, Y.
battle_reach = reach

; ----------------------------------------------------------------------------------------
; in_sight: can a shot from sight_x0, sight_y0 reach sight_x1, sight_y1? Walls block it;
; so does anyone standing between, but the shooter (sight_who) and the target. Bresenham's
; line, as battle.c steps it. After: A = 1 or 0. Changes A, X, Y.
in_sight:
        lda sight_x1                ; dx, dy; their signs
        sec
        sbc sight_x0
        ldx #1
        bcs @dx
        eor #$FF
        adc #1
        ldx #$FF
@dx:    sta sight_dx
        stx sight_sx
        lda sight_x0                ; (x0 < x1: +1, else -1)
        cmp sight_x1
        bcc @sx
        lda #$FF
        sta sight_sx
@sx:    lda sight_y1
        sec
        sbc sight_y0
        bcs @dy
        eor #$FF
        adc #1
@dy:    sta sight_dy
        lda #1
        sta sight_sy
        lda sight_y0
        cmp sight_y1
        bcc @sy
        lda #$FF
        sta sight_sy
@sy:    lda sight_dx                ; err = dx - dy
        sec
        sbc sight_dy
        sta sight_err
        lda sight_x0
        sta sight_x
        lda sight_y0
        sta sight_y
@step:  lda sight_x                 ; there?
        cmp sight_x1
        bne @on
        lda sight_y
        cmp sight_y1
        bne @on
        lda #1
        rts
@on:    lda sight_x                 ; past the start: a wall, or someone, blocks it
        cmp sight_x0
        bne @look
        lda sight_y
        cmp sight_y0
        beq @move
@look:  ldx sight_x
        ldy sight_y
        jsr square
        tax
        lda map_tiles, x
        jsr tile_blocks
        bcs @blocked
        ldx sight_x
        ldy sight_y
        jsr who_at
        cmp #NOBODY
        beq @move
        cmp sight_who
        bne @blocked
@move:  lda sight_err               ; e2 = 2 err
        asl a
        sta sight_e2
        clc                         ; e2 > -dy: e2 + dy > 0
        adc sight_dy
        beq @no_x
        bmi @no_x
        lda sight_err
        sec
        sbc sight_dy
        sta sight_err
        lda sight_x
        clc
        adc sight_sx
        sta sight_x
@no_x:  lda sight_e2                ; e2 < dx: e2 - dx < 0
        sec
        sbc sight_dx
        bpl @no_y
        lda sight_err
        clc
        adc sight_dx
        sta sight_err
        lda sight_y
        clc
        adc sight_sy
        sta sight_y
@no_y:  jmp @step
@blocked:
        lda #0
        rts

; ----------------------------------------------------------------------------------------
; battle_can_attack: can fighter can_who attack fighter can_target from can_x, can_y?
; Someone else, in the fight; not with a blast that would catch its thrower; next to it
; for melee, in sight from afar.
;   Takes:   can_who, can_target, can_x, can_y.
;   After:   A = 1 or 0. Changes A, X, Y.
battle_can_attack:
        ldx can_who
        cpx fighter_count
        bcs @no
        ldy can_target
        cpy fighter_count
        bcs @no
        cpx can_target
        beq @no
        lda fighters + F_STATE, y
        bne @no
        lda fighters + F_X, y
        sta dist_x
        lda fighters + F_Y, y
        sta dist_y
        ldx can_x
        ldy can_y
        jsr dist
        sta can_d
        ldx can_who
        lda fighters + F_AREA, x
        beq @aimed
        cmp can_d                   ; the blast would reach the thrower
        bcs @no
@aimed: lda fighters + F_RANGED, x
        bne @far
        lda can_d                   ; melee: next to it
        cmp #1
        bne @no
        lda #1                      ; (again: the cmp left Z set)
        rts
@far:   lda can_x
        sta sight_x0
        lda can_y
        sta sight_y0
        ldy can_target
        lda fighters + F_X, y
        sta sight_x1
        lda fighters + F_Y, y
        sta sight_y1
        stx sight_who
        jmp in_sight
@no:    lda #0
        rts

; battle_tn: the TN for fighter X to hit fighter Y (apb_battle_tn), in chk_tn: their Dodge,
; their Armor (none against the damage type they're weak to; Ward against a power), and
; cover against a shot. Changes A, X, Y.
battle_tn:
        stx tn_a
        sty tn_t
        lda fighters + F_POWER, x
        beq @armor
        lda fighters + F_WARD, y
        jmp @defense
@armor: lda fighters + F_DMG_TYPE, x
        cmp fighters + F_WEAK_TYPE, y
        beq @weak
        lda fighters + F_ARMOR, y
        jmp @defense
@weak:  lda #0
@defense:
        sta tn_defense
        lda #0
        sta tn_bonus
        lda fighters + F_RANGED, x  ; cover, against a shot
        beq @tn
        ldx fighters + F_X, y
        lda fighters + F_Y, y
        tay
        jsr battle_tile
        cmp #TILE_COVER
        bne @tn
        lda #COVER_BONUS
        sta tn_bonus
@tn:    ldy tn_t
        lda fighters + F_DODGE, y
        ldx tn_defense
        ldy tn_bonus
        jsr hit_tn
        ldx tn_a
        ldy tn_t
        rts

; ----------------------------------------------------------------------------------------
; emit: an event (ev_kind A, ev_actor X, ev_target Y; ev_value set already) told: the
; actor's square with it, if there is an actor. Changes A; keeps X, Y.
emit:   sta ev_kind
        stx ev_actor
        sty ev_target
        cpx #NOBODY
        beq battle_event
        lda fighters + F_X, x
        sta ev_x
        lda fighters + F_Y, x
        sta ev_y
        ; (on into battle_event)

; battle_event: whoever listens hears it (event_hook: the battle screen; an RTS till one
; does). tests/cart/test_battle.py reads the event here, so don't rename it. Keeps X, Y
; for the battle (the hook must too).
battle_event:
        jmp (event_hook)

; value: ev_value = A (high byte 0). Changes nothing else.
value:  sta ev_value
        pha
        lda #0
        sta ev_value + 1
        pla
        rts

; ----------------------------------------------------------------------------------------
; check_end: the fight's over? Won: no foes in it, a traveler is; lost: no traveler in it,
; none fled; fled: no traveler in it, one fled. Told once. Changes A, X, Y.
check_end:
        lda result
        bne @done
        lda #0
        sta end_travelers
        sta end_foes
        sta end_fled
        ldx #0
@who:   cpx fighter_count
        bcs @counted
        lda fighters + F_STATE, x
        bne @out
        lda fighters + F_SIDE, x
        beq @traveler
        inc end_foes
        bne @next                   ; (always)
@traveler:
        inc end_travelers
        bne @next                   ; (always)
@out:   cmp #GONE
        bne @next
        lda fighters + F_SIDE, x
        bne @next
        inc end_fled
@next:  inx
        bne @who                    ; (always)
@counted:
        lda end_foes
        bne @travelers
        lda end_travelers
        beq @travelers
        lda #BATTLE_WON
        bne @ended                  ; (always)
@travelers:
        lda end_travelers
        bne @done
        lda #BATTLE_LOST
        ldx end_fled
        beq @ended
        lda #BATTLE_FLED
@ended: sta result
        jsr value
        lda #EV_END
        ldx #NOBODY
        ldy #NOBODY
        jmp emit
@done:  rts

; hurt: fighter X takes dmg's damage: down at 0; a coward at a quarter of its most runs
; off. Changes A, X, Y.
hurt:   lda dmg + 1
        bne @down
        lda fighters + F_HEALTH, x
        cmp dmg
        bcc @down
        beq @down
        sec
        sbc dmg
        sta fighters + F_HEALTH, x
        lda fighters + F_COWARD, x  ; 4 x health <= its most?
        beq @done
        lda fighters + F_HEALTH, x
        sta hurt_4
        lda #0
        sta hurt_4 + 1
        asl hurt_4
        rol hurt_4 + 1
        asl hurt_4
        rol hurt_4 + 1
        lda fighters + F_HEALTH_MAX, x
        cmp hurt_4
        lda #0
        sbc hurt_4 + 1
        bcc @done
        lda #GONE                   ; runs off
        sta fighters + F_STATE, x
        lda #0
        jsr value
        lda #EV_GONE
        ldy #NOBODY
        jmp emit
@down:  lda #0
        sta fighters + F_HEALTH, x
        lda #DOWN
        sta fighters + F_STATE, x
        lda #0
        jsr value
        txa
        tay
        lda #EV_DOWN
        ldx #NOBODY
        jmp emit
@done:  rts

; ----------------------------------------------------------------------------------------
; attack: fighter att_who attacks fighter A: one roll, +10 from high ground onto lower;
; compared with the target's TN, or, for an area attack, with each fighter's in the
; blast. Each one's damage told, and taken. Changes A, X, Y.
attack: sta att_target
        lda #0
        sta att_bonus
        ldx att_who                 ; high ground, onto lower
        ldy fighters + F_Y, x
        lda fighters + F_X, x
        tax
        jsr battle_tile
        cmp #TILE_HIGH
        bne @rolled
        ldy att_target
        ldx fighters + F_X, y
        lda fighters + F_Y, y
        tay
        jsr battle_tile
        cmp #TILE_HIGH
        beq @rolled
        lda #HIGH_GROUND_BONUS
        sta att_bonus
@rolled:
        ldy att_target              ; the blast's centre
        lda fighters + F_X, y
        sta att_cx
        lda fighters + F_Y, y
        sta att_cy
        jsr d100
        sta att_roll
        lda #0
        sta att_i
@each:  ldx att_i
        cpx fighter_count
        bcc @in
        rts
@in:    lda fighters + F_STATE, x
        beq @near7
        jmp @next
@near7:
        ldy att_who
        lda fighters + F_AREA, y
        beq @single
        sta att_area                ; in the blast: within the area each way
        lda fighters + F_X, x
        sec
        sbc att_cx
        bcs @ax
        eor #$FF
        adc #1
@ax:    cmp att_area
        beq @ay
        bcc @near6
        jmp @next
@near6:
@ay:    lda fighters + F_Y, x
        sec
        sbc att_cy
        bcs @ay2
        eor #$FF
        adc #1
@ay2:   cmp att_area
        beq @hit
        bcc @near5
        jmp @next
@near5:
        jmp @hit
@single:
        cpx att_target
        bne @next
@hit:   lda att_roll                ; the roll, the total, the TN, the outcome
        sta chk_roll
        ldy att_who
        clc
        adc fighters + F_ATTACK, y
        sta chk_total
        lda #0
        adc #0
        sta chk_total + 1
        lda chk_total
        clc
        adc att_bonus
        sta chk_total
        bcc @total
        inc chk_total + 1
@total: ldx att_who
        ldy att_i
        jsr battle_tn
        jsr resolve
        ldx att_who                 ; its damage: melee's stat bonus, the target's Soak
        lda fighters + F_RANGED, x
        beq @melee
        lda #0
        beq @bonus                  ; (always)
@melee: lda fighters + F_STAT_BONUS, x
@bonus: sta att_stat
        ldy att_i
        lda fighters + F_SOAK, y
        tay
        lda fighters + F_WEAPON, x
        ldx att_stat
        jsr damage
        jsr roll_event
        lda dmg
        sta ev_value
        lda dmg + 1
        sta ev_value + 1
        lda #EV_ATTACK
        ldx att_who
        ldy att_i
        jsr emit
        lda dmg
        ora dmg + 1
        beq @next
        ldx att_i
        jsr hurt
@next:  inc att_i
        jmp @each

; roll_event: the roll as the event's (chk_*). Changes A.
roll_event:
        lda chk_roll
        sta ev_roll
        lda chk_total
        sta ev_total
        lda chk_total + 1
        sta ev_total + 1
        lda chk_tn
        sta ev_tn
        lda chk_tn + 1
        sta ev_tn + 1
        lda chk_result
        sta ev_result
        rts

; ground_hurts: fighter X, on a hazard, takes its damage less its Soak (if that's any).
; Changes A, X, Y.
ground_hurts:
        stx ground_who
        ldy fighters + F_Y, x
        lda fighters + F_X, x
        tax
        jsr battle_tile
        cmp #TILE_HAZARD
        bne @safe
        ldx ground_who
        lda #HAZARD_DAMAGE
        sec
        sbc fighters + F_SOAK, x
        beq @safe
        bcc @safe
        sta dmg
        jsr value
        lda #0
        sta dmg + 1
        lda #EV_HAZARD
        ldy #NOBODY
        jsr emit
        jmp hurt
@safe:  rts

; free_attack: fighter X's free attack on fighter Y, if both are in the fight and X can hit
; Y from where it stands. Changes A, X, Y.
free_attack:
        lda fighters + F_STATE, x
        ora fighters + F_STATE, y
        bne @no
        stx can_who
        sty can_target
        lda fighters + F_X, x
        sta can_x
        lda fighters + F_Y, x
        sta can_y
        jsr battle_can_attack
        beq @no
        lda #0
        jsr value
        lda #EV_FREE
        ldx can_who
        ldy can_target
        jsr emit
        stx att_who
        tya
        jmp attack
@no:    rts

; ----------------------------------------------------------------------------------------
; move_to: fighter move_who to move_x, move_y: first a free attack from each foe it pulls
; away from; then there, the ground's harm; then a free attack from each foe on guard it
; comes up to. Changes A, X, Y.
move_to:
        ldx move_who
        lda fighters + F_X, x
        sta move_sx
        lda fighters + F_Y, x
        sta move_sy
        cmp move_y
        bne @moving
        lda move_sx
        cmp move_x
        bne @moving
        rts
@moving:
        lda #0
        sta move_i
@away:  ldx move_i                  ; foes next to it, not next to where it's going
        cpx fighter_count
        bcs @go
        ldy move_who
        lda fighters + F_SIDE, x
        cmp fighters + F_SIDE, y
        beq @a_next
        jsr dist_to
        cmp #1
        bne @a_next
        lda move_x
        sta dist_x
        lda move_y
        sta dist_y
        lda fighters + F_Y, x
        tay
        lda fighters + F_X, x
        tax
        jsr dist
        cmp #2
        bcc @a_next
        ldx move_i
        ldy move_who
        jsr free_attack
@a_next:
        inc move_i
        jmp @away
@go:    ldx move_who
        lda fighters + F_STATE, x
        beq @there
        rts
@there: lda move_x
        sta fighters + F_X, x
        lda move_y
        sta fighters + F_Y, x
        lda #0
        jsr value
        lda #EV_MOVE
        ldy #NOBODY
        jsr emit
        jsr ground_hurts
        lda #0
        sta move_i
@guards:
        ldx move_i                  ; foes on guard it's come up to
        cpx fighter_count
        bcs @done
        lda fighters + F_GUARDING, x
        beq @g_next
        ldy move_who
        lda fighters + F_SIDE, x
        cmp fighters + F_SIDE, y
        beq @g_next
        jsr dist_to
        cmp #1
        bne @g_next
        lda move_sx
        sta dist_x
        lda move_sy
        sta dist_y
        lda fighters + F_Y, x
        tay
        lda fighters + F_X, x
        tax
        jsr dist
        cmp #2
        bcc @g_next
        ldx move_i
        lda fighters + F_STATE, x
        bne @g_next
        lda #0
        sta fighters + F_GUARDING, x
        ldy move_who
        jsr free_attack
@g_next:
        inc move_i
        jmp @guards
@done:  rts

; foes_next_to: how many of fighter X's foes in the fight stand next to it. After: A.
; Changes A, Y.
foes_next_to:
        lda #0
        sta next_n
        ldy #0
@who:   cpy fighter_count
        bcs @done
        lda fighters + F_STATE, y
        bne @next
        lda fighters + F_SIDE, y
        cmp fighters + F_SIDE, x
        beq @next
        jsr dist_to
        cmp #1
        bne @next
        inc next_n
@next:  iny
        bne @who                    ; (always)
@done:  lda next_n
        rts

; flee: fighter X tries to get out: on an exit it's out; anywhere else, Athletics against
; the flee TN. At a cost, it's out, but each foe next to it gets a free attack first.
; Changes A, X, Y.
flee:   stx flee_who
        ldy fighters + F_Y, x
        lda fighters + F_X, x
        tax
        jsr battle_tile
        cmp #TILE_EXIT
        bne @roll
        lda #0                      ; the exit: no roll
        sta chk_roll
        lda #SUCCESS
        sta chk_result
        bne @rolled                 ; (always)
@roll:  ldx flee_who
        jsr foes_next_to
        jsr flee_tn
        tax
        ldy flee_who
        lda fighters + F_ATHLETICS, y
        jsr check
@rolled:
        jsr roll_event
        lda chk_result
        jsr value
        lda #EV_FLEE
        ldx flee_who
        ldy #NOBODY
        jsr emit
        lda chk_result
        cmp #COST
        bne @out
        lda #0                      ; out, but each foe next to it hits it first
        sta flee_i
@foe:   ldx flee_i
        cpx fighter_count
        bcs @out
        ldy flee_who
        lda fighters + F_SIDE, x
        cmp fighters + F_SIDE, y
        beq @f_next
        jsr dist_to
        cmp #1
        bne @f_next
        ldy flee_who
        jsr free_attack
@f_next:
        inc flee_i
        jmp @foe
@out:   lda chk_result
        beq @still                  ; (FAIL: still here)
        ldx flee_who
        lda fighters + F_STATE, x
        bne @still
        lda #GONE
        sta fighters + F_STATE, x
        lda #0
        jsr value
        lda #EV_GONE
        ldy #NOBODY
        jmp emit
@still: rts

; ----------------------------------------------------------------------------------------
; nearest: the nearest of fighter near_who's foes in the fight, from near_x, near_y (one it
; can attack from there, if near_hit is 1), the first on a tie. After: A = it, or NOBODY.
; Changes A, X, Y.
nearest:
        lda #NOBODY
        sta near_best
        lda #$FF
        sta near_d
        lda #0
        sta near_i
@who:   ldx near_i
        cpx fighter_count
        bcs @done
        lda fighters + F_STATE, x
        bne @next
        ldy near_who
        lda fighters + F_SIDE, x
        cmp fighters + F_SIDE, y
        beq @next
        lda near_hit
        beq @far
        sty can_who
        stx can_target
        lda near_x
        sta can_x
        lda near_y
        sta can_y
        jsr battle_can_attack
        beq @next
@far:   ldx near_i
        lda fighters + F_X, x
        sta dist_x
        lda fighters + F_Y, x
        sta dist_y
        ldx near_x
        ldy near_y
        jsr dist
        cmp near_d
        bcs @next
        sta near_d
        lda near_i
        sta near_best
@next:  inc near_i
        jmp @who
@done:  lda near_best
        rts

; plan: what the computer does with fighter plan_who, by its rule: plan_x, plan_y where it
; moves, plan_target whom it attacks from there (NOBODY: nobody). Someone it can hit from
; where it stands, it hits; on guard, it stays. A shooter moves only as far as it must to
; get a shot (the cheapest square, top-left first); else it closes in on the nearest
; foe: the square nearest them it can reach (cheapest, then top-left, on a tie).
; Changes A, X, Y.
plan:   ldx plan_who
        stx near_who
        lda fighters + F_X, x
        sta plan_x
        sta near_x
        lda fighters + F_Y, x
        sta plan_y
        sta near_y
        lda #1
        sta near_hit
        jsr nearest
        sta plan_target
        cmp #NOBODY
        beq @near4
        jmp @done
@near4:
        ldx plan_who
        lda fighters + F_BEHAVIOR, x
        cmp #AI_GUARD
        bne @near3
        jmp @done
@near3:
        txa
        jsr reach
        ldx plan_who
        lda fighters + F_BEHAVIOR, x
        cmp #AI_SHOOT
        bne @close
        lda fighters + F_RANGED, x
        beq @close
        lda #$FF                    ; a shooter: the cheapest square with a shot
        sta plan_best
        lda #0
        sta plan_sy
@s_row: lda #0
        sta plan_sx
@s_col: ldx plan_sx
        ldy plan_sy
        jsr square
        tax
        lda cost_to, x
        cmp plan_best
        bcs @s_next
        sta plan_cost
        lda plan_sx
        sta near_x
        lda plan_sy
        sta near_y
        lda #1
        sta near_hit
        jsr nearest
        cmp #NOBODY
        beq @s_next
        sta plan_target
        lda plan_cost
        sta plan_best
        lda plan_sx
        sta plan_x
        lda plan_sy
        sta plan_y
@s_next:
        inc plan_sx
        lda plan_sx
        cmp map_w
        bcc @s_col
        inc plan_sy
        lda plan_sy
        cmp map_h
        bcc @s_row
        lda plan_best
        cmp #$FF
        beq @near2
        jmp @done
@near2:
@close: ldx plan_who                ; close in on the nearest
        lda fighters + F_X, x
        sta near_x
        lda fighters + F_Y, x
        sta near_y
        lda #0
        sta near_hit
        jsr nearest
        cmp #NOBODY
        bne @near1
        jmp @done
@near1:
        sta plan_goal
        tay
        ldx plan_who
        jsr dist_to
        sta plan_best
        lda #0
        sta plan_sy
@c_row: lda #0
        sta plan_sx
@c_col: ldx plan_sx
        ldy plan_sy
        jsr square
        tax
        lda cost_to, x
        cmp #$FF
        beq @c_next
        sta plan_cost
        ldy plan_goal
        lda fighters + F_X, y
        sta dist_x
        lda fighters + F_Y, y
        sta dist_y
        ldx plan_sx
        ldy plan_sy
        jsr dist
        cmp plan_best
        bcc @better
        bne @c_next
        ldx plan_x                  ; as near: cheaper?
        ldy plan_y
        jsr square
        tax
        lda plan_cost
        cmp cost_to, x
        bcs @c_next
        lda plan_best
@better:
        sta plan_best
        lda plan_sx
        sta plan_x
        lda plan_sy
        sta plan_y
@c_next:
        inc plan_sx
        lda plan_sx
        cmp map_w
        bcc @c_col
        inc plan_sy
        lda plan_sy
        cmp map_h
        bcc @c_row
        lda plan_x                  ; and whom it can hit from there
        sta near_x
        lda plan_y
        sta near_y
        lda #1
        sta near_hit
        lda plan_who
        sta near_who
        jsr nearest
        sta plan_target
@done:  rts

; guard: fighter X stands guard. Changes A, Y.
guard:  lda #1
        sta fighters + F_GUARDING, x
        lda #0
        jsr value
        lda #EV_GUARD
        ldy #NOBODY
        jmp emit

; foe_turn: foe X's turn, by its rule. Changes A, X, Y.
foe_turn:
        stx plan_who
        jsr plan
        lda plan_who
        sta move_who
        lda plan_x
        sta move_x
        lda plan_y
        sta move_y
        jsr move_to
        ldx plan_who
        lda fighters + F_STATE, x
        bne @done
        lda plan_target
        cmp #NOBODY
        beq @guard
        stx att_who
        jmp attack
@guard: lda fighters + F_BEHAVIOR, x
        cmp #AI_GUARD
        bne @done
        jmp guard
@done:  rts

; battle_quick: what the computer would do with fighter A now (apb_battle_quick), in
; act_x, act_y, act_kind, act_target: by the rule its weapon suggests. Changes A, X, Y.
battle_quick:
        ldx #0
        stx act_target
        cmp fighter_count
        bcs @nothing
        sta plan_who
        jsr plan
        lda plan_x
        sta act_x
        lda plan_y
        sta act_y
        lda plan_target
        cmp #NOBODY
        beq @no_target
        sta act_target
        lda #ACT_ATTACK
        sta act_kind
        rts
@no_target:
        ldx plan_who
        lda fighters + F_BEHAVIOR, x
        cmp #AI_GUARD
        bne @done_act
        lda #ACT_GUARD
        sta act_kind
        rts
@nothing:
        lda #0
        sta act_x
        sta act_y
@done_act:
        lda #ACT_DONE
        sta act_kind
        rts

; ----------------------------------------------------------------------------------------
; turn_of: the fighter whose turn it is at next_at, or NOBODY if it sits this one out (out
; of the fight, or the other side's surprise round). After: A. Changes A, X.
turn_of:
        ldx next_at
        lda order, x
        tax
        lda fighters + F_STATE, x
        bne @out
        lda round_no
        bne @yes
        lda surprise                ; round 0: only the side that sprang it
        cmp #SURPRISE_FOES
        beq @foes
        lda fighters + F_SIDE, x    ; (travelers' surprise)
        bne @out
        beq @yes                    ; (always)
@foes:  lda fighters + F_SIDE, x
        beq @out
@yes:   txa
        rts
@out:   lda #NOBODY
        rts

; advance: on to the next in the order; after the last, a new round: the order of play
; again, and anyone may wait again. Changes A, X.
advance:
        lda #0
        sta begun
        inc next_at
        lda next_at
        cmp fighter_count
        bcc @done
        lda #0
        sta next_at
        lda round_no
        cmp #255
        beq @order
        inc round_no
@order: jsr base_order
        lda #0
        ldx #FIGHTERS_MAX - 1
@wait:  sta fighters + F_WAITED, x
        dex
        bpl @wait
@done:  rts

; begin_turn: fighter X's turn begins: told; then, unless it's a turn put off with Wait come
; round, its guard ends and the ground may hurt it. Changes A, X, Y.
begin_turn:
        lda round_no
        jsr value
        lda #EV_TURN
        ldy #NOBODY
        jsr emit
        lda fighters + F_WAITED, x
        bne @done
        lda #0
        sta fighters + F_GUARDING, x
        jmp ground_hurts
@done:  rts

; ----------------------------------------------------------------------------------------
; battle_next: whose turn it is: plays the foes' turns (and passes anyone out of the
; fight) till it's a traveler's (apb_battle_next).
;   After:   A = that traveler, or NOBODY: the fight is over.
;   Changes: A, X, Y.
battle_next:
        lda #0
        sta next_guard
@turn:  jsr check_end
        lda result
        bne @over
        jsr turn_of
        cmp #NOBODY
        bne @someone
        jsr advance
        jmp @again
@someone:
        sta next_who
        tax
        lda fighters + F_SIDE, x
        bne @foe
        lda begun                   ; a traveler: their turn begins once
        bne @theirs
        jsr begin_turn
        lda #1
        sta begun
@theirs:
        ldx next_who
        lda fighters + F_STATE, x
        bne @gone
        txa
        rts
@gone:  jsr advance
        jmp @again
@foe:   jsr begin_turn
        ldx next_who
        lda fighters + F_STATE, x
        bne @foe_done
        jsr foe_turn
@foe_done:
        jsr advance
@again: inc next_guard              ; (bounded, as battle.c's)
        lda next_guard
        cmp #255
        bcc @turn
@over:  lda #NOBODY
        rts

; battle_act: traveler A's turn, from act_x, act_y, act_kind, act_target
; (apb_battle_act): moving there first (a square they can reach), then the action, if the
; rules allow it.
;   After:   A = 1; or 0: not allowed (nothing happened; still their turn).
;   Changes: A, X, Y.
battle_act:
        sta act_who
        lda result
        bne @no
        ldx act_who
        cpx fighter_count
        bcs @no
        ldy next_at
        txa
        cmp order, y
        bne @no
        lda act_x                   ; moving: somewhere they can reach
        cmp fighters + F_X, x
        bne @moves
        lda act_y
        cmp fighters + F_Y, x
        beq @stays
@moves: lda act_who
        ldx act_x
        ldy act_y
        jsr battle_can_reach
        beq @no
@stays: lda act_kind
        cmp #ACT_ATTACK
        bne @not_attack
        lda act_who
        sta can_who
        lda act_target
        sta can_target
        lda act_x
        sta can_x
        lda act_y
        sta can_y
        jsr battle_can_attack
        beq @no
        bne @allowed                ; (always)
@not_attack:
        cmp #ACT_WAIT
        bne @other
        ldx act_who                 ; wait: not moving, once a round
        lda act_x
        cmp fighters + F_X, x
        bne @no
        lda act_y
        cmp fighters + F_Y, x
        bne @no
        lda fighters + F_WAITED, x
        bne @no
        jmp wait
@other: cmp #ACT_DONE + 1           ; guard, flee, done
        bcc @allowed
@no:    lda #0
        rts
@allowed:
        lda act_who
        sta move_who
        lda act_x
        sta move_x
        lda act_y
        sta move_y
        jsr move_to
        ldx act_who
        lda fighters + F_STATE, x
        bne @acted
        lda act_kind
        cmp #ACT_ATTACK
        bne @guard
        stx att_who
        lda act_target
        jsr attack
        jmp @acted
@guard: cmp #ACT_GUARD
        bne @flee
        jsr guard
        jmp @acted
@flee:  cmp #ACT_FLEE
        bne @acted
        jsr flee
@acted: jsr advance
        jsr check_end
        lda #1
        rts

; wait: traveler act_who puts their turn off to the end of this round's order. After:
; A = 1. Changes A, X, Y.
wait:   ldx act_who
        lda #1
        sta fighters + F_WAITED, x
        lda #0
        jsr value
        lda #EV_WAIT
        ldy #NOBODY
        jsr emit
        ldx next_at                 ; the rest up one; them last
@up:    inx
        cpx fighter_count
        bcs @last
        lda order, x
        sta order - 1, x
        jmp @up
@last:  lda act_who
        sta order - 1, x
        lda #0
        sta begun
        lda #1
        rts

; The 8 steps round a square: dx, dy.
step_x: .byte $FF, 0, 1, $FF, 1, $FF, 0, 1
step_y: .byte $FF, $FF, $FF, 0, 0, 1, 1, 1

no_event:
        rts

        .segment "BSS"
map_w:          .res 1
map_h:          .res 1
map_tiles:        .res MAP_W_MAX * MAP_H_MAX  ; a row of 16 for each of the map's
fighter_count:  .res 1
fighters:       .res FIELDS * FIGHTERS_MAX  ; a row for each field (battle.inc)
base:           .res FIGHTERS_MAX       ; the order of play, by Grace
order:          .res FIGHTERS_MAX       ; this round's: Wait moves you back
round_no:       .res 1
next_at:        .res 1                  ; the place in the order
begun:          .res 1                  ; the traveler there has begun their turn
surprise:       .res 1
result:         .res 1                  ; BATTLE_*
cost_to:        .res MAP_W_MAX * MAP_H_MAX  ; reach: the cost to get to each square
occupied:       .res MAP_W_MAX * MAP_H_MAX  ; and who's on it
event_hook:     .res 2                  ; who hears what happens (an RTS: nobody)
ev_kind:        .res 1                  ; what happened (battle_event)
ev_actor:       .res 1
ev_target:      .res 1
ev_x:           .res 1
ev_y:           .res 1
ev_value:       .res 2
ev_roll:        .res 1
ev_total:       .res 2
ev_tn:          .res 2
ev_result:      .res 1
act_x:          .res 1                  ; a traveler's turn (battle_act, battle_quick)
act_y:          .res 1
act_kind:       .res 1
act_target:     .res 1
act_who:        .res 1
sq_x:           .res 1
at_x:           .res 1
at_y:           .res 1
sort_i:         .res 1
sort_p:         .res 1
sort_q:         .res 1
dist_x:         .res 1
dist_y:         .res 1
dist_dx:        .res 1
dt_a:           .res 1
dt_b:           .res 1
reach_who:      .res 1
reach_speed:    .res 1
reach_level:    .res 1
reach_x:        .res 1
reach_y:        .res 1
reach_i:        .res 1
relax_d:        .res 1
relax_nx:       .res 1
relax_sq:       .res 1
can_x:          .res 1
can_y:          .res 1
can_who:        .res 1
can_target:     .res 1
can_d:          .res 1
sight_x0:       .res 1
sight_y0:       .res 1
sight_x1:       .res 1
sight_y1:       .res 1
sight_who:      .res 1
sight_dx:       .res 1
sight_dy:       .res 1
sight_sx:       .res 1
sight_sy:       .res 1
sight_err:      .res 1
sight_e2:       .res 1
sight_x:        .res 1
sight_y:        .res 1
tn_a:           .res 1
tn_t:           .res 1
tn_defense:     .res 1
tn_bonus:       .res 1
end_travelers:  .res 1
end_foes:       .res 1
end_fled:       .res 1
hurt_4:         .res 2
att_who:        .res 1
att_target:     .res 1
att_bonus:      .res 1
att_cx:         .res 1
att_cy:         .res 1
att_roll:       .res 1
att_i:          .res 1
att_area:       .res 1
att_stat:       .res 1
ground_who:     .res 1
move_who:       .res 1
move_x:         .res 1
move_y:         .res 1
move_sx:        .res 1
move_sy:        .res 1
move_i:         .res 1
next_n:         .res 1
flee_who:       .res 1
flee_i:         .res 1
near_who:       .res 1
near_x:         .res 1
near_y:         .res 1
near_hit:       .res 1
near_best:      .res 1
near_d:         .res 1
near_i:         .res 1
plan_who:       .res 1
plan_x:         .res 1
plan_y:         .res 1
plan_target:    .res 1
plan_best:      .res 1
plan_cost:      .res 1
plan_goal:      .res 1
plan_sx:        .res 1
plan_sy:        .res 1
next_guard:     .res 1
next_who:       .res 1
