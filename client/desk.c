#include <string.h>

#include "apb.h"
#include "apb_desk.h"
#include "apb_hal.h"
#include "names.h"

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static char lines[APB_DESK_LINES][APB_DESK_TYPED + 1];   /* room for spaces and dashes */
static char joined[APB_DESK_LINES * (APB_DESK_TYPED + 1) + 1];
static char msg[48];

/* Menu labels are game text, so ASCII: "Board", "Start over". */
static const char label_board[] = { 66, 111, 97, 114, 100, 0 };
static const char label_again[] = { 83, 116, 97, 114, 116, 32, 111, 118, 101, 114, 0 };
static const char *const labels[2] = { label_board, label_again };


static void numbered(const char *before, uint8_t n, const char *after)
{
    uint8_t i = 0;

    while (*before) msg[i++] = *before++;
    msg[i++] = (char)('0' + n);
    while (*after) msg[i++] = *after++;
    msg[i] = '\0';
    hal_prompt(msg);
}

static void ascii_text(const char *ascii)
{
    while (*ascii) hal_text_char(*ascii++);
}

static void ascii_number(uint16_t v)
{
    char d[6];
    uint8_t n = 0;

    do {
        d[n++] = (char)(0x30 + v % 10);
        v = (uint16_t)(v / 10);
    } while (v);
    while (n) hal_text_char(d[--n]);
}

/* "Kestrel, Salvaged Warden, level 3. Debt 50000." in ASCII, like any game text. */
static void show(const apb_character *ch)
{
    static const char sep[] = { 44, 32, 0 };            /* ", "     */
    static const char lvl[] = { 44, 32, 108, 101, 118, 101, 108, 32, 0 };  /* ", level " */
    static const char debt[] = { 46, 32, 68, 101, 98, 116, 32, 0 };        /* ". Debt " */
    const char *p;
    uint8_t first = 1;
    uint8_t c;

    for (p = ch->name; *p; ++p) {
        c = apb_name_ascii(*p);
        if (!first && c >= 0x41 && c <= 0x5A) c = (uint8_t)(c + 0x20);
        first = (uint8_t)(c == 0x20 || c == 0x2D);
        hal_text_char((char)c);
    }
    ascii_text(sep);
    ascii_text(ch->race < APB_RACE_COUNT ? apb_race_names[ch->race] : (const char *)"?");
    hal_text_char(0x20);
    ascii_text(ch->cls < APB_CLASS_COUNT ? apb_class_names[ch->cls] : (const char *)"?");
    ascii_text(lvl);
    ascii_number(ch->level);
    ascii_text(debt);
    ascii_number(ch->debt);
    hal_text_char(0x2E);
    hal_text_end();
}

/* Symbols on a typed line, ignoring the spaces and dashes the decoder ignores. */
static uint8_t symbols(const char *p)
{
    uint8_t n = 0;

    for (; *p; ++p) {
        if (*p != ' ' && *p != '-') ++n;
    }
    return n;
}

/* A line the wrong length, before decoding: every line but the last has 20 symbols,
 * the last has 2 to 20. Returns the 1-based line, or 0 if they're all fine. */
static uint8_t wrong_length(uint8_t count)
{
    uint8_t i;
    uint8_t n;

    for (i = 0; i < count; ++i) {
        n = symbols(lines[i]);
        if (n > APB_PASSWORD_LINE || (i + 1 < count && n != APB_PASSWORD_LINE) || n < 2) {
            return (uint8_t)(i + 1);
        }
    }
    return 0;
}

/* Join the typed lines, separated by spaces (the decoder ignores them). */
static void join(uint8_t count)
{
    uint8_t i;
    uint16_t n = 0;
    const char *p;

    for (i = 0; i < count; ++i) {
        for (p = lines[i]; *p && (unsigned)n + 2u < sizeof(joined); ++p) joined[n++] = *p;
        joined[n++] = ' ';
    }
    joined[n] = '\0';
}

