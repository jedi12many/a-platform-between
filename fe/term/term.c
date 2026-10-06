/*
 * The terminal front end: play a Departure in a terminal.
 *
 *   apb [--width N] [--seed N] [--choices FILE] DEPARTURE
 *
 * DEPARTURE is an .apd image or a directory of DEPOT/CARnn files. The player boards at
 * the desk with their Passport, then plays. --choices reads the player's input (menu
 * numbers and typed lines, one per line) from FILE instead of the keyboard, and echoes
 * each one, so a playthrough can be recorded and replayed. Text wraps at --width
 * (default 40, the C64's screen, so writers see what a C64 player sees).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "apb.h"
#include "apb_desk.h"
#include "apb_hal.h"
#include "apb_vm.h"

static unsigned width = 40;
static FILE *input;
static int echo_input;
static const char *source;

/* ---------------------------------------------------------------- input */

static void read_line(char *out, size_t max)
{
    size_t n;

    fflush(stdout);
    if (!fgets(out, (int)max, input)) {
        printf("\n[end of input]\n");
        exit(0);
    }
    n = strlen(out);
    while (n && (out[n - 1] == '\n' || out[n - 1] == '\r')) out[--n] = '\0';
    if (echo_input) printf("%s\n", out);
}

/* ----------------------------------------------------------------- text */

static char para[2048];
static size_t para_len;

/* Print text wrapped at `width`, breaking at spaces; '\n' forces a break. */
static void wrapped(const char *text, const char *indent)
{
    size_t col = 0;
    const char *p = text;
    const char *word;
    size_t len;

    fputs(indent, stdout);
    col = strlen(indent);
    while (*p) {
        if (*p == '\n') {
            printf("\n%s", indent);
            col = strlen(indent);
            ++p;
            continue;
        }
        if (*p == ' ') {
            ++p;
            continue;
        }
        word = p;
        while (*p && *p != ' ' && *p != '\n') ++p;
        len = (size_t)(p - word);
        if (col > strlen(indent) && col + 1 + len > width) {
            printf("\n%s", indent);
            col = strlen(indent);
        } else if (col > strlen(indent)) {
            putchar(' ');
            ++col;
        }
        fwrite(word, 1, len, stdout);
        col += len;
        /* Keep runs of spaces inside fixed lines ("|" lines): print them as they are. */
        while (*p == ' ' && p[1] == ' ') {
            putchar(' ');
            ++col;
            ++p;
        }
    }
    putchar('\n');
}

void hal_init(void) {}
void hal_shutdown(void) {}

void hal_text_char(char c)
{
    if (para_len + 1 < sizeof(para)) para[para_len++] = c;
}

void hal_text_end(void)
{
    para[para_len] = '\0';
    wrapped(para, "");
    putchar('\n');
    para_len = 0;
}

void hal_chapter(const char *title)
{
    printf("~ %s ~\n\n", title);
}

void hal_pause(void)
{
    char buf[8];

    printf("(Enter to continue)\n");
    read_line(buf, sizeof(buf));
}

void hal_picture(uint8_t id, const char *name)
{
    (void)id;
    (void)name;             /* no pictures in a terminal */
}

static const char *const stat_names[] = { "Might", "Grace", "Grit", "Wits", "Presence", "Fate" };
static const char *const results[] = { "fail", "success at a cost", "success", "critical success" };

void hal_check(uint8_t rating, const apb_roll *roll)
{
    char line[96];

    sprintf(line, "[%s check: rolled %u + %d = %d against %d: %s]",
            rating < 6 ? stat_names[rating] : apb_skill_names[rating - 16],
            roll->roll, roll->total - roll->roll, roll->total, roll->tn,
            results[roll->result]);
    wrapped(line, "");
    putchar('\n');
}

static const apb_character *status_ch;

void hal_status(const apb_character *ch)
{
    status_ch = ch;
}

static void show_status(void)
{
    const apb_character *ch = status_ch;
    char line[96];
    char name[APB_NAME_LEN + 1];
    unsigned i;

    if (!ch) return;
    for (i = 0; ch->name[i]; ++i) {
        name[i] = (char)((i == 0 || ch->name[i - 1] == ' ' || ch->name[i - 1] == '-')
                         ? ch->name[i] : ch->name[i] + ('a' - 'A') * (ch->name[i] >= 'A' && ch->name[i] <= 'Z'));
    }
    name[i] = '\0';
    sprintf(line, "%s  Lvl %u  HP %u  Debt %u", name, ch->level, apb_health_max(ch),
            ch->debt);
    wrapped(line, "");
}

uint8_t hal_menu(const char *const *labels, uint8_t count)
{
    uint8_t i;
    char buf[16];
    int pick;

    show_status();
    for (i = 0; i < count; ++i) {
        printf("%u. %s\n", i + 1, labels[i]);
    }
    for (;;) {
        printf("> ");
        read_line(buf, sizeof(buf));
        pick = atoi(buf);
        if (pick >= 1 && pick <= count) {
            putchar('\n');
            return (uint8_t)(pick - 1);
        }
        printf("Pick a number from 1 to %u.\n", count);
    }
}

void hal_ask_line(char *out, uint8_t max)
{
    static char buf[128];

    printf("> ");
    read_line(buf, sizeof(buf));
    strncpy(out, buf, max);
    out[max] = '\0';
}

void hal_prompt(const char *msg)
{
    wrapped(msg, "");
}

void hal_error(const char *msg)
{
    printf("\nThe train has derailed: %s\n", msg);
}

/* ----------------------------------------------------------------- files */

static int is_apd;

