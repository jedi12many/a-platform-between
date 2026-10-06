/*
 * A Platform Between: rules core.
 *
 * Portable C that must build with a modern compiler and with cc65 for the 6502
 * (Commodore 64, Apple II). House rules for this code:
 *   - whole numbers only, no floating point;
 *   - declarations at the top of blocks, no designated initializers;
 *   - structs are passed by pointer, never by value;
 *   - every result must be identical on every platform.
 */
#ifndef APB_H
#define APB_H

#include <stdint.h>

#include "apb_registry.h"   /* generated from the registry/ text files */

/* ---------------------------------------------------------------- dice */

typedef struct {
    uint16_t state;
} apb_rng;

void     apb_rng_seed(apb_rng *rng, uint16_t seed);
uint16_t apb_rng_next(apb_rng *rng);
uint8_t  apb_d6(apb_rng *rng);

/* ------------------------------------------------------------- stats */

enum {
    APB_MIGHT = 0,
    APB_GRACE,
    APB_GRIT,
    APB_WITS,
    APB_PRESENCE,
    APB_FATE,
    APB_STAT_COUNT
};

/* Races, classes and skills come from the registry (the registry/ text files). */

#define APB_RATING_MAX  100   /* stats, skills and powers all top out at 100 */
#define APB_LEVEL_MAX   100
#define APB_XP_PER_LEVEL 100  /* every level costs the same; see apb_xp_award */
#define APB_POWER_SLOTS 8

extern const uint8_t apb_skill_stat[APB_SKILL_COUNT];  /* governing stat */

/* Names shown to players, from the registry. ASCII, like all game text. */
extern const char *const apb_race_names[APB_RACE_COUNT];
extern const char *const apb_class_names[APB_CLASS_COUNT];
extern const char *const apb_skill_names[APB_SKILL_COUNT];

/* ------------------------------------------- the core roll: d100 + skill */

/* Roll d100, add the rating (and any bonus), and beat the target number (TN).
 * A natural 100, or doubles (11, 22 .. 99) on a success, is a crit; within 20
 * under the TN is success at a cost; a natural 01 always fails. */
enum {
    APB_FAIL = 0,
    APB_COST,
    APB_SUCCESS,
    APB_CRIT
};

#define APB_COST_MARGIN 20

/* Task target numbers. On a normal task (TN 100), a rating is its chance. */
#define APB_TN_EASY      80
#define APB_TN_ROUTINE   90
#define APB_TN_NORMAL    100
#define APB_TN_TRICKY    110
#define APB_TN_HARD      120
#define APB_TN_VERY_HARD 130

/* A defense (Armor, Ward, Resolve, or a task's difficulty) as a TN. */
#define APB_TN_BASE      50

typedef struct {
    uint8_t roll;     /* the die, 1..100         */
    int16_t total;    /* roll + rating + bonus   */
    int16_t tn;
    uint8_t result;
} apb_roll;

uint8_t apb_d100(apb_rng *rng);
uint8_t apb_resolve(uint8_t roll, int16_t total, int16_t tn);
uint8_t apb_check(apb_rng *rng, uint8_t rating, int16_t bonus, int16_t tn, apb_roll *out);

/* TN for a defense of 0..100, after `reduce` (debuffs, pierce) is taken off;
 * the defense stops at 0, so the TN never goes below APB_TN_BASE. */
int16_t apb_defense_tn(int16_t defense, int16_t reduce);

/* Percent chance (1..100) of at least a success with this rating + bonus
 * against this TN. For sheets and screens; counts all 100 rolls exactly. */
uint8_t apb_chance(int16_t rating_and_bonus, int16_t tn);

/* -------------------------------------------------------- characters */

#define APB_NAME_LEN     8
#define APB_EQUIP_SLOTS  6
#define APB_PACK_SLOTS   6
#define APB_ECHO_SLOTS   8

#define APB_FLAG_VERIFIED 0x01  /* approved by the hub server          */
#define APB_FLAG_RETIRED  0x02  /* paid their Debt and went home       */
#define APB_FLAG_TABLETOP 0x04  /* changed at a tabletop game          */

typedef struct {
    uint16_t id;     /* 1..1023 in the Echo registry, 0 = empty slot */
    uint8_t  state;  /* 1..3, meaning set by the registry, 0 = unset  */
} apb_echo;

