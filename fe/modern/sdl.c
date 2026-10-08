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
        } else if (argv[i][0] == '-' || dir) {
            dir = NULL;
            break;
        } else {
            dir = argv[i];
        }
    }
    if (!dir) {
        fprintf(stderr, "usage: apb-modern [--seed N] [--choices FILE] [--shots DIR] DEPARTURE\n"
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
