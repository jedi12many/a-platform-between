/*
 * What every front end shows, worked out once: the status line, check results, and the
 * whole battle screen (map, roster, menus, what happened). It's all ASCII, like game
 * text; the literals in client/view.c and client/battle_view.c are ASCII on every
 * compiler (cc65's ascii_charmap.h). A front end shows the lines its own way.
 *
 * client/battle_view.c implements hal_battle_begin, _event, _turn and _end on top of
 * the three calls below, which the front end supplies.
 */
#ifndef APB_VIEW_H
#define APB_VIEW_H

#include "apb.h"

#define APB_VIEW_LINE 100       /* the longest line the view writes, with its NUL */
#define APB_VIEW_LABEL 40       /* a menu label, with its NUL                     */
#define APB_VIEW_MENU_MAX 9     /* one key picks on any machine                   */

/* Supplied by the front end. */
void    apb_view_out(const char *ascii, uint8_t wrap);  /* a line; wrap: word-wrap it */
uint8_t apb_view_pick(uint8_t count);   /* ask for 1..count; returns 0..count-1     */
uint8_t apb_view_go_on(void);           /* on quick: 1 to go on, 0 to take over      */
void    apb_view_fight(uint8_t on);     /* a fight starts (1) or ends (0): room for the
                                           map (the C64 puts its picture away)        */

/* "Kestrel  Lvl 1  HP 27/27  Debt 0" */
void apb_view_status(char *out, const apb_character *ch, uint8_t health);
/* "[Melee check: rolled 57 + 62 = 119 against 74: success]" (rating as in the VM:
 * 0..5 a stat, 16.. a skill) */
void apb_view_check(char *out, uint8_t rating, const apb_roll *roll);
/* The character's name as it reads: "Kestrel" */
void apb_view_name(char *out, const apb_character *ch);

/* The end of a trip: the outcome and the receipt. Then, if `stamped`, the words that
 * introduce the Travel Stamp, which the front end prints after them (its symbols are
 * in the platform's own character set); otherwise why there's none. */
void apb_view_receipt(const apb_receipt *r, uint8_t stamped);

/* Appending to a line: text, and a whole number. Each returns the new end. */
char *apb_view_put(char *at, const char *ascii);
char *apb_view_num(char *at, int16_t v);
char *apb_view_unum(char *at, uint16_t v);

#endif
