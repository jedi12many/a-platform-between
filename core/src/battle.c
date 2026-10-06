#include <string.h>

#include "apb_battle.h"

/*
 * The battle: docs/combat.md. Everything is decided by the order of play, the actions
 * taken and the dice, so a battle replays exactly from its actions.
 *
 * One battle at a time, kept as one array per field rather than an array of structs:
 * on the 6502, f_x[i] is a single indexed load, where b->f[i].x needs a multiply.
 */

/* --------------------------------------------------------------- state */

static uint8_t map_w;
static uint8_t map_h;
static uint8_t tiles[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t count;
static uint8_t order[APB_FIGHTERS_MAX];
static uint8_t round_no;
static uint8_t next;        /* index into order                              */
static uint8_t begun;       /* the traveler at `next` has started their turn */
static uint8_t surprise;
static uint8_t result;
static apb_rng *dice;
static void (*report)(const apb_event *ev);

/* Every field of every fighter: one row per field of apb_fighter, in the same order
 * (all bytes), so a fighter goes in and out with one loop. */
#define FIELDS 25
static uint8_t fd[FIELDS][APB_FIGHTERS_MAX];
/* Fails to compile if apb_fighter ever stops being FIELDS bytes. cc65 can't evaluate this,
 * but the struct is the same everywhere, so the native build checks it for both. */
#ifndef __CC65__
typedef char apb_fighter_is_bytes[sizeof(apb_fighter) == FIELDS ? 1 : -1];
#endif
#define f_side        fd[0]
#define f_state       fd[1]
#define f_x           fd[2]
#define f_y           fd[3]
#define f_health      fd[4]
#define f_health_max  fd[5]
#define f_grace       fd[6]
#define f_dodge       fd[7]
#define f_armor       fd[8]
#define f_ward        fd[9]
#define f_soak        fd[10]
#define f_speed       fd[11]
#define f_attack      fd[12]
#define f_athletics   fd[13]
#define f_weapon      fd[14]
#define f_stat_bonus  fd[15]
#define f_ranged      fd[16]
#define f_power       fd[17]
#define f_dmg_type    fd[18]
#define f_area        fd[19]
#define f_weak_type   fd[20]
#define f_behavior    fd[21]
#define f_coward      fd[22]
#define f_defending   fd[23]
#define f_opened      fd[24]

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static uint8_t cost_to[APB_MAP_H_MAX][APB_MAP_W_MAX];   /* movement used to get there */
static apb_event ev;
static apb_roll shot;

static const int8_t step_x[8] = { -1, 0, 1, -1, 1, -1, 0, 1 };
static const int8_t step_y[8] = { -1, -1, -1, 0, 0, 1, 1, 1 };

static uint8_t dist(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1)
{
    uint8_t dx = (uint8_t)(x0 > x1 ? x0 - x1 : x1 - x0);
    uint8_t dy = (uint8_t)(y0 > y1 ? y0 - y1 : y1 - y0);

    return dx > dy ? dx : dy;
}

static uint8_t dist_to(uint8_t a, uint8_t b)
{
    return dist(f_x[a], f_y[a], f_x[b], f_y[b]);
}

static void emit(uint8_t kind, uint8_t actor, uint8_t target, uint16_t value)
{
    ev.kind = kind;
    ev.actor = actor;
    ev.target = target;
    ev.value = value;
    if (actor != APB_NOBODY) {
        ev.x = f_x[actor];
        ev.y = f_y[actor];
    }
    if (report) report(&ev);
}

static uint8_t who_is_at(uint8_t x, uint8_t y)
{
    uint8_t i;

    for (i = 0; i < count; ++i) {
        if (f_state[i] == APB_IN_FIGHT && f_x[i] == x && f_y[i] == y) return i;
    }
    return APB_NOBODY;
}

/* ------------------------------------------------------------- setting up */

void apb_battle_init(uint8_t w, uint8_t h, apb_rng *rng, void (*on_event)(const apb_event *e))
{
    memset(tiles, 0, sizeof(tiles));
    map_w = (uint8_t)(w > APB_MAP_W_MAX ? APB_MAP_W_MAX : w);
    map_h = (uint8_t)(h > APB_MAP_H_MAX ? APB_MAP_H_MAX : h);
    count = 0;
    round_no = next = begun = surprise = 0;
    result = APB_BATTLE_ON;
    dice = rng;
    report = on_event;
}

void apb_battle_set_tile(uint8_t x, uint8_t y, uint8_t tile)
{
    if (x < map_w && y < map_h) tiles[y][x] = tile;
}

uint8_t apb_battle_tile(uint8_t x, uint8_t y)
{
    return (x < map_w && y < map_h) ? tiles[y][x] : APB_TILE_WALL;
}

uint8_t apb_battle_width(void) { return map_w; }
uint8_t apb_battle_height(void) { return map_h; }
uint8_t apb_battle_count(void) { return count; }
uint8_t apb_battle_round(void) { return round_no; }
uint8_t apb_battle_result(void) { return result; }

uint8_t apb_battle_add(const apb_fighter *f)
{
    uint8_t i = count;
    uint8_t k;

    if (count >= APB_FIGHTERS_MAX || f->x >= map_w || f->y >= map_h
        || apb_tile_cost(tiles[f->y][f->x]) == 0 || who_is_at(f->x, f->y) != APB_NOBODY) {
        return APB_NOBODY;
    }
    for (k = 0; k < FIELDS; ++k) fd[k][i] = ((const uint8_t *)f)[k];
    f_state[i] = APB_IN_FIGHT;
    if (f_health[i] > f_health_max[i]) f_health[i] = f_health_max[i];
    return count++;
}

void apb_battle_fighter(uint8_t i, apb_fighter *out)
{
    uint8_t k;

    memset(out, 0, sizeof(*out));
    if (i >= count) return;
    for (k = 0; k < FIELDS; ++k) ((uint8_t *)out)[k] = fd[k][i];
}

void apb_fighter_from(apb_fighter *out, const apb_character *ch, uint16_t weapon_item)
{
    uint8_t arch = APB_ARCH_MELEE;

    memset(out, 0, sizeof(*out));
    if (weapon_item != 0 && weapon_item < APB_ITEM_COUNT && apb_items[weapon_item].tier) {
        arch = apb_items[weapon_item].archetype;
        out->dmg_type = apb_items[weapon_item].damage;
    }
    out->side = APB_SIDE_TRAVELER;
    out->health_max = apb_health_max(ch);
    out->health = out->health_max;
    out->grace = ch->stat[APB_GRACE];
    out->dodge = apb_dodge(ch);
    out->armor = apb_armor(ch);
    out->speed = apb_speed(ch);
    out->athletics = apb_skill(ch, APB_SK_ATHLETICS);
    out->weapon = apb_weapon_damage(weapon_item);
    out->weak_type = 0xFF;
    if (arch == APB_ARCH_RANGED) {
        out->ranged = 1;
        out->attack = apb_skill(ch, APB_SK_RANGED);
    } else if (arch == APB_ARCH_FOCUS) {
        out->ranged = 1;
        out->power = 1;
        out->attack = apb_skill(ch, APB_SK_CHANNEL);
    } else {
        out->attack = apb_skill(ch, APB_SK_MELEE);
        out->stat_bonus = apb_melee_bonus(ch);
    }
}

void apb_battle_start(uint8_t first)
{
    uint8_t i;
    uint8_t j;
    uint8_t p;
    uint8_t q;

    /* Highest Grace first; travelers before foes on a tie; then the order they joined. */
    for (i = 0; i < count; ++i) order[i] = i;
    for (i = 1; i < count; ++i) {
        for (j = i; j > 0; --j) {
            p = order[j - 1];
            q = order[j];
            if (f_grace[q] > f_grace[p] || (f_grace[q] == f_grace[p] && f_side[q] < f_side[p])) {
                order[j] = p;
                order[j - 1] = q;
            } else {
                break;
            }
        }
    }
    surprise = first;
    round_no = first == APB_SURPRISE_NONE ? 1 : 0;
    next = 0;
    begun = 0;
    result = APB_BATTLE_ON;
}

/* ------------------------------------------------------------- the board */

/* Movement: the least it costs to reach every square, up to the fighter's speed. You
 * can't move through other fighters or into walls and pits. */
static void reach(uint8_t who)
{
    uint8_t x;
    uint8_t y;
    uint8_t d;
    uint8_t c;
    uint8_t nx;
    uint8_t ny;
    uint8_t changed = 1;
    uint8_t speed = f_speed[who];

    memset(cost_to, 0xFF, sizeof(cost_to));
    cost_to[f_y[who]][f_x[who]] = 0;
    while (changed) {
        changed = 0;
        for (y = 0; y < map_h; ++y) {
            for (x = 0; x < map_w; ++x) {
                if (cost_to[y][x] == 0xFF) continue;
                for (d = 0; d < 8; ++d) {
                    nx = (uint8_t)(x + step_x[d]);
                    ny = (uint8_t)(y + step_y[d]);
                    if (nx >= map_w || ny >= map_h) continue;
                    c = apb_tile_cost(tiles[ny][nx]);
                    if (c == 0 || who_is_at(nx, ny) != APB_NOBODY) continue;
                    c = (uint8_t)(cost_to[y][x] + c);
                    if (c <= speed && c < cost_to[ny][nx]) {
                        cost_to[ny][nx] = c;
                        changed = 1;
                    }
                }
            }
        }
    }
}

uint8_t apb_battle_can_reach(uint8_t who, uint8_t x, uint8_t y)
{
    if (who >= count || x >= map_w || y >= map_h) return 0;
    reach(who);
    return (uint8_t)(cost_to[y][x] != 0xFF);
}

/* Can a shot from x0,y0 reach x1,y1? Walls block it; so does anyone standing in
 * between (but not the shooter or the target). */
static uint8_t in_sight(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1, uint8_t shooter)
{
    int16_t dx = (int16_t)(x1 > x0 ? x1 - x0 : x0 - x1);
    int16_t dy = (int16_t)(y1 > y0 ? y1 - y0 : y0 - y1);
    int8_t sx = (int8_t)(x0 < x1 ? 1 : -1);
    int8_t sy = (int8_t)(y0 < y1 ? 1 : -1);
    int16_t err = (int16_t)(dx - dy);
    int16_t e2;
    uint8_t x = x0;
    uint8_t y = y0;
    uint8_t who;

    for (;;) {
        if (x == x1 && y == y1) return 1;
        if (!(x == x0 && y == y0)) {
            if (apb_tile_blocks_sight(tiles[y][x])) return 0;
            who = who_is_at(x, y);
            if (who != APB_NOBODY && who != shooter) return 0;
        }
        e2 = (int16_t)(2 * err);
        if (e2 > -dy) { err = (int16_t)(err - dy); x = (uint8_t)(x + sx); }
        if (e2 < dx) { err = (int16_t)(err + dx); y = (uint8_t)(y + sy); }
    }
}

uint8_t apb_battle_can_attack(uint8_t who, uint8_t target, uint8_t from_x, uint8_t from_y)
{
    uint8_t d;

    if (who >= count || target >= count || who == target) return 0;
    if (f_state[target] != APB_IN_FIGHT) return 0;
    d = dist(from_x, from_y, f_x[target], f_y[target]);
    if (f_area[who] && d <= f_area[who]) return 0;   /* the blast would catch you */
    if (!f_ranged[who]) return (uint8_t)(d == 1);
    return in_sight(from_x, from_y, f_x[target], f_y[target], who);
}

int16_t apb_battle_tn(uint8_t a, uint8_t t)
{
    int16_t defense = f_power[a] ? f_ward[t] : (f_dmg_type[a] == f_weak_type[t] ? 0 : f_armor[t]);
    int16_t bonus = 0;

    if (f_defending[t]) bonus = (int16_t)(bonus + APB_DEFEND_BONUS);
    if (f_ranged[a] && tiles[f_y[t]][f_x[t]] == APB_TILE_COVER) {
        bonus = (int16_t)(bonus + APB_COVER_BONUS);
    }
    return apb_hit_tn(f_dodge[t], defense, bonus, 0);
}

/* ------------------------------------------------------------- outcomes */

static void check_end(void)
{
    uint8_t i;
    uint8_t travelers = 0;
    uint8_t foes = 0;
    uint8_t fled = 0;

    if (result != APB_BATTLE_ON) return;
    for (i = 0; i < count; ++i) {
        if (f_state[i] == APB_IN_FIGHT) {
            if (f_side[i] == APB_SIDE_FOE) ++foes; else ++travelers;
        } else if (f_state[i] == APB_GONE && f_side[i] == APB_SIDE_TRAVELER) {
            ++fled;
        }
    }
    if (foes == 0 && travelers > 0) result = APB_BATTLE_WON;
    else if (travelers == 0) result = fled ? APB_BATTLE_FLED : APB_BATTLE_LOST;
    if (result != APB_BATTLE_ON) emit(APB_EV_END, APB_NOBODY, APB_NOBODY, result);
}

static void hurt(uint8_t who, uint16_t dmg)
{
    f_health[who] = (uint8_t)(dmg >= f_health[who] ? 0 : f_health[who] - dmg);
    if (f_health[who] == 0) {
        f_state[who] = APB_DOWN;
        emit(APB_EV_DOWN, APB_NOBODY, who, 0);
    } else if (f_coward[who] && 4u * f_health[who] <= f_health_max[who]) {
        f_state[who] = APB_GONE;            /* runs off */
        emit(APB_EV_GONE, who, APB_NOBODY, 0);
    }
}

/* One roll; for an area attack, compared with the TN of everyone in the blast. */
static void attack(uint8_t who, uint8_t target)
{
    int16_t bonus = 0;
    uint8_t i;
    uint8_t cx = f_x[target];
    uint8_t cy = f_y[target];
    uint8_t roll;
    uint16_t dmg;

    if (tiles[f_y[who]][f_x[who]] == APB_TILE_HIGH && tiles[cy][cx] != APB_TILE_HIGH) {
        bonus = APB_HIGH_GROUND_BONUS;
    }
    if (f_side[who] == APB_SIDE_TRAVELER && f_opened[target]) {
        bonus = (int16_t)(bonus + APB_HELP_BONUS);
        f_opened[target] = 0;
    }
    roll = apb_d100(dice);
    for (i = 0; i < count; ++i) {
        if (f_state[i] != APB_IN_FIGHT) continue;
        if (f_area[who] ? !apb_in_area((int8_t)(f_x[i] - cx), (int8_t)(f_y[i] - cy), f_area[who])
                        : i != target) {
            continue;
        }
        shot.roll = roll;
        shot.total = (int16_t)(roll + f_attack[who] + bonus);
        shot.tn = apb_battle_tn(who, i);
        shot.result = apb_resolve(roll, shot.total, shot.tn);
        dmg = apb_damage(&shot, f_weapon[who], f_ranged[who] ? 0 : f_stat_bonus[who], f_soak[i]);
        ev.roll = shot;
        emit(APB_EV_ATTACK, who, i, dmg);
        if (dmg) hurt(i, dmg);
    }
}

static void ground_hurts(uint8_t who)
{
    if (tiles[f_y[who]][f_x[who]] == APB_TILE_HAZARD && APB_HAZARD_DAMAGE > f_soak[who]) {
        emit(APB_EV_HAZARD, who, APB_NOBODY, (uint16_t)(APB_HAZARD_DAMAGE - f_soak[who]));
        hurt(who, (uint16_t)(APB_HAZARD_DAMAGE - f_soak[who]));
    }
}

static void move_to(uint8_t who, uint8_t x, uint8_t y)
{
    if (f_x[who] == x && f_y[who] == y) return;
    f_x[who] = x;
    f_y[who] = y;
    emit(APB_EV_MOVE, who, APB_NOBODY, 0);
    ground_hurts(who);
}

static uint8_t foes_next_to(uint8_t who)
{
    uint8_t i;
    uint8_t n = 0;

    for (i = 0; i < count; ++i) {
        if (f_state[i] == APB_IN_FIGHT && f_side[i] != f_side[who] && dist_to(i, who) == 1) ++n;
    }
    return n;
}

static void flee(uint8_t who)
{
    uint8_t i;

    if (tiles[f_y[who]][f_x[who]] == APB_TILE_EXIT) {
        shot.roll = 0;
        shot.result = APB_SUCCESS;
    } else {
        apb_check(dice, f_athletics[who], 0, apb_flee_tn(foes_next_to(who)), &shot);
    }
    ev.roll = shot;
    emit(APB_EV_FLEE, who, APB_NOBODY, shot.result);
    if (shot.result == APB_COST) {
        /* Out, but every foe next to you gets a free attack on the way. */
        for (i = 0; i < count && f_state[who] == APB_IN_FIGHT; ++i) {
            if (f_state[i] == APB_IN_FIGHT && f_side[i] != f_side[who] && !f_ranged[i]
                && dist_to(i, who) == 1) {
                attack(i, who);
            }
        }
    }
    if (shot.result != APB_FAIL && f_state[who] == APB_IN_FIGHT) {
        f_state[who] = APB_GONE;
        emit(APB_EV_GONE, who, APB_NOBODY, 0);
    }
}

/* ------------------------------------------------------------- the foes */

/* The nearest traveler (that it can attack from x, y, if `attackable`), or APB_NOBODY. */
static uint8_t nearest(uint8_t who, uint8_t x, uint8_t y, uint8_t attackable)
{
    uint8_t i;
    uint8_t best = APB_NOBODY;
    uint8_t best_d = 0xFF;
    uint8_t d;

    for (i = 0; i < count; ++i) {
        if (f_state[i] != APB_IN_FIGHT || f_side[i] != APB_SIDE_TRAVELER) continue;
        if (attackable && !apb_battle_can_attack(who, i, x, y)) continue;
        d = dist(x, y, f_x[i], f_y[i]);
        if (d < best_d) {
            best_d = d;
            best = i;
        }
    }
    return best;
}

/* A shooter moves only as far as it must to get a shot: the cheapest square it can
 * reach and fire from (top-left first on a tie). Returns 0 if there's none. */
static uint8_t find_shot(uint8_t who)
{
    uint8_t x;
    uint8_t y;
    uint8_t bx = 0;
    uint8_t by = 0;
    uint8_t best = 0xFF;

    reach(who);
    for (y = 0; y < map_h; ++y) {
        for (x = 0; x < map_w; ++x) {
            if (cost_to[y][x] < best && nearest(who, x, y, 1) != APB_NOBODY) {
                best = cost_to[y][x];
                bx = x;
                by = y;
            }
        }
    }
    if (best == 0xFF) return 0;
    move_to(who, bx, by);
    return 1;
}

static void foe_turn(uint8_t who)
{
    uint8_t target = nearest(who, f_x[who], f_y[who], 1);
    uint8_t x;
    uint8_t y;
    uint8_t bx = f_x[who];
    uint8_t by = f_y[who];
    uint8_t goal;
    uint8_t d;
    uint8_t best_d;

    if (target == APB_NOBODY && f_behavior[who] == APB_AI_SHOOT && f_ranged[who]
        && find_shot(who)) {
        if (f_state[who] != APB_IN_FIGHT) return;
        target = nearest(who, f_x[who], f_y[who], 1);
    }
    if (target == APB_NOBODY && f_behavior[who] != APB_AI_GUARD) {
        /* Close in: the reachable square nearest the nearest traveler (cheapest to get
         * to on a tie, then top-left first). */
        goal = nearest(who, f_x[who], f_y[who], 0);
        if (goal == APB_NOBODY) return;
        reach(who);
        best_d = dist_to(who, goal);
        for (y = 0; y < map_h; ++y) {
            for (x = 0; x < map_w; ++x) {
                if (cost_to[y][x] == 0xFF) continue;
                d = dist(x, y, f_x[goal], f_y[goal]);
                if (d < best_d || (d == best_d && cost_to[y][x] < cost_to[by][bx])) {
                    best_d = d;
                    bx = x;
                    by = y;
                }
            }
        }
        move_to(who, bx, by);
        if (f_state[who] != APB_IN_FIGHT) return;
        target = nearest(who, f_x[who], f_y[who], 1);
    }
    if (target != APB_NOBODY) attack(who, target);
}

/* ------------------------------------------------------------- turns */

/* The fighter whose turn it is at order position `next`, or APB_NOBODY if they sit this
 * one out (out of the fight, or it's the other side's surprise round). */
static uint8_t turn_of(void)
{
    uint8_t who = order[next];

    if (f_state[who] != APB_IN_FIGHT) return APB_NOBODY;
    if (round_no == 0 && ((surprise == APB_SURPRISE_FOES) != (f_side[who] == APB_SIDE_FOE))) {
        return APB_NOBODY;
    }
    return who;
}

static void advance(void)
{
    begun = 0;
    if (++next >= count) {
        next = 0;
        if (round_no < 255) ++round_no;
    }
}

/* Start of a fighter's turn: defending ends, and the ground may hurt. */
static void begin_turn(uint8_t who)
{
    f_defending[who] = 0;
    emit(APB_EV_TURN, who, APB_NOBODY, round_no);
    ground_hurts(who);
}

uint8_t apb_battle_next(void)
{
    uint8_t who;
    uint8_t guard;

    /* Bounded: a round can't have more turns than fighters. */
    for (guard = 0; guard < 255; ++guard) {
        check_end();
        if (result != APB_BATTLE_ON) return APB_NOBODY;
        who = turn_of();
        if (who == APB_NOBODY) {
            advance();
            continue;
        }
        if (f_side[who] == APB_SIDE_TRAVELER) {
            /* A refused action leaves it their turn; don't start it twice. */
            if (!begun) {
                begin_turn(who);
                begun = 1;
            }
            if (f_state[who] == APB_IN_FIGHT) return who;
            advance();
            continue;
        }
        begin_turn(who);
        if (f_state[who] == APB_IN_FIGHT) foe_turn(who);
        advance();
    }
    return APB_NOBODY;
}

uint8_t apb_battle_act(uint8_t who, const apb_action *a)
{
    uint8_t ok = 1;
    uint8_t t = a->target;

    if (result != APB_BATTLE_ON || who >= count || order[next] != who) return 0;
    if (a->move_x != f_x[who] || a->move_y != f_y[who]) {
        if (!apb_battle_can_reach(who, a->move_x, a->move_y)) return 0;
    }
    switch (a->kind) {
    case APB_ACT_ATTACK:
        ok = apb_battle_can_attack(who, t, a->move_x, a->move_y);
        break;
    case APB_ACT_HELP:
        ok = (uint8_t)(t < count && f_state[t] == APB_IN_FIGHT && f_side[t] != f_side[who]
                       && dist(a->move_x, a->move_y, f_x[t], f_y[t]) == 1);
        break;
    case APB_ACT_DEFEND:
    case APB_ACT_FLEE:
    case APB_ACT_WAIT:
        break;
    default:
        ok = 0;
    }
    if (!ok) return 0;

    move_to(who, a->move_x, a->move_y);
    if (f_state[who] == APB_IN_FIGHT) {
        if (a->kind == APB_ACT_ATTACK) {
            attack(who, t);
        } else if (a->kind == APB_ACT_DEFEND) {
            f_defending[who] = 1;
            emit(APB_EV_DEFEND, who, APB_NOBODY, 0);
        } else if (a->kind == APB_ACT_HELP) {
            f_opened[t] = 1;
            emit(APB_EV_HELP, who, t, 0);
        } else if (a->kind == APB_ACT_FLEE) {
            flee(who);
        }
    }
    advance();
    check_end();
    return 1;
}
