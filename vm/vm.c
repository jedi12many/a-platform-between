/*
 * The Story VM. Implements docs/vm-spec.md.
 *
 * The image is checked as it loads (the depot once, each car when it is loaded),
 * and every operand is checked again when it is used, so a bad image stops the VM
 * with an error instead of reading or writing outside its buffers. On the C64
 * (__CC65__) two load-time checks are skipped: the whole-image hash (it would mean
 * reading every car from disk at the start) and the instruction-boundary bitmap
 * (2 KB of memory); the runtime checks still stand.
 */
#include <string.h>

#include "apb.h"
#include "apb_hal.h"
#include "apb_vm.h"
#include "names.h"

#ifndef __CC65__
#define APB_VM_FULL_CHECKS 1
#endif

/* ------------------------------------------------------------- opcodes */

enum {
    OP_HALT_ERR = 0x00, OP_JMP = 0x01, OP_JZ = 0x02, OP_GOTO = 0x03, OP_SWITCH4 = 0x04,
    OP_END = 0x05,
    OP_TEXT = 0x10, OP_PICTURE = 0x11, OP_PAUSE = 0x12, OP_CHAPTER = 0x13,
    OP_MENU_CLEAR = 0x18, OP_OPTION = 0x19, OP_MENU = 0x1A,
    OP_PUSH8 = 0x20, OP_PUSH16 = 0x21, OP_FLAG = 0x22, OP_VAR = 0x23, OP_HAS = 0x24,
    OP_ECHO = 0x25, OP_RATING = 0x26, OP_LEVEL = 0x27, OP_RACE = 0x28, OP_CLASS = 0x29,
    OP_EQ = 0x30, OP_NE = 0x31, OP_LT = 0x32, OP_LE = 0x33, OP_GT = 0x34, OP_GE = 0x35,
    OP_AND = 0x36, OP_OR = 0x37, OP_NOT = 0x38, OP_CHECK = 0x39,
    OP_SET = 0x40, OP_CLR = 0x41, OP_LET = 0x42, OP_ADD = 0x43, OP_SUB = 0x44,
    OP_GIVE = 0x48, OP_TAKE = 0x49, OP_XP = 0x4A, OP_DEBT = 0x4B, OP_ECHO_SET = 0x4C,
    OP_LAST = 0x4C
};

/* Operand kinds, one letter each:
 * a addr  s scene  t string  f flag  v var  i item  e echo  r rating  p picture
 * b u8    w u16    h s16 */
static const char *const operands[OP_LAST + 1] = {
    "",  "a", "a", "s", "aaaa", "b", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,          /* 00 */
    "t", "p", "",  "",  0, 0, 0, 0, "", "ta", "", 0, 0, 0, 0, 0,          /* 10 */
    "b", "h", "f", "v", "i", "eb", "r", "", "", "", 0, 0, 0, 0, 0, 0,     /* 20 */
    "", "", "", "", "", "", "", "", "", "rb", 0, 0, 0, 0, 0, 0,           /* 30 */
    "f", "f", "v", "vb", "vb", 0, 0, 0, "i", "i", "b", "bw", "eb"        /* 40 */
};

#define SKILL_BASE   16
#define NO_MENU      0xFFFFu
#define NO_TITLE     0xFFFFu
#define STACK_MAX    16
#define MENU_MAX     9
#define LABEL_MAX    38
#define BPE_DEPTH    16
#define BRANCH_GIVES 3      /* items a Branch Line may give per Departure */

/* --------------------------------------------------------------- state */

static uint8_t depot[APB_VM_DEPOT_MAX];
static uint16_t depot_len;
static uint8_t car[APB_VM_CAR_MAX + 16];   /* padding: a damaged image can't read past it */
static uint16_t car_len;
#ifdef APB_VM_FULL_CHECKS
static uint8_t boundary[APB_VM_CAR_MAX / 8];
#endif

/* Depot fields. */
static uint8_t kind;
static uint16_t dep_id;
static uint8_t level_max;
static uint16_t flag_count;
static uint8_t var_count;
static uint16_t scene_count;
static uint16_t start_scene;
static uint16_t var_init_at;
static uint16_t dir_at;
static uint8_t pair_count;
static uint16_t pairs_at;
static uint8_t picture_count;
static uint16_t pictures_at;

