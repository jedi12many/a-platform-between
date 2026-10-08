/*
 * The battle screen's sound effects on the desktop and in the browser: client/sfx.c's
 * table played the way the C64's SID plays it (fe/c64/scene.c), a voice with the SID's
 * waveforms, its envelope and its timings, at 44100 samples a second. The platform plays
 * the samples (plat_sound); a scripted run makes none.
 */
#include <string.h>

#include "apb_scene.h"
#include "modern.h"

#define CLOCK      985248u          /* a PAL C64's, cycles a second */
#define FRAME      (SFX_RATE / 50)  /* the C64 moves the pitch a fiftieth at a time */
#define FULL       (255u << 16)     /* the envelope, with 16 bits below the SID's 8 */

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

/* One sample of the waveform, 0-4095, from the 24-bit phase. */
static unsigned wave(uint8_t control, uint32_t phase, uint32_t noise)
{
    if (control & 0x80) {
        /* The SID's noise: eight bits of its shift register. */
        return (unsigned)((((noise >> 20) & 1) << 11) | (((noise >> 18) & 1) << 10)
                          | (((noise >> 14) & 1) << 9) | (((noise >> 11) & 1) << 8)
                          | (((noise >> 9) & 1) << 7) | (((noise >> 5) & 1) << 6)
                          | (((noise >> 2) & 1) << 5) | ((noise & 1) << 4));
    }
    if (control & 0x40) return (phase >> 12) >= 0x800 ? 0xFFFu : 0u;    /* pulse, half */
    if (control & 0x20) return (unsigned)(phase >> 12);                 /* sawtooth   */
    if (control & 0x10) {                                               /* triangle   */
        return (unsigned)(((phase & 0x800000u ? ~phase : phase) >> 11) & 0xFFEu);
    }
    return 0x800u;
}

int sfx_render(uint8_t effect, int16_t *out, int max)
{
    const uint8_t *e;
    uint32_t phase = 0;
    uint32_t noise = 0x7FFFF8u;
    uint32_t level = 0;
    uint32_t sustain;
    uint32_t up;
    uint32_t down;
    uint32_t release;
    uint32_t step;
    uint8_t pitch;
    uint8_t frames;
    int gate = 1;
    int attacking = 1;
    int n;
    long v;

    if (effect >= APB_SFX_COUNT) return 0;
    e = apb_sfx[effect];
    pitch = e[1];
    frames = e[5];
    up = per_sample(attack_ms[e[3] >> 4]);
    down = per_sample(fall_ms[e[3] & 15]);
    release = per_sample(fall_ms[e[4] & 15]);
    sustain = (uint32_t)(e[4] >> 4) * 17u << 16;
    for (n = 0; n < max; ++n) {
        if (n && n % FRAME == 0 && gate) {
            /* A fiftieth: as the C64's interrupt does, the gate shuts when its time is
             * up, and until then the pitch slides. */
            if (--frames == 0) {
                gate = 0;
            } else {
                pitch = (uint8_t)(pitch + e[2]);
            }
        }
        if (gate) {
            if (attacking) {
                level = level + up >= FULL ? FULL : level + up;
                if (level == FULL) attacking = 0;
            } else if (level > sustain) {
                level = level - sustain > down ? level - down : sustain;
            }
        } else {
            if (level == 0) break;
            level = level > release ? level - release : 0;
        }
        step = (uint32_t)((uint64_t)((uint32_t)pitch << 8) * CLOCK / SFX_RATE);
        if (((phase + step) ^ phase) & 0x080000u) {
            /* Bit 19 rose (or fell): the noise register takes a step. */
            noise = ((noise << 1) | (((noise >> 22) ^ (noise >> 17)) & 1u)) & 0x7FFFFFu;
        }
        phase = (phase + step) & 0xFFFFFFu;
        v = ((long)wave(e[0], phase, noise) - 2048) * (long)(level >> 16) / 255 * 6;
        out[n] = (int16_t)v;
    }
    return n;
}

void hal_scene_sound(uint8_t effect)
{
    static int16_t samples[2 * SFX_RATE];   /* two seconds, longer than any of them */
    int n;

    if (modern_scripted()) return;
    n = sfx_render(effect, samples, 2 * SFX_RATE);
    if (n) plat_sound(samples, n);
}
