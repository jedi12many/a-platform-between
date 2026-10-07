/*
 * The battle screen (docs/combat.md), shared by every front end: the map two
 * characters to a square, so 16 squares fit in 40 columns; a key and a roster; two
 * short menus a turn, "Where to?" and "Then?", offering only what's possible; and what
 * happened, told in sentences with every roll. It implements the HAL's battle calls on
 * top of apb_view_out, apb_view_pick and apb_view_go_on (client/apb_view.h).
 */
#ifdef __CC65__
#include <ascii_charmap.h>      /* every literal in this file is ASCII */
#endif

#include <string.h>

#include "apb_battle.h"
#include "apb_hal.h"
#include "apb_view.h"
#include "apb_vm.h"

#define WIDTH 40

static const char tile_chars[] = ".#O~+^=>";
static const char *const tile_names[] = { "", "wall", "pit", "rough", "cover", "hazard",
                                          "high ground", "exit" };
static const char letters[] = "abcdefghijklmnopqrstuvwxyz";

/* Static: the 6502 gives a function at most 256 bytes of locals. */
static apb_fighter bf;
static char line[APB_VIEW_LINE];
static char name[APB_VM_FOE_NAME_MAX + 1];
static char labels[APB_VIEW_MENU_MAX][APB_VIEW_LABEL];
static uint8_t to_x[APB_VIEW_MENU_MAX];
static uint8_t to_y[APB_VIEW_MENU_MAX];
static uint8_t targets[APB_VIEW_MENU_MAX];
static uint8_t ok[APB_MAP_H_MAX][APB_MAP_W_MAX];     /* where you can get to this turn */
static uint8_t seen[8];
static uint8_t last_round;
static uint8_t redraw;
static uint8_t free_next;    /* the next attack is a free one       */
static uint8_t on_quick;     /* the computer is playing you          */

/* Foe `who` (1..) is the letter a, b, ... on the map. */
static char foe_letter(uint8_t who)
{
    return letters[(who - 1) % 26];
}

static const char *fighter_name(uint8_t who)
{
    if (who) return apb_vm_foe_name(who);
    apb_view_name(name, apb_vm_character());
    return name;
}

static void show_battle(void)
{
    uint8_t x;
    uint8_t y;
    uint8_t i;
    uint8_t t;
    char c;
    char *p;
    uint8_t n;

    memset(seen, 0, sizeof(seen));
    for (y = 0; y < apb_battle_height(); ++y) {
        n = 0;
        line[n++] = ' ';
        for (x = 0; x < apb_battle_width(); ++x) {
            t = (uint8_t)(apb_battle_tile(x, y) & 7);
            seen[t] = 1;
            c = tile_chars[t];
            for (i = 0; i < apb_battle_count(); ++i) {
                apb_battle_fighter(i, &bf);
                if (bf.state == APB_GONE || bf.x != x || bf.y != y) continue;
                c = bf.state == APB_DOWN ? 'x' : i == 0 ? '@' : foe_letter(i);
                if (bf.state == APB_IN_FIGHT) break;
            }
            line[n++] = ' ';
            line[n++] = c;
        }
        line[n] = '\0';
        apb_view_out(line, 0);
    }
    /* A key to the squares on this map, broken between entries. */
    p = line;
    for (t = 1; t < 8; ++t) {
        if (!seen[t]) continue;
        if (p != line && (uint8_t)(p - line) + 4 + strlen(tile_names[t]) > WIDTH) {
            apb_view_out(line, 0);
            p = line;
        }
        p = apb_view_put(p, p != line ? "  " : " ");
        *p++ = tile_chars[t];
        *p++ = ' ';
        p = apb_view_put(p, tile_names[t]);
    }
    if (p != line) apb_view_out(line, 0);
    for (i = 0; i < apb_battle_count(); ++i) {
        apb_battle_fighter(i, &bf);
        if (bf.state == APB_GONE) continue;
        p = line;
        *p++ = ' ';
        *p++ = i == 0 ? '@' : bf.state == APB_DOWN ? 'x' : foe_letter(i);
        *p++ = ' ';
        p = apb_view_put(p, fighter_name(i));
        if (i && bf.state == APB_DOWN) {
            apb_view_put(p, "  down");
        } else {
            p = apb_view_put(p, "  ");
            p = apb_view_unum(p, bf.health);
            p = apb_view_put(p, "/");
            p = apb_view_unum(p, bf.health_max);
            if (i) {
                p = apb_view_put(p, "  TN ");
                apb_view_num(p, apb_battle_tn(0, i));
            }
        }
        apb_view_out(line, 0);
    }
    redraw = 0;
}

