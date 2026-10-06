#include <string.h>

#include "apb.h"
#include "names.h"

/*
 * Passport password, format version 1. See docs/passport-spec.md.
 *
 * 360 bits of fields, a 16-bit CRC, 4 zero pad bits: 380 bits, written as 76
 * base-32 symbols in 4 lines of 19, each line followed by a check symbol.
 */

#define PAYLOAD_BITS   360
#define PAYLOAD_BYTES  (PAYLOAD_BITS / 8)
#define DATA_SYMBOLS   76
#define LINE_DATA      (APB_PASSWORD_LINE - 1)
#define BUF_BYTES      48

/* Crockford-style base 32: no I, L, O or U, so they can't be misread. */
static const char sym_upper[] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
static const char sym_lower[] = "0123456789abcdefghjkmnpqrstvwxyz";

typedef struct {
    uint8_t *buf;
    uint16_t pos;
} bitio;

static void put_bits(bitio *b, uint16_t value, uint8_t n)
{
    while (n--) {
        if ((value >> n) & 1u) {
            b->buf[b->pos >> 3] |= (uint8_t)(0x80u >> (b->pos & 7u));
        }
        ++b->pos;
    }
}

static uint16_t get_bits(bitio *b, uint8_t n)
{
    uint16_t value = 0;

    while (n--) {
        value = (uint16_t)(value << 1);
        if (b->buf[b->pos >> 3] & (uint8_t)(0x80u >> (b->pos & 7u))) {
            value |= 1u;
        }
        ++b->pos;
    }
    return value;
}

static uint16_t crc16(const uint8_t *data, uint8_t len)
{
    uint16_t crc = 0xFFFFu;
    uint8_t i;
    uint8_t bit;

    for (i = 0; i < len; ++i) {
        crc ^= (uint16_t)((uint16_t)data[i] << 8);
        for (bit = 0; bit < 8; ++bit) {
            if (crc & 0x8000u) {
                crc = (uint16_t)((uint16_t)(crc << 1) ^ 0x1021u);
            } else {
                crc = (uint16_t)(crc << 1);
            }
        }
    }
    return crc;
}

/* Odd weights are invertible mod 32, so any single wrong symbol changes it. */
static uint8_t line_check(const uint8_t *values)
{
    uint16_t sum = 0;
    uint8_t i;

    for (i = 0; i < LINE_DATA; ++i) {
        sum = (uint16_t)(sum + values[i] * (uint8_t)(2 * i + 1));
    }
    return (uint8_t)(sum & 31u);
}

static int8_t symbol_value(char c)
{
    uint8_t i;

    for (i = 0; i < 32; ++i) {
        if (sym_upper[i] == c || sym_lower[i] == c) {
            return (int8_t)i;
        }
    }
    /* Forgive the look-alikes the alphabet leaves out. */
    if (c == 'O' || c == 'o') return 0;
    if (c == 'I' || c == 'i' || c == 'L' || c == 'l') return 1;
    return -1;
}

static uint8_t is_separator(char c)
{
    return c == ' ' || c == '-' || c == '\n' || c == '\r' || c == '\t';
}

static uint8_t fields_fit(const apb_character *ch)
{
    uint8_t i;

    if (ch->race >= 32 || ch->cls >= 16) return 0;
    if (ch->level == 0 || ch->level >= 32 || ch->xp >= 128) return 0;
    if (ch->flags >= 128) return 0;
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        if (ch->stat[i] >= 16) return 0;
    }
    for (i = 0; i < APB_EQUIP_SLOTS; ++i) {
        if (ch->equipped[i] >= 1024) return 0;
    }
    for (i = 0; i < APB_PACK_SLOTS; ++i) {
        if (ch->pack[i] >= 1024) return 0;
    }
    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        if (ch->echo[i].id >= 1024 || ch->echo[i].state >= 4) return 0;
    }
    return 1;
}

