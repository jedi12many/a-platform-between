; A fight (docs/combat.md; the C version is core/include/apb_battle.h): its constants, and
; where each fighter's numbers are kept (battle.s's `fighters`: a row of 8 bytes for each
; field, the fighter's number the index, as battle.c keeps them).

MAP_W_MAX       = 16            ; a map's squares across (a row is 16 bytes: x + y x 16)
MAP_H_MAX       = 10
FIGHTERS_MAX    = 8
NOBODY          = $FF

; A fighter's fields (apb_fighter, in its order): each a row of FIGHTERS_MAX bytes.
F_SIDE          = 0 * FIGHTERS_MAX  ; SIDE_TRAVELER or SIDE_FOE
F_STATE         = 1 * FIGHTERS_MAX  ; IN_FIGHT, DOWN, GONE
F_X             = 2 * FIGHTERS_MAX
F_Y             = 3 * FIGHTERS_MAX
F_HEALTH        = 4 * FIGHTERS_MAX
F_HEALTH_MAX    = 5 * FIGHTERS_MAX
F_GRACE         = 6 * FIGHTERS_MAX  ; for the order of play
F_DODGE         = 7 * FIGHTERS_MAX
F_ARMOR         = 8 * FIGHTERS_MAX
F_WARD          = 9 * FIGHTERS_MAX
F_SOAK          = 10 * FIGHTERS_MAX
F_SPEED         = 11 * FIGHTERS_MAX
F_ATTACK        = 12 * FIGHTERS_MAX ; the rating it rolls
F_ATHLETICS     = 13 * FIGHTERS_MAX ; for fleeing
F_WEAPON        = 14 * FIGHTERS_MAX ; weapon damage
F_STAT_BONUS    = 15 * FIGHTERS_MAX ; added to melee damage
F_RANGED        = 16 * FIGHTERS_MAX ; 1: reaches anyone in sight
F_POWER         = 17 * FIGHTERS_MAX ; 1: aimed at Ward, not Armor
F_DMG_TYPE      = 18 * FIGHTERS_MAX
F_AREA          = 19 * FIGHTERS_MAX ; 0: one target
F_WEAK_TYPE     = 20 * FIGHTERS_MAX ; a damage type that ignores its Armor, or $FF
F_BEHAVIOR      = 21 * FIGHTERS_MAX ; AI_*
F_COWARD        = 22 * FIGHTERS_MAX ; 1: runs off at a quarter health
F_GUARDING      = 23 * FIGHTERS_MAX
F_WAITED        = 24 * FIGHTERS_MAX
FIELDS          = 25

SIDE_TRAVELER   = 0
SIDE_FOE        = 1
IN_FIGHT        = 0
DOWN            = 1
GONE            = 2
AI_CHARGE       = 0
AI_SHOOT        = 1
AI_GUARD        = 2

; A turn: move, then one of these (act_kind).
ACT_ATTACK      = 0
ACT_GUARD       = 1
ACT_WAIT        = 2
ACT_FLEE        = 3
ACT_DONE        = 4

; What happens (ev_kind; battle_event).
EV_TURN         = 0
EV_MOVE         = 1
EV_ATTACK       = 2
EV_DOWN         = 3
EV_HAZARD       = 4
EV_GUARD        = 5
EV_WAIT         = 6
EV_FLEE         = 7
EV_GONE         = 8
EV_END          = 9
EV_FREE         = 10

; What fightext.s's fight_text made of an event.
TEXT_NOTHING    = 0
TEXT_HEADING    = 1             ; "-- Round 2 --"
TEXT_SENTENCE   = 2

BATTLE_ON       = 0
BATTLE_WON      = 1
BATTLE_LOST     = 2
BATTLE_FLED     = 3

SURPRISE_NONE   = 0
SURPRISE_FOES   = 1             ; an ambush: the foes' free round
SURPRISE_TRAVELERS = 2          ; a sneak attack: the travelers'

; The squares (APB_TILE_*, the map's characters .#O~+^=>).
TILE_OPEN       = 0
TILE_WALL       = 1
TILE_PIT        = 2
TILE_ROUGH      = 3
TILE_COVER      = 4
TILE_HAZARD     = 5
TILE_HIGH       = 6
TILE_EXIT       = 7
TILE_COUNT      = 8

; The rules' numbers (docs/combat.md).
TN_BASE         = 50
UNARMED_DAMAGE  = 2
COVER_BONUS     = 20            ; to the TN, against ranged attacks and powers
HIGH_GROUND_BONUS = 10          ; to attacks from high ground
HAZARD_DAMAGE   = 5
FLEE_TN         = 100
FLEE_PER_FOE    = 10
ARCH_MELEE      = 0             ; an item's archetype (registry.ARCHETYPES)
ARCH_RANGED     = 1
ARCH_ARMOR      = 2
ARCH_FOCUS      = 4
FAIL            = 0             ; a roll's result (rules.s)
COST            = 1
SUCCESS         = 2
CRIT            = 3
