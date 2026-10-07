/*
 * The Deep Yards (docs/deep-yards.md): a floor's battle map, built from the yard number,
 * the floor and a pool of foes, the same on every machine. tools/yards/yard.py is a
 * reference written from the doc; `make test-yards` checks one against the other.
 *
 * Same house rules as the rest of the core. On the C64 this is in the LOAD overlay, and
 * there's no room for buffers of its own: the caller lends it APB_YARD_WORK bytes (the
 * VM uses the free space after the depot).
 */
#include <string.h>

#include "apb.h"

#define W APB_YARD_W
#define H APB_YARD_H
#define REACHED 0x80            /* in a square: the traveler can walk there */

static const uint8_t terrain[8] = { 3, 3, 4, 4, 6, 2, 1, 5 };

/* Static, not locals: the 6502 gives a function at most 256 bytes of them. */
static apb_rng r;
static uint8_t *sq;             /* W x H squares, row by row, in the lent space */
static uint8_t *foe_at;         /* x, y of each foe placed so far               */

/* The Deep Yards (docs/deep-yards.md, "Mixing"): a number from the yard and a key, the
 * same on every machine, never from the dice. */
uint16_t apb_yard_mix(uint16_t yard, uint16_t key)
{
    apb_rng m;
    uint8_t i;

    m.state = yard ? yard : 0xACE1u;
    for (i = 0; i < 3; ++i) {
        apb_rng_next(&m);
        /* Not just xorshift: that's linear, and picks would come in fixed pairs. */
        m.state = (uint16_t)(m.state * 0x9E37u + key);
        if (!m.state) m.state = 0xACE1u;
    }
    return apb_rng_next(&m);
}

static uint8_t roll(uint8_t n)
{
    return (uint8_t)(apb_rng_next(&r) % n);
}

/* Step 4: mark every square the traveler can walk to from the start. Square by square
 * until nothing changes: slow by a computer's standards, small by a C64's. */
static void flood(uint8_t start)
{
    uint8_t changed = 1;
    uint8_t i;
    uint8_t t;

    sq[start] |= REACHED;
    while (changed) {
        changed = 0;
        for (i = W + 1; i < W * (H - 1) - 1; ++i) {
            t = sq[i];
            if ((t & REACHED) || t == 1 || t == 2) continue;
            /* The edge is wall, so it's never marked, and no square inside has a
             * neighbour off the map. */
            if ((sq[i - W - 1] | sq[i - W] | sq[i - W + 1] | sq[i - 1] | sq[i + 1]
                 | sq[i + W - 1] | sq[i + W] | sq[i + W + 1]) & REACHED) {
                sq[i] = (uint8_t)(t | REACHED);
                changed = 1;
            }
        }
    }
}

/* A square a foe may stand on (step 5). */
static uint8_t foe_ok(uint8_t x, uint8_t y, uint8_t placed)
{
    uint8_t t = sq[y * W + x];
    uint8_t i;

    if (!(t & REACHED)) return 0;
    t &= (uint8_t)~REACHED;
    if (!(t == 0 || t == 3 || t == 4 || t == 6)) return 0;
    for (i = 0; i < placed; ++i) {
        if (foe_at[2 * i] == x && foe_at[2 * i + 1] == y) return 0;
    }
    return 1;
}

