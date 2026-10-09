/*
 * The modern front end on a desktop, with SDL2 (fe/modern/modern.h).
 *
 *   apb-modern [--seed N] [--choices FILE] [--shots DIR] DEPARTURE
 *
 * DEPARTURE is a directory of the Departure's files (DEPOT, CAR00, ..., pic00.apic, ...),
 * as `make modern` writes them under build/modern/. Saves go in the same directory.
 * The window scales the 640 x 400 screen to fit; menus take a key or a click.
 *
 * --choices plays from a file with no window at all, and writes the screen's rows to
 * stdout as they scroll (tests/modern/); --shots saves a picture of the screen (PPM)
 * each time the game waits.
 */
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <SDL.h>

#include "apb_scene.h"
#include "modern.h"

static uint32_t fb[SCR_W * SCR_H];
static SDL_Window *window;
static SDL_Renderer *renderer;
static SDL_Texture *texture;
static const char *shot_dir;
static unsigned shots;

void plat_show(void)
{
    if (!renderer) return;
    modern_render(fb);
    SDL_UpdateTexture(texture, NULL, fb, SCR_W * 4);
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
    SDL_RenderClear(renderer);
    SDL_RenderCopy(renderer, texture, NULL, NULL);
    SDL_RenderPresent(renderer);
}

uint16_t plat_key(void)
{
    SDL_Event ev;
    int row;

    plat_show();
    for (;;) {
        if (!SDL_WaitEvent(&ev)) continue;
        switch (ev.type) {
        case SDL_QUIT:
            SDL_Quit();
            exit(0);
        case SDL_WINDOWEVENT:
            plat_show();
            break;
        case SDL_TEXTINPUT:
            if ((unsigned char)ev.text.text[0] >= 0x20 && (unsigned char)ev.text.text[0] <= 0x7E
                && ev.text.text[1] == '\0') {
                return (uint8_t)ev.text.text[0];
            }
            break;
        case SDL_KEYDOWN:
            if (ev.key.keysym.sym == SDLK_RETURN || ev.key.keysym.sym == SDLK_KP_ENTER) return KEY_RETURN;
            if (ev.key.keysym.sym == SDLK_BACKSPACE) return KEY_DELETE;
            if (ev.key.keysym.sym == SDLK_ESCAPE) return KEY_ESCAPE;
            if (ev.key.keysym.sym == SDLK_UP) return KEY_ARROW | 1;
            if (ev.key.keysym.sym == SDLK_DOWN) return KEY_ARROW | 2;
            if (ev.key.keysym.sym == SDLK_LEFT) return KEY_ARROW | 3;
            if (ev.key.keysym.sym == SDLK_RIGHT) return KEY_ARROW | 4;
            break;
        case SDL_MOUSEBUTTONDOWN:
            /* SDL_RenderSetLogicalSize maps the click into the 640 x 400 screen. */
            row = ev.button.y / 16;
            if (ev.button.button == SDL_BUTTON_LEFT && row >= 0 && row < SCR_ROWS) {
                return (uint16_t)(KEY_CLICK | row);
            }
            break;
        default:
            break;
        }
    }
}

void plat_saved(void) {}

/* Sound: an SDL audio device that pulls the music's samples (fe/modern/sound.c). */
static SDL_AudioDeviceID audio;

static void SDLCALL pull(void *unused, Uint8 *stream, int len)
{
    (void)unused;
    sound_mix((int16_t *)stream, len / (int)sizeof(int16_t));
}

void plat_audio_start(void)
{
    SDL_AudioSpec want;

    if (!renderer) return;                  /* no window: no sound either */
    memset(&want, 0, sizeof(want));
    want.freq = SFX_RATE;
    want.format = AUDIO_S16SYS;
    want.channels = 1;
    want.samples = 1024;
    want.callback = pull;
    if (SDL_InitSubSystem(SDL_INIT_AUDIO) == 0) {
        audio = SDL_OpenAudioDevice(NULL, 0, &want, NULL, 0);
        if (audio) SDL_PauseAudioDevice(audio, 0);
    }
}

void plat_audio_lock(void)
{
    if (audio) SDL_LockAudioDevice(audio);
}

void plat_audio_unlock(void)
{
    if (audio) SDL_UnlockAudioDevice(audio);
}

/* --sounds DIR: every sound effect as a WAV file (sfx0.wav, ...), for tests and ears. */
static void put32(FILE *f, uint32_t v)
{
    fputc((int)(v & 0xFF), f);
    fputc((int)(v >> 8 & 0xFF), f);
    fputc((int)(v >> 16 & 0xFF), f);
    fputc((int)(v >> 24), f);
}

static int write_wav(const char *path, const int16_t *samples, int n)
{
    FILE *f = fopen(path, "wb");
    int i;

    if (!f) {
        fprintf(stderr, "can't write %s\n", path);
        return 1;
    }
    fwrite("RIFF", 1, 4, f);
    put32(f, (uint32_t)(36 + 2 * n));
    fwrite("WAVEfmt ", 1, 8, f);
    put32(f, 16);
    put32(f, 1u | 1u << 16);                        /* PCM, one channel */
    put32(f, SFX_RATE);
    put32(f, SFX_RATE * 2);
    put32(f, 2u | 16u << 16);                       /* 2 bytes a sample, 16 bits */
    fwrite("data", 1, 4, f);
    put32(f, (uint32_t)(2 * n));
    for (i = 0; i < n; ++i) {
        fputc(samples[i] & 0xFF, f);
        fputc((samples[i] >> 8) & 0xFF, f);
    }
    fclose(f);
    return 0;
}

