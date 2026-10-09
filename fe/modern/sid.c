/*
 * The SID on the desktop and in the browser: its three voices from its 25 registers, as
 * the music player (client/music.c) leaves them each fiftieth of a second, made into
 * samples, SFX_RATE a second. The C64 has the chip; this is what the music needs of it:
 * its oscillators (triangle, sawtooth, pulse with its width, noise, the four ANDed when
 * more than one is on, ring modulation and hard sync), its envelopes (attack, decay,
 * sustain and release, at the chip's rates) and its volume. Not its filter, which the
 * player leaves off.
 */
#include <string.h>

#include "modern.h"

#define CLOCK 985248u           /* a PAL C64's, cycles a second */
#define FULL  (255u << 16)      /* the envelope, with 16 bits below the SID's 8 */

/* The SID's envelope times, in milliseconds: attack (0-15), and decay or release. */
static const unsigned attack_ms[16] = {
    2, 8, 16, 24, 38, 56, 68, 80, 100, 250, 500, 800, 1000, 3000, 5000, 8000
};
static const unsigned fall_ms[16] = {
    6, 24, 48, 72, 114, 168, 204, 240, 300, 750, 1500, 2400, 3000, 9000, 15000, 24000
};

/* How much the envelope moves a sample, to cross its whole range in `ms`. */
static uint32_t per_sample(unsigned ms)
{
    uint32_t samples = (uint32_t)((uint64_t)ms * SFX_RATE / 1000u);

    return FULL / (samples ? samples : 1u);
}

void sid_reset(modern_sid *s)
{
    int v;

    memset(s, 0, sizeof(*s));
    for (v = 0; v < 3; ++v) s->noise[v] = 0x7FFFF8u;
}

void sid_registers(modern_sid *s, const uint8_t *regs)
{
    int v;
    uint8_t was;

    for (v = 0; v < 3; ++v) {
        was = s->regs[7 * v + 4];
        if ((regs[7 * v + 4] & 1) && !(was & 1)) s->stage[v] = 0;      /* gate on: attack */
        if (!(regs[7 * v + 4] & 1)) s->stage[v] = 2;                    /* off: release   */
    }
    memcpy(s->regs, regs, sizeof(s->regs));
}

/* One voice's waveform, 0-4095. */
static unsigned wave(const modern_sid *s, int v)
{
    uint8_t control = s->regs[7 * v + 4];
    uint32_t acc = s->acc[v];
    uint32_t noise = s->noise[v];
    unsigned pw = (unsigned)(s->regs[7 * v + 2] | (s->regs[7 * v + 3] & 15) << 8);
    unsigned out = 0xFFFu;
    uint32_t msb;

    if (!(control & 0xF0)) return 0x800u;
    if (control & 0x10) {
        msb = acc & 0x800000u;
        if (control & 0x04) msb ^= s->acc[(v + 2) % 3] & 0x800000u;    /* ring: voice before */
        out &= (unsigned)(((msb ? ~acc : acc) >> 11) & 0xFFEu);
    }
    if (control & 0x20) out &= (unsigned)(acc >> 12);
    if (control & 0x40) out &= (acc >> 12) >= pw ? 0xFFFu : 0u;
    if (control & 0x80) {
        out &= (unsigned)((((noise >> 20) & 1) << 11) | (((noise >> 18) & 1) << 10)
                          | (((noise >> 14) & 1) << 9) | (((noise >> 11) & 1) << 8)
                          | (((noise >> 9) & 1) << 7) | (((noise >> 5) & 1) << 6)
                          | (((noise >> 2) & 1) << 5) | ((noise & 1) << 4));
    }
    return out;
}

/* One voice's envelope, a sample on. */
static void envelope(modern_sid *s, int v)
{
    const uint8_t *r = s->regs + 7 * v;
    uint32_t sustain = (uint32_t)(r[6] >> 4) * 17u << 16;
    uint32_t step;

    if (s->stage[v] == 0) {                                 /* attack */
        step = per_sample(attack_ms[r[5] >> 4]);
        s->level[v] = s->level[v] + step >= FULL ? FULL : s->level[v] + step;
        if (s->level[v] == FULL) s->stage[v] = 1;
    } else if (s->stage[v] == 1) {                          /* decay, then sustain */
        step = per_sample(fall_ms[r[5] & 15]);
        if (s->level[v] > sustain) {
            s->level[v] = s->level[v] - sustain > step ? s->level[v] - step : sustain;
        }
    } else {                                                /* release */
        step = per_sample(fall_ms[r[6] & 15]);
        s->level[v] = s->level[v] > step ? s->level[v] - step : 0;
    }
}

void sid_render(modern_sid *s, int16_t *out, int n)
{
    int i;
    int v;
    long mix;
    uint32_t step[3];
    uint32_t before;
    int rose[3];
    unsigned volume = s->regs[24] & 15u;

    for (v = 0; v < 3; ++v) {
        step[v] = (uint32_t)((uint64_t)(s->regs[7 * v] | s->regs[7 * v + 1] << 8) * CLOCK
                             / SFX_RATE);
    }
    for (i = 0; i < n; ++i) {
        mix = 0;
        for (v = 0; v < 3; ++v) {
            before = s->acc[v];
            if (s->regs[7 * v + 4] & 0x08) {                /* the test bit holds it at 0 */
                s->acc[v] = 0;
                s->noise[v] = 0x7FFFF8u;
            } else {
                s->acc[v] = (s->acc[v] + step[v]) & 0xFFFFFFu;
            }
            rose[v] = !(before & 0x800000u) && (s->acc[v] & 0x800000u);
            if ((before ^ s->acc[v]) & 0x080000u && s->acc[v] & 0x080000u) {
                /* Bit 19 rose: the noise register takes a step. */
                s->noise[v] = ((s->noise[v] << 1)
                               | (((s->noise[v] >> 22) ^ (s->noise[v] >> 17)) & 1u)) & 0x7FFFFFu;
            }
        }
        for (v = 0; v < 3; ++v) {
            /* Hard sync: the voice before it starting a cycle starts this one's. */
            if ((s->regs[7 * v + 4] & 0x02) && rose[(v + 2) % 3]) s->acc[v] = 0;
            envelope(s, v);
            mix += ((long)wave(s, v) - 2048) * (long)(s->level[v] >> 16) / 255;
        }
        out[i] = (int16_t)(mix * (long)volume / 15 * 5);
    }
}
