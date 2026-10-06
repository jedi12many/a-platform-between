#include "apb.h"

/* Echo slots are kept oldest first, empty slots (id 0) at the end. */

uint8_t apb_echo_get(const apb_character *ch, uint16_t id)
{
    uint8_t i;

    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        if (ch->echo[i].id == id) {
            return ch->echo[i].state;
        }
    }
    return APB_ECHO_UNSET;
}

uint8_t apb_echo_get_or(const apb_character *ch, uint16_t id, uint8_t canon_default)
{
    uint8_t state = apb_echo_get(ch, id);

    return state == APB_ECHO_UNSET ? canon_default : state;
}

static void remove_slot(apb_character *ch, uint8_t slot)
{
    uint8_t i;

    for (i = slot; i + 1 < APB_ECHO_SLOTS; ++i) {
        ch->echo[i] = ch->echo[i + 1];
    }
    ch->echo[APB_ECHO_SLOTS - 1].id = 0;
    ch->echo[APB_ECHO_SLOTS - 1].state = APB_ECHO_UNSET;
}

uint8_t apb_echo_set(apb_character *ch, uint16_t id, uint8_t state, apb_echo *evicted)
{
    uint8_t i;
    uint8_t did_evict = 0;

    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        if (ch->echo[i].id == id) {
            ch->echo[i].state = state;
            return 0;
        }
    }

    if (ch->echo[APB_ECHO_SLOTS - 1].id != 0) {
        if (evicted) {
            *evicted = ch->echo[0];
        }
        remove_slot(ch, 0);
        did_evict = 1;
    }

    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        if (ch->echo[i].id == 0) {
            ch->echo[i].id = id;
            ch->echo[i].state = state;
            break;
        }
    }
    return did_evict;
}

void apb_echo_clear(apb_character *ch, uint16_t id)
{
    uint8_t i;

    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        if (ch->echo[i].id == id) {
            remove_slot(ch, i);
            return;
        }
    }
}
