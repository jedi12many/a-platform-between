/*
 * A tiny walk through the rules core: make a traveler, roll some checks, carry a
 * pulse rifle through three realms, plant an Echo, print the Passport.
 * Builds natively and as a Commodore 64 program (40 columns).
 */
#include <stdio.h>

#include "apb.h"
#include "apb_registry.h"

static const char *const result_names[] = { "FAIL", "AT A COST", "SUCCESS", "CRITICAL" };

static const char *const ranged_tech[] = {
    "SLING", "SLING", "CROSSBOW", "CROSSBOW", "MUSKET",
    "MUSKET", "RIFLE", "RIFLE", "PULSE RIFLE", "PULSE RIFLE"
};
static const char *const ranged_magic[] = {
    "SLING", "HEX-SLING", "HEX-SLING", "HEX-SLING", "WAND",
    "WAND", "WAND", "STORM STAFF", "STORM STAFF", "STORM STAFF"
};

static void show_translation(const char *realm_name, const apb_realm *realm,
                             const apb_item_def *item, uint8_t forced)
{
    apb_translation t;
    const char *form;

    apb_translate(item, realm, APB_ALL_ARCHETYPES, forced, &t);
    switch (t.form) {
    case APB_FORM_TECH:  form = ranged_tech[t.level];  break;
    case APB_FORM_MAGIC: form = ranged_magic[t.level]; break;
    case APB_FORM_RELIC: form = "RELIC";               break;
    default:             form = "PULSE RIFLE";         break;
    }
    printf("%-10s TL%u ML%u: %s T%u%s\n", realm_name, realm->tl, realm->ml, form,
           t.tier, t.dissonance ? " +DIS" : "");
}

int main(void)
{
    apb_character ch;
    apb_character back;
    apb_rng rng;
    apb_roll roll;
    apb_item_def rifle;
    apb_realm realm;
    char pw[APB_PASSWORD_BUF];
    uint8_t i;
    uint8_t line;

    apb_character_init(&ch, "Kestrel", APB_SALVAGED, APB_WARDEN);
    ch.stat[APB_MIGHT] = 5;
    ch.stat[APB_GRIT] = 4;
    ch.debt = 50000u;
    ch.equipped[0] = APB_ITEM_PULSE_RIFLE;

    printf("A PLATFORM BETWEEN - RULES CORE\n\n");
    printf("%s, SALVAGED WARDEN, LVL %u\n", ch.name, ch.level);
    printf("HEALTH %u  DEBT %u\n\n", apb_health_max(&ch), ch.debt);

    apb_rng_seed(&rng, 1985);
    for (i = 0; i < 3; ++i) {
        apb_check(&rng, ch.stat[APB_MIGHT], 0, 2, &roll);
        printf("MIGHT CHECK: %u+%u => %d %s\n", roll.die1, roll.die2, roll.total,
               result_names[roll.result]);
    }

    rifle.archetype = APB_ARCH_RANGED;
    rifle.tier = 4;
    rifle.damage = APB_DMG_ENERGY;
    rifle.native_tl = 8;
    rifle.native_ml = 0;
    printf("\n");
    realm.tl = 8; realm.ml = 0; show_translation("KEPLER-9", &realm, &rifle, 0);
    realm.tl = 2; realm.ml = 1; show_translation("BRONZE", &realm, &rifle, 0);
    realm.tl = 0; realm.ml = 7; show_translation("MYTHIC", &realm, &rifle, 0);
    realm.tl = 2; realm.ml = 1; show_translation("FORCED", &realm, &rifle, 1);

    apb_echo_set(&ch, APB_ECHO_WOLF_PUP, APB_WOLF_PUP_SAVED, NULL);
    apb_gain_xp(&ch, 40);
    printf("\nSAVED THE WOLF PUP. NOW LVL %u.\n", ch.level);

    apb_passport_encode(&ch, pw);
    printf("\nPASSPORT:\n");
    for (line = 0; line < APB_PASSWORD_LINES; ++line) {
        printf("  %.*s\n", APB_PASSWORD_LINE, pw + line * APB_PASSWORD_LINE);
    }

    if (apb_passport_decode(pw, &back, NULL) == APB_PP_OK
        && apb_echo_get(&back, APB_ECHO_WOLF_PUP) == APB_WOLF_PUP_SAVED) {
        printf("\nREAD BACK: %s, LVL %u, WOLF REMEMBERS.\n", back.name, back.level);
    } else {
        printf("\nREAD BACK FAILED\n");
        return 1;
    }
    return 0;
}
