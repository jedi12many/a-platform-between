/*
 * The battle screen with graphics on the desktop and in the browser (client/apb_scene.h):
 * the C64's multicolour character screen and sprites, kept here and drawn by render.c the
 * way the C64's VIC-II draws them (tools/vic.py is the reference), from the battle
 * graphics file BGFX (tools/battlegfx.py) in the Departure's directory.
 */
#include <string.h>

#include "apb_hal.h"
#include "apb_scene.h"
#include "modern.h"

uint8_t scn_active;
uint8_t scn_char[SCR_ROWS][SCR_COLS];
uint8_t scn_colour[SCR_ROWS][SCR_COLS];
uint8_t scn_regs[6];
modern_sprite scn_sprite[SCN_SPRITES];
const uint8_t *scn_charset;
const uint8_t *scn_shapes;

static uint8_t gfx[8192];
static uint16_t gfx_len;

const uint8_t *hal_scene_open(void)
{
    if (!gfx_len && (hal_load("BGFX", gfx, sizeof(gfx), &gfx_len) != HAL_OK || gfx_len < 2560
                     || gfx[0] != 'B' || gfx[1] != 'G')) {
        gfx_len = 0;
        return 0;
    }
    modern_end_row();
    scn_charset = gfx + APB_SCENE_TABLES;
    scn_shapes = gfx + APB_SCENE_TABLES + 2048;
    memset(scn_char, ' ', sizeof(scn_char));
    memset(scn_colour, 1, sizeof(scn_colour));
    memset(scn_sprite, 0, sizeof(scn_sprite));
    scn_active = 1;
    return gfx;
}

void hal_scene_close(void)
{
    scn_active = 0;
    plat_show();
}

void hal_scene_colours(uint8_t border, uint8_t background, uint8_t mc1, uint8_t mc2,
                       uint8_t sprite_mc1, uint8_t sprite_mc2)
{
    scn_regs[0] = border;
    scn_regs[1] = background;
    scn_regs[2] = mc1;
    scn_regs[3] = mc2;
    scn_regs[4] = sprite_mc1;
    scn_regs[5] = sprite_mc2;
}

void hal_scene_put(uint8_t col, uint8_t row, uint8_t ch, uint8_t colour)
{
    if (col < SCR_COLS && row < SCR_ROWS) {
        scn_char[row][col] = ch;
        scn_colour[row][col] = colour;
    }
}

void hal_scene_sprite(uint8_t n, int16_t x, int16_t y, uint8_t shape, uint8_t colour,
                      uint8_t mode)
{
    if (n >= SCN_SPRITES) return;
    scn_sprite[n].x = x;
    scn_sprite[n].y = y;
    scn_sprite[n].shape = shape;
    scn_sprite[n].colour = colour;
    scn_sprite[n].mode = mode;
}

void hal_scene_show(uint8_t frames)
{
    if (modern_scripted()) return;          /* tests don't wait for animations */
    if (frames) {
        plat_wait(frames * 20u);
    } else {
        plat_show();
    }
}

uint8_t hal_scene_key(void)
{
    uint16_t k;

    for (;;) {
        k = modern_key();
        if (k & KEY_ARROW) return (uint8_t)(k & 0xFF);
        if (k == KEY_RETURN) return APB_KEY_FIRE;
        if (k == KEY_DELETE || k == KEY_ESCAPE) return APB_KEY_BACK;
        if (k < 0x80) return (uint8_t)k;
    }
}

void hal_scene_sound(uint8_t effect)
{
    (void)effect;                           /* E9c */
}

void hal_scene_log(const char *ascii)
{
    modern_log(ascii);
}
