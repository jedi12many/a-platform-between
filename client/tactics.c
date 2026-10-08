/*
 * The battle screen with graphics (docs/c64-hardware.md, E9), shared by every front end
 * that has them (client/apb_scene.h): the map in tiles, three characters a square, nine
 * squares by five at a time; every fighter a figure of two sprites, a body and its
 * outline; the roster beside it, what happened under it, and the command bar at the
 * bottom, as in the Gold Box games: Move, Aim, Guard, Wait, Flee, Quick, Done.
 *
 * It implements the HAL's battle calls; the rules are core/src/battle.c's, unchanged, and
 * the sentences client/battle_text.c's, the same as the text screen's. Every sentence and
 * prompt also goes to hal_scene_log, so tests read a fight in words.
 */
#ifdef __CC65__
#include <ascii_charmap.h>      /* every literal in this file is ASCII */
#endif

#include <string.h>

#include "apb_battle.h"
#include "apb_hal.h"
#include "apb_scene.h"
#include "apb_view.h"
#include "apb_vm.h"

/* The screen. */
#define VIEW_W     9            /* squares across, and down, at a time */
#define VIEW_H     5
#define MAP_X      8            /* the map's top left, in pixels        */
#define MAP_Y      8
#define PANEL_COL  30
#define LOG_ROW    18
#define LOG_ROWS   4
#define LOG_WIDTH  38
#define PROMPT_ROW 22
#define BAR_ROW    24

/* Colours (the C64's). */
#define C_BLACK  0
#define C_WHITE  1
#define C_RED    2
#define C_CYAN   3
#define C_PURPLE 4
#define C_GREEN  5
#define C_BLUE   6
#define C_YELLOW 7

/* Sprites: the cursor and two effects on top, then each fighter's outline and body. */
#define SPR_CURSOR 0
#define SPR_EFFECT 1
#define SPR_SPARK  2
#define SPR_FIGHTER(i) (3 + 2 * (i))

/* The graphics file's tables (tools/battlegfx.py). */
#define T_SHARED  3
#define T_TILES   8
#define T_MARKED  152
#define T_LOOKS   160
#define T_EFFECTS 240
#define T_NAMES   256
#define STRANGER  7

static const uint8_t *g;
static apb_fighter bf;
static char line[APB_VIEW_LINE];
static char text[41];
static uint8_t ok[APB_MAP_H_MAX][APB_MAP_W_MAX];
static uint8_t marks;                         /* ok[][] is shown on the map        */
static uint8_t vx, vy;                        /* the top left square shown         */
static uint8_t look[APB_FIGHTERS_MAX];
static uint8_t shown_x[APB_FIGHTERS_MAX];     /* where each figure stands on screen */
static uint8_t shown_y[APB_FIGHTERS_MAX];
static uint8_t log_text[LOG_ROWS][LOG_WIDTH + 1];
static uint8_t log_new;                       /* rows of the newest sentence      */
static uint8_t on_quick;
static uint8_t whose;                         /* whose turn it is, for the roster  */

/* --------------------------------------------------------------------- drawing */

/* Text at col, row, padded with spaces to `width`. */
static void put_text(uint8_t col, uint8_t row, const char *s, uint8_t colour, uint8_t width)
{
    uint8_t i;

    for (i = 0; i < width; ++i) {
        hal_scene_put((uint8_t)(col + i), row, (uint8_t)(*s ? *s++ : ' '), colour);
    }
}

static uint8_t visible(uint8_t x, uint8_t y)
{
    return (uint8_t)(x >= vx && x < vx + VIEW_W && y >= vy && y < vy + VIEW_H);
}

static void draw_square(uint8_t x, uint8_t y)
{
    uint8_t t;
    uint8_t k;
    uint8_t col;
    uint8_t row;
    uint8_t ch;
    const uint8_t *tile;

    if (!visible(x, y)) return;
    t = (uint8_t)(apb_battle_tile(x, y) & 7);
    tile = g + T_TILES + t * 18;
    col = (uint8_t)(1 + (x - vx) * 3);
    row = (uint8_t)(1 + (y - vy) * 3);
    for (k = 0; k < 9; ++k) {
        ch = tile[k];
        if (k == 4 && marks && ok[y][x]) ch = g[T_MARKED + t];
        hal_scene_put((uint8_t)(col + k % 3), (uint8_t)(row + k / 3), ch, tile[9 + k]);
    }
}

