/*
 * What happened in a fight, in words: the sentences every battle screen tells
 * (docs/combat.md), the text one (client/battle_view.c) and the one with graphics
 * (client/tactics.c), so a fight reads the same everywhere. ASCII, as all client text.
 */
#ifdef __CC65__
#include <ascii_charmap.h>      /* every literal in this file is ASCII */
#endif

#include "apb_battle.h"
#include "apb_view.h"
#include "apb_vm.h"

static char name[APB_VM_FOE_NAME_MAX + 1];
static uint8_t last_round;
static uint8_t free_next;    /* the next attack is a free one */
static uint8_t ev_actor;

const char *apb_view_fighter(uint8_t who)
{
    if (who) return apb_vm_foe_name(who);
    apb_view_name(name, apb_vm_character());
    return name;
}

void apb_view_battle_reset(void)
{
    last_round = 0xFF;
    free_next = 0;
}

/* "Kestrel attacks" or "You attack": the actor, and the verb with or without its s. */
static char *subject(char *p, uint8_t you, const char *verb, const char *s)
{
    p = apb_view_put(p, you ? (const char *)"You" : apb_view_fighter(ev_actor));
    *p++ = ' ';
    p = apb_view_put(p, verb);
    return you ? p : apb_view_put(p, s);
}

static const char *const hits[] = { "a miss", "a glancing hit", "a hit", "a crit" };
static const char *const flees[] = { "still here", "out, but not cleanly", "out", "out" };

/* "57 + 62 = 119 against 74" */
static char *roll_numbers(char *p, const apb_roll *r)
{
    p = apb_view_unum(p, r->roll);
    p = apb_view_put(p, " + ");
    p = apb_view_num(p, (int16_t)(r->total - r->roll));
    p = apb_view_put(p, " = ");
    p = apb_view_num(p, r->total);
    p = apb_view_put(p, " against ");
    return apb_view_num(p, r->tn);
}

uint8_t apb_view_event(const apb_event *e, char *line)
{
    uint8_t you = (uint8_t)(e->actor == 0);
    char *p = line;

    ev_actor = e->actor;
    switch (e->kind) {
    case APB_EV_TURN:
        if (e->value == last_round) return APB_VIEW_NOTHING;
        last_round = (uint8_t)e->value;
        if (last_round) {
            p = apb_view_put(p, "-- Round ");
            p = apb_view_unum(p, last_round);
            apb_view_put(p, " --");
        } else {
            apb_view_put(p, "-- Caught off guard --");
        }
        return APB_VIEW_HEADING;
    case APB_EV_MOVE:
        p = subject(p, you, "move", "s");
        apb_view_put(p, ".");
        break;
    case APB_EV_FREE:
        free_next = 1;
        return APB_VIEW_NOTHING;
    case APB_EV_ATTACK:
        if (free_next) p = apb_view_put(p, "Free attack! ");
        free_next = 0;
        p = subject(p, you, "attack", "s");
        *p++ = ' ';
        p = apb_view_put(p, e->target ? apb_view_fighter(e->target) : (const char *)"you");
        p = apb_view_put(p, ": ");
        p = roll_numbers(p, &e->roll);
        p = apb_view_put(p, ", ");
        p = apb_view_put(p, hits[e->roll.result & 3]);
        if (e->roll.result != APB_FAIL) {
            p = apb_view_put(p, ": ");
            p = apb_view_unum(p, e->value);
            apb_view_put(p, " damage.");
        } else {
            apb_view_put(p, ".");
        }
        break;
    case APB_EV_DOWN:
        if (e->target) {
            p = apb_view_put(p, apb_view_fighter(e->target));
            apb_view_put(p, " is down.");
        } else {
            apb_view_put(p, "You are down.");
        }
        break;
    case APB_EV_HAZARD:
        p = apb_view_put(p, "The ground hurts ");
        p = apb_view_put(p, you ? (const char *)"you" : apb_view_fighter(e->actor));
        p = apb_view_put(p, ": ");
        p = apb_view_unum(p, e->value);
        apb_view_put(p, " damage.");
        break;
    case APB_EV_GUARD:
        p = subject(p, you, "stand", "s");
        apb_view_put(p, " guard.");
        break;
    case APB_EV_WAIT:
        p = subject(p, you, "wait", "s");
        apb_view_put(p, " to see what happens.");
        break;
    case APB_EV_FLEE:
        if (e->roll.roll) {
            p = subject(p, you, "tr", "ies");
            if (you) *p++ = 'y';
            p = apb_view_put(p, " to get away: ");
            p = roll_numbers(p, &e->roll);
            p = apb_view_put(p, ": ");
            p = apb_view_put(p, flees[e->roll.result & 3]);
            apb_view_put(p, ".");
        } else {
            p = subject(p, you, "take", "s");
            apb_view_put(p, " the exit.");
        }
        break;
    case APB_EV_GONE:
        if (you) {
            apb_view_put(p, "You are out of the fight.");
        } else {
            p = apb_view_put(p, apb_view_fighter(e->actor));
            apb_view_put(p, " runs off.");
        }
        break;
    default:
        return APB_VIEW_NOTHING;
    }
    return APB_VIEW_SENTENCE;
}

static const char *const endings[] = { "", "You won the fight.", "You lost the fight.",
                                       "You got away." };

const char *apb_view_ending(uint8_t result)
{
    return endings[result & 3];
}
