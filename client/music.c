/*
 * The music player in C (docs/music.md, client/apb_music.h), for the desktop and the
 * browser. tools/music/player.py is its reference: tests/music/check_music.py checks they
 * write the same registers, frame by frame, and that a damaged file plays silence.
 */
#include <string.h>

#include "apb_music.h"
#include "apb_scene.h"

/* The SID's frequency for each note on a PAL C64 (docs/music.md, "The note table"). */
static const uint16_t notes[96] = {
    0x0116, 0x0127, 0x0139, 0x014B, 0x015F, 0x0174, 0x018A, 0x01A1,
    0x01BA, 0x01D4, 0x01F0, 0x020E, 0x022D, 0x024E, 0x0271, 0x0296,
    0x02BE, 0x02E7, 0x0314, 0x0342, 0x0374, 0x03A9, 0x03E0, 0x041B,
    0x045A, 0x049C, 0x04E2, 0x052D, 0x057B, 0x05CF, 0x0627, 0x0685,
    0x06E8, 0x0751, 0x07C1, 0x0837, 0x08B4, 0x0938, 0x09C4, 0x0A59,
    0x0AF7, 0x0B9D, 0x0C4E, 0x0D0A, 0x0DD0, 0x0EA2, 0x0F81, 0x106D,
    0x1167, 0x1270, 0x1389, 0x14B2, 0x15ED, 0x173B, 0x189C, 0x1A13,
    0x1BA0, 0x1D45, 0x1F02, 0x20DA, 0x22CE, 0x24E0, 0x2711, 0x2964,
    0x2BDA, 0x2E76, 0x3139, 0x3426, 0x3740, 0x3A89, 0x3E04, 0x41B4,
    0x459C, 0x49C0, 0x4E23, 0x52C8, 0x57B4, 0x5CEB, 0x6272, 0x684C,
    0x6E80, 0x7512, 0x7C08, 0x8368, 0x8B39, 0x9380, 0x9C45, 0xA590,
    0xAF68, 0xB9D6, 0xC4E3, 0xD099, 0xDD00, 0xEA24, 0xF810, 0xFFFF
};

#define FX_NONE 255
#define STOP 254                    /* next_tune: fade out, then stop */
#define CMD_START 1
#define CMD_CHANGE 2
#define CMD_EFFECT 3
#define CMD_VOLUME 4

/* A byte of the file, or -1 past its end. */
static int byte_at(const apb_music *m, uint16_t at)
{
    return at < m->len ? m->d[at] : -1;
}

static int word_at(const apb_music *m, uint16_t at)
{
    int lo = byte_at(m, at);
    int hi = byte_at(m, (uint16_t)(at + 1));

    return lo < 0 || hi < 0 ? -1 : lo | hi << 8;
}

static uint16_t instrument_at(const apb_music *m, uint8_t i)
{
    return (uint16_t)(8 + 8 * m->d[3] + 10 * i);
}

static uint16_t steps_at(const apb_music *m)
{
    return (uint16_t)(8 + 8 * m->d[3] + 10 * m->d[4]);
}

static uint16_t patterns_at(const apb_music *m)
{
    return (uint16_t)(steps_at(m) + 2 * m->d[5]);
}

void apb_music_init(apb_music *m, const uint8_t *data, uint16_t len)
{
    memset(m, 0, sizeof(*m));
    m->d = data;
    m->len = len;
    m->ok = (uint8_t)(len >= 8 && len <= 1536 && data[0] == 'M' && data[1] == 'U' && data[2] == 1
                      && data[3] >= 1 && data[3] <= 32 && data[4] <= 32 && data[5] <= 128
                      && data[6] <= 128
                      && len >= 8u + 8u * data[3] + 10u * data[4] + 2u * data[5] + 2u * data[6]);
    m->volume = m->target = 15;
    m->next_tune = APB_MUSIC_NONE;
    m->tempo = 2;
    m->fx = FX_NONE;
    m->v[0].stopped = m->v[1].stopped = m->v[2].stopped = 1;
}

