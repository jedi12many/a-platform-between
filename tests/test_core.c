/*
 * Rules-core tests. The same file runs natively and on the sim65 6502
 * simulator; every expected value below must hold on both, which is how we
 * know a fight or a Passport comes out the same on every platform.
 */
#include <stdio.h>
#include <string.h>

#include "apb.h"
#include "apb_registry.h"
#include "apb_hal.h"   /* not used yet; compiled here so both toolchains check it */

static unsigned failures = 0;
static unsigned checks = 0;

#define CHECK(cond) do { \
    ++checks; \
    if (!(cond)) { ++failures; printf("FAIL line %d: %s\n", __LINE__, #cond); } \
} while (0)

static void test_rng(void)
{
    apb_rng rng;
    uint16_t counts[6];
    uint16_t i;
    uint8_t face;

    apb_rng_seed(&rng, 1);
    CHECK(apb_rng_next(&rng) == 0x8181u);
    CHECK(apb_rng_next(&rng) == 0x6021u);
    CHECK(apb_rng_next(&rng) == 0xE999u);

    apb_rng_seed(&rng, 0);
    CHECK(rng.state != 0);

    /* Every face shows up, none wildly over-represented, over 600 rolls. */
    memset(counts, 0, sizeof(counts));
    apb_rng_seed(&rng, 2026);
    for (i = 0; i < 600; ++i) {
        face = apb_d6(&rng);
        CHECK(face >= 1 && face <= 6);
        ++counts[face - 1];
    }
    for (i = 0; i < 6; ++i) {
        CHECK(counts[i] > 70 && counts[i] < 130);
    }
}

static void test_check(void)
{
    apb_rng rng;
    apb_roll roll;

    CHECK(apb_classify(5) == APB_FAIL);
    CHECK(apb_classify(-3) == APB_FAIL);
    CHECK(apb_classify(6) == APB_COST);
    CHECK(apb_classify(8) == APB_COST);
    CHECK(apb_classify(9) == APB_SUCCESS);
    CHECK(apb_classify(11) == APB_SUCCESS);
    CHECK(apb_classify(12) == APB_CRIT);

    apb_rng_seed(&rng, 42);
    apb_check(&rng, 4, 1, 2, &roll);
    CHECK(roll.total == roll.die1 + roll.die2 + 4 + 1 - 2);
    CHECK(roll.result == apb_classify(roll.total));
    /* Golden values: the same seed must give the same roll everywhere. */
    CHECK(roll.die1 == 2);
    CHECK(roll.die2 == 2);
}

static void test_character(void)
{
    apb_character ch;

    apb_character_init(&ch, "Kestrel", APB_SALVAGED, APB_WARDEN);
    CHECK(strcmp(ch.name, "KESTREL") == 0);
    CHECK(ch.level == 1);
    CHECK(apb_health_max(&ch) == 3 * 3 + 1 * 2);

    apb_character_init(&ch, "a very long name", APB_HUMAN, APB_ROGUE);
    CHECK(strcmp(ch.name, "A VERY L") == 0);

    apb_character_init(&ch, "Old Mae ", APB_HUMAN, APB_MEDIC);
    CHECK(strcmp(ch.name, "OLD MAE") == 0);

    apb_character_init(&ch, "Zed", APB_HUMAN, APB_TINKER);
    CHECK(apb_gain_xp(&ch, 14) == 0);
    CHECK(apb_gain_xp(&ch, 1) == 1);
    CHECK(ch.level == 2 && ch.xp == 0);
    CHECK(apb_gain_xp(&ch, 20 + 25 + 3) == 2);
    CHECK(ch.level == 4 && ch.xp == 3);

    ch.level = APB_LEVEL_MAX;
    CHECK(apb_gain_xp(&ch, 200) == 0);
    CHECK(ch.level == APB_LEVEL_MAX && ch.xp == 0);
}

static void test_translate(void)
{
    /* The examples from docs/translation.md. */
    apb_item_def rifle;
    apb_item_def bike;
    apb_realm kepler;
    apb_realm bronze;
    apb_realm mythic;
    apb_translation t;

    rifle.archetype = APB_ARCH_RANGED; rifle.tier = 4; rifle.damage = APB_DMG_ENERGY;
    rifle.native_tl = 8; rifle.native_ml = 0;
    bike.archetype = APB_ARCH_VEHICLE; bike.tier = 3; bike.damage = APB_DMG_KINETIC;
    bike.native_tl = 8; bike.native_ml = 0;
    kepler.tl = 8; kepler.ml = 0;
    bronze.tl = 2; bronze.ml = 1;
    mythic.tl = 0; mythic.ml = 7;

    apb_translate(&rifle, &kepler, APB_ALL_ARCHETYPES, 0, &t);
    CHECK(t.form == APB_FORM_NATIVE && t.tier == 4 && t.dissonance == 0);

    apb_translate(&rifle, &bronze, APB_ALL_ARCHETYPES, 0, &t);
    CHECK(t.form == APB_FORM_TECH && t.level == 2 && t.tier == 4);

    apb_translate(&rifle, &mythic, APB_ALL_ARCHETYPES, 0, &t);
    CHECK(t.form == APB_FORM_MAGIC && t.level == 7 && t.tier == 4);

    apb_translate(&rifle, &bronze, APB_ALL_ARCHETYPES, 1, &t);
    CHECK(t.form == APB_FORM_NATIVE && t.tier == 5 && t.dissonance == 1);

    /* An engine without vehicle rules shows the bike as a relic. */
    apb_translate(&bike, &kepler, APB_ALL_ARCHETYPES & ~(1u << APB_ARCH_VEHICLE), 0, &t);
    CHECK(t.form == APB_FORM_RELIC && t.tier == 3);

    rifle.tier = APB_TIER_MAX;
    apb_translate(&rifle, &bronze, APB_ALL_ARCHETYPES, 1, &t);
    CHECK(t.tier == APB_TIER_MAX);

    CHECK(apb_dissonance_band(2) == APB_DIS_CALM);
    CHECK(apb_dissonance_band(3) == APB_DIS_WARY);
    CHECK(apb_dissonance_band(5) == APB_DIS_MISFIRE);
    CHECK(apb_dissonance_band(7) == APB_DIS_NOTICED);
    CHECK(apb_dissonance_band(9) == APB_DIS_BACKLASH);
}

static void test_echoes(void)
{
    apb_character ch;
    apb_echo evicted;
    uint16_t id;

    apb_character_init(&ch, "Kestrel", APB_SALVAGED, APB_WARDEN);
    CHECK(apb_echo_get(&ch, APB_ECHO_WOLF_PUP) == APB_ECHO_UNSET);
    CHECK(apb_echo_get_or(&ch, APB_ECHO_WOLF_PUP, APB_WOLF_PUP_LEFT) == APB_WOLF_PUP_LEFT);

    CHECK(apb_echo_set(&ch, APB_ECHO_WOLF_PUP, APB_WOLF_PUP_SAVED, &evicted) == 0);
    CHECK(apb_echo_get(&ch, APB_ECHO_WOLF_PUP) == APB_WOLF_PUP_SAVED);
    CHECK(apb_echo_get_or(&ch, APB_ECHO_WOLF_PUP, APB_WOLF_PUP_LEFT) == APB_WOLF_PUP_SAVED);

    /* Payoffs transform an Echo in place. */
    apb_echo_set(&ch, APB_ECHO_WOLF_PUP, APB_WOLF_PUP_SWORN, &evicted);
    CHECK(apb_echo_get(&ch, APB_ECHO_WOLF_PUP) == APB_WOLF_PUP_SWORN);

    /* A Rewind clears it again. */
    apb_echo_clear(&ch, APB_ECHO_WOLF_PUP);
    CHECK(apb_echo_get(&ch, APB_ECHO_WOLF_PUP) == APB_ECHO_UNSET);

    /* Fill all 8 slots; the 9th evicts the oldest into the Legend. */
    for (id = 1; id <= APB_ECHO_SLOTS; ++id) {
        CHECK(apb_echo_set(&ch, id, 1, &evicted) == 0);
    }
    CHECK(apb_echo_set(&ch, 100, 2, &evicted) == 1);
    CHECK(evicted.id == 1 && evicted.state == 1);
    CHECK(apb_echo_get(&ch, 1) == APB_ECHO_UNSET);
    CHECK(apb_echo_get(&ch, 100) == 2);
    CHECK(ch.echo[APB_ECHO_SLOTS - 1].id == 100);
}

static void make_kestrel(apb_character *ch)
{
    apb_character_init(ch, "Kestrel", APB_SALVAGED, APB_WARDEN);
    ch->level = 7;
    ch->xp = 31;
    ch->stat[APB_MIGHT] = 6;
    ch->stat[APB_GRIT] = 5;
    ch->stat[APB_FATE] = 2;
    ch->perks[0] = 0x8001u;
    ch->perks[1] = 0x00F0u;
    ch->debt = 48210u;
    ch->equipped[0] = APB_ITEM_PULSE_RIFLE;
    ch->equipped[1] = APB_ITEM_BALLISTIC_WEAVE;
    ch->pack[0] = APB_ITEM_MERIDIAN_CORE;
    ch->pack[5] = 1023;
    apb_echo_set(ch, APB_ECHO_MERIDIAN, APB_MERIDIAN_CARRIED, NULL);
    apb_echo_set(ch, APB_ECHO_WOLF_PUP, APB_WOLF_PUP_SAVED, NULL);
    apb_echo_set(ch, APB_ECHO_JACE_CUTTER, APB_JACE_SPARED, NULL);
    ch->flags = APB_FLAG_VERIFIED;
}

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static apb_character ch;
static apb_character back;
static char pw[APB_PASSWORD_BUF];
static char spaced[APB_PASSWORD_BUF + 8];
static char typo[APB_PASSWORD_BUF];

static void test_passport(void)
{
    uint8_t line;
    uint8_t i;
    uint8_t j;

    make_kestrel(&ch);
    CHECK(apb_passport_encode(&ch, pw) == APB_PP_OK);
    CHECK(strlen(pw) == APB_PASSWORD_LEN);
    printf("passport: %s\n", pw);

    /* Golden password: identical on every platform. */
    CHECK(strcmp(pw, "2PB794AR0A0WZCD9K50J0103RBRMG080G000000N001G00000007ZR0E08GZ2M0000000000001MSA0Y") == 0);

    CHECK(apb_passport_decode(pw, &back, NULL) == APB_PP_OK);
    CHECK(memcmp(&ch, &back, sizeof(ch)) == 0);

    /* Four lines with spaces, in lower case, still decodes. */
    j = 0;
    for (i = 0; i < APB_PASSWORD_LEN; ++i) {
        if (i > 0 && i % APB_PASSWORD_LINE == 0) {
            spaced[j++] = ' ';
        }
        spaced[j++] = (pw[i] >= 'A' && pw[i] <= 'Z') ? (char)(pw[i] - 'A' + 'a') : pw[i];
    }
    spaced[j] = '\0';
    CHECK(apb_passport_decode(spaced, &back, NULL) == APB_PP_OK);
    CHECK(memcmp(&ch, &back, sizeof(ch)) == 0);

    /* One wrong symbol is caught, and the line is named. */
    strcpy(typo, pw);
    typo[45] = (typo[45] == '7') ? '8' : '7';
    line = 0;
    CHECK(apb_passport_decode(typo, &back, &line) == APB_PP_LINE_CHECK);
    CHECK(line == 3);

    /* Two adjacent symbols swapped is caught too. */
    strcpy(typo, pw);
    for (i = 0; i + 1 < APB_PASSWORD_LINE - 1; ++i) {
        if (typo[i] != typo[i + 1]) {
            char c = typo[i];
            typo[i] = typo[i + 1];
            typo[i + 1] = c;
            break;
        }
    }
    CHECK(apb_passport_decode(typo, &back, NULL) != APB_PP_OK);

    CHECK(apb_passport_decode("TOOSHORT", &back, NULL) == APB_PP_LENGTH);
    strcpy(typo, pw);
    typo[3] = 'U';
    CHECK(apb_passport_decode(typo, &back, NULL) == APB_PP_SYMBOL);

    /* Fields that don't fit the format are refused, not silently cut. */
    make_kestrel(&ch);
    ch.stat[APB_MIGHT] = 16;
    CHECK(apb_passport_encode(&ch, pw) == APB_PP_RANGE);
    make_kestrel(&ch);
    ch.equipped[2] = 1024;
    CHECK(apb_passport_encode(&ch, pw) == APB_PP_RANGE);
}

int main(void)
{
    test_rng();
    test_check();
    test_character();
    test_translate();
    test_echoes();
    test_passport();

    printf("%u checks, %u failed\n", checks, failures);
    return failures ? 1 : 0;
}