static int write_sounds(const char *dir)
{
    static int16_t samples[2 * SFX_RATE];
    char path[512];
    int effect;
    int n;

    for (effect = 0; effect < APB_SFX_COUNT; ++effect) {
        n = sfx_render((uint8_t)effect, samples, 2 * SFX_RATE);
        snprintf(path, sizeof(path), "%s/sfx%d.wav", dir, effect);
        if (write_wav(path, samples, n)) return 1;
    }
    return 0;
}

/* --music DEPARTURE DIR: each of its tunes, up to 20 seconds of it, as a WAV file
 * (tune0.wav, ...), for tests and ears. */
static int write_music(const char *departure, const char *dir)
{
    static uint8_t data[1536];
    static int16_t samples[20 * SFX_RATE];
    char path[512];
    FILE *f;
    size_t len;
    int tune;
    int n;

    snprintf(path, sizeof(path), "%s/MUSIC", departure);
    f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "no music in %s\n", departure);
        return 1;
    }
    len = fread(data, 1, sizeof(data), f);
    fclose(f);
    for (tune = 0; len >= 8 && tune < data[3]; ++tune) {
        n = music_render(data, (uint16_t)len, (uint8_t)tune, samples, 20 * SFX_RATE);
        snprintf(path, sizeof(path), "%s/tune%d.wav", dir, tune);
        if (write_wav(path, samples, n)) return 1;
    }
    return 0;
}

void plat_wait(unsigned ms)
{
    SDL_Event ev;

    plat_show();
    if (!renderer) return;
    while (SDL_PollEvent(&ev)) {
        if (ev.type == SDL_QUIT) {
            SDL_Quit();
            exit(0);
        }
    }
    SDL_Delay(ms);
}

/* A picture of the screen, for a person to look at. */
static void shot(void)
{
    char path[1024];
    FILE *f;
    int i;

    snprintf(path, sizeof(path), "%s/screen%03u.ppm", shot_dir, ++shots);
    f = fopen(path, "wb");
    if (!f) return;
    modern_render(fb);
    fprintf(f, "P6\n%d %d\n255\n", SCR_W, SCR_H);
    for (i = 0; i < SCR_W * SCR_H; ++i) {
        fputc((int)(fb[i] >> 16) & 0xFF, f);
        fputc((int)(fb[i] >> 8) & 0xFF, f);
        fputc((int)fb[i] & 0xFF, f);
    }
    fclose(f);
}

int main(int argc, char **argv)
{
    int i;
    unsigned seed = (unsigned)time(NULL);
    const char *dir = NULL;
    const char *choices = NULL;
    FILE *choice_file = NULL;

    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
            seed = (unsigned)atoi(argv[++i]);
        } else if (strcmp(argv[i], "--choices") == 0 && i + 1 < argc) {
            choices = argv[++i];
        } else if (strcmp(argv[i], "--shots") == 0 && i + 1 < argc) {
            shot_dir = argv[++i];
        } else if (strcmp(argv[i], "--sounds") == 0 && i + 1 < argc) {
            return write_sounds(argv[++i]);
        } else if (strcmp(argv[i], "--music") == 0 && i + 2 < argc) {
            return write_music(argv[i + 1], argv[i + 2]);
        } else if (argv[i][0] == '-' || dir) {
            dir = NULL;
            break;
        } else {
            dir = argv[i];
        }
    }
    if (!dir) {
        fprintf(stderr, "usage: apb-modern [--seed N] [--choices FILE] [--shots DIR] DEPARTURE\n"
                        "       apb-modern --sounds DIR   (the sound effects as WAV files)\n"
                        "       apb-modern --music DEPARTURE DIR   (its tunes as WAV files)\n"
                        "  DEPARTURE is a directory of its files (make modern writes them)\n");
        return 2;
    }
    if (choices) {
        choice_file = fopen(choices, "r");
        if (!choice_file) {
            fprintf(stderr, "can't open %s\n", choices);
            return 2;
        }
    } else {
        if (SDL_Init(SDL_INIT_VIDEO) != 0) {
            fprintf(stderr, "can't start SDL: %s\n", SDL_GetError());
            return 1;
        }
        window = SDL_CreateWindow("A Platform Between", SDL_WINDOWPOS_CENTERED,
                                  SDL_WINDOWPOS_CENTERED, SCR_W * 2, SCR_H * 2,
                                  SDL_WINDOW_RESIZABLE | SDL_WINDOW_ALLOW_HIGHDPI);
        renderer = window ? SDL_CreateRenderer(window, -1, SDL_RENDERER_PRESENTVSYNC) : NULL;
        texture = renderer ? SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGB888,
                                               SDL_TEXTUREACCESS_STREAMING, SCR_W, SCR_H) : NULL;
        if (!texture) {
            fprintf(stderr, "can't open a window: %s\n", SDL_GetError());
            return 1;
        }
        SDL_RenderSetLogicalSize(renderer, SCR_W, SCR_H);
        SDL_StartTextInput();
    }
    if (shot_dir) modern_on_wait = shot;
    modern_setup(dir, dir, choice_file, choice_file ? stdout : NULL);
    modern_play((uint16_t)seed);
    if (renderer) SDL_Quit();
    return 0;
}
