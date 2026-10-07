/*
 * A HAL for tests: reads a Departure's DEPOT and CARnn files from a directory, takes
 * menu picks from a list, and writes a plain transcript. Builds natively and for
 * sim65, so the same playthrough can be compared on both.
 *
 *   harness DIR SEED SCRIPT       e.g. harness build/vm/tiny 1985 2,1
 *
 * SEED+LEVEL (e.g. 48213+8) boards the built-in traveler at that level: a veteran, for
 * the Deep Yards' deep floors.
 *
 * SEED '-' asks for a Boarding Pass at the desk (after the Passport, or for the built-in
 * traveler), which then seeds the dice; travelling without one uses seed 1.
 *
 * A pick of 'S' saves the trip (DIR/SAVE) and quits when the menu comes back, the way a
 * player would; SEED 'resume' picks the saved trip up again instead of boarding.
 *
 * In a fight, a turn is a pick written X.Y.K.T: move to X,Y, then action K (APB_ACT_*)
 * on target T, e.g. 3.1.0.1 (move to 3,1 and attack fighter 1); q plays the turn on
 * quick (apb_battle_quick). Events print like the battle logs in tests/battle/.
 *
 * SCRIPT is a comma-separated list. A number picks from a menu (1-based); a token
 * starting with ':' is a typed line (':' alone is a blank line). If the script starts
 * with a typed line, the traveler boards at the boarding desk; otherwise the built-in
 * test traveler (Kestrel) is used. When the script runs out, the transcript ends with
 * "[out of picks]".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apb.h"
#include "apb_desk.h"

/* The 6502 has no room for the whole engine in one test program, so it's built twice
 * (Makefile): build/harness.sim without the Deep Yards (APB_VM_NO_YARDS), and
 * build/harness-yards.sim without the boarding desk (APB_HARNESS_NO_DESK): the yards'
 * playthroughs board the built-in traveler. */
#include "apb_hal.h"
#include "apb_vm.h"

static const char *dir;
static const char *picks;
static char para[1024];
static unsigned para_len;
static char path[160];

/* Game text is ASCII; this harness prints it as-is (sim65 and PCs are ASCII). */

void hal_init(void) {}
void hal_shutdown(void) {}

void hal_text_char(char c)
{
    if (para_len + 1 < sizeof(para)) {
        para[para_len++] = c;
    }
}

void hal_text_end(void)
{
    para[para_len] = '\0';
    printf("%s\n", para);
    para_len = 0;
}

void hal_chapter(const char *title)
{
    printf("=== %s\n", title);
}

void hal_pause(void)
{
    printf("[pause]\n");
}

void hal_picture(uint8_t id, const char *name)
{
    printf("[picture %u %s]\n", id, name);
}

void hal_status(const apb_character *ch)
{
    (void)ch;
}

static const char *const stat_names[] = { "MIGHT", "GRACE", "GRIT", "WITS", "PRESENCE", "FATE" };
static const char *const results[] = { "fail", "cost", "success", "crit" };

void hal_check(uint8_t rating, const apb_roll *roll)
{
    printf("[check %s: %u+%d=%d vs %d: %s]\n",
           rating < 6 ? stat_names[rating] : apb_skill_names[rating - 16],
           roll->roll, roll->total - roll->roll, roll->total, roll->tn,
           results[roll->result]);
}

/* ------------------------------------------------------------- battles */

static const char *const endings[] = { "on", "won", "lost", "fled" };
static const char tile_chars[] = ".#O~+^=>";

void hal_battle_begin(void)
{
    uint8_t x;
    uint8_t y;
    uint8_t i;
    char c;
    apb_fighter f;

    printf("[fight: %u x %u, %u fighters, health %u]\n", apb_battle_width(),
           apb_battle_height(), apb_battle_count(), apb_vm_health());
    for (y = 0; y < apb_battle_height(); ++y) {
        printf("  ");
        for (x = 0; x < apb_battle_width(); ++x) {
            c = tile_chars[apb_battle_tile(x, y) & 7];
            for (i = 0; i < apb_battle_count(); ++i) {
                apb_battle_fighter(i, &f);
                if (f.x == x && f.y == y) c = (char)('0' + i);
            }
            putchar(c);
        }
        putchar('\n');
    }
}

