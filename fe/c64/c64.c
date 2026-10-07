/*
 * The Commodore 64 front end (milestone E4, docs/c64.md): the HAL on the C64's screen,
 * keyboard and 1541 disk drive. The game is the program plus three overlays (LOAD, PASS
 * and BATTLE) that load from disk when the VM asks for them, and the Departure's own
 * files, DEPOT and CAR00, CAR01, ..., on the same disk.
 *
 * Text goes out through the KERNAL (CHROUT) in upper/lower case mode, word-wrapped at 40
 * columns, and waits with "-- more --" before anything scrolls off unread. Game text
 * arrives in ASCII and is turned into PETSCII here; the client's own messages are C
 * strings, which cc65 has already made PETSCII.
 */
#include <cbm.h>
#include <conio.h>
#include <string.h>

#include "apb.h"
#include "apb_desk.h"
#include "apb_hal.h"
#include "apb_view.h"
#include "apb_vm.h"

#define COLS 40
#define ROWS 25

#define BORDER     (*(volatile uint8_t *)0xD020)
#define BACKGROUND (*(volatile uint8_t *)0xD021)
#define TEXT_COLOR (*(volatile uint8_t *)0x0286)
#define JIFFY_LO   (*(volatile uint8_t *)0x00A2)
#define JIFFY_MID  (*(volatile uint8_t *)0x00A1)

#define PET_RETURN  0x0D
#define PET_DEL     0x14
#define PET_RVS_ON  0x12
#define PET_RVS_OFF 0x92
#define PET_LOWER   0x0E        /* upper/lower case character set */
#define PET_LOCK    0x08        /* and keep it: C= + SHIFT can't switch it back */
#define PET_CLEAR   0x93

#define INK_BLACK  0
#define INK_GREEN  5
#define INK_LGREEN 13
#define INK_GRAY   12
#define INK_YELLOW 7

/* ----------------------------------------------------------------- text */

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static uint8_t col;             /* where the cursor is on its row              */
static uint8_t wrapped_row;     /* the last character filled the row           */
static uint8_t rows_shown;      /* rows printed since the player last pressed a key */
static uint8_t word[COLS];
static uint8_t word_len;
static uint8_t spaces;          /* spaces waiting to go before the next word   */

static void more(void);

static void raw(uint8_t c)
{
    cbm_k_bsout(c);
}

static void newline(void)
{
    if (wrapped_row) {
        wrapped_row = 0;        /* the cursor already moved down */
        return;
    }
    raw(PET_RETURN);
    col = 0;
    more();
}

static void put(uint8_t c)
{
    raw(c);
    wrapped_row = 0;
    if (++col == COLS) {
        col = 0;
        wrapped_row = 1;
        more();
    }
}

/* Before anything scrolls off unread. */
static void more(void)
{
    static const char msg[] = "-- more --";
    uint8_t i;

    if (++rows_shown < ROWS - 2) return;
    raw(PET_RVS_ON);
    for (i = 0; msg[i]; ++i) raw((uint8_t)msg[i]);
    raw(PET_RVS_OFF);
    cgetc();
    for (i = 0; msg[i]; ++i) raw(PET_DEL);
    rows_shown = 0;
}

static void flush_word(void)
{
    uint8_t i;

    if (!word_len) return;
    if (col) {
        if (col + spaces + word_len > COLS) {
            newline();
        } else {
            while (spaces--) put(' ');
        }
    }
    for (i = 0; i < word_len; ++i) put(word[i]);
    word_len = 0;
    spaces = 0;
}

/* Out with the word and the spaces after it: before printing straight to the screen. */
static void settle(void)
{
    flush_word();
    while (spaces) {
        put(' ');
        --spaces;
    }
}

/* One PETSCII character into the word-wrapped stream. */
static void stream(uint8_t c)
{
    if (c == ' ') {
        flush_word();
        if (col) ++spaces;
    } else if (c == PET_RETURN) {
        flush_word();
        spaces = 0;
        newline();
    } else {
        if (word_len == COLS) flush_word();
        word[word_len++] = c;
    }
}

static void end_line(void)
{
    flush_word();
    spaces = 0;
    if (col || wrapped_row) newline();
    else {
        raw(PET_RETURN);
        more();
    }
}

/* Game text is ASCII; the screen, in upper/lower case mode, wants PETSCII. These are
 * byte values, not characters: this file never does arithmetic on a C literal. */
static uint8_t petscii(uint8_t c)
{
    if (c >= 0x61 && c <= 0x7A) return (uint8_t)(c - 0x20);     /* a-z */
    if (c >= 0x41 && c <= 0x5A) return (uint8_t)(c + 0x80);     /* A-Z */
    if (c == 0x0A) return PET_RETURN;
    if (c == 0x5F || c >= 0x7B) return 0x2D;                    /* no _ { | } ~ */
    return c;
}

