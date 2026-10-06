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

enum {
    APB_WARDEN = 0,
    APB_ROGUE,
    APB_TINKER,
    APB_CHANNELER,
    APB_MEDIC,
    APB_CLASS_COUNT
};

enum {
    APB_HUMAN = 0,
    APB_HOLLOWBORN,
    APB_GLASSFOLK,
    APB_RAD_DRYAD,
    APB_CHRONOMITE,
    APB_SALVAGED,
    APB_MOTH_FOLK,
    APB_RACE_COUNT
};

#define APB_STAT_CAP   12
#define APB_LEVEL_MAX  20

/* ---------------------------------------------------- the core roll */

/* 2d6 + stat + bonus - difficulty. */
enum {
    APB_FAIL = 0,     /* 5 or less: failure, and things move  */
    APB_COST,         /* 6-8: success at a cost, or partial   */
    APB_SUCCESS,      /* 9-11: success                        */
    APB_CRIT          /* 12+: success with something extra    */
};

typedef struct {
    uint8_t die1;
    uint8_t die2;
    int16_t total;
    uint8_t result;
} apb_roll;

uint8_t apb_classify(int16_t total);
uint8_t apb_check(apb_rng *rng, uint8_t stat, int8_t bonus, int8_t difficulty,
                  apb_roll *out);

/* -------------------------------------------------------- characters */

#define APB_NAME_LEN     8
#define APB_EQUIP_SLOTS  6
#define APB_PACK_SLOTS   6
#define APB_ECHO_SLOTS   8

#define APB_FLAG_VERIFIED 0x01  /* approved by the hub server          */
#define APB_FLAG_RETIRED  0x02  /* paid their Debt and went home       */

typedef struct {
    uint16_t id;     /* 1..1023 in the Echo registry, 0 = empty slot */
    uint8_t  state;  /* 1..3, meaning set by the registry, 0 = unset  */
} apb_echo;

typedef struct {
    char     name[APB_NAME_LEN + 1];
    uint8_t  race;
    uint8_t  cls;
    uint8_t  level;
    uint8_t  xp;
    uint8_t  stat[APB_STAT_COUNT];
    uint16_t perks[2];
    uint16_t debt;
    uint16_t equipped[APB_EQUIP_SLOTS];  /* item registry IDs, 0 = empty */
    uint16_t pack[APB_PACK_SLOTS];
    apb_echo echo[APB_ECHO_SLOTS];       /* oldest first */
    uint8_t  flags;
} apb_character;

void    apb_character_init(apb_character *ch, const char *name, uint8_t race,
                           uint8_t cls);
uint8_t apb_health_max(const apb_character *ch);
uint8_t apb_xp_to_next(uint8_t level);
uint8_t apb_gain_xp(apb_character *ch, uint8_t amount); /* returns levels gained */

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

#define APB_PASSPORT_VERSION 1
#define APB_PASSWORD_LINES   4
#define APB_PASSWORD_LINE    20   /* 19 data symbols + 1 check symbol */
#define APB_PASSWORD_LEN     (APB_PASSWORD_LINES * APB_PASSWORD_LINE)
#define APB_PASSWORD_BUF     (APB_PASSWORD_LEN + 1)

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
