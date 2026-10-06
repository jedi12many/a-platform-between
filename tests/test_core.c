/*
 * Rules-core tests. The same file runs natively and on the sim65 6502
 * simulator; every expected value below must hold on both, which is how we
 * know a fight or a Passport comes out the same on every platform.
 *
 * Golden values (dice, rolled stats, passwords) come from independent Python
 * implementations (tools/passport/passport.py and the xorshift16 in the docs),
 * never from this code's own output.
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

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static apb_character ch;
static apb_character back;
static char pw[APB_PASSWORD_BUF];
static char spaced[APB_PASSWORD_BUF + 16];
static char typo[APB_PASSWORD_BUF];

static void test_dice(void)
{
    apb_rng rng;
    uint16_t buckets[10];
    uint16_t i;
    uint8_t v;

    apb_rng_seed(&rng, 1);
    CHECK(apb_rng_next(&rng) == 0x8181u);
    CHECK(apb_rng_next(&rng) == 0x6021u);
    CHECK(apb_rng_next(&rng) == 0xE999u);

    apb_rng_seed(&rng, 0);
    CHECK(rng.state != 0);

    apb_rng_seed(&rng, 42);
    CHECK(apb_d100(&rng) == 27);
    CHECK(apb_d100(&rng) == 22);
    CHECK(apb_d100(&rng) == 5);
    CHECK(apb_d100(&rng) == 55);
    CHECK(apb_d100(&rng) == 19);

    /* 1000 rolls: all 1..100, and every block of ten roughly fair. */
    memset(buckets, 0, sizeof(buckets));
    apb_rng_seed(&rng, 2026);
    for (i = 0; i < 1000; ++i) {
        v = apb_d100(&rng);
        CHECK(v >= 1 && v <= 100);
        ++buckets[(v - 1) / 10];
    }
    for (i = 0; i < 10; ++i) {
        CHECK(buckets[i] > 60 && buckets[i] < 140);
    }
    for (i = 0; i < 600; ++i) {
        v = apb_d6(&rng);
        CHECK(v >= 1 && v <= 6);
    }
}

static void test_resolve(void)
{
    apb_rng rng;
    apb_roll roll;

    /* Beat the TN. Rating 62 against a normal task (TN 100). */
    CHECK(apb_resolve(39, 39 + 62, 100) == APB_SUCCESS);   /* 101 beats 100      */
    CHECK(apb_resolve(38, 38 + 62, 100) == APB_COST);      /* 100 only ties      */
    CHECK(apb_resolve(19, 19 + 62, 100) == APB_COST);      /* 81: within 20      */
    CHECK(apb_resolve(18, 18 + 62, 100) == APB_FAIL);      /* 80: 20 under       */
    CHECK(apb_resolve(44, 44 + 62, 100) == APB_CRIT);      /* doubles, success   */
    CHECK(apb_resolve(33, 33 + 62, 100) == APB_COST);      /* doubles, no success */
    CHECK(apb_resolve(100, 100, 250) == APB_CRIT);         /* natural 100        */
    CHECK(apb_resolve(1, 1 + 200, 100) == APB_FAIL);       /* natural 01         */

    /* Exact chances. A rating is its chance on a normal task. */
    CHECK(apb_chance(62, APB_TN_NORMAL) == 62);
    CHECK(apb_chance(62, APB_TN_HARD) == 42);
    CHECK(apb_chance(100, 150) == 50);                     /* 100 against 100    */
    CHECK(apb_chance(100, APB_TN_NORMAL) == 99);           /* only 01 fails      */
    CHECK(apb_chance(0, 150) == 1);                        /* only 100 succeeds  */
    CHECK(apb_chance(-50, 250) == 1);

    /* Golden rolls for seed 42 (27, 22, 5) from Python. */
    apb_rng_seed(&rng, 42);
    apb_check(&rng, 90, 0, 110, &roll);
    CHECK(roll.roll == 27 && roll.total == 117 && roll.result == APB_SUCCESS);
    apb_check(&rng, 60, 20, 100, &roll);
    CHECK(roll.roll == 22 && roll.total == 102 && roll.result == APB_CRIT);
    apb_check(&rng, 50, 0, 70, &roll);
    CHECK(roll.roll == 5 && roll.total == 55 && roll.result == APB_COST);
}