uint8_t apb_passport_encode(const apb_character *ch, char *out)
{
    uint8_t buf[BUF_BYTES];
    uint8_t values[LINE_DATA];
    bitio b;
    uint8_t i;
    uint8_t line;
    uint8_t name_done = 0;
    char *o = out;

    if (!fields_fit(ch)) {
        out[0] = '\0';
        return APB_PP_RANGE;
    }

    memset(buf, 0, sizeof(buf));
    b.buf = buf;
    b.pos = 0;

    put_bits(&b, APB_PASSPORT_VERSION, 4);
    for (i = 0; i < APB_NAME_LEN; ++i) {
        if (ch->name[i] == '\0') {
            name_done = 1;
        }
        put_bits(&b, name_done ? 0 : apb_name_index(ch->name[i]), 5);
    }
    put_bits(&b, ch->race, 5);
    put_bits(&b, ch->cls, 4);
    put_bits(&b, ch->level, 5);
    put_bits(&b, ch->xp, 7);
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        put_bits(&b, ch->stat[i], 4);
    }
    put_bits(&b, ch->perks[0], 16);
    put_bits(&b, ch->perks[1], 16);
    put_bits(&b, ch->debt, 16);
    for (i = 0; i < APB_EQUIP_SLOTS; ++i) {
        put_bits(&b, ch->equipped[i], 10);
    }
    for (i = 0; i < APB_PACK_SLOTS; ++i) {
        put_bits(&b, ch->pack[i], 10);
    }
    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        put_bits(&b, ch->echo[i].id, 10);
        put_bits(&b, ch->echo[i].state, 2);
    }
    put_bits(&b, ch->flags, 7);

    put_bits(&b, crc16(buf, PAYLOAD_BYTES), 16);

    b.pos = 0;
    for (line = 0; line < APB_PASSWORD_LINES; ++line) {
        for (i = 0; i < LINE_DATA; ++i) {
            values[i] = (uint8_t)get_bits(&b, 5);
            *o++ = sym_upper[values[i]];
        }
        *o++ = sym_upper[line_check(values)];
    }
    *o = '\0';
    return APB_PP_OK;
}

uint8_t apb_passport_decode(const char *in, apb_character *ch, uint8_t *bad_line)
{
    uint8_t symbols[APB_PASSWORD_LEN];
    uint8_t buf[BUF_BYTES];
    uint8_t count = 0;
    uint8_t line;
    uint8_t i;
    int8_t v;
    uint16_t stored_crc;
    bitio b;

    for (; *in != '\0'; ++in) {
        if (is_separator(*in)) {
            continue;
        }
        v = symbol_value(*in);
        if (v < 0) {
            return APB_PP_SYMBOL;
        }
        if (count == APB_PASSWORD_LEN) {
            return APB_PP_LENGTH;
        }
        symbols[count++] = (uint8_t)v;
    }
    if (count != APB_PASSWORD_LEN) {
        return APB_PP_LENGTH;
    }

    for (line = 0; line < APB_PASSWORD_LINES; ++line) {
        if (line_check(&symbols[line * APB_PASSWORD_LINE])
            != symbols[line * APB_PASSWORD_LINE + LINE_DATA]) {
            if (bad_line) {
                *bad_line = (uint8_t)(line + 1);
            }
            return APB_PP_LINE_CHECK;
        }
    }

    memset(buf, 0, sizeof(buf));
    b.buf = buf;
    b.pos = 0;
    for (line = 0; line < APB_PASSWORD_LINES; ++line) {
        for (i = 0; i < LINE_DATA; ++i) {
            put_bits(&b, symbols[line * APB_PASSWORD_LINE + i], 5);
        }
    }

    b.pos = PAYLOAD_BITS;
    stored_crc = get_bits(&b, 16);
    if (get_bits(&b, 4) != 0 || stored_crc != crc16(buf, PAYLOAD_BYTES)) {
        return APB_PP_CHECKSUM;
    }

    b.pos = 0;
    if (get_bits(&b, 4) != APB_PASSPORT_VERSION) {
        return APB_PP_VERSION;
    }

    memset(ch, 0, sizeof(*ch));
    for (i = 0; i < APB_NAME_LEN; ++i) {
        ch->name[i] = apb_name_char((uint8_t)get_bits(&b, 5));
    }
    apb_name_normalize(ch->name, ch->name);
    ch->race = (uint8_t)get_bits(&b, 5);
    ch->cls = (uint8_t)get_bits(&b, 4);
    ch->level = (uint8_t)get_bits(&b, 5);
    ch->xp = (uint8_t)get_bits(&b, 7);
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        ch->stat[i] = (uint8_t)get_bits(&b, 4);
    }
    ch->perks[0] = get_bits(&b, 16);
    ch->perks[1] = get_bits(&b, 16);
    ch->debt = get_bits(&b, 16);
    for (i = 0; i < APB_EQUIP_SLOTS; ++i) {
        ch->equipped[i] = get_bits(&b, 10);
    }
    for (i = 0; i < APB_PACK_SLOTS; ++i) {
        ch->pack[i] = get_bits(&b, 10);
    }
    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        ch->echo[i].id = get_bits(&b, 10);
        ch->echo[i].state = (uint8_t)get_bits(&b, 2);
    }
    ch->flags = (uint8_t)get_bits(&b, 7);
    return APB_PP_OK;
}
