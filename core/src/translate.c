#include "apb.h"

/*
 * Translation, as described in docs/translation.md:
 *   - an item the engine can't present becomes an Unidentified Relic;
 *   - an item the realm can support keeps its native form;
 *   - otherwise it takes the realm's dominant form (tech if TL >= ML, else
 *     magic) at the realm's level, unless forced;
 *   - tier is always conserved; forcing adds one tier and one Dissonance.
 */

void apb_translate(const apb_item_def *item, const apb_realm *realm,
                   uint16_t supported, uint8_t forced, apb_translation *out)
{
    out->tier = item->tier;
    out->dissonance = 0;

    /* Written as a shift-and-test on purpose: cc65 2.19 with -O miscompiles
     * `!(supported & (1u << archetype))`. The 6502 test run catches it. */
    if (((supported >> item->archetype) & 1u) == 0) {
        out->form = APB_FORM_RELIC;
        out->level = 0;
        return;
    }

    if (item->native_tl <= realm->tl && item->native_ml <= realm->ml) {
        out->form = APB_FORM_NATIVE;
        out->level = item->native_tl > item->native_ml ? item->native_tl
                                                       : item->native_ml;
        return;
    }

    if (forced) {
        out->form = APB_FORM_NATIVE;
        out->level = item->native_tl > item->native_ml ? item->native_tl
                                                       : item->native_ml;
        if (out->tier < APB_TIER_MAX) {
            ++out->tier;
        }
        out->dissonance = 1;
        return;
    }

    if (realm->tl >= realm->ml) {
        out->form = APB_FORM_TECH;
        out->level = realm->tl;
    } else {
        out->form = APB_FORM_MAGIC;
        out->level = realm->ml;
    }
}

uint8_t apb_dissonance_band(uint8_t dissonance)
{
    if (dissonance >= 9) return APB_DIS_BACKLASH;
    if (dissonance >= 7) return APB_DIS_NOTICED;
    if (dissonance >= 5) return APB_DIS_MISFIRE;
    if (dissonance >= 3) return APB_DIS_WARY;
    return APB_DIS_CALM;
}