static void command(apb_music *m, uint8_t what, uint8_t arg)
{
    if (m->cmds < APB_MUSIC_COMMANDS) {
        m->cmd[m->cmds][0] = what;
        m->cmd[m->cmds][1] = arg;
        ++m->cmds;
    }
}

void apb_music_start(apb_music *m, uint8_t tune) { command(m, CMD_START, tune); }
void apb_music_change(apb_music *m, uint8_t tune) { command(m, CMD_CHANGE, tune); }
void apb_music_effect(apb_music *m, uint8_t effect) { command(m, CMD_EFFECT, effect); }
void apb_music_volume(apb_music *m, uint8_t volume) { command(m, CMD_VOLUME, volume); }

static void fresh(apb_music *m)
{
    uint8_t i;

    memset(m->v, 0, sizeof(m->v));
    for (i = 0; i < 3; ++i) {
        m->v[i].stopped = 1;
        m->v[i].length = 1;
    }
}

/* On through the sequence to the next pattern; 0: the voice stops. */
static uint8_t next_pattern(apb_music *m, apb_music_voice *v)
{
    uint8_t n;
    int b;
    int at;

    for (n = 0; n < 63; ++n) {
        b = byte_at(m, v->seq);
        if (b < 0) return 0;
        ++v->seq;
        if (b == 0xFE) {
            v->loop = v->seq;
        } else if (b == 0xFF) {
            if (!v->loop) return 0;
            v->seq = v->loop;
        } else if (b >= 0xC0) {
            return 0;
        } else if (b >= 0x80) {
            v->transpose = (int8_t)(b - 0xA0);
        } else {
            if (b >= m->d[6]) return 0;
            at = word_at(m, (uint16_t)(patterns_at(m) + 2 * b));
            if (at < 0) return 0;
            v->pat = (uint16_t)at;
            return 1;
        }
    }
    return 0;
}

static void start(apb_music *m, uint8_t t)
{
    uint16_t at;
    uint8_t i;
    int seq;

    fresh(m);
    m->volume = m->target = 15;
    m->next_tune = APB_MUSIC_NONE;
    if (!m->ok || t >= m->d[3]) return;
    at = (uint16_t)(8 + 8 * t);
    m->tempo = m->d[at];
    if (m->tempo < 2 || m->tempo > 31) return;
    for (i = 0; i < 3; ++i) {
        seq = word_at(m, (uint16_t)(at + 2 + 2 * i));
        if (seq < 0) continue;
        m->v[i].stopped = 0;
        m->v[i].seq = (uint16_t)seq;
        if (!next_pattern(m, &m->v[i])) m->v[i].stopped = 1;
    }
}

static uint8_t clamp_note(int n)
{
    return (uint8_t)(n < 0 ? 0 : n > 95 ? 95 : n);
}

/* The next event; 0: the voice stops. */
static uint8_t fetch(apb_music *m, apb_music_voice *v)
{
    uint16_t n;
    uint16_t ins;
    uint8_t legato;
    uint8_t depth;
    int b;

    for (n = 0; n < 255; ++n) {
        b = byte_at(m, v->pat);
        if (b < 0) return 0;
        ++v->pat;
        if (b == 0xFF) {
            if (!next_pattern(m, v)) return 0;
        } else if (b == 0xE0) {
            v->slur_next = 1;
        } else if (b >= 0xC0 && b <= 0xDF) {
            if ((b & 0x1F) >= m->d[4]) return 0;
            v->instrument = (uint8_t)(b & 0x1F);
        } else if (b >= 0x80 && b <= 0xBF) {
            v->length = (uint8_t)((b & 0x3F) + 1);
        } else if (b <= 0x61) {
            legato = v->slur;
            v->slur = v->slur_next;
            v->slur_next = 0;
            v->frames = (uint16_t)(v->length * m->tempo);
            if (b == 0x60) {
                v->gate = 0;
            } else if (b <= 0x5F) {
                v->note = clamp_note(b + v->transpose);
                if (!m->d[4]) return 0;
                ins = instrument_at(m, v->instrument);
                if (!(legato && v->has_note)) {
                    v->has_note = 1;
                    v->gate = 1;
                    v->step = m->d[ins + 2];
                    v->pulse = (int16_t)(m->d[ins + 3] << 4);
                    v->sweep = (int16_t)(int8_t)m->d[ins + 4];
                    v->vib_count = 0;
                    v->vib_phase = 0;
                    v->vib_offset = 0;
                }
                depth = m->d[ins + 8];
                /* A damaged file's depth can be anything: past 15 the step is 0. */
                v->vib_step = depth && depth < 16
                    ? (uint16_t)((notes[clamp_note(v->note + 1)] - notes[v->note]) >> depth) : 0;
            }
            return 1;
        } else {
            return 0;
        }
    }
    return 0;
}

