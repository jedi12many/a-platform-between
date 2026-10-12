#include <string.h>

#include "apb_battle.h"

/*
 * The battle, rules v1 (the rules lab): docs/turn.md for the turn, docs/combat.md for the
 * rest. Everything is decided by the order of play, the actions taken and the dice, so a
 * battle replays exactly from its actions.
 *
 * It began as core/src/battle.c (rules v0) and keeps its shape: one battle at a time, one
 * array per field (on the 6502, f_x[i] is a single indexed load). What v1 adds: Speed from
 * conditions, paths that hazards hit step by step, flying, Shove and Dash, pushes and
 * falls, and conditions: put on, ticking, counted down, shaken off.
 */

/* --------------------------------------------------------------- state */

static uint8_t map_w;
static uint8_t map_h;
static uint8_t tiles[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t count;
static uint8_t base[APB_FIGHTERS_MAX];    /* the order of play                   */
static uint8_t order[APB_FIGHTERS_MAX];   /* this round's: Wait moves you back   */
static uint8_t round_no;
static uint8_t next;
static uint8_t begun;
static uint8_t acted_first;     /* the traveler whose turn it is acted before moving */
static uint8_t acting_first;    /* ... and is doing it now (apb_battle_act_first) */
static uint8_t surprise;
static uint8_t result;
static apb_rng *dice;
static uint8_t map_hz[3];          /* the map's hazards: damage, type, condition */
static void (*report)(const apb_event *ev);


#define FIELDS 29
static uint8_t fd[FIELDS][APB_FIGHTERS_MAX];
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
#define f_guarding    fd[23]
#define f_waited      fd[24]
#define f_on_hit      fd[26]
#define f_power_stat  fd[27]
#define f_level       fd[28]

/* Conditions: slots 0-1 for good, 2-5 the others. */
static uint8_t c_id[APB_FIGHTERS_MAX][APB_COND_SLOTS];
static uint8_t c_left[APB_FIGHTERS_MAX][APB_COND_SLOTS];   /* rounds left; 0: no countdown */
static uint8_t c_fresh[APB_FIGHTERS_MAX][APB_COND_SLOTS];  /* put on this turn            */
static uint8_t c_tier[APB_FIGHTERS_MAX][APB_COND_SLOTS];   /* a tiered one's tier         */
static uint8_t c_barrier[APB_FIGHTERS_MAX];                /* a barrier's damage left     */
static uint8_t c_from[APB_FIGHTERS_MAX][APB_COND_SLOTS];   /* the level of who put it on  */
static uint8_t putter = APB_NOBODY;    /* who's putting conditions on now (none: a hazard) */

/* Powers: what each fighter holds in this fight. */
static uint8_t p_id[APB_FIGHTERS_MAX][APB_POWERS_HELD];
static uint8_t p_rank[APB_FIGHTERS_MAX][APB_POWERS_HELD];
static uint8_t p_left[APB_FIGHTERS_MAX][APB_POWERS_HELD];  /* charges; 0xFF: at will      */

/* The ground, square by square: what a hazard does there (the map's, or a field's), and a
 * field's: whose, its rounds left, and what the square was before it. */
static uint8_t sq_dmg[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t sq_type[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t sq_cond[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t fl_owner[APB_MAP_H_MAX][APB_MAP_W_MAX];     /* APB_NOBODY: no field       */
static uint8_t fl_left[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t fl_was[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t fl_fresh[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t move_left[APB_FIGHTERS_MAX];                /* this turn's move            */
static uint8_t acting = APB_NOBODY;                         /* whose turn is under way     */

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static uint8_t cost_to[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t hz_to[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t came[APB_MAP_H_MAX][APB_MAP_W_MAX];         /* the step that got there     */
static uint8_t path_x[24];
static uint8_t path_y[24];
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

static void emit_c(uint8_t kind, uint8_t actor, uint8_t target, uint16_t value, uint8_t cond)
{
    ev.kind = kind;
    ev.actor = actor;
    ev.target = target;
    ev.value = value;
    ev.cond = cond;
    if (actor != APB_NOBODY) {
        ev.x = f_x[actor];
        ev.y = f_y[actor];
    }
    if (report) report(&ev);
}

static void emit(uint8_t kind, uint8_t actor, uint8_t target, uint16_t value)
{
    emit_c(kind, actor, target, value, 0);
}

static uint8_t who_is_at(uint8_t x, uint8_t y)
{
    uint8_t i;

    for (i = 0; i < count; ++i) {
        if (f_state[i] == APB_IN_FIGHT && f_x[i] == x && f_y[i] == y) return i;
    }
    return APB_NOBODY;
}

/* ------------------------------------------------------- conditions: reading */

static uint8_t has_flag(uint8_t who, uint16_t flag)
{
    uint8_t k;

    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (c_id[who][k] && (apb_conds[c_id[who][k]].flags & flag)) return 1;
    }
    return 0;
}

static uint8_t has(uint8_t who, uint8_t cond)
{
    uint8_t k;

    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (c_id[who][k] == cond) return 1;
    }
    return 0;
}

/* The sum of one of a fighter's signed effects (0 speed, 1 dodge, ... 9 shake: the order
 * of apb_cond_def's int8_t fields). */
static int16_t sum(uint8_t who, uint8_t what)
{
    uint8_t k;
    int16_t s = 0;
    const apb_cond_def *d;

    int16_t v;
    int16_t times;

    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (!c_id[who][k]) continue;
        d = &apb_conds[c_id[who][k]];
        times = (int16_t)((d->flags & APB_CF_TIERED) ? c_tier[who][k] : 1);
        switch (what) {
        case 1: v = d->dodge; break;
        case 2: v = d->armor; break;
        case 3: v = d->ward; break;
        case 4: v = d->soak; break;
        case 5: v = d->rolls; break;
        case 6: v = d->attacks; break;
        case 7: v = d->melee; break;
        case 8: v = d->next; break;
        case 9: v = d->shake; break;
        default: v = 0;
        }
        s = (int16_t)(s + v * times);
    }
    return s;
}

static uint8_t floor0(int16_t v)
{
    return (uint8_t)(v < 0 ? 0 : v > 255 ? 255 : v);
}

uint8_t apb_battle_speed(uint8_t who)
{
    uint8_t k;
    int8_t worst = 0;
    int8_t best = 0;
    int8_t s;

    if (who >= count) return 0;
    if (has_flag(who, APB_CF_SPEED0)) return 0;
    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (!c_id[who][k]) continue;
        s = apb_conds[c_id[who][k]].speed;
        if (s < worst) worst = s;
        if (s > best) best = s;
    }
    return floor0((int16_t)(f_speed[who] + worst + best));
}

uint8_t apb_battle_move_left(uint8_t who) { return who < count ? move_left[who] : 0; }

uint8_t apb_battle_dodge(uint8_t who)
{
    if (who >= count || has_flag(who, APB_CF_DODGE0)) return 0;
    return floor0((int16_t)(f_dodge[who] + sum(who, 1)));
}

uint8_t apb_battle_armor(uint8_t who) { return who < count ? floor0((int16_t)(f_armor[who] + sum(who, 2))) : 0; }
uint8_t apb_battle_ward(uint8_t who) { return who < count ? floor0((int16_t)(f_ward[who] + sum(who, 3))) : 0; }
uint8_t apb_battle_soak(uint8_t who) { return who < count ? floor0((int16_t)(f_soak[who] + sum(who, 4))) : 0; }

static uint8_t flying(uint8_t who) { return has_flag(who, APB_CF_FLY); }

static uint8_t immune_to(uint8_t who, uint8_t cond)
{
    uint8_t k;
    uint8_t j;

    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (!c_id[who][k]) continue;
        for (j = 0; j < 4; ++j) {
            if (apb_conds[c_id[who][k]].immune[j] == cond) return 1;
        }
    }
    return 0;
}

uint8_t apb_battle_conditions(uint8_t who, uint8_t *ids, uint8_t *rounds)
{
    uint8_t k;
    uint8_t n = 0;

    if (who >= count) return 0;
    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (!c_id[who][k]) continue;
        ids[n] = c_id[who][k];
        rounds[n] = c_left[who][k];
        ++n;
    }
    return n;
}

/* ------------------------------------------------------ conditions: changing */

static void fall_if_over_pit(uint8_t who);
static void put_on(uint8_t who, uint8_t cond);
static void put_on_tier(uint8_t who, uint8_t cond, uint8_t tier);

static void take_off(uint8_t who, uint8_t k)
{
    uint8_t cond = c_id[who][k];

    if (!cond) return;
    c_id[who][k] = 0;
    c_left[who][k] = 0;
    c_fresh[who][k] = 0;
    if (apb_conds[cond].barrier) c_barrier[who] = 0;
    emit_c(APB_EV_COND_OFF, who, APB_NOBODY, 0, cond);
    if ((apb_conds[cond].flags & APB_CF_FLY) && f_state[who] == APB_IN_FIGHT) fall_if_over_pit(who);
}

static void take_off_cond(uint8_t who, uint8_t cond)
{
    uint8_t k;

    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (c_id[who][k] == cond) take_off(who, k);
    }
}

/* Its effects ended by something (hit, healed): every condition with that flag goes. */
static void take_off_flag(uint8_t who, uint16_t flag)
{
    uint8_t k;

    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (c_id[who][k] && (apb_conds[c_id[who][k]].flags & flag)) take_off(who, k);
    }
}

/* The level gap (docs/turn.md, Levels and gear): twice the levels a is above b (below:
 * negative). Every roll's TN against a fighter is that much lower for the roller; a
 * hazard's or a scenario's condition is level 0's. */
static uint8_t level_of(uint8_t who)
{
    return (uint8_t)(who < count ? (f_level[who] > 100 ? 100 : f_level[who]) : 0);
}

static int16_t gap(uint8_t a, uint8_t b)
{
    return (int16_t)(2 * ((int16_t)level_of(a) - (int16_t)level_of(b)));
}

static void put_on(uint8_t who, uint8_t cond)
{
    put_on_tier(who, cond, 1);
}

/* A condition at a power's or an item's tier (docs/turn.md): a tiered one's numbers are
 * that many times its tier-1 numbers. The same one again: the longer time, the higher
 * tier. */
static void put_on_tier(uint8_t who, uint8_t cond, uint8_t tier)
{
    uint8_t k;
    uint8_t slot = APB_NOBODY;
    uint8_t least = 0xFF;
    uint8_t left;
    const apb_cond_def *d;

    if (who >= count || f_state[who] != APB_IN_FIGHT || !cond || cond >= apb_cond_count) return;
    d = &apb_conds[cond];
    if (!(d->flags & APB_CF_DEFINED)) return;
    if (immune_to(who, cond)) {
        emit_c(APB_EV_IMMUNE, who, APB_NOBODY, 0, cond);
        return;
    }
    if (d->opposite) take_off_cond(who, d->opposite);
    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (c_id[who][k] == cond) {
            /* The same one again: the longer time counts. */
            if (c_left[who][k] && d->rounds > c_left[who][k]) c_left[who][k] = d->rounds;
            if (tier > c_tier[who][k]) c_tier[who][k] = tier;
            if (level_of(putter) > c_from[who][k]) c_from[who][k] = level_of(putter);
            if (d->barrier) c_barrier[who] = (uint8_t)(d->barrier * c_tier[who][k]);
            return;
        }
    }
    for (k = 2; k < APB_COND_SLOTS; ++k) {
        if (!c_id[who][k]) { slot = k; break; }
    }
    if (slot == APB_NOBODY) {
        /* A fifth: it replaces the one with the fewest rounds left. */
        for (k = 2; k < APB_COND_SLOTS; ++k) {
            left = c_left[who][k] ? c_left[who][k] : 0xFE;
            if (left < least) { least = left; slot = k; }
        }
        if (slot == APB_NOBODY) slot = 2;
        take_off(who, slot);
    }
    c_id[who][slot] = cond;
    c_left[who][slot] = d->rounds;
    c_tier[who][slot] = (uint8_t)((d->flags & APB_CF_TIERED) ? tier : 1);
    c_from[who][slot] = level_of(putter);
    c_fresh[who][slot] = (uint8_t)(who == acting);     /* not counted the turn it went on */
    if (d->barrier) c_barrier[who] = (uint8_t)(d->barrier * c_tier[who][slot]);
    emit_c(APB_EV_COND_ON, who, APB_NOBODY, d->rounds, cond);
}

