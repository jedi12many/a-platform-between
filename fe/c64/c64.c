/*
 * The Commodore 64 front end (milestone E4, docs/c64.md): the HAL on the C64's screen,
 * keyboard and 1541 disk drive. The game is the program plus three overlays (LOAD, PASS
 * and BATTLE) that load from disk when the VM asks for them, and the Departure's own
 * files, DEPOT and CAR00, CAR01, ..., on the same disk.
 *
 * The screen is framed (docs/frames.md): the status bar on row 0, the view under it (the
 * picture on rows 1-12, or a fight's map on rows 0-15, fe/c64/scene.c), and under that
 * the story log, word-wrapped at 25 columns, which waits with "-- more --" before
 * anything scrolls off unread; beside it the party and the dice log; and the command row
 * at the foot, where keys are asked for and lines typed. Game text arrives in ASCII and
 * is turned into PETSCII here; the client's own messages are C strings, which cc65 has
 * already made PETSCII.
 */
#include <cbm.h>
#include <string.h>

#include "apb.h"
#include "apb_desk.h"
#include "apb_hal.h"
#include "apb_view.h"
#include "apb_vm.h"
#include "apb_cue.h"
#include "apb_scene.h"

#define COLS 40
#define ROWS 25

/* The frames (docs/frames.md). */
#define LOG_TOP    16
#define LOG_ROWS   8
#define LAST_ROW   (LOG_TOP + LOG_ROWS - 1)     /* the story log's bottom row      */
#define LOG_COLS   APB_FRAME_LOG_COLS
#define SIDE_COL   (LOG_COLS + 1)
#define SIDE_COLS  APB_FRAME_SIDE_COLS
#define PARTY_TOP  16
#define DICE_TOP   20
#define INPUT_ROW  24

/* The frames' own characters in our font (tools/c64font.py). */
#define G_LINE  0x60
#define G_EMPTY 0x61
#define G_HALF  0x62
#define G_FULL  0x63

#define SCREEN     ((uint8_t *)0xF800)  /* in VIC bank 3, under the KERNAL: write only */
#define COLORS     ((uint8_t *)0xD800)
#define BORDER     (*(volatile uint8_t *)0xD020)
#define BACKGROUND (*(volatile uint8_t *)0xD021)
#define BLINK_OFF  (*(volatile uint8_t *)0x00CC)
#define JIFFY_LO   (*(volatile uint8_t *)0x00A2)
#define JIFFY_MID  (*(volatile uint8_t *)0x00A1)

#define PET_RETURN  0x0D
#define PET_DEL     0x14

#define INK_BLACK  0
#define INK_WHITE  1
#define INK_RED    2
#define INK_CYAN   3
#define INK_GREEN  5
#define INK_BLUE   6
#define INK_YELLOW 7
#define INK_DGRAY  11
#define INK_GRAY   12
#define INK_LGREEN 13


/* fe/c64/split.s: the raster split, putting a loaded picture on screen, the text screen
 * and our font, and scrolling the text window (the screen is in the RAM under the
 * KERNAL ROM, which only the VIC and writes reach: reading it needs the ROM out). */
void split_on(void);
void split_off(void);
void irq_on(void);
void irq_off(void);
void pic_show(void);
void text_screen(void);
void font_install(void);
/* Rows top to scroll_last - 1 take the row under them, between columns scroll_left and
 * scroll_right - 1. */
extern uint8_t scroll_last, scroll_left, scroll_right;
void __fastcall__ text_scroll(uint8_t top);

/* fe/c64/tune.s: the music player's way in (docs/music.md). */
void tune_install(void);
void __fastcall__ tune_start(uint8_t t);
void __fastcall__ tune_change(uint8_t t);
uint8_t __fastcall__ tune_find(const char *ascii);
uint8_t tune_playing(void);
void tune_silence(void);

/* ----------------------------------------------------------------- text */

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static uint8_t col;             /* where the cursor is on the story log's bottom row */
static uint8_t icol;            /* and on the command row, where keys are asked for */
static uint8_t rows_shown;      /* rows printed since the player last pressed a key */
static uint8_t ink = INK_LGREEN;
/* Text buffers in the cassette buffer, $0334-$03FF (fe/c64/apb.cfg), which nothing else
 * uses: the main program has no room to spare. */
#pragma bss-name (push, "TAPEBSS")
static uint8_t word[LOG_COLS];
static char line[APB_VIEW_LINE];
static char roll_top[APB_VIEW_ROLL];
static char roll_bottom[APB_VIEW_ROLL];
static char file_name[24];
#pragma bss-name (pop)
static uint8_t word_len;
static uint8_t spaces;          /* spaces waiting to go before the next word   */

