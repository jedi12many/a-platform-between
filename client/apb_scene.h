/*
 * The battle screen with graphics (docs/c64-hardware.md, E9): what a front end that has
 * graphics supplies, for client/tactics.c to draw a fight with. A front end without them
 * (the terminal) links client/battle_view.c instead, the text screen.
 *
 * The screen is the C64's in multicolour character mode: 40 x 25 characters from the
 * set in the battle graphics (tools/battlegfx.py, the .bgfx file), each with a colour
 * (0-7 hires, 8-15 multicolour), and sprites over them, 24 x 21. Every front end shows it
 * the same, pixel for pixel; tools/vic.py is the reference.
 */
#ifndef APB_SCENE_H
#define APB_SCENE_H

#include "apb.h"

#define APB_SCENE_TABLES  512   /* the graphics file's tables (tools/battlegfx.py)  */
#define APB_SCENE_SPRITES 24    /* sprites the screen uses; 0 is drawn on top      */

/* Keys the battle screen asks for. Anything else comes as its ASCII code, letters as
 * capitals. Digits 1-9 are directions too, as on a numeric keypad (client/tactics.c). */
enum {
    APB_KEY_UP = 1, APB_KEY_DOWN, APB_KEY_LEFT, APB_KEY_RIGHT,
    APB_KEY_UP_LEFT, APB_KEY_UP_RIGHT, APB_KEY_DOWN_LEFT, APB_KEY_DOWN_RIGHT,
    APB_KEY_FIRE,                 /* Return, space, the joystick's button            */
    APB_KEY_BACK                  /* Delete, Escape                                   */
};

/* How a sprite is drawn. */
enum { APB_SPR_OFF = 0, APB_SPR_HIRES, APB_SPR_MULTI };

/* Sound effects: client/sfx.c says how each sounds, as the SID plays it. */
enum {
    APB_SFX_STEP = 0, APB_SFX_SWING, APB_SFX_SHOT, APB_SFX_HIT, APB_SFX_MISS,
    APB_SFX_DOWN, APB_SFX_SELECT, APB_SFX_NO, APB_SFX_COUNT
};
extern const uint8_t apb_sfx[APB_SFX_COUNT][6];

/* Into the battle screen, cleared, with its graphics loaded: returns their tables (the
 * file's first APB_SCENE_TABLES bytes), or 0 if they can't be had. */
const uint8_t *hal_scene_open(void);
/* Back to the story's screen (the picture comes back when the story shows one). */
void hal_scene_close(void);
void hal_scene_colours(uint8_t border, uint8_t background, uint8_t mc1, uint8_t mc2,
                       uint8_t sprite_mc1, uint8_t sprite_mc2);
void hal_scene_put(uint8_t col, uint8_t row, uint8_t ch, uint8_t colour);
/* Sprite n at x, y (the screen's pixels, its top left corner; off the screen is fine),
 * with shape `shape` (from the graphics) and its own colour. */
void hal_scene_sprite(uint8_t n, int16_t x, int16_t y, uint8_t shape, uint8_t colour,
                      uint8_t mode);
/* Show it all, then wait `frames` fiftieths of a second (0: just show). */
void hal_scene_show(uint8_t frames);
/* Show it all and wait for a key: APB_KEY_*, or ASCII. */
uint8_t hal_scene_key(void);
void hal_scene_sound(uint8_t effect);
/* A line for the record (the transcripts tests read): shown nowhere. ASCII. */
void hal_scene_log(const char *ascii);

#endif