typedef struct {
    uint8_t id;      /* 1..255 in the power registry, 0 = empty slot  */
    uint8_t rank;    /* 0..100                                       */
} apb_power;

typedef struct {
    char      name[APB_NAME_LEN + 1];
    uint8_t   race;
    uint8_t   cls;
    uint8_t   level;                     /* 1..100                        */
    uint8_t   xp;                        /* 0..99 toward the next level   */
    uint8_t   stat[APB_STAT_COUNT];      /* 0..100                        */
    uint8_t   training[APB_SKILL_COUNT]; /* 0..100; see apb_skill()       */
    uint16_t  tags;                      /* bit per tagged skill          */
    uint8_t   stat_points;               /* unspent, from levelling up    */
    uint8_t   skill_points;
    apb_power power[APB_POWER_SLOTS];    /* filled from the front         */
    uint16_t  debt;
    uint16_t  equipped[APB_EQUIP_SLOTS]; /* item registry IDs, 0 = empty  */
    uint16_t  pack[APB_PACK_SLOTS];
    apb_echo  echo[APB_ECHO_SLOTS];      /* oldest first                  */
    uint8_t   flags;
} apb_character;

void    apb_character_init(apb_character *ch, const char *name, uint8_t race,
                           uint8_t cls);
uint8_t apb_health_max(const apb_character *ch);

/* A skill's rating: half its governing stat plus training, at most 100. */
uint8_t apb_skill(const apb_character *ch, uint8_t skill);

/* ---------------------------------------------- character creation */
/* See docs/rules-v0.md. The same rules are printed in the tabletop rules. */

#define APB_BUY_BASE    25   /* every stat starts here                */
#define APB_BUY_POINTS  150  /* points to spend                       */
#define APB_BUY_MAX     70   /* highest a stat can be bought to       */
#define APB_REROLLS     3    /* times a rolled set may be re-rolled   */
#define APB_RACE_BONUS  10
#define APB_CLASS_BONUS 5
#define APB_TAG_BONUS   20   /* starting training in each tagged skill */

extern const uint8_t apb_race_bonus[APB_RACE_COUNT];   /* stat each race raises */
extern const uint8_t apb_class_bonus[APB_CLASS_COUNT]; /* stat each class raises */
extern const uint8_t apb_class_tags[APB_CLASS_COUNT][2]; /* skills each class tags */

/* 1 if `base` is a legal point-buy: every stat APB_BUY_BASE..APB_BUY_MAX and
 * exactly APB_BUY_POINTS spent. */
uint8_t apb_pointbuy_valid(const uint8_t *base);

/* One rolled stat: 3d6 x 5 (15..90). */
uint8_t apb_roll_stat(apb_rng *rng);
/* Six rolled stats in order; the player may then arrange them freely. */
void    apb_roll_stats(apb_rng *rng, uint8_t *out);

/* Make a new level-1 character from base stats (bought, or rolled and
 * arranged), adding race and class bonuses and tagging the class's two skills
 * plus `extra_tag`. Returns 1, or 0 if extra_tag is already a class tag or not
 * a skill. */
uint8_t apb_character_create(apb_character *ch, const char *name, uint8_t race,
                             uint8_t cls, const uint8_t *base, uint8_t extra_tag);

/* ------------------------------------------------------- progression */

#define APB_STAT_POINTS_PER_LEVEL 1

/* XP for a reward of `base`, for a character of `level` in content whose
 * level band tops out at `band_max`: full below or in the band, then 10% less
 * per level over it, nothing at 10 or more over. `base` at most 6000. */
uint16_t apb_xp_award(uint16_t base, uint8_t level, uint8_t band_max);

/* Add XP; returns levels gained. Each level grants stat and skill points. */
uint8_t apb_gain_xp(apb_character *ch, uint16_t amount);

/* Skill points per level: 1 + Wits / 20 (so 1..6). */
uint8_t apb_skill_points_per_level(const apb_character *ch);

/* Skill points one raise costs, by the skill's current rating: 1 below 50,
 * 2 below 75, 3 below 90, 4 from 90 up. */
uint8_t apb_skill_raise_cost(uint8_t rating);

/* Raise a stat by 1 (one stat point), or a skill's training by 1, or 2 if it
 * is tagged (skill points per apb_skill_raise_cost). Return 1 if raised, 0 if
 * not enough points or already at 100. */