uint8_t apb_battle_put(uint8_t who, uint8_t cond)
{
    if (who >= count) return 0;
    putter = APB_NOBODY;
    put_on(who, cond);
    return has(who, cond);
}

uint8_t apb_battle_put_tier(uint8_t who, uint8_t cond, uint8_t tier)
{
    if (who >= count) return 0;
    putter = APB_NOBODY;
    put_on_tier(who, cond, tier);
    return has(who, cond);
}

uint8_t apb_battle_trait(uint8_t who, uint8_t cond)
{
    uint8_t k;

    if (who >= count || !cond || cond >= apb_cond_count || !(apb_conds[cond].flags & APB_CF_DEFINED)) return 0;
    for (k = 0; k < 2; ++k) {
        if (c_id[who][k] == cond) return 1;
        if (!c_id[who][k]) {
            c_id[who][k] = cond;
            c_left[who][k] = 0;
            c_tier[who][k] = 1;
            return 1;
        }
    }
    return 0;
}

/* ------------------------------------------------------------- setting up */

void apb_battle_init(uint8_t w, uint8_t h, apb_rng *rng, void (*on_event)(const apb_event *e))
{
    memset(tiles, 0, sizeof(tiles));
    memset(c_id, 0, sizeof(c_id));
    memset(c_left, 0, sizeof(c_left));
    memset(c_fresh, 0, sizeof(c_fresh));
    memset(c_barrier, 0, sizeof(c_barrier));
    memset(c_tier, 1, sizeof(c_tier));
    memset(move_left, 0, sizeof(move_left));
    memset(p_id, 0, sizeof(p_id));
    map_hz[0] = APB_HAZARD_DAMAGE;
    map_hz[1] = APB_DMG_KINETIC;
    map_hz[2] = 0;
    memset(sq_dmg, APB_HAZARD_DAMAGE, sizeof(sq_dmg));
    memset(sq_type, APB_DMG_KINETIC, sizeof(sq_type));
    memset(sq_cond, 0, sizeof(sq_cond));
    memset(fl_owner, APB_NOBODY, sizeof(fl_owner));
    memset(fl_left, 0, sizeof(fl_left));
    memset(fl_fresh, 0, sizeof(fl_fresh));
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

void apb_battle_set_hazard(uint8_t damage, uint8_t type, uint8_t cond)
{
    map_hz[0] = damage;
    map_hz[1] = type;
    map_hz[2] = cond;
    memset(sq_dmg, damage, sizeof(sq_dmg));
    memset(sq_type, type, sizeof(sq_type));
    memset(sq_cond, cond, sizeof(sq_cond));
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
    uint8_t cost;

    if (count >= APB_FIGHTERS_MAX || f->x >= map_w || f->y >= map_h
        || who_is_at(f->x, f->y) != APB_NOBODY) {
        return APB_NOBODY;
    }
    cost = apb_tile_cost(tiles[f->y][f->x]);
    if (cost == 0) return APB_NOBODY;
    for (k = 0; k < FIELDS; ++k) fd[k][i] = ((const uint8_t *)f)[k];
    f_state[i] = APB_IN_FIGHT;
    f_guarding[i] = f_waited[i] = 0;
    if (f_health[i] > f_health_max[i]) f_health[i] = f_health_max[i];
    ++count;
    if (f_side[i] == APB_SIDE_TRAVELER && fd[25][i] != 0xFF) {
        apb_battle_trait(i, apb_race_trait(fd[25][i], 0));
        apb_battle_trait(i, apb_race_trait(fd[25][i], 1));
    }
    return i;
}

void apb_battle_fighter(uint8_t i, apb_fighter *out)
{
    uint8_t k;

    memset(out, 0, sizeof(*out));
    if (i >= count) return;
    for (k = 0; k < FIELDS; ++k) ((uint8_t *)out)[k] = fd[k][i];
}

#ifdef APB_ARENA
void apb_battle_rearm(uint8_t i, const apb_fighter *f)
{
    if (i >= count) return;
    f_dodge[i] = f->dodge;
    f_armor[i] = f->armor;
    f_ward[i] = f->ward;
    f_soak[i] = f->soak;
    f_speed[i] = f->speed;
    f_attack[i] = f->attack;
    f_weapon[i] = f->weapon;
    f_stat_bonus[i] = f->stat_bonus;
    f_ranged[i] = f->ranged;
    f_power[i] = f->power;
    f_dmg_type[i] = f->dmg_type;
    f_area[i] = f->area;
    f_behavior[i] = f->behavior;
    f_on_hit[i] = f->on_hit;
}
#endif

uint8_t apb_speed_v1(uint8_t grace, uint8_t armor_tier)
{
    uint8_t s = 5;

    if (grace >= 60) ++s;
    if (grace >= 90) ++s;
    if (armor_tier >= 3) --s;
    return s;
}

uint8_t apb_gear_damage_v1(uint8_t tier)
{
    return (uint8_t)(tier ? 2 + 3 * tier : APB_UNARMED_DAMAGE);
}

uint8_t apb_gear_armor_v1(uint8_t tier)
{
    return (uint8_t)(tier ? 5 + 5 * tier : 0);
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
    out->armor = apb_gear_armor_v1((uint8_t)(apb_armor(ch) / 10));
    out->speed = apb_speed_v1(ch->stat[APB_GRACE], (uint8_t)(apb_armor(ch) / 10));
    out->athletics = apb_skill(ch, APB_SK_ATHLETICS);
    out->weapon = apb_gear_damage_v1(weapon_item != 0 && weapon_item < APB_ITEM_COUNT
                                     ? apb_items[weapon_item].tier : 0);
    out->weak_type = 0xFF;
    out->behavior = APB_AI_CHARGE;
    if (arch == APB_ARCH_RANGED || arch == APB_ARCH_FOCUS) out->behavior = APB_AI_SHOOT;
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
    out->race = ch->race;
    out->on_hit = 0;
    out->power_stat = ch->cls < APB_CLASS_COUNT ? ch->stat[apb_class_bonus[ch->cls]] : 0;
    out->level = ch->level;
}

/* Who goes first: First (Early) before anyone; then highest Grace; travelers before foes
 * on a tie; then the order they joined. */
static uint8_t before(uint8_t q, uint8_t p)
{
    uint8_t fq = has_flag(q, APB_CF_FIRST);
    uint8_t fp = has_flag(p, APB_CF_FIRST);

    if (fq != fp) return fq;
    if (f_grace[q] != f_grace[p]) return (uint8_t)(f_grace[q] > f_grace[p]);
    return (uint8_t)(f_side[q] < f_side[p]);
}

void apb_battle_start(uint8_t first)
{
    uint8_t i;
    uint8_t j;
    uint8_t p;
    uint8_t q;

    for (i = 0; i < count; ++i) base[i] = i;
    for (i = 1; i < count; ++i) {
        for (j = i; j > 0; --j) {
            p = base[j - 1];
            q = base[j];
            if (before(q, p)) {
                base[j] = p;
                base[j - 1] = q;
            } else {
                break;
            }
        }
    }
    memcpy(order, base, sizeof(order));
    surprise = first;
    round_no = first == APB_SURPRISE_NONE ? 1 : 0;
    next = 0;
    begun = 0;
    result = APB_BATTLE_ON;
    for (i = 0; i < count; ++i) move_left[i] = apb_battle_speed(i);
}

/* ------------------------------------------------------------- the board */

/* A square's cost for `who`: flying makes pits and rough ground 1. 0: can't. */
static uint8_t cost_of(uint8_t who, uint8_t tile)
{
    if (flying(who) && (tile == APB_TILE_PIT || tile == APB_TILE_ROUGH)) return 1;
    return apb_tile_cost(tile);
}

/* The least it costs `who` to reach every square from sx, sy within budget, and of the
 * cheapest ways the one crossing fewest hazards (came[][] keeps the step). Anyone else
 * in a square blocks it; who's own square doesn't (for a Dash worked out from elsewhere). */
static void reach_from(uint8_t who, uint8_t sx, uint8_t sy, uint8_t budget)
{
    uint8_t x;
    uint8_t y;
    uint8_t d;
    uint8_t c;
    uint8_t h;
    uint8_t nx;
    uint8_t ny;
    uint8_t at;
    uint8_t changed = 1;

    memset(cost_to, 0xFF, sizeof(cost_to));
    memset(hz_to, 0xFF, sizeof(hz_to));
    cost_to[sy][sx] = 0;
    hz_to[sy][sx] = 0;
    while (changed) {
        changed = 0;
        for (y = 0; y < map_h; ++y) {
            for (x = 0; x < map_w; ++x) {
                if (cost_to[y][x] == 0xFF) continue;
                for (d = 0; d < 8; ++d) {
                    nx = (uint8_t)(x + step_x[d]);
                    ny = (uint8_t)(y + step_y[d]);
                    if (nx >= map_w || ny >= map_h) continue;
                    c = cost_of(who, tiles[ny][nx]);
                    if (c == 0) continue;
                    at = who_is_at(nx, ny);
                    if (at != APB_NOBODY && at != who) continue;
                    c = (uint8_t)(cost_to[y][x] + c);
                    h = (uint8_t)(hz_to[y][x] + (tiles[ny][nx] == APB_TILE_HAZARD));
                    if (c <= budget && (c < cost_to[ny][nx] || (c == cost_to[ny][nx] && h < hz_to[ny][nx]))) {
                        cost_to[ny][nx] = c;
                        hz_to[ny][nx] = h;
                        came[ny][nx] = d;
                        changed = 1;
                    }
                }
            }
        }
    }
}

static void reach(uint8_t who)
{
    reach_from(who, f_x[who], f_y[who], move_left[who]);
}

uint8_t apb_battle_can_reach(uint8_t who, uint8_t x, uint8_t y)
{
    if (who >= count || x >= map_w || y >= map_h) return 0;
    reach(who);
    return (uint8_t)(cost_to[y][x] != 0xFF);
}

static void copy_reach(uint8_t map[APB_MAP_H_MAX][APB_MAP_W_MAX])
{
    uint8_t x;
    uint8_t y;

    for (y = 0; y < map_h; ++y) {
        for (x = 0; x < map_w; ++x) map[y][x] = (uint8_t)(cost_to[y][x] != 0xFF);
    }
}

void apb_battle_reach_map(uint8_t who, uint8_t map[APB_MAP_H_MAX][APB_MAP_W_MAX])
{
    memset(map, 0, APB_MAP_H_MAX * APB_MAP_W_MAX);
    if (who >= count) return;
    reach(who);
    copy_reach(map);
}

void apb_battle_dash_map(uint8_t who, uint8_t x, uint8_t y, uint8_t map[APB_MAP_H_MAX][APB_MAP_W_MAX])
{
    memset(map, 0, APB_MAP_H_MAX * APB_MAP_W_MAX);
    if (who >= count || x >= map_w || y >= map_h) return;
    reach_from(who, x, y, apb_battle_speed(who));
    copy_reach(map);
}

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
    if (f_power[who] && has_flag(who, APB_CF_NO_POWERS)) return 0;
    d = dist(from_x, from_y, f_x[target], f_y[target]);
    if (f_area[who] && d <= f_area[who]) return 0;
    if (!f_ranged[who]) return (uint8_t)(d == 1);
    return in_sight(from_x, from_y, f_x[target], f_y[target], who);
}

