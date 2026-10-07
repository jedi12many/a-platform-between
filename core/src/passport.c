#include <string.h>

#include "apb.h"
#include "names.h"

/*
 * Passport password, format version 2. See docs/passport-spec.md.
 *
 * A fixed part, then counted lists (only what the character actually has), zero
 * bits up to a byte boundary, a CRC-16 over those bytes, and zero bits up to a
 * whole symbol. Written in base 32, in lines of 19 symbols plus a check symbol;
 * the last line may be shorter.
 */

#define LINE_DATA   (APB_PASSWORD_LINE - 1)
#define BUF_BYTES   90      /* 705 bits at most, see the spec */

/* Crockford-style base 32: no I, L, O or U, so they can't be misread. */
static const char sym_upper[] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
static const char sym_lower[] = "0123456789abcdefghjkmnpqrstvwxyz";

typedef struct {
    uint8_t *buf;
    uint16_t pos;
    uint16_t limit;   /* bits available */
    uint8_t  bad;     /* set when reading or writing past the limit */
} bitio;

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static uint8_t buf[BUF_BYTES];
static uint8_t symbols[APB_PASSWORD_MAX];
static apb_character work;

static void put_bits(bitio *b, uint16_t value, uint8_t n)
{
    if (b->pos + n > b->limit) {
        b->bad = 1;
        return;
    }
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

    if (b->pos + n > b->limit) {
        b->bad = 1;
        return 0;
    }
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
static uint8_t line_check(const uint8_t *values, uint8_t count)
{
    uint16_t sum = 0;
    uint8_t i;

    for (i = 0; i < count; ++i) {
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
    if (ch->level == 0 || ch->level > APB_LEVEL_MAX || ch->xp >= APB_XP_PER_LEVEL) return 0;
    if (ch->flags >= 128 || ch->tags >= (1u << APB_SKILL_COUNT)) return 0;
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        if (ch->stat[i] > APB_RATING_MAX) return 0;
    }
    for (i = 0; i < APB_SKILL_COUNT; ++i) {
        if (ch->training[i] > APB_RATING_MAX) return 0;
    }
    for (i = 0; i < APB_POWER_SLOTS; ++i) {
        if (ch->power[i].rank > APB_RATING_MAX) return 0;
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

static void put_items(bitio *b, const uint16_t *slots, uint8_t count)
{
    uint8_t i;
    uint8_t n = 0;

    for (i = 0; i < count; ++i) {
        if (slots[i]) ++n;
    }
    put_bits(b, n, 3);
    for (i = 0; i < count; ++i) {
        if (slots[i]) {
            put_bits(b, i, 3);
            put_bits(b, slots[i], 10);
        }
    }
}

static void get_items(bitio *b, uint16_t *slots, uint8_t count)
{
    uint8_t n = (uint8_t)get_bits(b, 3);
    uint8_t slot;

    if (n > count) {
        b->bad = 1;
        return;
    }
    while (n--) {
        slot = (uint8_t)get_bits(b, 3);
        if (slot >= count || slots[slot] != 0) {
            b->bad = 1;
            return;
        }
        slots[slot] = get_bits(b, 10);
        if (slots[slot] == 0) {
            b->bad = 1;
            return;
        }
    }
}

/* Bits out to symbols: lines of 19 data symbols, each followed by its check. */
static void write_symbols(bitio *b, char *o)
{
    uint16_t data;
    uint16_t s;
    uint8_t line_len = 0;

    data = (uint16_t)((b->pos + 4u) / 5u);
    b->limit = (uint16_t)(data * 5u);
    b->pos = 0;
    for (s = 0; s < data; ++s) {
        symbols[line_len] = (uint8_t)get_bits(b, 5);
        *o++ = sym_upper[symbols[line_len]];
        ++line_len;
        if (line_len == LINE_DATA || s + 1 == data) {
            *o++ = sym_upper[line_check(symbols, line_len)];
            line_len = 0;
        }
    }
    *o = '\0';
}

static void start_bits(bitio *b)
{
    memset(buf, 0, sizeof(buf));
    b->buf = buf;
    b->pos = 0;
    b->limit = BUF_BYTES * 8;
    b->bad = 0;
}

/* The character's fields as Passport bits, ending in the CRC-16 (also kept in
 * packed_crc). */
static uint16_t packed_crc;

static uint8_t pack(const apb_character *ch, bitio *b)
{
    uint8_t i;
    uint8_t n;
    uint8_t name_done = 0;

    if (!fields_fit(ch)) {
        return APB_PP_RANGE;
    }
    start_bits(b);

    put_bits(b, APB_PASSPORT_VERSION, 4);
    for (i = 0; i < APB_NAME_LEN; ++i) {
        if (ch->name[i] == '\0') {
            name_done = 1;
        }
        put_bits(b, name_done ? 0 : apb_name_index(ch->name[i]), 5);
    }
    put_bits(b, ch->race, 5);
    put_bits(b, ch->cls, 4);
    put_bits(b, ch->level, 7);
    put_bits(b, ch->xp, 7);
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        put_bits(b, ch->stat[i], 7);
    }
    put_bits(b, ch->stat_points, 8);
    put_bits(b, ch->skill_points, 8);
    put_bits(b, ch->debt, 16);
    put_bits(b, ch->flags, 7);
    put_bits(b, ch->tags, APB_SKILL_COUNT);

    n = 0;
    for (i = 0; i < APB_SKILL_COUNT; ++i) {
        if (ch->training[i]) ++n;
    }
    put_bits(b, n, 4);
    for (i = 0; i < APB_SKILL_COUNT; ++i) {
        if (ch->training[i]) {
            put_bits(b, i, 4);
            put_bits(b, ch->training[i], 7);
        }
    }

    n = 0;
    for (i = 0; i < APB_POWER_SLOTS; ++i) {
        if (ch->power[i].id) ++n;
    }
    put_bits(b, n, 4);
    for (i = 0; i < APB_POWER_SLOTS; ++i) {
        if (ch->power[i].id) {
            put_bits(b, ch->power[i].id, 8);
            put_bits(b, ch->power[i].rank, 7);
        }
    }

    put_items(b, ch->equipped, APB_EQUIP_SLOTS);
    put_items(b, ch->pack, APB_PACK_SLOTS);

    n = 0;
    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        if (ch->echo[i].id) ++n;
    }
    put_bits(b, n, 4);
    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        if (ch->echo[i].id) {
            put_bits(b, ch->echo[i].id, 10);
            put_bits(b, ch->echo[i].state, 2);
        }
    }

    b->pos = (uint16_t)((b->pos + 7u) & ~7u);
    packed_crc = crc16(buf, (uint8_t)(b->pos >> 3));
    put_bits(b, packed_crc, 16);
    return b->bad ? APB_PP_RANGE : APB_PP_OK;
}

