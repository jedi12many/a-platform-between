/*
 * Seeing and being seen (docs/open-floors.md, Being seen): the rules lab's, beside its
 * battle engine. The looker rolls d100 + its Notice; whoever might be seen sets the TN:
 * 50 + its Stealth sneaking or hiding, 80 not; light, distance, cover and alertness move
 * it. A party is a group (its best rolls or sets the TN, the others move it 10 each).
 *
 * Same house rules as the core (apb.h). Tested against tools/rules/seeing.py by
 * tests/seeing/run_seeing.py, natively and on sim65.
 */
#ifndef APB_SEEING_H
#define APB_SEEING_H

#include "apb.h"

#define APB_SEE_PARTY_MAX   4
#define APB_SEE_BANDS_MAX   24     /* an 80 x 40 open floor has up to 19 (walkable / 150) */
#define APB_SEE_NONE        0xFF   /* a distance never checked at */

enum { APB_LIGHT_DAY = 0, APB_LIGHT_DUSK, APB_LIGHT_NIGHT };

/* The line between two squares (apb_sight). */
#define APB_SIGHT_BLOCKED   0xFF
#define APB_SIGHT_CLEAR     0
#define APB_SIGHT_COVER     1      /* a cover square on it (not either end) */

/* The TN's modifiers, as flags (apb_see_event.mods), in the doc's order. */
#define APB_SEE_DUSK        0x01
#define APB_SEE_NIGHT       0x02
#define APB_SEE_FAR         0x04   /* distance: +10 a full 4 squares past the first 4 */
#define APB_SEE_BETWEEN     0x08   /* cover on the line */
#define APB_SEE_IN_COVER    0x10   /* whoever might be seen stands in cover */
#define APB_SEE_ALERT       0x20   /* the looker is alert */
#define APB_SEE_LIGHT       0x40   /* whoever might be seen carries a light, at night */

/* What happened (apb_see_event.kind, .outcome). */
enum { APB_SEE_PARTY_LOOKS = 0, APB_SEE_BAND_LOOKS };
enum { APB_SEE_NOT_YET = 0, APB_SEE_HEARD, APB_SEE_SPOTTED, APB_SEE_SEEN };

/* One of a group's others' rolls, and what it did to the TN. */
typedef struct {
    uint8_t roll;
    uint8_t rating;
    int16_t tn;
    uint8_t result;
    int8_t  shift;
} apb_see_help;

/* A check, or a sighting with no roll (adjacent: .auto set), for the log. */
typedef struct {
    uint8_t kind;
    uint8_t band;
    uint8_t d;
    uint8_t automatic;
    int16_t base;          /* 50 + a Stealth, or 80, before the modifiers */
    uint8_t base_rating;   /* that Stealth (0 for 80) */
    int16_t shift;         /* a sneaking party's others, on the base */
    uint8_t mods;          /* APB_SEE_* */
    int16_t dist_mod;           /* the distance's part of the modifiers */
    int16_t tn;            /* base + shift + modifiers */
    uint8_t n_sneak;
    apb_see_help sneak[APB_SEE_PARTY_MAX - 1];
    uint8_t n_help;
    apb_see_help help[APB_SEE_PARTY_MAX - 1];
    uint8_t rating;        /* the looker's Notice (or Sense) */
    apb_roll look;
    uint8_t outcome;       /* APB_SEE_NOT_YET .. APB_SEE_SEEN */
} apb_see_event;

typedef struct {
    uint8_t x, y;
    uint8_t sense, stealth;
    uint8_t hiding;
    uint8_t spotted;       /* the party has spotted it */
    uint8_t seen;          /* it has seen the party */
    uint8_t alert;
    uint8_t party_last;    /* the distance at the party's last check of it (or NONE) */
    uint8_t band_last;     /* and at its last check of the party */
} apb_see_band;

typedef struct {
    const uint8_t *tiles;  /* the floor's squares, a row at a time (the battle's terrain) */
    uint8_t w, h;
    uint8_t light;
    uint8_t n;             /* travelers */
    uint8_t notice[APB_SEE_PARTY_MAX];
    uint8_t stealth[APB_SEE_PARTY_MAX];
    uint8_t sneaking;
    uint8_t carried_light;
    uint8_t bands;
    apb_see_band band[APB_SEE_BANDS_MAX];
    uint8_t fight;         /* 1 + the band that saw the party, or 0 */
    uint8_t ambush;        /* and it hadn't been spotted first */
} apb_seeing;

/* The battle's distance: the larger gap, across or down. */
uint8_t apb_see_dist(uint8_t ax, uint8_t ay, uint8_t bx, uint8_t by);

/* The line from (ax, ay) to (bx, by): APB_SIGHT_BLOCKED by a wall, APB_SIGHT_COVER if a
 * cover square's on it, APB_SIGHT_CLEAR. The battle engine's Bresenham. */
uint8_t apb_sight(const uint8_t *tiles, uint8_t w, uint8_t ax, uint8_t ay, uint8_t bx, uint8_t by);

/* Notice / 5 squares, doubled by day, halved at night, at least 1. */
uint8_t apb_sight_range(uint8_t notice, uint8_t light);

/* The modifiers' flags for a check, and their total (the distance's part in *dist_mod). */
int16_t apb_see_mods(uint8_t light, uint8_t d, uint8_t sight, uint8_t in_cover, uint8_t alert,
                     uint8_t carried_light, uint8_t *flags, int16_t *dist_mod);

/* One step of the party's leader to (x, y): every band checked, as the doc's
 * *Precisely* says. Events go to ev (at most 2 a band); returns how many. Stops (and sets
 * s->fight) when a band sees the party. */
uint8_t apb_seeing_step(apb_seeing *s, apb_rng *rng, uint8_t x, uint8_t y, apb_see_event *ev);

#endif
