/*
 * The native arena's rules (docs/arena.md, "The native arena"): the real battle engine
 * (core/src/battle.c) compiled to WebAssembly, for tools/arena/web/arena.js to play a
 * fight by hand in a modern page. No story, no Boarding Pass, no Travel Stamp: a fight,
 * set up from a scenario, turn by turn.
 *
 * Each call returns JSON (ASCII, in a static buffer): what happened since the last call
 * (the events, in order) and the state of the fight now.
 *
 *   ar_begin(seed, spec)      set up a fight; spec is lines:
 *                               map W H, then H rows (docs/combat.md's squares)
 *                               traveler X Y PASSPORT WEAPON_ITEM
 *                               foe X Y HEALTH GRACE DODGE ARMOR WARD SOAK SPEED ATTACK
 *                                   WEAPON RANGED POWER TYPE AREA WEAK BEHAVIOR COWARD
 *   ar_next()                 play foes until it's a traveler's turn, or the end
 *   ar_reach(who)             the squares `who` can reach this turn
 *   ar_targets(who, x, y)     who `who` can attack from x, y, and the TN for each
 *   ar_act(who, kind, x, y, target)    a turn: move to x, y, then APB_ACT_*
 *   ar_quick(who)             the turn the computer would play for `who`
 *   ar_equip(who, slot, item) gear from the pack: slot 0 the hand (0: bare-handed), slot 1
 *                             the body (0: no armor)
 *
 * Plain C99, built only with Emscripten (`make arena-web`).
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <emscripten.h>

#include "apb.h"
#include "apb_battle.h"

static apb_rng rng;
static apb_character chars[APB_FIGHTERS_MAX];
static uint16_t weapon_of[APB_FIGHTERS_MAX];
static uint8_t is_traveler[APB_FIGHTERS_MAX];
static char json[32768];
static size_t used;
static int events;                       /* events written since the last call */
static uint8_t reach[APB_MAP_H_MAX][APB_MAP_W_MAX];

static void put(const char *fmt, ...)
{
    va_list ap;
    int n;

    va_start(ap, fmt);
    n = vsnprintf(json + used, sizeof(json) - used, fmt, ap);
    va_end(ap);
    if (n > 0) used += (size_t)n < sizeof(json) - used ? (size_t)n : sizeof(json) - used - 1;
}

static const char *const event_kinds[] = {
    "turn", "move", "attack", "down", "hazard", "guard", "wait", "flee", "gone", "end", "free"
};

static void on_event(const apb_event *e)
{
    put(events++ ? ",{" : "{");
    put("\"kind\":\"%s\",\"actor\":%u,\"target\":%u,\"x\":%u,\"y\":%u,\"value\":%u",
        e->kind < 11 ? event_kinds[e->kind] : "?", e->actor, e->target, e->x, e->y, e->value);
    if (e->kind == APB_EV_ATTACK || e->kind == APB_EV_FLEE) {
        put(",\"roll\":%u,\"total\":%d,\"tn\":%d,\"result\":%u", e->roll.roll, e->roll.total,
            e->roll.tn, e->roll.result);
    }
    put("}");
}

static void begin_reply(void)
{
    used = 0;
    events = 0;
    put("{\"events\":[");
}