static void voice_frame(apb_music *m, apb_music_voice *v)
{
    uint16_t ins;
    uint16_t base;
    uint8_t c;
    uint8_t p;
    uint8_t depth;
    uint8_t speed;
    int16_t high;
    int16_t low;

    if (v->stopped) return;
    if (v->frames) --v->frames;
    if (v->frames == 0 && !fetch(m, v)) {
        v->stopped = 1;
        v->gate = 0;
        return;
    }
    if (v->frames == 1 && !v->slur && v->has_note) v->gate = 0;
    if (!v->has_note) return;
    ins = instrument_at(m, v->instrument);
    /* The waveform table. */
    base = steps_at(m);
    if (v->step < m->d[5]) {
        c = m->d[base + 2 * v->step];
        p = m->d[base + 2 * v->step + 1];
        if (c == 0xFF) {
            v->step = p;
            if (v->step < m->d[5] && m->d[base + 2 * v->step] != 0xFF) {
                v->control = m->d[base + 2 * v->step];
                v->pitch = m->d[base + 2 * v->step + 1];
                ++v->step;
            }
        } else {
            v->control = c;
            v->pitch = p;
            ++v->step;
        }
    }
    /* The pulse width. */
    if (m->d[ins + 4]) {
        v->pulse = (int16_t)(v->pulse + v->sweep);
        high = (int16_t)(m->d[ins + 6] << 4);
        low = (int16_t)(m->d[ins + 5] << 4);
        if (v->pulse > high) {
            v->pulse = high;
            v->sweep = (int16_t)-v->sweep;
        } else if (v->pulse < low) {
            v->pulse = low;
            v->sweep = (int16_t)-v->sweep;
        }
    }
    /* Vibrato. */
    depth = m->d[ins + 8];
    speed = m->d[ins + 9];
    if (depth) {
        if (v->vib_count < 255) ++v->vib_count;
        if (v->vib_count > m->d[ins + 7]) {
            if (v->vib_phase < speed || v->vib_phase >= 3 * speed) {
                v->vib_offset = (uint16_t)(v->vib_offset + v->vib_step);
            } else {
                v->vib_offset = (uint16_t)(v->vib_offset - v->vib_step);
            }
            ++v->vib_phase;
            if (v->vib_phase >= 4 * speed) v->vib_phase = 0;
        }
    }
}

static void write_voice(apb_music *m, uint8_t i)
{
    apb_music_voice *v = &m->v[i];
    uint8_t *r = m->regs + 7 * i;
    uint16_t ins;
    uint16_t f;
    uint8_t n;
    int rel;

    if (i == 2 && m->fx != FX_NONE) return;
    if (!v->has_note) {
        r[4] &= 0xFE;
        return;
    }
    ins = instrument_at(m, v->instrument);
    if (v->pitch & 0x80) {
        n = clamp_note(v->pitch & 0x7F);
    } else {
        rel = (v->pitch & 0x40) ? v->pitch - 128 : v->pitch;
        n = clamp_note(v->note + rel);
    }
    f = (uint16_t)(notes[n] + v->vib_offset);
    r[0] = (uint8_t)(f & 0xFF);
    r[1] = (uint8_t)(f >> 8);
    r[2] = (uint8_t)(v->pulse & 0xFF);
    r[3] = (uint8_t)((v->pulse >> 8) & 0x0F);
    r[4] = (uint8_t)((v->control & 0xFE) | v->gate);
    r[5] = m->d[ins];
    r[6] = m->d[ins + 1];
}

