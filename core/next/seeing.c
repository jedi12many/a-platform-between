#include "apb_seeing.h"

/*
 * Seeing and being seen (docs/open-floors.md): the rules lab's. A check is the core roll
 * (apb_resolve); a party is a group. See apb_seeing.h.
 */

#define OPEN_TN   80     /* Easy: not sneaking, not hiding */
#define HELP      10     /* what each of a group's others moves the TN */

uint8_t apb_see_dist(uint8_t ax, uint8_t ay, uint8_t bx, uint8_t by)
{
    uint8_t dx = (uint8_t)(ax > bx ? ax - bx : bx - ax);
    uint8_t dy = (uint8_t)(ay > by ? ay - by : by - ay);

    return dx > dy ? dx : dy;
}

uint8_t apb_sight(const uint8_t *tiles, uint8_t w, uint8_t ax, uint8_t ay, uint8_t bx, uint8_t by)
{
    int16_t dx = (int16_t)(bx > ax ? bx - ax : ax - bx);
    int16_t dy = (int16_t)(by > ay ? by - ay : ay - by);
    int8_t sx = (int8_t)(ax < bx ? 1 : -1);
    int8_t sy = (int8_t)(ay < by ? 1 : -1);
    int16_t err = (int16_t)(dx - dy);
    int16_t e2;
    uint8_t x = ax;
    uint8_t y = ay;
    uint8_t cover = APB_SIGHT_CLEAR;
    uint8_t t;

    for (;;) {
        if (x == bx && y == by) return cover;
        if (!(x == ax && y == ay)) {
            t = tiles[(uint16_t)y * w + x];
            if (t == APB_TILE_WALL) return APB_SIGHT_BLOCKED;
            if (t == APB_TILE_COVER) cover = APB_SIGHT_COVER;
        }
        e2 = (int16_t)(2 * err);
        if (e2 > -dy) { err = (int16_t)(err - dy); x = (uint8_t)(x + sx); }
        if (e2 < dx) { err = (int16_t)(err + dx); y = (uint8_t)(y + sy); }
    }
}

uint8_t apb_sight_range(uint8_t notice, uint8_t light)
{
    uint8_t r = (uint8_t)(notice / 5);

    if (light == APB_LIGHT_DAY) r = (uint8_t)(r * 2);
    else if (light == APB_LIGHT_NIGHT) r = (uint8_t)(r / 2);
    return r ? r : 1;
}

int16_t apb_see_mods(uint8_t light, uint8_t d, uint8_t sight, uint8_t in_cover, uint8_t alert,
                     uint8_t carried_light, uint8_t *flags, int16_t *dist_mod)
{
    int16_t m = 0;
    uint8_t f = 0;

    *dist_mod = 0;
    if (light == APB_LIGHT_DUSK) { f |= APB_SEE_DUSK; m += 10; }
    else if (light == APB_LIGHT_NIGHT) { f |= APB_SEE_NIGHT; m += 20; }
    if (d >= 8) {
        *dist_mod = (int16_t)(10 * ((d - 4) / 4));
        f |= APB_SEE_FAR;
        m += *dist_mod;
    }
    if (sight == APB_SIGHT_COVER) { f |= APB_SEE_BETWEEN; m += 20; }
    if (in_cover) { f |= APB_SEE_IN_COVER; m += 10; }
    if (alert) { f |= APB_SEE_ALERT; m -= 20; }
    if (carried_light && light == APB_LIGHT_NIGHT) { f |= APB_SEE_LIGHT; m -= 20; }
    *flags = f;
    return m;
}

/* What one of a group's others does to the TN, looking: a success takes 10 off (a crit
 * 20), a fail puts 10 on (a natural 01, 20); sneaking, the other way round. */
static int8_t helper_shift(uint8_t roll, uint8_t result, uint8_t sneaking)
{
    int8_t v;

    if (roll <= 1) v = 2 * HELP;
    else if (result == APB_FAIL) v = HELP;
    else if (result == APB_COST) v = 0;
    else if (result == APB_CRIT) v = -2 * HELP;
    else v = -HELP;
    return (int8_t)(sneaking ? -v : v);
}

/* The first of the highest. */
static uint8_t best(const uint8_t *r, uint8_t n)
{
    uint8_t i, b = 0;

    for (i = 1; i < n; ++i) {
        if (r[i] > r[b]) b = i;
    }
    return b;
}

static void help_roll(apb_rng *rng, apb_see_help *h, uint8_t rating, int16_t tn, uint8_t sneaking)
{
    h->roll = apb_d100(rng);
    h->rating = rating;
    h->tn = tn;
    h->result = apb_resolve(h->roll, (int16_t)(h->roll + rating), tn);
    h->shift = helper_shift(h->roll, h->result, sneaking);
}

static uint8_t tile_at(const apb_seeing *s, uint8_t x, uint8_t y)
{
    return s->tiles[(uint16_t)y * s->w + x];
}