uint8_t apb_passport_encode(const apb_character *ch, char *out)
{
    bitio b;

    out[0] = '\0';
    if (pack(ch, &b) != APB_PP_OK) {
        return APB_PP_RANGE;
    }
    write_symbols(&b, out);
    return APB_PP_OK;
}

uint16_t apb_passport_check(const apb_character *ch)
{
    bitio b;

    return pack(ch, &b) == APB_PP_OK ? packed_crc : 0;
}

/* ------------------------------------------------------- Boarding Pass */

/* Version 4, Departure 16, ticket 32, character check 16, seed 16, Rewind 1: 85 bits,
 * 17 symbols and a check symbol. See docs/boarding.md. */
#define PASS_SYMBOLS 17

uint8_t apb_pass_encode(const apb_pass *pass, char *out)
{
    bitio b;

    start_bits(&b);
    put_bits(&b, APB_PASS_VERSION, 4);
    put_bits(&b, pass->departure, 16);
    put_bits(&b, (uint16_t)(pass->ticket >> 16), 16);
    put_bits(&b, (uint16_t)(pass->ticket & 0xFFFFu), 16);
    put_bits(&b, pass->check, 16);
    put_bits(&b, pass->seed, 16);
    put_bits(&b, pass->rewind ? 1 : 0, 1);
    write_symbols(&b, out);
    return APB_PP_OK;
}

