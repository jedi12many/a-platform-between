/*
 * The end of a trip: the outcome and the receipt, as ASCII lines (client/apb_view.h).
 * In a file of its own so the C64 can keep it in an overlay.
 */
#ifdef __CC65__
#include <ascii_charmap.h>      /* every literal in this file is ASCII */
#endif

#include "apb_view.h"
#include "apb_vm.h"

static char line[APB_VIEW_LINE];

static void item_line(const char *what, uint16_t item)
{
    char *p = apb_view_put(line, what);

    apb_view_put(p, item < APB_ITEM_COUNT ? apb_item_names[item] : (const char *)"?");
    apb_view_out(line, 0);
}

void apb_view_receipt(const apb_receipt *r, uint8_t stamped)
{
    uint8_t i;
    char *p;

    apb_view_out(r->outcome == APB_VM_COMPLETE ? "~ Departure complete ~"
                                               : "~ Departure failed ~", 0);
    apb_view_out("", 0);
    apb_view_out("Your receipt:", 0);
    if (r->xp) {
        p = apb_view_unum(apb_view_put(line, "  "), r->xp);
        apb_view_put(p, " XP");
        apb_view_out(line, 0);
    }
    if (r->debt_paid) {
        p = apb_view_unum(apb_view_put(line, "  "), r->debt_paid);
        apb_view_put(p, " Debt paid");
        apb_view_out(line, 0);
    }
    if (r->debt_added) {
        p = apb_view_unum(apb_view_put(line, "  "), r->debt_added);
        apb_view_put(p, " Debt added");
        apb_view_out(line, 0);
    }
    for (i = 0; i < r->gained_count; ++i) item_line("  Gained: ", r->gained[i]);
    for (i = 0; i < r->lost_count; ++i) item_line("  Lost: ", r->lost[i]);
    if (r->echo_count) {
        p = apb_view_unum(apb_view_put(line, "  "), r->echo_count);
        p = apb_view_put(p, r->echo_count == 1 ? " Echo" : " Echoes");
        apb_view_put(p, " will follow you.");
        apb_view_out(line, 0);
    }
    apb_view_out("", 0);
    if (stamped) {
        apb_view_out("Your Travel Stamp. Type it in at the Waystation to have this trip "
                     "stamped into your Passport:", 1);
        apb_view_out("", 0);
    } else {
        apb_view_out("You travelled without a Boarding Pass, so this trip can't be "
                     "stamped.", 1);
    }
}
