/*
 * Combat rules on the command line, for tests/combat/check_combat.py to compare with
 * the Python reference (tools/rules/combat.py). Native and sim65.
 *
 *   attack attacks SEED N RATING BONUS TN WEAPON STAT SOAK   N attacks: roll total result damage
 *   attack sheet PASSPORT                                    dodge speed armor melee, weapons
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apb.h"

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static apb_character ch;
static apb_rng rng;
static apb_roll roll;

int main(int argc, char **argv)
{
    uint16_t i;
    uint16_t n;
    uint16_t dmg;

    if (argc == 10 && strcmp(argv[1], "attacks") == 0) {
        apb_rng_seed(&rng, (uint16_t)atol(argv[2]));
        n = (uint16_t)atoi(argv[3]);
        for (i = 0; i < n; ++i) {
            dmg = apb_attack(&rng, (uint8_t)atoi(argv[4]), (int16_t)atoi(argv[5]),
                             (int16_t)atoi(argv[6]), (uint8_t)atoi(argv[7]),
                             (uint8_t)atoi(argv[8]), (uint8_t)atoi(argv[9]), &roll);
            printf("%u %d %u %u\n", roll.roll, roll.total, roll.result, dmg);
        }
        return 0;
    }
    if (argc == 3 && strcmp(argv[1], "sheet") == 0) {
        if (apb_passport_decode(argv[2], &ch, 0) != APB_PP_OK) {
            printf("bad passport\n");
            return 1;
        }
        printf("%u %u %u %u", apb_dodge(&ch), apb_speed(&ch), apb_armor(&ch),
               apb_melee_bonus(&ch));
        for (i = 0; i < APB_EQUIP_SLOTS; ++i) {
            if (ch.equipped[i]) printf(" %u", apb_weapon_damage(ch.equipped[i]));
        }
        printf("\n");
        return 0;
    }
    printf("usage: attack attacks SEED N RATING BONUS TN WEAPON STAT SOAK | sheet PASSPORT\n");
    return 2;
}
