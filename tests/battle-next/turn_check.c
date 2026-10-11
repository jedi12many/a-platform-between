/*
 * For tests/battle-next/run_battles.py: puts conditions on a fighter in the rules lab's
 * engine (core/next/battle.c) and prints its numbers, for tools/rules/turn.py to work out
 * again. One case a line on stdin:
 *
 *   GRACE ARMOR_TIER RACE SPEED DODGE ARMOR WARD SOAK COND COND ...
 *
 * (RACE 255: none; conditions by id, in the order they're put on.) Prints, a line each:
 *
 *   SPEED_V1 SPEED DODGE ARMOR WARD SOAK: ID ID ...    (its conditions, in its slots)
 */
#include <stdio.h>
#include <string.h>

#include "apb.h"
#include "apb_battle.h"

static apb_rng rng;
static apb_fighter f;
static char line[400];
static uint8_t ids[APB_COND_SLOTS];
static uint8_t left[APB_COND_SLOTS];

int main(void)
{
    int v[8];
    int n;
    int c;
    uint8_t k;
    uint8_t got;
    char *p;

    apb_rng_seed(&rng, 1);
    while (fgets(line, sizeof(line), stdin)) {
        if (sscanf(line, "%d %d %d %d %d %d %d %d%n", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5],
                   &v[6], &v[7], &n) != 8) {
            continue;
        }
        apb_battle_init(3, 3, &rng, 0);
        memset(&f, 0, sizeof(f));
        f.side = APB_SIDE_TRAVELER;
        f.x = f.y = 1;
        f.health = f.health_max = 50;
        f.grace = (uint8_t)v[0];
        f.race = (uint8_t)v[2];
        f.speed = (uint8_t)v[3];
        f.dodge = (uint8_t)v[4];
        f.armor = (uint8_t)v[5];
        f.ward = (uint8_t)v[6];
        f.soak = (uint8_t)v[7];
        apb_battle_add(&f);
        p = line + n;
        while (sscanf(p, "%d%n", &c, &n) == 1) {
            apb_battle_put(0, (uint8_t)c);
            p += n;
        }
        printf("%u %u %u %u %u %u:", apb_speed_v1((uint8_t)v[0], (uint8_t)v[1]), apb_battle_speed(0),
               apb_battle_dodge(0), apb_battle_armor(0), apb_battle_ward(0), apb_battle_soak(0));
        got = apb_battle_conditions(0, ids, left);
        for (k = 0; k < got; ++k) printf(" %u", ids[k]);
        printf("\n");
    }
    return 0;
}
