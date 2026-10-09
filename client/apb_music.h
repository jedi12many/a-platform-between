/*
 * The music player (docs/music.md): a Departure's tunes, from the file tools/music/musicc.py
 * writes, played a frame at a time into the SID's 25 registers. The desktop and the
 * browser use this; the C64 has the same player in 6502 (fe/c64/music.s); and
 * tools/music/player.py is the reference both must match, frame by frame.
 */
#ifndef APB_MUSIC_H
#define APB_MUSIC_H

#include "apb.h"

#define APB_MUSIC_NONE 255          /* change(): fade out and stop */
#define APB_MUSIC_COMMANDS 8

typedef struct {
    uint8_t stopped, has_note;
    uint16_t seq, loop, pat;        /* loop: 0 = none (offsets are never 0) */
    int8_t transpose;
    uint8_t length, instrument;
    uint16_t frames;
    uint8_t note, slur_next, slur, gate;
    uint8_t step, control, pitch;
    int16_t pulse, sweep;
    uint8_t vib_count, vib_phase;
    uint16_t vib_offset, vib_step;
} apb_music_voice;

typedef struct {
    const uint8_t *d;
    uint16_t len;
    uint8_t ok;
    apb_music_voice v[3];
    uint8_t regs[25];
    uint8_t volume, target, fade_count, next_tune, tempo;
    uint8_t fx, fx_frames, fx_release, fx_pitch, fx_first;     /* fx = 255: none */
    uint8_t cmd[APB_MUSIC_COMMANDS][2];
    uint8_t cmds;
} apb_music;

void apb_music_init(apb_music *m, const uint8_t *data, uint16_t len);
/* Commands: they take effect at the next frame. */
void apb_music_start(apb_music *m, uint8_t tune);
void apb_music_change(apb_music *m, uint8_t tune);
void apb_music_effect(apb_music *m, uint8_t effect);
void apb_music_volume(apb_music *m, uint8_t volume);
/* One frame: m->regs is what the SID's registers hold after it. */
void apb_music_frame(apb_music *m);
/* A tune's number by its name, or APB_MUSIC_NONE. */
uint8_t apb_music_find(const apb_music *m, const char *name);
/* True while a tune has a voice playing. */
uint8_t apb_music_playing(const apb_music *m);

#endif