void hal_battle_begin(void)
{
    apb_view_fight(1);
    apb_view_out("-- A fight! --", 0);
    last_round = 0xFF;
    free_next = on_quick = 0;
    show_battle();
    apb_view_out("", 0);
}

static uint8_t ev_actor;

/* "Kestrel attacks" or "You attack": the actor, and the verb with or without its s. */
static char *subject(char *p, uint8_t you, const char *verb, const char *s)
{
    p = apb_view_put(p, you ? (const char *)"You" : fighter_name(ev_actor));
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

void hal_battle_event(const apb_event *e)
{
    uint8_t you = (uint8_t)(e->actor == 0);
    char *p = line;

    ev_actor = e->actor;
    switch (e->kind) {
    case APB_EV_TURN:
        if (e->value != last_round) {
            last_round = (uint8_t)e->value;
            if (last_round) {
                p = apb_view_put(p, "-- Round ");
                p = apb_view_unum(p, last_round);
                apb_view_put(p, " --");
                apb_view_out(line, 0);
            } else {
                apb_view_out("-- Caught off guard --", 0);
            }
        }
        return;
    case APB_EV_MOVE:
        p = subject(p, you, "move", "s");
        apb_view_put(p, ".");
        break;
    case APB_EV_FREE:
        free_next = 1;
        return;
    case APB_EV_ATTACK:
        if (free_next) p = apb_view_put(p, "Free attack! ");
        free_next = 0;
        p = subject(p, you, "attack", "s");
        *p++ = ' ';
        p = apb_view_put(p, e->target ? fighter_name(e->target) : (const char *)"you");
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
            p = apb_view_put(p, fighter_name(e->target));
            apb_view_put(p, " is down.");
        } else {
            apb_view_put(p, "You are down.");
        }
        break;
    case APB_EV_HAZARD:
        p = apb_view_put(p, "The ground hurts ");
        p = apb_view_put(p, you ? (const char *)"you" : fighter_name(e->actor));
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
            p = apb_view_put(p, fighter_name(e->actor));
            apb_view_put(p, " runs off.");
        }
        break;
    default:
        return;
    }
    apb_view_out(line, 1);
    redraw = 1;
}

/* A battle menu: no saving in a fight. */
static uint8_t battle_pick(const char *question, uint8_t count)
{
    uint8_t i;
    char *p;

    apb_view_out(question, 0);
    for (i = 0; i < count; ++i) {
        p = apb_view_unum(line, (uint16_t)(i + 1));
        p = apb_view_put(p, ". ");
        apb_view_put(p, labels[i]);
        apb_view_out(line, 1);
    }
    return apb_view_pick(count);
}

static uint8_t dist(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1)
{
    uint8_t dx = (uint8_t)(x0 > x1 ? x0 - x1 : x1 - x0);
    uint8_t dy = (uint8_t)(y0 > y1 ? y0 - y1 : y1 - y0);

    return dx > dy ? dx : dy;
}

static uint8_t here_x;
static uint8_t here_y;

