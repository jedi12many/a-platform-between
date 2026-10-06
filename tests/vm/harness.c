/*
 * A HAL for tests: reads a Departure's DEPOT and CARnn files from a directory, takes
 * menu picks from a list, and writes a plain transcript. Builds natively and for
 * sim65, so the same playthrough can be compared on both.
 *
 *   harness DIR SEED SCRIPT       e.g. harness build/vm/tiny 1985 2,1
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

uint8_t hal_menu(const char *const *labels, uint8_t count)
{
    uint8_t i;

    for (i = 0; i < count; ++i) {
        printf("  %u) %s\n", i + 1, labels[i]);
    }
    next_token();
    printf("> %s\n", tok);
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
    (void)name; (void)src; (void)len;
    return HAL_IO_ERROR;
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

static void print_receipt(const apb_receipt *r)
{
    uint8_t i;

    printf("[receipt: departure %u, %s, xp %u, debt paid %u added %u",
           r->departure, r->outcome == APB_VM_COMPLETE ? "complete" : "failed",
           r->xp, r->debt_paid, r->debt_added);
    printf(", gained");
    for (i = 0; i < r->gained_count; ++i) printf(" %u", r->gained[i]);
    printf(", lost");
    for (i = 0; i < r->lost_count; ++i) printf(" %u", r->lost[i]);
    printf(", echoes");
    for (i = 0; i < r->echo_count; ++i) printf(" %u=%u", r->echoes[i].id, r->echoes[i].state);
    printf("]\n");
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

    if (picks[0] == ':') {
        apb_desk_run(&traveler);
    }
    if (apb_vm_board(&traveler, (uint16_t)atoi(argv[2])) != 0) {
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
