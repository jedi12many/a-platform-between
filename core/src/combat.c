#include "apb.h"

/*
 * Combat rules: docs/combat.md. Only the arithmetic lives here; the battle itself
 * (maps, turns, foes) is milestone E3.2.
 */

uint8_t apb_dodge(const apb_character *ch)
{
    return (uint8_t)(ch->stat[APB_GRACE] / 5u);
}

uint8_t apb_speed(const apb_character *ch)
{
    return (uint8_t)(4u + ch->stat[APB_GRACE] / 25u);
}

uint8_t apb_armor(const apb_character *ch)
{
    uint8_t i;
    uint8_t best = 0;
    uint16_t id;

    for (i = 0; i < APB_EQUIP_SLOTS; ++i) {
        id = ch->equipped[i];
        if (id != 0 && id < APB_ITEM_COUNT && apb_items[id].archetype == APB_ARCH_ARMOR
            && apb_items[id].tier > best) {
            best = apb_items[id].tier;
        }
    }
    return (uint8_t)(10u * best);
}

uint8_t apb_melee_bonus(const apb_character *ch)
{
    return (uint8_t)(ch->stat[APB_MIGHT] / 20u);
}

uint8_t apb_weapon_damage(uint16_t item)
{
    if (item == 0 || item >= APB_ITEM_COUNT || apb_items[item].tier == 0) {
        return APB_UNARMED_DAMAGE;
    }
    return (uint8_t)(5u * apb_items[item].tier);
}

int16_t apb_hit_tn(int16_t dodge, int16_t defense, int16_t bonus, int16_t reduce)
{
    int16_t d = (int16_t)(dodge + defense + bonus - reduce);

    return (int16_t)(APB_TN_BASE + (d < 0 ? 0 : d));
}

uint16_t apb_damage(const apb_roll *roll, uint8_t weapon, uint8_t stat_bonus, uint8_t soak)
{
    uint16_t dmg;
    int16_t over;

    if (roll->result == APB_FAIL) {
        return 0;
    }
    if (roll->result == APB_COST) {
        dmg = (uint16_t)(weapon / 2u);              /* glancing: no margin, no bonus */
    } else {
        over = (int16_t)(roll->total - roll->tn);  /* a natural 100 may not beat it */
        dmg = (uint16_t)(weapon + stat_bonus + (over > 0 ? over / 10 : 0));
        if (roll->result == APB_CRIT) {
            dmg = (uint16_t)(dmg * 2u);
        }
    }
    return (uint16_t)(dmg > soak ? dmg - soak : 0);
}

uint16_t apb_attack(apb_rng *rng, uint8_t rating, int16_t bonus, int16_t tn, uint8_t weapon,
                    uint8_t stat_bonus, uint8_t soak, apb_roll *out)
{
    apb_check(rng, rating, bonus, tn, out);
    return apb_damage(out, weapon, stat_bonus, soak);
}

uint8_t apb_in_area(int8_t dx, int8_t dy, uint8_t area)
{
    uint8_t ax = (uint8_t)(dx < 0 ? -dx : dx);
    uint8_t ay = (uint8_t)(dy < 0 ? -dy : dy);

    return (uint8_t)(ax <= area && ay <= area);
}

int16_t apb_flee_tn(uint8_t adjacent_foes)
{
    return (int16_t)(APB_FLEE_TN + APB_FLEE_PER_FOE * adjacent_foes);
}

/* Movement cost of each tile, in the order of the APB_TILE_ enum; 0 can't be entered. */
static const uint8_t tile_cost[APB_TILE_COUNT] = { 1, 0, 0, 2, 2, 1, 1, 1 };

uint8_t apb_tile_cost(uint8_t tile)
{
    return tile < APB_TILE_COUNT ? tile_cost[tile] : 0;
}

uint8_t apb_tile_blocks_sight(uint8_t tile)
{
    return (uint8_t)(tile == APB_TILE_WALL || tile >= APB_TILE_COUNT);
}
