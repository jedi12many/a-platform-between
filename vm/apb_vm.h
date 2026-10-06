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

#define APB_VM_DEPOT_MAX   4096
#define APB_VM_CAR_MAX     16384
#define APB_VM_RECEIPT_MAX 8        /* entries per list in a receipt */

/* What apb_vm_run returns. */
enum {
    APB_VM_COMPLETE = 0,    /* ~ end complete                        */
    APB_VM_FAILED,          /* ~ end failed                          */
    APB_VM_ERROR            /* the image is bad: see apb_vm_error()  */
};

/* What a Departure hands back (docs/boarding.md). */
typedef struct {
    uint16_t departure;
    uint8_t  outcome;                       /* APB_VM_COMPLETE or APB_VM_FAILED */
    uint16_t xp;                            /* awarded, after the level band    */
    uint16_t debt_paid;                     /* one of these two is 0            */
    uint16_t debt_added;
    uint8_t  gained_count;
    uint16_t gained[APB_VM_RECEIPT_MAX];    /* item ids                         */
    uint8_t  lost_count;
    uint16_t lost[APB_VM_RECEIPT_MAX];
    uint8_t  echo_count;
    apb_echo echoes[APB_VM_RECEIPT_MAX];    /* Echoes set, latest state         */
} apb_receipt;

/* Load and check the image, and board `snapshot` (copied). Returns 0, or
 * APB_VM_ERROR with apb_vm_error() set. `seed` seeds the dice. */
uint8_t apb_vm_board(const apb_character *snapshot, uint16_t seed);

/* Play until the Departure ends or the image turns out to be bad. */
uint8_t apb_vm_run(void);

#ifdef APB_VM_TRACE
/* Coverage builds only: called with each instruction's car and offset before it runs.
 * The front end (a test harness) defines it. */
void apb_vm_trace(uint8_t car, uint16_t pc);
#endif

const apb_receipt   *apb_vm_receipt(void);
const apb_character *apb_vm_character(void);   /* the working copy */
const char          *apb_vm_error(void);       /* e.g. "car 1 at 233: bad jump" */

#endif