static void more(void);
static uint8_t wait_key(void);

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

static uint8_t petscii(uint8_t c);

/* Text at c0, row, in `colour`, padded with spaces to `width`: PETSCII, or ASCII.
 * (Static locals, here and below: cc65 makes far less code of them.) */
static void put_at(uint8_t c0, uint8_t row, const char *s, uint8_t colour, uint8_t width,
                   uint8_t ascii)
{
    static uint8_t *p;
    static uint8_t c;

    p = SCREEN + row * COLS + c0;
    while (width--) {
        c = (uint8_t)(*s ? *s++ : 0x20);
        if (ascii) c = petscii(c);
        *p = screen_code(c);
        p[COLORS - SCREEN] = colour;
        ++p;
    }
}

/* The command row: `s` from its start, the rest blank; the cursor after it. */
static void command(const char *s, uint8_t colour, uint8_t ascii)
{
    put_at(0, INPUT_ROW, s, colour, COLS, ascii);
    icol = (uint8_t)strlen(s);
}

/* The view: the game's name, until a picture comes. */
static void clear_view(void)
{
    uint8_t row;

    for (row = 1; row < LOG_TOP; ++row) clear_row(row);
    put_at(11, 8, "A Platform Between", INK_DGRAY, 18, 0);
}

/* The end of a row: scroll the story log up one. tests/c64/run_c64.py reads the log's
 * bottom row as this function starts, so don't rename it. */
static void newline(void)
{
    more();
    scroll_last = LAST_ROW;
    scroll_left = 0;
    scroll_right = LOG_COLS;
    text_scroll(LOG_TOP);
    memset(SCREEN + LAST_ROW * COLS, 0x20, LOG_COLS);
    col = 0;
}

static void put(uint8_t c)
{
    if (col == LOG_COLS) newline();
    SCREEN[LAST_ROW * COLS + col] = screen_code(c);
    COLORS[LAST_ROW * COLS + col] = ink;
    ++col;
}

/* Before the log scrolls: if its top row hasn't been read, wait. rows_shown is the rows
 * over the bottom one printed since the player last pressed a key. */
static void more(void)
{
    uint8_t i;

    if (rows_shown < LOG_ROWS - 1) {
        ++rows_shown;
        return;
    }
    command("-- more --", INK_YELLOW, 0);
    for (i = 0; i < 10; ++i) SCREEN[INPUT_ROW * COLS + i] |= 0x80;
    wait_key();
    command("", ink, 0);
    rows_shown = 0;
}