static void test_defense(void)
{
    /* TN = 50 + defense: 100 against 100 is a coin flip. */
    CHECK(apb_defense_tn(100, 0) == 150);
    CHECK(apb_defense_tn(0, 0) == 50);
    CHECK(apb_defense_tn(20, 60) == 50);                   /* stops at 0         */
    CHECK(apb_defense_tn(-30, 0) == 50);

    /* The iron golem (Armor 90, 30 against lightning) from docs/rules-v0.md. */
    CHECK(apb_defense_tn(90, 0) == 140);
    CHECK(apb_chance(70, apb_defense_tn(90, 0)) == 30);        /* the fighter alone */
    CHECK(apb_chance(70, apb_defense_tn(90, 20)) == 50);       /* after Rust        */
    CHECK(apb_chance(70 + 20, apb_defense_tn(90, 0)) == 50);   /* with Overclock    */
    CHECK(apb_chance(70 + 20, apb_defense_tn(90, 20)) == 70);  /* both              */
    CHECK(apb_chance(70, apb_defense_tn(90, 20)) == 50);       /* adamant, Pierce 20 */
    CHECK(apb_chance(60, apb_defense_tn(30, 0)) == 80);        /* lightning         */
    CHECK(apb_chance(70 - 20, apb_defense_tn(40, 0)) == 60);   /* called shot, seam */
}

static void make_kestrel(apb_character *out)
{
    uint8_t base[APB_STAT_COUNT];

    base[APB_MIGHT] = 70; base[APB_GRACE] = 40; base[APB_GRIT] = 60;
    base[APB_WITS] = 45; base[APB_PRESENCE] = 35; base[APB_FATE] = 50;
    apb_character_create(out, "Kestrel", APB_SALVAGED, APB_WARDEN, base,
                         APB_SK_ATHLETICS);
}

static void test_creation(void)
{
    apb_rng rng;
    uint8_t base[APB_STAT_COUNT];
    uint8_t i;
    uint16_t n;
    uint8_t v;

    /* Point-buy: 25 everywhere, 150 points, nothing above 70. */
    base[APB_MIGHT] = 70; base[APB_GRACE] = 40; base[APB_GRIT] = 60;
    base[APB_WITS] = 45; base[APB_PRESENCE] = 35; base[APB_FATE] = 50;
    CHECK(apb_pointbuy_valid(base));
    base[APB_FATE] = 51;
    CHECK(!apb_pointbuy_valid(base));          /* 151 points */
    base[APB_FATE] = 49;
    CHECK(!apb_pointbuy_valid(base));          /* 149 points */
    base[APB_FATE] = 50; base[APB_MIGHT] = 71; base[APB_GRIT] = 59;
    CHECK(!apb_pointbuy_valid(base));          /* over 70    */
    base[APB_MIGHT] = 70; base[APB_GRIT] = 60; base[APB_GRACE] = 24; base[APB_WITS] = 61;
    CHECK(!apb_pointbuy_valid(base));          /* under 25   */

    /* A Salvaged Warden: +10 and +5 Might, tags Melee, Endurance and one pick. */
    make_kestrel(&ch);
    CHECK(strcmp(ch.name, "KESTREL") == 0 && ch.level == 1 && ch.xp == 0);
    CHECK(ch.stat[APB_MIGHT] == 85 && ch.stat[APB_GRIT] == 60);
    CHECK(ch.tags == ((1u << APB_SK_MELEE) | (1u << APB_SK_ENDURANCE)
                      | (1u << APB_SK_ATHLETICS)));
    CHECK(ch.training[APB_SK_MELEE] == 20 && ch.training[APB_SK_TECH] == 0);
    CHECK(apb_skill(&ch, APB_SK_MELEE) == 85 / 2 + 20);
    CHECK(apb_skill(&ch, APB_SK_TECH) == 45 / 2);
    CHECK(apb_health_max(&ch) == 10 + 60 / 4 + 2);

    /* The extra tag can't repeat a class tag. */
    CHECK(apb_character_create(&ch, "Wren", APB_GLASSFOLK, APB_MEDIC, base,
                               APB_SK_MEDICINE) == 0);
    CHECK(apb_character_create(&ch, "Wren", APB_GLASSFOLK, APB_MEDIC, base,
                               APB_SKILL_COUNT) == 0);

    /* Rolled stats: 3d6 x 5. Golden values from Python. */
    apb_rng_seed(&rng, 1985);
    apb_roll_stats(&rng, base);
    CHECK(base[0] == 45 && base[1] == 55 && base[2] == 40);
    CHECK(base[3] == 70 && base[4] == 40 && base[5] == 15);
    apb_rng_seed(&rng, 7);
    for (n = 0; n < 300; ++n) {
        v = apb_roll_stat(&rng);
        CHECK(v >= 15 && v <= 90 && v % 5 == 0);
    }
    for (i = 0; i < APB_CLASS_COUNT; ++i) {
        CHECK(apb_class_tags[i][0] != apb_class_tags[i][1]);
    }
}

