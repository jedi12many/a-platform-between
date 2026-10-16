/*
 * The story VM for the native arena's exploring (docs/rooms.md, Talk): the game's own VM
 * (vm/vm.c) and rules (core/, v0), compiled to WebAssembly with Emscripten, playing the
 * talk Departure (content/sidings/yards-talk/) for tools/arena/web/rooms.js.
 *
 * The page boards the party's leader once a descent, and the Departure never ends: it
 * waits at a menu of `@` labels (the host's menus, never shown) for the page to say whom
 * it's talking to, plays the conversation, and comes back to wait again, so what the
 * story remembers lasts the whole descent. A menu waits for the page with Asyncify
 * (js_menu), as the browser game waits for a key.
 *
 *   st_start(PASSPORT, SEED)    board and play (async: ccall with {async: true}); it
 *                               returns only if the Departure ends or the image is bad
 *   st_pack(IDS, N)             the leader's pack, as the page has it, before a talk
 *   st_pack_now(OUT)            the pack after it (the story gives and takes): its count
 *   st_error()                  what went wrong, if st_start returned APB_VM_ERROR
 *
 * The Departure's files are embedded at /talk (DEPOT, CAR00, ...).
 */
#include <stdio.h>
#include <string.h>

#include <emscripten.h>

#include "apb.h"
#include "apb_hal.h"
#include "apb_vm.h"

static char para[1024];
static unsigned para_len;

EM_JS(void, js_text, (const char *text), { Module.onText(UTF8ToString(text)); });

EM_JS(void, js_check, (const char *rating, int roll, int total, int tn, int result), {
    Module.onCheck(UTF8ToString(rating), roll, total, tn, result);
});

EM_JS(void, js_error, (const char *msg), { Module.onError(UTF8ToString(msg)); });

/* The page answers a menu when it's ready: the player's pick, or, for the host's own
 * menus (every label `@...`), its own. */
EM_ASYNC_JS(int, js_menu, (const char *const *labels, int count), {
    var list = [];
    for (var i = 0; i < count; i++) list.push(UTF8ToString(HEAPU32[(labels >> 2) + i]));
    return await Module.onMenu(list);
});

void hal_init(void) {}
void hal_shutdown(void) {}

void hal_text_char(char c)
{
    if (para_len < sizeof(para) - 1) para[para_len++] = c;
}

void hal_text_end(void)
{
    para[para_len] = '\0';
    js_text(para);
    para_len = 0;
}

void hal_chapter(const char *title) { (void)title; }
void hal_pause(void) {}

void hal_check(uint8_t rating, const apb_roll *roll)
{
    static const char *const stats[APB_STAT_COUNT] = {
        "Might", "Grace", "Grit", "Wits", "Presence", "Fate"
    };
    const char *name = rating < APB_STAT_COUNT ? stats[rating]
                     : rating >= 16 && rating < 16 + APB_SKILL_COUNT ? apb_skill_names[rating - 16]
                     : "?";
    js_check(name, roll->roll, roll->total, roll->tn, roll->result);
}

/* Talk ends in a fight by telling the page (`@fight`), which plays it on the rules lab;
 * the talk Departure has no `fight` of its own. Were one there, the traveler would fight
 * it on quick. */
void hal_battle_begin(void) {}
void hal_battle_event(const apb_event *ev) { (void)ev; }
void hal_battle_turn(uint8_t who, apb_action *out) { apb_battle_quick(who, out); }
void hal_battle_end(uint8_t result) { (void)result; }

void hal_picture(uint8_t id, const char *name) { (void)id; (void)name; }
void hal_music(const char *name) { (void)name; }
void hal_status(const apb_character *ch) { (void)ch; }

uint8_t hal_menu(const char *const *labels, uint8_t count)
{
    return (uint8_t)js_menu(labels, count);
}

void hal_ask_line(char *out, uint8_t max) { (void)max; out[0] = '\0'; }
void hal_prompt(const char *msg) { js_text(msg); }

uint8_t hal_load(const char *name, uint8_t *dst, uint16_t max, uint16_t *len)
{
    char path[64];
    FILE *f;
    size_t n;

    snprintf(path, sizeof(path), "/talk/%s", name);
    f = fopen(path, "rb");
    if (!f) return HAL_NOT_FOUND;
    n = fread(dst, 1, max, f);
    if (n == max && fgetc(f) != EOF) {
        fclose(f);
        return HAL_TOO_BIG;
    }
    fclose(f);
    *len = (uint16_t)n;
    return HAL_OK;
}

uint8_t hal_save(const char *name, const uint8_t *src, uint16_t len)
{
    (void)name; (void)src; (void)len;
    return HAL_IO_ERROR;
}

void hal_error(const char *msg) { js_error(msg); }

static char error[96];

EMSCRIPTEN_KEEPALIVE int st_start(const char *passport, int seed)
{
    apb_character ch;
    uint8_t bad = 0;

    if (apb_passport_decode(passport, &ch, &bad) != 0) {
        snprintf(error, sizeof(error), "the leader's Passport won't read (line %u)", bad);
        return APB_VM_ERROR;
    }
    if (apb_vm_board(&ch, (uint16_t)seed) != 0) {
        snprintf(error, sizeof(error), "%s", apb_vm_error());
        return APB_VM_ERROR;
    }
    return apb_vm_run();
}

EMSCRIPTEN_KEEPALIVE const char *st_error(void)
{
    return error[0] ? error : apb_vm_error();
}

/* The pack is the page's (the explore's): it's written into the VM's working copy before
 * each talk, so `has` and `take` see it, and read back after, so `give` lands in it. What
 * the leader holds and wears isn't the story's to trade, so the copy holds nothing else.
 * The working copy is the VM's own; this host is the only one that writes it. */
EMSCRIPTEN_KEEPALIVE void st_pack(const int *ids, int n)
{
    apb_character *ch = (apb_character *)apb_vm_character();
    int i;

    for (i = 0; i < APB_EQUIP_SLOTS; ++i) ch->equipped[i] = 0;
    for (i = 0; i < APB_PACK_SLOTS; ++i) ch->pack[i] = (uint16_t)(i < n ? ids[i] : 0);
}

EMSCRIPTEN_KEEPALIVE int st_pack_now(int *out)
{
    const apb_character *ch = apb_vm_character();
    int i, n = 0;

    for (i = 0; i < APB_PACK_SLOTS; ++i) if (ch->pack[i]) out[n++] = ch->pack[i];
    return n;
}
