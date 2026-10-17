/*
 * The native arena's rules (docs/arena.md, "The native arena"): the rules lab's battle
 * engine (core/next/battle.c: rules v1, docs/turn.md) compiled to WebAssembly, for
 * tools/arena/web/arena.js to play a
 * fight by hand in a modern page. No story, no Boarding Pass, no Travel Stamp: a fight,
 * set up from a scenario, turn by turn.
 *
 * Each call returns JSON (ASCII, in a static buffer): what happened since the last call
 * (the events, in order) and the state of the fight now.
 *
 *   ar_begin(seed, spec)      set up a fight; spec is lines:
 *                               map W H, then H rows (docs/combat.md's squares)
 *                               hazard DAMAGE TYPE COND (kinetic.. or none; a condition's
 *                                   name, or -)
 *                               traveler X Y PASSPORT WEAPON_ITEM
 *                               foe X Y HEALTH GRACE DODGE ARMOR WARD SOAK SPEED ATTACK
 *                                   WEAPON RANGED POWER TYPE AREA WEAK BEHAVIOR COWARD
 *                                   [hit COND] [level N]
 *   ar_next()                 play foes until it's a traveler's turn, or the end
 *   ar_reach(who)             the squares `who` can reach this turn
 *   ar_targets(who, x, y)     who `who` can attack from x, y, and the TN for each
 *   ar_dash(who, x, y)        the squares a Dash from x, y could reach
 *   ar_power(who, use, x, y)  what power `use` could be used on from x, y: fighters (with
 *                             the TN, 0 if there's no roll) and squares
 *   ar_shoves(who, x, y)      who `who` can shove from x, y, and the TN for each
 *   ar_act(who, kind, x, y, target, dx, dy, use, blink)   a turn: move to x, y (walking,
 *                             or by Blink, power blink - 1, if blink isn't 0), then
 *                             APB_ACT_* (a Dash on to dx, dy; power `use` on target, or the
 *                             square dx, dy)
 *   ar_act_first(who, kind, target, dx, dy, use)   the action before the move, from where
 *                             `who` stands (an attack, a Shove, Guard, a power not Blink);
 *                             the turn goes on, and ar_act with APB_ACT_DONE moves and ends it
 *   ar_quick(who)             the turn the computer would play for `who`
 *   ar_equip(who, slot, item) gear from the pack: slot 0 the hand (0: bare-handed), slot 1
 *                             the body (0: no armor)
 *
 * A fight's spec can also say who has the first round: `surprise travelers` (they
 * ambushed the foes) or `surprise foes`.
 *
 * Seeing and being seen on an open floor (docs/open-floors.md, Being seen: the rules
 * lab's core/next/seeing.c), for the explore prototype:
 *
 *   ar_see_begin(seed, spec)  set up a floor (seed 0: the dice go on from where they were);
 *                             spec is lines:
 *                               floor W H, then H rows of digits (the squares, APB_TILE_*)
 *                               light day|dusk|night
 *                               traveler STEALTH NOTICE        (marching order)
 *                               band X Y SENSE STEALTH HIDING [SPOTTED SEEN ALERT PARTY_LAST
 *                                   BAND_LAST]  (how it stands: carried over a rebuild)
 *   ar_see_step(x, y, sneaking, lamp)   the leader steps to x, y: the checks, as events,
 *                             and every band as it stands now; "fight" is 1 + the band that
 *                             saw the party (0: none), "ambush" whether it hadn't been spotted
 *
 * The party's rolls and the bands' come from their own dice, apart from a fight's.
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
#include "apb_seeing.h"

static apb_rng rng;
static apb_character chars[APB_FIGHTERS_MAX];
static uint16_t weapon_of[APB_FIGHTERS_MAX];
static uint8_t is_traveler[APB_FIGHTERS_MAX];
static char json[32768];
static size_t used;
static int events;                       /* events written since the last call */
static uint8_t reach[APB_MAP_H_MAX][APB_MAP_W_MAX];
static const char *const types[] = { "kinetic", "energy", "fire", "cold", "mind" };
static uint8_t cids[APB_COND_SLOTS];
static uint8_t pids[APB_POWERS_HELD];
static uint8_t pranks[APB_POWERS_HELD];
static uint8_t pleft[APB_POWERS_HELD];
static uint8_t crounds[APB_COND_SLOTS];