/* The loaded car. */
static uint8_t car_index = 0xFF;
static uint16_t car_title;
static uint16_t code_len;
static uint16_t string_count;
static uint16_t offsets_at;         /* in car[] */
static uint16_t strings_at;
static uint16_t strings_len;
#define CODE_AT 9

/* Running state. */
static uint16_t pc;
static uint8_t flags[64];
static uint8_t vars[128];
static int16_t stack[STACK_MAX];
static uint8_t sp;
static uint8_t menu_count;
static uint16_t menu_label[MENU_MAX];
static uint16_t menu_target[MENU_MAX];
static char labels[MENU_MAX][LABEL_MAX];
static const char *label_ptrs[MENU_MAX];
static char title_buf[LABEL_MAX + 4];
static apb_character ch;
static apb_rng rng;
static apb_receipt receipt;
static uint16_t boarded_debt;
static uint8_t gives;

static char error_buf[48];
static uint8_t failed;
static uint16_t steps;              /* instructions since the last menu */
#define STEPS_MAX 20000u

/* ------------------------------------------------------------- helpers */

static uint16_t rd16(const uint8_t *p)
{
    return (uint16_t)(p[0] | ((uint16_t)p[1] << 8));
}

static void put_num(char *out, uint16_t v)
{
    char tmp[6];
    uint8_t n = 0;

    do {
        tmp[n++] = (char)('0' + v % 10);
        v = (uint16_t)(v / 10);
    } while (v);
    while (n) {
        *out++ = tmp[--n];
    }
    *out = '\0';
}

/* Error messages are C strings in the platform's own character set (unlike game text,
 * which is always ASCII); hal_error shows them as they are. */
static void fail(const char *what, uint16_t at)
{
    uint8_t n = 0;
    char num[6];
    const char *p;

    if (failed) {
        return;
    }
    failed = 1;
    for (p = what; *p && n < 30; ++p) {
        error_buf[n++] = *p;
    }
    if (car_index != 0xFF) {
        error_buf[n++] = ' ';
        put_num(num, car_index);
        for (p = num; *p; ++p) error_buf[n++] = *p;
        error_buf[n++] = ':';
        put_num(num, at);
        for (p = num; *p; ++p) error_buf[n++] = *p;
    }
    error_buf[n] = '\0';
}

/* ------------------------------------------------------- loading: depot */

static uint8_t load_depot(void)
{
    uint16_t at;
    uint8_t i;
    uint8_t n;

    if (hal_load("DEPOT", depot, APB_VM_DEPOT_MAX, &depot_len) != HAL_OK) {
        fail("can't load DEPOT", 0);
        return 0;
    }
    if (depot_len < 21 || depot[0] != 0x44 || depot[1] != 0x50 || depot[2] != 0) {
        fail("not a v0 depot", 0);
        return 0;
    }
    kind = depot[3];
    dep_id = rd16(depot + 4);
    level_max = depot[10];
    flag_count = rd16(depot + 11);
    var_count = depot[13];
    scene_count = rd16(depot + 14);
    start_scene = rd16(depot + 16);
    if (kind > 1 || flag_count > 512 || var_count > 128 || scene_count == 0
        || scene_count > 1024 || start_scene >= scene_count || depot[20] > 40) {
        fail("bad depot header", 0);
        return 0;
    }
    at = (uint16_t)(21 + depot[20]);
    var_init_at = at;
    at = (uint16_t)(at + var_count);
    dir_at = at;
    at = (uint16_t)(at + 3u * scene_count);
    if (at >= depot_len) {
        fail("depot too short", 0);
        return 0;
    }
    pair_count = depot[at];
    pairs_at = (uint16_t)(at + 1);
    at = (uint16_t)(pairs_at + 2u * pair_count);
    if (pair_count > 128 || at >= depot_len) {
        fail("bad pair table", 0);
        return 0;
    }
    for (i = 0; i < pair_count; ++i) {
        if (depot[pairs_at + 2 * i] >= 0x80 + i || depot[pairs_at + 2 * i + 1] >= 0x80 + i) {
            fail("pair refers forward", 0);
            return 0;
        }
    }
    picture_count = depot[at];
    pictures_at = (uint16_t)(at + 1);
    at = pictures_at;
    for (i = 0; i < picture_count; ++i) {
        if (at >= depot_len) {
            fail("bad picture list", 0);
            return 0;
        }
        n = depot[at];
        at = (uint16_t)(at + 1 + n);
    }
    if (at != depot_len) {
        fail("depot has trailing bytes", 0);
        return 0;
    }
    for (n = 0, at = 0; at < scene_count; ++at) {
        if (depot[dir_at + 3 * at] >= 64) {
            fail("bad scene directory", 0);
            return 0;
        }
    }
    return 1;
}

