/*
 * The modern front end (milestone E6): the same game on a desktop (SDL2, fe/modern/sdl.c)
 * and in a browser (WebAssembly, fe/modern/web.c), from one screen.
 *
 * The screen is the C64's (docs/c64.md): 40 x 25 characters, a status bar on row 0, the
 * picture on rows 1-12, and a text window under it. fe/modern/screen.c implements the
 * whole HAL on that screen; fe/modern/render.c draws it, 640 x 400 pixels, with the
 * pictures in full colour. A platform supplies only the few functions at the bottom of
 * this file: a window, the keyboard and mouse, and where saves live.
 *
 * Unlike core/ and vm/, this code never runs on a 6502: it's plain C99.
 */
#ifndef APB_MODERN_H
#define APB_MODERN_H

#include <stdint.h>
#include <stdio.h>

#define SCR_COLS 40
#define SCR_ROWS 25
#define SCR_W 640               /* the framebuffer: 16 x 16 pixels a character */
#define SCR_H 400

#define PIC_TOP 1               /* the picture's rows on the screen */
#define PIC_ROWS 12

/* What the screen holds, for render.c: a character (ASCII, 0x80 set for reverse) and a
 * colour (0..15, the C64's palette) in each cell, and the picture. */
extern uint8_t scr_char[SCR_ROWS][SCR_COLS];
extern uint8_t scr_ink[SCR_ROWS][SCR_COLS];
extern uint8_t scr_cursor_row, scr_cursor_col, scr_cursor_on;

typedef struct {
    uint16_t w, h;
    uint8_t colours;            /* palette entries */
    uint8_t palette[256][3];
    uint8_t *pixels;            /* w * h palette indices, row by row */
} modern_picture;

extern modern_picture scr_picture;
extern uint8_t scr_picture_shown;      /* drawn on rows 1-12 */

/* The battle screen with graphics (client/apb_scene.h, fe/modern/scene.c): while a fight
 * is on, render.c draws this instead, the C64's multicolour character screen and its
 * sprites, from the battle graphics (tools/battlegfx.py), twice the C64's size. */
#define SCN_SPRITES 24
typedef struct {
    int16_t x, y;
    uint8_t shape, colour, mode;    /* mode: APB_SPR_OFF, _HIRES, _MULTI */
} modern_sprite;

extern uint8_t scn_active;
extern uint8_t scn_char[SCR_ROWS][SCR_COLS];
extern uint8_t scn_colour[SCR_ROWS][SCR_COLS];
extern uint8_t scn_regs[6];         /* border, background, mc1, mc2, sprite mc1, mc2 */
extern modern_sprite scn_sprite[SCN_SPRITES];
extern const uint8_t *scn_charset;  /* 256 x 8 bytes */
extern const uint8_t *scn_shapes;   /* 64 bytes each */

/* render.c: the screen into `fb`, SCR_W x SCR_H pixels of 0x00RRGGBB. */
void modern_render(uint32_t *fb);
/* The C64's sixteen colours, 0x00RRGGBB. */
extern const uint32_t modern_palette[16];

/* screen.c: playing a Departure. `dir` holds its DEPOT, CARnn and picNN.apic files;
 * saves go to `save_dir`. With `choices`, keys come from that file (lines as in
 * tests/term/fare-edge.choices) and the screen's rows are written to `transcript` as they
 * scroll, the way tests/c64/run_c64.py records the C64. */
void modern_setup(const char *dir, const char *save_dir, FILE *choices, FILE *transcript);
/* Called each time the game waits for the player, with a choices file too: for
 * pictures of the screen (apb-modern --shots). */
extern void (*modern_on_wait)(void);
/* The trip: the start menu, boarding, the story and the receipt. Returns at the end. */
void modern_play(uint16_t seed);

/* ------------------------------------------------- what a platform supplies */

#define KEY_RETURN 13
#define KEY_DELETE 8
#define KEY_CLICK  0x100        /* | row: the player clicked a row of the screen */
#define KEY_ARROW  0x200        /* | APB_KEY_UP..APB_KEY_RIGHT: an arrow key */
#define KEY_ESCAPE 27

/* Show the screen (call modern_render), then wait for a key or a click and return it:
 * ASCII, KEY_RETURN, KEY_DELETE or KEY_CLICK | row. */
uint16_t plat_key(void);
/* Show the screen without waiting. */
void plat_show(void);
/* A save was written: make it last (the browser copies it to IndexedDB). */
void plat_saved(void);
/* Show the screen and wait `ms` milliseconds, for animation. */
void plat_wait(unsigned ms);

/* screen.c, for scene.c: a key as the story's screen takes them (from the choices file
 * in tests), with no cursor; and a line into the transcript, if there is one. */
uint16_t modern_key(void);
void modern_log(const char *line);
void modern_end_row(void);           /* the story's last row into the transcript */
int modern_scripted(void);          /* keys come from a choices file */

#endif
