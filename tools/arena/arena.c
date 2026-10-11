/*
 * The arena's fights (docs/arena.md): many battles on the real battle engine
 * (core/src/battle.c), both sides played by the computer, for tools/arena/arena.py to
 * add up. Every fight starts the same and only the dice differ: fight i is seeded
 * SEED + i.
 *
 *   arena FILE
 *
 * FILE is written by arena.py, one fighter a line:
 *
 *   fights N
 *   seed S
 *   rounds R                         a fight still on after R rounds is a draw
 *   map W H                          then H rows of W squares (docs/combat.md)
 *   traveler X Y PASSPORT ARCH TIER TYPE ARMOR
 *                                    ARCH: melee, ranged or focus; TIER: the weapon's
 *                                    (its damage is 5 x tier); TYPE: APB_DMG_*; ARMOR:
 *                                    the armor's tier (Armor 10 x tier)
 *   foe X Y HEALTH GRACE DODGE ARMOR WARD SOAK SPEED ATTACK WEAPON RANGED POWER TYPE AREA
 *       WEAK BEHAVIOR COWARD         a foe's card, as registry/foes.txt has it
 *
 * Built on the rules lab's engine (build/arena-next: core/next/, docs/turn.md), it also
 * reads:
 *
 *   hazard DAMAGE TYPE COND          what the map's hazards do (TYPE 255: none; COND an
 *                                    id from registry/conditions.txt, or 0)
 *   foe ... hit COND                 a condition the foe's hits put on
 *   foe ... level N                  its level (rules next: its Resist is twice it), 1 if not said
 *   power WHO POWER RANK             a power fighter WHO (in the order of the lines above)
 *                                    holds (an id from registry/powers.txt)
 *
 * Prints a line per fight:
 *
 *   fight I RESULT ROUNDS  then, per fighter: HEALTH DEALT DOWN
 *
 * RESULT: won, lost, fled or draw; HEALTH: what it has left; DEALT: the damage it did;
 * DOWN: the round it went down in, or 0. And with -v, each fight's events too.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apb.h"
#include "apb_battle.h"

#define LINE_MAX 400

static apb_rng rng;
static apb_character ch;
static apb_fighter fighters[APB_FIGHTERS_MAX];
static uint8_t fighter_count;
static char rows[APB_MAP_H_MAX][APB_MAP_W_MAX + 1];
static int map_w, map_h;
#ifdef APB_RULES_NEXT
static int hazard[3] = { APB_HAZARD_DAMAGE, APB_DMG_KINETIC, 0 };
static int powers[APB_FIGHTERS_MAX * APB_POWERS_HELD][3];
static int power_count;
#endif
static unsigned dealt[APB_FIGHTERS_MAX];
static unsigned down_round[APB_FIGHTERS_MAX];
static unsigned round_now;
static int verbose;

static const char *const endings[] = { "on", "won", "lost", "fled" };

static void on_event(const apb_event *e)
{
    switch (e->kind) {
    case APB_EV_TURN:
        round_now = e->value;
        break;
    case APB_EV_ATTACK:
    case APB_EV_HAZARD:
        if (e->kind == APB_EV_ATTACK && e->actor < APB_FIGHTERS_MAX) dealt[e->actor] += e->value;
        break;
#ifdef APB_RULES_NEXT
    case APB_EV_HIT:
        if (e->actor < APB_FIGHTERS_MAX) dealt[e->actor] += e->value;
        break;
#endif
    case APB_EV_DOWN:
        if (e->target < APB_FIGHTERS_MAX) down_round[e->target] = round_now;
        break;
    }
    if (!verbose) return;
    switch (e->kind) {
    case APB_EV_TURN:   printf("  round %u: %u's turn\n", e->value, e->actor); break;
    case APB_EV_MOVE:   printf("    %u moves to %u,%u\n", e->actor, e->x, e->y); break;
    case APB_EV_ATTACK:
        printf("    %u attacks %u: %u+%d=%d vs %d, %u damage\n", e->actor, e->target, e->roll.roll,
               e->roll.total - e->roll.roll, e->roll.total, e->roll.tn, e->value);
        break;
    case APB_EV_DOWN:   printf("    %u is down\n", e->target); break;
    case APB_EV_HAZARD: printf("    %u takes %u from the ground\n", e->actor, e->value); break;
    case APB_EV_GUARD:  printf("    %u guards\n", e->actor); break;
    case APB_EV_FREE:   printf("    %u gets a free attack on %u\n", e->actor, e->target); break;
    case APB_EV_GONE:   printf("    %u is gone\n", e->actor); break;
    case APB_EV_END:    printf("  the fight is %s\n", endings[e->value & 3]); break;
#ifdef APB_RULES_NEXT
    case APB_EV_POWER:  printf("    %u uses %s (tier %u) at %u,%u\n", e->actor, apb_powers[e->cond].name, e->value, e->x, e->y); break;
    case APB_EV_HIT:
        printf("    %u's %s on %u: %u+%d=%d vs %d, %u damage\n", e->actor, apb_powers[e->cond].name,
               e->target, e->roll.roll, e->roll.total - e->roll.roll, e->roll.total, e->roll.tn, e->value);
        break;
    case APB_EV_MEND:   printf("    %u heals %u: %u\n", e->actor, e->target, e->value); break;
    case APB_EV_COND_ON: printf("    %u is %s\n", e->actor, apb_conds[e->cond].name); break;
    case APB_EV_TICK:   printf("    %u takes %u from %s\n", e->actor, e->value, apb_conds[e->cond].name); break;
    case APB_EV_SHIFT:  printf("    %u is shifted to %u,%u\n", e->actor, e->x, e->y); break;
    case APB_EV_PUSH:   printf("    %u is pushed to %u,%u\n", e->actor, e->x, e->y); break;
    case APB_EV_FALL:   printf("    %u falls into the pit\n", e->actor); break;
#endif
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

/* A traveler's fighter: as apb_fighter_from makes it, with a weapon and armor of the
 * given archetype and tiers, as docs/combat.md prices them, so a build can be tried
 * with gear the registry hasn't got yet. */