/* A part of an .apd container: "DEPOT" or "CARnn". */
static uint8_t load_from_apd(const char *name, uint8_t *dst, uint16_t max, uint16_t *len)
{
    FILE *f = fopen(source, "rb");
    unsigned char head[8];
    unsigned char lens[128];
    unsigned long offset;
    unsigned want;
    unsigned cars;
    unsigned i;
    unsigned size;

    if (!f) return HAL_NOT_FOUND;
    if (fread(head, 1, 8, f) != 8 || memcmp(head, "APD1", 4) != 0) {
        fclose(f);
        return HAL_IO_ERROR;
    }
    cars = head[6];
    if (fread(lens, 2, cars, f) != cars) {
        fclose(f);
        return HAL_IO_ERROR;
    }
    offset = 8 + 2ul * cars;
    if (strcmp(name, "DEPOT") == 0) {
        size = (unsigned)(head[4] | (head[5] << 8));
    } else if (strncmp(name, "CAR", 3) == 0) {
        want = (unsigned)atoi(name + 3);
        if (want >= cars) {
            fclose(f);
            return HAL_NOT_FOUND;
        }
        offset += (unsigned)(head[4] | (head[5] << 8));
        for (i = 0; i < want; ++i) offset += (unsigned)(lens[2 * i] | (lens[2 * i + 1] << 8));
        size = (unsigned)(lens[2 * want] | (lens[2 * want + 1] << 8));
    } else {
        fclose(f);
        return HAL_NOT_FOUND;
    }
    if (size > max) {
        fclose(f);
        return HAL_TOO_BIG;
    }
    if (fseek(f, (long)offset, SEEK_SET) != 0 || fread(dst, 1, size, f) != size) {
        fclose(f);
        return HAL_IO_ERROR;
    }
    fclose(f);
    *len = (uint16_t)size;
    return HAL_OK;
}

uint8_t hal_load(const char *name, uint8_t *dst, uint16_t max, uint16_t *len)
{
    static char path[512];
    FILE *f;
    size_t n;

    if (is_apd) return load_from_apd(name, dst, max, len);
    snprintf(path, sizeof(path), "%s/%s", source, name);
    f = fopen(path, "rb");
    if (!f) return HAL_NOT_FOUND;
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
    return HAL_IO_ERROR;        /* saves arrive with E2 */
}

/* --------------------------------------------------------------- the end */

static void show_receipt(const apb_receipt *r)
{
    uint8_t i;

    printf("%s\n", r->outcome == APB_VM_COMPLETE ? "~ Departure complete ~"
                                                 : "~ Departure failed ~");
    printf("\nYour receipt:\n");
    if (r->xp) printf("  %u XP\n", r->xp);
    if (r->debt_paid) printf("  %u Debt paid\n", r->debt_paid);
    if (r->debt_added) printf("  %u Debt added\n", r->debt_added);
    for (i = 0; i < r->gained_count; ++i) {
        printf("  Gained: %s\n", r->gained[i] < APB_ITEM_COUNT ? apb_item_names[r->gained[i]] : "?");
    }
    for (i = 0; i < r->lost_count; ++i) {
        printf("  Lost: %s\n", r->lost[i] < APB_ITEM_COUNT ? apb_item_names[r->lost[i]] : "?");
    }
    if (r->echo_count) printf("  %u Echo%s will follow you.\n", r->echo_count,
                              r->echo_count == 1 ? "" : "es");
    putchar('\n');
    if (r->ticket) {
        printf("Ticket %lu.\n", (unsigned long)r->ticket);
        wrapped("Take it to the Waystation to have it stamped into your Passport.", "");
    } else {
        wrapped("You travelled without a Boarding Pass, so this trip can't be stamped.", "");
    }
}

static apb_character traveler;
static apb_pass pass;

int main(int argc, char **argv)
{
    int i;
    unsigned seed = (unsigned)time(NULL);
    const char *choices = NULL;
    size_t n;

    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--width") == 0 && i + 1 < argc) {
            width = (unsigned)atoi(argv[++i]);
            if (width < 20) width = 20;
        } else if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
            seed = (unsigned)atoi(argv[++i]);
        } else if (strcmp(argv[i], "--choices") == 0 && i + 1 < argc) {
            choices = argv[++i];
        } else if (argv[i][0] == '-') {
            break;
        } else {
            source = argv[i];
        }
    }
    if (!source || i < argc) {
        fprintf(stderr, "usage: apb [--width N] [--seed N] [--choices FILE] DEPARTURE\n"
                        "  DEPARTURE is an .apd image or a directory of DEPOT/CARnn files\n"
                        "  --seed sets the dice when travelling without a Boarding Pass\n");
        return 2;
    }
    n = strlen(source);
    is_apd = n > 4 && strcmp(source + n - 4, ".apd") == 0;
    input = stdin;
    if (choices) {
        input = fopen(choices, "r");
        if (!input) {
            fprintf(stderr, "can't open %s\n", choices);
            return 2;
        }
        echo_input = 1;
    }

    hal_init();
    printf("A PLATFORM BETWEEN\n\n");
    apb_desk_run(&traveler);
    if (apb_vm_open() != 0) {
        printf("This Departure can't be boarded: %s\n", apb_vm_error());
        return 1;
    }
    putchar('\n');
    if ((apb_desk_pass(&traveler, apb_vm_departure(), &pass)
         ? apb_vm_board_pass(&traveler, &pass)
         : apb_vm_board(&traveler, (uint16_t)seed)) != 0) {
        printf("This Departure can't be boarded: %s\n", apb_vm_error());
        return 1;
    }
    if (apb_vm_run() == APB_VM_ERROR) {
        return 1;
    }
    show_receipt(apb_vm_receipt());
    hal_shutdown();
    return 0;
}
