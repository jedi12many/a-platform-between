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
    sprintf(line, "%s  Lvl %u  HP %u/%u  Debt %u", name, ch->level, apb_vm_health(),
            apb_health_max(ch), ch->debt);
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
        if (buf[0] == 's' || buf[0] == 'S') {
            return APB_MENU_SAVE;
        }
        pick = atoi(buf);
        if (pick >= 1 && pick <= count) {
            putchar('\n');
            return (uint8_t)(pick - 1);
        }
        printf("Pick a number from 1 to %u, or s to save.\n", count);
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

/* A save sits beside the Departure: GAME.apd.save, or SAVE in a directory of files. */
static const char *file_path(const char *name)
{
    static char path[512];

    if (is_apd) snprintf(path, sizeof(path), "%s.save", source);
    else snprintf(path, sizeof(path), "%s/%s", source, name);
    return path;
}

uint8_t hal_load(const char *name, uint8_t *dst, uint16_t max, uint16_t *len)
{
    const char *path;
    FILE *f;
    size_t n;

    if (is_apd && strcmp(name, "SAVE") != 0) return load_from_apd(name, dst, max, len);
    path = file_path(name);
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
    FILE *f;
    size_t n;

    f = fopen(file_path(name), "wb");
    if (!f) return HAL_IO_ERROR;
    n = fwrite(src, 1, len, f);
    fclose(f);
    return n == len ? HAL_OK : HAL_IO_ERROR;
}

/* ----------------------------------------------------------- battles */

/* The battle screen (docs/combat.md): the map two characters to a square, so 16 squares
 * fit in 40 columns; a roster; and two short menus a turn, "Where to?" and "Then?", that
 * offer only what's possible. */
static const char tile_chars[] = ".#O~+^=>";
static const char *const tile_names[] = { "", "wall", "pit", "rough", "cover", "hazard",
                                          "high ground", "exit" };
static apb_fighter bf;
static uint8_t last_round;
static uint8_t redraw;
static uint8_t free_next;    /* the next attack is a free one       */
static uint8_t on_quick;     /* the computer is playing you          */

/* Foe `who` (1..) is the letter a, b, ... on the map. */
static char foe_letter(uint8_t who)
{
    static const char letters[] = "abcdefghijklmnopqrstuvwxyz";

    return letters[(who - 1) % 26];
}

static const char *fighter_name(uint8_t who)
{
    static char name[APB_NAME_LEN + 1];
    const apb_character *ch = apb_vm_character();
    unsigned i;

    if (who) return apb_vm_foe_name(who);
    for (i = 0; ch->name[i]; ++i) {
        name[i] = (char)((i == 0 || ch->name[i - 1] == ' ' || ch->name[i - 1] == '-')
                         ? ch->name[i] : ch->name[i] + ('a' - 'A') * (ch->name[i] >= 'A' && ch->name[i] <= 'Z'));
    }
    name[i] = '\0';
    return name;
}

static void show_battle(void)
{
    static uint8_t seen[8];
    uint8_t x;
    uint8_t y;
    uint8_t i;
    uint8_t t;
    char c;
    char line[96];
    size_t n;

    memset(seen, 0, sizeof(seen));
    for (y = 0; y < apb_battle_height(); ++y) {
        n = 0;
        line[n++] = ' ';
        for (x = 0; x < apb_battle_width(); ++x) {
            t = apb_battle_tile(x, y) & 7;
            seen[t] = 1;
            c = tile_chars[t];
            for (i = 0; i < apb_battle_count(); ++i) {
                apb_battle_fighter(i, &bf);
                if (bf.state == APB_GONE || bf.x != x || bf.y != y) continue;
                c = bf.state == APB_DOWN ? 'x' : i == 0 ? '@' : foe_letter(i);
                if (bf.state == APB_IN_FIGHT) break;
            }
            line[n++] = ' ';
            line[n++] = c;
        }
        line[n] = '\0';
        printf("%s\n", line);
    }
    /* A key to the squares on this map, broken between entries. */
    n = 0;
    for (t = 1; t < 8; ++t) {
        if (!seen[t]) continue;
        if (n && n + 4 + strlen(tile_names[t]) > width) {
            printf("%s\n", line);
            n = 0;
        }
        n += (size_t)sprintf(line + n, "%s%c %s", n ? "  " : " ", tile_chars[t], tile_names[t]);
    }
    if (n) printf("%s\n", line);
    for (i = 0; i < apb_battle_count(); ++i) {
        apb_battle_fighter(i, &bf);
        if (bf.state == APB_GONE) continue;
        if (i == 0) {
            sprintf(line, " @ %s  %u/%u", fighter_name(0), bf.health, bf.health_max);
        } else if (bf.state == APB_DOWN) {
            sprintf(line, " x %s  down", fighter_name(i));
        } else {
            sprintf(line, " %c %s  %u/%u  TN %d", foe_letter(i), fighter_name(i), bf.health,
                    bf.health_max, apb_battle_tn(0, i));
        }
        printf("%s\n", line);
    }
    redraw = 0;
}

