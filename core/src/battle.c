#include <string.h>

#include "apb_battle.h"

/*
 * The battle: docs/combat.md. Everything is decided by the order of play, the
 * actions taken and the dice, so a battle replays exactly from its actions.
 */

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

static void emit(apb_battle *b, uint8_t kind, uint8_t actor, uint8_t target, uint16_t value)
{
    ev.kind = kind;
    ev.actor = actor;
    ev.target = target;
    ev.value = value;
    if (actor != APB_NOBODY) {
        ev.x = b->f[actor].x;
        ev.y = b->f[actor].y;
    }
    if (b->on_event) b->on_event(&ev);
}

static uint8_t who_is_at(const apb_battle *b, uint8_t x, uint8_t y)
{
    uint8_t i;

    for (i = 0; i < b->count; ++i) {
        if (b->f[i].state == APB_IN_FIGHT && b->f[i].x == x && b->f[i].y == y) return i;
    }
    return APB_NOBODY;
}

void apb_battle_init(apb_battle *b, uint8_t w, uint8_t h, apb_rng *rng,
                     void (*on_event)(const apb_event *e))
{
    memset(b, 0, sizeof(*b));
    b->w = (uint8_t)(w > APB_MAP_W_MAX ? APB_MAP_W_MAX : w);
    b->h = (uint8_t)(h > APB_MAP_H_MAX ? APB_MAP_H_MAX : h);
    b->rng = rng;
    b->on_event = on_event;
}

uint8_t apb_battle_add(apb_battle *b, const apb_fighter *f)
{
    if (b->count >= APB_FIGHTERS_MAX || f->x >= b->w || f->y >= b->h
        || apb_tile_cost(b->tile[f->y][f->x]) == 0 || who_is_at(b, f->x, f->y) != APB_NOBODY) {
        return APB_NOBODY;
    }
    memcpy(&b->f[b->count], f, sizeof(*f));
    b->f[b->count].state = APB_IN_FIGHT;
    if (b->f[b->count].health > b->f[b->count].health_max) {
        b->f[b->count].health = b->f[b->count].health_max;
    }
    return b->count++;
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

void apb_battle_start(apb_battle *b, uint8_t surprise)
{
    uint8_t i;
    uint8_t j;
    uint8_t t;
    apb_fighter *p;
    apb_fighter *q;

    /* Highest Grace first; travelers before foes on a tie; then the order they joined. */
    for (i = 0; i < b->count; ++i) b->order[i] = i;
    for (i = 1; i < b->count; ++i) {
        for (j = i; j > 0; --j) {
            p = &b->f[b->order[j - 1]];
            q = &b->f[b->order[j]];
            if (q->grace > p->grace || (q->grace == p->grace && q->side < p->side)) {
                t = b->order[j];
                b->order[j] = b->order[j - 1];
                b->order[j - 1] = t;
            } else {
                break;
            }
        }
    }
    b->surprise = surprise;
    b->round = surprise == APB_SURPRISE_NONE ? 1 : 0;
    b->next = 0;
    b->result = APB_BATTLE_ON;
}

/* ------------------------------------------------------------- the board */

/* Movement: the least it costs to reach every square, up to the fighter's speed. You
 * can't move through other fighters or into walls and pits. */
static void reach(apb_battle *b, uint8_t who)
{
    uint8_t x;
    uint8_t y;
    uint8_t d;
    uint8_t c;
    uint8_t nx;
    uint8_t ny;
    uint8_t changed = 1;
    apb_fighter *f = &b->f[who];

    memset(cost_to, 0xFF, sizeof(cost_to));
    cost_to[f->y][f->x] = 0;
    while (changed) {
        changed = 0;
        for (y = 0; y < b->h; ++y) {
            for (x = 0; x < b->w; ++x) {
                if (cost_to[y][x] == 0xFF) continue;
                for (d = 0; d < 8; ++d) {
                    nx = (uint8_t)(x + step_x[d]);
                    ny = (uint8_t)(y + step_y[d]);
                    if (nx >= b->w || ny >= b->h) continue;
                    c = apb_tile_cost(b->tile[ny][nx]);
                    if (c == 0 || who_is_at(b, nx, ny) != APB_NOBODY) continue;
                    c = (uint8_t)(cost_to[y][x] + c);
                    if (c <= f->speed && c < cost_to[ny][nx]) {
                        cost_to[ny][nx] = c;
                        changed = 1;
                    }
                }
            }
        }
    }
}

uint8_t apb_battle_can_reach(apb_battle *b, uint8_t who, uint8_t x, uint8_t y)
{
    if (who >= b->count || x >= b->w || y >= b->h) return 0;
    reach(b, who);
    return (uint8_t)(cost_to[y][x] != 0xFF);
}

/* Can a shot from x0,y0 reach x1,y1? Walls block it; so does anyone standing in
 * between (but not the shooter or the target). */
static uint8_t in_sight(const apb_battle *b, uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1,
                        uint8_t shooter)
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
            if (apb_tile_blocks_sight(b->tile[y][x])) return 0;
            who = who_is_at(b, x, y);
            if (who != APB_NOBODY && who != shooter) return 0;
        }
        e2 = (int16_t)(2 * err);
        if (e2 > -dy) { err = (int16_t)(err - dy); x = (uint8_t)(x + sx); }
        if (e2 < dx) { err = (int16_t)(err + dx); y = (uint8_t)(y + sy); }
    }
}