static void flush_word(void)
{
    uint8_t i;

    if (!word_len) return;
    if (col) {
        if (col + spaces + word_len > LOG_COLS) {
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
        if (word_len == LOG_COLS) flush_word();
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
    if (c >= 0x7B && c <= 0x7E) return (uint8_t)(c + 0x60);     /* { | } ~ in our font */
    if (c >= 0x7F) return 0x2D;
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

/* A key, with the cursor where the next character goes: a block that blinks with the
 * clock (the ROM's cursor can't read the screen under the KERNAL, so it's ours). */
static uint8_t wait_key(void)
{
    uint8_t k;
    uint16_t at = (uint16_t)(INPUT_ROW * COLS + (icol < COLS ? icol : COLS - 1));

    COLORS[at] = ink;
    while (!(k = cbm_k_getin())) {
        SCREEN[at] = (uint8_t)(JIFFY_LO & 0x10 ? 0x20 : 0xA0);
    }
    SCREEN[at] = 0x20;
    return k;
}

static uint8_t key(void)
{
    uint8_t k = wait_key();

    rows_shown = 0;
    return k;
}

static void draw_status(void);

/* Only once, at the start: in the LOAD overlay (main asks for it first). */
#pragma code-name (push, "OVERLAY1")

void hal_init(void)
{
    uint8_t row;

    BORDER = INK_BLACK;
    BACKGROUND = INK_BLACK;
    BLINK_OFF = 1;              /* the ROM's cursor: never, it would read the ROM   */
    for (row = 0; row < ROWS; ++row) clear_row(row);
    /* Our font (tools/c64font.py, on every disk), loaded where the picture goes, then
     * moved under the I/O, where the VIC reads it. */
    if (cbm_load("font", 8, 0)) font_install();
    /* The Departure's music (tools/music/musicc.py --c64), there too before the pictures
     * need the room; then the raster interrupt that plays it, from now on. */
    if (cbm_load("music", 8, 0)) tune_install();
    text_screen();
    irq_on();
    clear_view();
    for (row = LOG_TOP; row <= LAST_ROW; ++row) {
        SCREEN[row * COLS + LOG_COLS] = G_LINE;      /* the frames' dividing line */
        COLORS[row * COLS + LOG_COLS] = INK_DGRAY;
    }
    col = icol = rows_shown = 0;
    draw_status();
}

#pragma code-name (pop)

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

/* "~ The Static ~", as the terminal has it (our font has the ~). */
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
static uint8_t picture_id;

/* ----------------------------------------------------------------- music */

uint8_t plat_tune_find(const char *ascii)
{
    return tune_find(ascii);
}

/* Into a tune: from silence at once, else after the one playing fades. */
void plat_tune_cue(uint8_t t)
{
    if (t != 255 && !tune_playing()) tune_start(t);
    else tune_change(t);
}

void hal_scene_music(uint8_t moment)
{
    apb_cue_scene(moment);
}

void hal_picture(uint8_t id, const char *name)
{
    static char pic[] = "pic00";

    (void)name;
    pic[3] = (char)('0' + id / 10);
    pic[4] = (char)('0' + id % 10);
    BORDER = INK_GRAY;
    if (cbm_load(pic, 8, 0) != 0) {
        picture_up = 1;
        picture_id = id;
        pic_show();
        split_on();
    }
    BORDER = INK_BLACK;
}

void hal_music(const char *name)
{
    apb_cue_story(name);
}


/* A check: into the dice log. */
void hal_check(uint8_t rating, const apb_roll *roll)
{
    apb_view_check_roll(roll_top, roll_bottom, line, rating, roll);
    hal_frame_roll(roll_top, roll_bottom, line);
}

static const apb_character *status_ch;

void hal_status(const apb_character *ch)
{
    status_ch = ch;
    draw_status();
}

/* Row 0, in reverse: "Kestrel  Lvl 1  HP 27/27  Debt 0", or the game's name; and the
 * traveler in the party frame. */
static void draw_status(void)
{
    static const char title[] = "A PLATFORM BETWEEN";
    static uint8_t i;

    if (status_ch) {
        apb_view_status(line, status_ch, apb_vm_health());
        put_at(1, 0, line, INK_YELLOW, COLS - 1, 1);
        apb_view_name(line, status_ch);
        hal_frame_member(0, line, apb_vm_health(), apb_health_max(status_ch),
                         APB_MEMBER_READY);
    } else {
        put_at(1, 0, title, INK_YELLOW, COLS - 1, 0);
    }
    SCREEN[0] = 0x20;
    COLORS[0] = INK_YELLOW;
    for (i = 0; i < COLS; ++i) SCREEN[i] |= 0x80;
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
            return (uint8_t)(k - '1');
        }
        if (k == 's' || k == 'S') {
            echo_key(k);
            return APB_MENU_SAVE;
        }
    }
}

/* Typed on the command row, then into the story log, "> " and all. */
void hal_ask_line(char *out, uint8_t max)
{
    uint8_t n = 0;
    uint8_t k;

    command("> ", INK_WHITE, 0);
    for (;;) {
        k = key();
        if (k == PET_RETURN) break;
        if (k == PET_DEL) {
            if (n) {
                --n;
                SCREEN[INPUT_ROW * COLS + --icol] = 0x20;
            }
        } else if (n < max && icol < COLS - 1
                   && ((k >= 0x20 && k < 0x60) || (k >= 0xC1 && k <= 0xDA))) {
            out[n++] = (char)k;
            SCREEN[INPUT_ROW * COLS + icol++] = screen_code(k);
        }
    }
    out[n] = '\0';
    command("", ink, 0);
    plat_out("> ");
    settle();
    for (k = 0; k < n; ++k) put((uint8_t)out[k]);
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

/* A line of the receipt (client/receipt_view.c). */
void apb_view_out(const char *ascii, uint8_t wrap)
{
    if (wrap) {
        ascii_out(ascii);
    } else {
        settle();
        while (*ascii) put(petscii((uint8_t)*ascii++));
    }
    end_line();
}

/* ------------------------------------------------------- the battle screen */

/* Code only a fight uses is in the BATTLE overlay, with the fight (docs/c64.md). */
#pragma code-name (push, "OVERLAY3")

/* fe/c64/scene.c, the battle screen, has the view for a fight (on) and gives it back
 * after (off): the frames under it are this file's all along, but the view's colours are
 * the fight's, and the picture's memory under the KERNAL has the fight's graphics. */
void c64_scene(uint8_t on)
{
    if (on) {
        settle();
        if (col) newline();
        if (picture_up) split_off();
        return;
    }
    apb_cue_back();
    clear_view();
    draw_status();
    if (picture_up) {
        picture_up = 0;
        hal_picture(picture_id, 0);
    }
    rows_shown = 0;
}

/* ------------------------------------------------------------------ the frames */

void hal_frame_say(const char *ascii)
{
    settle();
    if (col) newline();
    rows_shown = 0;
    ascii_out(ascii);
    end_line();
    rows_shown = 0;
}

#pragma code-name (pop)

/* The dice log: each roll two rows, the newest at the bottom, bright. The record is
 * the tests' (hal_scene_log, fe/c64/split.s). */
void hal_frame_roll(const char *top, const char *bottom, const char *record)
{
    scroll_last = LAST_ROW;
    scroll_left = SIDE_COL;
    scroll_right = COLS;
    text_scroll(DICE_TOP);
    text_scroll(DICE_TOP);
    memset(COLORS + DICE_TOP * COLS + SIDE_COL, INK_GRAY, SIDE_COLS);
    memset(COLORS + (DICE_TOP + 1) * COLS + SIDE_COL, INK_GRAY, SIDE_COLS);
    put_at(SIDE_COL, LAST_ROW - 1, top, INK_WHITE, SIDE_COLS, 1);
    put_at(SIDE_COL, LAST_ROW, bottom, INK_CYAN, SIDE_COLS, 1);
    hal_scene_log(record);
}

void hal_frame_member(uint8_t slot, const char *name, uint8_t health, uint8_t max,
                      uint8_t state)
{
    static const char down[] = "down";
    static uint8_t row;
    static uint8_t halves;
    static uint8_t k;
    static uint8_t c;
    static uint8_t *bar;

    row = (uint8_t)(PARTY_TOP + slot);
    put_at(SIDE_COL, row, "", INK_WHITE, SIDE_COLS, 0);
    if (!*name) return;
    put_at(SIDE_COL + 1, row, name, state == APB_MEMBER_TURN ? INK_YELLOW : INK_WHITE,
           APB_FRAME_NAME, 1);
    bar = SCREEN + row * COLS + SIDE_COL;
    if (state == APB_MEMBER_TURN) *bar = 0x3E;          /* > */
    if (state == APB_MEMBER_DOWN) {
        put_at(COLS - 5, row, down, INK_BLUE, 5, 0);
        return;
    }
    /* Health as a bar of five, in halves. */
    halves = (uint8_t)(max ? (uint16_t)health * 10 / max : 0);
    if (health && !halves) halves = 1;
    c = (uint8_t)((uint16_t)health * 3 <= max ? INK_RED : INK_GREEN);
    bar += SIDE_COLS - 5;
    for (k = 0; k < 5; ++k) {
        *bar = (uint8_t)(halves >= 2 ? G_FULL : halves ? G_HALF : G_EMPTY);
        bar[COLORS - SCREEN] = c;
        ++bar;
        halves = (uint8_t)(halves >= 2 ? halves - 2 : 0);
    }
}

#pragma code-name (push, "OVERLAY3")

void hal_frame_command(const char *ascii, uint8_t colour, uint8_t from, uint8_t to)
{
    command(ascii, colour, 1);
    while (from < to) COLORS[INPUT_ROW * COLS + from++] = INK_WHITE;
}

#pragma code-name (pop)

/* ----------------------------------------------------------------- disk */

#define DEVICE 8
#define LFN    2


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

/* In the PASS overlay, with the stamp's code: ask for it first. */
#pragma code-name (push, "OVERLAY2")

static void show_receipt(const apb_receipt *r)
{
    uint8_t i;
    uint8_t j;
    uint8_t stamped;

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

#pragma code-name (pop)

static uint8_t board(void)
{
    uint8_t with_pass;
    uint16_t seed;

    if (apb_vm_open() != 0) {
        plat_out("This Departure can't be boarded: ");
        plat_out(apb_vm_error());
        end_line();
        return 1;
    }
    APB_NEED(APB_OVL_PASS);
    with_pass = apb_desk_run(apb_vm_departure(), &traveler, &pass);
    end_line();
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
    APB_NEED(APB_OVL_LOAD);
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
        APB_NEED(APB_OVL_PASS);
        show_receipt(apb_vm_receipt());
    }
    plat_out("(press a key)");
    end_line();
    key();
    tune_silence();
    irq_off();
    return 0;
}