uint8_t apb_battle_can_shove(uint8_t who, uint8_t target, uint8_t from_x, uint8_t from_y)
{
    if (who >= count || target >= count || who == target) return 0;
    if (f_state[target] != APB_IN_FIGHT || f_side[target] == f_side[who]) return 0;
    return (uint8_t)(dist(from_x, from_y, f_x[target], f_y[target]) == 1);
}

int16_t apb_battle_tn(uint8_t a, uint8_t t)
{
    int16_t defense = f_power[a] ? apb_battle_ward(t)
                                 : (f_dmg_type[a] == f_weak_type[t] ? 0 : apb_battle_armor(t));
    int16_t bonus = 0;

    if (f_ranged[a] && tiles[f_y[t]][f_x[t]] == APB_TILE_COVER) {
        bonus = (int16_t)(bonus + APB_COVER_BONUS);
    }
    return (int16_t)(apb_hit_tn(apb_battle_dodge(t), defense, bonus, 0) - gap(a, t));
}

int16_t apb_battle_shove_tn(uint8_t a, uint8_t t)
{
    return (int16_t)(apb_hit_tn(apb_battle_dodge(t), apb_battle_armor(t), 0, 0) - gap(a, t));
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
    if (f_state[who] != APB_IN_FIGHT || dmg == 0) return;
    f_health[who] = (uint8_t)(dmg >= f_health[who] ? 0 : f_health[who] - dmg);
    if (f_health[who] == 0) {
        f_state[who] = APB_DOWN;
        emit(APB_EV_DOWN, APB_NOBODY, who, 0);
        return;
    }
    take_off_flag(who, APB_CF_ENDS_HIT);
    if (f_coward[who] && 4u * f_health[who] <= f_health_max[who]) {
        f_state[who] = APB_GONE;
        emit(APB_EV_GONE, who, APB_NOBODY, 0);
    }
}

/* Damage that has already been through Soak (or that Soak doesn't touch), of a type or
 * APB_NO_TYPE: doubled if who is vulnerable to the type, then a barrier takes what it
 * can. Returns what reaches health. */
static uint16_t through(uint8_t who, uint16_t dmg, uint8_t type)
{
    uint8_t k;
    uint16_t took;

    if (type != APB_NO_TYPE) {
        for (k = 0; k < APB_COND_SLOTS; ++k) {
            if (c_id[who][k] && apb_conds[c_id[who][k]].vulnerable == type) {
                dmg = (uint16_t)(dmg * 2);
                break;
            }
        }
    }
    if (dmg && c_barrier[who]) {
        took = dmg < c_barrier[who] ? dmg : c_barrier[who];
        c_barrier[who] = (uint8_t)(c_barrier[who] - took);
        dmg = (uint16_t)(dmg - took);
        emit(APB_EV_ABSORB, who, APB_NOBODY, took);
        if (!c_barrier[who]) {
            for (k = 0; k < APB_COND_SLOTS; ++k) {
                if (c_id[who][k] && apb_conds[c_id[who][k]].barrier) take_off(who, k);
            }
        }
    }
    return dmg;
}

static uint16_t less_soak(uint8_t who, uint16_t dmg, uint8_t type)
{
    uint8_t s = type == APB_NO_TYPE ? 0 : apb_battle_soak(who);

    return (uint16_t)(dmg > s ? dmg - s : 0);
}

/* Whoever hit `who` in melee feels its thorns. */
static void thorns(uint8_t who, uint8_t attacker)
{
    uint8_t k;
    uint16_t dmg;
    const apb_cond_def *d;

    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (!c_id[who][k] || f_state[attacker] != APB_IN_FIGHT) continue;
        d = &apb_conds[c_id[who][k]];
        if (!d->thorns) continue;
        dmg = through(attacker, less_soak(attacker, d->thorns, d->thorns_type), d->thorns_type);
        emit_c(APB_EV_THORNS, who, attacker, dmg, c_id[who][k]);
        hurt(attacker, dmg);
    }
}

/* One roll; for an area attack, compared with the TN of everyone in the blast. */
static void attack(uint8_t who, uint8_t target)
{
    int16_t bonus;
    uint8_t i;
    uint8_t k;
    uint8_t cx = f_x[target];
    uint8_t cy = f_y[target];
    uint8_t roll;
    uint16_t dmg;

    putter = who;
    bonus = (int16_t)(sum(who, 5) + sum(who, 6) + sum(who, 8) + (f_ranged[who] ? 0 : sum(who, 7)));
    if (tiles[f_y[who]][f_x[who]] == APB_TILE_HIGH && tiles[cy][cx] != APB_TILE_HIGH) {
        bonus = (int16_t)(bonus + APB_HIGH_GROUND_BONUS);
    }
    roll = apb_d100(dice);
    /* Focused and the like: the next attack, and then they're gone. */
    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (c_id[who][k] && apb_conds[c_id[who][k]].next) take_off(who, k);
    }
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
        dmg = apb_damage(&shot, f_weapon[who], f_ranged[who] ? 0 : f_stat_bonus[who], apb_battle_soak(i));
        dmg = through(i, dmg, f_dmg_type[who]);
        ev.roll = shot;
        emit(APB_EV_ATTACK, who, i, dmg);
        hurt(i, dmg);
        if (shot.result != APB_FAIL) {
            if (f_on_hit[who]) put_on(i, f_on_hit[who]);
            if (!f_ranged[who]) thorns(i, who);
        }
        if (f_state[who] != APB_IN_FIGHT) break;
    }
}

/* The ground hits `who`: on stepping into a hazard, and at the start of a turn on one. */
static void hazard_hits(uint8_t who)
{
    uint8_t k;
    uint8_t x = f_x[who];
    uint8_t y = f_y[who];
    uint8_t type = sq_type[y][x];
    uint16_t dmg = sq_dmg[y][x];

    if (tiles[y][x] != APB_TILE_HAZARD) return;
    for (k = 0; k < APB_COND_SLOTS; ++k) {
        if (c_id[who][k] && type != APB_NO_TYPE && apb_conds[c_id[who][k]].immune_hazard == type) {
            dmg = 0;
        }
    }
    dmg = through(who, less_soak(who, dmg, type), type);
    emit(APB_EV_HAZARD, who, APB_NOBODY, dmg);
    hurt(who, dmg);
    if (sq_cond[y][x]) {
        /* A field's condition is its owner's; a hazard of the map's, nobody's (Resist 0). */
        k = putter;
        putter = fl_owner[y][x];
        put_on(who, sq_cond[y][x]);
        putter = k;
    }
}

static void fall(uint8_t who)
{
    emit(APB_EV_FALL, who, APB_NOBODY, 0);
    f_state[who] = APB_DOWN;
    emit(APB_EV_DOWN, APB_NOBODY, who, 0);
}

static void fall_if_over_pit(uint8_t who)
{
    if (tiles[f_y[who]][f_x[who]] == APB_TILE_PIT && !flying(who)) fall(who);
}

