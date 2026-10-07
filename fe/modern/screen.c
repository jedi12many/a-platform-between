/*
 * The modern front end's screen and HAL (fe/modern/modern.h). It works like the C64's
 * (fe/c64/c64.c): 40 columns, word-wrapped into a text window that scrolls up from the
 * bottom row, "-- more --" before anything scrolls off unread, a status bar on row 0
 * and the picture on rows 1-12. Menus can be picked with a key or a click.
 */
#include <stdlib.h>
#include <string.h>

#include "apb.h"
#include "apb_desk.h"
#include "apb_hal.h"
#include "apb_view.h"
#include "apb_vm.h"
#include "modern.h"

#define LAST_ROW (SCR_ROWS - 1)

/* The C64's colours, by number. */
#define INK_WHITE   1
#define INK_YELLOW  7
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

static uint8_t col;             /* where the cursor is on the bottom row          */
static uint8_t top = 1;         /* the text window's first row                    */
static uint8_t rows_shown;      /* rows printed since the player last pressed a key */
static uint8_t reverse;         /* 0x80: characters in reverse                    */
static uint8_t ink = INK_LGREY;
static char word[SCR_COLS];
static uint8_t word_len;
static uint8_t spaces;          /* spaces waiting to go before the next word   */

static void more(void);

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

    scr_cursor_row = LAST_ROW;
    scr_cursor_col = col;
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

/* The end of a row: into the transcript, if there is one, and scroll the window up. */
static void newline(void)
{
    int n = SCR_COLS;
    int i;

    if (transcript) {
        while (n && (scr_char[LAST_ROW][n - 1] & 0x7F) == ' ') --n;
        for (i = 0; i < n; ++i) fputc(scr_char[LAST_ROW][i] & 0x7F, transcript);
        fputc('\n', transcript);
    }
    memmove(scr_char[top], scr_char[top + 1], (size_t)(LAST_ROW - top) * SCR_COLS);
    memmove(scr_ink[top], scr_ink[top + 1], (size_t)(LAST_ROW - top) * SCR_COLS);
    clear_row(LAST_ROW);
    col = 0;
    more();
}

static void put(char c)
{
    if (col == SCR_COLS) newline();
    if ((unsigned char)c < 0x20 || (unsigned char)c > 0x7E) c = ' ';
    scr_char[LAST_ROW][col] = (uint8_t)((uint8_t)c | reverse);
    scr_ink[LAST_ROW][col] = ink;
    ++col;
}

/* Before anything scrolls off unread. (A choices file reads everything at once.) */
static void more(void)
{
    static const char msg[] = "-- more --";
    uint8_t i;

    if (++rows_shown < LAST_ROW - top) return;
    if (choices) {
        rows_shown = 0;
        return;
    }
    reverse = 0x80;
    for (i = 0; msg[i]; ++i) put(msg[i]);
    reverse = 0;
    key();
    clear_row(LAST_ROW);
    col = 0;
    rows_shown = 0;
}

static void flush_word(void)
{
    uint8_t i;

    if (!word_len) return;
    if (col) {
        if (col + spaces + word_len > SCR_COLS) {
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
        if (word_len == SCR_COLS) flush_word();
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
    top = 1;
    col = rows_shown = 0;
    draw_status();
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

void hal_check(uint8_t rating, const apb_roll *roll)
{
    apb_view_check(line, rating, roll);
    out(line);
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
            end_line();
            return (uint8_t)(k - '1');
        }
        if (k == 's' || k == 'S') {
            echo_key((char)k);
            return APB_MENU_SAVE;
        }
    }
}

void hal_ask_line(char *dst, uint8_t max)
{
    uint8_t n = 0;
    uint16_t k;

    out("> ");
    settle();
    for (;;) {
        k = key_for(1);
        if (k == KEY_RETURN) break;
        if (k == KEY_DELETE) {
            if (n) {
                --n;
                --col;
                scr_char[LAST_ROW][col] = ' ';
            }
        } else if (k >= 0x20 && k <= 0x7E && n < max && col < SCR_COLS - 1) {
            dst[n++] = (char)k;
            put((char)k);
        }
    }
    dst[n] = '\0';
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
    uint8_t row;

    snprintf(path, sizeof(path), "%s/pic%02u.apic", dir, id);
    if (transcript) {
        settle();
        fprintf(transcript, "[picture %s]\n", name);
    }
    if (!load_picture(path)) return;
    picture_up = 1;
    scr_picture_shown = 1;
    if (top != PIC_TOP + PIC_ROWS) {
        /* The text window shrinks to the rows under the picture. */
        for (row = PIC_TOP; row < PIC_TOP + PIC_ROWS; ++row) clear_row(row);
        top = PIC_TOP + PIC_ROWS;
        rows_shown = 0;
    }
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

/* A fight needs the whole screen for its map and menus: the picture goes, and comes
 * back when the fight's over. */
void apb_view_fight(uint8_t on)
{
    uint8_t row;

    if (!picture_up) return;
    if (on) {
        scr_picture_shown = 0;
        top = PIC_TOP;
    } else {
        for (row = PIC_TOP; row < PIC_TOP + PIC_ROWS; ++row) clear_row(row);
        scr_picture_shown = 1;
        top = PIC_TOP + PIC_ROWS;
    }
    rows_shown = 0;
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

static uint8_t board(uint16_t seed)
{
    uint8_t with_pass;

    apb_desk_run(&traveler);
    if (apb_vm_open() != 0) {
        out("This Departure can't be boarded: ");
        out(apb_vm_error());
        end_line();
        return 1;
    }
    end_line();
    with_pass = apb_desk_pass(&traveler, apb_vm_departure(), &pass);
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
    if (apb_vm_run() != APB_VM_ERROR) {
        draw_status();
        show_receipt(apb_vm_receipt());
    }
    out("(press a key)");
    end_line();
    key();
    if (transcript) {
        fprintf(transcript, "[the trip is over]\n");
        fflush(transcript);
    }
}
