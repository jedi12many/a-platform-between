/*
 * A Platform Between: the battle, rules v1 (the rules lab: docs/turn.md).
 *
 * The same engine as core/include/apb_battle.h (rules v0, which the game plays), with
 * v1's movement (Speed, paths, hazards on every step, flying), its new actions (Shove,
 * Dash), pushes and falls, and conditions in play (registry/conditions.txt). Only the
 * arena builds it, with -Icore/next ahead of -Icore/include, so it's this header that
 * apb_battle.h means there. At the freeze it replaces the v0 engine.
 *
 * Same house rules as the rest of the core.
 */
#ifndef APB_BATTLE_H
#define APB_BATTLE_H

#include "apb.h"

#define APB_RULES_NEXT   1

#define APB_MAP_W_MAX    16
#define APB_MAP_H_MAX    10
#define APB_FIGHTERS_MAX 8
#define APB_NOBODY       0xFF

enum { APB_SIDE_TRAVELER = 0, APB_SIDE_FOE };

enum {
    APB_AI_CHARGE = 0,
    APB_AI_SHOOT,
    APB_AI_GUARD
};

enum { APB_IN_FIGHT = 0, APB_DOWN, APB_GONE };

/* Every field is a byte, and battle.c relies on it: don't add a wider one. */
typedef struct {
    uint8_t side;
    uint8_t state;
    uint8_t x, y;
    uint8_t health, health_max;
    uint8_t grace;
    uint8_t dodge, armor, ward, soak, speed;
    uint8_t attack;
    uint8_t athletics;
    uint8_t weapon;
    uint8_t stat_bonus;
    uint8_t ranged;
    uint8_t power;
    uint8_t dmg_type;
    uint8_t area;
    uint8_t weak_type;
    uint8_t behavior;
    uint8_t coward;
    uint8_t guarding;
    uint8_t waited;
    /* v1 */
    uint8_t might, grit, wits, presence, fate;   /* for shaking off (a foe: its Grace) */
    uint8_t race;             /* a traveler's (its traits go on), or 0xFF           */
    uint8_t on_hit;           /* a condition its hits put on, or 0                  */
    uint8_t power_stat;       /* its class's stat: half of it goes into a power's roll */
} apb_fighter;

/* A turn: move, then one of these. */
enum {
    APB_ACT_ATTACK = 0,
    APB_ACT_GUARD,
    APB_ACT_WAIT,
    APB_ACT_FLEE,
    APB_ACT_DONE,
    APB_ACT_SHOVE,            /* target: a foe next to you                    */
    APB_ACT_DASH,             /* move again, to dash_x, dash_y                */
    APB_ACT_POWER             /* power `use`: on target, or the square dash_x, dash_y */
};

typedef struct {
    uint8_t move_x, move_y;
    uint8_t kind;
    uint8_t target;
    uint8_t dash_x, dash_y;   /* a Dash's square, or a power's                 */
    uint8_t use;              /* which of the fighter's powers                 */
    uint8_t move_use;         /* 0: walk to move_x, move_y; else power move_use - 1, a
                               * shift of yourself (Blink), takes you there instead */
} apb_action;

enum {
    APB_EV_TURN = 0,
    APB_EV_MOVE,              /* actor stepped to x, y (one event a square)            */
    APB_EV_ATTACK,
    APB_EV_DOWN,
    APB_EV_HAZARD,            /* actor hit by the ground: value damage                 */
    APB_EV_GUARD,
    APB_EV_WAIT,
    APB_EV_FLEE,
    APB_EV_GONE,
    APB_EV_END,
    APB_EV_FREE,
    /* v1 */
    APB_EV_COND_ON,           /* cond went on actor                                    */
    APB_EV_COND_OFF,          /* cond ended on actor                                   */
    APB_EV_IMMUNE,            /* cond didn't land on actor                             */
    APB_EV_TICK,              /* cond did actor value damage at its turn's start       */
    APB_EV_HEAL,              /* cond healed actor value                               */
    APB_EV_SKIP,              /* cond took actor's turn                                */
    APB_EV_SHAKE,             /* actor rolled to shake off cond: roll                  */
    APB_EV_STAND,             /* actor stood up                                        */
    APB_EV_DASH,              /* actor dashes: its steps follow                        */
    APB_EV_SHOVE,             /* actor shoved target: roll                             */
    APB_EV_PUSH,              /* actor pushed to x, y                                  */
    APB_EV_SLAM,              /* actor pushed into something: value damage             */
    APB_EV_FALL,              /* actor fell into a pit                                 */
    APB_EV_THORNS,            /* actor's thorns hurt target: value damage              */
    APB_EV_ABSORB,            /* actor's barrier took value damage                     */
    APB_EV_POWER,             /* actor uses power cond (its id) at x, y; value its tier */
    APB_EV_HIT,               /* actor's power on target: roll, value damage           */
    APB_EV_MEND,              /* actor's power heals target value                      */
    APB_EV_FIELD,             /* the square x, y becomes tile value (actor's field), or
                                 goes back to it (actor APB_NOBODY)                    */
    APB_EV_SHIFT              /* actor is shifted to x, y                              */
};