/* A condition by its name: the word at s (what follows it on the line doesn't count). */
static uint8_t cond_named(const char *s)
{
    uint16_t i;
    size_t n = strcspn(s, " \t\r\n");

    for (i = 1; i < apb_cond_count; ++i) {
        if (apb_conds[i].name && strlen(apb_conds[i].name) == n && strncmp(apb_conds[i].name, s, n) == 0) {
            return (uint8_t)i;
        }
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
    "turn", "move", "attack", "down", "hazard", "guard", "wait", "flee", "gone", "end", "free",
    "cond_on", "cond_off", "immune", "tick", "heal", "skip", "shake", "stand", "dash", "shove",
    "push", "slam", "fall", "thorns", "absorb", "power", "hit", "mend", "field", "shift", "random"
};
#define EVENT_KINDS 32

static void on_event(const apb_event *e)
{
    put(events++ ? ",{" : "{");
    put("\"kind\":\"%s\",\"actor\":%u,\"target\":%u,\"x\":%u,\"y\":%u,\"value\":%u,\"cond\":%u",
        e->kind < EVENT_KINDS ? event_kinds[e->kind] : "?", e->actor, e->target, e->x, e->y,
        e->value, e->cond);
    if (e->kind == APB_EV_ATTACK || e->kind == APB_EV_FLEE || e->kind == APB_EV_SHAKE
        || e->kind == APB_EV_SHOVE || e->kind == APB_EV_HIT || e->kind == APB_EV_RANDOM) {
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
    uint8_t k;
    uint8_t n;
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
            "\"type\":%u,\"area\":%u,\"weak\":%d,\"guarding\":%u,\"waited\":%u,\"level\":%u",
            f.side, f.state, f.x, f.y, f.health, f.health_max, f.grace, f.dodge, f.armor, f.ward,
            f.soak, f.speed, f.attack, f.weapon, f.stat_bonus, f.ranged, f.power, f.dmg_type,
            f.area, f.weak_type == 0xFF ? -1 : f.weak_type, f.guarding, f.waited, f.level);
        put(",\"speed_now\":%u,\"move_left\":%u,\"dodge_now\":%u,\"armor_now\":%u,"
            "\"ward_now\":%u,\"soak_now\":%u,\"conds\":[", apb_battle_speed(i),
            apb_battle_move_left(i), apb_battle_dodge(i), apb_battle_armor(i), apb_battle_ward(i),
            apb_battle_soak(i));
        n = apb_battle_conditions(i, cids, crounds);
        for (k = 0; k < n; ++k) put(k ? ",[%u,%u]" : "[%u,%u]", cids[k], crounds[k]);
        put("],\"powers\":[");
        n = apb_battle_powers(i, pids, pranks, pleft);
        for (k = 0; k < n; ++k) {
            put(k ? ",[%u,%u,%d,%u,%u]" : "[%u,%u,%d,%u,%u]", pids[k], pranks[k],
                pleft[k] == 0xFF ? -1 : pleft[k], apb_power_tier(pranks[k]), apb_battle_power_rating(i, k));
        }
        put("]");
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
        } else if (strcmp(word, "hazard") == 0) {
            static char kind[32];
            static char cond[32];
            if (sscanf(line, "%*s %d %31s %31s", &v[0], kind, cond) != 3) return refuse("bad hazard");
            apb_battle_set_hazard((uint8_t)v[0], type_named(kind), cond_named(cond));
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
        } else if (strcmp(word, "power") == 0) {
            static char pname[32];
            uint16_t id;
            if (sscanf(line, "%*s %d %31s %d", &v[0], pname, &v[1]) != 3) return refuse("bad power");
            for (id = 1; id < apb_power_count; ++id) {
                if (apb_powers[id].name && strcmp(apb_powers[id].name, pname) == 0) break;
            }
            if (id >= apb_power_count || apb_battle_learn((uint8_t)v[0], (uint8_t)id, (uint8_t)v[1]) == APB_NOBODY) {
                return refuse("bad power");
            }
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
            f.race = 0xFF;
            if (strstr(line, " hit ")) f.on_hit = cond_named(strstr(line, " hit ") + 5);
            f.level = (uint8_t)(strstr(line, " level ") ? atoi(strstr(line, " level ") + 7) : 1);
            if (apb_battle_add(&f) == APB_NOBODY) return refuse("a foe can't stand there");
        }
    }
    if (row < 0 || apb_battle_count() == 0) return refuse("no fight");
    apb_battle_start(strstr(spec, "\nsurprise travelers") ? APB_SURPRISE_TRAVELERS
                     : strstr(spec, "\nsurprise foes") ? APB_SURPRISE_FOES : APB_SURPRISE_NONE);
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

