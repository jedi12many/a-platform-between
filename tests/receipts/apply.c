/*
 * Applies a receipt to a Passport and prints the new Passport and what happened, then
 * the receipt as a Travel Stamp (Departure 7, ticket 123456789), for
 * tests/receipts/check_apply.py to compare with the Python reference. Native and sim65.
 *
 *   apply PASSPORT XP PAID ADDED GAINED LOST ECHOES [rewind DEPARTURE]
 *
 * GAINED and LOST are item ids separated by commas, ECHOES is id:state:was entries
 * separated by commas; '-' is an empty list.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apb.h"

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static apb_character ch;
static apb_receipt r;
static apb_applied out;
static char password[APB_PASSWORD_BUF];
static char stamp[APB_STAMP_BUF];

static uint8_t parse_list(const char *s, uint16_t *list)
{
    uint8_t n = 0;

    if (strcmp(s, "-") == 0) return 0;
    while (*s && n < APB_RECEIPT_MAX) {
        list[n++] = (uint16_t)atoi(s);
        while (*s && *s != ',') ++s;
        if (*s == ',') ++s;
    }
    return n;
}

static void parse_echoes(const char *s)
{
    if (strcmp(s, "-") == 0) return;
    while (*s && r.echo_count < APB_RECEIPT_MAX) {
        r.echoes[r.echo_count].id = (uint16_t)atoi(s);
        while (*s != ':') ++s;
        r.echoes[r.echo_count].state = (uint8_t)atoi(++s);
        while (*s != ':') ++s;
        r.echoes[r.echo_count].was = (uint8_t)atoi(++s);
        ++r.echo_count;
        while (*s && *s != ',') ++s;
        if (*s == ',') ++s;
    }
}

int main(int argc, char **argv)
{
    uint8_t i;

    if (argc != 8 && argc != 10) {
        printf("usage: apply PASSPORT XP PAID ADDED GAINED LOST ECHOES [rewind DEPARTURE]\n");
        return 2;
    }
    if (apb_passport_decode(argv[1], &ch, 0) != APB_PP_OK) {
        printf("bad passport\n");
        return 1;
    }
    r.xp = (uint16_t)atol(argv[2]);
    r.debt_paid = (uint16_t)atol(argv[3]);
    r.debt_added = (uint16_t)atol(argv[4]);
    r.gained_count = parse_list(argv[5], r.gained);
    r.lost_count = parse_list(argv[6], r.lost);
    parse_echoes(argv[7]);

    if (argc == 10) r.departure = (uint16_t)atoi(argv[9]);
    apb_receipt_apply(&ch, &r, (uint8_t)(argc == 10), &out);
    if (apb_passport_encode(&ch, password) != APB_PP_OK) {
        printf("can't encode\n");
        return 1;
    }
    printf("%s\nlevels %u gone %u stored", password, out.levels, out.gone);
    for (i = 0; i < out.stored_count; ++i) printf(" %u", out.stored[i]);
    printf(" shifted");
    for (i = 0; i < out.shifted_count; ++i) printf(" %u", out.shifted[i]);
    printf(" legend");
    for (i = 0; i < out.legend_count; ++i) printf(" %u=%u", out.legend[i].id, out.legend[i].state);
    printf("\n");
    r.departure = argc == 10 ? (uint16_t)atoi(argv[9]) : 7;
    r.ticket = 123456789UL;
    if (apb_stamp_encode(&r, stamp) != APB_PP_OK) {
        printf("can't stamp\n");
        return 1;
    }
    printf("%s\n", stamp);
    return 0;
}
