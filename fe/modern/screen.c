/*
 * The modern front end's screen and HAL (fe/modern/modern.h). It works like the C64's
 * (fe/c64/c64.c), framed (docs/frames.md): a status bar on row 0 and the view under it
 * (the picture on rows 1-12, or a fight's map on rows 0-15); under that, the story log,
 * word-wrapped, scrolling up from its bottom row, "-- more --" before anything scrolls off
 * unread; beside it the party and the dice log; and the command row at the foot, where
 * the player types. Menus can be picked with a key or a click.
 */
#include <stdlib.h>
#include <string.h>

#include "apb.h"
#include "apb_desk.h"
#include "apb_hal.h"
#include "apb_view.h"
#include "apb_vm.h"
#include "apb_scene.h"
#include "modern.h"

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

/* The C64's colours, by number. */
#define INK_WHITE   1
#define INK_RED     2
#define INK_CYAN    3
#define INK_GREEN   5
#define INK_BLUE    6
#define INK_YELLOW  7
#define INK_DGREY  11
#define INK_GREY   12
#define INK_LGREEN 13
#define INK_LGREY  15

uint8_t scr_char[SCR_ROWS][SCR_COLS];
uint8_t scr_ink[SCR_ROWS][SCR_COLS];
uint8_t scr_cursor_row, scr_cursor_col, scr_cursor_on;
modern_picture scr_picture;
uint8_t scr_picture_shown;

static const char *dir;
static const char *save_dir;
static FILE *choices;
static FILE *transcript;

static uint8_t col;             /* where the cursor is on the story log's bottom row */
static uint8_t icol;            /* and on the command row, where keys are asked for */
static uint8_t rows_shown;      /* rows printed since the player last pressed a key */
static uint8_t reverse;         /* 0x80: characters in reverse                    */
static uint8_t ink = INK_LGREY;
static char word[SCR_COLS];
static uint8_t word_len;
static uint8_t spaces;          /* spaces waiting to go before the next word   */

static void more(void);
static void settle(void);
static void newline(void);

/* ----------------------------------------------------------------- keys */

static char typed[128];         /* the rest of a line from the choices file */
static size_t typed_at, typed_len;
static int typing;              /* a line is being typed from the choices file */

static void end_of_input(void)
{
    fprintf(transcript, "[end of input]\n");
    fflush(transcript);
    exit(0);
}

/* From the choices file: a whole line typed (for a typed line), or its first key. */
static uint16_t choice_key(int line)
{
    size_t n;

    if (typing) {
        if (typed_at < typed_len) return (uint8_t)typed[typed_at++];
        typing = 0;
        return KEY_RETURN;
    }
    if (!fgets(typed, sizeof(typed), choices)) end_of_input();
    n = strlen(typed);
    while (n && (typed[n - 1] == '\n' || typed[n - 1] == '\r')) typed[--n] = '\0';
    if (line) {
        typing = 1;
        typed_at = 0;
        typed_len = n;
        return choice_key(1);
    }
    return n ? (uint8_t)typed[0] : KEY_RETURN;
}

void (*modern_on_wait)(void);

static uint16_t key_for(int line)
{
    uint16_t k;

    scr_cursor_row = INPUT_ROW;
    scr_cursor_col = icol;
    scr_cursor_on = 1;
    if (modern_on_wait && !(line && typing)) modern_on_wait();
    k = choices ? choice_key(line) : plat_key();
    scr_cursor_on = 0;
    rows_shown = 0;
    return k;
}

static uint16_t key(void)
{
    return key_for(0);
}

uint16_t modern_key(void)
{
    uint16_t k;

    if (modern_on_wait) modern_on_wait();
    k = choices ? choice_key(0) : plat_key();
    rows_shown = 0;
    return k;
}

/* Before the battle screen takes over: the story's last row into the transcript. */
void modern_end_row(void)
{
    settle();
    if (col) newline();
}

void modern_log(const char *s)
{
    if (transcript) fprintf(transcript, "%s\n", s);
}

void modern_note(const char *s)
{
    if (transcript) {
        settle();
        fprintf(transcript, "%s\n", s);
    }
}

int modern_scripted(void)
{
    return choices != NULL;
}

