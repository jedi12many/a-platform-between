/*
 * Which tune plays when (docs/music.md), the same on every machine that has music: the
 * story's `~ music` cues, a fight's `battle`, `won` and `lost`, and the story's tune
 * again after. A tune already playing isn't started again.
 *
 * The front end provides two things: finding a tune by its name, and fading into one.
 */
#ifndef APB_CUE_H
#define APB_CUE_H

#include "apb.h"

/* hal_music: a story cue (0: fade out). */
void apb_cue_story(const char *name);
/* hal_scene_music: a fight's moment (APB_SCENE_FIGHT, ... in apb_scene.h). */
void apb_cue_scene(uint8_t moment);
/* Back on the story's screen. */
void apb_cue_back(void);

/* The front end's: a tune's number by its ASCII name, or 255; fade into tune t (255:
 * fade out). */
uint8_t plat_tune_find(const char *ascii);
void plat_tune_cue(uint8_t t);

#endif