typedef struct {
    uint8_t kind;
    uint8_t actor;
    uint8_t target;
    uint8_t x, y;
    uint16_t value;
    apb_roll roll;
    uint8_t cond;             /* v1: the condition, for the COND_*, TICK, HEAL, SKIP, SHAKE events */
} apb_event;

enum {
    APB_BATTLE_ON = 0,
    APB_BATTLE_WON,
    APB_BATTLE_LOST,
    APB_BATTLE_FLED
};

enum { APB_SURPRISE_NONE = 0, APB_SURPRISE_FOES, APB_SURPRISE_TRAVELERS };

/* ---------------------------------------------------------- conditions (v1) */

#define APB_COND_SLOTS   6    /* 2 always on (a race's traits, a foe's nature), 4 others */
#define APB_COND_MAX     127
#define APB_NO_TYPE      0xFF

/* Each condition's effects (registry/conditions.txt, generated into conditions.c). */
enum {
    APB_CF_SPEED0       = 0x0001,
    APB_CF_DODGE0       = 0x0002,
    APB_CF_LOSE_TURN    = 0x0004,
    APB_CF_DOWN         = 0x0008,
    APB_CF_ENDS_HIT     = 0x0010,
    APB_CF_ENDS_HEAL    = 0x0020,
    APB_CF_NO_POWERS    = 0x0040,
    APB_CF_NO_HEAL      = 0x0080,
    APB_CF_FLY          = 0x0100,
    APB_CF_FIRST        = 0x0200,
    APB_CF_TIERED       = 0x0400,
    APB_CF_DEFINED      = 0x8000
};

typedef struct {
    uint16_t flags;
    uint8_t rounds;           /* 0: no countdown                                   */
    uint8_t shake_stat;       /* APB_MIGHT.., or 0xFF: can't be shaken off         */
    uint8_t shake_tn;
    uint8_t opposite, then;   /* condition ids, or 0                               */
    int8_t speed, dodge, armor, ward, soak, rolls, attacks, melee, next, shake;
    uint8_t heal, barrier;
    uint8_t dot, dot_type;    /* dot_type APB_NO_TYPE: Soak doesn't count          */
    uint8_t thorns, thorns_type;
    uint8_t vulnerable;       /* a damage type, or APB_NO_TYPE                     */
    uint8_t immune_hazard;    /* a damage type, or APB_NO_TYPE                     */
    uint8_t immune[4];        /* condition ids, 0 = none                           */
    uint8_t race;             /* a trait of this race, or 0xFF                     */
    char tag[5];
    const char *name;         /* its registry name                                 */
} apb_cond_def;

/* Indexed by id, as long as the registry's highest id + 1 (apb_cond_count): check an id
 * against it before looking it up. */
extern const apb_cond_def apb_conds[];
extern const uint8_t apb_cond_count;
/* The two traits of a race, or 0. */
uint8_t apb_race_trait(uint8_t race, uint8_t which);

/* ------------------------------------------------------------- powers (v1) */

#define APB_POWER_MAX    127
#define APB_POWERS_HELD  4    /* in a fight, a fighter's at most                   */

enum { APB_SH_BOLT = 0, APB_SH_BURST, APB_SH_WARD, APB_SH_FIELD, APB_SH_MEND, APB_SH_HEX,
       APB_SH_SHIFT };
enum { APB_TG_SELF = 0, APB_TG_ALLY, APB_TG_FOE, APB_TG_SQUARE, APB_TG_AROUND };

/* Each power (registry/powers.txt, generated into conditions.c with the conditions). */
typedef struct {
    uint8_t defined;
    uint8_t cls;              /* a class, or 0xFF: any                            */
    uint8_t shape;            /* APB_SH_*                                         */
    uint8_t element;          /* a damage type, or APB_NO_TYPE                    */
    uint8_t uses;             /* charges a fight, or 0: at will                   */
    uint8_t target;           /* APB_TG_*                                         */
    uint8_t adjacent;         /* a foe next to you (cc65 reserves "near")          */
    uint8_t cond;             /* what it puts on, or 0                            */
    const char *name;
} apb_power_def;

extern const apb_power_def apb_powers[];
extern const uint8_t apb_power_count;

