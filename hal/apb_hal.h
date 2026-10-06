/*
 * A Platform Between: the platform interface (HAL).
 *
 * Everything the Story VM needs from a machine. Each front end (terminal, C64,
 * Apple II, DOS, Amiga, SNES, SDL2/browser) implements these functions and
 * nothing else; the VM and rules core are shared.
 *
 * Text arrives as ASCII. Converting to the machine's character set (PETSCII on
 * the C64), word-wrapping to the screen width, and paging ("more") are the
 * front end's job.
 *
 * Same house rules as core/: builds with cc65, whole numbers only.
 */
#ifndef APB_HAL_H
#define APB_HAL_H

#include <stdint.h>

#include "apb.h"

/* Results for the file functions. */
enum {
    HAL_OK = 0,
    HAL_NOT_FOUND,
    HAL_TOO_BIG,
    HAL_IO_ERROR
};

/* ------------------------------------------------------------ setup */

void hal_init(void);
void hal_shutdown(void);

/* ------------------------------------------------------------- text */

/* One character of a paragraph, ASCII 0x20..0x7E. The front end buffers words
 * and wraps them; nothing need appear until hal_text_end(). */
void hal_text_char(char c);

/* End of a paragraph. */
void hal_text_end(void);

/* A chapter title card, e.g. "The Static". */
void hal_chapter(const char *title);

/* Wait for any key. */
void hal_pause(void);

/* ---------------------------------------------------- presentation */

/* Show picture `id` from the image's picture list (the name is given for
 * front ends that load pictures by name). Front ends without pictures ignore it. */
void hal_picture(uint8_t id, const char *name);

/* Redraw the status bar (name, health, level, Debt, ...). */
void hal_status(const apb_character *ch);

/* ------------------------------------------------------------ input */

/* Show `count` (1..9) menu labels, numbered from 1, and return the index
 * (0-based) the player picked. Labels are ASCII, at most 37 characters. */
uint8_t hal_menu(const char *const *labels, uint8_t count);

/* Ask for a name: up to `max` characters into `out`, NUL-terminated. The VM
 * normalizes it to the name alphabet afterwards. */
void hal_ask_name(char *out, uint8_t max);

/* ------------------------------------------------------------ files */

/* Load the named file ("DEPOT", "CAR03", a save, the ledger) into `dst`, at most
 * `max` bytes. On a C64 these are files on the Departure's disk. */
uint8_t hal_load(const char *name, uint8_t *dst, uint16_t max, uint16_t *len);

uint8_t hal_save(const char *name, const uint8_t *src, uint16_t len);

/* ----------------------------------------------------------- errors */

/* The VM stopped: show "The train has derailed: <msg>" and wait. */
void hal_error(const char *msg);

#endif
