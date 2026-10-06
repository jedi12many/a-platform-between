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
#include "apb_battle.h"

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

/* One character of a paragraph: ASCII 0x20..0x7E, or '\n' for a line break (from a
 * '|' line). The front end buffers words and wraps them; nothing need appear until
 * hal_text_end(). */
void hal_text_char(char c);

/* End of a paragraph. */
void hal_text_end(void);

/* A chapter title card, e.g. "The Static". */
void hal_chapter(const char *title);

/* Wait for any key. */
void hal_pause(void);

/* A check was rolled: show it, the way a player at a table would see it.
 * `rating` is numbered as in the VM spec: 0..5 a stat, 16..27 a skill. */
void hal_check(uint8_t rating, const apb_roll *roll);

/* ---------------------------------------------------------- battles */

/* A fight has begun: the map and the fighters are set up (read them with the
 * apb_battle_* functions in apb_battle.h). Show them. */
void hal_battle_begin(void);

/* Something happened in the fight: show it. */
void hal_battle_event(const apb_event *ev);

/* A traveler's turn: fill `out` with what they do. Front ends can offer only what's
 * allowed (apb_battle_can_reach, apb_battle_can_attack); the VM checks again, says so
 * with hal_prompt if it isn't allowed, and asks again. */
void hal_battle_turn(uint8_t who, apb_action *out);

/* The fight is over: result is APB_BATTLE_WON, _LOST or _FLED. */
void hal_battle_end(uint8_t result);

/* ---------------------------------------------------- presentation */

/* Show picture `id` from the image's picture list (the name, in ASCII, is given for
 * front ends that load pictures by name). Front ends without pictures ignore it. */
void hal_picture(uint8_t id, const char *name);

/* Redraw the status bar (name, health, level, Debt, ...). */
void hal_status(const apb_character *ch);

/* ------------------------------------------------------------ input */

/* Show `count` (1..9) menu labels, numbered from 1, and return the index
 * (0-based) the player picked. Labels are ASCII, at most 37 characters.
 * Return APB_MENU_SAVE instead to save the trip: the VM saves it ("SAVE", through
 * hal_save), says so with hal_prompt, and shows the menu again. */
#define APB_MENU_SAVE 0xFE
uint8_t hal_menu(const char *const *labels, uint8_t count);

/* Ask the player to type a line: up to `max` characters into `out`, NUL-terminated,
 * in the platform's own character set. Used by the boarding desk for Passport lines. */
void hal_ask_line(char *out, uint8_t max);

/* A message from the client itself (the boarding desk), not from a Departure. Unlike
 * game text, `msg` is a C string in the platform's own character set. */
void hal_prompt(const char *msg);

/* ------------------------------------------------------------ files */

/* Load the named file ("DEPOT", "CAR03", a save, the ledger) into `dst`, at most
 * `max` bytes. On a C64 these are files on the Departure's disk. File names are C
 * strings in the platform's own character set. */
uint8_t hal_load(const char *name, uint8_t *dst, uint16_t max, uint16_t *len);

uint8_t hal_save(const char *name, const uint8_t *src, uint16_t len);

/* ----------------------------------------------------------- errors */

/* The VM stopped: show "The train has derailed: <msg>" and wait. Unlike game text,
 * `msg` is a C string in the platform's own character set. */
void hal_error(const char *msg);

#endif
