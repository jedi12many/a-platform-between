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
#include "apb_battle.h"

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
void apb_view_check(char *out, uint8_t rating, const apb_roll *roll);  /* (not if APB_FRAMED) */
/* A roll for the dice log (docs/frames.md): two short lines, "Wits 119" and "vs 74: pass"
 * (APB_VIEW_ROLL each, with the NUL), and the whole of it for the record, "[Wits 119 vs
 * 74: pass]". `who` rolled (shortened to fit: its last word, or its start); `outcome` is
 * the result in a word or two ("hit 6"). */
#define APB_VIEW_ROLL 15
void apb_view_roll(char *top, char *bottom, char *record, const char *who,
                   const apb_roll *roll, const char *outcome);
/* A check's roll, as apb_view_roll has it. */
void apb_view_check_roll(char *top, char *bottom, char *record, uint8_t rating,
                         const apb_roll *roll);
/* The character's name as it reads: "Kestrel" */
void apb_view_name(char *out, const apb_character *ch);

/* The end of a trip: the outcome and the receipt. Then, if `stamped`, the words that
 * introduce the Travel Stamp, which the front end prints after them (its symbols are
 * in the platform's own character set); otherwise why there's none. */
void apb_view_receipt(const apb_receipt *r, uint8_t stamped);

/* A fight in words (client/battle_text.c), for every battle screen. */
enum { APB_VIEW_NOTHING = 0, APB_VIEW_SENTENCE, APB_VIEW_HEADING };
void        apb_view_battle_reset(void);              /* a fight begins          */
/* What an event says, into `line` (APB_VIEW_LINE): a sentence, a heading ("-- Round
 * 2 --"), or nothing to say. */
uint8_t     apb_view_event(const apb_event *e, char *line);
const char *apb_view_fighter(uint8_t who);            /* "Ash rat", or the traveler */
const char *apb_view_ending(uint8_t result);          /* "You won the fight."    */
/* With the rolls apart (a screen with a dice log), a fight's sentences leave the numbers
 * out ("You attack the drone: a hit: 6 damage."), and an event's roll is had from
 * apb_view_event_roll: 1 if it has one. */
void        apb_view_rolls_apart(uint8_t on);
uint8_t     apb_view_event_roll(const apb_event *e, char *top, char *bottom, char *record);

/* Appending to a line: text, and a whole number. Each returns the new end. */
char *apb_view_put(char *at, const char *ascii);
char *apb_view_num(char *at, int16_t v);
char *apb_view_unum(char *at, uint16_t v);

#endif