uint8_t apb_pass_decode(const char *in, apb_pass *pass)
{
    uint8_t count = 0;
    int8_t v;
    bitio b;

    for (; *in != '\0'; ++in) {
        if (is_separator(*in)) {
            continue;
        }
        v = symbol_value(*in);
        if (v < 0) {
            return APB_PP_SYMBOL;
        }
        if (count > PASS_SYMBOLS) {
            return APB_PP_LENGTH;
        }
        symbols[count++] = (uint8_t)v;
    }
    if (count != PASS_SYMBOLS + 1) {
        return APB_PP_LENGTH;
    }
    if (line_check(symbols, PASS_SYMBOLS) != symbols[PASS_SYMBOLS]) {
        return APB_PP_LINE_CHECK;
    }
    start_bits(&b);
    for (v = 0; v < PASS_SYMBOLS; ++v) {
        put_bits(&b, symbols[(uint8_t)v], 5);
    }
    b.pos = 0;
    if (get_bits(&b, 4) != APB_PASS_VERSION) {
        return APB_PP_VERSION;
    }
    pass->departure = get_bits(&b, 16);
    pass->ticket = (uint32_t)get_bits(&b, 16) << 16;
    pass->ticket |= get_bits(&b, 16);
    pass->check = get_bits(&b, 16);
    pass->seed = get_bits(&b, 16);
    pass->rewind = (uint8_t)get_bits(&b, 1);
    return APB_PP_OK;
}

/* Read a password of lines (a Passport, a Travel Stamp): check each line's check symbol
 * and pack the data symbols into `b`, ready to read from the start. */
static uint8_t read_lines(const char *in, bitio *b, uint8_t *bad_line)
{
    uint8_t count = 0;
    uint8_t lines;
    uint8_t line;
    uint8_t line_start;
    uint8_t line_len;
    uint8_t data;
    uint8_t i;
    int8_t v;

    for (; *in != '\0'; ++in) {
        if (is_separator(*in)) {
            continue;
        }
        v = symbol_value(*in);
        if (v < 0) {
            return APB_PP_SYMBOL;
        }
        if (count == APB_PASSWORD_MAX) {
            return APB_PP_LENGTH;
        }
        symbols[count++] = (uint8_t)v;
    }

    lines = (uint8_t)((count + APB_PASSWORD_LINE - 1) / APB_PASSWORD_LINE);
    if (lines == 0 || count - (lines - 1) * APB_PASSWORD_LINE < 2) {
        return APB_PP_LENGTH;
    }

    /* Check each line, and pack the data symbols into bits as we go. */
    memset(buf, 0, sizeof(buf));
    b->buf = buf;
    b->pos = 0;
    b->limit = BUF_BYTES * 8;
    b->bad = 0;
    data = 0;
    for (line = 0; line < lines; ++line) {
        line_start = (uint8_t)(line * APB_PASSWORD_LINE);
        line_len = (uint8_t)(line + 1 < lines ? LINE_DATA : count - line_start - 1);
        if (line_check(&symbols[line_start], line_len) != symbols[line_start + line_len]) {
            if (bad_line) {
                *bad_line = (uint8_t)(line + 1);
            }
            return APB_PP_LINE_CHECK;
        }
        for (i = 0; i < line_len; ++i) {
            put_bits(b, symbols[line_start + i], 5);
        }
        data = (uint8_t)(data + line_len);
    }
    if (b->bad) {
        return APB_PP_LENGTH;
    }
    b->limit = (uint16_t)(data * 5u);
    b->pos = 0;
    return APB_PP_OK;
}

/* After the fields: zero padding to a byte, the CRC of the bytes so far, then zero
 * padding to the last symbol. */
static uint8_t read_crc(bitio *b)
{
    uint8_t n;
    uint16_t stored_crc;

    while (b->pos & 7u) {
        if (get_bits(b, 1) != 0 || b->bad) return APB_PP_CHECKSUM;
    }
    n = (uint8_t)(b->pos >> 3);
    stored_crc = get_bits(b, 16);
    if (b->bad || stored_crc != crc16(buf, n)) {
        return APB_PP_CHECKSUM;
    }
    if (b->limit - b->pos >= 5) {
        return APB_PP_LENGTH;
    }
    while (b->pos < b->limit) {
        if (get_bits(b, 1) != 0) return APB_PP_CHECKSUM;
    }
    return APB_PP_OK;
}

