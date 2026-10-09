/*
 * The battle screen on the C64 (client/apb_scene.h, docs/c64.md): the VIC-II's
 * multicolour character mode in bank 3 (the characters at $E000, the screen at $E800, the
 * sprite shapes at $EC00, all in the RAM under the KERNAL, loaded from the disk files
 * btab, bchr and bspr, tools/battlegfx.py), more sprites than the VIC's eight (planned
 * here, put up by the raster interrupt in fe/c64/sprites.s), the keyboard and a joystick in
 * port 2, and the sound effects (the music player plays them, fe/c64/tune.s).
 *
 * It's in the BATTLE overlay with the rules and client/tactics.c, so it's here only
 * during a fight. The story's text screen at $0400 is left as it was, and fe/c64/c64.c
 * puts its colours and picture back after (c64_scene).
 */
#include <cbm.h>
#include <string.h>

#include "apb_scene.h"

#define SCREEN     ((uint8_t *)0xE800)
#define COLOURS    ((uint8_t *)0xD800)
#define BORDER     (*(volatile uint8_t *)0xD020)
#define BACKGROUND (*(volatile uint8_t *)0xD021)
#define CHAR_MC1   (*(volatile uint8_t *)0xD022)
#define CHAR_MC2   (*(volatile uint8_t *)0xD023)
#define SPRITE_MC1 (*(volatile uint8_t *)0xD025)
#define SPRITE_MC2 (*(volatile uint8_t *)0xD026)
#define JOYSTICK   (*(volatile uint8_t *)0xDC00)

#define SHAPES_AT  176          /* sprite pointer of the shapes at $EC00, in bank 3   */
#define SPRITES    APB_SCENE_SPRITES
#define TOP        50           /* the screen's top and left, in the VIC's sprite     */
#define LEFT       24           /* coordinates                                        */
#define LAST_LINE  250          /* a sprite starting here or lower isn't seen         */
#define TALL       21
#define LEAD       3            /* lines between one sprite's end and the next's start
                                   on the same VIC sprite: time to set it up         */
#define AT_ONCE    4            /* VIC sprites set up on one line, at most            */
#define EVENTS     16

/* fe/c64/c64.c */
void c64_scene(uint8_t on);

/* fe/c64/tune.s */
void __fastcall__ tune_effect(uint8_t effect);

/* fe/c64/sprites.s */
typedef struct {
    uint8_t top_x[8], top_y[8], top_ptr[8], top_col[8];
    uint8_t top_msb, top_mc, top_en, ev_n;
    uint8_t ev_line[EVENTS], ev_slot[EVENTS], ev_s2[EVENTS], ev_x[EVENTS], ev_y[EVENTS];
    uint8_t ev_ptr[EVENTS], ev_col[EVENTS], ev_msb[EVENTS], ev_mc[EVENTS];
} scene_plan;

extern scene_plan scene_next;            /* tests/c64/run_c64.py draws the screen from it */
extern volatile uint8_t scene_pending;
void scene_start(void);
void scene_stop(void);
void __fastcall__ scene_wait(uint8_t frames);

/* The sprites as tactics.c asked for them. */
static int16_t scene_x[SPRITES];
static int16_t scene_y[SPRITES];
static uint8_t scene_shape[SPRITES];
static uint8_t scene_colour[SPRITES];
static uint8_t scene_mode[SPRITES];

static uint8_t tables[APB_SCENE_TABLES];

/* ------------------------------------------------------------------ opening */

const uint8_t *hal_scene_open(void)
{
    c64_scene(1);
    BORDER = 12;
    if (!cbm_load("btab", 8, tables) || !cbm_load("bchr", 8, 0) || !cbm_load("bspr", 8, 0)
        || tables[0] != 0x42 || tables[1] != 0x47) {
        BORDER = 0;
        c64_scene(0);
        return 0;
    }
    memset(SCREEN, 0x20, 1000);
    memset(COLOURS, 1, 1000);
    memset(scene_mode, APB_SPR_OFF, sizeof(scene_mode));
    scene_start();
    return tables;
}

void hal_scene_close(void)
{
    scene_stop();
    c64_scene(0);
}

void hal_scene_colours(uint8_t border, uint8_t background, uint8_t mc1, uint8_t mc2,
                       uint8_t sprite_mc1, uint8_t sprite_mc2)
{
    BORDER = border;
    BACKGROUND = background;
    CHAR_MC1 = mc1;
    CHAR_MC2 = mc2;
    SPRITE_MC1 = sprite_mc1;
    SPRITE_MC2 = sprite_mc2;
}