static int traveler(apb_fighter *f, const char *passport, const char *arch, int tier, int type,
                    int armor)
{
    if (apb_passport_decode(passport, &ch, 0) != APB_PP_OK) return 0;
    apb_fighter_from(f, &ch, 0);
    f->weapon = (uint8_t)(tier ? 5 * tier : f->weapon);
    f->dmg_type = (uint8_t)type;
    f->armor = (uint8_t)(10 * armor);
#ifdef APB_RULES_NEXT
    f->speed = apb_speed_v1(f->grace, (uint8_t)armor);
#endif
    if (strcmp(arch, "ranged") == 0) {
        f->ranged = 1;
        f->stat_bonus = 0;
        f->attack = apb_skill(&ch, APB_SK_RANGED);
        f->behavior = APB_AI_SHOOT;
    } else if (strcmp(arch, "focus") == 0) {
        f->ranged = 1;
        f->power = 1;
        f->stat_bonus = 0;
        f->attack = apb_skill(&ch, APB_SK_CHANNEL);
        f->behavior = APB_AI_SHOOT;
    } else if (strcmp(arch, "melee") != 0) {
        return 0;
    }
    return 1;
}

static int read_file(const char *path, unsigned *fights, unsigned *seed, unsigned *rounds)
{
    FILE *in = fopen(path, "r");
    static char line[LINE_MAX];
    static char word[LINE_MAX];
    static char arch[16];
    int v[18];
    int row = -1;
    apb_fighter *f;

    if (!in) return 0;
    while (fgets(line, sizeof(line), in)) {
        line[strcspn(line, "\r\n")] = '\0';
        if (row >= 0 && row < map_h) {
            line[APB_MAP_W_MAX] = '\0';
            memcpy(rows[row], line, strlen(line) + 1);
            ++row;
            continue;
        }
        if (line[0] == '#' || sscanf(line, "%s", word) != 1) continue;
        if (strcmp(word, "fights") == 0) {
            *fights = (unsigned)atol(line + 7);
        } else if (strcmp(word, "seed") == 0) {
            *seed = (unsigned)atol(line + 5);
        } else if (strcmp(word, "rounds") == 0) {
            *rounds = (unsigned)atol(line + 7);
        } else if (strcmp(word, "map") == 0) {
            if (sscanf(line, "%*s %d %d", &map_w, &map_h) != 2 || map_w < 1 || map_h < 1
                || map_w > APB_MAP_W_MAX || map_h > APB_MAP_H_MAX) {
                fprintf(stderr, "arena: bad map: %s\n", line);
                return 0;
            }
            row = 0;
#ifdef APB_RULES_NEXT
        } else if (strcmp(word, "power") == 0) {
            if (power_count == APB_FIGHTERS_MAX * APB_POWERS_HELD
                || sscanf(line, "%*s %d %d %d", &powers[power_count][0], &powers[power_count][1],
                          &powers[power_count][2]) != 3) {
                fprintf(stderr, "arena: bad power: %s\n", line);
                return 0;
            }
            ++power_count;
        } else if (strcmp(word, "hazard") == 0) {
            if (sscanf(line, "%*s %d %d %d", &hazard[0], &hazard[1], &hazard[2]) != 3) {
                fprintf(stderr, "arena: bad hazard: %s\n", line);
                return 0;
            }
#endif
        } else if (fighter_count == APB_FIGHTERS_MAX) {
            fprintf(stderr, "arena: more than %d fighters\n", APB_FIGHTERS_MAX);
            return 0;
        } else if (strcmp(word, "traveler") == 0) {
            f = &fighters[fighter_count];
            if (sscanf(line, "%*s %d %d %s %15s %d %d %d", &v[0], &v[1], word, arch, &v[2], &v[3],
                       &v[4]) != 7 || !traveler(f, word, arch, v[2], v[3], v[4])) {
                fprintf(stderr, "arena: bad traveler: %s\n", line);
                return 0;
            }
            f->x = (uint8_t)v[0];
            f->y = (uint8_t)v[1];
            ++fighter_count;
        } else if (strcmp(word, "foe") == 0) {
            f = &fighters[fighter_count];
            if (sscanf(line, "%*s %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d",
                       &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8], &v[9],
                       &v[10], &v[11], &v[12], &v[13], &v[14], &v[15], &v[16], &v[17]) != 18) {
                fprintf(stderr, "arena: bad foe: %s\n", line);
                return 0;
            }
            memset(f, 0, sizeof(*f));
            f->side = APB_SIDE_FOE;
            f->x = (uint8_t)v[0]; f->y = (uint8_t)v[1];
            f->health = f->health_max = (uint8_t)v[2];
            f->grace = (uint8_t)v[3]; f->dodge = (uint8_t)v[4]; f->armor = (uint8_t)v[5];
            f->ward = (uint8_t)v[6]; f->soak = (uint8_t)v[7]; f->speed = (uint8_t)v[8];
            f->attack = (uint8_t)v[9]; f->weapon = (uint8_t)v[10]; f->ranged = (uint8_t)v[11];
            f->power = (uint8_t)v[12]; f->dmg_type = (uint8_t)v[13]; f->area = (uint8_t)v[14];
            f->weak_type = (uint8_t)v[15]; f->behavior = (uint8_t)v[16]; f->coward = (uint8_t)v[17];
#ifdef APB_RULES_NEXT
            f->race = 0xFF;
            {
                const char *hit = strstr(line, " hit ");
                const char *lv = strstr(line, " level ");
                if (hit) f->on_hit = (uint8_t)atoi(hit + 5);
                f->level = lv ? (uint8_t)atoi(lv + 7) : 1;
            }
#endif
            ++fighter_count;
        }
    }
    fclose(in);
    return map_w > 0 && fighter_count > 0;
}