/* A click on a row that starts "3. ", a menu line: as if 3 were pressed. */
static uint16_t menu_key(void)
{
    uint16_t k = key();
    uint8_t row;

    if (k & KEY_CLICK) {
        row = (uint8_t)(k & 0xFF);
        if (row < SCR_ROWS && scr_char[row][0] >= '1' && scr_char[row][0] <= '9'
            && scr_char[row][1] == '.') {
            return scr_char[row][0];
        }
        return 0;
    }
    return k;
}

/* ----------------------------------------------------------------- text */

static void clear_row(uint8_t row)
{
    memset(scr_char[row], ' ', SCR_COLS);
    memset(scr_ink[row], ink, SCR_COLS);
}

/* Text at col, row, in `colour`, padded with spaces to `width`. */
static void put_at(uint8_t c0, uint8_t row, const char *s, uint8_t colour, uint8_t width)
{
    uint8_t i;

    for (i = 0; i < width; ++i) {
        scr_char[row][c0 + i] = (uint8_t)(*s ? *s++ : ' ');
        scr_ink[row][c0 + i] = colour;
    }
}

/* The view: the game's name, until a picture comes. */
static void clear_view(void)
{
    uint8_t row;

    for (row = 1; row < LOG_TOP; ++row) clear_row(row);
    put_at(11, 8, "A Platform Between", INK_DGREY, 18);
}

/* The end of a row: into the transcript, if there is one, and scroll the log up. */
static void newline(void)
{
    int n = LOG_COLS;
    int i;
    uint8_t row;

    if (transcript) {
        while (n && (scr_char[LAST_ROW][n - 1] & 0x7F) == ' ') --n;
        for (i = 0; i < n; ++i) fputc(scr_char[LAST_ROW][i] & 0x7F, transcript);
        fputc('\n', transcript);
    }
    more();
    for (row = LOG_TOP; row < LAST_ROW; ++row) {
        memcpy(scr_char[row], scr_char[row + 1], LOG_COLS);
        memcpy(scr_ink[row], scr_ink[row + 1], LOG_COLS);
    }
    memset(scr_char[LAST_ROW], ' ', LOG_COLS);
    col = 0;
}

static void put(char c)
{
    if (col == LOG_COLS) newline();
    if ((unsigned char)c < 0x20 || (unsigned char)c > 0x7E) c = ' ';
    scr_char[LAST_ROW][col] = (uint8_t)((uint8_t)c | reverse);
    scr_ink[LAST_ROW][col] = ink;
    ++col;
}

/* The command row: `s` from its start, the rest blank; the cursor after it. */
static void command(const char *s, uint8_t colour)
{
    put_at(0, INPUT_ROW, s, colour, SCR_COLS);
    icol = (uint8_t)strlen(s);
}

/* Before the log scrolls: if its top row hasn't been read, wait. rows_shown is the rows
 * over the bottom one printed since the player last pressed a key. (A choices file reads
 * everything at once.) */