void hal_battle_event(const apb_event *e)
{
    switch (e->kind) {
    case APB_EV_TURN:   printf("round %u: %u's turn\n", e->value, e->actor); break;
    case APB_EV_MOVE:   printf("  %u moves to %u,%u\n", e->actor, e->x, e->y); break;
    case APB_EV_ATTACK:
        printf("  %u attacks %u: %u+%d=%d vs %d: %s, %u damage\n", e->actor, e->target,
               e->roll.roll, e->roll.total - e->roll.roll, e->roll.total, e->roll.tn,
               results[e->roll.result], e->value);
        break;
    case APB_EV_DOWN:   printf("  %u is down\n", e->target); break;
    case APB_EV_HAZARD: printf("  %u takes %u from the ground\n", e->actor, e->value); break;
    case APB_EV_GUARD:  printf("  %u guards\n", e->actor); break;
    case APB_EV_WAIT:   printf("  %u waits\n", e->actor); break;
    case APB_EV_FREE:   printf("  %u gets a free attack on %u\n", e->actor, e->target); break;
    case APB_EV_FLEE:
        if (e->roll.roll) {
            printf("  %u tries to flee: %u+%d=%d vs %d: %s\n", e->actor, e->roll.roll,
                   e->roll.total - e->roll.roll, e->roll.total, e->roll.tn,
                   results[e->roll.result]);
        } else {
            printf("  %u takes the exit\n", e->actor);
        }
        break;
    case APB_EV_GONE:   printf("  %u is gone\n", e->actor); break;
    case APB_EV_END:    break;
    }
}

void hal_battle_end(uint8_t result)
{
    printf("[the fight is %s; health %u]\n", endings[result & 3], apb_vm_health());
}

/* The next script token into `tok`; exits cleanly when the script runs out. */
static char tok[64];

static void next_token(void)
{
    uint8_t n = 0;

    if (!picks || !*picks) {
        printf("[out of picks]\n");
        exit(0);
    }
    while (*picks && *picks != ',' && (unsigned)n + 1u < sizeof(tok)) tok[n++] = *picks++;
    tok[n] = '\0';
    if (*picks == ',') ++picks;
}

static uint8_t quitting;

void hal_battle_turn(uint8_t who, apb_action *out)
{
    unsigned v[4];

    next_token();
    printf("> %s\n", tok);
    if (tok[0] == 'q') {
        apb_battle_quick(who, out);
        printf("  (quick: %u.%u.%u.%u)\n", out->move_x, out->move_y, out->kind, out->target);
        return;
    }
    v[0] = v[1] = v[2] = v[3] = 255;
    sscanf(tok, "%u.%u.%u.%u", &v[0], &v[1], &v[2], &v[3]);
    out->move_x = (uint8_t)v[0];
    out->move_y = (uint8_t)v[1];
    out->kind = (uint8_t)v[2];
    out->target = (uint8_t)v[3];
}

uint8_t hal_menu(const char *const *labels, uint8_t count)
{
    uint8_t i;

    if (quitting) {
        printf("[quit]\n");
        exit(0);
    }
    for (i = 0; i < count; ++i) {
        printf("  %u) %s\n", i + 1, labels[i]);
    }
    next_token();
    printf("> %s\n", tok);
    if (tok[0] == 'S') {
        quitting = 1;
        return APB_MENU_SAVE;
    }
    return (uint8_t)(atoi(tok) - 1);
}

void hal_ask_line(char *out, uint8_t max)
{
    next_token();
    printf("< %s\n", tok + (tok[0] == ':'));
    strncpy(out, tok + (tok[0] == ':'), max);
    out[max - 1] = '\0';
}

void hal_prompt(const char *msg)
{
    printf("* %s\n", msg);
}

uint8_t hal_load(const char *name, uint8_t *dst, uint16_t max, uint16_t *len)
{
    FILE *f;
    size_t n;

    sprintf(path, "%s/%s", dir, name);
    f = fopen(path, "rb");
    if (!f) {
        return HAL_NOT_FOUND;
    }
    n = fread(dst, 1, max, f);
    if (n == max && fgetc(f) != EOF) {
        fclose(f);
        return HAL_TOO_BIG;
    }
    fclose(f);
    *len = (uint16_t)n;
    return HAL_OK;
}

