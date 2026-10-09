/*
 * The battle screen's sound effects (client/apb_scene.h), as the SID's first voice plays
 * them on the C64 (fe/c64/scene.c), and as the desktop and the browser synthesise them
 * the same way (fe/modern/sound.c). One table, so every machine makes the same sounds.
 */
#include "apb_scene.h"

/* Waveform (a SID control byte, gate on), pitch (the frequency's high byte), how much
 * the pitch moves each fiftieth of a second while the gate is open (signed), attack and
 * decay, sustain and release (SID nibbles), and how many fiftieths the gate is open. */
const uint8_t apb_sfx[APB_SFX_COUNT][6] = {
    { 0x81, 0x06, 0x00, 0x00, 0xA1, 2 },     /* step: a scuff of noise     */
    { 0x81, 0x30, 0xF8, 0x02, 0x83, 5 },     /* swing: a whoosh, falling   */
    { 0x21, 0x40, 0xFA, 0x00, 0xA4, 7 },     /* shot: a zip, falling       */
    { 0x81, 0x10, 0xFF, 0x08, 0x09, 3 },     /* hit: a thump               */
    { 0x41, 0x18, 0xFF, 0x05, 0x00, 3 },     /* miss: a dull clack         */
    { 0x21, 0x18, 0xFF, 0x0A, 0x0A, 16 },    /* down: a long falling note  */
    { 0x11, 0x28, 0x00, 0x00, 0xA2, 2 },     /* select: a blip             */
    { 0x21, 0x06, 0x00, 0x00, 0xA4, 5 }      /* no: a low buzz             */
};