static void draw_map(void)
{
    uint8_t x;
    uint8_t y;
    uint8_t col;
    uint8_t row;

    /* Squares outside a small map: black. */
    for (row = 1; row <= VIEW_H * 3; ++row) {
        for (col = 1; col <= VIEW_W * 3; ++col) hal_scene_put(col, row, ' ', C_BLACK);
    }
    for (y = vy; y < vy + VIEW_H && y < apb_battle_height(); ++y) {
        for (x = vx; x < vx + VIEW_W && x < apb_battle_width(); ++x) draw_square(x, y);
    }
}

/* The frame round the map, Gold Box style: characters 1-8 (tools/battlegfx.py). */
static void draw_frame(void)
{
    uint8_t i;

    hal_scene_put(0, 0, 1, C_BLUE);
    hal_scene_put(28, 0, 3, C_BLUE);
    hal_scene_put(0, 16, 5, C_BLUE);
    hal_scene_put(28, 16, 6, C_BLUE);
    for (i = 1; i < 28; ++i) {
        hal_scene_put(i, 0, 2, C_BLUE);
        hal_scene_put(i, 16, 8, C_BLUE);
    }
    for (i = 1; i < 16; ++i) {
        hal_scene_put(0, i, 4, C_BLUE);
        hal_scene_put(28, i, 7, C_BLUE);
    }
}

static int16_t square_px(uint8_t x)
{
    return (int16_t)(MAP_X + ((int16_t)x - vx) * 24);
}

static int16_t square_py(uint8_t y)
{
    return (int16_t)(MAP_Y + ((int16_t)y - vy) * 24);
}

/* A fighter's figure at pixel x, y (its square's corner), in colour `colour`. */
static void figure_at(uint8_t i, int16_t x, int16_t y, uint8_t colour)
{
    const uint8_t *l = g + T_LOOKS + look[i] * 5;
    uint8_t down;

    apb_battle_fighter(i, &bf);
    if (bf.state == APB_GONE) {
        hal_scene_sprite(SPR_FIGHTER(i), 0, 0, 0, 0, APB_SPR_OFF);
        hal_scene_sprite((uint8_t)(SPR_FIGHTER(i) + 1), 0, 0, 0, 0, APB_SPR_OFF);
        return;
    }
    down = (uint8_t)(bf.state == APB_DOWN ? 2 : 0);
    hal_scene_sprite(SPR_FIGHTER(i), x, (int16_t)(y + 2), l[1 + down], C_BLACK, APB_SPR_HIRES);
    hal_scene_sprite((uint8_t)(SPR_FIGHTER(i) + 1), x, (int16_t)(y + 2), l[down], colour,
                     APB_SPR_MULTI);
}

static void place(uint8_t i)
{
    if (!visible(shown_x[i], shown_y[i])) {
        hal_scene_sprite(SPR_FIGHTER(i), 0, 0, 0, 0, APB_SPR_OFF);
        hal_scene_sprite((uint8_t)(SPR_FIGHTER(i) + 1), 0, 0, 0, 0, APB_SPR_OFF);
        return;
    }
    figure_at(i, square_px(shown_x[i]), square_py(shown_y[i]), g[T_LOOKS + look[i] * 5 + 4]);
}

static void place_all(void)
{
    uint8_t i;

    for (i = 0; i < apb_battle_count(); ++i) place(i);
}

static void cursor(uint8_t x, uint8_t y, uint8_t colour)
{
    if (!visible(x, y)) {
        hal_scene_sprite(SPR_CURSOR, 0, 0, 0, 0, APB_SPR_OFF);
        return;
    }
    hal_scene_sprite(SPR_CURSOR, (int16_t)(square_px(x) + 2), (int16_t)(square_py(y) + 1),
                     g[T_EFFECTS], colour, APB_SPR_HIRES);
}

static void cursor_off(void)
{
    hal_scene_sprite(SPR_CURSOR, 0, 0, 0, 0, APB_SPR_OFF);
}