/* Decode what was typed: a Boarding Pass or a Passport, whichever it is. */
static uint8_t decode(apb_character *out, apb_pass *pass, uint8_t *bad)
{
    if (apb_password_kind(joined) == APB_KIND_PASS) {
        return apb_pass_decode(joined, pass, out, bad);
    }
    return apb_passport_decode(joined, out, bad);
}

uint8_t apb_desk_run(uint16_t departure, apb_character *out, apb_pass *pass)
{
    uint8_t count;
    uint8_t result;
    uint8_t bad;
    uint8_t with_pass;

    for (;;) {
        hal_prompt("Your Boarding Pass, please, one line at a time, then a blank line. "
                   "(Or your Passport, to travel without one.)");
        count = 0;
        while (count < APB_DESK_LINES) {
            numbered("Line ", (uint8_t)(count + 1), ":");
            hal_ask_line(lines[count], APB_DESK_TYPED);
            if (lines[count][0] == '\0') {
                break;
            }
            ++count;
        }
        if (count == 0) {
            continue;
        }
        if (count < 3) {
            hal_prompt("A pass or a Passport is at least 3 lines. Let's start again.");
            continue;
        }
        for (;;) {
            bad = wrong_length(count);
            if (bad) {
                numbered("Line ", bad, bad == count
                         ? " is too long or too short. Type it again:"
                         : " should have 20 letters. Type it again:");
                hal_ask_line(lines[bad - 1], APB_DESK_TYPED);
                continue;
            }
            join(count);
            bad = 0;
            result = decode(out, pass, &bad);
            if (result != APB_PP_LINE_CHECK || bad == 0 || bad > count) {
                break;
            }
            numbered("Line ", bad, " has a typo. Type it again:");
            hal_ask_line(lines[bad - 1], APB_DESK_TYPED);
        }
        with_pass = (uint8_t)(apb_password_kind(joined) == APB_KIND_PASS);
        if (result == APB_PP_OK) {
            if (with_pass && pass->departure != departure) {
                hal_prompt("That Boarding Pass is for a different Departure. The Waystation "
                           "will issue one for this one.");
                continue;
            }
            show(out);
            if (!with_pass) {
                hal_prompt("That's a Passport, not a Boarding Pass: nothing you earn on this "
                           "trip can be stamped.");
            }
            if (hal_menu(labels, 2) == 0) {
                return with_pass;
            }
            continue;
        }
        if (result == APB_PP_SYMBOL) {
            hal_prompt("Something there isn't a letter a pass uses. Let's start again.");
        } else if (result == APB_PP_VERSION) {
            hal_prompt("That's from a different version of the game.");
        } else if (result == APB_PP_CHECKSUM) {
            hal_prompt("Every line checks out, but the whole doesn't. Check them all.");
        } else {
            hal_prompt("That isn't a whole pass or Passport. Let's start again.");
        }
    }
}

uint16_t apb_desk_yard(uint16_t fresh)
{
    const char *p;
    uint32_t v;
    uint8_t n;

    for (;;) {
        hal_prompt("Which yard? Type a yard's number to go down one someone shared, or a "
                   "blank line for a new one.");
        hal_ask_line(lines[0], APB_DESK_TYPED);
        if (lines[0][0] == '\0') {
            return fresh;
        }
        /* Digits are the same in ASCII and PETSCII, so comparing with '0'..'9' is safe. */
        v = 0;
        n = 0;
        for (p = lines[0]; *p; ++p) {
            if (*p == ' ') continue;
            if (*p < '0' || *p > '9' || ++n > 5) break;
            v = v * 10 + (uint32_t)(*p - '0');
        }
        if (!*p && n && v <= 65535UL) {
            return (uint16_t)v;
        }
        hal_prompt("A yard's number is a whole number from 0 to 65535. Type it again.");
    }
}
