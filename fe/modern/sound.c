/*
 * The music and the sound effects on the desktop and in the browser (docs/music.md): the
 * C64's player (client/music.c) a fiftieth of a second at a time, its registers into the
 * SID (sid.c), as the C64's raster interrupt does it (fe/c64/tune.s). The tunes are the
 * Departure's MUSIC file; the battle screen's sound effects are the player's too, on
 * its third voice. The platform's audio pulls the samples (sound_mix), from its own
 * thread on the desktop, so everything that touches the player here holds its lock.
 *
 * Which tune plays when is client/cue.c's. A scripted run (a choices file, for tests)
 * makes no sound, but its transcript says each tune it would start: "[music NAME]".
 */
#include <stdio.h>
#include <string.h>

#include "apb_cue.h"
#include "apb_hal.h"
#include "apb_music.h"
#include "apb_scene.h"
#include "modern.h"

#define FRAME (SFX_RATE / 50)   /* samples a frame */
#define NONE  255

static uint8_t tunes[1536];
static uint16_t tunes_len;
static apb_music music;
static modern_sid sid;
static int frame_left;          /* samples until the player's next frame */
static int started;

void sound_setup(void)
{
    if (hal_load("MUSIC", tunes, sizeof(tunes), &tunes_len) != HAL_OK) tunes_len = 0;
    apb_music_init(&music, tunes, tunes_len);
    sid_reset(&sid);
    frame_left = 0;
}

void sound_mix(int16_t *out, int n)
{
    int k;

    while (n > 0) {
        if (frame_left == 0) {
            apb_music_frame(&music);
            sid_registers(&sid, music.regs);
            frame_left = FRAME;
        }
        k = n < frame_left ? n : frame_left;
        sid_render(&sid, out, k);
        out += k;
        n -= k;
        frame_left -= k;
    }
}

/* The platform's audio starts with the first sound: browsers only allow it after a key. */
static void lock(void)
{
    if (!started && !modern_scripted()) {
        started = 1;
        plat_audio_start();
    }
    plat_audio_lock();
}

/* Tune t's name, from the file (docs/music.md: after the tables). */
static const char *tune_name(uint8_t t)
{
    static char name[24];
    const uint8_t *d = tunes;
    uint16_t at;
    uint8_t i;

    name[0] = '\0';
    if (!music.ok || t >= d[3]) return name;
    at = (uint16_t)(8u + 8u * d[3] + 10u * d[4] + 2u * d[5] + 2u * d[6]);
    for (i = 0; i < t && at < tunes_len; ++i) at = (uint16_t)(at + 1 + d[at]);
    for (i = 0; at + 1u + i < tunes_len && i < d[at] && i < sizeof(name) - 1; ++i) {
        name[i] = (char)d[at + 1 + i];
    }
    name[i] = '\0';
    return name;
}

uint8_t plat_tune_find(const char *ascii)
{
    return apb_music_find(&music, ascii);
}

/* Into a tune: from silence at once, else after the one playing fades. */
void plat_tune_cue(uint8_t t)
{
    char line[40];

    if (t == NONE) snprintf(line, sizeof(line), "[music off]");
    else snprintf(line, sizeof(line), "[music %s]", tune_name(t));
    modern_note(line);
    lock();
    if (t != NONE && !apb_music_playing(&music)) apb_music_start(&music, t);
    else apb_music_change(&music, t);
    plat_audio_unlock();
}

void hal_music(const char *name)
{
    apb_cue_story(name);
}

void hal_scene_music(uint8_t moment)
{
    apb_cue_scene(moment);
}

void hal_scene_sound(uint8_t effect)
{
    lock();
    apb_music_effect(&music, effect);
    plat_audio_unlock();
}

/* A sound effect alone, as the player and the SID make it, until it has died away. */
int sfx_render(uint8_t effect, int16_t *out, int max)
{
    static apb_music m;
    static modern_sid s;
    int n = 0;
    int k;

    if (effect >= APB_SFX_COUNT) return 0;
    apb_music_init(&m, tunes, 0);
    sid_reset(&s);
    apb_music_effect(&m, effect);
    while (n < max) {
        apb_music_frame(&m);
        sid_registers(&s, m.regs);
        if (n && s.level[0] == 0 && s.level[1] == 0 && s.level[2] == 0) break;
        k = max - n < FRAME ? max - n : FRAME;
        sid_render(&s, out + n, k);
        n += k;
    }
    return n;
}

/* A tune alone, from the start, until it ends (a sting) or `max` samples. */
int music_render(const uint8_t *data, uint16_t len, uint8_t tune, int16_t *out, int max)
{
    static apb_music m;
    static modern_sid s;
    int n = 0;
    int k;

    apb_music_init(&m, data, len);
    sid_reset(&s);
    apb_music_start(&m, tune);
    while (n < max) {
        apb_music_frame(&m);
        sid_registers(&s, m.regs);
        if (n && !apb_music_playing(&m) && s.level[0] == 0 && s.level[1] == 0
            && s.level[2] == 0) {
            break;
        }
        k = max - n < FRAME ? max - n : FRAME;
        sid_render(&s, out + n, k);
        n += k;
    }
    return n;
}
