/* Which tune plays when: client/apb_cue.h. */
#include "apb_cue.h"
#include "apb_scene.h"

#define NONE 255

/* The fight's tunes' names, in ASCII on every compiler (cc65 would make PETSCII of a
 * literal). */
static const char name_battle[] = { 0x62, 0x61, 0x74, 0x74, 0x6C, 0x65, 0 };
static const char name_won[] = { 0x77, 0x6F, 0x6E, 0 };
static const char name_lost[] = { 0x6C, 0x6F, 0x73, 0x74, 0 };

static uint8_t story = NONE;            /* the story's tune */
static uint8_t now = NONE;              /* the one cued last */

static void play(uint8_t t)
{
    if (t == now) return;
    now = t;
    plat_tune_cue(t);
}

void apb_cue_story(const char *name)
{
    uint8_t t = NONE;

    if (name) {
        t = plat_tune_find(name);
        if (t == NONE) return;          /* not in the music file: whatever plays, plays on */
    }
    story = t;
    play(t);
}

void apb_cue_scene(uint8_t moment)
{
    const char *name = 0;
    uint8_t t;

    if (moment == APB_SCENE_FIGHT) name = name_battle;
    else if (moment == APB_SCENE_WON) name = name_won;
    else if (moment == APB_SCENE_LOST) name = name_lost;
    if (!name) {
        play(story);
        return;
    }
    t = plat_tune_find(name);
    if (t != NONE) play(t);
}

void apb_cue_back(void)
{
    play(story);
}
