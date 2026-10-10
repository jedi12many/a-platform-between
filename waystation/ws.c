/*
 * The Waystation website's rules (milestone W1, docs/waystation-web.md): the rules core,
 * compiled to WebAssembly, so the site makes characters, reads and edits Passports and
 * applies Travel Stamps with exactly the code a C64 runs. waystation/site/app.js calls
 * these; each returns JSON (ASCII, in a static buffer) describing what happened.
 *
 * The site holds one character at a time, "the traveler": made by ws_create, or loaded
 * from a Passport by ws_load; ws_raise_* spend its points and ws_stamp applies a Travel
 * Stamp to it. ws_traveler describes it, with its new Passport.
 *
 * Plain C99, built only with Emscripten (`make waystation`).
 */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include <emscripten.h>

#include "apb.h"

static apb_character traveler;
static int have_traveler;
static char json[4096];
static size_t used;
static char password[APB_PASSWORD_BUF];

static void put(const char *fmt, ...)
{
    va_list ap;
    int n;

    va_start(ap, fmt);
    n = vsnprintf(json + used, sizeof(json) - used, fmt, ap);
    va_end(ap);
    if (n > 0) used += (size_t)n < sizeof(json) - used ? (size_t)n : sizeof(json) - used - 1;
}

static const char *refused(uint8_t err, uint8_t line)
{
    static const char *const why[] = {
        "ok", "a value doesn't fit", "it's the wrong length",
        "a character that isn't one of the symbols", "a typo", "the checksum doesn't match",
        "it was made by a newer version of the game"
    };

    used = 0;
    put("{\"ok\":false,\"error\":\"%s\",\"line\":%u}", err < 7 ? why[err] : "it can't be read", line);
    return json;
}

static void put_list(const char *key, const uint16_t *items, uint8_t n)
{
    uint8_t i;

    put("\"%s\":[", key);
    for (i = 0; i < n; ++i) put(i ? ",%u" : "%u", items[i]);
    put("]");
}

/* The traveler: everything on the sheet, worked out by the rules core. */
EMSCRIPTEN_KEEPALIVE const char *ws_traveler(void)
{
    uint8_t i;
    uint8_t rating;

    if (!have_traveler) return refused(APB_PP_LENGTH, 0);
    if (apb_passport_encode(&traveler, password) != APB_PP_OK) password[0] = '\0';
    used = 0;
    put("{\"ok\":true,\"name\":\"%s\",\"race\":%u,\"class\":%u,\"level\":%u,\"xp\":%u,",
        traveler.name, traveler.race, traveler.cls, traveler.level, traveler.xp);
    put("\"stats\":[");
    for (i = 0; i < APB_STAT_COUNT; ++i) put(i ? ",%u" : "%u", traveler.stat[i]);
    put("],\"skills\":[");
    for (i = 0; i < APB_SKILL_COUNT; ++i) {
        rating = apb_skill(&traveler, i);
        put("%s{\"rating\":%u,\"training\":%u,\"tagged\":%s,\"cost\":%u}", i ? "," : "", rating,
            traveler.training[i], (traveler.tags >> i) & 1 ? "true" : "false",
            apb_skill_raise_cost(rating));
    }
    put("],\"stat_points\":%u,\"skill_points\":%u,\"debt\":%u,\"flags\":%u,",
        traveler.stat_points, traveler.skill_points, traveler.debt, traveler.flags);
    put("\"health\":%u,\"dodge\":%u,\"speed\":%u,\"armor\":%u,\"melee_bonus\":%u,"
        "\"skill_points_per_level\":%u,",
        apb_health_max(&traveler), apb_dodge(&traveler), apb_speed(&traveler),
        apb_armor(&traveler), apb_melee_bonus(&traveler), apb_skill_points_per_level(&traveler));
    put_list("equipped", traveler.equipped, APB_EQUIP_SLOTS);
    put(",");
    put_list("pack", traveler.pack, APB_PACK_SLOTS);
    put(",\"powers\":[");
    for (i = 0; i < APB_POWER_SLOTS && traveler.power[i].id; ++i) {
        put("%s[%u,%u]", i ? "," : "", traveler.power[i].id, traveler.power[i].rank);
    }
    put("],\"echoes\":[");
    for (i = 0; i < APB_ECHO_SLOTS && traveler.echo[i].id; ++i) {
        put("%s[%u,%u]", i ? "," : "", traveler.echo[i].id, traveler.echo[i].state);
    }
    put("],\"passport\":\"%s\"}", password);
    return json;
}

/* A new level-1 traveler. `rolled`: the stats were rolled (15..90 each, arranged as the
 * player liked) rather than bought (APB_BUY_POINTS spent, APB_BUY_BASE..APB_BUY_MAX). */
EMSCRIPTEN_KEEPALIVE const char *ws_create(const char *name, int race, int cls, int s0, int s1,
                                           int s2, int s3, int s4, int s5, int tag, int rolled)
{
    uint8_t base[APB_STAT_COUNT];
    int in[APB_STAT_COUNT];
    int i;
    apb_character made;

    in[0] = s0; in[1] = s1; in[2] = s2; in[3] = s3; in[4] = s4; in[5] = s5;
    used = 0;
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        if (in[i] < (rolled ? 15 : APB_BUY_BASE) || in[i] > (rolled ? 90 : APB_BUY_MAX)) {
            put("{\"ok\":false,\"error\":\"a stat is out of range\"}");
            return json;
        }
        base[i] = (uint8_t)in[i];
    }
    if (!rolled && !apb_pointbuy_valid(base)) {
        put("{\"ok\":false,\"error\":\"spend exactly %u points\"}", APB_BUY_POINTS);
        return json;
    }
    if (race < 0 || race >= APB_RACE_COUNT || cls < 0 || cls >= APB_CLASS_COUNT) {
        put("{\"ok\":false,\"error\":\"pick a race and a class\"}");
        return json;
    }
    if (!name[0] || tag < 0 || tag > 255
        || !apb_character_create(&made, name, (uint8_t)race, (uint8_t)cls, base, (uint8_t)tag)) {
        put("{\"ok\":false,\"error\":\"%s\"}", name[0] ? "tag a skill your class doesn't" : "name your traveler");
        return json;
    }
    traveler = made;
    have_traveler = 1;
    return ws_traveler();
}