static void free_attack(uint8_t i, uint8_t who)
{
    if (f_state[i] != APB_IN_FIGHT || f_state[who] != APB_IN_FIGHT) return;
    if (has_flag(i, APB_CF_LOSE_TURN)) return;      /* asleep, stunned: no free attacks */
    if (!apb_battle_can_attack(i, who, f_x[i], f_y[i])) return;
    emit(APB_EV_FREE, i, who, 0);
    attack(i, who);
}

/* Moving along the path reach() found, a step at a time: pulling away from foes next to
 * you gives each a free attack first; each hazard stepped into hits; ending next to a foe
 * on guard that you weren't next to gives it one after. */
static void walk(uint8_t who, uint8_t x, uint8_t y)
{
    uint8_t i;
    uint8_t n = 0;
    uint8_t d;
    uint8_t sx = f_x[who];
    uint8_t sy = f_y[who];
    uint8_t px = x;
    uint8_t py = y;

    if (sx == x && sy == y) return;
    /* The steps, from the end back. */
    while ((px != sx || py != sy) && n < sizeof(path_x)) {
        path_x[n] = px;
        path_y[n] = py;
        ++n;
        d = came[py][px];
        px = (uint8_t)(px - step_x[d]);
        py = (uint8_t)(py - step_y[d]);
    }
    for (i = 0; i < count; ++i) {
        if (f_side[i] != f_side[who] && dist_to(i, who) == 1 && dist(f_x[i], f_y[i], x, y) > 1) {
            free_attack(i, who);
        }
    }
    while (n > 0 && f_state[who] == APB_IN_FIGHT) {
        --n;
        f_x[who] = path_x[n];
        f_y[who] = path_y[n];
        emit(APB_EV_MOVE, who, APB_NOBODY, 0);
        hazard_hits(who);
    }
    if (f_state[who] != APB_IN_FIGHT) return;
    for (i = 0; i < count; ++i) {
        if (f_guarding[i] && f_side[i] != f_side[who] && dist_to(i, who) == 1
            && dist(f_x[i], f_y[i], sx, sy) > 1 && f_state[i] == APB_IN_FIGHT) {
            f_guarding[i] = 0;
            free_attack(i, who);
        }
    }
}

static void move_to(uint8_t who, uint8_t x, uint8_t y)
{
    if (f_x[who] == x && f_y[who] == y) return;
    reach(who);
    if (cost_to[y][x] == 0xFF) return;
    walk(who, x, y);
}

/* Pushed n squares straight along dx, dy (docs/turn.md, Being pushed). */
static void push(uint8_t who, int8_t dx, int8_t dy, uint8_t n)
{
    uint8_t nx;
    uint8_t ny;
    uint16_t dmg;

    while (n-- > 0 && f_state[who] == APB_IN_FIGHT) {
        nx = (uint8_t)(f_x[who] + dx);
        ny = (uint8_t)(f_y[who] + dy);
        if (nx >= map_w || ny >= map_h || tiles[ny][nx] == APB_TILE_WALL
            || who_is_at(nx, ny) != APB_NOBODY) {
            dmg = through(who, less_soak(who, 3, APB_DMG_KINETIC), APB_DMG_KINETIC);
            emit(APB_EV_SLAM, who, APB_NOBODY, dmg);
            hurt(who, dmg);
            return;
        }
        f_x[who] = nx;
        f_y[who] = ny;
        emit(APB_EV_PUSH, who, APB_NOBODY, 0);
        if (tiles[ny][nx] == APB_TILE_PIT && !flying(who)) {
            fall(who);
            return;
        }
        hazard_hits(who);
    }
}

static void shove(uint8_t who, uint8_t t)
{
    int8_t dx = (int8_t)(f_x[t] > f_x[who] ? 1 : f_x[t] < f_x[who] ? -1 : 0);
    int8_t dy = (int8_t)(f_y[t] > f_y[who] ? 1 : f_y[t] < f_y[who] ? -1 : 0);

    putter = who;
    apb_check(dice, f_athletics[who], sum(who, 5), apb_battle_shove_tn(who, t), &shot);
    ev.roll = shot;
    emit(APB_EV_SHOVE, who, t, shot.result);
    if (shot.result == APB_FAIL) return;
    push(t, dx, dy, (uint8_t)(shot.result == APB_CRIT ? 2 : 1));
    if (shot.result == APB_CRIT) put_on(t, 9);              /* KNOCKED_DOWN */
    if (shot.result == APB_COST) put_on(who, 16);           /* EXPOSED      */
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
        apb_check(dice, f_athletics[who], sum(who, 5), apb_flee_tn(foes_next_to(who)), &shot);
    }
    ev.roll = shot;
    emit(APB_EV_FLEE, who, APB_NOBODY, shot.result);
    if (shot.result == APB_COST) {
        for (i = 0; i < count; ++i) {
            if (f_side[i] != f_side[who] && dist_to(i, who) == 1) free_attack(i, who);
        }
    }
    if (shot.result != APB_FAIL && f_state[who] == APB_IN_FIGHT) {
        f_state[who] = APB_GONE;
        emit(APB_EV_GONE, who, APB_NOBODY, 0);
    }
}

/* ------------------------------------------------------------- powers */

uint8_t apb_power_tier(uint8_t rank)
{
    return (uint8_t)(1 + (rank > 100 ? 100 : rank) / 20);
}

uint8_t apb_battle_learn(uint8_t who, uint8_t power, uint8_t rank)
{
    uint8_t k;

    if (who >= count || power >= apb_power_count || !apb_powers[power].defined) return APB_NOBODY;
    for (k = 0; k < APB_POWERS_HELD; ++k) {
        if (!p_id[who][k]) {
            p_id[who][k] = power;
            p_rank[who][k] = (uint8_t)(rank > 100 ? 100 : rank);
            p_left[who][k] = apb_powers[power].uses ? apb_powers[power].uses : 0xFF;
            return k;
        }
    }
    return APB_NOBODY;
}

uint8_t apb_battle_powers(uint8_t who, uint8_t *ids, uint8_t *ranks, uint8_t *left)
{
    uint8_t k;

    if (who >= count) return 0;
    for (k = 0; k < APB_POWERS_HELD && p_id[who][k]; ++k) {
        ids[k] = p_id[who][k];
        ranks[k] = p_rank[who][k];
        left[k] = p_left[who][k];
    }
    return k;
}

uint8_t apb_battle_power_rating(uint8_t who, uint8_t use)
{
    if (who >= count || use >= APB_POWERS_HELD || !p_id[who][use]) return 0;
    /* A foe's card has no class stat: its powers roll its Attack (the rank, its tier). */
    if (f_side[who] == APB_SIDE_FOE) return f_attack[who];
    return floor0((int16_t)(f_power_stat[who] / 2 + p_rank[who][use]));
}

/* Can `who` use power `use` now (it has it, charges left, not silenced)? */
static uint8_t usable(uint8_t who, uint8_t use)
{
    return (uint8_t)(who < count && use < APB_POWERS_HELD && p_id[who][use] && p_left[who][use]
                     && !has_flag(who, APB_CF_NO_POWERS));
}

/* A power's TN against t (docs/turn.md): Ward and Dodge; a hex's, or a mind power's, 50
 * alone; and cover; less the level gap, as every roll's. */
static int16_t power_tn(uint8_t who, uint8_t t, const apb_power_def *d)
{
    int16_t bonus = tiles[f_y[t]][f_x[t]] == APB_TILE_COVER ? APB_COVER_BONUS : 0;

    if (d->shape == APB_SH_HEX || d->element == APB_DMG_MIND) return (int16_t)(apb_hit_tn(0, 0, bonus, 0) - gap(who, t));
    return (int16_t)(apb_hit_tn(apb_battle_dodge(t), apb_battle_ward(t), bonus, 0) - gap(who, t));
}

static uint8_t burst_area(uint8_t tier)
{
    return (uint8_t)(tier >= 6 ? 2 : 1);
}

/* Is fighter t one power `use` can be used on, from x, y? */
static uint8_t power_can_target(uint8_t who, uint8_t use, uint8_t t, uint8_t x, uint8_t y)
{
    const apb_power_def *d = &apb_powers[p_id[who][use]];
    uint8_t d2;

    if (t >= count || f_state[t] != APB_IN_FIGHT) return 0;
    d2 = dist(x, y, f_x[t], f_y[t]);
    switch (d->target) {
    case APB_TG_SELF:
        return (uint8_t)(t == who);
    case APB_TG_ALLY:
        if (f_side[t] != f_side[who]) return 0;
        if (t == who) return 1;
        return (uint8_t)(d2 == 1);
    case APB_TG_FOE:
        if (f_side[t] == f_side[who]) return 0;
        if (d->adjacent) return (uint8_t)(d2 == 1);
        return in_sight(x, y, f_x[t], f_y[t], who);
    }
    return 0;
}

uint8_t apb_battle_power_targets(uint8_t who, uint8_t use, uint8_t x, uint8_t y,
                                 uint8_t *targets, int16_t *tns)
{
    uint8_t i;
    uint8_t n = 0;
    uint8_t sh;

    if (!usable(who, use)) return 0;
    sh = apb_powers[p_id[who][use]].shape;
    for (i = 0; i < count; ++i) {
        if (!power_can_target(who, use, i, x, y)) continue;
        targets[n] = i;
        tns[n] = (sh == APB_SH_BOLT || sh == APB_SH_HEX || sh == APB_SH_SHIFT)
                 ? power_tn(who, i, &apb_powers[p_id[who][use]]) : 0;
        ++n;
    }
    return n;
}

/* Can power `use` go on the square sx, sy, from x, y (a burst's centre, a field's middle,
 * a shift's end)? `who` is taken to stand at x, y. */