uint8_t apb_battle_can_attack(apb_battle *b, uint8_t who, uint8_t target, uint8_t from_x,
                              uint8_t from_y)
{
    const apb_fighter *a;
    const apb_fighter *t;

    if (who >= b->count || target >= b->count || who == target) return 0;
    a = &b->f[who];
    t = &b->f[target];
    if (t->state != APB_IN_FIGHT) return 0;
    if (a->area && dist(from_x, from_y, t->x, t->y) <= a->area) return 0;   /* the blast would catch you */
    if (!a->ranged) return (uint8_t)(dist(from_x, from_y, t->x, t->y) == 1);
    return in_sight(b, from_x, from_y, t->x, t->y, who);
}

int16_t apb_battle_tn(const apb_battle *b, uint8_t attacker, uint8_t target, uint8_t from_x,
                      uint8_t from_y)
{
    const apb_fighter *a = &b->f[attacker];
    const apb_fighter *t = &b->f[target];
    int16_t defense = a->power ? t->ward : (a->dmg_type == t->weak_type ? 0 : t->armor);
    int16_t bonus = 0;

    (void)from_x;
    (void)from_y;
    if (t->defending) bonus = (int16_t)(bonus + APB_DEFEND_BONUS);
    if (a->ranged && b->tile[t->y][t->x] == APB_TILE_COVER) bonus = (int16_t)(bonus + APB_COVER_BONUS);
    return apb_hit_tn(t->dodge, defense, bonus, 0);
}

/* ------------------------------------------------------------- outcomes */

static void check_end(apb_battle *b)
{
    uint8_t i;
    uint8_t travelers = 0;
    uint8_t foes = 0;
    uint8_t fled = 0;

    if (b->result != APB_BATTLE_ON) return;
    for (i = 0; i < b->count; ++i) {
        if (b->f[i].state == APB_IN_FIGHT) {
            if (b->f[i].side == APB_SIDE_FOE) ++foes; else ++travelers;
        } else if (b->f[i].state == APB_GONE && b->f[i].side == APB_SIDE_TRAVELER) {
            ++fled;
        }
    }
    if (foes == 0 && travelers > 0) b->result = APB_BATTLE_WON;
    else if (travelers == 0) b->result = fled ? APB_BATTLE_FLED : APB_BATTLE_LOST;
    if (b->result != APB_BATTLE_ON) emit(b, APB_EV_END, APB_NOBODY, APB_NOBODY, b->result);
}

static void hurt(apb_battle *b, uint8_t who, uint16_t dmg)
{
    apb_fighter *f = &b->f[who];

    f->health = (uint8_t)(dmg >= f->health ? 0 : f->health - dmg);
    if (f->health == 0) {
        f->state = APB_DOWN;
        emit(b, APB_EV_DOWN, APB_NOBODY, who, 0);
    } else if (f->coward && 4u * f->health <= f->health_max) {
        f->state = APB_GONE;                /* runs off */
        emit(b, APB_EV_GONE, who, APB_NOBODY, 0);
    }
}

