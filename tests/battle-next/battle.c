/*
 * Plays a battle scenario on the rules lab's engine (core/next/, docs/turn.md) and prints
 * every event, for tests/battle-next/run_battles.py. tests/battle/battle.c's runner, with
 * rules v1's additions.
 *
 *   battle-next FILE
 *
 * A scenario is lines of words ('#' lines and blank lines are skipped):
 *
 *   seed N
 *   surprise none|foes|travelers
 *   map                  then the rows of the map (docs/combat.md), then: end
 *   hazard DAMAGE TYPE COND              what the map's hazards do (TYPE: kinetic.. or
 *                                        none; COND a condition's name, or -)
 *   traveler PASSPORT WEAPON [HEALTH]    takes the next '@' square, row by row
 *   foe L HEALTH GRACE DODGE ARMOR WARD SOAK SPEED ATTACK WEAPON RANGED POWER TYPE AREA
 *       WEAK BEHAVIOR COWARD [hit COND]  stands on the map's letter L
 *   trait WHO COND                       a condition for good (a foe's nature)
 *   put WHO COND                         a condition as the fight begins
 *   act X Y KIND TARGET [DX DY]          a traveler's turn (KIND: APB_ACT_*, 5 Shove,
 *                                        6 Dash to DX, DY)
 *   act q                                a traveler's turn on quick
 *
 * Every attack's line ends with the target's Soak and its conditions' tags, so
 * run_battles.py can work the damage out again.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apb.h"
#include "apb_battle.h"

static apb_rng rng;
static apb_character ch;
static apb_fighter f;
static apb_action act;
static char line[200];
static char word[200];
static char name[64];
static char rows[APB_MAP_H_MAX][APB_MAP_W_MAX + 2];
static int v[17];
static uint8_t ids[APB_COND_SLOTS];
static uint8_t left[APB_COND_SLOTS];

static const char *const results[] = { "fail", "cost", "success", "crit" };
static const char *const endings[] = { "on", "won", "lost", "fled" };
static const char *const types[] = { "kinetic", "energy", "fire", "cold", "mind" };

static const char *cond_name(uint8_t c)
{
    /* Not a ?: : cc65 won't mix a const char * and a string literal there. */
    if (apb_conds[c].name) return apb_conds[c].name;
    return "?";
}

static uint8_t cond_named(const char *s)
{
    uint16_t i;

    for (i = 1; i <= APB_COND_MAX; ++i) {
        if (apb_conds[i].name && strcmp(apb_conds[i].name, s) == 0) return (uint8_t)i;
    }
    return 0;
}

static uint8_t type_named(const char *s)
{
    uint8_t i;

    for (i = 0; i < 5; ++i) {
        if (strcmp(types[i], s) == 0) return i;
    }
    return APB_NO_TYPE;
}

static void tags(uint8_t who)
{
    uint8_t n = apb_battle_conditions(who, ids, left);
    uint8_t i;

    printf(" [soak %u", apb_battle_soak(who));
    for (i = 0; i < n; ++i) printf(" %s", apb_conds[ids[i]].tag);
    printf("]");
}