static uint8_t power_square_ok(uint8_t who, uint8_t use, uint8_t x, uint8_t y, uint8_t sx, uint8_t sy)
{
    const apb_power_def *d = &apb_powers[p_id[who][use]];
    uint8_t tier = apb_power_tier(p_rank[who][use]);
    uint8_t at;
    int8_t dx;
    int8_t dy;
    uint8_t n;
    uint8_t i;
    uint8_t cx;
    uint8_t cy;

    if (sx >= map_w || sy >= map_h || (sx == x && sy == y)) return 0;
    if (d->shape == APB_SH_SHIFT) {
        /* In a straight line (8 ways), up to tier + 2, through no wall; onto a square it
         * could stand on, with nobody there. */
        dx = (int8_t)(sx > x ? 1 : sx < x ? -1 : 0);
        dy = (int8_t)(sy > y ? 1 : sy < y ? -1 : 0);
        n = dist(x, y, sx, sy);
        if (n > tier + 2) return 0;
        if ((uint8_t)(x + dx * n) != sx || (uint8_t)(y + dy * n) != sy) return 0;
        for (i = 1; i <= n; ++i) {
            cx = (uint8_t)(x + dx * i);
            cy = (uint8_t)(y + dy * i);
            if (apb_tile_blocks_sight(tiles[cy][cx])) return 0;
        }
        at = who_is_at(sx, sy);
        return (uint8_t)((at == APB_NOBODY || at == who) && cost_of(who, tiles[sy][sx]) != 0);
    }
    /* A burst's centre or a field's middle: a square in sight. */
    if (apb_tile_blocks_sight(tiles[sy][sx]) || !in_sight(x, y, sx, sy, who)) return 0;
    if (d->shape == APB_SH_BURST) {
        /* Not where its blast would catch you. */
        return (uint8_t)(dist(x, y, sx, sy) > burst_area(tier));
    }
    if (d->shape == APB_SH_FIELD) {
        return (uint8_t)(tiles[sy][sx] == APB_TILE_OPEN || tiles[sy][sx] == APB_TILE_ROUGH);
    }
    return 0;
}

void apb_battle_power_squares(uint8_t who, uint8_t use, uint8_t x, uint8_t y,
                              uint8_t map[APB_MAP_H_MAX][APB_MAP_W_MAX])
{
    uint8_t sx;
    uint8_t sy;
    uint8_t ox;
    uint8_t oy;

    memset(map, 0, APB_MAP_H_MAX * APB_MAP_W_MAX);
    if (!usable(who, use) || apb_powers[p_id[who][use]].target != APB_TG_SQUARE) return;
    ox = f_x[who];
    oy = f_y[who];
    f_x[who] = x;
    f_y[who] = y;
    for (sy = 0; sy < map_h; ++sy) {
        for (sx = 0; sx < map_w; ++sx) map[sy][sx] = power_square_ok(who, use, x, y, sx, sy);
    }
    f_x[who] = ox;
    f_y[who] = oy;
}

/* A square becomes `tile` for `rounds` of who's turns: a field (docs/items.md), or a
 * fire rider's burning square. Hazards it makes do dmg of type, and put on cond. */
static void make_field(uint8_t who, uint8_t x, uint8_t y, uint8_t tile, uint8_t rounds,
                       uint8_t dmg, uint8_t type, uint8_t cond)
{
    if (fl_owner[y][x] == APB_NOBODY) fl_was[y][x] = tiles[y][x];
    fl_owner[y][x] = who;
    fl_left[y][x] = rounds;
    fl_fresh[y][x] = 1;
    tiles[y][x] = tile;
    sq_dmg[y][x] = dmg;
    sq_type[y][x] = type;
    sq_cond[y][x] = cond;
    ev.x = x;
    ev.y = y;
    ev.kind = APB_EV_FIELD;
    ev.actor = who;
    ev.target = APB_NOBODY;
    ev.value = tile;
    ev.cond = 0;
    if (report) report(&ev);
}

/* The end of who's turn: its fields count down, and those run out go back. */
static void fields_tick(uint8_t who)
{
    uint8_t x;
    uint8_t y;

    for (y = 0; y < map_h; ++y) {
        for (x = 0; x < map_w; ++x) {
            if (fl_owner[y][x] != who) continue;
            if (fl_fresh[y][x]) {
                fl_fresh[y][x] = 0;
                continue;
            }
            if (fl_left[y][x] && --fl_left[y][x]) continue;
            tiles[y][x] = fl_was[y][x];
            fl_owner[y][x] = APB_NOBODY;
            sq_dmg[y][x] = map_hz[0];
            sq_type[y][x] = map_hz[1];
            sq_cond[y][x] = map_hz[2];
            ev.x = x;
            ev.y = y;
            ev.kind = APB_EV_FIELD;
            ev.actor = APB_NOBODY;
            ev.target = APB_NOBODY;
            ev.value = tiles[y][x];
            ev.cond = 0;
            if (report) report(&ev);
        }
    }
}

/* The element's rider, on a power's hit (docs/items.md, Elements). */
static void rider(uint8_t who, uint8_t t, uint8_t element, uint8_t tier)
{
    int8_t dx;
    int8_t dy;
    uint8_t x;
    uint8_t y;

    if (f_state[t] != APB_IN_FIGHT) return;
    switch (element) {
    case APB_DMG_FIRE:
        /* Its square burns till the end of the caster's next turn. */
        x = f_x[t];
        y = f_y[t];
        if (tiles[y][x] == APB_TILE_OPEN || tiles[y][x] == APB_TILE_ROUGH || tiles[y][x] == APB_TILE_HAZARD) {
            make_field(who, x, y, APB_TILE_HAZARD, 1, (uint8_t)(5 * tier), APB_DMG_FIRE, 0);
        }
        break;
    case APB_DMG_COLD:
        put_on(t, 5);                                    /* CHILLED */
        break;
    case APB_DMG_KINETIC:
        dx = (int8_t)(f_x[t] > f_x[who] ? 1 : f_x[t] < f_x[who] ? -1 : 0);
        dy = (int8_t)(f_y[t] > f_y[who] ? 1 : f_y[t] < f_y[who] ? -1 : 0);
        push(t, dx, dy, 1);
        break;
    }
}

/* One power's roll against t, and what a hit does: Bolt and Burst damage, Hex a hex, and
 * any: the rider and the power's condition. Returns the result. */
static uint8_t power_hits(uint8_t who, uint8_t use, uint8_t t, uint8_t roll, int16_t bonus)
{
    const apb_power_def *d = &apb_powers[p_id[who][use]];
    uint8_t tier = apb_power_tier(p_rank[who][use]);
    uint16_t dmg = 0;

    shot.roll = roll;
    shot.total = (int16_t)(roll + apb_battle_power_rating(who, use) + bonus);
    shot.tn = power_tn(who, t, d);
    shot.result = apb_resolve(roll, shot.total, shot.tn);
    if (d->shape == APB_SH_BOLT || d->shape == APB_SH_BURST || d->shape == APB_SH_HEX) {
        /* A hex hurts too, half a bolt's (5 x tier, halved, rounded up). */
        dmg = apb_damage(&shot, (uint8_t)(d->shape == APB_SH_HEX ? (5 * tier + 1) / 2 : 5 * tier), 0,
                         d->element == APB_DMG_ENERGY ? 0 : apb_battle_soak(t));
        dmg = through(t, dmg, d->element);
    }
    ev.roll = shot;
    emit_c(APB_EV_HIT, who, t, dmg, p_id[who][use]);
    hurt(t, dmg);
    if (shot.result != APB_FAIL && f_state[t] == APB_IN_FIGHT) {
        if (d->shape == APB_SH_HEX) put_on_tier(t, 35, tier);        /* HEXED */
        if (d->shape != APB_SH_SHIFT) {
            if (d->cond) put_on_tier(t, d->cond, tier);
            rider(who, t, d->element, tier);
        }
    }
    return shot.result;
}

/* Is power `use` a shift of yourself to a square (Blink)? That's a move, not an action. */
static uint8_t self_shift(uint8_t who, uint8_t use)
{
    const apb_power_def *d;

    if (use >= APB_POWERS_HELD || !p_id[who][use]) return 0;
    d = &apb_powers[p_id[who][use]];
    return (uint8_t)(d->shape == APB_SH_SHIFT && d->target == APB_TG_SQUARE);
}

static void use_power(uint8_t who, uint8_t use, uint8_t t, uint8_t sx, uint8_t sy)
{
    const apb_power_def *d = &apb_powers[p_id[who][use]];
    uint8_t tier = apb_power_tier(p_rank[who][use]);
    uint8_t roll;
    uint8_t i;
    uint8_t n;
    uint8_t cx;
    uint8_t cy;
    uint8_t tile;
    int8_t dx;
    int8_t dy;
    int8_t px;
    int8_t py;
    int16_t bonus;
    uint16_t heal;

    putter = who;
    if (p_left[who][use] != 0xFF) --p_left[who][use];
    if (d->target == APB_TG_SQUARE) {
        cx = sx;
        cy = sy;
    } else if (d->target == APB_TG_AROUND) {
        cx = f_x[who];
        cy = f_y[who];
    } else {
        cx = f_x[t];
        cy = f_y[t];
    }
    ev.x = cx;
    ev.y = cy;
    ev.kind = APB_EV_POWER;
    ev.actor = who;
    ev.target = t;
    ev.value = tier;
    ev.cond = p_id[who][use];
    if (report) report(&ev);
    bonus = (int16_t)(sum(who, 5) + sum(who, 6) + sum(who, 8));
    if (d->shape == APB_SH_BOLT || d->shape == APB_SH_HEX || d->shape == APB_SH_BURST
        || (d->shape == APB_SH_SHIFT && d->target == APB_TG_FOE)) {
        /* An attack roll: Focused and the like are used up by it. */
        for (i = 0; i < APB_COND_SLOTS; ++i) {
            if (c_id[who][i] && apb_conds[c_id[who][i]].next) take_off(who, i);
        }
    }
    switch (d->shape) {
    case APB_SH_BOLT:
    case APB_SH_HEX:
        roll = apb_d100(dice);
        power_hits(who, use, t, roll, bonus);
        break;
    case APB_SH_BURST:
        roll = apb_d100(dice);
        for (i = 0; i < count; ++i) {
            if (f_state[i] != APB_IN_FIGHT) continue;
            if (d->target == APB_TG_AROUND && i == who) continue;
            if (!apb_in_area((int8_t)(f_x[i] - cx), (int8_t)(f_y[i] - cy), burst_area(tier))) continue;
            power_hits(who, use, i, roll, bonus);
        }
        break;
    case APB_SH_WARD:
        if (d->cond) put_on_tier(t, d->cond, tier);
        break;
    case APB_SH_MEND:
        heal = has_flag(t, APB_CF_NO_HEAL) ? 0 : (uint16_t)(5 * tier);
        if (heal > (uint16_t)(f_health_max[t] - f_health[t])) heal = (uint16_t)(f_health_max[t] - f_health[t]);
        f_health[t] = (uint8_t)(f_health[t] + heal);
        emit_c(APB_EV_MEND, who, t, heal, p_id[who][use]);
        if (heal) take_off_flag(t, APB_CF_ENDS_HEAL);
        if (d->cond) put_on_tier(t, d->cond, tier);
        break;
    case APB_SH_FIELD:
        /* A line of tier + 2 squares, across the line from you to its middle. */
        dx = (int8_t)(cx > f_x[who] ? 1 : cx < f_x[who] ? -1 : 0);
        dy = (int8_t)(cy > f_y[who] ? 1 : cy < f_y[who] ? -1 : 0);
        px = (int8_t)-dy;
        py = dx;
        n = (uint8_t)(tier + 2);
        tile = d->element == APB_DMG_COLD ? APB_TILE_ROUGH
             : d->element == APB_DMG_KINETIC ? APB_TILE_WALL
             : d->element == APB_DMG_MIND ? APB_TILE_COVER : APB_TILE_HAZARD;
        for (i = 0; i < n; ++i) {
            sx = (uint8_t)(cx + px * (int8_t)(i - (n - 1) / 2));
            sy = (uint8_t)(cy + py * (int8_t)(i - (n - 1) / 2));
            if (sx >= map_w || sy >= map_h || who_is_at(sx, sy) != APB_NOBODY) continue;
            if (tiles[sy][sx] != APB_TILE_OPEN && tiles[sy][sx] != APB_TILE_ROUGH) continue;
            make_field(who, sx, sy, tile, 3, (uint8_t)(5 * tier),
                       d->element == APB_NO_TYPE ? APB_DMG_KINETIC : d->element, d->cond);
        }
        break;
    case APB_SH_SHIFT:
        if (d->target == APB_TG_SQUARE) {
            /* Yourself: there in a blink; nobody gets a free attack. */
            f_x[who] = sx;
            f_y[who] = sy;
            emit(APB_EV_SHIFT, who, APB_NOBODY, 0);
            hazard_hits(who);
            if (f_state[who] == APB_IN_FIGHT) fall_if_over_pit(who);
        } else {
            roll = apb_d100(dice);
            if (power_hits(who, use, t, roll, bonus) != APB_FAIL && f_state[t] == APB_IN_FIGHT) {
                dx = (int8_t)(f_x[t] > f_x[who] ? 1 : f_x[t] < f_x[who] ? -1 : 0);
                dy = (int8_t)(f_y[t] > f_y[who] ? 1 : f_y[t] < f_y[who] ? -1 : 0);
                push(t, dx, dy, (uint8_t)(tier + 2));
            }
        }
        break;
    }
}