static void effect_frame(apb_music *m)
{
    const uint8_t *e = apb_sfx[m->fx];
    uint8_t first = m->fx_first;

    m->fx_first = 0;
    if (!first) {
        if (m->fx_frames) {
            --m->fx_frames;
            if (m->fx_frames) m->fx_pitch = (uint8_t)(m->fx_pitch + e[2]);
        } else if (--m->fx_release == 0) {
            m->fx = FX_NONE;
            m->v[2].gate = 0;
            write_voice(m, 2);
            return;
        }
    }
    m->regs[14] = 0;
    m->regs[15] = m->fx_pitch;
    m->regs[16] = 0;
    m->regs[17] = 8;
    m->regs[18] = (uint8_t)((e[0] & 0xFE) | (m->fx_frames ? 1 : 0));
    m->regs[19] = e[3];
    m->regs[20] = e[4];
}

void apb_music_frame(apb_music *m)
{
    uint8_t i;
    uint8_t what;
    uint8_t arg;

    for (i = 0; i < m->cmds; ++i) {
        what = m->cmd[i][0];
        arg = m->cmd[i][1];
        if (what == CMD_START) {
            start(m, arg);
        } else if (what == CMD_CHANGE) {
            m->next_tune = arg == APB_MUSIC_NONE ? STOP : arg;
            m->target = 0;
            m->fade_count = 0;
        } else if (what == CMD_EFFECT) {
            if (arg < APB_SFX_COUNT) {
                m->fx = arg;
                m->fx_frames = apb_sfx[arg][5];
                m->fx_release = 12;
                m->fx_pitch = apb_sfx[arg][1];
                m->fx_first = 1;
            }
        } else if (what == CMD_VOLUME) {
            m->volume = m->target = (uint8_t)(arg & 15);
        }
    }
    m->cmds = 0;
    if (m->volume != m->target && ++m->fade_count >= 2) {
        m->fade_count = 0;
        m->volume = (uint8_t)(m->target > m->volume ? m->volume + 1 : m->volume - 1);
    }
    if (m->volume == 0 && m->target == 0 && m->next_tune != APB_MUSIC_NONE) {
        if (m->next_tune == STOP) {
            fresh(m);
            m->next_tune = APB_MUSIC_NONE;
        } else {
            start(m, m->next_tune);
        }
    }
    for (i = 0; i < 3; ++i) {
        voice_frame(m, &m->v[i]);
        write_voice(m, i);
    }
    if (m->fx != FX_NONE) effect_frame(m);
    m->regs[21] = m->regs[22] = m->regs[23] = 0;
    m->regs[24] = m->volume;
}

uint8_t apb_music_find(const apb_music *m, const char *name)
{
    uint16_t at;
    uint8_t t;
    uint8_t n;
    int len;

    if (!m->ok) return APB_MUSIC_NONE;
    at = (uint16_t)(patterns_at(m) + 2 * m->d[6]);
    n = (uint8_t)strlen(name);
    for (t = 0; t < m->d[3]; ++t) {
        len = byte_at(m, at);
        if (len < 0 || at + 1 + len > m->len) return APB_MUSIC_NONE;
        if (len == n && !memcmp(m->d + at + 1, name, n)) return t;
        at = (uint16_t)(at + 1 + len);
    }
    return APB_MUSIC_NONE;
}

uint8_t apb_music_playing(const apb_music *m)
{
    return (uint8_t)(!m->v[0].stopped || !m->v[1].stopped || !m->v[2].stopped);
}
