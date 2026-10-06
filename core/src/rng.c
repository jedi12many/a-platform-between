#include "apb.h"

/*
 * xorshift16 (7, 9, 8): full period of 65535, cheap on a 6502, and identical on
 * every platform. A zero state would lock the generator, so zero is remapped.
 */

void apb_rng_seed(apb_rng *rng, uint16_t seed)
{
    rng->state = seed ? seed : 0xACE1u;
}

uint16_t apb_rng_next(apb_rng *rng)
{
    uint16_t x = rng->state;

    x ^= (uint16_t)(x << 7);
    x ^= (uint16_t)(x >> 9);
    x ^= (uint16_t)(x << 8);
    rng->state = x;
    return x;
}

uint8_t apb_d6(apb_rng *rng)
{
    uint8_t v;

    /* Top three bits, rejecting 6 and 7, so every face is equally likely. */
    do {
        v = (uint8_t)(apb_rng_next(rng) >> 13);
    } while (v > 5);
    return (uint8_t)(v + 1);
}