static uint8_t dir_car(uint16_t scene)
{
    return depot[dir_at + 3 * scene];
}

static uint16_t dir_off(uint16_t scene)
{
    return rd16(depot + dir_at + 3 * scene + 1);
}

/* --------------------------------------------------------- text decoding */

/* Expands string `id` of the loaded car. Each output byte goes to `out`, which is
 * either the HAL (to == 0) or a buffer of `max` bytes. Returns 0 on a bad string. */
static uint8_t expand(uint16_t id, char *to, uint8_t max, uint8_t check_only)
{
    uint8_t stack_b[BPE_DEPTH + 2];
    uint8_t depth_b[BPE_DEPTH + 2];
    uint8_t s;
    uint16_t at;
    uint8_t c;
    uint8_t d;
    uint8_t want_var = 0;
    uint8_t n = 0;
    char num[6];
    const char *p;
    const char *ins;

    if (id >= string_count) {
        return 0;
    }
    at = rd16(car + offsets_at + 2 * id);
    if (at >= strings_len) {
        return 0;
    }
    at = (uint16_t)(strings_at + at);
    for (;;) {
        if (at >= car_len) {
            return 0;                  /* no terminator */
        }
        c = car[at++];
        if (c == 0) {
            break;
        }
        s = 0;
        stack_b[s] = c;
        depth_b[s] = 0;
        ++s;
        while (s) {
            --s;
            c = stack_b[s];
            d = depth_b[s];
            if (c >= 0x80) {
                c = (uint8_t)(c - 0x80);
                if (c >= pair_count || d >= BPE_DEPTH) {
                    return 0;
                }
                stack_b[s] = depot[pairs_at + 2 * c + 1];
                depth_b[s] = (uint8_t)(d + 1);
                ++s;
                stack_b[s] = depot[pairs_at + 2 * c];
                depth_b[s] = (uint8_t)(d + 1);
                ++s;
                continue;
            }
            ins = 0;
            num[0] = '\0';
            if (want_var) {
                want_var = 0;
                if (c < 1 || c > var_count) {
                    return 0;
                }
                put_num(num, vars[c - 1]);
                ins = num;
            } else if (c == 0x05) {
                want_var = 1;
                continue;
            } else if (c == 0x01) {
                if (!check_only) {
                    /* Names are stored in capitals; in prose they read "Old Mae". */
                    d = 1;
                    for (p = ch.name; *p; ++p) {
                        c = apb_name_ascii(*p);
                        if (!d && c >= 0x41 && c <= 0x5A) {
                            c = (uint8_t)(c + 0x20);
                        }
                        d = (uint8_t)(c == 0x20 || c == 0x2D);
                        if (to) {
                            if (n < max) to[n++] = (char)c;
                        } else {
                            hal_text_char((char)c);
                        }
                    }
                }
                continue;
            } else if (c == 0x02) {
                ins = ch.race < APB_RACE_COUNT ? apb_race_names[ch.race] : (const char *)"";
            } else if (c == 0x03) {
                ins = ch.cls < APB_CLASS_COUNT ? apb_class_names[ch.cls] : (const char *)"";
            } else if (c == 0x04) {
                put_num(num, ch.debt);
                ins = num;
            } else if (c == 0x06) {
                put_num(num, ch.level);
                ins = num;
            } else if (c != 0x0A && (c < 0x20 || c > 0x7E)) {
                return 0;
            }
            if (check_only) {
                continue;
            }
            if (ins) {
                /* put_num writes '0'..'9' as C literals: convert back to ASCII
                 * digits on platforms whose literals aren't ASCII. */
                for (p = ins; *p; ++p) {
                    c = (uint8_t)*p;
                    if (ins == num) {
                        c = (uint8_t)(0x30 + (*p - '0'));
                    }
                    if (to) {
                        if (n < max) to[n++] = (char)c;
                    } else {
                        hal_text_char((char)c);
                    }
                }
            } else if (to) {
                if (n < max) to[n++] = (char)c;
            } else {
                hal_text_char(c == 0x0A ? '\n' : (char)c);
            }
        }
    }
    if (want_var) {
        return 0;
    }
    if (to) {
        to[n] = '\0';
    }
    return 1;
}