/* One roll; for an area attack, compared with the TN of everyone in the blast. */
static void attack(apb_battle *b, uint8_t who, uint8_t target)
{
    apb_fighter *a = &b->f[who];
    int16_t bonus = 0;
    uint8_t i;
    uint8_t cx = b->f[target].x;
    uint8_t cy = b->f[target].y;
    uint8_t roll;
    uint16_t dmg;

    if (b->tile[a->y][a->x] == APB_TILE_HIGH && b->tile[cy][cx] != APB_TILE_HIGH) {
        bonus = APB_HIGH_GROUND_BONUS;
    }
    if (a->side == APB_SIDE_TRAVELER && b->f[target].opened) {
        bonus = (int16_t)(bonus + APB_HELP_BONUS);
        b->f[target].opened = 0;
    }
    roll = apb_d100(b->rng);
    for (i = 0; i < b->count; ++i) {
        if (b->f[i].state != APB_IN_FIGHT) continue;
        if (a->area ? !apb_in_area((int8_t)(b->f[i].x - cx), (int8_t)(b->f[i].y - cy), a->area)
                    : i != target) {
            continue;
        }
        shot.roll = roll;
        shot.total = (int16_t)(roll + a->attack + bonus);
        shot.tn = apb_battle_tn(b, who, i, a->x, a->y);
        shot.result = apb_resolve(roll, shot.total, shot.tn);
        dmg = apb_damage(&shot, a->weapon, a->ranged ? 0 : a->stat_bonus, b->f[i].soak);
        ev.roll = shot;
        emit(b, APB_EV_ATTACK, who, i, dmg);
        if (dmg) hurt(b, i, dmg);
    }
}

static void move_to(apb_battle *b, uint8_t who, uint8_t x, uint8_t y)
{
    apb_fighter *f = &b->f[who];

    if (f->x == x && f->y == y) return;
    f->x = x;
    f->y = y;
    emit(b, APB_EV_MOVE, who, APB_NOBODY, 0);
    if (b->tile[y][x] == APB_TILE_HAZARD) {
        emit(b, APB_EV_HAZARD, who, APB_NOBODY,
             (uint16_t)(APB_HAZARD_DAMAGE > f->soak ? APB_HAZARD_DAMAGE - f->soak : 0));
        if (APB_HAZARD_DAMAGE > f->soak) hurt(b, who, (uint16_t)(APB_HAZARD_DAMAGE - f->soak));
    }
}

static uint8_t foes_next_to(const apb_battle *b, uint8_t who)
{
    uint8_t i;
    uint8_t n = 0;

    for (i = 0; i < b->count; ++i) {
        if (b->f[i].state == APB_IN_FIGHT && b->f[i].side != b->f[who].side
            && dist(b->f[i].x, b->f[i].y, b->f[who].x, b->f[who].y) == 1) {
            ++n;
        }
    }
    return n;
}

static void flee(apb_battle *b, uint8_t who)
{
    apb_fighter *f = &b->f[who];
    uint8_t i;

    if (b->tile[f->y][f->x] == APB_TILE_EXIT) {
        shot.roll = 0;
        shot.result = APB_SUCCESS;
    } else {
        apb_check(b->rng, f->athletics, 0, apb_flee_tn(foes_next_to(b, who)), &shot);
    }
    ev.roll = shot;
    emit(b, APB_EV_FLEE, who, APB_NOBODY, shot.result);
    if (shot.result == APB_COST) {
        /* Out, but every foe next to you gets a free attack on the way. */
        for (i = 0; i < b->count && f->state == APB_IN_FIGHT; ++i) {
            if (b->f[i].state == APB_IN_FIGHT && b->f[i].side != f->side && !b->f[i].ranged
                && dist(b->f[i].x, b->f[i].y, f->x, f->y) == 1) {
                attack(b, i, who);
            }
        }
    }
    if (shot.result != APB_FAIL && f->state == APB_IN_FIGHT) {
        f->state = APB_GONE;
        emit(b, APB_EV_GONE, who, APB_NOBODY, 0);
    }
}

