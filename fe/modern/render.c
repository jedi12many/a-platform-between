/*
 * Drawing the modern front end's screen (fe/modern/modern.h): 40 x 25 characters of
 * 16 x 16 pixels (the 8 x 8 font, doubled), and the picture on rows 1-12, stretched to
 * the C64's shape (a 160 x 96 picture's pixels come out four wide and two high, as on
 * the C64), in its own full colours.
 */
#include "font8x8.h"
#include "modern.h"

/* Pepto's measured C64 palette, as tools/c64pic.py uses it. */
const uint32_t modern_palette[16] = {
    0x000000, 0xFFFFFF, 0x68372B, 0x70A4B2, 0x6F3D86, 0x588D43, 0x352879, 0xB8C76F,
    0x6F4F25, 0x433900, 0x9A6759, 0x444444, 0x6C6C6C, 0x9AD284, 0x6C5EB5, 0x959595
};

#define BACKGROUND 0x000000u

static void draw_cell(uint32_t *fb, int row, int col, uint8_t ch, uint32_t ink, int cursor)
{
    const unsigned char *glyph;
    int reverse = (ch & 0x80) != 0;
    int y, x;
    uint32_t fg = reverse ? BACKGROUND : ink;
    uint32_t bg = reverse ? ink : BACKGROUND;
    uint32_t *p;
    unsigned bits;

    ch &= 0x7F;
    if (ch < 0x20 || ch > 0x7E) ch = ' ';
    glyph = font8x8[ch - 0x20];
    if (cursor) {
        fg = BACKGROUND;
        bg = ink;
    }
    for (y = 0; y < 16; ++y) {
        bits = glyph[y / 2];
        p = fb + (row * 16 + y) * SCR_W + col * 16;
        for (x = 0; x < 16; ++x) p[x] = (bits >> (x / 2)) & 1 ? fg : bg;
    }
}

static void draw_picture(uint32_t *fb)
{
    const modern_picture *pic = &scr_picture;
    int area_h = PIC_ROWS * 16;
    int y, x;
    const uint8_t *src;
    const uint8_t *rgb;
    uint32_t *p;

    for (y = 0; y < area_h; ++y) {
        src = pic->pixels + (size_t)(y * pic->h / area_h) * pic->w;
        p = fb + (PIC_TOP * 16 + y) * SCR_W;
        for (x = 0; x < SCR_W; ++x) {
            rgb = pic->palette[src[x * pic->w / SCR_W]];
            p[x] = ((uint32_t)rgb[0] << 16) | ((uint32_t)rgb[1] << 8) | rgb[2];
        }
    }
}

void modern_render(uint32_t *fb)
{
    int row, col;
    int picture = scr_picture_shown && scr_picture.pixels;

    for (row = 0; row < SCR_ROWS; ++row) {
        if (picture && row >= PIC_TOP && row < PIC_TOP + PIC_ROWS) continue;
        for (col = 0; col < SCR_COLS; ++col) {
            draw_cell(fb, row, col, scr_char[row][col], modern_palette[scr_ink[row][col] & 15],
                      scr_cursor_on && row == scr_cursor_row && col == scr_cursor_col);
        }
    }
    if (picture) draw_picture(fb);
}