uint8_t hal_save(const char *name, const uint8_t *src, uint16_t len)
{
    FILE *f;
    uint8_t ok;

    sprintf(path, "%s/%s", dir, name);
    f = fopen(path, "wb");
    if (!f) {
        return HAL_IO_ERROR;
    }
    ok = (uint8_t)(fwrite(src, 1, len, f) == len);
    fclose(f);
    return ok ? HAL_OK : HAL_IO_ERROR;
}

void hal_error(const char *msg)
{
    printf("[error: %s]\n", msg);
}

#ifdef APB_VM_TRACE
/* The coverage build lists every instruction it runs on stderr: "car offset". */
void apb_vm_trace(uint8_t car_no, uint16_t pc)
{
    fprintf(stderr, "%u %u\n", car_no, pc);
}
#endif

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static apb_character traveler;
static apb_pass pass;
static char stamp[APB_STAMP_BUF];

static void print_receipt(const apb_receipt *r)
{
    uint8_t i;

    printf("[receipt: departure %u, %s, xp %u, debt paid %u added %u",
           r->departure, r->outcome == APB_VM_COMPLETE ? "complete" : "failed",
           r->xp, r->debt_paid, r->debt_added);
    if (r->ticket) {
        printf(", ticket %lu", (unsigned long)r->ticket);
    }
    printf(", gained");
    for (i = 0; i < r->gained_count; ++i) printf(" %u", r->gained[i]);
    printf(", lost");
    for (i = 0; i < r->lost_count; ++i) printf(" %u", r->lost[i]);
    printf(", echoes");
    for (i = 0; i < r->echo_count; ++i) printf(" %u=%u", r->echoes[i].id, r->echoes[i].state);
    printf("]\n");
    if (r->ticket) {
        apb_stamp_encode(r, stamp);
        printf("[stamp: %s]\n", stamp);
    }
}

int main(int argc, char **argv)
{
    uint8_t base[APB_STAT_COUNT];
    uint8_t result;

    if (argc != 4) {
        printf("usage: harness DIR SEED PICKS\n");
        return 2;
    }
    dir = argv[1];
    picks = argv[3];

    /* The test traveler: Kestrel, a Salvaged Warden (docs/rules-v0.md example). */
    base[APB_MIGHT] = 70; base[APB_GRACE] = 40; base[APB_GRIT] = 60;
    base[APB_WITS] = 45; base[APB_PRESENCE] = 35; base[APB_FATE] = 50;
    apb_character_create(&traveler, "Kestrel", APB_SALVAGED, APB_WARDEN, base,
                         APB_SK_ATHLETICS);
    traveler.equipped[0] = APB_ITEM_PULSE_RIFLE;
    if (strchr(argv[2], '+')) traveler.level = (uint8_t)atoi(strchr(argv[2], '+') + 1);

#ifndef APB_HARNESS_NO_DESK
    if (picks[0] == ':') {
        apb_desk_run(&traveler);
    }
#endif
    if (strcmp(argv[2], "resume") == 0) {
        result = apb_vm_resume();
#ifndef APB_HARNESS_NO_DESK
    } else if (strcmp(argv[2], "-") == 0) {
        if (apb_vm_open() != 0) {
            printf("[refused: %s]\n", apb_vm_error());
            return 0;
        }
        if (apb_desk_pass(&traveler, apb_vm_departure(), &pass)) {
            result = apb_vm_board_pass(&traveler, &pass);
        } else {
            result = apb_vm_board(&traveler, apb_vm_siding() ? apb_desk_yard(1) : 1);
        }
#endif
    } else {
        result = apb_vm_board(&traveler, (uint16_t)atoi(argv[2]));
    }
    if (result != 0) {
        printf("[refused: %s]\n", apb_vm_error());
        return 0;
    }
    result = apb_vm_run();
    if (result == APB_VM_ERROR) {
        return 0;
    }
    print_receipt(apb_vm_receipt());
    printf("[level %u, xp %u, debt %u]\n", apb_vm_character()->level,
           apb_vm_character()->xp, apb_vm_character()->debt);
    return 0;
}
