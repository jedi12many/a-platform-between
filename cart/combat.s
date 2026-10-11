; The combat rules (docs/combat.md; the C version is core/src/combat.c, the reference
; tools/rules/combat.py): a traveler's fighter from their sheet, the TN to hit, the damage
; of a hit, the TN to flee, what the squares cost. Code in the fight's asset (asset 2),
; run where it's staged.

        .include "zp.inc"
        .include "char.inc"
        .include "battle.inc"

        .export fighter_from, new_fighter, hit_tn, damage, dmg, flee_tn, tile_cost
        .export tile_blocks, divide
        .import traveler, health_max, skill_rating, chk_result, chk_total, chk_tn
        .import item_tier, item_arch, item_damage
        .importzp ITEM_COUNT, SK_MELEE, SK_ATHLETICS, SK_RANGED, SK_CHANNEL

EQUIP_SLOTS     = 6
GRACE           = 1                 ; the stats' places
MIGHT           = 0

; A fighter's fields, in new_fighter: apb_fighter's order, a byte each.
N_SIDE          = 0
N_HEALTH        = 4
N_HEALTH_MAX    = 5
N_GRACE         = 6
N_DODGE         = 7
N_ARMOR         = 8
N_SPEED         = 11
N_ATTACK        = 12
N_ATHLETICS     = 13
N_WEAPON        = 14
N_STAT_BONUS    = 15
N_RANGED        = 16
N_POWER         = 17
N_DMG_TYPE      = 18
N_WEAK_TYPE     = 20
N_BEHAVIOR      = 21

        .segment "BATTLE"

; ----------------------------------------------------------------------------------------
; fighter_from: the traveler (`traveler`) as a fighter, in new_fighter (apb_fighter_from):
; their health, Grace, Dodge (Grace / 5), Armor (10 x the best armor tier they wear),
; Speed (4 + Grace / 25), Athletics; and the weapon's: its damage (5 x its tier, or 2 bare-
; handed), the skill it rolls (Melee, with Might / 20 on its damage; Ranged; Channel, at
; Ward), and the rule quick plays it by (charge with a melee weapon, else shoot).
;   Takes:   A/X = the weapon item (low/high): 0, or one the traveler has.
;   Changes: A, X, Y; zp_t0-zp_t3.
fighter_from:
        sta zp_t0
        stx zp_t1
        ldx #FIELDS - 1             ; all 0
        lda #0
@clear: sta new_fighter, x
        dex
        bpl @clear
        lda #ARCH_MELEE             ; the weapon's archetype and damage type: an item with
        sta zp_t2                   ; a tier, else bare hands (melee, kinetic)
        jsr weapon_item
        bcs @bare
        ldx zp_t0
        lda item_arch, x
        sta zp_t2
        lda item_damage, x
        sta new_fighter + N_DMG_TYPE
@bare:  lda #SIDE_TRAVELER
        sta new_fighter + N_SIDE
        jsr health_max
        sta new_fighter + N_HEALTH_MAX
        sta new_fighter + N_HEALTH
        lda traveler + CH_STATS + GRACE
        sta new_fighter + N_GRACE
        ldx #5                      ; Dodge: Grace / 5
        jsr divide
        sta new_fighter + N_DODGE
        jsr armor
        sta new_fighter + N_ARMOR
        lda traveler + CH_STATS + GRACE ; Speed: 4 + Grace / 25
        ldx #25
        jsr divide
        clc
        adc #4
        sta new_fighter + N_SPEED
        lda #SK_ATHLETICS
        jsr skill_rating
        sta new_fighter + N_ATHLETICS
        jsr weapon_damage
        sta new_fighter + N_WEAPON
        lda #$FF
        sta new_fighter + N_WEAK_TYPE
        lda zp_t2                   ; by the weapon's kind
        cmp #ARCH_RANGED
        beq @ranged
        cmp #ARCH_FOCUS
        beq @focus
        lda #AI_CHARGE              ; melee (and anything else): Melee, Might / 20 more
        sta new_fighter + N_BEHAVIOR
        lda #SK_MELEE
        jsr skill_rating
        sta new_fighter + N_ATTACK
        lda traveler + CH_STATS + MIGHT
        ldx #20
        jsr divide
        sta new_fighter + N_STAT_BONUS
        rts
@focus: lda #1                      ; a focus: Channel, at Ward, from afar
        sta new_fighter + N_POWER
        lda #SK_CHANNEL
        bne @far                    ; (always)
@ranged:
        lda #SK_RANGED
@far:   jsr skill_rating
        sta new_fighter + N_ATTACK
        lda #1
        sta new_fighter + N_RANGED
        lda #AI_SHOOT
        sta new_fighter + N_BEHAVIOR
        rts

; weapon_item: C clear if item zp_t0/zp_t1 is one of the registry's, with a tier. Changes
; A, X.
weapon_item:
        lda zp_t1
        bne @not
        lda zp_t0
        beq @not
        cmp #ITEM_COUNT
        bcs @not
        tax
        lda item_tier, x
        beq @not
        clc
        rts
@not:   sec
        rts

; weapon_damage: item zp_t0/zp_t1's damage: 5 x its tier, or 2 bare-handed
; (apb_weapon_damage). After: A. Changes A, X.
weapon_damage:
        jsr weapon_item
        bcs @bare
        lda item_tier, x
        sta zp_t3
        asl a
        asl a
        clc
        adc zp_t3
        rts