/* The fight as it is now, after the events. */
static const char *end_reply(uint8_t whose)
{
    uint8_t i;
    uint8_t x;
    uint8_t y;
    apb_fighter f;

    put("],\"round\":%u,\"result\":%u,\"whose\":%d,\"map\":[", apb_battle_round(),
        apb_battle_result(), whose == APB_NOBODY ? -1 : whose);
    for (y = 0; y < apb_battle_height(); ++y) {
        put(y ? ",\"" : "\"");
        for (x = 0; x < apb_battle_width(); ++x) put("%u", apb_battle_tile(x, y));
        put("\"");
    }
    put("],\"fighters\":[");
    for (i = 0; i < apb_battle_count(); ++i) {
        apb_battle_fighter(i, &f);
        put(i ? ",{" : "{");
        put("\"side\":%u,\"state\":%u,\"x\":%u,\"y\":%u,\"health\":%u,\"health_max\":%u,"
            "\"grace\":%u,\"dodge\":%u,\"armor\":%u,\"ward\":%u,\"soak\":%u,\"speed\":%u,"
            "\"attack\":%u,\"weapon\":%u,\"stat_bonus\":%u,\"ranged\":%u,\"power\":%u,"
            "\"type\":%u,\"area\":%u,\"weak\":%d,\"guarding\":%u,\"waited\":%u",
            f.side, f.state, f.x, f.y, f.health, f.health_max, f.grace, f.dodge, f.armor, f.ward,
            f.soak, f.speed, f.attack, f.weapon, f.stat_bonus, f.ranged, f.power, f.dmg_type,
            f.area, f.weak_type == 0xFF ? -1 : f.weak_type, f.guarding, f.waited);
        if (is_traveler[i]) {
            put(",\"item\":%u,\"armor_item\":%u,\"melee_bonus\":%u", weapon_of[i],
                chars[i].equipped[1], apb_melee_bonus(&chars[i]));
        }
        put("}");
    }
    put("]}");
    return json;
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

static const char *refuse(const char *why)
{
    used = 0;
    put("{\"error\":\"%s\"}", why);
    return json;
}

/* The fighter a traveler is with this character and weapon. */
static void make_traveler(apb_fighter *f, uint8_t i)
{
    apb_fighter_from(f, &chars[i], weapon_of[i]);
}

EMSCRIPTEN_KEEPALIVE
const char *ar_begin(unsigned seed, const char *spec)
{
    static char line[256];
    static char word[128];
    const char *p = spec;
    size_t n;
    int w = 0;
    int h = 0;
    int row = -1;
    int v[18];
    uint8_t who;
    apb_fighter f;

    apb_rng_seed(&rng, (uint16_t)seed);
    memset(is_traveler, 0, sizeof(is_traveler));
    begin_reply();
    while (*p) {
        n = strcspn(p, "\n");
        if (n >= sizeof(line)) n = sizeof(line) - 1;
        memcpy(line, p, n);
        line[n] = '\0';
        p += n;
        if (*p) ++p;
        if (row >= 0 && row < h) {
            for (n = 0; n < (size_t)w && line[n]; ++n) {
                apb_battle_set_tile((uint8_t)n, (uint8_t)row, tile_of(line[n]));
            }
            ++row;
            continue;
        }
        if (sscanf(line, "%127s", word) != 1) continue;
        if (strcmp(word, "map") == 0) {
            if (sscanf(line, "%*s %d %d", &w, &h) != 2 || w < 1 || h < 1 || w > APB_MAP_W_MAX
                || h > APB_MAP_H_MAX) {
                return refuse("bad map");
            }
            apb_battle_init((uint8_t)w, (uint8_t)h, &rng, on_event);
            row = 0;
        } else if (row < 0) {
            return refuse("the map comes first");
        } else if (strcmp(word, "traveler") == 0) {
            who = apb_battle_count();
            if (who >= APB_FIGHTERS_MAX
                || sscanf(line, "%*s %d %d %127s %d", &v[0], &v[1], word, &v[2]) != 4
                || apb_passport_decode(word, &chars[who], 0) != APB_PP_OK) {
                return refuse("bad traveler");
            }
            weapon_of[who] = (uint16_t)v[2];
            make_traveler(&f, who);
            f.x = (uint8_t)v[0];
            f.y = (uint8_t)v[1];
            if (apb_battle_add(&f) == APB_NOBODY) return refuse("a traveler can't stand there");
            is_traveler[who] = 1;
        } else if (strcmp(word, "foe") == 0) {
            if (sscanf(line, "%*s %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d",
                       &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7], &v[8], &v[9],
                       &v[10], &v[11], &v[12], &v[13], &v[14], &v[15], &v[16], &v[17]) != 18) {
                return refuse("bad foe");
            }
            memset(&f, 0, sizeof(f));
            f.side = APB_SIDE_FOE;
            f.x = (uint8_t)v[0]; f.y = (uint8_t)v[1];
            f.health = f.health_max = (uint8_t)v[2];
            f.grace = (uint8_t)v[3]; f.dodge = (uint8_t)v[4]; f.armor = (uint8_t)v[5];
            f.ward = (uint8_t)v[6]; f.soak = (uint8_t)v[7]; f.speed = (uint8_t)v[8];
            f.attack = (uint8_t)v[9]; f.weapon = (uint8_t)v[10]; f.ranged = (uint8_t)v[11];
            f.power = (uint8_t)v[12]; f.dmg_type = (uint8_t)v[13]; f.area = (uint8_t)v[14];
            f.weak_type = (uint8_t)v[15]; f.behavior = (uint8_t)v[16]; f.coward = (uint8_t)v[17];
            if (apb_battle_add(&f) == APB_NOBODY) return refuse("a foe can't stand there");
        }
    }
    if (row < 0 || apb_battle_count() == 0) return refuse("no fight");
    apb_battle_start(APB_SURPRISE_NONE);
    return end_reply(APB_NOBODY);
}