void hal_scene_put(uint8_t col, uint8_t row, uint8_t ch, uint8_t colour)
{
    uint16_t at;

    if (col >= 40 || row >= 25) return;
    at = (uint16_t)(row * 40 + col);
    SCREEN[at] = ch;
    COLOURS[at] = colour;
}

void hal_scene_sprite(uint8_t n, int16_t x, int16_t y, uint8_t shape, uint8_t colour,
                      uint8_t mode)
{
    if (n >= SPRITES) return;
    scene_x[n] = x;
    scene_y[n] = y;
    scene_shape[n] = shape;
    scene_colour[n] = colour;
    scene_mode[n] = mode;
}

/* ------------------------------------------------------------------ the plan */

/* Twenty-four sprites on eight: sorted down the screen, each takes a VIC sprite that's
 * free (none yet, or one whose last sprite has finished, LEAD lines before this one
 * starts). The cursor and effects go first, then bodies, then outlines; one that can't
 * be fitted isn't shown this frame (an outline before a body: a figure without its
 * outline still reads). */
static uint8_t order[SPRITES];
static uint8_t line_of[SPRITES];          /* its top, in raster lines           */
static uint8_t rank[SPRITES];
static uint8_t free_at[8];                /* the line each VIC sprite is free from */
static uint8_t used;                      /* VIC sprites with something on them  */
/* The events as they're found, before they're put in the order of their lines. */
static uint8_t r_line[EVENTS], r_slot[EVENTS], r_x[EVENTS], r_y[EVENTS], r_ptr[EVENTS];
static uint8_t r_col[EVENTS], r_bits[EVENTS];      /* 1: x high bit; 2: multicolour */

static void plan(void)
{
    scene_plan *p = &scene_next;
    uint8_t n = 0;
    uint8_t i;
    uint8_t j;
    uint8_t k;
    uint8_t s;
    uint8_t ev;
    uint8_t bit;
    uint8_t msb;
    uint8_t mc;
    int16_t x;
    int16_t y;

    scene_wait(0);                       /* the last plan has been taken */
    for (i = 0; i < SPRITES; ++i) {
        if (!scene_mode[i]) continue;
        y = (int16_t)(scene_y[i] + TOP);
        x = (int16_t)(scene_x[i] + LEFT);
        if (y <= TOP - TALL || y >= LAST_LINE || x <= 0 || x >= 320 + LEFT) continue;
        line_of[i] = (uint8_t)y;
        rank[i] = (uint8_t)(i < 3 ? 0 : (i & 1) ? 2 : 1);      /* 3, 5, ...: outlines */
        /* Into place, down the screen. */
        for (j = n; j && (line_of[order[j - 1]] > line_of[i]
                          || (line_of[order[j - 1]] == line_of[i] && rank[order[j - 1]] > rank[i]));
             --j) {
            order[j] = order[j - 1];
        }
        order[j] = i;
        ++n;
    }
    used = 0;
    ev = 0;
    p->top_msb = p->top_mc = 0;
    for (k = 0; k < n; ++k) {
        i = order[k];
        x = (int16_t)(scene_x[i] + LEFT);
        if (used != 0xFF) {
            /* A VIC sprite nothing's used yet this frame: set at the frame's start. */
            for (s = 0, bit = 1; used & bit; ++s, bit = (uint8_t)(bit << 1)) {}
            used |= bit;
            p->top_x[s] = (uint8_t)x;
            p->top_y[s] = line_of[i];
            p->top_ptr[s] = (uint8_t)(SHAPES_AT + scene_shape[i]);
            p->top_col[s] = scene_colour[i];
            if (x > 255) p->top_msb |= bit;
            if (scene_mode[i] == APB_SPR_MULTI) p->top_mc |= bit;
        } else {
            /* The one that's free soonest, if it's free in time, and not too many are
             * being set up on that line already. */
            s = 0;
            for (j = 1; j < 8; ++j) {
                if (free_at[j] < free_at[s]) s = j;
            }
            if (ev == EVENTS || free_at[s] + LEAD > line_of[i]) continue;
            for (j = 0, bit = 0; j < ev; ++j) {
                if (r_line[j] == free_at[s]) ++bit;
            }
            if (bit >= AT_ONCE) continue;
            /* Into place, in the order the lines come. */
            for (j = ev; j && r_line[j - 1] > free_at[s]; --j) {
                r_line[j] = r_line[j - 1];
                r_slot[j] = r_slot[j - 1];
                r_x[j] = r_x[j - 1];
                r_y[j] = r_y[j - 1];
                r_ptr[j] = r_ptr[j - 1];
                r_col[j] = r_col[j - 1];
                r_bits[j] = r_bits[j - 1];
            }
            r_line[j] = free_at[s];
            r_slot[j] = s;
            r_x[j] = (uint8_t)x;
            r_y[j] = line_of[i];
            r_ptr[j] = (uint8_t)(SHAPES_AT + scene_shape[i]);
            r_col[j] = scene_colour[i];
            r_bits[j] = (uint8_t)((x > 255 ? 1 : 0) | (scene_mode[i] == APB_SPR_MULTI ? 2 : 0));
            ++ev;
        }
        free_at[s] = (uint8_t)(line_of[i] + TALL);
    }
    p->top_en = used;
    /* Into the plan, with $D010 and $D01C as each event leaves them. */
    msb = p->top_msb;
    mc = p->top_mc;
    for (k = 0; k < ev; ++k) {
        s = r_slot[k];
        bit = (uint8_t)(1 << s);
        msb = (uint8_t)(r_bits[k] & 1 ? msb | bit : msb & ~bit);
        mc = (uint8_t)(r_bits[k] & 2 ? mc | bit : mc & ~bit);
        p->ev_line[k] = r_line[k];
        p->ev_slot[k] = s;
        p->ev_s2[k] = (uint8_t)(s * 2);
        p->ev_x[k] = r_x[k];
        p->ev_y[k] = r_y[k];
        p->ev_ptr[k] = r_ptr[k];
        p->ev_col[k] = r_col[k];
        p->ev_msb[k] = msb;
        p->ev_mc[k] = mc;
    }
    p->ev_n = ev;
    scene_pending = 1;
}

