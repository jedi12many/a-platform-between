#include <string.h>

#include "apb.h"
#include "names.h"

/* ---------------------------------------------------- the core roll */

uint8_t apb_classify(int16_t total)
{
    if (total >= 12) return APB_CRIT;
    if (total >= 9)  return APB_SUCCESS;
    if (total >= 6)  return APB_COST;
    return APB_FAIL;
}

uint8_t apb_check(apb_rng *rng, uint8_t stat, int8_t bonus, int8_t difficulty,
                  apb_roll *out)
{
    out->die1 = apb_d6(rng);
    out->die2 = apb_d6(rng);
    out->total = (int16_t)(out->die1 + out->die2 + stat + bonus - difficulty);
    out->result = apb_classify(out->total);
    return out->result;
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
        ch->stat[i] = 3;
    }
}

uint8_t apb_health_max(const apb_character *ch)
{
    return (uint8_t)(ch->stat[APB_GRIT] * 3 + ch->level * 2);
}

uint8_t apb_xp_to_next(uint8_t level)
{
    /* 15 at level 1, 105 at level 19: always fits the Passport's 7 bits. */
    return (uint8_t)(10 + level * 5);
}

uint8_t apb_gain_xp(apb_character *ch, uint8_t amount)
{
    uint16_t xp = (uint16_t)(ch->xp + amount);
    uint8_t gained = 0;

    while (ch->level < APB_LEVEL_MAX && xp >= apb_xp_to_next(ch->level)) {
        xp = (uint16_t)(xp - apb_xp_to_next(ch->level));
        ++ch->level;
        ++gained;
    }
    if (ch->level >= APB_LEVEL_MAX) {
        xp = 0;
    }
    ch->xp = (uint8_t)xp;
    return gained;
}