int main(int argc, char **argv)
{
    unsigned fights = 1;
    unsigned seed = 1;
    unsigned rounds = 50;
    unsigned n;
    unsigned steps;
    uint8_t i;
    uint8_t who;
    uint8_t result;
    int x;
    int y;
    apb_action act;
    apb_fighter now;
    const char *path = argv[argc - 1];

    verbose = argc == 3 && strcmp(argv[1], "-v") == 0;
    if (argc < 2 || argc > 3 || !read_file(path, &fights, &seed, &rounds)) {
        fprintf(stderr, "usage: arena [-v] FILE (written by tools/arena/arena.py)\n");
        return 2;
    }
    for (n = 0; n < fights; ++n) {
        apb_rng_seed(&rng, (uint16_t)(seed + n));
        apb_battle_init((uint8_t)map_w, (uint8_t)map_h, &rng, on_event);
#ifdef APB_RULES_NEXT
        apb_battle_set_hazard((uint8_t)hazard[0], (uint8_t)hazard[1], (uint8_t)hazard[2]);
#endif
        for (y = 0; y < map_h; ++y) {
            for (x = 0; x < map_w && rows[y][x]; ++x) {
                apb_battle_set_tile((uint8_t)x, (uint8_t)y, tile_of(rows[y][x]));
            }
        }
        memset(dealt, 0, sizeof(dealt));
        memset(down_round, 0, sizeof(down_round));
        round_now = 0;
        for (i = 0; i < fighter_count; ++i) {
            if (apb_battle_add(&fighters[i]) == APB_NOBODY) {
                fprintf(stderr, "arena: fighter %u can't stand at %u,%u\n", i, fighters[i].x,
                        fighters[i].y);
                return 1;
            }
        }
#ifdef APB_RULES_NEXT
        for (i = 0; i < power_count; ++i) {
            apb_battle_learn((uint8_t)powers[i][0], (uint8_t)powers[i][1], (uint8_t)powers[i][2]);
        }
#endif
        if (verbose) printf("fight %u\n", n);
        apb_battle_start(APB_SURPRISE_NONE);
        result = APB_BATTLE_ON;
        steps = 0;
        while ((who = apb_battle_next()) != APB_NOBODY) {
            if (apb_battle_round() > rounds || ++steps > 20000u) break;
            apb_battle_quick(who, &act);
            if (!apb_battle_act(who, &act)) {        /* quick's choice refused: just end */
                act.kind = APB_ACT_DONE;
#ifdef APB_RULES_NEXT
                act.move_use = 0;
#endif
                apb_battle_fighter(who, &now);
                act.move_x = now.x;
                act.move_y = now.y;
                apb_battle_act(who, &act);
            }
        }
        result = apb_battle_result();
        printf("fight %u %s %u", n, result == APB_BATTLE_ON ? "draw" : endings[result & 3],
               apb_battle_round());
        for (i = 0; i < fighter_count; ++i) {
            apb_battle_fighter(i, &now);
            printf("  %u %u %u", now.state == APB_IN_FIGHT || now.state == APB_GONE ? now.health : 0,
                   dealt[i], down_round[i]);
        }
        printf("\n");
    }
    return 0;
}