static void ascii_out(const char *s)
{
    while (*s) stream(petscii((uint8_t)*s++));
}

static void plat_out(const char *s)
{
    while (*s) stream((uint8_t)*s++);
}

static uint8_t key(void)
{
    uint8_t k;

    cursor(1);
    k = (uint8_t)cgetc();
    cursor(0);
    rows_shown = 0;
    return k;
}

void hal_init(void)
{
    BORDER = INK_BLACK;
    BACKGROUND = INK_BLACK;
    TEXT_COLOR = INK_LGREEN;
    raw(PET_LOWER);
    raw(PET_LOCK);
    raw(PET_CLEAR);
    col = rows_shown = 0;
}

void hal_shutdown(void) {}

void hal_text_char(char c)
{
    stream(petscii((uint8_t)c));
}

void hal_text_end(void)
{
    end_line();
    end_line();
}

/* "~ The Static ~", as the terminal has it; the C64 has no ~, so it reads "- The Static -". */
static const char tilde_space[] = { 0x7E, 0x20, 0 };
static const char space_tilde[] = { 0x20, 0x7E, 0 };

void hal_chapter(const char *title)
{
    ascii_out(tilde_space);
    ascii_out(title);
    ascii_out(space_tilde);
    end_line();
    end_line();
}

void hal_pause(void)
{
    plat_out("(press a key)");
    end_line();
    key();
}

void hal_picture(uint8_t id, const char *name)
{
    (void)id;
    (void)name;             /* pictures come later (docs/c64.md) */
}

static char line[APB_VIEW_LINE];

void hal_check(uint8_t rating, const apb_roll *roll)
{
    apb_view_check(line, rating, roll);
    ascii_out(line);
    end_line();
    end_line();
}

static const apb_character *status_ch;

void hal_status(const apb_character *ch)
{
    status_ch = ch;
}

static void show_status(void)
{
    if (!status_ch) return;
    apb_view_status(line, status_ch, apb_vm_health());
    TEXT_COLOR = INK_YELLOW;
    ascii_out(line);
    end_line();
    TEXT_COLOR = INK_LGREEN;
}

/* "> 3": the key the player pressed, shown. */
static void echo_key(uint8_t k)
{
    plat_out("> ");
    settle();
    put(k);
    end_line();
}

static void numbered(uint8_t i, const char *label)
{
    put((uint8_t)('1' + i));
    plat_out(". ");
    ascii_out(label);
    end_line();
}

uint8_t hal_menu(const char *const *labels, uint8_t count)
{
    uint8_t i;
    uint8_t k;

    show_status();
    for (i = 0; i < count; ++i) numbered(i, labels[i]);
    for (;;) {
        k = key();
        if (k >= '1' && k < '1' + count) {
            echo_key(k);
            end_line();
            return (uint8_t)(k - '1');
        }
        if (k == 's' || k == 'S') {
            echo_key(k);
            return APB_MENU_SAVE;
        }
    }
}

void hal_ask_line(char *out, uint8_t max)
{
    uint8_t n = 0;
    uint8_t k;

    plat_out("> ");
    settle();
    for (;;) {
        k = key();
        if (k == PET_RETURN) break;
        if (k == PET_DEL) {
            if (n) {
                --n;
                raw(PET_DEL);
                --col;
            }
        } else if (n < max && col < COLS - 1
                   && ((k >= 0x20 && k < 0x60) || (k >= 0xC1 && k <= 0xDA))) {
            out[n++] = (char)k;
            put(k);
        }
    }
    out[n] = '\0';
    end_line();
}

void hal_prompt(const char *msg)
{
    plat_out(msg);
    end_line();
}

void hal_error(const char *msg)
{
    end_line();
    plat_out("The train has derailed: ");
    plat_out(msg);
    end_line();
}

/* ------------------------------------------------------- the battle screen */

void apb_view_out(const char *ascii, uint8_t wrap)
{
    if (wrap) {
        ascii_out(ascii);
    } else {
        /* Map rows and the roster: as they are, spaces and all. */
        settle();
        while (*ascii) put(petscii((uint8_t)*ascii++));
    }
    end_line();
}

uint8_t apb_view_pick(uint8_t count)
{
    uint8_t k;

    for (;;) {
        k = key();
        if (k >= '1' && k < '1' + count) {
            echo_key(k);
            return (uint8_t)(k - '1');
        }
    }
}

uint8_t apb_view_go_on(void)
{
    uint8_t k = key();

    echo_key(k);
    return (uint8_t)!(k == 't' || k == 'T');
}

/* ----------------------------------------------------------------- disk */

#define DEVICE 8
#define LFN    2

static char file_name[24];

static void name_with(const char *before, const char *name, const char *after)
{
    strcpy(file_name, before);
    strcat(file_name, name);
    strcat(file_name, after);
}