uint16_t apb_yard_build(uint16_t yard, uint8_t floor, const uint8_t *pool, uint16_t pool_len,
                        uint8_t *out, uint8_t *work)
{
    uint16_t p;
    uint16_t names;
    uint16_t at;
    uint16_t v;
    uint16_t extra;
    const uint8_t *foe;
    uint8_t pool_n;
    uint8_t ey;
    uint8_t x;
    uint8_t y;
    uint8_t i;
    uint8_t j;
    uint8_t n;
    uint8_t limit;
    uint8_t kind;
    uint8_t tries;
    uint8_t found;

    sq = work;
    foe_at = work + W * H;

    /* Find the pool's foes and their names. */
    p = (uint16_t)(2 + (pool[0] * pool[1] + 1) / 2);
    p = (uint16_t)(p + 1 + 2u * pool[p]);
    pool_n = pool[p++];
    if (!pool_n || (uint16_t)(p + 18u * pool_n) > pool_len) return 0;

    if (floor == 0) floor = 1;          /* floor 0 counts as 1 */
    apb_rng_seed(&r, apb_yard_mix(yard, (uint16_t)(floor * 256u + 255u)));

    /* 1. The room: wall round the edge, open ground inside. */
    for (y = 0; y < H; ++y) {
        for (x = 0; x < W; ++x) {
            sq[y * W + x] = (uint8_t)(x == 0 || y == 0 || x == W - 1 || y == H - 1);
        }
    }
    /* 2. The way out. */
    ey = (uint8_t)(1 + roll(6));
    sq[ey * W] = 7;
    /* 3. Terrain. */
    for (i = (uint8_t)(6 + floor / 2); i; --i) {
        x = (uint8_t)(3 + roll(8));
        y = (uint8_t)(1 + roll(6));
        j = terrain[roll(8)];
        if (y == ey) continue;
        if (j == 5 && floor < 4) j = 3;
        sq[y * W + x] = j;
    }
    /* 4. Where the traveler can get to. */
    flood((uint8_t)(ey * W + 1));

    /* 6. The record: the map, then the start. */
    out[0] = W;
    out[1] = H;
    for (i = 0; i < W * H / 2; ++i) {
        out[2 + i] = (uint8_t)(((sq[2 * i] & 7) << 4) | (sq[2 * i + 1] & 7));
    }
    at = 2 + W * H / 2;
    out[at++] = 1;
    out[at++] = 1;
    out[at++] = ey;

    /* 5. The foes. */
    n = (uint8_t)(1 + (floor - 1) / 4);
    if (n > APB_YARD_FOES_MAX) n = APB_YARD_FOES_MAX;
    limit = (uint8_t)(1 + floor / 3);
    if (limit > pool_n) limit = pool_n;
    extra = (uint16_t)(floor - 1u);
    out[at++] = n;
    names = (uint16_t)(at + 18u * n);       /* where this record's names go */
    p = (uint16_t)(p + 18u * pool_n);       /* the pool's names              */
    for (i = 0; i < n; ++i) {
        kind = roll(limit);
        found = 0;
        for (tries = 0; tries < 32 && !found; ++tries) {
            x = (uint8_t)(7 + roll(4));
            y = (uint8_t)(1 + roll(6));
            found = foe_ok(x, y, i);
        }
        if (!found) {
            /* All 32 missed: the first good square, x from 10 down, y from 1 up. */
            for (x = W - 2; x >= 1; --x) {
                for (y = 1; y <= H - 2; ++y) {
                    if (foe_ok(x, y, i)) {
                        found = 1;
                        break;
                    }
                }
                if (found) break;
            }
        }
        if (!found) return 0;       /* can't happen: the start row is always clear */
        foe_at[2 * i] = x;
        foe_at[2 * i + 1] = y;
        foe = pool + 2 + (pool[0] * pool[1] + 1) / 2;
        foe = foe + 1 + 2u * foe[0] + 1 + 18u * kind;
        memcpy(out + at, foe, 18);
        out[at] = x;
        out[at + 1] = y;
        v = (uint16_t)(foe[2] + extra);
        out[at + 2] = (uint8_t)(v > 255 ? 255 : v);
        v = (uint16_t)(foe[9] + extra);
        out[at + 9] = (uint8_t)(v > 200 ? 200 : v);
        at = (uint16_t)(at + 18);
        /* Its name, from the pool's list. */
        v = p;
        for (j = 0; j < kind; ++j) v = (uint16_t)(v + 1 + pool[v]);
        memcpy(out + names, pool + v, (size_t)(1 + pool[v]));
        names = (uint16_t)(names + 1 + pool[v]);
    }
    return names;
}
