/*
 * The boarding desk: how every client starts. The player types their Passport, one
 * line at a time; a line with a typo is named so only that line is retyped; then the
 * character is shown and the player boards. Characters are made at the Waystation
 * website (docs/waystation-web.md), never here.
 *
 * Portable C on the HAL, shared by every front end.
 */
#ifndef APB_DESK_H
#define APB_DESK_H

#include "apb.h"

#define APB_DESK_LINES 8        /* a Passport is at most 8 lines            */
#define APB_DESK_TYPED 38       /* a typed line, with spaces or dashes      */

/* Run the desk until the player boards. Fills `out` and returns 1. */
uint8_t apb_desk_run(apb_character *out);

#endif