void hal_battle_begin(void)
{
    printf("-- A fight! --\n");
    last_round = 0xFF;
    free_next = on_quick = 0;
    show_battle();
    putchar('\n');
}

void hal_battle_event(const apb_event *e)
{
    static const char *const hits[] = { "a miss", "a glancing hit", "a hit", "a crit" };
    static const char *const flees[] = { "still here", "out, but not cleanly", "out", "out" };
    static char line[160];
    static char actor[APB_VM_FOE_NAME_MAX + 1];
    uint8_t you = (uint8_t)(e->actor == 0);
    int n;

    strcpy(actor, you ? "You" : fighter_name(e->actor));
    line[0] = '\0';
    switch (e->kind) {
    case APB_EV_TURN:
        if (e->value != last_round) {
            last_round = (uint8_t)e->value;
            if (last_round) printf("-- Round %u --\n", last_round);
            else printf("-- Caught off guard --\n");
        }
        return;
    case APB_EV_MOVE:
        sprintf(line, "%s move%s.", actor, you ? "" : "s");
        break;
    case APB_EV_FREE:
        free_next = 1;
        return;
    case APB_EV_ATTACK:
        n = free_next ? sprintf(line, "Free attack! ") : 0;
        free_next = 0;
        n += sprintf(line + n, "%s attack%s %s: %u + %d = %d against %d, %s", actor,
                    you ? "" : "s", e->target ? fighter_name(e->target) : "you",
                    e->roll.roll, e->roll.total - e->roll.roll, e->roll.total, e->roll.tn,
                    hits[e->roll.result & 3]);
        if (e->roll.result != APB_FAIL) sprintf(line + n, ": %u damage.", e->value);
        else strcpy(line + n, ".");
        break;
    case APB_EV_DOWN:
        if (e->target) sprintf(line, "%s is down.", fighter_name(e->target));
        else strcpy(line, "You are down.");
        break;
    case APB_EV_HAZARD:
        sprintf(line, "The ground hurts %s: %u damage.", you ? "you" : fighter_name(e->actor),
                e->value);
        break;
    case APB_EV_GUARD:
        sprintf(line, "%s stand%s guard.", actor, you ? "" : "s");
        break;
    case APB_EV_WAIT:
        sprintf(line, "%s wait%s to see what happens.", actor, you ? "" : "s");
        break;
    case APB_EV_FLEE:
        if (e->roll.roll) {
            sprintf(line, "%s tr%s to get away: %u + %d = %d against %d: %s.", actor,
                    you ? "y" : "ies", e->roll.roll, e->roll.total - e->roll.roll,
                    e->roll.total, e->roll.tn, flees[e->roll.result & 3]);
        } else {
            sprintf(line, "%s take%s the exit.", actor, you ? "" : "s");
        }
        break;
    case APB_EV_GONE:
        if (you) strcpy(line, "You are out of the fight.");
        else sprintf(line, "%s runs off.", actor);
        break;
    default:
        return;
    }
    wrapped(line, "");
    redraw = 1;
}

/* A battle menu: no saving in a fight. */
static uint8_t battle_pick(const char *question, char labels[][40], uint8_t count)
{
    uint8_t i;
    char buf[64];
    int pick;

    printf("%s\n", question);
    for (i = 0; i < count; ++i) {
        sprintf(buf, "%u. %.39s", i + 1, labels[i]);
        wrapped(buf, "");
    }
    for (;;) {
        printf("> ");
        read_line(buf, sizeof(buf));
        pick = atoi(buf);
        if (pick >= 1 && pick <= count) return (uint8_t)(pick - 1);
        printf("Pick a number from 1 to %u.\n", count);
    }
}

static uint8_t dist(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1)
{
    uint8_t dx = (uint8_t)(x0 > x1 ? x0 - x1 : x1 - x0);
    uint8_t dy = (uint8_t)(y0 > y1 ? y0 - y1 : y1 - y0);

    return dx > dy ? dx : dy;
}

/* The square `who` can reach that is nearest x,y (and, if `tile` isn't 0xFF, of that
 * tile; within `within` squares of x,y), keeping off hazards when it can. Returns 0 if
 * there is none, or if it's no nearer than where they stand. */
