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

/* The game's letters, as the C64 has them (tools/c64font.py): font8x8 (bit 0 the left)
 * with each stroke a pixel wider to the right, unless that would close a one-pixel gap. */
static unsigned bold(unsigned row)
{
    return (row | ((row << 1) & ~row & ~(row >> 1))) & 0xFFu;
}

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
        bits = bold(glyph[y / 2]);
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

/* The battle screen: the C64's multicolour character mode and its sprites, as the VIC-II
 * draws them (tools/vic.py), each C64 pixel two by two. */
static void plot(uint8_t *px, int x, int y, uint8_t c)
{
    if (x >= 0 && x < 320 && y >= 0 && y < 200) px[y * 320 + x] = c;
}

static void render_scene(uint32_t *fb)
{
    static uint8_t px[320 * 200];
    int row, col, y, x, n;
    uint8_t ch, colour, b, v, c;
    const uint8_t *glyph;
    const uint8_t *data;
    const modern_sprite *s;
    uint32_t bits;

    for (row = 0; row < SCR_ROWS; ++row) {
        for (col = 0; col < SCR_COLS; ++col) {
            ch = scn_char[row][col];
            colour = scn_colour[row][col];
            glyph = scn_charset + ch * 8;
            for (y = 0; y < 8; ++y) {
                b = glyph[y];
                for (x = 0; x < 8; ++x) {
                    if (colour & 8) {
                        v = (uint8_t)((b >> (6 - 2 * (x / 2))) & 3);
                        c = v == 0 ? scn_regs[1] : v == 1 ? scn_regs[2] : v == 2 ? scn_regs[3]
                                                                         : (uint8_t)(colour & 7);
                    } else {
                        c = (b >> (7 - x)) & 1 ? (uint8_t)(colour & 7) : scn_regs[1];
                    }
                    px[(row * 8 + y) * 320 + col * 8 + x] = c;
                }
            }
        }
    }
    /* Sprite 0 is on top: draw the last first. */
    for (n = SCN_SPRITES - 1; n >= 0; --n) {
        s = &scn_sprite[n];
        if (!s->mode) continue;
        data = scn_shapes + s->shape * 64;
        for (y = 0; y < 21; ++y) {
            bits = ((uint32_t)data[y * 3] << 16) | ((uint32_t)data[y * 3 + 1] << 8) | data[y * 3 + 2];
            if (s->mode == 2) {
                for (x = 0; x < 12; ++x) {
                    v = (uint8_t)((bits >> (22 - 2 * x)) & 3);
                    if (!v) continue;
                    c = v == 1 ? scn_regs[4] : v == 2 ? s->colour : scn_regs[5];
                    plot(px, s->x + 2 * x, s->y + y, c);
                    plot(px, s->x + 2 * x + 1, s->y + y, c);
                }
            } else {
                for (x = 0; x < 24; ++x) {
                    if ((bits >> (23 - x)) & 1) plot(px, s->x + x, s->y + y, s->colour);
                }
            }
        }
    }
    for (y = 0; y < SCR_H; ++y) {
        for (x = 0; x < SCR_W; ++x) fb[y * SCR_W + x] = modern_palette[px[(y / 2) * 320 + x / 2] & 15];
    }
}

void modern_render(uint32_t *fb)
{
    int row, col;
    int picture = scr_picture_shown && scr_picture.pixels;

    if (scn_active) {
        render_scene(fb);
        return;
    }

    for (row = 0; row < SCR_ROWS; ++row) {
        if (picture && row >= PIC_TOP && row < PIC_TOP + PIC_ROWS) continue;
        for (col = 0; col < SCR_COLS; ++col) {
            draw_cell(fb, row, col, scr_char[row][col], modern_palette[scr_ink[row][col] & 15],
                      scr_cursor_on && row == scr_cursor_row && col == scr_cursor_col);
        }
    }
    if (picture) draw_picture(fb);
}