static void more(void)
{
    uint8_t i;

    if (rows_shown < LOG_ROWS - 1) {
        ++rows_shown;
        return;
    }
    if (choices) {
        rows_shown = 0;
        return;
    }
    command("-- more --", INK_YELLOW);
    for (i = 0; i < 10; ++i) scr_char[INPUT_ROW][i] |= 0x80;
    key();
    command("", ink);
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

/* One character into the word-wrapped stream. */
static void stream(char c)
{
    if (c == ' ') {
        flush_word();
        if (col) ++spaces;
    } else if (c == '\n') {
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

/* Game text and the client's own messages are both ASCII here. */
static void out(const char *s)
{
    while (*s) stream(*s++);
}

static void draw_status(void);

void modern_setup(const char *departure_dir, const char *saves, FILE *choice_file, FILE *out_file)
{
    uint8_t row;

    dir = departure_dir;
    save_dir = saves;
    choices = choice_file;
    transcript = out_file;
    for (row = 0; row < SCR_ROWS; ++row) clear_row(row);
    clear_view();
    for (row = LOG_TOP; row <= LAST_ROW; ++row) {
        scr_char[row][LOG_COLS] = SCR_GLYPH_LINE;     /* the frames' dividing line */
        scr_ink[row][LOG_COLS] = INK_DGREY;
    }
    col = icol = rows_shown = 0;
    draw_status();
    sound_setup();
}

void hal_init(void) {}
void hal_shutdown(void) {}

void hal_text_char(char c)
{
    stream(c);
}

void hal_text_end(void)
{
    end_line();
    end_line();
}

void hal_chapter(const char *title)
{
    out("~ ");
    out(title);
    out(" ~");
    end_line();
    end_line();
}

void hal_pause(void)
{
    out("(press a key)");
    end_line();
    key();
}

static char line[APB_VIEW_LINE];

static char roll_top[APB_VIEW_ROLL];
static char roll_bottom[APB_VIEW_ROLL];

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
    const char *text = "A PLATFORM BETWEEN";
    uint8_t i;

    if (status_ch) {
        apb_view_status(line, status_ch, apb_vm_health());
        text = line;
    }
    for (i = 0; i < SCR_COLS; ++i) {
        scr_char[0][i] = ' ' | 0x80;
        scr_ink[0][i] = INK_YELLOW;
    }
    for (i = 0; text[i] && i < SCR_COLS - 1; ++i) scr_char[0][i + 1] = (uint8_t)(text[i] | 0x80);
    if (status_ch) {
        apb_view_name(line, status_ch);
        hal_frame_member(0, line, apb_vm_health(), apb_health_max(status_ch), APB_MEMBER_READY);
    }
}

/* ------------------------------------------------------------- the frames */

void hal_frame_say(const char *ascii)
{
    settle();
    if (col) newline();
    rows_shown = 0;
    out(ascii);
    end_line();
    rows_shown = 0;
}

/* The dice log: each roll two rows, the newest at the bottom, bright. */
void hal_frame_roll(const char *top, const char *bottom, const char *record)
{
    uint8_t row;

    for (row = DICE_TOP; row + 2 < SCR_ROWS - 1; ++row) {
        memcpy(scr_char[row] + SIDE_COL, scr_char[row + 2] + SIDE_COL, SIDE_COLS);
        memset(scr_ink[row] + SIDE_COL, INK_GREY, SIDE_COLS);
    }
    put_at(SIDE_COL, (uint8_t)(LAST_ROW - 1), top, INK_WHITE, SIDE_COLS);
    put_at(SIDE_COL, LAST_ROW, bottom, INK_CYAN, SIDE_COLS);
    modern_note(record);
}

void hal_frame_member(uint8_t slot, const char *name, uint8_t health, uint8_t max,
                      uint8_t state)
{
    uint8_t row = (uint8_t)(PARTY_TOP + slot);
    uint8_t halves;
    uint8_t k;
    uint8_t c;

    if (slot > 3) return;
    put_at(SIDE_COL, row, "", INK_WHITE, SIDE_COLS);
    if (!*name) return;
    scr_char[row][SIDE_COL] = state == APB_MEMBER_TURN ? '>' : ' ';
    scr_ink[row][SIDE_COL] = INK_YELLOW;
    for (k = 0; k < APB_FRAME_NAME && name[k]; ++k) {
        scr_char[row][SIDE_COL + 1 + k] = (uint8_t)name[k];
        scr_ink[row][SIDE_COL + 1 + k] = state == APB_MEMBER_TURN ? INK_YELLOW : INK_WHITE;
    }
    if (state == APB_MEMBER_DOWN) {
        put_at(SCR_COLS - 5, row, "down", INK_BLUE, 5);
        return;
    }
    /* Health as a bar of five, in halves. */
    halves = (uint8_t)(max ? (unsigned)health * 10 / max : 0);
    if (health && !halves) halves = 1;
    c = (uint8_t)((unsigned)health * 3 <= max ? INK_RED : INK_GREEN);
    for (k = 0; k < 5; ++k) {
        scr_char[row][SCR_COLS - 5 + k] = halves >= 2 ? SCR_GLYPH_FULL
                                          : halves == 1 ? SCR_GLYPH_HALF : SCR_GLYPH_EMPTY;
        scr_ink[row][SCR_COLS - 5 + k] = c;
        halves = (uint8_t)(halves >= 2 ? halves - 2 : 0);
    }
}

void hal_frame_command(const char *ascii, uint8_t colour, uint8_t from, uint8_t to)
{
    uint8_t i;

    command(ascii, colour);
    for (i = from; i < to && i < SCR_COLS; ++i) scr_ink[INPUT_ROW][i] = INK_WHITE;
}

/* "> 3": the key the player pressed, shown. */
static void echo_key(char k)
{
    out("> ");
    settle();
    put(k);
    end_line();
}

static void numbered(uint8_t i, const char *label)
{
    ink = INK_WHITE;
    put((char)('1' + i));
    out(". ");
    out(label);
    end_line();
    ink = INK_LGREY;
}

uint8_t hal_menu(const char *const *labels, uint8_t count)
{
    uint8_t i;
    uint16_t k;

    draw_status();
    for (i = 0; i < count; ++i) numbered(i, labels[i]);
    for (;;) {
        k = menu_key();
        if (k >= '1' && k < '1' + count) {
            echo_key((char)k);
            return (uint8_t)(k - '1');
        }
        if (k == 's' || k == 'S') {
            echo_key((char)k);
            return APB_MENU_SAVE;
        }
    }
}

/* Typed on the command row, then into the story log, "> " and all. */
void hal_ask_line(char *dst, uint8_t max)
{
    uint8_t n = 0;
    uint16_t k;

    command("> ", INK_WHITE);
    for (;;) {
        k = key_for(1);
        if (k == KEY_RETURN) break;
        if (k == KEY_DELETE) {
            if (n) {
                --n;
                scr_char[INPUT_ROW][--icol] = ' ';
            }
        } else if (k >= 0x20 && k <= 0x7E && n < max && icol < SCR_COLS - 1) {
            dst[n++] = (char)k;
            scr_char[INPUT_ROW][icol++] = (uint8_t)k;
        }
    }
    dst[n] = '\0';
    command("", ink);
    out("> ");
    settle();
    for (k = 0; k < n; ++k) put(dst[k]);
    end_line();
}

void hal_prompt(const char *msg)
{
    out(msg);
    end_line();
}

void hal_error(const char *msg)
{
    end_line();
    out("The train has derailed: ");
    out(msg);
    end_line();
}

/* ------------------------------------------------------------- pictures */

/* A picture file (tools/pictures.py): "APIC", width and height (16 bits, low byte first),
 * the number of colours (0 for 256), the palette (red, green, blue each), and a palette
 * index for each pixel, row by row. */
#define PIC_MAX_W 640
#define PIC_MAX_H 384
static uint8_t pic_pixels[PIC_MAX_W * PIC_MAX_H];

static int load_picture(const char *path)
{
    FILE *f = fopen(path, "rb");
    uint8_t head[9];
    unsigned w, h, colours;
    int ok = 0;

    if (!f) return 0;
    if (fread(head, 1, 9, f) == 9 && memcmp(head, "APIC", 4) == 0) {
        w = (unsigned)(head[4] | (head[5] << 8));
        h = (unsigned)(head[6] | (head[7] << 8));
        colours = head[8] ? head[8] : 256;
        if (w && h && w <= PIC_MAX_W && h <= PIC_MAX_H
            && fread(scr_picture.palette, 3, colours, f) == colours
            && fread(pic_pixels, 1, (size_t)w * h, f) == (size_t)w * h) {
            scr_picture.w = (uint16_t)w;
            scr_picture.h = (uint16_t)h;
            scr_picture.colours = (uint8_t)(colours - 1);
            scr_picture.pixels = pic_pixels;
            ok = 1;
        }
    }
    fclose(f);
    return ok;
}

static uint8_t picture_up;      /* a picture is loaded */

/* picNN.apic beside the Departure's files; a missing picture leaves the last one up. */
void hal_picture(uint8_t id, const char *name)
{
    char path[1024];

    snprintf(path, sizeof(path), "%s/pic%02u.apic", dir, id);
    if (transcript) {
        settle();
        fprintf(transcript, "[picture %s]\n", name);
    }
    if (!load_picture(path)) return;
    picture_up = 1;
    scr_picture_shown = 1;
    plat_show();
}

/* ------------------------------------------------------- the battle screen */

void apb_view_out(const char *ascii, uint8_t wrap)
{
    if (wrap) {
        out(ascii);
    } else {
        /* Map rows and the roster: as they are, spaces and all. */
        settle();
        while (*ascii) put(*ascii++);
    }
    end_line();
}

uint8_t apb_view_pick(uint8_t count)
{
    uint16_t k;

    for (;;) {
        k = menu_key();
        if (k >= '1' && k < '1' + count) {
            echo_key((char)k);
            return (uint8_t)(k - '1');
        }
    }
}

/* The text battle screen isn't this one's (client/tactics.c draws a fight in the view). */
void apb_view_fight(uint8_t on)
{
    (void)on;
}

/* After a fight: the view as it was, and the party's health from the story. */
void modern_view_back(void)
{
    clear_view();
    scr_picture_shown = picture_up;
    draw_status();
}

uint8_t apb_view_go_on(void)
{
    uint16_t k = key();

    if (k & KEY_CLICK) k = KEY_RETURN;
    echo_key(k == KEY_RETURN ? ' ' : (char)k);
    return (uint8_t)!(k == 't' || k == 'T');
}

/* ----------------------------------------------------------------- files */

uint8_t hal_load(const char *name, uint8_t *dst, uint16_t max, uint16_t *len)
{
    char path[1024];
    FILE *f;
    size_t n;

    snprintf(path, sizeof(path), "%s/%s", strcmp(name, "SAVE") == 0 ? save_dir : dir, name);
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
    char path[1024];
    FILE *f;
    size_t n;

    snprintf(path, sizeof(path), "%s/%s", save_dir, name);
    f = fopen(path, "wb");
    if (!f) return HAL_IO_ERROR;
    n = fwrite(src, 1, len, f);
    if (fclose(f) != 0 || n != len) return HAL_IO_ERROR;
    plat_saved();
    return HAL_OK;
}

/* ---------------------------------------------------------------- the trip */

static apb_character traveler;
static apb_pass pass;
static char stamp[APB_STAMP_BUF];

static const char *const start_labels[2] = { "Board", "Pick up a saved trip" };

static void show_receipt(const apb_receipt *r)
{
    uint8_t i;
    uint8_t j;
    uint8_t stamped = (uint8_t)(r->ticket && apb_stamp_encode(r, stamp) == APB_PP_OK);

    apb_view_receipt(r, stamped);
    for (i = 0; stamped && stamp[i]; i = (uint8_t)(i + APB_PASSWORD_LINE)) {
        settle();
        put(' ');
        put(' ');
        for (j = 0; j < APB_PASSWORD_LINE && stamp[i + j]; ++j) put(stamp[i + j]);
        end_line();
    }
}

/* A Boarding Pass the platform gave us (modern_give_pass): boarded without the desk. */
static char given[APB_PASS_BUF];

void modern_give_pass(const char *text)
{
    strncpy(given, text, sizeof(given) - 1);
    given[sizeof(given) - 1] = '\0';
}

static uint8_t board(uint16_t seed)
{
    uint8_t with_pass;

    if (apb_vm_open() != 0) {
        out("This Departure can't be boarded: ");
        out(apb_vm_error());
        end_line();
        return 1;
    }
    if (given[0] && apb_pass_decode(given, &pass, &traveler, 0) == APB_PP_OK
        && pass.departure == apb_vm_departure()) {
        with_pass = 1;                  /* the platform issued it: no codes to type */
    } else {
        with_pass = apb_desk_run(apb_vm_departure(), &traveler, &pass);
        end_line();
    }
    given[0] = '\0';
    if (!with_pass && apb_vm_siding()) seed = apb_desk_yard(seed);   /* a Siding's yard */
    if ((with_pass ? apb_vm_board_pass(&traveler, &pass) : apb_vm_board(&traveler, seed)) != 0) {
        out("This Departure can't be boarded: ");
        out(apb_vm_error());
        end_line();
        return 1;
    }
    return 0;
}

void modern_play(uint16_t seed)
{
    for (;;) {
        if (hal_menu(start_labels, 2) == 1) {
            if (apb_vm_resume() == 0) {
                out("Picking up where you left off.");
                end_line();
                end_line();
                break;
            }
            out("There's no trip to pick up: ");
            out(apb_vm_error());
            end_line();
            end_line();
        } else if (board(seed) == 0) {
            break;
        }
    }
    stamp[0] = '\0';
    if (apb_vm_run() != APB_VM_ERROR) {
        draw_status();
        show_receipt(apb_vm_receipt());
    }
    plat_trip_over(stamp);
    out("(press a key)");
    end_line();
    key();
    if (transcript) {
        fprintf(transcript, "[the trip is over]\n");
        fflush(transcript);
    }
}