static void on_event(const apb_event *e)
{
    switch (e->kind) {
    case APB_EV_TURN:
        printf("round %u: %u's turn (speed %u)\n", e->value, e->actor, apb_battle_speed(e->actor));
        break;
    case APB_EV_MOVE:   printf("  %u steps to %u,%u\n", e->actor, e->x, e->y); break;
    case APB_EV_ATTACK:
        printf("  %u attacks %u: %u+%d=%d vs %d: %s, %u damage", e->actor, e->target,
               e->roll.roll, e->roll.total - e->roll.roll, e->roll.total, e->roll.tn,
               results[e->roll.result], e->value);
        tags(e->target);
        printf("\n");
        break;
    case APB_EV_DOWN:   printf("  %u is down\n", e->target); break;
    case APB_EV_HAZARD: printf("  %u takes %u from the ground\n", e->actor, e->value); break;
    case APB_EV_GUARD:  printf("  %u guards\n", e->actor); break;
    case APB_EV_WAIT:   printf("  %u waits\n", e->actor); break;
    case APB_EV_FREE:   printf("  %u gets a free attack on %u\n", e->actor, e->target); break;
    case APB_EV_FLEE:
        if (e->roll.roll) {
            printf("  %u tries to flee: %u+%d=%d vs %d: %s\n", e->actor, e->roll.roll,
                   e->roll.total - e->roll.roll, e->roll.total, e->roll.tn, results[e->roll.result]);
        } else {
            printf("  %u takes the exit\n", e->actor);
        }
        break;
    case APB_EV_GONE:   printf("  %u is gone\n", e->actor); break;
    case APB_EV_END:    printf("the fight is %s\n", endings[e->value & 3]); break;
    case APB_EV_COND_ON:
        printf("  %u is %s", e->actor, cond_name(e->cond));
        if (e->value) printf(" (%u rounds)", e->value);
        printf("\n");
        break;
    case APB_EV_COND_OFF: printf("  %u is no longer %s\n", e->actor, cond_name(e->cond)); break;
    case APB_EV_IMMUNE:   printf("  %u is immune to %s\n", e->actor, cond_name(e->cond)); break;
    case APB_EV_TICK:
        printf("  %u takes %u from %s", e->actor, e->value, cond_name(e->cond));
        tags(e->actor);
        printf("\n");
        break;
    case APB_EV_HEAL:   printf("  %u heals %u from %s\n", e->actor, e->value, cond_name(e->cond)); break;
    case APB_EV_SKIP:   printf("  %u loses the turn: %s\n", e->actor, cond_name(e->cond)); break;
    case APB_EV_SHAKE:
        printf("  %u tries to shake off %s: %u+%d=%d vs %d: %s\n", e->actor, cond_name(e->cond),
               e->roll.roll, e->roll.total - e->roll.roll, e->roll.total, e->roll.tn,
               results[e->roll.result]);
        break;
    case APB_EV_STAND:  printf("  %u stands up (%u to move)\n", e->actor, e->value); break;
    case APB_EV_DASH:   printf("  %u dashes\n", e->actor); break;
    case APB_EV_SHOVE:
        printf("  %u shoves %u: %u+%d=%d vs %d: %s\n", e->actor, e->target, e->roll.roll,
               e->roll.total - e->roll.roll, e->roll.total, e->roll.tn, results[e->roll.result]);
        break;
    case APB_EV_PUSH:   printf("  %u is pushed to %u,%u\n", e->actor, e->x, e->y); break;
    case APB_EV_SLAM:   printf("  %u is slammed into something: %u damage\n", e->actor, e->value); break;
    case APB_EV_FALL:   printf("  %u falls into the pit\n", e->actor); break;
    case APB_EV_THORNS: printf("  %u's %s hurts %u: %u damage\n", e->actor, cond_name(e->cond), e->target, e->value); break;
    case APB_EV_ABSORB: printf("  %u's barrier takes %u\n", e->actor, e->value); break;
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
    uint8_t c;
    uint16_t seed = 1;
    char letter;
    char *p;
    int n;

    if (argc != 2 || !(in = fopen(argv[1], "r"))) {
        printf("usage: battle-next FILE\n");
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
        } else if (strcmp(word, "hazard") == 0) {
            if (sscanf(line, "%*s %d %63s %63s", &v[0], word, name) != 3) {
                printf("bad hazard: %s\n", line);
                return 1;
            }
            apb_battle_set_hazard((uint8_t)v[0], type_named(word), cond_named(name));
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
            who = apb_battle_add(&f);
            if (who == APB_NOBODY) {
                printf("couldn't place it\n");
            } else {
                printf("%u: traveler at %u,%u, health %u, attack %u, speed %u, TN to hit %d",
                       who, f.x, f.y, f.health, f.attack, apb_battle_speed(who),
                       apb_hit_tn(apb_battle_dodge(who), apb_battle_armor(who), 0, 0));
                tags(who);
                printf("\n");
            }
        } else if (strcmp(word, "foe") == 0) {
            n = 0;
            if (sscanf(line, "%*s %c %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d%n", &letter,
                       &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8], &v[9],
                       &v[10], &v[11], &v[12], &v[13], &v[14], &v[15], &n) != 17) {
                printf("bad foe: %s\n", line);
                return 1;
            }
            memset(&f, 0, sizeof(f));
            f.side = APB_SIDE_FOE;
            f.race = 0xFF;
            f.health = f.health_max = (uint8_t)v[0];
            f.grace = (uint8_t)v[1]; f.dodge = (uint8_t)v[2]; f.armor = (uint8_t)v[3];
            f.ward = (uint8_t)v[4]; f.soak = (uint8_t)v[5]; f.speed = (uint8_t)v[6];
            f.attack = (uint8_t)v[7]; f.weapon = (uint8_t)v[8]; f.ranged = (uint8_t)v[9];
            f.power = (uint8_t)v[10]; f.dmg_type = (uint8_t)v[11]; f.area = (uint8_t)v[12];
            f.weak_type = (uint8_t)v[13]; f.behavior = (uint8_t)v[14]; f.coward = (uint8_t)v[15];
            p = line + n;
            if (sscanf(p, " hit %63s", name) == 1) f.on_hit = cond_named(name);
            find(letter, 0, &f.x, &f.y);
            who = apb_battle_add(&f);
            if (who == APB_NOBODY) printf("couldn't place it\n");
            else printf("%u: foe %c at %u,%u, health %u, speed %u\n", who, letter, f.x, f.y, f.health,
                        apb_battle_speed(who));
        } else if (strcmp(word, "trait") == 0 || strcmp(word, "put") == 0) {
            if (sscanf(line, "%*s %d %63s", &v[0], name) != 2 || !(c = cond_named(name))) {
                printf("bad %s: %s\n", word, line);
                return 1;
            }
            if (word[0] == 't') {
                if (!apb_battle_trait((uint8_t)v[0], c)) printf("no room for %s\n", name);
                else printf("%d has %s for good\n", v[0], name);
            } else {
                apb_battle_put((uint8_t)v[0], c);
            }
        } else if (strcmp(word, "act") == 0) {
            if (!started) {
                apb_battle_start(surprise);
                started = 1;
            }
            who = apb_battle_next();
            if (who == APB_NOBODY) break;
            if (strcmp(line, "act q") == 0) {
                apb_battle_quick(who, &act);
                printf("  (quick: act %u %u %u %u)\n", act.move_x, act.move_y, act.kind, act.target);
            } else {
                v[4] = v[5] = 0;
                sscanf(line, "%*s %d %d %d %d %d %d", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5]);
                act.move_x = (uint8_t)v[0];
                act.move_y = (uint8_t)v[1];
                act.kind = (uint8_t)v[2];
                act.target = (uint8_t)v[3];
                act.dash_x = (uint8_t)v[4];
                act.dash_y = (uint8_t)v[5];
            }
            if (!apb_battle_act(who, &act)) printf("  (not allowed: %s)\n", line);
        }
    }
    fclose(in);
    if (!started) apb_battle_start(surprise);
    if (apb_battle_next() != APB_NOBODY) printf("out of actions\n");
    return 0;
}