/* --------------------------------------------------------- loading: cars */

static uint8_t valid_rating(uint8_t r)
{
    return (uint8_t)(r < APB_STAT_COUNT || (r >= SKILL_BASE && r < SKILL_BASE + APB_SKILL_COUNT));
}

#ifdef APB_VM_FULL_CHECKS
static void mark(uint16_t at)
{
    boundary[at >> 3] |= (uint8_t)(1u << (at & 7));
}

static uint8_t marked(uint16_t at)
{
    return (uint8_t)((boundary[at >> 3] >> (at & 7)) & 1u);
}
#endif

/* Walk the code once: every opcode known, every operand in range. Scene starts
 * come from the directory, in increasing order within a car. */
static uint8_t verify_car(uint8_t index)
{
    uint16_t at = 0;
    uint16_t scene = 0;
    uint16_t next_start = 0xFFFFu;
    uint16_t v;
    uint16_t menu;
    uint8_t op;
    const char *k;
    const uint8_t *code = car + CODE_AT;

#ifdef APB_VM_FULL_CHECKS
    memset(boundary, 0, sizeof(boundary));
#endif
    /* First scene of this car. */
    while (scene < scene_count && dir_car(scene) != index) ++scene;
    if (scene < scene_count) next_start = dir_off(scene);

    while (at < code_len) {
        if (at == next_start) {
            if (at + 2 > code_len) {
                fail("bad scene start", at);
                return 0;
            }
            menu = rd16(code + at);
            if (menu != NO_MENU && (uint16_t)(at + menu) >= code_len) {
                fail("bad menu offset", at);
                return 0;
            }
            at = (uint16_t)(at + 2);
            for (++scene; scene < scene_count && dir_car(scene) != index; ++scene) {
            }
            if (scene < scene_count) {
                if (dir_off(scene) <= next_start) {
                    fail("scenes out of order", at);
                    return 0;
                }
                next_start = dir_off(scene);
            } else {
                next_start = 0xFFFFu;
            }
            continue;
        }
#ifdef APB_VM_FULL_CHECKS
        mark(at);
#endif
        op = code[at];
        if (op > OP_LAST || operands[op] == 0 || op == OP_HALT_ERR) {
            fail("unknown opcode", at);
            return 0;
        }
        if (kind == 1 && (op == OP_DEBT || op == OP_ECHO_SET)) {
            fail("not allowed in a Branch Line", at);
            return 0;
        }
        ++at;
        for (k = operands[op]; *k; ++k) {
            if (*k == 'b' || *k == 'v' || *k == 'r' || *k == 'p') {
                if (at + 1 > code_len) break;
                v = code[at];
                at = (uint16_t)(at + 1);
            } else {
                if (at + 2 > code_len) break;
                v = rd16(code + at);
                at = (uint16_t)(at + 2);
            }
            if ((*k == 'a' && v >= code_len) || (*k == 's' && v >= scene_count)
                || (*k == 't' && v >= string_count) || (*k == 'f' && v >= flag_count)
                || (*k == 'v' && v >= var_count) || (*k == 'p' && v >= picture_count)
                || (*k == 'r' && !valid_rating((uint8_t)v))
                || (*k == 'i' && (v >= APB_ITEM_COUNT || apb_items[v].tier == 0))
                || (*k == 'e' && (v >= APB_ECHO_COUNT || apb_echo_defaults[v] == 0))) {
                fail("operand out of range", at);
                return 0;
            }
        }
        if (*k) {
            fail("instruction runs off the end", at);
            return 0;
        }
    }
    if (next_start != 0xFFFFu) {
        fail("scene start past the code", at);
        return 0;
    }
#ifdef APB_VM_FULL_CHECKS
    /* Second pass: every jump lands on an instruction, every menu on MENU_CLEAR. */
    scene = 0;
    at = 0;
    while (scene < scene_count) {
        if (dir_car(scene) == index) {
            menu = rd16(code + dir_off(scene));
            if (menu != NO_MENU && (!marked((uint16_t)(dir_off(scene) + menu))
                                    || code[dir_off(scene) + menu] != OP_MENU_CLEAR)) {
                fail("menu offset isn't MENU_CLEAR", dir_off(scene));
                return 0;
            }
        }
        ++scene;
    }
    for (at = 0; at < code_len; ++at) {
        if (!marked(at)) continue;
        op = code[at];
        v = (uint16_t)(at + 1);
        for (k = operands[op]; *k; ++k) {
            if (*k == 'a' && !marked(rd16(code + v))) {
                fail("jump into an instruction", at);
                return 0;
            }
            v = (uint16_t)(v + ((*k == 'b' || *k == 'v' || *k == 'r' || *k == 'p') ? 1 : 2));
        }
    }
#endif
    /* Every string must decode. */
    for (v = 0; v < string_count; ++v) {
        if (!expand(v, 0, 0, 1)) {
            fail("bad string", v);
            return 0;
        }
    }
    if (car_title != NO_TITLE && car_title >= string_count) {
        fail("bad chapter title", 0);
        return 0;
    }
    return 1;
}