/* Keep square x, y on the screen, a square in from the edge where the map allows. */
static void show_square(uint8_t x, uint8_t y)
{
    uint8_t nx = vx;
    uint8_t ny = vy;
    uint8_t w = apb_battle_width();
    uint8_t h = apb_battle_height();

    if (w > VIEW_W) {
        if (x < nx + 1) nx = (uint8_t)(x ? x - 1 : 0);
        if (x + 2 > nx + VIEW_W) nx = (uint8_t)(x + 2 - VIEW_W);
        if (nx + VIEW_W > w) nx = (uint8_t)(w - VIEW_W);
    }
    if (h > VIEW_H) {
        if (y < ny + 1) ny = (uint8_t)(y ? y - 1 : 0);
        if (y + 2 > ny + VIEW_H) ny = (uint8_t)(y + 2 - VIEW_H);
        if (ny + VIEW_H > h) ny = (uint8_t)(h - VIEW_H);
    }
    if (nx != vx || ny != vy) {
        vx = nx;
        vy = ny;
        draw_map();
        place_all();
    }
}

/* --------------------------------------------------------------------- the panel */

static char *bar_into(char *p, uint8_t health, uint8_t max)
{
    uint8_t k;
    uint8_t halves = (uint8_t)(max ? (uint16_t)health * 10 / max : 0);

    if (health && !halves) halves = 1;
    for (k = 0; k < 5; ++k) {
        *p++ = (char)(halves >= 2 ? 10 : halves == 1 ? 11 : 9);
        halves = (uint8_t)(halves >= 2 ? halves - 2 : 0);
    }
    return p;
}

static void draw_panel(void)
{
    uint8_t i;
    uint8_t row = 2;
    uint8_t colour;
    char *p;

    p = apb_view_put(text, "Round ");
    apb_view_unum(p, apb_battle_round());
    put_text(PANEL_COL, 0, text, C_CYAN, 10);
    for (i = 0; i < apb_battle_count() && row < 17; ++i) {
        apb_battle_fighter(i, &bf);
        if (bf.state == APB_GONE) continue;
        colour = (uint8_t)(i == whose ? C_YELLOW : bf.state == APB_DOWN ? C_BLUE : C_WHITE);
        put_text(PANEL_COL, row, apb_view_fighter(i), colour, 10);
        if (bf.state == APB_DOWN) {
            put_text(PANEL_COL, (uint8_t)(row + 1), "down", C_BLUE, 10);
        } else {
            p = bar_into(text, bf.health, bf.health_max);
            *p++ = ' ';
            p = apb_view_unum(p, bf.health);
            *p = '\0';
            put_text(PANEL_COL, (uint8_t)(row + 1), text, i ? C_RED : C_GREEN, 10);
        }
        row = (uint8_t)(row + 2);
    }
    while (row < 17) {
        put_text(PANEL_COL, row, "", C_WHITE, 10);
        ++row;
    }
}

/* --------------------------------------------------------------------- the log */

static void draw_log(void)
{
    uint8_t r;

    for (r = 0; r < LOG_ROWS; ++r) {
        put_text(1, (uint8_t)(LOG_ROW + r), (const char *)log_text[r],
                 r + log_new >= LOG_ROWS ? C_WHITE : C_CYAN, LOG_WIDTH);
    }
}

static void log_row(const char *s, uint8_t n)
{
    uint8_t r;

    for (r = 0; r + 1 < LOG_ROWS; ++r) memcpy(log_text[r], log_text[r + 1], LOG_WIDTH + 1);
    memcpy(log_text[LOG_ROWS - 1], s, n);
    log_text[LOG_ROWS - 1][n] = '\0';
    hal_scene_log((const char *)log_text[LOG_ROWS - 1]);
    if (log_new < LOG_ROWS) ++log_new;
}

/* A sentence into the log, broken between words to fit; the record has its rows. */
static void say(const char *s)
{
    uint8_t n;
    uint8_t cut;

    log_new = 0;
    while (*s) {
        n = (uint8_t)strlen(s);
        if (n <= LOG_WIDTH) {
            log_row(s, n);
            break;
        }
        for (cut = LOG_WIDTH; cut && s[cut] != ' '; --cut) {}
        if (!cut) cut = LOG_WIDTH;
        log_row(s, cut);
        s += cut;
        while (*s == ' ') ++s;
    }
    draw_log();
}

static void prompt(const char *s, uint8_t colour)
{
    put_text(1, PROMPT_ROW, s, colour, LOG_WIDTH);
}

/* --------------------------------------------------------------------- the bar */

static const char *const commands[] = { "Move", "Aim", "Guard", "Wait", "Flee", "Quick", "Done" };
static const char command_keys[] = "MAGWFQD";
#define COMMANDS 7

