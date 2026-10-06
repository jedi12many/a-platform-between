/*
 * Applying a receipt to a character (docs/boarding.md, "Applying a receipt").
 */
#include <string.h>

#include "apb.h"

/* Static: the 6502 gives a function at most 256 bytes of locals, and the hub may
 * call this with no report wanted. */
static apb_applied scratch;

static uint8_t remove_item(uint16_t *slots, uint8_t count, uint16_t item)
{
    uint8_t i;

    for (i = 0; i < count; ++i) {
        if (slots[i] == item) {
            slots[i] = 0;
            return 1;
        }
    }
    return 0;
}

static uint8_t add_item(uint16_t *slots, uint8_t count, uint16_t item)
{
    uint8_t i;

    for (i = 0; i < count; ++i) {
        if (slots[i] == 0) {
            slots[i] = item;
            return 1;
        }
    }
    return 0;
}

void apb_receipt_apply(apb_character *ch, const apb_receipt *r, apb_applied *out)
{
    uint8_t i;
    uint8_t now;
    long debt;
    apb_echo evicted;

    if (!out) {
        out = &scratch;
    }
    memset(out, 0, sizeof(*out));

    out->levels = apb_gain_xp(ch, r->xp);

    debt = (long)ch->debt - (long)r->debt_paid + (long)r->debt_added;
    ch->debt = (uint16_t)(debt < 0 ? 0 : debt > 65535L ? 65535u : debt);

    /* Lost before gained: whatever the Departure took makes room for what it gave. The
     * pack is searched first, the same order the VM takes items in. */
    for (i = 0; i < r->lost_count && i < APB_RECEIPT_MAX; ++i) {
        if (!remove_item(ch->pack, APB_PACK_SLOTS, r->lost[i])
            && !remove_item(ch->equipped, APB_EQUIP_SLOTS, r->lost[i])) {
            ++out->gone;
        }
    }
    for (i = 0; i < r->gained_count && i < APB_RECEIPT_MAX; ++i) {
        if (!add_item(ch->pack, APB_PACK_SLOTS, r->gained[i])) {
            out->stored[out->stored_count++] = r->gained[i];
        }
    }

    for (i = 0; i < r->echo_count && i < APB_RECEIPT_MAX; ++i) {
        now = apb_echo_get(ch, r->echoes[i].id);
        if (now != r->echoes[i].was && now != r->echoes[i].state) {
            out->shifted[out->shifted_count++] = r->echoes[i].id;
        }
        if (apb_echo_set(ch, r->echoes[i].id, r->echoes[i].state, &evicted)) {
            out->legend[out->legend_count++] = evicted;
        }
    }
}