static uint8_t load_car(uint8_t index)
{
    static char name[6];

    /* File names are C strings in the platform's character set, like "DEPOT". */
    name[0] = 'C'; name[1] = 'A'; name[2] = 'R';
    name[3] = (char)('0' + index / 10);
    name[4] = (char)('0' + index % 10);
    name[5] = '\0';
    car_index = index;
    if (hal_load(name, car, APB_VM_CAR_MAX, &car_len) != HAL_OK) {
        fail("can't load car", 0);
        return 0;
    }
    if (car_len < CODE_AT || car[0] != 0x43 || car[1] != 0x52 || car[2] != index) {
        fail("bad car header", 0);
        return 0;
    }
    car_title = rd16(car + 3);
    code_len = rd16(car + 5);
    string_count = rd16(car + 7);
    offsets_at = (uint16_t)(CODE_AT + code_len);
    strings_at = (uint16_t)(offsets_at + 2u * string_count);
    if (code_len > car_len || string_count > 1024 || strings_at > car_len) {
        fail("bad car sizes", 0);
        return 0;
    }
    strings_len = (uint16_t)(car_len - strings_at);
    return verify_car(index);
}

#ifdef APB_VM_FULL_CHECKS
static uint16_t crc_byte(uint16_t crc, uint8_t b)
{
    uint8_t bit;

    crc ^= (uint16_t)((uint16_t)b << 8);
    for (bit = 0; bit < 8; ++bit) {
        crc = (crc & 0x8000u) ? (uint16_t)((crc << 1) ^ 0x1021u) : (uint16_t)(crc << 1);
    }
    return crc;
}

/* Load every car once to check the whole-image hash. */
static uint8_t check_hash(void)
{
    uint16_t crc = 0xFFFFu;
    uint16_t i;
    uint8_t cars = 0;
    uint16_t s;

    for (s = 0; s < scene_count; ++s) {
        if (dir_car(s) >= cars) cars = (uint8_t)(dir_car(s) + 1);
    }
    for (i = 0; i < depot_len; ++i) {
        crc = crc_byte(crc, (i == 18 || i == 19) ? 0 : depot[i]);
    }
    for (i = 0; i < cars; ++i) {
        if (!load_car((uint8_t)i)) {
            return 0;
        }
        for (s = 0; s < car_len; ++s) {
            crc = crc_byte(crc, car[s]);
        }
    }
    if (crc != rd16(depot + 18)) {
        car_index = 0xFF;
        fail("image hash doesn't match", 0);
        return 0;
    }
    return 1;
}
#endif

/* -------------------------------------------------------------- receipt */

static void receipt_item(uint16_t *list, uint8_t *count, uint16_t item)
{
    if (*count < APB_VM_RECEIPT_MAX) {
        list[(*count)++] = item;
    }
}

