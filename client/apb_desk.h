/*
 * The boarding desk: how every client starts. The player types their Boarding Pass (the
 * trip and the character in one, from the Waystation website), one line at a time; a
 * line with a typo is named so only that line is retyped; then the character is shown
 * and the player boards. A Passport works too, for a trip nothing can be stamped from.
 * Characters are made at the Waystation website (docs/waystation-web.md), never here.
 *
 * Portable C on the HAL, shared by every front end.
 */
#ifndef APB_DESK_H
#define APB_DESK_H

#include "apb.h"

#define APB_DESK_LINES 9        /* a Boarding Pass is at most 9 lines        */
#define APB_DESK_TYPED 38       /* a typed line, with spaces or dashes      */

/* Run the desk until the player boards `departure`'s train. Fills `out` with the
 * character; returns 1 with `pass` filled for a Boarding Pass, or 0 for a Passport (the
 * player was told nothing they earn can be stamped). */
uint8_t apb_desk_run(uint16_t departure, apb_character *out, apb_pass *pass);

/* A Siding's yard (docs/deep-yards.md), asked after travelling without a pass: the
 * number the player types, or `fresh` for a blank line. */
uint16_t apb_desk_yard(uint16_t fresh);

#endif