EMSCRIPTEN_KEEPALIVE
const char *ar_next(void)
{
    uint8_t who;

    begin_reply();
    who = apb_battle_next();
    return end_reply(who);
}

EMSCRIPTEN_KEEPALIVE
const char *ar_reach(unsigned who)
{
    uint8_t x;
    uint8_t y;

    used = 0;
    put("{\"reach\":[");
    if (who < apb_battle_count()) apb_battle_reach_map((uint8_t)who, reach);
    for (y = 0; y < apb_battle_height(); ++y) {
        put(y ? ",\"" : "\"");
        for (x = 0; x < apb_battle_width(); ++x) put("%u", who < apb_battle_count() ? reach[y][x] : 0);
        put("\"");
    }
    put("]}");
    return json;
}

EMSCRIPTEN_KEEPALIVE
const char *ar_targets(unsigned who, unsigned x, unsigned y)
{
    uint8_t i;
    int n = 0;
    apb_fighter f;

    used = 0;
    put("{\"targets\":[");
    for (i = 0; i < apb_battle_count(); ++i) {
        apb_battle_fighter(i, &f);
        if (i != who && f.state == APB_IN_FIGHT && f.side != APB_SIDE_TRAVELER
            && apb_battle_can_attack((uint8_t)who, i, (uint8_t)x, (uint8_t)y)) {
            put(n++ ? ",{" : "{");
            put("\"who\":%u,\"tn\":%d}", i, apb_battle_tn((uint8_t)who, i));
        }
    }
    put("]}");
    return json;
}

EMSCRIPTEN_KEEPALIVE
const char *ar_act(unsigned who, unsigned kind, unsigned x, unsigned y, unsigned target)
{
    apb_action a;

    a.move_x = (uint8_t)x;
    a.move_y = (uint8_t)y;
    a.kind = (uint8_t)kind;
    a.target = (uint8_t)target;
    begin_reply();
    if (!apb_battle_act((uint8_t)who, &a)) {
        used = 0;
        put("{\"refused\":true}");
        return json;
    }
    return end_reply(APB_NOBODY);
}

EMSCRIPTEN_KEEPALIVE
const char *ar_quick(unsigned who)
{
    apb_action a;

    apb_battle_quick((uint8_t)who, &a);
    used = 0;
    put("{\"x\":%u,\"y\":%u,\"kind\":%u,\"target\":%u}", a.move_x, a.move_y, a.kind, a.target);
    return json;
}

EMSCRIPTEN_KEEPALIVE
const char *ar_equip(unsigned who, unsigned slot, unsigned item)
{
    apb_fighter f;
    uint8_t arch;

    if (who >= APB_FIGHTERS_MAX || !is_traveler[who] || slot > 1 || item >= APB_ITEM_COUNT) {
        return refuse("can't equip that");
    }
    arch = item ? apb_items[item].archetype : 0xFF;
    if (slot == 1) {
        if (item && arch != APB_ARCH_ARMOR) return refuse("that isn't armor");
        chars[who].equipped[1] = (uint16_t)item;
    } else {
        if (item && arch != APB_ARCH_MELEE && arch != APB_ARCH_RANGED && arch != APB_ARCH_FOCUS) {
            return refuse("that isn't a weapon or a focus");
        }
        weapon_of[who] = (uint16_t)item;
        chars[who].equipped[0] = (uint16_t)item;
    }
    make_traveler(&f, (uint8_t)who);
    apb_battle_rearm((uint8_t)who, &f);
    begin_reply();
    return end_reply((uint8_t)who);
}