/* The square you can reach (ok[][]) nearest x,y (and, if `tile` isn't 0xFF, of that
 * tile; within `within` squares of x,y), keeping off hazards when you can, into menu
 * entry n. Returns 0 if there is none, or if it's no nearer than where you stand. */
static uint8_t best_square(uint8_t x, uint8_t y, uint8_t tile, uint8_t within, uint8_t n)
{
    uint8_t i;
    uint8_t j;
    uint8_t t;
    uint8_t d;
    uint16_t score;
    uint16_t best = 0xFFFF;

    for (j = 0; j < apb_battle_height(); ++j) {
        for (i = 0; i < apb_battle_width(); ++i) {
            t = apb_battle_tile(i, j);
            if (!ok[j][i] || (i == here_x && j == here_y)) continue;
            if (tile != 0xFF && t != tile) continue;
            d = dist(i, j, x, y);
            if (d > within) continue;
            score = (uint16_t)(d * 2 + (t == APB_TILE_HAZARD ? 64 : 0));
            if (score < best) {
                best = score;
                to_x[n] = i;
                to_y[n] = j;
            }
        }
    }
    if (best == 0xFFFF) return 0;
    if (tile == 0xFF && within == 0xFF
        && dist(to_x[n], to_y[n], x, y) >= dist(here_x, here_y, x, y)) {
        return 0;
    }
    return 1;
}

/* The nearest square of a kind, anywhere on the map, for "toward the exit". */
static uint8_t nearest_tile(uint8_t tile, uint8_t *x, uint8_t *y)
{
    uint8_t i;
    uint8_t j;
    uint8_t best = 0xFF;

    for (j = 0; j < apb_battle_height(); ++j) {
        for (i = 0; i < apb_battle_width(); ++i) {
            if (apb_battle_tile(i, j) == tile && dist(i, j, here_x, here_y) < best) {
                best = dist(i, j, here_x, here_y);
                *x = i;
                *y = j;
            }
        }
    }
    return (uint8_t)(best != 0xFF);
}

/* "Next to Rust-guard (a)" */
static void foe_label(uint8_t n, const char *how, uint8_t foe)
{
    char *p = apb_view_put(labels[n], how);

    p = apb_view_put(p, fighter_name(foe));
    p = apb_view_put(p, " (");
    *p++ = foe_letter(foe);
    apb_view_put(p, ")");
}

