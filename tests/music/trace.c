/*
 * The C music player's registers, a frame a line (tests/music/check_music.py):
 *
 *   music_trace MUSIC TUNE FRAMES [FRAME:COMMAND:ARG ...]
 *
 * COMMAND is start, change, effect or volume; it's given before that frame is played.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apb_music.h"

static uint8_t data[65536];

int main(int argc, char **argv)
{
    static apb_music m;
    FILE *f;
    size_t len;
    long frames;
    long n;
    int i;
    int k;
    char what[16];
    long at;
    int arg;

    if (argc < 4) {
        fprintf(stderr, "usage: music_trace MUSIC TUNE FRAMES [FRAME:COMMAND:ARG ...]\n");
        return 2;
    }
    f = fopen(argv[1], "rb");
    if (!f) return 2;
    len = fread(data, 1, sizeof(data), f);
    fclose(f);
    apb_music_init(&m, data, (uint16_t)(len > 65535 ? 65535 : len));
    apb_music_start(&m, (uint8_t)atoi(argv[2]));
    frames = atol(argv[3]);
    for (n = 0; n < frames; ++n) {
        for (i = 4; i < argc; ++i) {
            if (sscanf(argv[i], "%ld:%15[a-z]:%d", &at, what, &arg) == 3 && at == n) {
                if (!strcmp(what, "start")) apb_music_start(&m, (uint8_t)arg);
                else if (!strcmp(what, "change")) apb_music_change(&m, (uint8_t)arg);
                else if (!strcmp(what, "effect")) apb_music_effect(&m, (uint8_t)arg);
                else if (!strcmp(what, "volume")) apb_music_volume(&m, (uint8_t)arg);
            }
        }
        apb_music_frame(&m);
        for (k = 0; k < 25; ++k) printf(k ? " %02x" : "%02x", m.regs[k]);
        printf("\n");
    }
    return 0;
}