/* ------------------------------------------------------------- the foes */

static uint8_t nearest(uint8_t who, uint8_t x, uint8_t y, uint8_t attackable)
{
    uint8_t i;
    uint8_t best = APB_NOBODY;
    uint8_t best_d = 0xFF;
    uint8_t d;

    for (i = 0; i < count; ++i) {
        if (f_state[i] != APB_IN_FIGHT || f_side[i] == f_side[who]) continue;
        if (attackable && !apb_battle_can_attack(who, i, x, y)) continue;
        d = dist(x, y, f_x[i], f_y[i]);
        if (d < best_d) {
            best_d = d;
            best = i;
        }
    }
    return best;
}

static uint8_t plan_x;
static uint8_t plan_y;
static uint8_t plan_blink;      /* 0, or the power (+1) the plan's move is a blink by */
static uint8_t plan_target;
static uint8_t plan_kind;          /* APB_ACT_ATTACK, or APB_ACT_POWER          */
static uint8_t plan_use;
static uint8_t plan_sx;
static uint8_t plan_sy;

/* As v0's plan: but of two squares as good, the one that isn't a hazard. */
static uint8_t better(uint8_t x, uint8_t y)
{
    uint8_t hz = tiles[y][x] == APB_TILE_HAZARD;
    uint8_t phz = tiles[plan_y][plan_x] == APB_TILE_HAZARD;

    if (hz != phz) return (uint8_t)(!hz);
    return (uint8_t)(cost_to[y][x] < cost_to[plan_y][plan_x]);
}

static void plan(uint8_t who)
{
    uint8_t x;
    uint8_t y;
    uint8_t t;
    uint8_t goal;
    uint8_t d;
    uint8_t best;

    plan_x = f_x[who];
    plan_y = f_y[who];
    plan_target = nearest(who, plan_x, plan_y, 1);
    if (plan_target != APB_NOBODY || f_behavior[who] == APB_AI_GUARD) return;
    reach(who);
    if (f_behavior[who] == APB_AI_SHOOT && f_ranged[who]) {
        best = 0xFF;
        for (y = 0; y < map_h; ++y) {
            for (x = 0; x < map_w; ++x) {
                if (cost_to[y][x] < best && (t = nearest(who, x, y, 1)) != APB_NOBODY) {
                    best = cost_to[y][x];
                    plan_x = x;
                    plan_y = y;
                    plan_target = t;
                }
            }
        }
        if (best != 0xFF) return;
    }
    goal = nearest(who, f_x[who], f_y[who], 0);
    if (goal == APB_NOBODY) return;
    best = dist_to(who, goal);
    for (y = 0; y < map_h; ++y) {
        for (x = 0; x < map_w; ++x) {
            if (cost_to[y][x] == 0xFF) continue;
            if (tiles[y][x] == APB_TILE_PIT) continue;      /* a flyer doesn't stop over one */
            d = dist(x, y, f_x[goal], f_y[goal]);
            if (d < best || (d == best && better(x, y))) {
                best = d;
                plan_x = x;
                plan_y = y;
            }
        }
    }
    plan_target = nearest(who, plan_x, plan_y, 1);
}

/* ------------------------------------------------- the computer's powers */

/* How likely a roll of rating against tn is to land, in percent (glancing hits aside). */
static int16_t chance(int16_t rating, int16_t tn)
{
    int16_t p = (int16_t)(100 + rating - tn);

    return (int16_t)(p < 0 ? 0 : p > 100 ? 100 : p);
}

static uint8_t foes_within(uint8_t who, uint8_t x, uint8_t y, uint8_t d)
{
    uint8_t i;
    uint8_t n = 0;

    for (i = 0; i < count; ++i) {
        if (f_state[i] == APB_IN_FIGHT && f_side[i] != f_side[who] && dist(x, y, f_x[i], f_y[i]) <= d) ++n;
    }
    return n;
}

/* A blast on cx, cy (Area a): how many of who's foes it catches, or 0 if it catches any of
 * who's side (who too, unless `around`). */
static uint8_t blast_count(uint8_t who, uint8_t cx, uint8_t cy, uint8_t a, uint8_t around)
{
    uint8_t i;
    uint8_t n = 0;

    for (i = 0; i < count; ++i) {
        if (f_state[i] != APB_IN_FIGHT || (around && i == who)) continue;
        if (!apb_in_area((int8_t)(f_x[i] - cx), (int8_t)(f_y[i] - cy), a)) continue;
        if (f_side[i] == f_side[who]) return 0;
        ++n;
    }
    return n;
}

/* How many of who's melee foes could reach x, y next turn (within their Speed and a
 * step); and in *closest, the distance to the nearest foe of all. */
static uint8_t reachers(uint8_t who, uint8_t x, uint8_t y, uint8_t *closest)
{
    uint8_t i;
    uint8_t d;
    uint8_t n = 0;

    *closest = 0xFF;
    for (i = 0; i < count; ++i) {
        if (f_state[i] != APB_IN_FIGHT || f_side[i] == f_side[who]) continue;
        d = dist(x, y, f_x[i], f_y[i]);
        if (d < *closest) *closest = d;
        if (!f_ranged[i] && d <= apb_battle_speed(i) + 1) ++n;
    }
    return n;
}

/* Would a push of n along dx, dy from t's square drop it in a pit (or onto a hazard)? */
static uint8_t push_lands_badly(uint8_t t, int8_t dx, int8_t dy, uint8_t n)
{
    uint8_t x = f_x[t];
    uint8_t y = f_y[t];

    while (n-- > 0) {
        x = (uint8_t)(x + dx);
        y = (uint8_t)(y + dy);
        if (x >= map_w || y >= map_h || tiles[y][x] == APB_TILE_WALL || who_is_at(x, y) != APB_NOBODY) return 0;
        if (tiles[y][x] == APB_TILE_PIT) return (uint8_t)!flying(t);
        if (tiles[y][x] == APB_TILE_HAZARD) return 1;
    }
    return 0;
}

/* The computer's choice of a power (docs/turn.md, "How the computer uses powers"): the
 * first of these that it can, from where its plan has it standing; or none, and it keeps
 * to its weapon. Sets plan_kind, plan_use, plan_target, plan_sx, plan_sy. */