static uint8_t best_square(uint8_t who, uint8_t x, uint8_t y, uint8_t tile, uint8_t within,
                           uint8_t *out_x, uint8_t *out_y)
{
    static uint8_t ok[APB_MAP_H_MAX][APB_MAP_W_MAX];
    uint8_t i;
    uint8_t j;
    uint8_t t;
    uint8_t d;
    uint16_t score;
    uint16_t best = 0xFFFF;

    apb_battle_fighter(who, &bf);
    for (j = 0; j < apb_battle_height(); ++j) {
        for (i = 0; i < apb_battle_width(); ++i) ok[j][i] = apb_battle_can_reach(who, i, j);
    }
    for (j = 0; j < apb_battle_height(); ++j) {
        for (i = 0; i < apb_battle_width(); ++i) {
            t = apb_battle_tile(i, j);
            if (!ok[j][i] || (i == bf.x && j == bf.y)) continue;
            if (tile != 0xFF && t != tile) continue;
            d = dist(i, j, x, y);
            if (d > within) continue;
            score = (uint16_t)(d * 2 + (t == APB_TILE_HAZARD ? 64 : 0));
            if (score < best) {
                best = score;
                *out_x = i;
                *out_y = j;
            }
        }
    }
    if (best == 0xFFFF) return 0;
    if (tile == 0xFF && within == 0xFF && dist(*out_x, *out_y, x, y) >= dist(bf.x, bf.y, x, y)) {
        return 0;
    }
    return 1;
}

/* The nearest square of a kind, anywhere on the map, for "toward the exit". */
static uint8_t nearest_tile(uint8_t tile, uint8_t from_x, uint8_t from_y, uint8_t *x, uint8_t *y)
{
    uint8_t i;
    uint8_t j;
    uint8_t best = 0xFF;

    for (j = 0; j < apb_battle_height(); ++j) {
        for (i = 0; i < apb_battle_width(); ++i) {
            if (apb_battle_tile(i, j) == tile && dist(i, j, from_x, from_y) < best) {
                best = dist(i, j, from_x, from_y);
                *x = i;
                *y = j;
            }
        }
    }
    return (uint8_t)(best != 0xFF);
}

void hal_battle_turn(uint8_t who, apb_action *out)
{
    static char labels[16][40];
    static uint8_t to_x[16];
    static uint8_t to_y[16];
    static uint8_t targets[16];
    uint8_t n;
    uint8_t i;
    uint8_t pick;
    uint8_t x;
    uint8_t y;
    uint8_t here_x;
    uint8_t here_y;
    uint8_t adjacent;
    uint8_t waited;
    char buf[16];

    if (redraw) {
        putchar('\n');
        show_battle();
        putchar('\n');
    }
    if (on_quick) {
        printf("On quick: Enter, or t to take over.\n> ");
        read_line(buf, sizeof(buf));
        if (buf[0] == 't' || buf[0] == 'T') {
            on_quick = 0;
        } else {
            putchar('\n');
            apb_battle_quick(who, out);
            return;
        }
    }
    apb_battle_fighter(who, &bf);
    here_x = bf.x;
    here_y = bf.y;
    waited = bf.waited;
    for (;;) {
        /* Where to? */
        n = 0;
        strcpy(labels[n], "Stay here");
        to_x[n] = here_x;
        to_y[n++] = here_y;
        for (i = 1; i < apb_battle_count() && n < 12; ++i) {
            apb_battle_fighter(i, &bf);
            if (bf.state != APB_IN_FIGHT) continue;
            x = bf.x;
            y = bf.y;
            if (dist(here_x, here_y, x, y) > 1
                && best_square(who, x, y, 0xFF, 1, &to_x[n], &to_y[n])) {
                sprintf(labels[n++], "Next to %.20s (%c)", fighter_name(i), foe_letter(i));
            } else if (dist(here_x, here_y, x, y) > 1
                       && best_square(who, x, y, 0xFF, 0xFF, &to_x[n], &to_y[n])) {
                sprintf(labels[n++], "Toward %.20s (%c)", fighter_name(i), foe_letter(i));
            }
        }
        if (apb_battle_tile(here_x, here_y) != APB_TILE_EXIT
            && nearest_tile(APB_TILE_EXIT, here_x, here_y, &x, &y)) {
            if (best_square(who, x, y, APB_TILE_EXIT, 0xFF, &to_x[n], &to_y[n])) {
                strcpy(labels[n++], "To the exit");
            } else if (best_square(who, x, y, 0xFF, 0xFF, &to_x[n], &to_y[n])) {
                strcpy(labels[n++], "Toward the exit");
            }
        }
        if (apb_battle_tile(here_x, here_y) != APB_TILE_COVER
            && best_square(who, here_x, here_y, APB_TILE_COVER, 0xFF, &to_x[n], &to_y[n])) {
            strcpy(labels[n++], "Into cover");
        }
        if (apb_battle_tile(here_x, here_y) != APB_TILE_HIGH
            && best_square(who, here_x, here_y, APB_TILE_HIGH, 0xFF, &to_x[n], &to_y[n])) {
            strcpy(labels[n++], "Onto high ground");
        }
        /* Instead of moving: put the turn off, or hand it to the computer. */
        if (!waited) {
            strcpy(labels[n], "Wait: act at the end of the round");
            to_x[n++] = 0xFE;
        }
        strcpy(labels[n], "Quick: the computer plays you");
        to_x[n++] = 0xFD;
        pick = battle_pick("Where to?", labels, n);
        if (to_x[pick] == 0xFE) {
            putchar('\n');
            out->move_x = here_x;
            out->move_y = here_y;
            out->kind = APB_ACT_WAIT;
            out->target = 0;
            return;
        }
        if (to_x[pick] == 0xFD) {
            putchar('\n');
            on_quick = 1;
            apb_battle_quick(who, out);
            return;
        }
        out->move_x = to_x[pick];
        out->move_y = to_y[pick];

        /* Then? */
        n = 0;
        adjacent = 0;
        for (i = 1; i < apb_battle_count() && n < 12; ++i) {
            apb_battle_fighter(i, &bf);
            if (bf.state != APB_IN_FIGHT) continue;
            if (dist(out->move_x, out->move_y, bf.x, bf.y) == 1) ++adjacent;
            if (!apb_battle_can_attack(who, i, out->move_x, out->move_y)) continue;
            sprintf(labels[n], "Attack %.20s (%c): TN %d", fighter_name(i), foe_letter(i),
                    apb_battle_tn(who, i));
            targets[n++] = i;
        }
        strcpy(labels[n], "Guard: hit the first to come close");
        targets[n++] = 0xF0 | APB_ACT_GUARD;
        if (apb_battle_tile(out->move_x, out->move_y) == APB_TILE_EXIT) {
            strcpy(labels[n], "Take the exit");
        } else {
            sprintf(labels[n], "Flee: TN %d", apb_flee_tn(adjacent));
        }
        targets[n++] = 0xF0 | APB_ACT_FLEE;
        strcpy(labels[n], "Done");
        targets[n++] = 0xF0 | APB_ACT_DONE;
        strcpy(labels[n], "Back");
        targets[n++] = 0xFF;
        pick = battle_pick("Then?", labels, n);
        if (targets[pick] == 0xFF) continue;
        putchar('\n');
        if (targets[pick] < 0xF0) {
            out->kind = APB_ACT_ATTACK;
            out->target = targets[pick];
        } else {
            out->kind = (uint8_t)(targets[pick] & 0x0F);
            out->target = 0;
        }
        return;
    }
}