uint8_t apb_passport_decode(const char *in, apb_character *ch, uint8_t *bad_line)
{
    uint8_t i;
    uint8_t n;
    uint8_t version;
    bitio b;

    n = read_lines(in, &b, bad_line);
    if (n != APB_PP_OK) {
        return n;
    }
    version = (uint8_t)get_bits(&b, 4);
    if (version != APB_PASSPORT_VERSION) {
        return APB_PP_VERSION;
    }

    memset(&work, 0, sizeof(work));
    for (i = 0; i < APB_NAME_LEN; ++i) {
        work.name[i] = apb_name_char((uint8_t)get_bits(&b, 5));
    }
    apb_name_normalize(work.name, work.name);
    work.race = (uint8_t)get_bits(&b, 5);
    work.cls = (uint8_t)get_bits(&b, 4);
    work.level = (uint8_t)get_bits(&b, 7);
    work.xp = (uint8_t)get_bits(&b, 7);
    for (i = 0; i < APB_STAT_COUNT; ++i) {
        work.stat[i] = (uint8_t)get_bits(&b, 7);
    }
    work.stat_points = (uint8_t)get_bits(&b, 8);
    work.skill_points = (uint8_t)get_bits(&b, 8);
    work.debt = get_bits(&b, 16);
    work.flags = (uint8_t)get_bits(&b, 7);
    work.tags = get_bits(&b, APB_SKILL_COUNT);

    n = (uint8_t)get_bits(&b, 4);
    if (n > APB_SKILL_COUNT) b.bad = 1;
    while (n-- && !b.bad) {
        i = (uint8_t)get_bits(&b, 4);
        if (i >= APB_SKILL_COUNT || work.training[i] != 0) {
            b.bad = 1;
            break;
        }
        work.training[i] = (uint8_t)get_bits(&b, 7);
        if (work.training[i] == 0) b.bad = 1;
    }

    n = (uint8_t)get_bits(&b, 4);
    if (n > APB_POWER_SLOTS) b.bad = 1;
    for (i = 0; i < n && !b.bad; ++i) {
        work.power[i].id = (uint8_t)get_bits(&b, 8);
        work.power[i].rank = (uint8_t)get_bits(&b, 7);
        if (work.power[i].id == 0) b.bad = 1;
    }

    if (!b.bad) get_items(&b, work.equipped, APB_EQUIP_SLOTS);
    if (!b.bad) get_items(&b, work.pack, APB_PACK_SLOTS);

    n = (uint8_t)get_bits(&b, 4);
    if (n > APB_ECHO_SLOTS) b.bad = 1;
    for (i = 0; i < n && !b.bad; ++i) {
        work.echo[i].id = get_bits(&b, 10);
        work.echo[i].state = (uint8_t)get_bits(&b, 2);
        if (work.echo[i].id == 0) b.bad = 1;
    }
    if (b.bad) {
        return APB_PP_CHECKSUM;
    }

    n = read_crc(&b);
    if (n != APB_PP_OK) {
        return n;
    }

    if (!fields_fit(&work)) {
        return APB_PP_CHECKSUM;
    }
    memcpy(ch, &work, sizeof(work));
    return APB_PP_OK;
}

/* ------------------------------------------------------- Travel Stamp */

static void put_list(bitio *b, const uint16_t *items, uint8_t count)
{
    uint8_t i;

    put_bits(b, count, 4);
    for (i = 0; i < count; ++i) {
        put_bits(b, items[i], 10);
    }
}