static void plan_power(uint8_t who)
{
    static uint8_t tg[APB_FIGHTERS_MAX];
    static int16_t tn[APB_FIGHTERS_MAX];
    static uint8_t sq[APB_MAP_H_MAX][APB_MAP_W_MAX];
    uint8_t k;
    uint8_t n;
    uint8_t i;
    uint8_t x;
    uint8_t y;
    uint8_t best;
    uint8_t bi;
    uint8_t tier;
    uint8_t step;
    int16_t v;
    int16_t bv;
    int16_t weapon;
    const apb_power_def *d;

    plan_kind = APB_ACT_ATTACK;
    plan_blink = 0;
    for (step = 1; step <= 8; ++step) {
        for (k = 0; k < APB_POWERS_HELD; ++k) {
            if (!usable(who, k)) continue;
            d = &apb_powers[p_id[who][k]];
            tier = apb_power_tier(p_rank[who][k]);
            switch (step) {
            case 1:
                /* Mend: you, or a friend next to you, at half health or less (most hurt). */
                if (d->shape != APB_SH_MEND) break;
                n = apb_battle_power_targets(who, k, plan_x, plan_y, tg, tn);
                best = APB_NOBODY;
                bv = 0;
                for (i = 0; i < n; ++i) {
                    v = (int16_t)(f_health_max[tg[i]] - f_health[tg[i]]);
                    if (2 * f_health[tg[i]] <= f_health_max[tg[i]] && !has_flag(tg[i], APB_CF_NO_HEAL) && v > bv) {
                        bv = v;
                        best = tg[i];
                    }
                }
                if (best == APB_NOBODY) break;
                plan_kind = APB_ACT_POWER;
                plan_use = k;
                plan_target = best;
                return;
            case 2:
                /* Blink as your move: a shooter with a foe next to it goes where fewer
                 * melee foes can reach it next turn (their Speed and a step) than where
                 * it stands; of those, the fewest, then where it can still shoot someone,
                 * then the furthest from them. Then it acts from there. */
                if (plan_blink || !self_shift(who, k) || !f_ranged[who]) break;
                if (!foes_within(who, f_x[who], f_y[who], 1)) break;
                n = reachers(who, f_x[who], f_y[who], &x);
                apb_battle_power_squares(who, k, f_x[who], f_y[who], sq);
                bv = 0;
                for (y = 0; y < map_h; ++y) {
                    for (i = 0; i < map_w; ++i) {
                        if (!sq[y][i] || tiles[y][i] == APB_TILE_HAZARD) continue;
                        tier = reachers(who, i, y, &bi);
                        if (tier >= n) continue;
                        v = (int16_t)((n - tier) * 0x200 + bi
                                      + (nearest(who, i, y, 1) != APB_NOBODY ? 0x100 : 0));
                        if (v > bv) {
                            bv = v;
                            plan_sx = i;
                            plan_sy = y;
                        }
                    }
                }
                if (!bv) break;
                plan_blink = (uint8_t)(k + 1);
                plan_x = plan_sx;
                plan_y = plan_sy;
                plan_target = nearest(who, plan_x, plan_y, 1);
                break;
            case 3:
                /* A shove of a power (Bull rush) that drops a foe in a pit, or onto a hazard. */
                if (d->shape != APB_SH_SHIFT || d->target != APB_TG_FOE) break;
                n = apb_battle_power_targets(who, k, plan_x, plan_y, tg, tn);
                for (i = 0; i < n; ++i) {
                    if (!push_lands_badly(tg[i], (int8_t)(f_x[tg[i]] > plan_x ? 1 : f_x[tg[i]] < plan_x ? -1 : 0),
                                          (int8_t)(f_y[tg[i]] > plan_y ? 1 : f_y[tg[i]] < plan_y ? -1 : 0),
                                          (uint8_t)(tier + 2))) continue;
                    plan_kind = APB_ACT_POWER;
                    plan_use = k;
                    plan_target = tg[i];
                    return;
                }
                break;
            case 4:
                /* A blast that catches two foes or more, and none of your side. */
                if (d->shape != APB_SH_BURST) break;
                if (d->target == APB_TG_AROUND) {
                    if (blast_count(who, plan_x, plan_y, burst_area(tier), 1) < 2) break;
                    plan_kind = APB_ACT_POWER;
                    plan_use = k;
                    return;
                }
                apb_battle_power_squares(who, k, plan_x, plan_y, sq);
                best = 1;
                for (y = 0; y < map_h; ++y) {
                    for (x = 0; x < map_w; ++x) {
                        if (!sq[y][x]) continue;
                        n = blast_count(who, x, y, burst_area(tier), 0);
                        if (n > best) {
                            best = n;
                            plan_sx = x;
                            plan_sy = y;
                        }
                    }
                }
                if (best < 2) break;
                plan_kind = APB_ACT_POWER;
                plan_use = k;
                return;
            case 5:
                /* A ward on a friend next to you who hasn't it, with a foe near them; on
                 * yourself only when there's nobody to attack this turn. */
                if (d->shape != APB_SH_WARD || !d->cond) break;
                n = apb_battle_power_targets(who, k, plan_x, plan_y, tg, tn);
                for (i = 0; i < n; ++i) {
                    /* You from where you'll stand; a friend from where they are. */
                    x = tg[i] == who ? plan_x : f_x[tg[i]];
                    y = tg[i] == who ? plan_y : f_y[tg[i]];
                    if (has(tg[i], d->cond) || !foes_within(tg[i], x, y, 3)) continue;
                    if (tg[i] == who && plan_target != APB_NOBODY) continue;
                    plan_kind = APB_ACT_POWER;
                    plan_use = k;
                    plan_target = tg[i];
                    return;
                }
                break;
            case 6:
                /* A hex on the foe with the best Attack that hasn't it yet, and has health
                 * enough to be worth it (three of your weapon's hits or more). */
                if (d->shape != APB_SH_HEX) break;
                n = apb_battle_power_targets(who, k, plan_x, plan_y, tg, tn);
                best = APB_NOBODY;
                for (i = 0; i < n; ++i) {
                    if (has(tg[i], 35) || (d->cond && (has(tg[i], d->cond) || immune_to(tg[i], d->cond)))) continue;
                    if (f_health[tg[i]] < 3 * (f_weapon[who] + (f_ranged[who] ? 0 : f_stat_bonus[who]))) continue;
                    if (chance((int16_t)apb_battle_power_rating(who, k), tn[i]) < 30) continue;
                    if (best == APB_NOBODY || f_attack[tg[i]] > f_attack[best]) best = tg[i];
                }
                if (best == APB_NOBODY) break;
                plan_kind = APB_ACT_POWER;
                plan_use = k;
                plan_target = best;
                return;
            case 7:
                /* A bolt, when it beats the weapon (or the weapon can't reach anyone). */
                if (d->shape != APB_SH_BOLT) break;
                weapon = 0;
                if (plan_target != APB_NOBODY) {
                    v = (int16_t)(f_weapon[who] + (f_ranged[who] ? 0 : f_stat_bonus[who]) - apb_battle_soak(plan_target));
                    weapon = (int16_t)(chance((int16_t)(f_attack[who] + sum(who, 5) + sum(who, 6)),
                                              apb_battle_tn(who, plan_target)) * (v < 1 ? 1 : v));
                }
                n = apb_battle_power_targets(who, k, plan_x, plan_y, tg, tn);
                bv = weapon;
                bi = APB_NOBODY;
                for (i = 0; i < n; ++i) {
                    v = (int16_t)(5 * tier - (d->element == APB_DMG_ENERGY ? 0 : apb_battle_soak(tg[i])));
                    v = (int16_t)(chance((int16_t)(apb_battle_power_rating(who, k) + sum(who, 5) + sum(who, 6)), tn[i])
                                  * (v < 1 ? 1 : v));
                    if (v > bv) {
                        bv = v;
                        bi = tg[i];
                    }
                }
                if (bi == APB_NOBODY) break;
                plan_kind = APB_ACT_POWER;
                plan_use = k;
                plan_target = bi;
                return;
            case 8:
                /* A field across the way of a foe coming at a shooter: halfway to it. */
                if (d->shape != APB_SH_FIELD || !f_ranged[who] || d->element == APB_NO_TYPE) break;
                best = nearest(who, plan_x, plan_y, 0);
                if (best == APB_NOBODY || f_ranged[best]) break;
                n = dist(plan_x, plan_y, f_x[best], f_y[best]);
                if (n < 3 || n > 6) break;
                x = (uint8_t)((plan_x + f_x[best]) / 2);
                y = (uint8_t)((plan_y + f_y[best]) / 2);
                apb_battle_power_squares(who, k, plan_x, plan_y, sq);
                if (!sq[y][x]) break;
                plan_kind = APB_ACT_POWER;
                plan_use = k;
                plan_sx = x;
                plan_sy = y;
                return;
            }
        }
    }
}

static void guard(uint8_t who)
{
    f_guarding[who] = 1;
    emit(APB_EV_GUARD, who, APB_NOBODY, 0);
}

static void foe_turn(uint8_t who)
{
    uint8_t px;
    uint8_t py;

    plan(who);
    plan_power(who);
    if (plan_blink) use_power(who, (uint8_t)(plan_blink - 1), APB_NOBODY, plan_x, plan_y);
    else move_to(who, plan_x, plan_y);
    if (f_state[who] != APB_IN_FIGHT) return;
    if (plan_kind == APB_ACT_POWER) {
        /* As the player's would be: checked again from where it got to. */
        px = f_x[who];
        py = f_y[who];
        if (apb_powers[p_id[who][plan_use]].target == APB_TG_SQUARE
                ? power_square_ok(who, plan_use, px, py, plan_sx, plan_sy)
                : apb_powers[p_id[who][plan_use]].target == APB_TG_AROUND
                  || power_can_target(who, plan_use, plan_target, px, py)) {
            use_power(who, plan_use, plan_target, plan_sx, plan_sy);
        }
        return;
    }
    if (plan_target != APB_NOBODY && apb_battle_can_attack(who, plan_target, f_x[who], f_y[who])) {
        attack(who, plan_target);
    } else if (f_behavior[who] == APB_AI_GUARD) {
        guard(who);
    }
}

void apb_battle_quick(uint8_t who, apb_action *out)
{
    memset(out, 0, sizeof(*out));
    if (who >= count) return;
    plan(who);
    plan_power(who);
    out->move_x = plan_x;
    out->move_y = plan_y;
    out->dash_x = plan_x;
    out->dash_y = plan_y;
    out->kind = APB_ACT_DONE;
    out->move_use = plan_blink;
    if (plan_kind == APB_ACT_POWER) {
        out->kind = APB_ACT_POWER;
        out->use = plan_use;
        out->target = plan_target == APB_NOBODY ? 0 : plan_target;
        if (apb_powers[p_id[who][plan_use]].target == APB_TG_SQUARE) {
            out->dash_x = plan_sx;
            out->dash_y = plan_sy;
        }
    } else if (plan_target != APB_NOBODY) {
        out->kind = APB_ACT_ATTACK;
        out->target = plan_target;
    } else if (f_behavior[who] == APB_AI_GUARD) {
        out->kind = APB_ACT_GUARD;
    }
}

/* ------------------------------------------------------------- turns */

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
    acted_first = 0;
    if (++next >= count) {
        next = 0;
        if (round_no < 255) ++round_no;
        memcpy(order, base, sizeof(order));
        memset(f_waited, 0, sizeof(f_waited));
    }
}

/* The start of a turn (docs/turn.md): guarding ends; the ground; conditions tick; standing
 * up. Returns 1 if the turn goes on, 0 if a condition took it (or the fighter's out). Not
 * again when a turn put off with Wait comes round. */