static void receipt_echo(uint16_t id, uint8_t state)
{
    uint8_t i;

    for (i = 0; i < receipt.echo_count; ++i) {
        if (receipt.echoes[i].id == id) {
            receipt.echoes[i].state = state;
            return;
        }
    }
    if (receipt.echo_count < APB_VM_RECEIPT_MAX) {
        receipt.echoes[receipt.echo_count].id = id;
        receipt.echoes[receipt.echo_count].state = state;
        ++receipt.echo_count;
    }
}

static uint8_t carrying(uint16_t item)
{
    uint8_t i;

    for (i = 0; i < APB_EQUIP_SLOTS; ++i) if (ch.equipped[i] == item) return 1;
    for (i = 0; i < APB_PACK_SLOTS; ++i) if (ch.pack[i] == item) return 1;
    return 0;
}

static void give(uint16_t item)
{
    uint8_t i;

    if (kind == 1) {
        if (apb_items[item].tier > 3 || gives >= BRANCH_GIVES) {
            return;
        }
        ++gives;
    }
    for (i = 0; i < APB_PACK_SLOTS; ++i) {
        if (ch.pack[i] == 0) {
            ch.pack[i] = item;
            break;
        }
    }
    /* A full pack still earns the item: the lost-and-found keeps it. */
    receipt_item(receipt.gained, &receipt.gained_count, item);
}

static void take(uint16_t item)
{
    uint8_t i;

    for (i = 0; i < APB_PACK_SLOTS; ++i) {
        if (ch.pack[i] == item) {
            ch.pack[i] = 0;
            receipt_item(receipt.lost, &receipt.lost_count, item);
            return;
        }
    }
    for (i = 0; i < APB_EQUIP_SLOTS; ++i) {
        if (ch.equipped[i] == item) {
            ch.equipped[i] = 0;
            receipt_item(receipt.lost, &receipt.lost_count, item);
            return;
        }
    }
}

static void award_xp(uint8_t n)
{
    uint16_t xp;

    if (kind == 1) {
        xp = ch.level > level_max ? 0 : n;
    } else {
        xp = apb_xp_award(n, ch.level, level_max);
    }
    apb_gain_xp(&ch, xp);
    receipt.xp = (uint16_t)(receipt.xp + xp);
}

/* -------------------------------------------------------------- running */

static uint8_t push(int16_t v)
{
    if (sp >= STACK_MAX) {
        fail("stack overflow", pc);
        return 0;
    }
    stack[sp++] = v;
    return 1;
}

static int16_t pop(void)
{
    if (sp == 0) {
        fail("stack underflow", pc);
        return 0;
    }
    return stack[--sp];
}

static uint8_t enter(uint16_t scene)
{
    if (scene >= scene_count) {
        fail("bad scene", pc);
        return 0;
    }
    if (dir_car(scene) != car_index && !load_car(dir_car(scene))) {
        return 0;
    }
    pc = (uint16_t)(dir_off(scene) + 2);
    return 1;
}

static uint8_t rating_value(uint8_t r)
{
    return r < APB_STAT_COUNT ? ch.stat[r] : apb_skill(&ch, (uint8_t)(r - SKILL_BASE));
}

uint8_t apb_vm_board(const apb_character *snapshot, uint16_t seed)
{
    uint8_t i;

    failed = 0;
    error_buf[0] = '\0';
    car_index = 0xFF;
    if (!load_depot()) {
        return APB_VM_ERROR;
    }
#ifdef APB_VM_FULL_CHECKS
    if (!check_hash()) {
        return APB_VM_ERROR;
    }
#endif
    memcpy(&ch, snapshot, sizeof(ch));
    memset(flags, 0, sizeof(flags));
    for (i = 0; i < var_count; ++i) {
        vars[i] = depot[var_init_at + i];
    }
    memset(&receipt, 0, sizeof(receipt));
    receipt.departure = dep_id;
    boarded_debt = ch.debt;
    gives = 0;
    sp = 0;
    menu_count = 0;
    apb_rng_seed(&rng, seed);
    car_index = 0xFF;
    if (!enter(start_scene)) {
        return APB_VM_ERROR;
    }
    return 0;
}

#define FETCH8()  (code[pc++])
#define FETCH16() (pc = (uint16_t)(pc + 2), rd16(code + pc - 2))