/* Six rolled stats (3d6 x 5 each), from the page's seed. */
EMSCRIPTEN_KEEPALIVE const char *ws_roll(unsigned seed)
{
    apb_rng rng;
    uint8_t out[APB_STAT_COUNT];
    int i;

    apb_rng_seed(&rng, (uint16_t)seed);
    apb_roll_stats(&rng, out);
    used = 0;
    put("[");
    for (i = 0; i < APB_STAT_COUNT; ++i) put(i ? ",%u" : "%u", out[i]);
    put("]");
    return json;
}

EMSCRIPTEN_KEEPALIVE const char *ws_load(const char *text)
{
    apb_character ch;
    uint8_t line = 0;
    uint8_t err = apb_passport_decode(text, &ch, &line);

    if (err != APB_PP_OK) return refused(err, line);
    traveler = ch;
    have_traveler = 1;
    return ws_traveler();
}

/* Spend a stat point, or skill points: 1 if it was spent. */
EMSCRIPTEN_KEEPALIVE int ws_raise_stat(int stat)
{
    return have_traveler && stat >= 0 && stat < APB_STAT_COUNT && apb_raise_stat(&traveler, (uint8_t)stat);
}

EMSCRIPTEN_KEEPALIVE int ws_raise_skill(int skill)
{
    return have_traveler && skill >= 0 && skill < APB_SKILL_COUNT
        && apb_raise_skill(&traveler, (uint8_t)skill);
}

/* Apply a Travel Stamp to the traveler. With no server to remember the tickets it
 * issued, the static site takes the stamp on trust (W2 checks it); `rewind` as the
 * player says. Returns the receipt and what landing it did. */
EMSCRIPTEN_KEEPALIVE const char *ws_stamp(const char *text, int rewind)
{
    static apb_receipt r;
    static apb_applied out;
    uint8_t line = 0;
    uint8_t err;
    uint8_t i;

    if (!have_traveler) return refused(APB_PP_LENGTH, 0);
    err = apb_stamp_decode(text, &r, &line);
    if (err != APB_PP_OK) return refused(err, line);
    apb_receipt_apply(&traveler, &r, (uint8_t)(rewind != 0), &out);
    used = 0;
    put("{\"ok\":true,\"departure\":%u,\"ticket\":%lu,\"outcome\":%u,\"xp\":%u,\"debt_paid\":%u,"
        "\"debt_added\":%u,", r.departure, (unsigned long)r.ticket, r.outcome, r.xp, r.debt_paid,
        r.debt_added);
    put_list("gained", r.gained, r.gained_count);
    put(",");
    put_list("lost", r.lost, r.lost_count);
    put(",\"echoes\":[");
    for (i = 0; i < r.echo_count; ++i) {
        put("%s[%u,%u,%u]", i ? "," : "", r.echoes[i].id, r.echoes[i].state, r.echoes[i].was);
    }
    put("],\"levels\":%u,\"gone\":%u,", out.levels, out.gone);
    put_list("stored", out.stored, out.stored_count);
    put(",");
    put_list("shifted", out.shifted, out.shifted_count);
    put(",\"legend\":[");
    for (i = 0; i < out.legend_count; ++i) {
        put("%s[%u,%u]", i ? "," : "", out.legend[i].id, out.legend[i].state);
    }
    put("]}");
    return json;
}

/* A Boarding Pass for the loaded traveler (docs/boarding.md): the platform page issues
 * one when they board from Your travelers, and keeps the ticket to know the stamp that
 * comes back. The ticket comes in two halves, as JavaScript's numbers are doubles. */
EMSCRIPTEN_KEEPALIVE const char *ws_issue(int departure, unsigned ticket_hi, unsigned ticket_lo,
                                          unsigned seed, int rewind)
{
    static char issued[APB_PASS_BUF];
    apb_pass pass;

    if (!have_traveler) return "";
    pass.departure = (uint16_t)departure;
    pass.ticket = ((uint32_t)(ticket_hi & 0xFFFFu) << 16) | (ticket_lo & 0xFFFFu);
    pass.seed = (uint16_t)seed;
    pass.rewind = (uint8_t)(rewind != 0);
    if (apb_pass_encode(&pass, &traveler, issued) != APB_PP_OK) return "";
    return issued;
}

/* The creation rules' numbers, for the creator's page. */
EMSCRIPTEN_KEEPALIVE const char *ws_rules(void)
{
    uint8_t i;

    used = 0;
    put("{\"buy_base\":%u,\"buy_points\":%u,\"buy_max\":%u,\"rerolls\":%u,\"race_bonus\":%u,"
        "\"class_bonus\":%u,\"tag_bonus\":%u,\"name_len\":%u,\"class_tags\":[",
        APB_BUY_BASE, APB_BUY_POINTS, APB_BUY_MAX, APB_REROLLS, APB_RACE_BONUS,
        APB_CLASS_BONUS, APB_TAG_BONUS, APB_NAME_LEN);
    for (i = 0; i < APB_CLASS_COUNT; ++i) {
        put("%s[%u,%u]", i ? "," : "", apb_class_tags[i][0], apb_class_tags[i][1]);
    }
    put("]}");
    return json;
}
