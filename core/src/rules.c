#include <string.h>

#include "apb.h"
#include "names.h"

/* ------------------------------------------- the core roll: d100 + skill */

uint8_t apb_resolve(uint8_t roll, int16_t total, int16_t tn)
{
    if (roll <= 1) return APB_FAIL;
    if (roll >= 100) return APB_CRIT;
    if (total > tn) {
        return (roll % 11 == 0) ? APB_CRIT : APB_SUCCESS;
    }
    if (total > tn - APB_COST_MARGIN) return APB_COST;
    return APB_FAIL;
}

uint8_t apb_check(apb_rng *rng, uint8_t rating, int16_t bonus, int16_t tn, apb_roll *out)
{
    out->roll = apb_d100(rng);
    out->total = (int16_t)(out->roll + rating + bonus);
    out->tn = tn;
    out->result = apb_resolve(out->roll, out->total, tn);
    return out->result;
}

int16_t apb_defense_tn(int16_t defense, int16_t reduce)
{
    int16_t d = (int16_t)(defense - reduce);

    return (int16_t)(APB_TN_BASE + (d < 0 ? 0 : d));
}

uint8_t apb_chance(int16_t rating_and_bonus, int16_t tn)
{
    uint8_t roll;
    uint8_t wins = 0;

    for (roll = 1; roll <= 100; ++roll) {
        if (apb_resolve(roll, (int16_t)(roll + rating_and_bonus), tn) >= APB_SUCCESS) {
            ++wins;
        }
    }
    return wins;
}

/* -------------------------------------------------------- characters */


void apb_character_init(apb_character *ch, const char *name, uint8_t race,
                        uint8_t cls)
{
    uint8_t i;

    memset(ch, 0, sizeof(*ch));
    apb_name_normalize(name, ch->name);
    ch->race = race;
    ch->cls = cls;
    ch->level = 1;
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        ch->stat[i] = APB_BUY_BASE;
    }
}

uint8_t apb_health_max(const apb_character *ch)
{
    /* 10 + Grit/4 + 2 per level: 18 for a new Grit-35 character, 235 at most. */
    return (uint8_t)(10 + ch->stat[APB_GRIT] / 4 + ch->level * 2);
}

uint8_t apb_skill(const apb_character *ch, uint8_t skill)
{
    uint16_t v;

    if (skill >= APB_SKILL_COUNT) return 0;
    v = (uint16_t)(ch->stat[apb_skill_stat[skill]] / 2 + ch->training[skill]);
    return (uint8_t)(v > APB_RATING_MAX ? APB_RATING_MAX : v);
}

/* ---------------------------------------------- character creation */

/* Race and class bonuses and tags come from the registry (registry.c). */

uint8_t apb_pointbuy_valid(const uint8_t *base)
{
    uint8_t i;
    uint16_t spent = 0;

    for (i = 0; i < APB_STAT_COUNT; ++i) {
        if (base[i] < APB_BUY_BASE || base[i] > APB_BUY_MAX) {
            return 0;
        }
        spent = (uint16_t)(spent + base[i] - APB_BUY_BASE);
    }
    return spent == APB_BUY_POINTS;
}

uint8_t apb_roll_stat(apb_rng *rng)
{
    uint8_t sum = (uint8_t)(apb_d6(rng) + apb_d6(rng) + apb_d6(rng));

    return (uint8_t)(sum * 5);
}

void apb_roll_stats(apb_rng *rng, uint8_t *out)
{
    uint8_t i;

    for (i = 0; i < APB_STAT_COUNT; ++i) {
        out[i] = apb_roll_stat(rng);
    }
}

static void add_capped(uint8_t *value, uint8_t amount)
{
    uint16_t v = (uint16_t)(*value + amount);

    *value = (uint8_t)(v > APB_RATING_MAX ? APB_RATING_MAX : v);
}

static void tag_skill(apb_character *ch, uint8_t skill)
{
    ch->tags |= (uint16_t)(1u << skill);
    ch->training[skill] = APB_TAG_BONUS;
}

uint8_t apb_character_create(apb_character *ch, const char *name, uint8_t race,
                             uint8_t cls, const uint8_t *base, uint8_t extra_tag)
{
    uint8_t i;

    if (race >= APB_RACE_COUNT || cls >= APB_CLASS_COUNT
        || extra_tag >= APB_SKILL_COUNT
        || extra_tag == apb_class_tags[cls][0]
        || extra_tag == apb_class_tags[cls][1]) {
        return 0;
    }

    apb_character_init(ch, name, race, cls);
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        ch->stat[i] = base[i] > APB_RATING_MAX ? APB_RATING_MAX : base[i];
    }
    add_capped(&ch->stat[apb_race_bonus[race]], APB_RACE_BONUS);
    add_capped(&ch->stat[apb_class_bonus[cls]], APB_CLASS_BONUS);
    tag_skill(ch, apb_class_tags[cls][0]);
    tag_skill(ch, apb_class_tags[cls][1]);
    tag_skill(ch, extra_tag);
    return 1;
}

/* ------------------------------------------------------- progression */

uint16_t apb_xp_award(uint16_t base, uint8_t level, uint8_t band_max)
{
    uint8_t over;

    if (level <= band_max) return base;
    over = (uint8_t)(level - band_max);
    if (over >= 10) return 0;
    return (uint16_t)((uint16_t)(base * (uint16_t)(10 - over)) / 10);
}

uint8_t apb_skill_points_per_level(const apb_character *ch)
{
    return (uint8_t)(1 + ch->stat[APB_WITS] / 20);
}

uint8_t apb_skill_raise_cost(uint8_t rating)
{
    if (rating < 50) return 1;
    if (rating < 75) return 2;
    if (rating < 90) return 3;
    return 4;
}

uint8_t apb_gain_xp(apb_character *ch, uint16_t amount)
{
    uint8_t gained = 0;
    uint16_t sp;

    if (ch->level >= APB_LEVEL_MAX) {
        ch->xp = 0;
        return 0;
    }
    amount = (uint16_t)(amount + ch->xp);
    while (amount >= APB_XP_PER_LEVEL && ch->level < APB_LEVEL_MAX) {
        amount = (uint16_t)(amount - APB_XP_PER_LEVEL);
        ++ch->level;
        ++gained;
        sp = (uint16_t)(ch->stat_points + APB_STAT_POINTS_PER_LEVEL);
        ch->stat_points = (uint8_t)(sp > 255 ? 255 : sp);
        sp = (uint16_t)(ch->skill_points + apb_skill_points_per_level(ch));
        ch->skill_points = (uint8_t)(sp > 255 ? 255 : sp);
    }
    ch->xp = (uint8_t)(ch->level >= APB_LEVEL_MAX ? 0 : amount);
    return gained;
}

uint8_t apb_raise_stat(apb_character *ch, uint8_t stat)
{
    if (stat >= APB_STAT_COUNT || ch->stat_points == 0
        || ch->stat[stat] >= APB_RATING_MAX) {
        return 0;
    }
    --ch->stat_points;
    ++ch->stat[stat];
    return 1;
}

uint8_t apb_raise_skill(apb_character *ch, uint8_t skill)
{
    uint8_t cost;

    if (skill >= APB_SKILL_COUNT || ch->training[skill] >= APB_RATING_MAX) {
        return 0;
    }
    cost = apb_skill_raise_cost(apb_skill(ch, skill));
    if (ch->skill_points < cost) {
        return 0;
    }
    ch->skill_points = (uint8_t)(ch->skill_points - cost);
    add_capped(&ch->training[skill], (uint8_t)((ch->tags >> skill) & 1u ? 2 : 1));
    return 1;
}