void hal_scene_show(uint8_t frames)
{
    plan();
    scene_wait(frames);
}

/* ------------------------------------------------------------------ keys */

/* The keyboard's PETSCII: the cursor keys, Return, space, DEL, RUN/STOP and the left
 * arrow; letters (unshifted, PETSCII's 65-90, are ASCII's capitals) and digits as they
 * are. The joystick in port 2: its directions, repeating when held, and its button. */
static uint8_t petscii_key(uint8_t k)
{
    switch (k) {
    case 145: return APB_KEY_UP;
    case 17:  return APB_KEY_DOWN;
    case 157: return APB_KEY_LEFT;
    case 29:  return APB_KEY_RIGHT;
    case 13:  return APB_KEY_FIRE;
    case 20:  case 3: case 95: return APB_KEY_BACK;
    }
    if (k >= 193 && k <= 218) return (uint8_t)(k - 128);
    return k;
}

static const uint8_t stick_key[16] = {
    0, APB_KEY_UP, APB_KEY_DOWN, 0, APB_KEY_LEFT, APB_KEY_UP_LEFT, APB_KEY_DOWN_LEFT, 0,
    APB_KEY_RIGHT, APB_KEY_UP_RIGHT, APB_KEY_DOWN_RIGHT, 0, 0, 0, 0, 0
};
static uint8_t stick_was;
static uint8_t stick_wait;

uint8_t hal_scene_key(void)
{
    uint8_t k;
    uint8_t j;

    plan();
    for (;;) {
        scene_wait(1);
        k = cbm_k_getin();
        if (k) return petscii_key(k);
        j = (uint8_t)(~JOYSTICK & 0x1F);
        if (j != stick_was) {
            stick_was = j;
            stick_wait = 15;
            if (j & 0x10) return APB_KEY_FIRE;
            if (stick_key[j]) return stick_key[j];
        } else if (j && !(j & 0x10) && stick_key[j] && !--stick_wait) {
            stick_wait = 5;
            return stick_key[j];
        }
    }
}

/* ------------------------------------------------------------------ sound */

/* On the music's third voice (docs/music.md): the player has client/sfx.c's table. */
void hal_scene_sound(uint8_t effect)
{
    if (effect < APB_SFX_COUNT) tune_effect(effect);
}
