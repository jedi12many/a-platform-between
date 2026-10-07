/*
 * Prints Deep Yards maps (core/src/yard.c) for tests/yards/check_yards.py to compare
 * with tools/yards/yard.py, natively and on sim65:
 *
 *   yardgen POOLHEX YARD COUNT     COUNT yards from YARD (each the mix of the last),
 *                                  floors 0..12 and 255 of each, one record per line, hex
 *   yardgen pick YARD KEY SALT N   one pick of 1..N
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apb.h"

static uint8_t pool[256];
static uint8_t out[APB_YARD_RECORD_MAX];
static uint8_t work[APB_YARD_WORK];
static const uint8_t floors[14] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 255 };

static uint8_t hex(char c)
{
    if (c >= '0' && c <= '9') return (uint8_t)(c - '0');
    return (uint8_t)(c - 'a' + 10);
}

int main(int argc, char **argv)
{
    uint16_t pool_len;
    uint16_t yard;
    uint16_t count;
    uint16_t len;
    uint16_t i;
    uint8_t f;

    if (argc == 6 && strcmp(argv[1], "pick") == 0) {
        printf("%u\n", (unsigned)(1 + apb_yard_mix((uint16_t)atol(argv[2]),
               (uint16_t)(atol(argv[3]) * 256 + atol(argv[4]))) % (uint16_t)atol(argv[5])));
        return 0;
    }
    if (argc != 4) {
        printf("usage: yardgen POOLHEX YARD COUNT\n");
        return 2;
    }
    pool_len = (uint16_t)(strlen(argv[1]) / 2);
    for (i = 0; i < pool_len; ++i) pool[i] = (uint8_t)(hex(argv[1][2 * i]) * 16 + hex(argv[1][2 * i + 1]));
    yard = (uint16_t)atol(argv[2]);
    count = (uint16_t)atol(argv[3]);
    while (count--) {
        for (f = 0; f < sizeof(floors); ++f) {
            len = apb_yard_build(yard, floors[f], pool, pool_len, out, work);
            for (i = 0; i < len; ++i) printf("%02x", out[i]);
            printf("\n");
        }
        yard = apb_yard_mix(yard, 0x5A5A);
    }
    return 0;
}
