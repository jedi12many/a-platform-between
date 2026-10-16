/*
 * The rules lab's seeing (core/next/seeing.c) on an approach, its log as
 * tools/rules/seeing.py writes it, for tests/seeing/run_seeing.py. A case on stdin, as
 * numbers (run_seeing.py writes them):
 *
 *   seed light w h sneaking carried_light travelers bands steps
 *   h rows of w digits (the battle's terrain)
 *   a line each traveler: stealth notice
 *   a line each band: x y sense stealth hiding
 *   a line each step: x y (the first, where the party starts)
 */
#include <stdio.h>
#include <stdlib.h>

#include "apb_seeing.h"

static const char *const result_names[4] = { "fail", "cost", "success", "crit" };
static const char *const light_names[3] = { "day", "dusk", "night" };

static uint8_t tiles[64 * 128];
static apb_seeing s;
static apb_see_event ev[2 * APB_SEE_BANDS_MAX];

static unsigned num(void)
{
    unsigned v;

    if (scanf("%u", &v) != 1) exit(2);
    return v;
}

static void mods(const apb_see_event *e)
{
    if (e->mods & APB_SEE_DUSK) printf(" +10 dusk");
    if (e->mods & APB_SEE_NIGHT) printf(" +20 night");
    if (e->mods & APB_SEE_FAR) printf(" +%d distance", e->dist_mod);
    if (e->mods & APB_SEE_BETWEEN) printf(" +20 cover between");
    if (e->mods & APB_SEE_IN_COVER) printf(" +10 in cover");
    if (e->mods & APB_SEE_ALERT) printf(" -20 alert");
    if (e->mods & APB_SEE_LIGHT) printf(" -20 a light");
}

static void help_line(const char *what, const char *rating, const apb_see_help *h)
{
    printf("    %s: %s %u rolls %u = %d against %d: %s, %+d\n", what, rating, h->rating, h->roll,
           h->roll + h->rating, h->tn, result_names[h->result], h->shift);
}

static void show(const apb_see_event *e)
{
    const apb_see_band *k = &s.band[e->band];
    uint8_t i;

    printf("  band %u at %u,%u, %u away: ", e->band + 1, k->x, k->y, e->d);
    if (e->kind == APB_SEE_PARTY_LOOKS) {
        if (e->automatic) {
            printf("the party looks: spotted, no roll\n");
            return;
        }
        printf("the party looks\n");
        if (k->hiding) printf("    TN 50 + %u hiding", e->base_rating);
        else printf("    TN 80 open");
        mods(e);
        printf(" = %d\n", e->tn);
        for (i = 0; i < e->n_help; ++i) help_line("helping", "Notice", &e->help[i]);
        printf("    looks: Notice %u rolls %u = %d against %d: %s: %s\n", e->rating, e->look.roll,
               e->look.total, e->look.tn, result_names[e->look.result],
               e->outcome == APB_SEE_SPOTTED ? "spotted" : e->outcome == APB_SEE_HEARD ? "heard"
                                                                                        : "not yet");
        return;
    }
    if (e->automatic) {
        printf("band %u looks: seen, no roll\n", e->band + 1);
        return;
    }
    printf("band %u looks\n", e->band + 1);
    for (i = 0; i < e->n_sneak; ++i) help_line("sneaking", "Stealth", &e->sneak[i]);
    if (s.sneaking) {
        printf("    TN 50 + %u sneaking", e->base_rating);
        if (s.n > 1) printf(" %+d the others", e->shift);
    } else {
        printf("    TN 80 walking");
    }
    mods(e);
    printf(" = %d\n", e->tn);
    printf("    looks: Sense %u rolls %u = %d against %d: %s: %s\n", e->rating, e->look.roll,
           e->look.total, e->look.tn, result_names[e->look.result],
           e->outcome == APB_SEE_SEEN ? "seen" : e->outcome == APB_SEE_HEARD ? "heard: alert"
                                                                            : "not yet");
}

int main(void)
{
    apb_rng rng;
    unsigned seed, steps, step, i, x, y, n;
    int c;

    seed = num();
    s.light = (uint8_t)num();
    s.w = (uint8_t)num();
    s.h = (uint8_t)num();
    s.sneaking = (uint8_t)num();
    s.carried_light = (uint8_t)num();
    s.n = (uint8_t)num();
    s.bands = (uint8_t)num();
    steps = num();
    if ((unsigned)s.w * s.h > sizeof(tiles) || s.n < 1 || s.n > APB_SEE_PARTY_MAX ||
        s.bands > APB_SEE_BANDS_MAX) return 2;
    for (i = 0; i < (unsigned)s.w * s.h; ++i) {
        do {
            c = getchar();
        } while (c == ' ' || c == '\n' || c == '\r');
        if (c < '0' || c > '7') return 2;
        tiles[i] = (uint8_t)(c - '0');
    }
    s.tiles = tiles;
    for (i = 0; i < s.n; ++i) {
        s.stealth[i] = (uint8_t)num();
        s.notice[i] = (uint8_t)num();
    }
    for (i = 0; i < s.bands; ++i) {
        s.band[i].x = (uint8_t)num();
        s.band[i].y = (uint8_t)num();
        s.band[i].sense = (uint8_t)num();
        s.band[i].stealth = (uint8_t)num();
        s.band[i].hiding = (uint8_t)num();
        s.band[i].party_last = APB_SEE_NONE;
        s.band[i].band_last = APB_SEE_NONE;
    }
    apb_rng_seed(&rng, (uint16_t)seed);
    printf("light %s; the party %s%s\n", light_names[s.light], s.sneaking ? "sneaks" : "walks",
           s.carried_light ? ", carrying a light" : "");
    for (step = 0; step < steps; ++step) {
        x = num();
        y = num();
        n = apb_seeing_step(&s, &rng, (uint8_t)x, (uint8_t)y, ev);
        if (n) printf("step %u: the party at %u,%u\n", step, x, y);
        for (i = 0; i < n; ++i) show(&ev[i]);
        if (s.fight) {
            printf("the fight: band %u%s\n", s.fight, s.ambush ? ", an ambush" : "");
            return 0;
        }
    }
    printf("the end of the way: not seen\n");
    return 0;
}
