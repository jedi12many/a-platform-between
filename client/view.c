/*
 * The status line and check results, as ASCII lines (client/apb_view.h).
 */
#ifdef __CC65__
#include <ascii_charmap.h>      /* every literal in this file is ASCII */
#endif

#include "apb_view.h"
#include <string.h>

#include "names.h"

char *apb_view_put(char *at, const char *ascii)
{
    while (*ascii) *at++ = *ascii++;
    *at = '\0';
    return at;
}

char *apb_view_unum(char *at, uint16_t v)
{
    char d[6];
    uint8_t n = 0;

    do {
        d[n++] = (char)(0x30 + v % 10);
        v = (uint16_t)(v / 10);
    } while (v);
    while (n) *at++ = d[--n];
    *at = '\0';
    return at;
}

char *apb_view_num(char *at, int16_t v)
{
    if (v < 0) {
        *at++ = '-';
        return apb_view_unum(at, (uint16_t)(0 - v));
    }
    return apb_view_unum(at, (uint16_t)v);
}

void apb_view_name(char *out, const apb_character *ch)
{
    const char *p;
    uint8_t first = 1;
    uint8_t c;

    /* Names are kept in capitals: "KESTREL" reads "Kestrel". */
    for (p = ch->name; *p; ++p) {
        c = apb_name_ascii(*p);
        if (!first && c >= 0x41 && c <= 0x5A) c = (uint8_t)(c + 0x20);
        first = (uint8_t)(c == 0x20 || c == 0x2D);
        *out++ = (char)c;
    }
    *out = '\0';
}

void apb_view_status(char *out, const apb_character *ch, uint8_t health)
{
    apb_view_name(out, ch);
    out = apb_view_put(out + strlen(out), "  Lvl ");
    out = apb_view_unum(out, ch->level);
    out = apb_view_put(out, "  HP ");
    out = apb_view_unum(out, health);
    out = apb_view_put(out, "/");
    out = apb_view_unum(out, apb_health_max(ch));
    out = apb_view_put(out, "  Debt ");
    apb_view_unum(out, ch->debt);
}

static const char *const stat_names[] = { "Might", "Grace", "Grit", "Wits", "Presence", "Fate" };
static const char *const results[] = { "fail", "success at a cost", "success", "critical success" };

void apb_view_check(char *out, uint8_t rating, const apb_roll *roll)
{
    out = apb_view_put(out, "[");
    out = apb_view_put(out, rating < 6 ? stat_names[rating]
                                       : rating >= 16 && rating < 16 + APB_SKILL_COUNT
                                         ? apb_skill_names[rating - 16] : (const char *)"?");
    out = apb_view_put(out, " check: rolled ");
    out = apb_view_unum(out, roll->roll);
    out = apb_view_put(out, " + ");
    out = apb_view_num(out, (int16_t)(roll->total - roll->roll));
    out = apb_view_put(out, " = ");
    out = apb_view_num(out, roll->total);
    out = apb_view_put(out, " against ");
    out = apb_view_num(out, roll->tn);
    out = apb_view_put(out, ": ");
    out = apb_view_put(out, results[roll->result & 3]);
    apb_view_put(out, "]");
}
