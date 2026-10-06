/*
 * A Platform Between: the battle (docs/combat.md).
 *
 * A fight on a battle map, played one turn at a time from a stream of actions, so it
 * plays the same on every machine and in tests. The rules arithmetic is in apb.h
 * (apb_hit_tn, apb_damage, the tiles); this is the board, the turns and the foes.
 *
 * Same house rules as the rest of the core; the battle's state is about 400 bytes.
 */
#ifndef APB_BATTLE_H
#define APB_BATTLE_H

#include "apb.h"

#define APB_MAP_W_MAX    16
#define APB_MAP_H_MAX    10
#define APB_FIGHTERS_MAX 8
#define APB_NOBODY       0xFF

enum { APB_SIDE_TRAVELER = 0, APB_SIDE_FOE };

/* How a foe fights (printed on its card). */
enum {
    APB_FOE_CHARGE = 0,   /* close in and attack the nearest traveler          */
    APB_FOE_SHOOT,        /* shoot whoever it can see; otherwise close in      */
    APB_FOE_GUARD         /* stay put; attack anyone who comes next to it      */
};

/* A fighter's state. */
enum { APB_IN_FIGHT = 0, APB_DOWN, APB_GONE };

/* Every field is a byte, and battle.c relies on it: don't add a wider one. */
typedef struct {
    uint8_t side;
    uint8_t state;
    uint8_t x, y;
    uint8_t health, health_max;
    uint8_t grace;            /* for the order of play                         */
    uint8_t dodge, armor, ward, soak, speed;
    uint8_t attack;           /* the rating it rolls                           */
    uint8_t athletics;        /* for fleeing                                   */
    uint8_t weapon;           /* weapon damage                                 */
    uint8_t stat_bonus;       /* added to melee damage                         */
    uint8_t ranged;           /* 1: reaches anyone in sight; 0: next to it     */
    uint8_t power;            /* 1: aimed at Ward, not Armor                   */
    uint8_t dmg_type;         /* APB_DMG_*                                     */
    uint8_t area;             /* 0: one target                                 */
    uint8_t weak_type;        /* a damage type that ignores its Armor, or 0xFF */
    uint8_t behavior;         /* APB_FOE_*                                     */
    uint8_t coward;           /* 1: runs off at a quarter health               */
    uint8_t defending;        /* +20 to its TN until its next turn             */
    uint8_t opened;           /* +20 to the next traveler attack on it (Help)  */
} apb_fighter;

enum {
    APB_ACT_ATTACK = 0,       /* target: a fighter (or, for an area, any one in the blast) */
    APB_ACT_DEFEND,
    APB_ACT_HELP,             /* target: a foe next to you                     */
    APB_ACT_FLEE,
    APB_ACT_WAIT
};

typedef struct {
    uint8_t move_x, move_y;   /* where to move first (its own square: stay)    */
    uint8_t kind;             /* APB_ACT_*                                     */
    uint8_t target;
} apb_action;

/* What happened, for the front end to show and tests to log. */
enum {
    APB_EV_TURN = 0,          /* actor's turn begins                           */
    APB_EV_MOVE,              /* actor moved to x, y                           */
    APB_EV_ATTACK,            /* actor attacked target: roll, damage           */
    APB_EV_DOWN,              /* target is down                                */
    APB_EV_HAZARD,            /* actor took damage from the ground             */
    APB_EV_DEFEND,
    APB_EV_HELP,              /* actor opened target up                        */
    APB_EV_FLEE,              /* actor tried to flee: roll (result), x/y unused */
    APB_EV_GONE,              /* actor left the fight                          */
    APB_EV_END                /* the fight is over: value is APB_BATTLE_*      */
};

typedef struct {
    uint8_t kind;
    uint8_t actor;
    uint8_t target;
    uint8_t x, y;
    uint16_t value;           /* damage, or the fight's result                 */
    apb_roll roll;
} apb_event;

enum {
    APB_BATTLE_ON = 0,
    APB_BATTLE_WON,
    APB_BATTLE_LOST,
    APB_BATTLE_FLED
};

/* Who acts first: nobody, or one side gets a free round (an ambush, a sneak attack). */
enum { APB_SURPRISE_NONE = 0, APB_SURPRISE_FOES, APB_SURPRISE_TRAVELERS };

/* There is one battle at a time, kept inside battle.c as plain arrays: cc65 makes far
 * smaller code for those than for a struct reached through a pointer. */

/* Start an empty battle on a w x h map of open ground. */
void    apb_battle_init(uint8_t w, uint8_t h, apb_rng *rng,
                        void (*on_event)(const apb_event *ev));
void    apb_battle_set_tile(uint8_t x, uint8_t y, uint8_t tile);
uint8_t apb_battle_tile(uint8_t x, uint8_t y);
uint8_t apb_battle_width(void);
uint8_t apb_battle_height(void);

/* Add a fighter; returns its index, or APB_NOBODY if the battle is full or the square
 * can't hold it. */
uint8_t apb_battle_add(const apb_fighter *f);
uint8_t apb_battle_count(void);
/* A copy of a fighter as they are now. */
void    apb_battle_fighter(uint8_t who, apb_fighter *out);
/* A traveler's fighter, from their character and the weapon they fight with. */
void    apb_fighter_from(apb_fighter *out, const apb_character *ch, uint16_t weapon_item);

/* Work out the order of play and begin. */
void    apb_battle_start(uint8_t surprise);
uint8_t apb_battle_round(void);
uint8_t apb_battle_result(void);   /* APB_BATTLE_* */

/* Whose turn it is: plays foes' turns (and skips anyone out of the fight) until it is a
 * traveler's, and returns that traveler, or APB_NOBODY when the fight is over. */
uint8_t apb_battle_next(void);
/* Play the traveler's turn. Returns 1, or 0 if the action isn't allowed (out of reach,
 * no line of sight, a square it can't get to): nothing happens, and it's still their
 * turn. */
uint8_t apb_battle_act(uint8_t who, const apb_action *a);

/* Helpers the front ends use to offer only what's possible. */
uint8_t apb_battle_can_reach(uint8_t who, uint8_t x, uint8_t y);
uint8_t apb_battle_can_attack(uint8_t who, uint8_t target, uint8_t from_x, uint8_t from_y);
int16_t apb_battle_tn(uint8_t attacker, uint8_t target);

#endif