static void test_progression(void)
{
    uint8_t i;

    CHECK(apb_xp_award(300, 5, 10) == 300);
    CHECK(apb_xp_award(300, 10, 10) == 300);
    CHECK(apb_xp_award(300, 11, 10) == 270);
    CHECK(apb_xp_award(300, 15, 10) == 150);
    CHECK(apb_xp_award(300, 19, 10) == 30);
    CHECK(apb_xp_award(300, 20, 10) == 0);

    make_kestrel(&ch);
    CHECK(apb_gain_xp(&ch, 99) == 0 && ch.level == 1 && ch.xp == 99);
    CHECK(apb_gain_xp(&ch, 1) == 1 && ch.level == 2 && ch.xp == 0);
    CHECK(ch.stat_points == 1);
    CHECK(ch.skill_points == 1 + 45 / 20);
    CHECK(apb_gain_xp(&ch, 250) == 2 && ch.level == 4 && ch.xp == 50);
    CHECK(ch.stat_points == 3 && ch.skill_points == 9);

    /* Raises cost more the better you are. */
    CHECK(apb_skill_raise_cost(49) == 1 && apb_skill_raise_cost(50) == 2);
    CHECK(apb_skill_raise_cost(74) == 2 && apb_skill_raise_cost(75) == 3);
    CHECK(apb_skill_raise_cost(89) == 3 && apb_skill_raise_cost(90) == 4);

    /* Melee is at 62: 2 points, and tagged, so +2 training. */
    CHECK(apb_raise_skill(&ch, APB_SK_MELEE) && ch.training[APB_SK_MELEE] == 22);
    CHECK(ch.skill_points == 7);
    /* Tech is at 22: 1 point, untagged, +1. */
    CHECK(apb_raise_skill(&ch, APB_SK_TECH) && ch.training[APB_SK_TECH] == 1);
    CHECK(ch.skill_points == 6);
    CHECK(apb_raise_stat(&ch, APB_WITS) && ch.stat[APB_WITS] == 46 && ch.stat_points == 2);

    /* Nothing goes past 100. */
    ch.stat[APB_MIGHT] = 100;
    CHECK(!apb_raise_stat(&ch, APB_MIGHT));
    ch.training[APB_SK_MELEE] = 99;
    CHECK(apb_raise_skill(&ch, APB_SK_MELEE) && ch.training[APB_SK_MELEE] == 100);
    CHECK(ch.skill_points == 2);
    ch.skill_points = 3;
    ch.training[APB_SK_PERSUADE] = 80;
    CHECK(!apb_raise_skill(&ch, APB_SK_PERSUADE));   /* rating 97: costs 4 */
    CHECK(apb_skill(&ch, APB_SK_MELEE) == 100);
    ch.stat_points = 0;
    CHECK(!apb_raise_stat(&ch, APB_WITS));

    /* Level 100 is the top. */
    ch.level = 99; ch.xp = 0;
    CHECK(apb_gain_xp(&ch, 1000) == 1 && ch.level == 100 && ch.xp == 0);
    CHECK(apb_gain_xp(&ch, 1000) == 0 && ch.level == 100);
    CHECK(apb_health_max(&ch) == 10 + 60 / 4 + 200);
    for (i = 0; i < APB_STAT_COUNT; ++i) ch.stat[i] = 100;
    CHECK(apb_health_max(&ch) == 235);
}