uint8_t apb_raise_stat(apb_character *ch, uint8_t stat);
uint8_t apb_raise_skill(apb_character *ch, uint8_t skill);

/* ------------------------------------------------------- Translation */

enum {
    APB_ARCH_MELEE = 0,
    APB_ARCH_RANGED,
    APB_ARCH_ARMOR,
    APB_ARCH_TOOL,
    APB_ARCH_FOCUS,
    APB_ARCH_VEHICLE,
    APB_ARCH_COUNT
};

enum {
    APB_DMG_KINETIC = 0,
    APB_DMG_ENERGY,
    APB_DMG_FIRE,
    APB_DMG_COLD,
    APB_DMG_MIND
};

enum {
    APB_FORM_NATIVE = 0,  /* looks like itself                          */
    APB_FORM_TECH,        /* re-imagined as technology at `level`       */
    APB_FORM_MAGIC,       /* re-imagined as magic at `level`            */
    APB_FORM_RELIC        /* the engine can't present it: Unidentified Relic */
};

#define APB_TIER_MAX 9
#define APB_ALL_ARCHETYPES 0xFFFFu

typedef struct {
    uint8_t archetype;
    uint8_t tier;
    uint8_t damage;
    uint8_t native_tl;
    uint8_t native_ml;
} apb_item_def;

typedef struct {
    uint8_t tl;
    uint8_t ml;
} apb_realm;

typedef struct {
    uint8_t form;
    uint8_t level;       /* tech or magic level of the form it takes */
    uint8_t tier;        /* conserved, +1 when forced                */
    uint8_t dissonance;  /* added on arrival                         */
} apb_translation;

/* Every item in the registry, indexed by id (all zeros where there's none),
 * its name, and every Echo's canon default state. */
extern const apb_item_def apb_items[APB_ITEM_COUNT];
extern const char *const apb_item_names[APB_ITEM_COUNT];
extern const uint8_t apb_echo_defaults[APB_ECHO_COUNT];

/* supported: bitmask of archetypes the engine can present (1 << APB_ARCH_x). */
void apb_translate(const apb_item_def *item, const apb_realm *realm,
                   uint16_t supported, uint8_t forced, apb_translation *out);

enum {
    APB_DIS_CALM = 0,    /* 0-2                                        */
    APB_DIS_WARY,        /* 3-4: locals wary, prices up                */
    APB_DIS_MISFIRE,     /* 5-6: forced items can misfire              */
    APB_DIS_NOTICED,     /* 7-8: the realm sends something            */
    APB_DIS_BACKLASH     /* 9+: pulled back to the Waystation          */
};

uint8_t apb_dissonance_band(uint8_t dissonance);

/* ------------------------------------------------------------ Echoes */

#define APB_ECHO_UNSET 0

uint8_t apb_echo_get(const apb_character *ch, uint16_t id);
uint8_t apb_echo_get_or(const apb_character *ch, uint16_t id, uint8_t canon_default);
/* Plant or update an Echo. If all slots are full, the oldest is evicted into
 * *evicted (for the Legend) and 1 is returned; otherwise 0. */
uint8_t apb_echo_set(apb_character *ch, uint16_t id, uint8_t state, apb_echo *evicted);
void    apb_echo_clear(apb_character *ch, uint16_t id);

/* ---------------------------------------------------------- Passport */

#define APB_PASSPORT_VERSION 2
#define APB_PASSWORD_LINE    20   /* 19 data symbols + 1 check symbol; the last line may be shorter */
#define APB_PASSWORD_MAX     160  /* the longest possible password, in symbols */
#define APB_PASSWORD_BUF     (APB_PASSWORD_MAX + 1)

enum {
    APB_PP_OK = 0,
    APB_PP_RANGE,        /* a field doesn't fit the format (encode)   */
    APB_PP_LENGTH,       /* wrong number of symbols                   */
    APB_PP_SYMBOL,       /* a character that isn't in the alphabet    */
    APB_PP_LINE_CHECK,   /* a line's check symbol doesn't match       */
    APB_PP_CHECKSUM,     /* whole-password checksum doesn't match     */
    APB_PP_VERSION       /* made by a newer version of the game       */
};

uint8_t apb_passport_encode(const apb_character *ch, char *out);
/* bad_line receives the 1-based line number on APB_PP_LINE_CHECK; may be NULL. */
uint8_t apb_passport_decode(const char *in, apb_character *ch, uint8_t *bad_line);

#endif