static uint8_t begin_turn(uint8_t who)
{
    uint8_t k;
    uint8_t cond;
    uint8_t s;
    uint16_t dmg;
    uint16_t heal;
    const apb_cond_def *d;

    emit(APB_EV_TURN, who, APB_NOBODY, round_no);
    acting = who;
    if (f_waited[who]) return 1;
    f_guarding[who] = 0;
    move_left[who] = apb_battle_speed(who);
    hazard_hits(who);
    for (k = 0; k < APB_COND_SLOTS && f_state[who] == APB_IN_FIGHT; ++k) {
        cond = c_id[who][k];
        if (!cond || !apb_conds[cond].dot) continue;
        d = &apb_conds[cond];
        dmg = through(who, less_soak(who, d->dot, d->dot_type), d->dot_type);
        emit_c(APB_EV_TICK, who, APB_NOBODY, dmg, cond);
        hurt(who, dmg);
    }
    for (k = 0; k < APB_COND_SLOTS && f_state[who] == APB_IN_FIGHT; ++k) {
        cond = c_id[who][k];
        if (!cond || !apb_conds[cond].heal) continue;
        heal = has_flag(who, APB_CF_NO_HEAL) ? 0 : apb_conds[cond].heal;
        if (heal > (uint16_t)(f_health_max[who] - f_health[who])) heal = (uint16_t)(f_health_max[who] - f_health[who]);
        f_health[who] = (uint8_t)(f_health[who] + heal);
        /* Said when it heals, or when something (a curse) stops it. */
        if (heal || has_flag(who, APB_CF_NO_HEAL)) emit_c(APB_EV_HEAL, who, APB_NOBODY, heal, cond);
        if (heal) take_off_flag(who, APB_CF_ENDS_HEAL);
    }
    if (f_state[who] != APB_IN_FIGHT) return 0;
    for (k = 0; k < APB_COND_SLOTS; ++k) {
        cond = c_id[who][k];
        if (cond && (apb_conds[cond].flags & APB_CF_LOSE_TURN)) {
            emit_c(APB_EV_SKIP, who, APB_NOBODY, 0, cond);
            return 0;
        }
    }
    if (has_flag(who, APB_CF_DOWN)) {
        /* Standing up takes half your Speed, rounded up. */
        take_off_flag(who, APB_CF_DOWN);
        s = apb_battle_speed(who);
        move_left[who] = (uint8_t)(s - (s + 1) / 2);
        emit(APB_EV_STAND, who, APB_NOBODY, move_left[who]);
    }
    return 1;
}

/* The end of a turn: count down (not what went on during it), then shake off. */
static void end_turn(uint8_t who)
{
    uint8_t k;
    uint8_t cond;
    uint8_t then;
    int16_t bonus;
    const apb_cond_def *d;

    acting = APB_NOBODY;
    putter = APB_NOBODY;
    fields_tick(who);
    if (f_state[who] != APB_IN_FIGHT) return;
    for (k = 0; k < APB_COND_SLOTS; ++k) {
        cond = c_id[who][k];
        if (!cond || c_fresh[who][k]) continue;
        if (c_left[who][k] && --c_left[who][k] == 0) {
            then = apb_conds[cond].then;
            take_off(who, k);
            if (then) put_on(who, then);
        }
    }
    memset(c_fresh[who], 0, sizeof(c_fresh[who]));
    for (k = 0; k < APB_COND_SLOTS && f_state[who] == APB_IN_FIGHT; ++k) {
        cond = c_id[who][k];
        if (!cond) continue;
        d = &apb_conds[cond];
        if (!d->shake_tn) continue;
        /* d100 against its number, less the level gap to whoever put it on. */
        bonus = (int16_t)(sum(who, 9) + sum(who, 5));
        apb_check(dice, 0, bonus, (int16_t)(d->shake_tn - 2 * ((int16_t)level_of(who) - (int16_t)c_from[who][k])),
                  &shot);
        ev.roll = shot;
        emit_c(APB_EV_SHAKE, who, APB_NOBODY, shot.result, cond);
        if (shot.result >= APB_SUCCESS) take_off(who, k);
    }
}

uint8_t apb_battle_next(void)
{
    uint8_t who;
    uint8_t guard;
    uint8_t on;

    for (guard = 0; guard < 255; ++guard) {
        check_end();
        if (result != APB_BATTLE_ON) return APB_NOBODY;
        who = turn_of();
        if (who == APB_NOBODY) {
            advance();
            continue;
        }
        if (f_side[who] == APB_SIDE_TRAVELER) {
            if (!begun) {
                begun = 1;
                on = begin_turn(who);
                if (!on) {
                    end_turn(who);
                    advance();
                    continue;
                }
            }
            if (f_state[who] == APB_IN_FIGHT) return who;
            advance();
            continue;
        }
        on = begin_turn(who);
        if (on && f_state[who] == APB_IN_FIGHT) foe_turn(who);
        end_turn(who);
        advance();
    }
    return APB_NOBODY;
}

/* The standard action before the move (docs/turn.md, Actions: either order): an attack,
 * a power (not Blink: that's a move), a Shove or Guard, from where you stand. The turn
 * goes on: the next apb_battle_act is the move, with APB_ACT_DONE. */
uint8_t apb_battle_act_first(uint8_t who, const apb_action *a)
{
    apb_action here;

    if (a->kind != APB_ACT_ATTACK && a->kind != APB_ACT_SHOVE && a->kind != APB_ACT_POWER
        && a->kind != APB_ACT_GUARD) return 0;
    here = *a;
    here.move_x = f_x[who];
    here.move_y = f_y[who];
    here.move_use = 0;
    acting_first = 1;
    who = apb_battle_act(who, &here);
    acting_first = 0;
    return who;
}

uint8_t apb_battle_act(uint8_t who, const apb_action *a)
{
    uint8_t ok = 1;
    uint8_t t = a->target;
    uint8_t i;
    uint8_t ox;
    uint8_t oy;

    if (result != APB_BATTLE_ON || who >= count || order[next] != who || !begun) return 0;
    if (acted_first && a->kind != APB_ACT_DONE) return 0;     /* acted: only the move is left */
    if (a->move_use) {
        /* Blink is a move: from where you stand, instead of walking. */
        i = (uint8_t)(a->move_use - 1);
        if (i >= APB_POWERS_HELD || !usable(who, i) || !self_shift(who, i)
            || !power_square_ok(who, i, f_x[who], f_y[who], a->move_x, a->move_y)) return 0;
    } else if (a->move_x != f_x[who] || a->move_y != f_y[who]) {
        if (!apb_battle_can_reach(who, a->move_x, a->move_y)) return 0;
    }
    switch (a->kind) {
    case APB_ACT_ATTACK:
        ok = apb_battle_can_attack(who, t, a->move_x, a->move_y);
        break;
    case APB_ACT_SHOVE:
        ok = apb_battle_can_shove(who, t, a->move_x, a->move_y);
        break;
    case APB_ACT_WAIT:
        ok = (uint8_t)(a->move_x == f_x[who] && a->move_y == f_y[who] && !f_waited[who]);
        break;
    case APB_ACT_DASH:
        /* As if standing where the move ends, with a full Speed. */
        ox = f_x[who];
        oy = f_y[who];
        f_x[who] = a->move_x;
        f_y[who] = a->move_y;
        reach_from(who, a->move_x, a->move_y, apb_battle_speed(who));
        ok = (uint8_t)(a->dash_x < map_w && a->dash_y < map_h && cost_to[a->dash_y][a->dash_x] != 0xFF);
        f_x[who] = ox;
        f_y[who] = oy;
        break;
    case APB_ACT_POWER:
        /* Shifting yourself is your move, not your action. */
        ok = (uint8_t)(usable(who, a->use) && !self_shift(who, a->use));
        if (!ok) break;
        /* As if standing where the move ends. */
        ox = f_x[who];
        oy = f_y[who];
        f_x[who] = a->move_x;
        f_y[who] = a->move_y;
        i = apb_powers[p_id[who][a->use]].target;
        if (i == APB_TG_SQUARE) ok = power_square_ok(who, a->use, a->move_x, a->move_y, a->dash_x, a->dash_y);
        else if (i != APB_TG_AROUND) ok = power_can_target(who, a->use, t, a->move_x, a->move_y);
        f_x[who] = ox;
        f_y[who] = oy;
        break;
    case APB_ACT_GUARD:
    case APB_ACT_FLEE:
    case APB_ACT_DONE:
        break;
    default:
        ok = 0;
    }
    if (!ok) return 0;

    if (a->kind == APB_ACT_WAIT) {
        f_waited[who] = 1;
        emit(APB_EV_WAIT, who, APB_NOBODY, 0);
        for (i = next; i + 1 < count; ++i) order[i] = order[i + 1];
        order[count - 1] = who;
        begun = 0;
        return 1;
    }
    if (acting_first) {
        /* The action now, from where you stand; the move is still to come. */
        acting_first = 0;
        acted_first = 1;
        if (a->kind == APB_ACT_ATTACK) attack(who, t);
        else if (a->kind == APB_ACT_GUARD) guard(who);
        else if (a->kind == APB_ACT_SHOVE) shove(who, t);
        else use_power(who, a->use, t, a->dash_x, a->dash_y);
        check_end();
        return 1;
    }
    if (a->move_use) {
        use_power(who, (uint8_t)(a->move_use - 1), APB_NOBODY, a->move_x, a->move_y);
        move_left[who] = 0;
    } else {
        move_to(who, a->move_x, a->move_y);
    }
    if (f_state[who] == APB_IN_FIGHT) {
        switch (a->kind) {
        case APB_ACT_ATTACK: attack(who, t); break;
        case APB_ACT_GUARD:  guard(who); break;
        case APB_ACT_FLEE:   flee(who); break;
        case APB_ACT_SHOVE:  shove(who, t); break;
        case APB_ACT_POWER:
            use_power(who, a->use, t, a->dash_x, a->dash_y);
            break;
        case APB_ACT_DASH:
            emit(APB_EV_DASH, who, APB_NOBODY, 0);
            move_left[who] = apb_battle_speed(who);
            move_to(who, a->dash_x, a->dash_y);
            break;
        }
    }
    if (f_state[who] == APB_IN_FIGHT) fall_if_over_pit(who);
    end_turn(who);
    advance();
    check_end();
    return 1;
}