static void test_registry(void)
{
    apb_realm bronze;
    apb_translation t;

    /* Generated from registry/: spot checks that the tables match the files. */
    CHECK(APB_RACE_COUNT == 7 && APB_CLASS_COUNT == 5 && APB_SKILL_COUNT == 12);
    CHECK(strcmp(apb_race_names[APB_SALVAGED], "Salvaged") == 0);
    CHECK(strcmp(apb_race_names[APB_RAD_DRYAD], "Rad-Dryad") == 0);
    CHECK(strcmp(apb_class_names[APB_CHANNELER], "Channeler") == 0);
    CHECK(strcmp(apb_skill_names[APB_SK_INTUITION], "Intuition") == 0);
    CHECK(apb_race_bonus[APB_SALVAGED] == APB_MIGHT);
    CHECK(apb_class_bonus[APB_MEDIC] == APB_WITS);
    CHECK(apb_class_tags[APB_WARDEN][0] == APB_SK_MELEE);
    CHECK(apb_class_tags[APB_WARDEN][1] == APB_SK_ENDURANCE);
    CHECK(apb_skill_stat[APB_SK_INTUITION] == APB_FATE);

    CHECK(apb_items[APB_ITEM_PULSE_RIFLE].archetype == APB_ARCH_RANGED);
    CHECK(apb_items[APB_ITEM_PULSE_RIFLE].tier == 4);
    CHECK(apb_items[APB_ITEM_PULSE_RIFLE].damage == APB_DMG_ENERGY);
    CHECK(apb_items[APB_ITEM_PULSE_RIFLE].native_tl == 8);
    CHECK(apb_items[APB_ITEM_TICKET_STUB].native_ml == 5);
    CHECK(apb_items[APB_ITEM_NONE].tier == 0);
    CHECK(strcmp(apb_item_names[APB_ITEM_TICKET_STUB], "Blank ticket stub") == 0);
    CHECK(apb_item_names[APB_ITEM_NONE][0] == '\0');

    /* Registry items Translate directly. */
    bronze.tl = 2; bronze.ml = 1;
    apb_translate(&apb_items[APB_ITEM_PULSE_RIFLE], &bronze, APB_ALL_ARCHETYPES, 0, &t);
    CHECK(t.form == APB_FORM_TECH && t.level == 2 && t.tier == 4);

    /* Canon defaults answer for Echoes a character never earned. */
    CHECK(apb_echo_defaults[APB_ECHO_WOLF_PUP] == APB_WOLF_PUP_LEFT);
    CHECK(apb_echo_defaults[APB_ECHO_SEED_VAULT] == APB_SEED_VAULT_DELIVERED);
    apb_character_init(&ch, "Zed", APB_HUMAN, APB_ROGUE);
    CHECK(apb_echo_get_or(&ch, APB_ECHO_JACE_CUTTER,
                          apb_echo_defaults[APB_ECHO_JACE_CUTTER]) == APB_JACE_CUTTER_KILLED);
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
    apb_echo evicted;
    uint16_t id;

    make_kestrel(&ch);
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

static void make_legend(apb_character *out)
{
    uint8_t i;

    apb_character_init(out, "Old Mae", APB_MOTH_FOLK, APB_MEDIC);
    out->level = 100;
    for (i = 0; i < APB_STAT_COUNT; ++i) out->stat[i] = 100;
    out->stat_points = 255;
    out->skill_points = 200;
    out->debt = 65535u;
    out->flags = APB_FLAG_VERIFIED | APB_FLAG_TABLETOP;
    out->tags = (1u << APB_SK_MEDICINE) | (1u << APB_SK_SURVIVAL) | (1u << APB_SK_RANGED);
    for (i = 0; i < APB_SKILL_COUNT; ++i) out->training[i] = (uint8_t)(100 - i);
    for (i = 0; i < APB_POWER_SLOTS; ++i) {
        out->power[i].id = (uint8_t)(i + 1);
        out->power[i].rank = (uint8_t)(100 - i);
    }
    for (i = 0; i < APB_EQUIP_SLOTS; ++i) out->equipped[i] = (uint16_t)(1000 + i);
    for (i = 0; i < APB_PACK_SLOTS; ++i) out->pack[i] = (uint16_t)(1010 + i);
    for (i = 0; i < APB_ECHO_SLOTS; ++i) {
        out->echo[i].id = (uint16_t)(1000 + i);
        out->echo[i].state = (uint8_t)(i % 3 + 1);
    }
}

static void test_passport(void)
{
    uint8_t line;
    uint8_t i;
    uint8_t j;
    uint8_t len;
    char c;

    /* A new character: short password. Golden value from passport.py. */
    make_kestrel(&ch);
    ch.debt = 50000u;
    ch.equipped[0] = APB_ITEM_PULSE_RIFLE;
    apb_echo_set(&ch, APB_ECHO_WOLF_PUP, APB_WOLF_PUP_SAVED, NULL);
    CHECK(apb_passport_encode(&ch, pw) == APB_PP_OK);
    printf("new character: %s\n", pw);
    CHECK(strcmp(pw, "4PB794AR0A0105AM7HDT8V4000RD8000K60M2A4D502008208GRN703") == 0);
    CHECK(apb_passport_decode(pw, &back, NULL) == APB_PP_OK);
    CHECK(memcmp(&ch, &back, sizeof(ch)) == 0);

    /* Spaces between lines and lower case still decode. */
    j = 0;
    len = (uint8_t)strlen(pw);
    for (i = 0; i < len; ++i) {
        if (i > 0 && i % APB_PASSWORD_LINE == 0) {
            spaced[j++] = ' ';
        }
        spaced[j++] = (pw[i] >= 'A' && pw[i] <= 'Z') ? (char)(pw[i] - 'A' + 'a') : pw[i];
    }
    spaced[j] = '\0';
    CHECK(apb_passport_decode(spaced, &back, NULL) == APB_PP_OK);
    CHECK(memcmp(&ch, &back, sizeof(ch)) == 0);

    /* One wrong symbol is caught, and the line is named, even on the short last line. */
    strcpy(typo, pw);
    typo[25] = (typo[25] == '7') ? '8' : '7';
    line = 0;
    CHECK(apb_passport_decode(typo, &back, &line) == APB_PP_LINE_CHECK && line == 2);
    strcpy(typo, pw);
    typo[len - 3] = (typo[len - 3] == '7') ? '8' : '7';
    line = 0;
    CHECK(apb_passport_decode(typo, &back, &line) == APB_PP_LINE_CHECK && line == 3);

    /* Two neighbors swapped is caught too. */
    strcpy(typo, pw);
    for (i = 0; i + 1 < APB_PASSWORD_LINE - 1; ++i) {
        if (typo[i] != typo[i + 1]) {
            c = typo[i];
            typo[i] = typo[i + 1];
            typo[i + 1] = c;
            break;
        }
    }
    CHECK(apb_passport_decode(typo, &back, NULL) != APB_PP_OK);

    /* A missing line, or junk, is refused. */
    strcpy(typo, pw);
    typo[40] = '\0';
    CHECK(apb_passport_decode(typo, &back, NULL) != APB_PP_OK);
    CHECK(apb_passport_decode("TOOSHORT", &back, NULL) != APB_PP_OK);
    CHECK(apb_passport_decode("", &back, NULL) == APB_PP_LENGTH);
    strcpy(typo, pw);
    typo[3] = 'U';
    CHECK(apb_passport_decode(typo, &back, NULL) == APB_PP_SYMBOL);

    /* A level-100 legend with everything filled: the longest password. */
    make_legend(&ch);
    CHECK(apb_passport_encode(&ch, pw) == APB_PP_OK);
    printf("legend: %s\n", pw);
    CHECK(strlen(pw) == 149);
    CHECK(strcmp(pw, "4YR80T2A0CK4069JCK4SS69ZY8ZZZGM54R343HJ0RHW560PZDF7QCBJDQAT6QCR0740B30F20K10Q00MTZ0YY12XRFM3YJQTKZB9KXJZPW7WHZKBYHZTSZD9FXWFM7X6ZAZTVYSFPZXMSZFG0QCRJ") == 0);
    CHECK(apb_passport_decode(pw, &back, NULL) == APB_PP_OK);
    CHECK(memcmp(&ch, &back, sizeof(ch)) == 0);

    /* Fields that don't fit are refused, not silently cut. */
    make_kestrel(&ch);
    ch.stat[APB_MIGHT] = 101;
    CHECK(apb_passport_encode(&ch, pw) == APB_PP_RANGE);
    make_kestrel(&ch);
    ch.equipped[2] = 1024;
    CHECK(apb_passport_encode(&ch, pw) == APB_PP_RANGE);
    make_kestrel(&ch);
    ch.level = 101;
    CHECK(apb_passport_encode(&ch, pw) == APB_PP_RANGE);
}

int main(void)
{
    test_dice();
    test_resolve();
    test_defense();
    test_creation();
    test_progression();
    test_registry();
    test_translate();
    test_echoes();
    test_passport();

    printf("%u checks, %u failed\n", checks, failures);
    return failures ? 1 : 0;
}
