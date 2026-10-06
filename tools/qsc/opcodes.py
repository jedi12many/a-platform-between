"""The Story VM's instruction set, as listed in docs/vm-spec.md.

Operand kinds: u8, u16, s16 are plain numbers; addr is a code offset in the car;
scene, str, flag, var, item, echo, pic are ids of that kind; rating is a stat (0-5)
or a skill (16-27).
"""

OPS = {
    # flow
    "HALT_ERR":   (0x00, []),
    "JMP":        (0x01, ["addr"]),
    "JZ":         (0x02, ["addr"]),
    "GOTO":       (0x03, ["scene"]),
    "SWITCH4":    (0x04, ["addr", "addr", "addr", "addr"]),
    "END":        (0x05, ["u8"]),
    # text and presentation
    "TEXT":       (0x10, ["str"]),
    "PICTURE":    (0x11, ["pic"]),
    "PAUSE":      (0x12, []),
    "CHAPTER":    (0x13, []),
    # menus
    "MENU_CLEAR": (0x18, []),
    "OPTION":     (0x19, ["str", "addr"]),
    "MENU":       (0x1A, []),
    # expressions
    "PUSH8":      (0x20, ["u8"]),
    "PUSH16":     (0x21, ["s16"]),
    "FLAG":       (0x22, ["flag"]),
    "VAR":        (0x23, ["var"]),
    "HAS":        (0x24, ["item"]),
    "ECHO":       (0x25, ["echo", "u8"]),
    "RATING":     (0x26, ["rating"]),
    "LEVEL":      (0x27, []),
    "RACE":       (0x28, []),
    "CLASS":      (0x29, []),
    "EQ":         (0x30, []),
    "NE":         (0x31, []),
    "LT":         (0x32, []),
    "LE":         (0x33, []),
    "GT":         (0x34, []),
    "GE":         (0x35, []),
    "AND":        (0x36, []),
    "OR":         (0x37, []),
    "NOT":        (0x38, []),
    "CHECK":      (0x39, ["rating", "u8"]),
    "FIGHT":      (0x3A, ["enc", "u8"]),
    # changing state
    "SET":        (0x40, ["flag"]),
    "CLR":        (0x41, ["flag"]),
    "LET":        (0x42, ["var"]),
    "ADD":        (0x43, ["var", "u8"]),
    "SUB":        (0x44, ["var", "u8"]),
    "GIVE":       (0x48, ["item"]),
    "TAKE":       (0x49, ["item"]),
    "XP":         (0x4A, ["u8"]),
    "DEBT":       (0x4B, ["u8", "u16"]),
    "ECHO_SET":   (0x4C, ["echo", "u8"]),
    "HEAL":       (0x4D, ["u8"]),
}

BY_CODE = {code: (name, operands) for name, (code, operands) in OPS.items()}

WIDTH = {"u8": 1, "var": 1, "pic": 1, "rating": 1, "enc": 1,
         "u16": 2, "s16": 2, "addr": 2, "scene": 2, "str": 2, "flag": 2, "item": 2,
         "echo": 2}

# Opcodes a Branch Line image may not contain.
OFFICIAL_ONLY = {"DEBT", "ECHO_SET"}

COMPARE = {"=": "EQ", "!=": "NE", "<": "LT", "<=": "LE", ">": "GT", ">=": "GE"}

SKILL_RATING_BASE = 16      # RATING 16 + n is skill n
NO_MENU = 0xFFFF            # a scene's menu offset when it has no menu
NO_TITLE = 0xFFFF           # a car's title string when its chapter has none
STACK_DEPTH = 16
MAX_OPTIONS = 9
MAX_CAR = 16384
MAX_DEPOT = 4096                # vm/apb_vm.h, APB_VM_DEPOT_MAX
MAX_ENCOUNTERS = 32
MAP_TILES = ".#O~+^=>"          # tile codes 0..7, in order (core/include/apb.h, APB_TILE_*)
ENCOUNTER_FOE_BYTES = 18        # x, y, then 16 numbers (docs/vm-spec.md)
FOE_NAME_MAX = 20               # each foe's display name, after the numbers
BPE_MAX_PAIRS = 128
BPE_MAX_DEPTH = 16

# Bytes inside strings.
TXT_END = 0x00
TXT_NAME = 0x01
TXT_RACE = 0x02
TXT_CLASS = 0x03
TXT_DEBT = 0x04
TXT_VAR = 0x05              # followed by the variable's index + 1 (never 0x00)
TXT_LEVEL = 0x06
TXT_NEWLINE = 0x0A