static const char *reach_reply(void)
{
    uint8_t x;
    uint8_t y;

    used = 0;
    put("{\"reach\":[");
    for (y = 0; y < apb_battle_height(); ++y) {
        put(y ? ",\"" : "\"");
        for (x = 0; x < apb_battle_width(); ++x) put("%u", reach[y][x]);
        put("\"");
    }
    put("]}");
    return json;
}

EMSCRIPTEN_KEEPALIVE
const char *ar_dash(unsigned who, unsigned x, unsigned y)
{
    apb_battle_dash_map((uint8_t)who, (uint8_t)x, (uint8_t)y, reach);
    return reach_reply();
}

EMSCRIPTEN_KEEPALIVE
const char *ar_power(unsigned who, unsigned use, unsigned x, unsigned y)
{
    static uint8_t tg[APB_FIGHTERS_MAX];
    static int16_t tn[APB_FIGHTERS_MAX];
    uint8_t n;
    uint8_t i;
    uint8_t sx;
    uint8_t sy;

    n = apb_battle_power_targets((uint8_t)who, (uint8_t)use, (uint8_t)x, (uint8_t)y, tg, tn);
    apb_battle_power_squares((uint8_t)who, (uint8_t)use, (uint8_t)x, (uint8_t)y, reach);
    used = 0;
    put("{\"targets\":[");
    for (i = 0; i < n; ++i) put(i ? ",{\"who\":%u,\"tn\":%d}" : "{\"who\":%u,\"tn\":%d}", tg[i], tn[i]);
    put("],\"squares\":[");
    for (sy = 0; sy < apb_battle_height(); ++sy) {
        put(sy ? ",\"" : "\"");
        for (sx = 0; sx < apb_battle_width(); ++sx) put("%u", reach[sy][sx]);
        put("\"");
    }
    put("]}");
    return json;
}

EMSCRIPTEN_KEEPALIVE
const char *ar_shoves(unsigned who, unsigned x, unsigned y)
{
    uint8_t i;
    int n = 0;

    used = 0;
    put("{\"targets\":[");
    for (i = 0; i < apb_battle_count(); ++i) {
        if (apb_battle_can_shove((uint8_t)who, i, (uint8_t)x, (uint8_t)y)) {
            put(n++ ? ",{" : "{");
            put("\"who\":%u,\"tn\":%d}", i, apb_battle_shove_tn((uint8_t)who, i));
        }
    }
    put("]}");
    return json;
}

EMSCRIPTEN_KEEPALIVE
const char *ar_act(unsigned who, unsigned kind, unsigned x, unsigned y, unsigned target,
                   unsigned dx, unsigned dy, unsigned use, unsigned blink)
{
    apb_action a;

    a.move_x = (uint8_t)x;
    a.move_y = (uint8_t)y;
    a.kind = (uint8_t)kind;
    a.target = (uint8_t)target;
    a.dash_x = (uint8_t)dx;
    a.dash_y = (uint8_t)dy;
    a.use = (uint8_t)use;
    a.move_use = (uint8_t)blink;    /* 0: walk; else Blink (power blink - 1) is the move */
    begin_reply();
    if (!apb_battle_act((uint8_t)who, &a)) {
        used = 0;
        put("{\"refused\":true}");
        return json;
    }
    return end_reply(APB_NOBODY);
}