/* ------------------------------------------------------------- the foes */

static uint8_t nearest_traveler(const apb_battle *b, uint8_t x, uint8_t y)
{
    uint8_t i;
    uint8_t best = APB_NOBODY;
    uint8_t best_d = 0xFF;
    uint8_t d;

    for (i = 0; i < b->count; ++i) {
        if (b->f[i].state != APB_IN_FIGHT || b->f[i].side != APB_SIDE_TRAVELER) continue;
        d = dist(x, y, b->f[i].x, b->f[i].y);
        if (d < best_d) {
            best_d = d;
            best = i;
        }
    }
    return best;
}

/* The nearest traveler it can attack from x, y, or APB_NOBODY. */
static uint8_t target_from(apb_battle *b, uint8_t who, uint8_t x, uint8_t y)
{
    uint8_t i;
    uint8_t best = APB_NOBODY;
    uint8_t best_d = 0xFF;
    uint8_t d;

    for (i = 0; i < b->count; ++i) {
        if (b->f[i].side != APB_SIDE_TRAVELER || !apb_battle_can_attack(b, who, i, x, y)) continue;
        d = dist(x, y, b->f[i].x, b->f[i].y);
        if (d < best_d) {
            best_d = d;
            best = i;
        }
    }
    return best;
}

/* A shooter moves only as far as it must to get a shot: the cheapest square it can
 * reach and fire from (top-left first on a tie). Returns 0 if there's none. */
static uint8_t find_shot(apb_battle *b, uint8_t who)
{
    uint8_t x;
    uint8_t y;
    uint8_t bx = 0;
    uint8_t by = 0;
    uint8_t best = 0xFF;

    reach(b, who);
    for (y = 0; y < b->h; ++y) {
        for (x = 0; x < b->w; ++x) {
            if (cost_to[y][x] < best && target_from(b, who, x, y) != APB_NOBODY) {
                best = cost_to[y][x];
                bx = x;
                by = y;
            }
        }
    }
    if (best == 0xFF) return 0;
    move_to(b, who, bx, by);
    return 1;
}

static void foe_turn(apb_battle *b, uint8_t who)
{
    apb_fighter *f = &b->f[who];
    uint8_t target = target_from(b, who, f->x, f->y);
    uint8_t x;
    uint8_t y;
    uint8_t bx = f->x;
    uint8_t by = f->y;
    uint8_t goal;
    uint8_t d;
    uint8_t best_d;

    if (target == APB_NOBODY && f->behavior == APB_FOE_SHOOT && f->ranged && find_shot(b, who)) {
        if (f->state != APB_IN_FIGHT) return;
        target = target_from(b, who, f->x, f->y);
    }
    if (target == APB_NOBODY && f->behavior != APB_FOE_GUARD) {
        /* Close in: the reachable square nearest the nearest traveler (cheapest to get
         * to on a tie, then top-left first). */
        goal = nearest_traveler(b, f->x, f->y);
        if (goal == APB_NOBODY) return;
        reach(b, who);
        best_d = dist(f->x, f->y, b->f[goal].x, b->f[goal].y);
        for (y = 0; y < b->h; ++y) {
            for (x = 0; x < b->w; ++x) {
                if (cost_to[y][x] == 0xFF) continue;
                d = dist(x, y, b->f[goal].x, b->f[goal].y);
                if (d < best_d || (d == best_d && cost_to[y][x] < cost_to[by][bx])) {
                    best_d = d;
                    bx = x;
                    by = y;
                }
            }
        }
        move_to(b, who, bx, by);
        if (f->state != APB_IN_FIGHT) return;
        target = target_from(b, who, f->x, f->y);
    }
    if (target != APB_NOBODY) attack(b, who, target);
}

/* ------------------------------------------------------------- turns */

/* The fighter whose turn it is at order position `next`, or APB_NOBODY if they sit this
 * one out (out of the fight, or it's the other side's surprise round). */
