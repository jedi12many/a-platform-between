/*
 * A Platform Between: the Story VM.
 *
 * Loads a Departure image through the HAL (hal_load "DEPOT", "CAR00", ...), checks
 * it, and plays it: text and menus go out through the HAL, choices come back the
 * same way. It plays a working copy of the boarding snapshot and records every
 * change in a receipt (docs/boarding.md); it never writes a Passport.
 *
 * Same house rules as core/: portable C that builds with cc65. One VM at a time;
 * its buffers are static (about 21 KB: a 4 KB depot and one 16 KB car).
 */
#ifndef APB_VM_H
#define APB_VM_H

#include <stdint.h>

#include "apb.h"

#ifndef APB_VM_DEPOT_MAX
#define APB_VM_DEPOT_MAX   4096     /* a test build may use less (the 6502 harness: 2 KB) */
#endif
#ifndef APB_VM_CAR_MAX
#define APB_VM_CAR_MAX     6144     /* the compiler's limit; the 6502 harness uses 4 KB */
#endif
#define APB_VM_REWARD_SITES 32      /* XP, GIVE and DEBT instructions in one Departure */
#define APB_VM_FOE_NAME_MAX 20      /* a foe's display name in an encounter record */
#define APB_VM_SAVE_MAX    768      /* the largest save file, in bytes */

/* What apb_vm_run returns. The first two match the receipt's APB_OUTCOME_*. */
enum {
    APB_VM_COMPLETE = APB_OUTCOME_COMPLETE, /* ~ end complete                        */
    APB_VM_FAILED = APB_OUTCOME_FAILED,     /* ~ end failed                          */
    APB_VM_ERROR                            /* the image is bad: see apb_vm_error()  */
};

/* The receipt (apb_receipt, in apb.h) is what a Departure hands back. */

/* Load and check the image's depot, so apb_vm_departure() can be asked before
 * boarding (to check a Boarding Pass). Optional: boarding opens it if needed.
 * Returns 0, or APB_VM_ERROR with apb_vm_error() set. */
uint8_t  apb_vm_open(void);
uint16_t apb_vm_departure(void);
/* 1 for a Siding (kind 2, like the Deep Yards, docs/deep-yards.md): its seed is a yard,
 * so a front end boarding without a Boarding Pass asks which (apb_desk_yard). */
uint8_t  apb_vm_siding(void);

/* Board `snapshot` (copied) with a Boarding Pass: it must be for this Departure and
 * this character as they are (apb_passport_check). The pass seeds the dice, and its
 * ticket goes into the receipt. On a Rewind pass, the Echoes this Departure plants are
 * forgotten before play. Returns 0, or APB_VM_ERROR with apb_vm_error() set. */
uint8_t apb_vm_board_pass(const apb_character *snapshot, const apb_pass *pass);

/* Board without a pass (tests, and play that won't be stamped): `seed` seeds the
 * dice and the receipt's ticket is 0. */
uint8_t apb_vm_board(const apb_character *snapshot, uint16_t seed);

/* Pick up a saved trip instead of boarding: loads "SAVE" through the HAL, checks it
 * belongs to this image and isn't damaged, and shows the menu it was saved at when
 * apb_vm_run is called. A save is made when hal_menu returns APB_MENU_SAVE. */
uint8_t apb_vm_resume(void);

/* Play until the Departure ends or the image turns out to be bad. */
uint8_t apb_vm_run(void);

#ifdef APB_VM_TRACE
/* Coverage builds only: called with each instruction's car and offset before it runs.
 * The front end (a test harness) defines it. */
void apb_vm_trace(uint8_t car, uint16_t pc);
#endif

const apb_receipt   *apb_vm_receipt(void);
uint8_t              apb_vm_health(void);       /* now; it carries from fight to fight */
/* In a fight, the display name (ASCII, like game text) of fighter `who`: a foe. The
 * traveler is fighter 0, and gets "". */
const char          *apb_vm_foe_name(uint8_t who);
const apb_character *apb_vm_character(void);   /* the working copy */
const char          *apb_vm_error(void);       /* e.g. "car 1 at 233: bad jump" */

#endif