uint8_t apb_vm_run(void)
{
    const uint8_t *code;
    uint8_t op;
    uint16_t a;
    uint16_t b;
    int16_t x;
    int16_t y;
    uint8_t i;
    apb_roll roll;

    steps = 0;
    while (!failed) {
        code = car + CODE_AT;
        if (++steps > STEPS_MAX) {
            fail("runaway: no menu or end", pc);
            break;
        }
        if (pc >= code_len) {
            fail("ran off the code", pc);
            break;
        }
        op = code[pc];
        if (op > OP_LAST || operands[op] == 0) {
            fail("bad opcode", pc);
            break;
        }
        /* Every operand is inside the code: verify_car checked each instruction,
         * and every jump target is below code_len, but check again here. */
        if ((uint16_t)(pc + 1 + 8) > code_len && op == OP_SWITCH4) {
            fail("bad instruction", pc);
            break;
        }
        ++pc;
        switch (op) {
        case OP_JMP:
            a = FETCH16();
            if (a >= code_len) { fail("bad jump", pc); break; }
            pc = a;
            break;
        case OP_JZ:
            a = FETCH16();
            if (a >= code_len) { fail("bad jump", pc); break; }
            if (pop() == 0) pc = a;
            break;
        case OP_GOTO:
            a = FETCH16();
            enter(a);
            break;
        case OP_SWITCH4:
            x = pop();
            if (x < 0 || x > 3) { fail("bad switch", pc); break; }
            a = rd16(code + pc + 2 * (uint8_t)x);
            if (a >= code_len) { fail("bad jump", pc); break; }
            pc = a;
            break;
        case OP_END:
            i = FETCH8();
            receipt.outcome = i ? APB_VM_FAILED : APB_VM_COMPLETE;
            if (ch.debt < boarded_debt) {
                receipt.debt_paid = (uint16_t)(boarded_debt - ch.debt);
            } else {
                receipt.debt_added = (uint16_t)(ch.debt - boarded_debt);
            }
            hal_status(&ch);
            return receipt.outcome;
        case OP_TEXT:
            a = FETCH16();
            if (!expand(a, 0, 0, 0)) { fail("bad string", pc); break; }
            hal_text_end();
            break;
        case OP_PICTURE:
            i = FETCH8();
            if (i >= picture_count) { fail("bad picture", pc); break; }
            a = pictures_at;
            while (i--) a = (uint16_t)(a + 1 + depot[a]);
            for (b = 0; b < depot[a] && b < LABEL_MAX; ++b) title_buf[b] = (char)depot[a + 1 + b];
            title_buf[b] = '\0';
            hal_picture((uint8_t)(code[pc - 1]), title_buf);
            break;
        case OP_PAUSE:
            hal_pause();
            break;
        case OP_CHAPTER:
            if (car_title != NO_TITLE) {
                if (!expand(car_title, title_buf, LABEL_MAX, 0)) { fail("bad title", pc); break; }
                hal_chapter(title_buf);
            }
            break;
        case OP_MENU_CLEAR:
            menu_count = 0;
            break;
        case OP_OPTION:
            a = FETCH16();
            b = FETCH16();
            if (menu_count >= MENU_MAX || a >= string_count || b >= code_len) {
                fail("bad option", pc);
                break;
            }
            menu_label[menu_count] = a;
            menu_target[menu_count] = b;
            ++menu_count;
            break;
        case OP_MENU:
            if (menu_count == 0) { fail("empty menu", pc); break; }
            for (i = 0; i < menu_count; ++i) {
                if (!expand(menu_label[i], labels[i], LABEL_MAX - 1, 0)) {
                    fail("bad label", pc);
                    break;
                }
                label_ptrs[i] = labels[i];
            }
            if (failed) break;
            hal_status(&ch);
            steps = 0;
            i = hal_menu(label_ptrs, menu_count);
            if (i >= menu_count) { fail("menu pick out of range", pc); break; }
            pc = menu_target[i];
            break;
        case OP_PUSH8:
            push(FETCH8());
            break;
        case OP_PUSH16:
            push((int16_t)FETCH16());
            break;
        case OP_FLAG:
            a = FETCH16();
            if (a >= flag_count) { fail("bad flag", pc); break; }
            push((flags[a >> 3] >> (a & 7)) & 1);
            break;
        case OP_VAR:
            i = FETCH8();
            if (i >= var_count) { fail("bad var", pc); break; }
            push(vars[i]);
            break;
        case OP_HAS:
            a = FETCH16();
            push(carrying(a));
            break;
        case OP_ECHO:
            a = FETCH16();
            i = FETCH8();
            push(apb_echo_get_or(&ch, a, i));
            break;
        case OP_RATING:
            i = FETCH8();
            if (!valid_rating(i)) { fail("bad rating", pc); break; }
            push(rating_value(i));
            break;
        case OP_LEVEL:
            push(ch.level);
            break;
        case OP_RACE:
            push(ch.race);
            break;
        case OP_CLASS:
            push(ch.cls);
            break;
        case OP_EQ: case OP_NE: case OP_LT: case OP_LE: case OP_GT: case OP_GE:
        case OP_AND: case OP_OR:
            y = pop();
            x = pop();
            switch (op) {
            case OP_EQ: push(x == y); break;
            case OP_NE: push(x != y); break;
            case OP_LT: push(x < y); break;
            case OP_LE: push(x <= y); break;
            case OP_GT: push(x > y); break;
            case OP_GE: push(x >= y); break;
            case OP_AND: push(x && y); break;
            default: push(x || y); break;
            }
            break;
        case OP_NOT:
            push(!pop());
            break;
        case OP_CHECK:
            i = FETCH8();
            a = FETCH8();
            if (!valid_rating(i)) { fail("bad rating", pc); break; }
            apb_check(&rng, rating_value(i), 0, (int16_t)a, &roll);
            hal_check(i, &roll);
            push(roll.result);
            break;
        case OP_SET:
        case OP_CLR:
            a = FETCH16();
            if (a >= flag_count) { fail("bad flag", pc); break; }
            if (op == OP_SET) flags[a >> 3] |= (uint8_t)(1u << (a & 7));
            else flags[a >> 3] &= (uint8_t)~(1u << (a & 7));
            break;
        case OP_LET:
            i = FETCH8();
            if (i >= var_count) { fail("bad var", pc); break; }
            x = pop();
            vars[i] = (uint8_t)(x < 0 ? 0 : (x > 255 ? 255 : x));
            break;
        case OP_ADD:
        case OP_SUB:
            i = FETCH8();
            a = FETCH8();
            if (i >= var_count) { fail("bad var", pc); break; }
            b = vars[i];
            if (op == OP_ADD) b = (uint16_t)(b + a > 255 ? 255 : b + a);
            else b = (uint16_t)(b < a ? 0 : b - a);
            vars[i] = (uint8_t)b;
            break;
        case OP_GIVE:
            a = FETCH16();
            if (a >= APB_ITEM_COUNT || apb_items[a].tier == 0) { fail("bad item", pc); break; }
            give(a);
            break;
        case OP_TAKE:
            a = FETCH16();
            if (a >= APB_ITEM_COUNT) { fail("bad item", pc); break; }
            take(a);
            break;
        case OP_XP:
            award_xp(FETCH8());
            break;
        case OP_DEBT:
            i = FETCH8();
            a = FETCH16();
            if (kind == 1 || i > 2) { fail("bad debt", pc); break; }
            if (i == 0) ch.debt = a;
            else if (i == 1) ch.debt = (uint16_t)(ch.debt > 0xFFFFu - a ? 0xFFFFu : ch.debt + a);
            else ch.debt = (uint16_t)(ch.debt < a ? 0 : ch.debt - a);
            break;
        case OP_ECHO_SET:
            a = FETCH16();
            i = FETCH8();
            if (kind == 1 || a >= APB_ECHO_COUNT || apb_echo_defaults[a] == 0 || i < 1 || i > 3) {
                fail("bad echo", pc);
                break;
            }
            apb_echo_set(&ch, a, i, 0);
            receipt_echo(a, i);
            break;
        default:
            fail("bad opcode", pc);
            break;
        }
    }
    hal_error(error_buf);
    return APB_VM_ERROR;
}

const apb_receipt *apb_vm_receipt(void)
{
    return &receipt;
}

const apb_character *apb_vm_character(void)
{
    return &ch;
}

const char *apb_vm_error(void)
{
    return error_buf;
}
