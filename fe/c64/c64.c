/*
 * The Commodore 64 front end (milestone E4, docs/c64.md): the HAL on the C64's screen,
 * keyboard and 1541 disk drive. The game is the program plus three overlays (LOAD, PASS
 * and BATTLE) that load from disk when the VM asks for them, and the Departure's own
 * files, DEPOT and CAR00, CAR01, ..., on the same disk.
 *
 * Text is written straight to the screen in upper/lower case, word-wrapped at 40
 * columns, into a window under the status bar (and the picture, when there is one), and
 * waits with "-- more --" before anything scrolls off unread. Game text arrives in ASCII
 * and is turned into PETSCII here; the client's own messages are C strings, which cc65
 * has already made PETSCII.
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
#define LAST_ROW (ROWS - 1)

#define SCREEN     ((uint8_t *)0x0400)
#define COLORS     ((uint8_t *)0xD800)
#define BORDER     (*(volatile uint8_t *)0xD020)
#define BACKGROUND (*(volatile uint8_t *)0xD021)
#define VIC_MEMORY (*(volatile uint8_t *)0xD018)
#define CASE_LOCK  (*(volatile uint8_t *)0x0291)
#define JIFFY_LO   (*(volatile uint8_t *)0x00A2)
#define JIFFY_MID  (*(volatile uint8_t *)0x00A1)

#define PET_RETURN  0x0D
#define PET_DEL     0x14

#define INK_BLACK  0
#define INK_GREEN  5
#define INK_YELLOW 7
#define INK_GRAY   12
#define INK_LGREEN 13

/* The screen (docs/c64.md): row 0 is the status bar; under it, the picture (rows 1-12)
 * when there is one; the rest is the text window, written at the bottom row and
 * scrolled up a row at a time. Only the window scrolls, so the picture's colours and
 * the status bar stay put. */
#define PICTURE_TOP 1
#define PICTURE_ROWS 12

/* fe/c64/split.s: the raster split, and putting a loaded picture on screen. */
void split_on(void);
void split_off(void);
void pic_show(void);

/* ----------------------------------------------------------------- text */

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static uint8_t col;             /* where the cursor is on the bottom row          */
static uint8_t top;             /* the text window's first row                    */
static uint8_t rows_shown;      /* rows printed since the player last pressed a key */
static uint8_t reverse;         /* 0x80: characters in reverse                    */
static uint8_t ink = INK_LGREEN;
static uint8_t word[COLS];
static uint8_t word_len;
static uint8_t spaces;          /* spaces waiting to go before the next word   */

static void more(void);

/* PETSCII to the screen's own codes (upper/lower case set). */
static uint8_t screen_code(uint8_t c)
{
    if (c < 0x20) return 0x20;
    if (c < 0x40) return c;
    if (c < 0x60) return (uint8_t)(c - 0x40);
    if (c < 0x80) return (uint8_t)(c - 0x20);
    if (c < 0xA0) return 0x20;
    if (c < 0xC0) return (uint8_t)(c - 0x40);
    if (c == 0xFF) return 0x5E;
    return (uint8_t)(c - 0x80);
}

static void clear_row(uint8_t row)
{
    memset(SCREEN + row * COLS, 0x20, COLS);
    memset(COLORS + row * COLS, ink, COLS);
}

/* The end of a row: scroll the window up one. tests/c64/run_c64.py reads the bottom
 * row as this function starts, so don't rename it. */
static void newline(void)
{
    memmove(SCREEN + top * COLS, SCREEN + (top + 1) * COLS, (LAST_ROW - top) * COLS);
    memmove(COLORS + top * COLS, COLORS + (top + 1) * COLS, (LAST_ROW - top) * COLS);
    clear_row(LAST_ROW);
    col = 0;
    more();
}

static void put(uint8_t c)
{
    if (col == COLS) newline();
    SCREEN[LAST_ROW * COLS + col] = (uint8_t)(screen_code(c) | reverse);
    COLORS[LAST_ROW * COLS + col] = ink;
    ++col;
}