uint8_t hal_load(const char *name, uint8_t *dst, uint16_t max, uint16_t *len)
{
    int n;
    uint8_t extra;
    uint8_t result = HAL_OK;

    name_with("", name, ",s,r");
    BORDER = INK_GRAY;
    if (cbm_open(LFN, DEVICE, 2, file_name) != 0) {
        BORDER = INK_BLACK;
        return HAL_IO_ERROR;
    }
    n = cbm_read(LFN, dst, max);
    if (n <= 0) {
        result = HAL_NOT_FOUND;
    } else if ((uint16_t)n == max && cbm_read(LFN, &extra, 1) == 1) {
        result = HAL_TOO_BIG;
    }
    cbm_close(LFN);
    BORDER = INK_BLACK;
    *len = n > 0 ? (uint16_t)n : 0;
    return result;
}

uint8_t hal_save(const char *name, const uint8_t *src, uint16_t len)
{
    int n;

    name_with("@0:", name, ",s,w");
    BORDER = INK_GRAY;
    if (cbm_open(LFN, DEVICE, 2, file_name) != 0) {
        BORDER = INK_BLACK;
        return HAL_IO_ERROR;
    }
    n = cbm_write(LFN, src, len);
    cbm_close(LFN);
    BORDER = INK_BLACK;
    return (uint8_t)(n == (int)len ? HAL_OK : HAL_IO_ERROR);
}

/* The overlays: files OVL1..OVL3 on the disk, each loading to the overlay area. */
static uint8_t overlay_in;

void hal_overlay(uint8_t which)
{
    static char ovl[] = "ovl0";

    if (which == overlay_in) return;
    ovl[3] = (char)('0' + which);
    for (;;) {
        BORDER = INK_GREEN;
        if (cbm_load(ovl, DEVICE, 0) != 0) break;
        BORDER = INK_BLACK;
        overlay_in = 0;
        plat_out("Can't read the disk. Check it's in the drive, then press a key.");
        end_line();
        key();
    }
    BORDER = INK_BLACK;
    overlay_in = which;
}

/* ---------------------------------------------------------------- the trip */

static apb_character traveler;
static apb_pass pass;
static char stamp[APB_STAMP_BUF];

/* "Board", "Pick up a saved trip": menu labels are ASCII, like game text. */
static const char label_board[] = { 66, 111, 97, 114, 100, 0 };
static const char label_resume[] = { 80, 105, 99, 107, 32, 117, 112, 32, 97, 32, 115, 97,
                                     118, 101, 100, 32, 116, 114, 105, 112, 0 };
static const char *const start_labels[2] = { label_board, label_resume };

static void show_receipt(const apb_receipt *r)
{
    uint8_t i;
    uint8_t j;
    uint8_t stamped;

    APB_NEED(APB_OVL_PASS);
    stamped = (uint8_t)(r->ticket && apb_stamp_encode(r, stamp) == APB_PP_OK);
    apb_view_receipt(r, stamped);
    for (i = 0; stamped && stamp[i]; i = (uint8_t)(i + APB_PASSWORD_LINE)) {
        settle();
        put(' ');
        put(' ');
        for (j = 0; j < APB_PASSWORD_LINE && stamp[i + j]; ++j) put((uint8_t)stamp[i + j]);
        end_line();
    }
}

static uint8_t board(void)
{
    APB_NEED(APB_OVL_PASS);
    apb_desk_run(&traveler);
    if (apb_vm_open() != 0) {
        plat_out("This Departure can't be boarded: ");
        plat_out(apb_vm_error());
        end_line();
        return 1;
    }
    end_line();
    APB_NEED(APB_OVL_PASS);
    if ((apb_desk_pass(&traveler, apb_vm_departure(), &pass)
         ? apb_vm_board_pass(&traveler, &pass)
         : apb_vm_board(&traveler, (uint16_t)(JIFFY_LO | (JIFFY_MID << 8)))) != 0) {
        plat_out("This Departure can't be boarded: ");
        plat_out(apb_vm_error());
        end_line();
        return 1;
    }
    return 0;
}

int main(void)
{
    hal_init();
    plat_out("A PLATFORM BETWEEN");
    end_line();
    end_line();
    for (;;) {
        if (hal_menu(start_labels, 2) == 1) {
            if (apb_vm_resume() == 0) {
                plat_out("Picking up where you left off.");
                end_line();
                end_line();
                break;
            }
            plat_out("There's no trip to pick up: ");
            plat_out(apb_vm_error());
            end_line();
            end_line();
        } else if (board() == 0) {
            break;
        }
    }
    if (apb_vm_run() != APB_VM_ERROR) {
        show_receipt(apb_vm_receipt());
    }
    plat_out("(press a key)");
    end_line();
    key();
    return 0;
}
