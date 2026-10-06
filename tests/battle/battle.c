/*
 * Plays a battle scenario and prints every event, for tests/battle/run_battles.py.
 * Builds natively and for sim65, so the same battle can be compared on both.
 *
 *   battle FILE
 *
 * A scenario is lines of words ('#' lines and blank lines are skipped):
 *
 *   seed N
 *   surprise none|foes|travelers
 *   map                  then the rows of the map (docs/combat.md), then: end
 *   traveler PASSPORT WEAPON [HEALTH]    takes the next '@' square, row by row
 *   foe L HEALTH GRACE DODGE ARMOR WARD SOAK SPEED ATTACK WEAPON RANGED POWER TYPE AREA
 *       WEAK BEHAVIOR COWARD             stands on the map's letter L
 *   act X Y KIND TARGET                  a traveler's turn (KIND: APB_ACT_*)
 *
 * Fighters are numbered in the order they're added. When the actions run out, the log
 * ends with "out of actions".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apb.h"
#include "apb_battle.h"

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static apb_rng rng;
static apb_character ch;
static apb_fighter f;
static apb_action act;
static char line[200];
static char word[200];
static char rows[APB_MAP_H_MAX][APB_MAP_W_MAX + 2];
static int v[17];

static const char *const results[] = { "fail", "cost", "success", "crit" };
static const char *const endings[] = { "on", "won", "lost", "fled" };

static void on_event(const apb_event *e)
{
    switch (e->kind) {
    case APB_EV_TURN:   printf("round %u: %u's turn\n", e->value, e->actor); break;
    case APB_EV_MOVE:   printf("  %u moves to %u,%u\n", e->actor, e->x, e->y); break;
    case APB_EV_ATTACK:
        printf("  %u attacks %u: %u+%d=%d vs %d: %s, %u damage\n", e->actor, e->target,
               e->roll.roll, e->roll.total - e->roll.roll, e->roll.total, e->roll.tn,
               results[e->roll.result], e->value);
        break;
    case APB_EV_DOWN:   printf("  %u is down\n", e->target); break;
    case APB_EV_HAZARD: printf("  %u takes %u from the ground\n", e->actor, e->value); break;
    case APB_EV_DEFEND: printf("  %u defends\n", e->actor); break;
    case APB_EV_HELP:   printf("  %u opens %u up\n", e->actor, e->target); break;
    case APB_EV_FLEE:
        if (e->roll.roll) {
            printf("  %u tries to flee: %u+%d=%d vs %d: %s\n", e->actor, e->roll.roll,
                   e->roll.total - e->roll.roll, e->roll.total, e->roll.tn,
                   results[e->roll.result]);
        } else {
            printf("  %u takes the exit\n", e->actor);
        }
        break;
    case APB_EV_GONE:   printf("  %u is gone\n", e->actor); break;
    case APB_EV_END:    printf("the fight is %s\n", endings[e->value & 3]); break;
    }
}

static uint8_t tile_of(char c)
{
    switch (c) {
    case '#': return APB_TILE_WALL;
    case 'O': return APB_TILE_PIT;
    case '~': return APB_TILE_ROUGH;
    case '+': return APB_TILE_COVER;
    case '^': return APB_TILE_HAZARD;
    case '=': return APB_TILE_HIGH;
    case '>': return APB_TILE_EXIT;
    default:  return APB_TILE_OPEN;
    }
}

/* The n-th square (row by row) holding `c`. */
static uint8_t find(char c, uint8_t n, uint8_t *x, uint8_t *y)
{
    uint8_t i;
    uint8_t j;

    for (j = 0; j < apb_battle_height(); ++j) {
        for (i = 0; i < apb_battle_width(); ++i) {
            if (rows[j][i] == c && n-- == 0) {
                *x = i;
                *y = j;
                return 1;
            }
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    FILE *in;
    uint8_t h = 0;
    uint8_t w = 0;
    uint8_t in_map = 0;
    uint8_t travelers = 0;
    uint8_t surprise = APB_SURPRISE_NONE;
    uint8_t started = 0;
    uint8_t who;
    uint8_t i;
    uint16_t seed = 1;
    char letter;

    if (argc != 2 || !(in = fopen(argv[1], "r"))) {
        printf("usage: battle FILE\n");
        return 2;
    }
    memset(rows, 0, sizeof(rows));
    while (fgets(line, sizeof(line), in)) {
        line[strcspn(line, "\r\n")] = '\0';
        if (in_map) {
            if (strcmp(line, "end") == 0) {
                in_map = 0;
                apb_battle_init(w, h, &rng, on_event);
                for (h = 0; h < apb_battle_height(); ++h) {
                    for (i = 0; i < apb_battle_width(); ++i) apb_battle_set_tile(i, h, tile_of(rows[h][i]));
                }
            } else if (h < APB_MAP_H_MAX) {
                for (i = 0; i < APB_MAP_W_MAX && line[i]; ++i) rows[h][i] = line[i];
                rows[h][i] = '\0';
                if (i > w) w = i;
                ++h;
            }
            continue;
        }
        if (line[0] == '#' || line[0] == '\0') continue;
        if (sscanf(line, "%s", word) != 1) continue;
        if (strcmp(word, "seed") == 0) {
            seed = (uint16_t)atol(line + 5);
            apb_rng_seed(&rng, seed);
        } else if (strcmp(word, "surprise") == 0) {
            surprise = strstr(line, "foes") ? APB_SURPRISE_FOES
                     : strstr(line, "travelers") ? APB_SURPRISE_TRAVELERS : APB_SURPRISE_NONE;
        } else if (strcmp(word, "map") == 0) {
            in_map = 1;
            h = w = 0;
        } else if (strcmp(word, "traveler") == 0) {
            v[1] = -1;
            if (sscanf(line, "%*s %s %d %d", word, &v[0], &v[1]) < 2
                || apb_passport_decode(word, &ch, 0) != APB_PP_OK) {
                printf("bad traveler: %s\n", line);
                return 1;
            }
            apb_fighter_from(&f, &ch, (uint16_t)v[0]);
            if (v[1] >= 0) f.health = (uint8_t)v[1];
            find('@', travelers++, &f.x, &f.y);
            printf("%u: traveler at %u,%u, health %u, attack %u, TN to hit %d\n",
                   apb_battle_count(), f.x, f.y, f.health, f.attack, apb_hit_tn(f.dodge, f.armor, 0, 0));
            if (apb_battle_add(&f) == APB_NOBODY) printf("couldn't place it\n");
        } else if (strcmp(word, "foe") == 0) {
            if (sscanf(line, "%*s %c %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d", &letter,
                       &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8], &v[9],
                       &v[10], &v[11], &v[12], &v[13], &v[14], &v[15]) != 17) {
                printf("bad foe: %s\n", line);
                return 1;
            }
            memset(&f, 0, sizeof(f));
            f.side = APB_SIDE_FOE;
            f.health = f.health_max = (uint8_t)v[0];
            f.grace = (uint8_t)v[1]; f.dodge = (uint8_t)v[2]; f.armor = (uint8_t)v[3];
            f.ward = (uint8_t)v[4]; f.soak = (uint8_t)v[5]; f.speed = (uint8_t)v[6];
            f.attack = (uint8_t)v[7]; f.weapon = (uint8_t)v[8]; f.ranged = (uint8_t)v[9];
            f.power = (uint8_t)v[10]; f.dmg_type = (uint8_t)v[11]; f.area = (uint8_t)v[12];
            f.weak_type = (uint8_t)v[13]; f.behavior = (uint8_t)v[14]; f.coward = (uint8_t)v[15];
            find(letter, 0, &f.x, &f.y);
            printf("%u: foe %c at %u,%u, health %u\n", apb_battle_count(), letter, f.x, f.y, f.health);
            if (apb_battle_add(&f) == APB_NOBODY) printf("couldn't place it\n");
        } else if (strcmp(word, "act") == 0) {
            if (!started) {
                apb_battle_start(surprise);
                started = 1;
            }
            who = apb_battle_next();
            if (who == APB_NOBODY) break;
            sscanf(line, "%*s %d %d %d %d", &v[0], &v[1], &v[2], &v[3]);
            act.move_x = (uint8_t)v[0];
            act.move_y = (uint8_t)v[1];
            act.kind = (uint8_t)v[2];
            act.target = (uint8_t)v[3];
            if (!apb_battle_act(who, &act)) printf("  (not allowed: %s)\n", line);
        }
    }
    fclose(in);
    if (!started) apb_battle_start(surprise);
    if (apb_battle_next() != APB_NOBODY) printf("out of actions\n");
    return 0;
}