/* Before anything scrolls off unread. */
static void more(void)
{
    static const char msg[] = "-- more --";
    uint8_t i;

    if (++rows_shown < LAST_ROW - top) return;
    reverse = 0x80;
    for (i = 0; msg[i]; ++i) put((uint8_t)msg[i]);
    reverse = 0;
    gotoxy(col, LAST_ROW);
    cursor(1);
    cgetc();
    cursor(0);
    clear_row(LAST_ROW);
    col = 0;
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
    newline();
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

    gotoxy(col, LAST_ROW);
    cursor(1);
    k = (uint8_t)cgetc();
    cursor(0);
    rows_shown = 0;
    return k;
}

static void draw_status(void);

void hal_init(void)
{
    uint8_t row;

    BORDER = INK_BLACK;
    BACKGROUND = INK_BLACK;
    VIC_MEMORY = 0x17;          /* screen at $0400, the upper/lower case characters */
    CASE_LOCK = 0x80;           /* and C= + SHIFT can't switch them back            */
    for (row = 0; row < ROWS; ++row) clear_row(row);
    top = 1;
    col = rows_shown = 0;
    draw_status();
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

/* Pictures are files pic00, pic01, ... on the disk (tools/c64pic.py), loaded into the
 * RAM under the KERNAL at $E000, where the VIC can show it but nothing else lives. A
 * missing picture just leaves the last one up. */
static uint8_t picture_up;      /* a picture is loaded at $E000 */

void hal_picture(uint8_t id, const char *name)
{
    static char pic[] = "pic00";
    uint8_t row;

    (void)name;
    pic[3] = (char)('0' + id / 10);
    pic[4] = (char)('0' + id % 10);
    BORDER = INK_GRAY;
    if (cbm_load(pic, 8, 0) != 0) {
        picture_up = 1;
        pic_show();
        if (top != PICTURE_TOP + PICTURE_ROWS) {
            /* The text window shrinks to the rows under the picture. */
            for (row = PICTURE_TOP; row < PICTURE_TOP + PICTURE_ROWS; ++row) clear_row(row);
            top = PICTURE_TOP + PICTURE_ROWS;
            rows_shown = 0;
            split_on();
        }
    }
    BORDER = INK_BLACK;
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
    draw_status();
}

/* Row 0, in reverse: "Kestrel  Lvl 1  HP 27/27  Debt 0", or the game's name. */
static void draw_status(void)
{
    static const char title[] = "A PLATFORM BETWEEN";
    uint8_t i;
    uint8_t c;

    for (i = 0; i < COLS; ++i) {
        SCREEN[i] = 0xA0;
        COLORS[i] = INK_YELLOW;
    }
    if (status_ch) {
        apb_view_status(line, status_ch, apb_vm_health());
        for (i = 0; line[i] && i < COLS - 1; ++i) {
            c = screen_code(petscii((uint8_t)line[i]));
            SCREEN[i + 1] = (uint8_t)(c | 0x80);
        }
    } else {
        for (i = 0; title[i]; ++i) SCREEN[i + 1] = (uint8_t)(screen_code((uint8_t)title[i]) | 0x80);
    }
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

    draw_status();
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
                --col;
                SCREEN[LAST_ROW * COLS + col] = 0x20;
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

/* A fight needs the whole screen for its map and menus: the picture goes, and comes
 * back when the fight's over. */
void apb_view_fight(uint8_t on)
{
    uint8_t row;

    if (!picture_up) return;
    if (on) {
        split_off();
        top = PICTURE_TOP;
    } else {
        for (row = PICTURE_TOP; row < PICTURE_TOP + PICTURE_ROWS; ++row) clear_row(row);
        pic_show();
        top = PICTURE_TOP + PICTURE_ROWS;
        split_on();
    }
    rows_shown = 0;
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
    uint8_t with_pass;
    uint16_t seed;

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
    with_pass = apb_desk_pass(&traveler, apb_vm_departure(), &pass);
    seed = (uint16_t)(JIFFY_LO | (JIFFY_MID << 8));
    if (!with_pass && apb_vm_siding()) seed = apb_desk_yard(seed);   /* a Siding's yard */
    if ((with_pass ? apb_vm_board_pass(&traveler, &pass) : apb_vm_board(&traveler, seed)) != 0) {
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
        draw_status();
        show_receipt(apb_vm_receipt());
    }
    plat_out("(press a key)");
    end_line();
    key();
    split_off();
    return 0;
}