/* A power's tier (1 + rank / 20) and its roll (half its class's stat, plus its rank). */
uint8_t apb_power_tier(uint8_t rank);

/* Speed (docs/turn.md): 5, +1 at Grace 60, +1 more at 90, -1 in heavy armor. */
uint8_t apb_speed_v1(uint8_t grace, uint8_t armor_tier);

/* ----------------------------------------------------------- the battle */

void    apb_battle_init(uint8_t w, uint8_t h, apb_rng *rng,
                        void (*on_event)(const apb_event *ev));
void    apb_battle_set_tile(uint8_t x, uint8_t y, uint8_t tile);
uint8_t apb_battle_tile(uint8_t x, uint8_t y);
uint8_t apb_battle_width(void);
uint8_t apb_battle_height(void);
/* What the map's hazards do (docs/turn.md, Hazards): damage (of a type, or APB_NO_TYPE),
 * and a condition, or 0. A plain hazard: 5 kinetic, none. */
void    apb_battle_set_hazard(uint8_t damage, uint8_t type, uint8_t cond);

uint8_t apb_battle_add(const apb_fighter *f);
uint8_t apb_battle_count(void);
void    apb_battle_fighter(uint8_t who, apb_fighter *out);
void    apb_fighter_from(apb_fighter *out, const apb_character *ch, uint16_t weapon_item);
#ifdef APB_ARENA
void    apb_battle_rearm(uint8_t who, const apb_fighter *f);
#endif

/* Conditions as a fight begins: one for good (a foe's nature), or one as if a hit had put
 * it on. Returns 1 if it landed. */
uint8_t apb_battle_trait(uint8_t who, uint8_t cond);
uint8_t apb_battle_put(uint8_t who, uint8_t cond);
uint8_t apb_battle_put_tier(uint8_t who, uint8_t cond, uint8_t tier);
/* A fighter's powers: learn one (rank 0-100) before the fight begins; returns its slot,
 * or APB_NOBODY. What it holds: ids, ranks and charges left (0xFF: at will). */
uint8_t apb_battle_learn(uint8_t who, uint8_t power, uint8_t rank);
uint8_t apb_battle_powers(uint8_t who, uint8_t *ids, uint8_t *ranks, uint8_t *left);
/* What power `use` could be used on from x, y: fighters (with the TN, or 0 for none),
 * or the squares (map: 1 yes). */
uint8_t apb_battle_power_targets(uint8_t who, uint8_t use, uint8_t x, uint8_t y,
                                 uint8_t *targets, int16_t *tns);
void    apb_battle_power_squares(uint8_t who, uint8_t use, uint8_t x, uint8_t y,
                                 uint8_t map[APB_MAP_H_MAX][APB_MAP_W_MAX]);
uint8_t apb_battle_power_rating(uint8_t who, uint8_t use);

/* A fighter's conditions now: up to APB_COND_SLOTS ids and the rounds each has left (0:
 * no countdown). Returns how many. */
uint8_t apb_battle_conditions(uint8_t who, uint8_t *ids, uint8_t *rounds);
/* Its numbers with its conditions counted. */
uint8_t apb_battle_speed(uint8_t who);       /* Speed now                           */
uint8_t apb_battle_move_left(uint8_t who);   /* what this turn's move has left      */
uint8_t apb_battle_dodge(uint8_t who);
uint8_t apb_battle_armor(uint8_t who);
uint8_t apb_battle_ward(uint8_t who);
uint8_t apb_battle_soak(uint8_t who);

void    apb_battle_start(uint8_t surprise);
uint8_t apb_battle_round(void);
uint8_t apb_battle_result(void);
uint8_t apb_battle_next(void);
uint8_t apb_battle_act(uint8_t who, const apb_action *a);
void    apb_battle_quick(uint8_t who, apb_action *out);

uint8_t apb_battle_can_reach(uint8_t who, uint8_t x, uint8_t y);
void    apb_battle_reach_map(uint8_t who, uint8_t map[APB_MAP_H_MAX][APB_MAP_W_MAX]);
/* Where a Dash from x, y could go (as if `who` stood there). */
void    apb_battle_dash_map(uint8_t who, uint8_t x, uint8_t y,
                            uint8_t map[APB_MAP_H_MAX][APB_MAP_W_MAX]);
uint8_t apb_battle_can_attack(uint8_t who, uint8_t target, uint8_t from_x, uint8_t from_y);
uint8_t apb_battle_can_shove(uint8_t who, uint8_t target, uint8_t from_x, uint8_t from_y);
int16_t apb_battle_tn(uint8_t attacker, uint8_t target);
int16_t apb_battle_shove_tn(uint8_t target);

#endif
