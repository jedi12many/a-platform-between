/*
 * The battle screen with graphics (docs/frames.md, E12): what a front end that has
 * graphics supplies, for client/tactics.c to draw a fight with. A front end without them
 * (the terminal) links client/battle_view.c instead, the text screen.
 *
 * The screen is framed (docs/frames.md): the battle map is the view at the top, rows 0-15,
 * the C64's multicolour character mode, 40 x 16 characters from the set in the battle
 * graphics (tools/battlegfx.py, the .bgfx file), each with a colour (0-7 hires, 8-15
 * multicolour), and sprites over them, 24 x 21, kept to the view. Every front end shows it
 * the same, pixel for pixel; tools/vic.py is the reference. Under it stay the story's
 * frames, the same as in the story: the story log, the party, the dice log and the
 * command row, which tactics.c writes through the hal_frame_ calls.
 */
#ifndef APB_SCENE_H
#define APB_SCENE_H

#include "apb.h"

#define APB_SCENE_TABLES  640   /* the graphics file's tables (tools/battlegfx.py)  */
#define APB_SCENE_ROWS    16    /* the view: the map's rows of characters           */
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
/* The fight's music (docs/music.md): the Departure's tune `battle` as it starts, then
 * `won` or `lost`; after a flight, or back on the story's screen, the story's tune again.
 * Front ends without music ignore it. */
enum { APB_SCENE_FIGHT = 0, APB_SCENE_WON, APB_SCENE_LOST, APB_SCENE_FLED };
void hal_scene_music(uint8_t moment);
/* A line for the record (the transcripts tests read): shown nowhere. ASCII. */
void hal_scene_log(const char *ascii);

/* The frames under the view (docs/frames.md), the story's and a fight's alike. The
 * front end keeps them; all text is ASCII. */
#define APB_FRAME_LOG_COLS  25  /* the story log's width                            */
#define APB_FRAME_SIDE_COLS 14  /* the party's and the dice log's                   */
#define APB_FRAME_NAME      7   /* a name in the party frame                        */
/* A sentence into the story log, word-wrapped, with no "-- more --": a fight's. */
void hal_frame_say(const char *ascii);
/* A roll into the dice log, in two short lines (APB_FRAME_SIDE_COLS); `record` is the
 * whole of it, for the transcript. */
void hal_frame_roll(const char *top, const char *bottom, const char *record);
/* Traveler `slot` (0-3) in the party frame: name, health and its most, and how they are
 * shown. A name of "" empties the slot. */
enum { APB_MEMBER_READY = 0, APB_MEMBER_TURN, APB_MEMBER_DOWN };
void hal_frame_member(uint8_t slot, const char *name, uint8_t health, uint8_t max,
                      uint8_t state);
/* The command row: `ascii` in `colour`, characters from..to-1 of it in white (the chosen
 * command); the rest of the row blank. */
void hal_frame_command(const char *ascii, uint8_t colour, uint8_t from, uint8_t to);

#endif
