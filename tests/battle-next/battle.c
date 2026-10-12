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
 *   power WHO NAME RANK                  a power the fighter holds (registry/powers.txt)
 *   act X Y KIND TARGET [DX DY [USE [BLINK]]]  a traveler's turn (KIND: APB_ACT_*, 5 Shove,
 *                                        6 Dash to DX, DY, 7 power USE on TARGET or the
 *                                        square DX, DY); BLINK: power BLINK - 1 takes them
 *                                        to X, Y instead of walking
 *   act q                                a traveler's turn on quick
 *   first KIND TARGET [DX DY [USE]]      the action before the move, from where the traveler
 *                                        stands (as act's); the next act is the move, KIND 0
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
static char line[128];
static char rows[APB_MAP_H_MAX][APB_MAP_W_MAX + 2];
static int v[17];
static uint8_t ids[APB_COND_SLOTS];
static uint8_t left[APB_COND_SLOTS];

static const char *const results[] = { "fail", "cost", "success", "crit" };
static const char *const endings[] = { "on", "won", "lost", "fled" };
static const char *const types[] = { "kinetic", "energy", "fire", "cold", "mind" };

static const char *power_name(uint8_t p)
{
    if (p < apb_power_count && apb_powers[p].name) return apb_powers[p].name;
    return "?";
}

static uint8_t power_named(const char *s)
{
    uint16_t i;

    for (i = 1; i < apb_power_count; ++i) {
        if (apb_powers[i].name && strcmp(apb_powers[i].name, s) == 0) return (uint8_t)i;
    }
    return 0;
}

static const char *cond_name(uint8_t c)
{
    /* Not a ?: : cc65 won't mix a const char * and a string literal there. */
    if (c < apb_cond_count && apb_conds[c].name) return apb_conds[c].name;
    return "?";
}

static uint8_t cond_named(const char *s)
{
    uint16_t i;

    for (i = 1; i < apb_cond_count; ++i) {
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
    case APB_EV_POWER:
        printf("  %u uses %s (tier %u) at %u,%u\n", e->actor, power_name(e->cond), e->value, e->x, e->y);
        break;
    case APB_EV_HIT:
        printf("  %u's %s on %u: %u+%d=%d vs %d: %s, %u damage", e->actor, power_name(e->cond),
               e->target, e->roll.roll, e->roll.total - e->roll.roll, e->roll.total, e->roll.tn,
               results[e->roll.result], e->value);
        tags(e->target);
        printf("\n");
        break;
    case APB_EV_MEND:   printf("  %u's %s heals %u: %u\n", e->actor, power_name(e->cond), e->target, e->value); break;
    case APB_EV_FIELD:
        if (e->actor == APB_NOBODY) printf("  %u,%u is itself again\n", e->x, e->y);
        else printf("  %u,%u becomes %c (%u's field)\n", e->x, e->y, "_#O~+^=>"[e->value & 7], e->actor);
        break;
    case APB_EV_SHIFT:  printf("  %u is shifted to %u,%u\n", e->actor, e->x, e->y); break;
    case APB_EV_RANDOM:
        printf("  %u is %s: %u, %s\n", e->actor, cond_name(e->cond), e->roll.roll,
               e->value == 0 ? "loses the turn" : e->value == 1 ? "lashes out" : "acts as it chooses");
        break;
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

/* The line's words, split where they are (no sscanf: the 6502 build has no room for it). */
static char *wd[24];
static uint8_t nw;
static uint8_t len;

static void split(void)
{
    uint8_t i;

    nw = 0;
    len = (uint8_t)strlen(line);
    for (i = 0; i < len; ++i) {
        if (line[i] == ' ' || line[i] == '\t') {
            line[i] = '\0';
        } else if ((i == 0 || line[i - 1] == '\0') && nw < 24) {
            wd[nw++] = line + i;
        }
    }
}

/* The line as it was, for saying what was refused. */
static void unsplit(void)
{
    uint8_t i;

    for (i = 0; i < len; ++i) if (line[i] == '\0') line[i] = ' ';
}

static int num(uint8_t i)
{
    return i < nw ? atoi(wd[i]) : 0;
}

/* The word after `key` (hit, level), or 0. */
static const char *after(const char *key)
{
    uint8_t i;

    for (i = 1; i + 1 < nw; ++i) if (strcmp(wd[i], key) == 0) return wd[i + 1];
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
    uint8_t first;
    uint16_t seed = 1;
    const char *p;

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
        split();
        if (!nw) continue;
        if (strcmp(wd[0], "seed") == 0) {
            seed = (uint16_t)atol(wd[nw > 1 ? 1 : 0]);
            apb_rng_seed(&rng, seed);
        } else if (strcmp(wd[0], "surprise") == 0) {
            surprise = nw < 2 ? APB_SURPRISE_NONE : strcmp(wd[1], "foes") == 0 ? APB_SURPRISE_FOES
                     : strcmp(wd[1], "travelers") == 0 ? APB_SURPRISE_TRAVELERS : APB_SURPRISE_NONE;
        } else if (strcmp(wd[0], "map") == 0) {
            in_map = 1;
            h = w = 0;
        } else if (strcmp(wd[0], "hazard") == 0) {
            if (nw < 4) {
                printf("bad hazard\n");
                return 1;
            }
            apb_battle_set_hazard((uint8_t)num(1), type_named(wd[2]), cond_named(wd[3]));
        } else if (strcmp(wd[0], "traveler") == 0) {
            if (nw < 3 || apb_passport_decode(wd[1], &ch, 0) != APB_PP_OK) {
                printf("bad traveler: %s\n", nw > 1 ? wd[1] : "");
                return 1;
            }
            apb_fighter_from(&f, &ch, (uint16_t)num(2));
            if (nw > 3) f.health = (uint8_t)num(3);
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
        } else if (strcmp(wd[0], "foe") == 0) {
            if (nw < 18) {
                printf("bad foe: %s\n", nw > 1 ? wd[1] : "");
                return 1;
            }
            for (i = 0; i < 16; ++i) v[i] = num((uint8_t)(i + 2));
            memset(&f, 0, sizeof(f));
            f.side = APB_SIDE_FOE;
            f.race = 0xFF;
            f.health = f.health_max = (uint8_t)v[0];
            f.grace = (uint8_t)v[1]; f.dodge = (uint8_t)v[2]; f.armor = (uint8_t)v[3];
            f.ward = (uint8_t)v[4]; f.soak = (uint8_t)v[5]; f.speed = (uint8_t)v[6];
            f.attack = (uint8_t)v[7]; f.weapon = (uint8_t)v[8]; f.ranged = (uint8_t)v[9];
            f.power = (uint8_t)v[10]; f.dmg_type = (uint8_t)v[11]; f.area = (uint8_t)v[12];
            f.weak_type = (uint8_t)v[13]; f.behavior = (uint8_t)v[14]; f.coward = (uint8_t)v[15];
            if ((p = after("hit")) != 0) f.on_hit = cond_named(p);
            f.level = 1;
            if ((p = after("level")) != 0) f.level = (uint8_t)atoi(p);
            find(wd[1][0], 0, &f.x, &f.y);
            who = apb_battle_add(&f);
            if (who == APB_NOBODY) printf("couldn't place it\n");
            else printf("%u: foe %c at %u,%u, health %u, speed %u\n", who, wd[1][0], f.x, f.y, f.health,
                        apb_battle_speed(who));
        } else if (strcmp(wd[0], "power") == 0) {
            if (nw < 4 || !(c = power_named(wd[2]))) {
                printf("bad power: %s\n", nw > 2 ? wd[2] : "");
                return 1;
            }
            v[0] = num(1);
            v[1] = num(3);
            i = apb_battle_learn((uint8_t)v[0], c, (uint8_t)v[1]);
            if (i == APB_NOBODY) printf("can't learn %s\n", wd[2]);
            else printf("%d has %s at rank %d (tier %u, rolls %u)\n", v[0], wd[2], v[1],
                        apb_power_tier((uint8_t)v[1]), apb_battle_power_rating((uint8_t)v[0], i));
        } else if (strcmp(wd[0], "trait") == 0 || strcmp(wd[0], "put") == 0) {
            if (nw < 3 || !(c = cond_named(wd[2]))) {
                printf("bad %s: %s\n", wd[0], nw > 2 ? wd[2] : "");
                return 1;
            }
            if (wd[0][0] == 't') {
                if (!apb_battle_trait((uint8_t)num(1), c)) printf("no room for %s\n", wd[2]);
                else printf("%d has %s for good\n", num(1), wd[2]);
            } else {
                apb_battle_put((uint8_t)num(1), c);
            }
        } else if (strcmp(wd[0], "act") == 0 || strcmp(wd[0], "first") == 0) {
            if (!started) {
                apb_battle_start(surprise);
                started = 1;
            }
            who = apb_battle_next();
            if (who == APB_NOBODY) break;
            first = (uint8_t)(wd[0][0] == 'f');
            if (!first && nw == 2 && strcmp(wd[1], "q") == 0) {
                apb_battle_quick(who, &act);
                printf("  (quick: act %u %u %u %u", act.move_x, act.move_y, act.kind, act.target);
                if (act.move_use) printf(" %u %u %u %u", act.dash_x, act.dash_y, act.use, act.move_use);
                printf(")\n");
            } else {
                /* first: no move, so its numbers start at KIND */
                c = (uint8_t)(first ? 2 : 0);
                act.move_x = (uint8_t)(first ? 0 : num(1));
                act.move_y = (uint8_t)(first ? 0 : num(2));
                act.kind = (uint8_t)num((uint8_t)(3 - c));
                act.target = (uint8_t)num((uint8_t)(4 - c));
                act.dash_x = (uint8_t)num((uint8_t)(5 - c));
                act.dash_y = (uint8_t)num((uint8_t)(6 - c));
                act.use = (uint8_t)num((uint8_t)(7 - c));
                act.move_use = (uint8_t)(first ? 0 : num(8));
            }
            if (!(first ? apb_battle_act_first(who, &act) : apb_battle_act(who, &act))) {
                unsplit();
                printf("  (not allowed: %s)\n", line);
            }
        }
    }
    fclose(in);
    if (!started) apb_battle_start(surprise);
    if (apb_battle_next() != APB_NOBODY) printf("out of actions\n");
    return 0;
}