EMSCRIPTEN_KEEPALIVE
const char *ar_act_first(unsigned who, unsigned kind, unsigned target, unsigned dx, unsigned dy,
                         unsigned use)
{
    apb_action a;

    a.move_x = a.move_y = a.move_use = 0;
    a.kind = (uint8_t)kind;
    a.target = (uint8_t)target;
    a.dash_x = (uint8_t)dx;
    a.dash_y = (uint8_t)dy;
    a.use = (uint8_t)use;
    begin_reply();
    if (!apb_battle_act_first((uint8_t)who, &a)) {
        used = 0;
        put("{\"refused\":true}");
        return json;
    }
    return end_reply((uint8_t)who);
}

EMSCRIPTEN_KEEPALIVE
const char *ar_quick(unsigned who)
{
    apb_action a;

    apb_battle_quick((uint8_t)who, &a);
    used = 0;
    put("{\"x\":%u,\"y\":%u,\"kind\":%u,\"target\":%u,\"dx\":%u,\"dy\":%u,\"use\":%u,\"blink\":%u}",
        a.move_x, a.move_y, a.kind, a.target, a.dash_x, a.dash_y, a.use, a.move_use);
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

/* ---------------------------------------------------------------- seeing */

#define SEE_W_MAX 96
#define SEE_H_MAX 48

static apb_rng see_rng;
static apb_seeing see;
static uint8_t see_tiles[SEE_W_MAX * SEE_H_MAX];
static apb_see_event see_ev[2 * APB_SEE_BANDS_MAX];

EMSCRIPTEN_KEEPALIVE
const char *ar_see_begin(unsigned seed, const char *spec)
{
    static char line[128];
    static char word[16];
    const char *p = spec;
    size_t n;
    int w = 0;
    int h = 0;
    int row = -1;
    int v[10];
    int k;
    apb_see_band *b;

    if (seed) apb_rng_seed(&see_rng, (uint16_t)seed);
    memset(&see, 0, sizeof(see));
    see.tiles = see_tiles;
    while (*p) {
        n = strcspn(p, "\n");
        if (n >= sizeof(line)) n = sizeof(line) - 1;
        memcpy(line, p, n);
        line[n] = '\0';
        p += strcspn(p, "\n");
        if (*p) ++p;
        if (row >= 0 && row < h) {
            if (strlen(line) < (size_t)w) return refuse("a short row");
            for (k = 0; k < w; ++k) {
                if (line[k] < '0' || line[k] > '7') return refuse("a bad square");
                see_tiles[row * w + k] = (uint8_t)(line[k] - '0');
            }
            ++row;
            continue;
        }
        if (sscanf(line, "%15s", word) != 1) continue;
        if (strcmp(word, "floor") == 0) {
            if (sscanf(line, "%*s %d %d", &w, &h) != 2 || w < 1 || h < 1 || w > SEE_W_MAX
                || h > SEE_H_MAX) {
                return refuse("bad floor");
            }
            see.w = (uint8_t)w;
            see.h = (uint8_t)h;
            row = 0;
        } else if (strcmp(word, "light") == 0) {
            see.light = strstr(line, "night") ? APB_LIGHT_NIGHT : strstr(line, "dusk") ? APB_LIGHT_DUSK
                        : APB_LIGHT_DAY;
        } else if (strcmp(word, "traveler") == 0) {
            if (see.n >= APB_SEE_PARTY_MAX || sscanf(line, "%*s %d %d", &v[0], &v[1]) != 2) {
                return refuse("bad traveler");
            }
            see.stealth[see.n] = (uint8_t)v[0];
            see.notice[see.n] = (uint8_t)v[1];
            ++see.n;
        } else if (strcmp(word, "band") == 0) {
            v[5] = v[6] = v[7] = 0;
            v[8] = v[9] = APB_SEE_NONE;
            k = sscanf(line, "%*s %d %d %d %d %d %d %d %d %d %d", &v[0], &v[1], &v[2], &v[3], &v[4],
                       &v[5], &v[6], &v[7], &v[8], &v[9]);
            if (see.bands >= APB_SEE_BANDS_MAX || (k != 5 && k != 10) || row < h
                || v[0] < 0 || v[1] < 0 || v[0] >= w || v[1] >= h) {
                return refuse("bad band");
            }
            b = &see.band[see.bands++];
            b->x = (uint8_t)v[0]; b->y = (uint8_t)v[1];
            b->sense = (uint8_t)v[2]; b->stealth = (uint8_t)v[3]; b->hiding = (uint8_t)!!v[4];
            b->spotted = (uint8_t)!!v[5]; b->seen = (uint8_t)!!v[6]; b->alert = (uint8_t)!!v[7];
            b->party_last = (uint8_t)v[8]; b->band_last = (uint8_t)v[9];
        }
    }
    if (row < 0 || row < h || see.n == 0) return refuse("no floor");
    used = 0;
    put("{\"bands\":%u}", see.bands);
    return json;
}

static void put_help(const apb_see_help *h, uint8_t n)
{
    uint8_t i;

    for (i = 0; i < n; ++i) {
        put(i ? ",{" : "{");
        put("\"roll\":%u,\"rating\":%u,\"tn\":%d,\"result\":%u,\"shift\":%d}", h[i].roll,
            h[i].rating, h[i].tn, h[i].result, h[i].shift);
    }
}

EMSCRIPTEN_KEEPALIVE
const char *ar_see_step(unsigned x, unsigned y, unsigned sneaking, unsigned lamp)
{
    uint8_t n;
    uint8_t i;
    const apb_see_event *e;
    const apb_see_band *b;

    if (!see.w || x >= see.w || y >= see.h) return refuse("no floor, or off it");
    see.sneaking = (uint8_t)!!sneaking;
    see.carried_light = (uint8_t)!!lamp;
    see.fight = 0;
    see.ambush = 0;
    n = apb_seeing_step(&see, &see_rng, (uint8_t)x, (uint8_t)y, see_ev);
    used = 0;
    put("{\"events\":[");
    for (i = 0; i < n; ++i) {
        e = &see_ev[i];
        put(i ? ",{" : "{");
        put("\"kind\":\"%s\",\"band\":%u,\"d\":%u,\"automatic\":%u,\"outcome\":%u",
            e->kind == APB_SEE_PARTY_LOOKS ? "party" : "band", e->band, e->d, e->automatic,
            e->outcome);
        if (!e->automatic) {
            put(",\"base\":%d,\"base_rating\":%u,\"shift\":%d,\"mods\":%u,\"dist_mod\":%d,"
                "\"tn\":%d,\"rating\":%u,\"roll\":%u,\"total\":%d,\"look_tn\":%d,\"result\":%u",
                e->base, e->base_rating, e->shift, e->mods, e->dist_mod, e->tn, e->rating,
                e->look.roll, e->look.total, e->look.tn, e->look.result);
            put(",\"sneak\":[");
            put_help(e->sneak, e->n_sneak);
            put("],\"help\":[");
            put_help(e->help, e->n_help);
            put("]");
        }
        put("}");
    }
    put("],\"fight\":%u,\"ambush\":%u,\"bands\":[", see.fight, see.ambush);
    for (i = 0; i < see.bands; ++i) {
        b = &see.band[i];
        put(i ? ",[%u,%u,%u,%u,%u]" : "[%u,%u,%u,%u,%u]", b->spotted, b->seen, b->alert,
            b->party_last, b->band_last);
    }
    put("]}");
    return json;
}