/* The party looks at band b, d away along a line `sight`. */
static void party_looks(apb_seeing *s, apb_rng *rng, uint8_t b, uint8_t d, uint8_t sight,
                        apb_see_event *e)
{
    apb_see_band *k = &s->band[b];
    uint8_t i, top = best(s->notice, s->n);
    int16_t tn;

    e->base_rating = k->hiding ? k->stealth : 0;
    e->base = (int16_t)(k->hiding ? APB_TN_BASE + k->stealth : OPEN_TN);
    e->shift = 0;
    e->tn = (int16_t)(e->base + apb_see_mods(s->light, d, sight,
                                             (uint8_t)(tile_at(s, k->x, k->y) == APB_TILE_COVER),
                                             0, 0, &e->mods, &e->dist_mod));
    tn = e->tn;
    e->n_sneak = 0;
    e->n_help = 0;
    for (i = 0; i < s->n; ++i) {
        if (i == top) continue;
        help_roll(rng, &e->help[e->n_help], s->notice[i], tn, 0);
        tn = (int16_t)(tn + e->help[e->n_help].shift);
        ++e->n_help;
    }
    e->rating = s->notice[top];
    apb_check(rng, e->rating, 0, tn, &e->look);
    if (e->look.result >= APB_SUCCESS) {
        e->outcome = APB_SEE_SPOTTED;
        k->spotted = 1;
    } else {
        e->outcome = (uint8_t)(e->look.result == APB_COST ? APB_SEE_HEARD : APB_SEE_NOT_YET);
    }
}

/* Band b looks at the party, d away along a line `sight`, the leader at (x, y). */
static void band_looks(apb_seeing *s, apb_rng *rng, uint8_t b, uint8_t d, uint8_t sight,
                       uint8_t x, uint8_t y, apb_see_event *e)
{
    apb_see_band *k = &s->band[b];
    uint8_t i, top;

    e->n_sneak = 0;
    e->n_help = 0;
    e->shift = 0;
    if (s->sneaking) {
        top = best(s->stealth, s->n);
        e->base_rating = s->stealth[top];
        e->base = (int16_t)(APB_TN_BASE + s->stealth[top]);
        for (i = 0; i < s->n; ++i) {
            if (i == top) continue;
            help_roll(rng, &e->sneak[e->n_sneak], s->stealth[i], APB_TN_NORMAL, 1);
            e->shift = (int16_t)(e->shift + e->sneak[e->n_sneak].shift);
            ++e->n_sneak;
        }
    } else {
        e->base_rating = 0;
        e->base = OPEN_TN;
    }
    e->tn = (int16_t)(e->base + e->shift +
                      apb_see_mods(s->light, d, sight, (uint8_t)(tile_at(s, x, y) == APB_TILE_COVER),
                                   k->alert, s->carried_light, &e->mods, &e->dist_mod));
    e->rating = k->sense;
    apb_check(rng, e->rating, 0, e->tn, &e->look);
    if (e->look.result >= APB_SUCCESS) {
        e->outcome = APB_SEE_SEEN;
        k->seen = 1;
    } else if (e->look.result == APB_COST) {
        e->outcome = APB_SEE_HEARD;
        k->alert = 1;
    } else {
        e->outcome = APB_SEE_NOT_YET;
    }
}

uint8_t apb_seeing_step(apb_seeing *s, apb_rng *rng, uint8_t x, uint8_t y, apb_see_event *ev)
{
    uint8_t b, d, line, n = 0;
    apb_see_band *k;
    apb_see_event *e;

    for (b = 0; b < s->bands; ++b) {
        k = &s->band[b];
        d = apb_see_dist(x, y, k->x, k->y);
        line = apb_sight(s->tiles, s->w, x, y, k->x, k->y);
        /* The party looks. */
        if (!k->spotted && line != APB_SIGHT_BLOCKED &&
            d <= apb_sight_range(s->notice[best(s->notice, s->n)], s->light)) {
            if (d <= 1 || k->party_last == APB_SEE_NONE || (uint16_t)d + 4 <= k->party_last) {
                e = &ev[n++];
                e->kind = APB_SEE_PARTY_LOOKS;
                e->band = b;
                e->d = d;
                e->automatic = (uint8_t)(d <= 1);
                if (e->automatic) {
                    k->spotted = 1;
                    e->outcome = APB_SEE_SPOTTED;
                } else {
                    k->party_last = d;
                    party_looks(s, rng, b, d, line, e);
                }
            }
        }
        /* The band looks back. */
        if (line != APB_SIGHT_BLOCKED && d <= apb_sight_range(k->sense, s->light)) {
            if (d <= 1 || k->band_last == APB_SEE_NONE || (uint16_t)d + 4 <= k->band_last) {
                e = &ev[n++];
                e->kind = APB_SEE_BAND_LOOKS;
                e->band = b;
                e->d = d;
                e->automatic = (uint8_t)(d <= 1);
                if (e->automatic) {
                    k->seen = 1;
                    e->outcome = APB_SEE_SEEN;
                } else {
                    k->band_last = d;
                    band_looks(s, rng, b, d, line, x, y, e);
                }
            }
        }
        if (k->seen) {
            s->fight = (uint8_t)(b + 1);
            s->ambush = (uint8_t)!k->spotted;
            return n;
        }
    }
    return n;
}