static uint8_t turn_of(const apb_battle *b)
{
    uint8_t who = b->order[b->next];
    const apb_fighter *f = &b->f[who];

    if (f->state != APB_IN_FIGHT) return APB_NOBODY;
    if (b->round == 0 && ((b->surprise == APB_SURPRISE_FOES) != (f->side == APB_SIDE_FOE))) {
        return APB_NOBODY;
    }
    return who;
}

static void advance(apb_battle *b)
{
    b->begun = 0;
    if (++b->next >= b->count) {
        b->next = 0;
        if (b->round < 255) ++b->round;
    }
}

/* Start of a fighter's turn: defending ends, and the ground may hurt. */
static void begin_turn(apb_battle *b, uint8_t who)
{
    apb_fighter *f = &b->f[who];

    f->defending = 0;
    emit(b, APB_EV_TURN, who, APB_NOBODY, b->round);
    if (b->tile[f->y][f->x] == APB_TILE_HAZARD && APB_HAZARD_DAMAGE > f->soak) {
        emit(b, APB_EV_HAZARD, who, APB_NOBODY, (uint16_t)(APB_HAZARD_DAMAGE - f->soak));
        hurt(b, who, (uint16_t)(APB_HAZARD_DAMAGE - f->soak));
    }
}

uint8_t apb_battle_next(apb_battle *b)
{
    uint8_t who;
    uint8_t guard;

    /* Bounded: a round can't have more turns than fighters. */
    for (guard = 0; guard < 255; ++guard) {
        check_end(b);
        if (b->result != APB_BATTLE_ON) return APB_NOBODY;
        who = turn_of(b);
        if (who == APB_NOBODY) {
            advance(b);
            continue;
        }
        if (b->f[who].side == APB_SIDE_TRAVELER) {
            /* A refused action leaves it their turn; don't start it twice. */
            if (!b->begun) {
                begin_turn(b, who);
                b->begun = 1;
            }
            if (b->f[who].state == APB_IN_FIGHT) return who;
            advance(b);
            continue;
        }
        begin_turn(b, who);
        if (b->f[who].state == APB_IN_FIGHT) foe_turn(b, who);
        advance(b);
    }
    return APB_NOBODY;
}

uint8_t apb_battle_act(apb_battle *b, uint8_t who, const apb_action *a)
{
    apb_fighter *f;
    uint8_t ok = 1;

    if (b->result != APB_BATTLE_ON || who >= b->count || b->order[b->next] != who) return 0;
    f = &b->f[who];
    if (a->move_x != f->x || a->move_y != f->y) {
        if (!apb_battle_can_reach(b, who, a->move_x, a->move_y)) return 0;
    }
    switch (a->kind) {
    case APB_ACT_ATTACK:
        ok = apb_battle_can_attack(b, who, a->target, a->move_x, a->move_y);
        break;
    case APB_ACT_HELP:
        ok = (uint8_t)(a->target < b->count && b->f[a->target].state == APB_IN_FIGHT
                       && b->f[a->target].side != f->side
                       && dist(a->move_x, a->move_y, b->f[a->target].x, b->f[a->target].y) == 1);
        break;
    case APB_ACT_DEFEND:
    case APB_ACT_FLEE:
    case APB_ACT_WAIT:
        break;
    default:
        ok = 0;
    }
    if (!ok) return 0;

    move_to(b, who, a->move_x, a->move_y);
    if (f->state == APB_IN_FIGHT) {
        if (a->kind == APB_ACT_ATTACK) {
            attack(b, who, a->target);
        } else if (a->kind == APB_ACT_DEFEND) {
            f->defending = 1;
            emit(b, APB_EV_DEFEND, who, APB_NOBODY, 0);
        } else if (a->kind == APB_ACT_HELP) {
            b->f[a->target].opened = 1;
            emit(b, APB_EV_HELP, who, a->target, 0);
        } else if (a->kind == APB_ACT_FLEE) {
            flee(b, who);
        }
    }
    advance(b);
    check_end(b);
    return 1;
}