static void draw_bar(uint8_t chosen)
{
    uint8_t i;
    uint8_t col = 1;
    const char *s;

    for (i = 0; i < COMMANDS; ++i) {
        s = commands[i];
        while (*s) hal_scene_put(col++, BAR_ROW, (uint8_t)*s++, i == chosen ? C_WHITE : C_CYAN);
        hal_scene_put(col++, BAR_ROW, ' ', C_CYAN);
    }
    while (col < 40) hal_scene_put(col++, BAR_ROW, ' ', C_CYAN);
}

static void clear_bar(void)
{
    put_text(0, BAR_ROW, "", C_CYAN, 40);
}

/* --------------------------------------------------------------------- keys */

static const uint8_t digit_dir[] = {
    APB_KEY_DOWN_LEFT, APB_KEY_DOWN, APB_KEY_DOWN_RIGHT, APB_KEY_LEFT, APB_KEY_FIRE,
    APB_KEY_RIGHT, APB_KEY_UP_LEFT, APB_KEY_UP, APB_KEY_UP_RIGHT
};
static const char digits[] = "123456789";
static const char lower[] = "abcdefghijklmnopqrstuvwxyz";
static const char upper[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

/* A key: digits as the keypad's directions, small letters as capitals. */
static uint8_t key(void)
{
    uint8_t k = hal_scene_key();
    uint8_t i;

    for (i = 0; i < 9; ++i) {
        if (k == (uint8_t)digits[i]) return digit_dir[i];
    }
    for (i = 0; i < 26; ++i) {
        if (k == (uint8_t)lower[i]) return (uint8_t)upper[i];
    }
    if (k == ' ' || k == 13) return APB_KEY_FIRE;
    if (k == 8 || k == 27) return APB_KEY_BACK;
    return k;
}

static const int8_t dir_dx[] = { 0, 0, 0, -1, 1, -1, 1, -1, 1 };
static const int8_t dir_dy[] = { 0, -1, 1, 0, 0, -1, -1, 1, 1 };

/* --------------------------------------------------------------------- moving */

static uint8_t dist(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1)
{
    uint8_t dx = (uint8_t)(x0 > x1 ? x0 - x1 : x1 - x0);
    uint8_t dy = (uint8_t)(y0 > y1 ? y0 - y1 : y1 - y0);

    return dx > dy ? dx : dy;
}

/* The way a figure walks from where it's shown to x, y: one square at a time, each
 * step the one nearest the goal that isn't a wall or a pit (the rules have already
 * said the move is allowed; this is only how it looks). */
static uint8_t step_x;
static uint8_t step_y;

static void next_step(uint8_t x, uint8_t y, uint8_t gx, uint8_t gy)
{
    uint8_t d;
    uint8_t best = 0xFF;
    uint8_t nx;
    uint8_t ny;
    uint8_t t;

    step_x = gx;
    step_y = gy;
    for (d = 1; d < 9; ++d) {
        nx = (uint8_t)(x + dir_dx[d]);
        ny = (uint8_t)(y + dir_dy[d]);
        if (nx >= apb_battle_width() || ny >= apb_battle_height()) continue;
        t = apb_battle_tile(nx, ny);
        if (t == APB_TILE_WALL || t == APB_TILE_PIT) continue;
        if (dist(nx, ny, gx, gy) < best) {
            best = dist(nx, ny, gx, gy);
            step_x = nx;
            step_y = ny;
        }
    }
}

static void walk(uint8_t i, uint8_t gx, uint8_t gy)
{
    uint8_t steps = 0;
    uint8_t f;
    int16_t x0;
    int16_t y0;
    int16_t x1;
    int16_t y1;

    while ((shown_x[i] != gx || shown_y[i] != gy) && steps++ < 20) {
        next_step(shown_x[i], shown_y[i], gx, gy);
        show_square(step_x, step_y);
        x0 = square_px(shown_x[i]);
        y0 = square_py(shown_y[i]);
        x1 = square_px(step_x);
        y1 = square_py(step_y);
        hal_scene_sound(APB_SFX_STEP);
        for (f = 1; f <= 3; ++f) {
            figure_at(i, (int16_t)(x0 + (x1 - x0) * f / 3), (int16_t)(y0 + (y1 - y0) * f / 3),
                      g[T_LOOKS + look[i] * 5 + 4]);
            hal_scene_show(2);
        }
        shown_x[i] = step_x;
        shown_y[i] = step_y;
    }
    shown_x[i] = gx;
    shown_y[i] = gy;
    place(i);
}

/* --------------------------------------------------------------------- blows */

static void flash(uint8_t i, uint8_t colour)
{
    uint8_t n;

    if (!visible(shown_x[i], shown_y[i])) return;
    for (n = 0; n < 3; ++n) {
        figure_at(i, square_px(shown_x[i]), square_py(shown_y[i]), colour);
        hal_scene_show(3);
        place(i);
        hal_scene_show(3);
    }
}

static void spark(uint8_t i)
{
    if (!visible(shown_x[i], shown_y[i])) return;
    hal_scene_sprite(SPR_SPARK, (int16_t)(square_px(shown_x[i]) + 6),
                     (int16_t)(square_py(shown_y[i]) + 4), g[T_EFFECTS + 2], C_YELLOW,
                     APB_SPR_HIRES);
}

static void blow(const apb_event *e)
{
    uint8_t a = e->actor;
    uint8_t t = e->target;
    uint8_t f;
    int16_t x0;
    int16_t y0;
    int16_t x1;
    int16_t y1;

    show_square(shown_x[a], shown_y[a]);
    x0 = square_px(shown_x[a]);
    y0 = square_py(shown_y[a]);
    x1 = square_px(shown_x[t]);
    y1 = square_py(shown_y[t]);
    apb_battle_fighter(a, &bf);
    if (bf.ranged) {
        /* A bolt flies from one to the other. */
        hal_scene_sound(APB_SFX_SHOT);
        for (f = 0; f <= 8; ++f) {
            hal_scene_sprite(SPR_EFFECT, (int16_t)(x0 + (x1 - x0) * f / 8),
                             (int16_t)(y0 + 2 + (y1 - y0) * f / 8), g[T_EFFECTS + 1], C_CYAN,
                             APB_SPR_MULTI);
            hal_scene_show(1);
        }
        hal_scene_sprite(SPR_EFFECT, 0, 0, 0, 0, APB_SPR_OFF);
    } else {
        /* A lunge: a quarter of the way there and back, and a slash. */
        hal_scene_sound(APB_SFX_SWING);
        figure_at(a, (int16_t)(x0 + (x1 - x0) / 4), (int16_t)(y0 + (y1 - y0) / 4),
                  g[T_LOOKS + look[a] * 5 + 4]);
        hal_scene_sprite(SPR_EFFECT, (int16_t)(x1 + 6), (int16_t)(y1 + 2), g[T_EFFECTS + 3],
                         C_WHITE, APB_SPR_HIRES);
        hal_scene_show(4);
        hal_scene_sprite(SPR_EFFECT, 0, 0, 0, 0, APB_SPR_OFF);
        place(a);
    }
    if (e->roll.result == APB_FAIL) {
        hal_scene_sound(APB_SFX_MISS);
        hal_scene_show(4);
        return;
    }
    hal_scene_sound(APB_SFX_HIT);
    spark(t);
    flash(t, C_WHITE);
    hal_scene_sprite(SPR_SPARK, 0, 0, 0, 0, APB_SPR_OFF);
}

/* --------------------------------------------------------------------- the calls */

/* A fighter's look: a traveler by race; a foe by its name in the graphics' table. */
static uint8_t look_of(uint8_t i)
{
    const char *name;
    const uint8_t *entry;
    uint8_t k;
    uint8_t n;

    if (!i) return (uint8_t)(apb_vm_character()->race < STRANGER ? apb_vm_character()->race
                                                                  : STRANGER);
    name = apb_vm_foe_name(i);
    n = (uint8_t)strlen(name);
    for (k = 0; k < 8; ++k) {
        entry = g + T_NAMES + k * 32;
        if (entry[0] && entry[0] == n && !memcmp(entry + 1, name, n)) {
            return (uint8_t)(STRANGER + 1 + k);
        }
    }
    return STRANGER;
}

void hal_battle_begin(void)
{
    uint8_t i;
    uint8_t r;

    g = hal_scene_open();
    hal_scene_colours(C_BLUE, g[T_SHARED + 2], g[T_SHARED + 3], g[T_SHARED + 4],
                      g[T_SHARED], g[T_SHARED + 1]);
    apb_view_battle_reset();
    on_quick = 0;
    marks = 0;
    whose = 0xFF;
    vx = vy = 0;
    for (r = 0; r < 25; ++r) put_text(0, r, "", C_WHITE, 40);
    for (r = 0; r < LOG_ROWS; ++r) log_text[r][0] = '\0';
    for (i = 0; i < APB_SCENE_SPRITES; ++i) hal_scene_sprite(i, 0, 0, 0, 0, APB_SPR_OFF);
    for (i = 0; i < apb_battle_count(); ++i) {
        apb_battle_fighter(i, &bf);
        look[i] = look_of(i);
        shown_x[i] = bf.x;
        shown_y[i] = bf.y;
    }
    show_square(shown_x[0], shown_y[0]);
    draw_frame();
    draw_map();
    place_all();
    draw_panel();
    say("-- A fight! --");
}

void hal_battle_event(const apb_event *e)
{
    uint8_t said = apb_view_event(e, line);

    switch (e->kind) {
    case APB_EV_TURN:
        whose = e->actor;
        draw_panel();
        break;
    case APB_EV_MOVE:
        say(line);
        walk(e->actor, e->x, e->y);
        return;
    case APB_EV_ATTACK:
        blow(e);
        break;
    case APB_EV_DOWN:
        hal_scene_sound(APB_SFX_DOWN);
        place(e->target);
        break;
    case APB_EV_HAZARD:
        hal_scene_sound(APB_SFX_HIT);
        flash(e->actor, C_RED);
        break;
    case APB_EV_GONE:
        place(e->actor);
        break;
    }
    if (said != APB_VIEW_NOTHING) say(line);
    draw_panel();
}

/* --------------------------------------------------------------------- your turn */

static uint8_t here_x;
static uint8_t here_y;
static uint8_t waited;
static uint8_t to_x;
static uint8_t to_y;
static uint8_t targets[APB_FIGHTERS_MAX];

static void show_marks(uint8_t on)
{
    marks = on;
    draw_map();
}

/* Move: the figure follows a cursor over the squares it can reach; fire to stop there,
 * back to stay where it was. */
static void choose_square(uint8_t who)
{
    uint8_t k;
    uint8_t nx;
    uint8_t ny;
    uint8_t cx = to_x;
    uint8_t cy = to_y;

    prompt("Move: the arrows, then fire.", C_YELLOW);
    hal_scene_log("[Move]");
    for (;;) {
        show_square(cx, cy);
        shown_x[who] = cx;
        shown_y[who] = cy;
        place(who);
        cursor(cx, cy, C_YELLOW);
        k = key();
        if (k == APB_KEY_FIRE) {
            to_x = cx;
            to_y = cy;
            return;
        }
        if (k == APB_KEY_BACK) {
            shown_x[who] = to_x;
            shown_y[who] = to_y;
            place(who);
            return;
        }
        if (k >= APB_KEY_UP && k <= APB_KEY_DOWN_RIGHT) {
            nx = (uint8_t)(cx + dir_dx[k]);
            ny = (uint8_t)(cy + dir_dy[k]);
            if (nx < apb_battle_width() && ny < apb_battle_height() && ok[ny][nx]) {
                cx = nx;
                cy = ny;
                hal_scene_sound(APB_SFX_STEP);
            } else {
                hal_scene_sound(APB_SFX_NO);
            }
        }
    }
}

/* Aim: the cursor goes round the foes in reach from the square chosen; fire to attack.
 * Returns the target, or APB_NOBODY. */
static uint8_t choose_target(uint8_t who)
{
    uint8_t n = 0;
    uint8_t i;
    uint8_t at = 0;
    uint8_t k;
    char *p;

    for (i = 1; i < apb_battle_count(); ++i) {
        apb_battle_fighter(i, &bf);
        if (bf.state == APB_IN_FIGHT && apb_battle_can_attack(who, i, to_x, to_y)) {
            targets[n++] = i;
        }
    }
    if (!n) {
        hal_scene_sound(APB_SFX_NO);
        prompt("Nobody in reach from there.", C_RED);
        hal_scene_log("[Nobody in reach from there.]");
        return APB_NOBODY;
    }
    for (;;) {
        i = targets[at];
        show_square(shown_x[i], shown_y[i]);
        cursor(shown_x[i], shown_y[i], C_RED);
        p = apb_view_put(text, "Aim: ");
        p = apb_view_put(p, apb_view_fighter(i));
        p = apb_view_put(p, ", TN ");
        apb_view_num(p, apb_battle_tn(who, i));
        prompt(text, C_YELLOW);
        line[0] = '[';
        apb_view_put(apb_view_put(line + 1, text), "]");
        hal_scene_log(line);
        k = key();
        if (k == APB_KEY_FIRE) return i;
        if (k == APB_KEY_BACK) return APB_NOBODY;
        if (k >= APB_KEY_UP && k <= APB_KEY_DOWN_RIGHT) {
            at = (uint8_t)(k == APB_KEY_LEFT || k == APB_KEY_UP || k == APB_KEY_UP_LEFT
                           || k == APB_KEY_DOWN_LEFT ? (at ? at - 1 : n - 1)
                                                     : (at + 1 < n ? at + 1 : 0));
            hal_scene_sound(APB_SFX_SELECT);
        }
    }
}

static void act(apb_action *out, uint8_t kind, uint8_t target)
{
    out->move_x = to_x;
    out->move_y = to_y;
    out->kind = kind;
    out->target = target;
    show_marks(0);
    cursor_off();
    clear_bar();
    prompt("", C_WHITE);
}

void hal_battle_turn(uint8_t who, apb_action *out)
{
    uint8_t chosen = 0;
    uint8_t k;
    uint8_t i;
    uint8_t t;
    char *p;

    apb_battle_fighter(who, &bf);
    here_x = to_x = bf.x;
    here_y = to_y = bf.y;
    waited = bf.waited;
    shown_x[who] = bf.x;
    shown_y[who] = bf.y;
    whose = who;
    draw_panel();
    show_square(here_x, here_y);
    if (on_quick) {
        prompt("On quick: T takes over.", C_YELLOW);
        hal_scene_log("[On quick: T takes over.]");
        if (key() != 'T') {
            apb_battle_quick(who, out);
            prompt("", C_WHITE);
            return;
        }
        on_quick = 0;
    }
    apb_battle_reach_map(who, ok);
    show_marks(1);
    for (;;) {
        cursor(to_x, to_y, C_YELLOW);
        draw_bar(chosen);
        p = apb_view_put(text, apb_view_fighter(who));
        apb_view_put(p, ": choose.");
        prompt(text, C_YELLOW);
        line[0] = '[';
        apb_view_put(apb_view_put(line + 1, text), "]");
        hal_scene_log(line);
        k = key();
        if (k == APB_KEY_LEFT) {
            chosen = (uint8_t)(chosen ? chosen - 1 : COMMANDS - 1);
            continue;
        }
        if (k == APB_KEY_RIGHT) {
            chosen = (uint8_t)(chosen + 1 < COMMANDS ? chosen + 1 : 0);
            continue;
        }
        if (k == APB_KEY_FIRE) {
            k = (uint8_t)command_keys[chosen];
        }
        for (i = 0; i < COMMANDS; ++i) {
            if (k == (uint8_t)command_keys[i]) chosen = i;
        }
        draw_bar(chosen);
        hal_scene_sound(APB_SFX_SELECT);
        switch (k) {
        case 'M':
            choose_square(who);
            break;
        case 'A':
            t = choose_target(who);
            if (t != APB_NOBODY) {
                act(out, APB_ACT_ATTACK, t);
                return;
            }
            break;
        case 'G':
            act(out, APB_ACT_GUARD, 0);
            return;
        case 'W':
            if (to_x != here_x || to_y != here_y || waited) {
                hal_scene_sound(APB_SFX_NO);
                prompt("You can only wait before you move.", C_RED);
                hal_scene_log("[You can only wait before you move.]");
                hal_scene_show(25);
                break;
            }
            act(out, APB_ACT_WAIT, 0);
            return;
        case 'F':
            act(out, APB_ACT_FLEE, 0);
            return;
        case 'Q':
            on_quick = 1;
            act(out, APB_ACT_DONE, 0);
            apb_battle_quick(who, out);
            return;
        case 'D':
            act(out, APB_ACT_DONE, 0);
            return;
        }
    }
}

void hal_battle_end(uint8_t result)
{
    uint8_t r;

    cursor_off();
    clear_bar();
    say(apb_view_ending(result));
    prompt("Press a key.", C_YELLOW);
    hal_scene_log("[Press a key.]");
    key();
    for (r = 0; r < 25; ++r) put_text(0, r, "", C_WHITE, 40);
    hal_scene_close();
}