uint8_t apb_stamp_encode(const apb_receipt *r, char *out)
{
    bitio b;
    uint8_t i;

    out[0] = '\0';
    if (r->gained_count > APB_RECEIPT_MAX || r->lost_count > APB_RECEIPT_MAX
        || r->echo_count > APB_RECEIPT_MAX) {
        return APB_PP_RANGE;
    }
    for (i = 0; i < r->gained_count; ++i) if (r->gained[i] > 1023u) return APB_PP_RANGE;
    for (i = 0; i < r->lost_count; ++i) if (r->lost[i] > 1023u) return APB_PP_RANGE;
    for (i = 0; i < r->echo_count; ++i) {
        if (r->echoes[i].id > 1023u || r->echoes[i].state > 3 || r->echoes[i].was > 3) {
            return APB_PP_RANGE;
        }
    }

    start_bits(&b);
    put_bits(&b, APB_STAMP_VERSION, 4);
    put_bits(&b, r->departure, 16);
    put_bits(&b, (uint16_t)(r->ticket >> 16), 16);
    put_bits(&b, (uint16_t)(r->ticket & 0xFFFFu), 16);
    put_bits(&b, r->outcome ? 1 : 0, 1);
    put_bits(&b, r->xp, 16);
    put_bits(&b, r->debt_added ? 1 : 0, 1);         /* 1: Debt added, 0: paid */
    put_bits(&b, r->debt_added ? r->debt_added : r->debt_paid, 16);
    put_list(&b, r->gained, r->gained_count);
    put_list(&b, r->lost, r->lost_count);
    put_bits(&b, r->echo_count, 4);
    for (i = 0; i < r->echo_count; ++i) {
        put_bits(&b, r->echoes[i].id, 10);
        put_bits(&b, r->echoes[i].state, 2);
        put_bits(&b, r->echoes[i].was, 2);
    }
    b.pos = (uint16_t)((b.pos + 7u) & ~7u);
    put_bits(&b, crc16(buf, (uint8_t)(b.pos >> 3)), 16);
    write_symbols(&b, out);
    return APB_PP_OK;
}

/* Decoding stamps is the Waystation's job (W1), not a client's: builds that need it
 * define APB_WAYSTATION (the website, and the receipt tests), so a train doesn't carry
 * it (the 6502 harness has no room for it). */
#ifdef APB_WAYSTATION

static uint8_t get_list(bitio *b, uint16_t *items)
{
    uint8_t n = (uint8_t)get_bits(b, 4);
    uint8_t i;

    if (n > APB_RECEIPT_MAX) {
        b->bad = 1;
        return 0;
    }
    for (i = 0; i < n; ++i) {
        items[i] = get_bits(b, 10);
    }
    return n;
}

static apb_receipt stamped;

uint8_t apb_stamp_decode(const char *in, apb_receipt *r, uint8_t *bad_line)
{
    bitio b;
    uint8_t i;
    uint16_t amount;

    i = read_lines(in, &b, bad_line);
    if (i != APB_PP_OK) {
        return i;
    }
    if (get_bits(&b, 4) != APB_STAMP_VERSION) {
        return b.bad ? APB_PP_LENGTH : APB_PP_VERSION;
    }
    memset(&stamped, 0, sizeof(stamped));
    stamped.departure = get_bits(&b, 16);
    stamped.ticket = (uint32_t)get_bits(&b, 16) << 16;
    stamped.ticket |= get_bits(&b, 16);
    stamped.outcome = (uint8_t)get_bits(&b, 1);
    stamped.xp = get_bits(&b, 16);
    i = (uint8_t)get_bits(&b, 1);           /* 1: Debt added, 0: paid */
    amount = get_bits(&b, 16);
    if (i) stamped.debt_added = amount;
    else stamped.debt_paid = amount;
    stamped.gained_count = get_list(&b, stamped.gained);
    if (!b.bad) stamped.lost_count = get_list(&b, stamped.lost);
    if (!b.bad) {
        stamped.echo_count = (uint8_t)get_bits(&b, 4);
        if (stamped.echo_count > APB_RECEIPT_MAX) b.bad = 1;
    }
    for (i = 0; i < stamped.echo_count && !b.bad; ++i) {
        stamped.echoes[i].id = get_bits(&b, 10);
        stamped.echoes[i].state = (uint8_t)get_bits(&b, 2);
        stamped.echoes[i].was = (uint8_t)get_bits(&b, 2);
    }
    if (b.bad) {
        return APB_PP_CHECKSUM;
    }
    i = read_crc(&b);
    if (i != APB_PP_OK) {
        return i;
    }
    memcpy(r, &stamped, sizeof(stamped));
    return APB_PP_OK;
}

#endif /* APB_WAYSTATION */