void hal_battle_turn(uint8_t who, apb_action *out)
{
    uint8_t n;
    uint8_t i;
    uint8_t pick;
    uint8_t x;
    uint8_t y;
    uint8_t adjacent;
    uint8_t waited;
    char *p;

    if (redraw) {
        apb_view_out("", 0);
        show_battle();
        apb_view_out("", 0);
    }
    if (on_quick) {
        apb_view_out("On quick: Enter, or t to take over.", 0);
        if (apb_view_go_on()) {
            apb_view_out("", 0);
            apb_battle_quick(who, out);
            return;
        }
        on_quick = 0;
    }
    apb_battle_fighter(who, &bf);
    here_x = bf.x;
    here_y = bf.y;
    waited = bf.waited;
    apb_battle_reach_map(who, ok);
    for (;;) {
        /* Where to? Room is kept for the exit, cover, high ground, wait and quick. */
        n = 0;
        apb_view_put(labels[n], "Stay here");
        to_x[n] = here_x;
        to_y[n++] = here_y;
        for (i = 1; i < apb_battle_count() && n < APB_VIEW_MENU_MAX - 5; ++i) {
            apb_battle_fighter(i, &bf);
            if (bf.state != APB_IN_FIGHT) continue;
            x = bf.x;
            y = bf.y;
            if (dist(here_x, here_y, x, y) > 1 && best_square(x, y, 0xFF, 1, n)) {
                foe_label(n++, "Next to ", i);
            } else if (dist(here_x, here_y, x, y) > 1 && best_square(x, y, 0xFF, 0xFF, n)) {
                foe_label(n++, "Toward ", i);
            }
        }
        if (apb_battle_tile(here_x, here_y) != APB_TILE_EXIT
            && nearest_tile(APB_TILE_EXIT, &x, &y)) {
            if (best_square(x, y, APB_TILE_EXIT, 0xFF, n)) {
                apb_view_put(labels[n++], "To the exit");
            } else if (best_square(x, y, 0xFF, 0xFF, n)) {
                apb_view_put(labels[n++], "Toward the exit");
            }
        }
        if (apb_battle_tile(here_x, here_y) != APB_TILE_COVER
            && best_square(here_x, here_y, APB_TILE_COVER, 0xFF, n)) {
            apb_view_put(labels[n++], "Into cover");
        }
        if (apb_battle_tile(here_x, here_y) != APB_TILE_HIGH
            && best_square(here_x, here_y, APB_TILE_HIGH, 0xFF, n)) {
            apb_view_put(labels[n++], "Onto high ground");
        }
        /* Instead of moving: put the turn off, or hand it to the computer. */
        if (!waited) {
            apb_view_put(labels[n], "Wait: act at the end of the round");
            to_x[n++] = 0xFE;
        }
        apb_view_put(labels[n], "Quick: the computer plays you");
        to_x[n++] = 0xFD;
        pick = battle_pick("Where to?", n);
        if (to_x[pick] == 0xFE) {
            apb_view_out("", 0);
            out->move_x = here_x;
            out->move_y = here_y;
            out->kind = APB_ACT_WAIT;
            out->target = 0;
            return;
        }
        if (to_x[pick] == 0xFD) {
            apb_view_out("", 0);
            on_quick = 1;
            apb_battle_quick(who, out);
            return;
        }
        out->move_x = to_x[pick];
        out->move_y = to_y[pick];

        /* Then? Room is kept for guard, flee, done and back. */
        n = 0;
        adjacent = 0;
        for (i = 1; i < apb_battle_count(); ++i) {
            apb_battle_fighter(i, &bf);
            if (bf.state != APB_IN_FIGHT) continue;
            if (dist(out->move_x, out->move_y, bf.x, bf.y) == 1) ++adjacent;
            if (n >= APB_VIEW_MENU_MAX - 4) continue;
            if (!apb_battle_can_attack(who, i, out->move_x, out->move_y)) continue;
            foe_label(n, "Attack ", i);
            p = apb_view_put(labels[n] + strlen(labels[n]), ": TN ");
            apb_view_num(p, apb_battle_tn(who, i));
            targets[n++] = i;
        }
        apb_view_put(labels[n], "Guard: hit the first to come close");
        targets[n++] = 0xF0 | APB_ACT_GUARD;
        if (apb_battle_tile(out->move_x, out->move_y) == APB_TILE_EXIT) {
            apb_view_put(labels[n], "Take the exit");
        } else {
            p = apb_view_put(labels[n], "Flee: TN ");
            apb_view_num(p, apb_flee_tn(adjacent));
        }
        targets[n++] = 0xF0 | APB_ACT_FLEE;
        apb_view_put(labels[n], "Done");
        targets[n++] = 0xF0 | APB_ACT_DONE;
        apb_view_put(labels[n], "Back");
        targets[n++] = 0xFF;
        pick = battle_pick("Then?", n);
        if (targets[pick] == 0xFF) continue;
        apb_view_out("", 0);
        if (targets[pick] < 0xF0) {
            out->kind = APB_ACT_ATTACK;
            out->target = targets[pick];
        } else {
            out->kind = (uint8_t)(targets[pick] & 0x0F);
            out->target = 0;
        }
        return;
    }
}

void hal_battle_end(uint8_t result)
{
    static const char *const endings[] = { "", "You won the fight.", "You lost the fight.",
                                           "You got away." };

    apb_view_out(endings[result & 3], 0);
    apb_view_out("", 0);
    apb_view_fight(0);
}