@bare:  lda #UNARMED_DAMAGE
        rts

; armor: 10 x the best tier of the armor the traveler wears (apb_armor). After: A. Changes
; A, X, Y; zp_t3.
armor:  lda #0
        sta zp_t3
        ldy #0
@slot:  lda traveler + CH_EQUIPPED + 1, y   ; an item: one of the registry's armor
        bne @next
        ldx traveler + CH_EQUIPPED, y
        beq @next
        cpx #ITEM_COUNT
        bcs @next
        lda item_arch, x
        cmp #ARCH_ARMOR
        bne @next
        lda item_tier, x
        cmp zp_t3
        bcc @next
        sta zp_t3
@next:  iny
        iny
        cpy #EQUIP_SLOTS * 2
        bne @slot
        lda zp_t3                   ; x 10: x 8 + x 2
        asl a
        sta zp_t3
        asl a
        asl a
        clc
        adc zp_t3
        rts

; ----------------------------------------------------------------------------------------
; hit_tn: the TN to hit (apb_hit_tn): 50 + Dodge + the defense + a bonus (cover), into
; chk_tn (16 bits).
;   Takes:   A = the Dodge; X = the defense (Armor or Ward); Y = the bonus.
;   Changes: A.
hit_tn: sta chk_tn
        lda #0
        sta chk_tn + 1
        txa
        jsr @add
        tya
        jsr @add
        lda #TN_BASE
@add:   clc
        adc chk_tn
        sta chk_tn
        bcc @same
        inc chk_tn + 1
@same:  rts

; ----------------------------------------------------------------------------------------
; damage: a hit's damage (apb_damage), into dmg (16 bits): a miss, none; a glancing hit
; (at a cost), half the weapon's; a hit, the weapon's, the stat bonus and 1 for every full
; 10 the total beat the TN by, twice that for a crit; less the target's Soak, to 0.
;   Takes:   chk_result, chk_total, chk_tn (rules.s); A = the weapon's damage; X = the
;            stat bonus; Y = the Soak.
;   Changes: A, X; zp_t0, zp_t1.
damage: sty soak
        ldy #0
        sty dmg + 1
        sta dmg
        lda chk_result
        cmp #COST
        bcc @none                   ; (FAIL)
        bne @hit
        lsr dmg                     ; glancing: half the weapon's, no more
        jmp @soak
@hit:   txa                         ; + the stat bonus
        clc
        adc dmg
        sta dmg
        bcc @margin
        inc dmg + 1
@margin:
        lda chk_total               ; + (total - TN) / 10, if it's over
        sec
        sbc chk_tn
        sta zp_t0
        lda chk_total + 1
        sbc chk_tn + 1
        bmi @crit
        sta zp_t1
        ldx #0                      ; / 10: tens taken away
@tens:  lda zp_t0
        sec
        sbc #10
        tay
        lda zp_t1
        sbc #0
        bcc @counted
        sta zp_t1
        sty zp_t0
        inx
        bne @tens
@counted:
        txa
        clc
        adc dmg
        sta dmg
        bcc @crit
        inc dmg + 1
@crit:  lda chk_result              ; a crit: twice it
        cmp #CRIT
        bne @soak
        asl dmg
        rol dmg + 1
@soak:  lda dmg                     ; less the Soak, to 0
        sec
        sbc soak
        tax
        lda dmg + 1
        sbc #0
        bcs @fine
@none:  lda #0
        tax
@fine:  stx dmg
        sta dmg + 1
        ldy soak
        rts

; ----------------------------------------------------------------------------------------
; flee_tn: the TN to flee: 100 + 10 for each foe next to you (apb_flee_tn).
;   Takes:   A = the foes next to you (0-8). After: A. Changes A, X.
flee_tn:
        tax
        lda #FLEE_TN
@foe:   dex
        bmi @done
        clc
        adc #FLEE_PER_FOE
        jmp @foe
@done:  rts

; tile_cost: what a square costs to enter (apb_tile_cost): 1, 2 for rough ground and
; cover, 0 for one that can't be (a wall, a pit, past the tiles). Takes A. After: A.
; Changes A, X.
tile_cost:
        cmp #TILE_COUNT
        bcs @none
        tax
        lda costs, x
        rts
@none:  lda #0
        rts

; tile_blocks: C set if a square blocks sight (a wall; or past the tiles). Takes A.
; Changes nothing else.
tile_blocks:
        cmp #TILE_WALL
        beq @blocks
        cmp #TILE_COUNT
        rts                         ; (C set: past them)
@blocks:
        sec
        rts

; ----------------------------------------------------------------------------------------
; divide: A / X, both 8 bits, X 1 or more. After: A = the quotient. Changes A, X.
divide: stx divisor
        ldx #0
@take:  cmp divisor
        bcc @done
        sbc divisor                 ; (C set)
        inx
        bne @take                   ; (always)
@done:  txa
        rts

; Each square's movement cost (the tiles' order).
costs:  .byte 1, 0, 0, 2, 2, 1, 1, 1

        .segment "BSS"
new_fighter:    .res FIELDS         ; a fighter to add (battle_add), apb_fighter's order
dmg:            .res 2
soak:           .res 1
divisor:        .res 1