void hal_battle_end(uint8_t result)
{
    static const char *const endings[] = { "", "You won the fight.", "You lost the fight.",
                                           "You got away." };

    printf("%s\n\n", endings[result & 3]);
}

/* --------------------------------------------------------------- the end */

static char stamp[APB_STAMP_BUF];

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
    if (r->ticket && apb_stamp_encode(r, stamp) == APB_PP_OK) {
        wrapped("Your Travel Stamp. Type it in at the Waystation to have this trip "
                "stamped into your Passport:", "");
        putchar('\n');
        for (i = 0; stamp[i]; i = (uint8_t)(i + APB_PASSWORD_LINE)) {
            printf("  %.*s\n", APB_PASSWORD_LINE, stamp + i);
        }
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
    int resume = 0;

    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--width") == 0 && i + 1 < argc) {
            width = (unsigned)atoi(argv[++i]);
            if (width < 20) width = 20;
        } else if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
            seed = (unsigned)atoi(argv[++i]);
        } else if (strcmp(argv[i], "--resume") == 0) {
            resume = 1;
        } else if (strcmp(argv[i], "--choices") == 0 && i + 1 < argc) {
            choices = argv[++i];
        } else if (argv[i][0] == '-') {
            break;
        } else {
            source = argv[i];
        }
    }
    if (!source || i < argc) {
        fprintf(stderr, "usage: apb [--width N] [--seed N] [--choices FILE] [--resume] DEPARTURE\n"
                        "  DEPARTURE is an .apd image or a directory of DEPOT/CARnn files\n"
                        "  --seed sets the dice when travelling without a Boarding Pass\n"
                        "  --resume picks up the trip saved with s at a menu\n");
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
    if (resume) {
        if (apb_vm_resume() != 0) {
            printf("There's no trip to pick up: %s\n", apb_vm_error());
            return 1;
        }
        printf("Picking up where you left off.\n\n");
        if (apb_vm_run() == APB_VM_ERROR) {
            return 1;
        }
        show_receipt(apb_vm_receipt());
        hal_shutdown();
        return 0;
    }
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
