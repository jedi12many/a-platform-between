"""Reference implementation of the Passport password, format version 2.

Written from docs/passport-spec.md, independently of core/src/passport.c, so the
two can check each other. Also the starting point for the character-sheet printer
and the web Passport Office.

    python3 tools/passport/passport.py decode "<password>"
    python3 tools/passport/passport.py new NAME RACE CLASS M,G,G,W,P,F TAG [ITEM] [ECHO=STATE...]

`new` makes a test character until the Waystation website exists (point-buy stats,
before race and class bonuses), and prints its Passport in lines. ITEM is equipped (`-`
for none, or several separated by commas); ECHO=STATE plants Echoes, as if earlier
Departures had.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "registry"))
import registry  # noqa: E402

VERSION = 2
NAME_ALPHABET = " ABCDEFGHIJKLMNOPQRSTUVWXYZ-'.!?"
SYMBOLS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
LINE_DATA = 19

# Names come from the registry, the same files the C engine is generated from.
_REG = registry.load()
STATS = [s.lower() for s in registry.STATS]
SKILLS = [e["display"] for e in sorted(_REG["skills"].values(), key=lambda e: e["id"])]
RACES = [e["display"] for e in sorted(_REG["races"].values(), key=lambda e: e["id"])]
CLASSES = [e["display"] for e in sorted(_REG["classes"].values(), key=lambda e: e["id"])]
ITEMS = {e["id"]: e["display"] for e in _REG["items"].values()}
ECHOES = {e["id"]: e for e in _REG["echoes"].values()}


class PassportError(ValueError):
    pass


SKILLS = 12                     # the Passport's lists, at most (docs/passport-spec.md)
POWER_SLOTS = 8
ITEM_SLOTS = 6
ECHO_SLOTS = 8


def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def line_check(values):
    return sum(v * (2 * i + 1) for i, v in enumerate(values)) % 32


def new_character():
    return {
        "name": "", "race": 0, "class": 0, "level": 1, "xp": 0,
        "stats": [25] * 6, "stat_points": 0, "skill_points": 0,
        "debt": 0, "flags": 0, "tags": [],
        "training": {},            # skill index -> 1..100
        "powers": [],              # [(id, rank)] in slot order
        "equipped": {},            # slot -> item id
        "pack": {},                # slot -> item id
        "echoes": [],              # [(id, state)] oldest first
    }


def field_bits(ch):
    """The Passport's fields as bits, from its version on (docs/passport-spec.md)."""
    bits = []

    def put(value, n):
        if value < 0 or value >= (1 << n):
            raise PassportError(f"value {value} doesn't fit in {n} bits")
        bits.extend((value >> (n - 1 - i)) & 1 for i in range(n))

    put(VERSION, 4)
    name = ch["name"].upper()[:8].ljust(8)
    for c in name:
        put(NAME_ALPHABET.index(c) if c in NAME_ALPHABET else 0, 5)
    put(ch["race"], 5)
    put(ch["class"], 4)
    put(ch["level"], 7)
    put(ch["xp"], 7)
    for v in ch["stats"]:
        put(v, 7)
    put(ch["stat_points"], 8)
    put(ch["skill_points"], 8)
    put(ch["debt"], 16)
    put(ch["flags"], 7)
    put(sum(1 << s for s in ch["tags"]), 12)
    trained = sorted((s, t) for s, t in ch["training"].items() if t)
    put(len(trained), 4)
    for s, t in trained:
        put(s, 4)
        put(t, 7)
    put(len(ch["powers"]), 4)
    for pid, rank in ch["powers"]:
        put(pid, 8)
        put(rank, 7)
    for key in ("equipped", "pack"):
        items = sorted(ch[key].items())
        put(len(items), 3)
        for slot, item in items:
            put(slot, 3)
            put(item, 10)
    put(len(ch["echoes"]), 4)
    for eid, state in ch["echoes"]:
        put(eid, 10)
        put(state, 2)
    return bits


def to_bytes(bits):
    """Bits, padded with zeros to a whole byte, as bytes."""
    bits = bits + [0] * (-len(bits) % 8)
    return bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8))


def _payload(ch):
    """The Passport's fields as bytes, before the CRC."""
    return to_bytes(field_bits(ch))


def check(ch):
    """The Passport's CRC-16: what a Boarding Pass carries to name the character as boarded."""
    return crc16(_payload(ch))


def symbols(bits):
    """Bits to password text: lines of 19 data symbols, each followed by its check."""
    while len(bits) % 5:
        bits.append(0)
    values = [int("".join(map(str, bits[i:i + 5])), 2) for i in range(0, len(bits), 5)]
    out = ""
    for start in range(0, len(values), LINE_DATA):
        line = values[start:start + LINE_DATA]
        out += "".join(SYMBOLS[v] for v in line) + SYMBOLS[line_check(line)]
    return out


def to_bits(value, n):
    if value < 0 or value >= (1 << n):
        raise PassportError(f"value {value} doesn't fit in {n} bits")
    return [(value >> (n - 1 - i)) & 1 for i in range(n)]


def encode(ch):
    payload = _payload(ch)
    bits = [(b >> (7 - i)) & 1 for b in payload for i in range(8)] + to_bits(crc16(payload), 16)
    return symbols(bits)


def lines(password):
    """Split a password into its display lines of up to 20 symbols."""
    return [password[i:i + 20] for i in range(0, len(password), 20)]


PASSPORT_LONGEST = 149          # the longest Passport any character has (and pass, stamp)
PASS_LONGEST = 163
STAMP_LONGEST = 84


def read_symbols(text, what="Passport", longest=PASSPORT_LONGEST):
    """A typed password's data bits, each line's check symbol checked. More symbols than
    the longest there can be is the wrong length."""
    values = []
    for c in text:
        if c in " -\n\r\t":
            continue
        u = c.upper()
        if u == "O":
            u = "0"
        elif u in "IL":
            u = "1"
        if u not in SYMBOLS:
            raise PassportError(f"'{c}' isn't a {what} symbol")
        if len(values) == longest:
            raise PassportError("wrong length")
        values.append(SYMBOLS.index(u))

    data = []
    for n, start in enumerate(range(0, len(values), 20), 1):
        line = values[start:start + 20]
        if len(line) < 2:
            raise PassportError("wrong length")
        if line_check(line[:-1]) != line[-1]:
            raise PassportError(f"line {n} has a typo")
        data.extend(line[:-1])
    return [(v >> (4 - i)) & 1 for v in data for i in range(5)]


def decode(text):
    return read_character(read_symbols(text), 0)


def read_character(bits, pos):
    """The character from `bits[pos:]` (its version, its fields), then the CRC-16 over
    every byte of `bits` before it."""

    def get(n):
        nonlocal pos
        if pos + n > len(bits):
            raise PassportError("password is too short")
        value = int("".join(map(str, bits[pos:pos + n])), 2)
        pos += n
        return value

    if get(4) != VERSION:
        raise PassportError("made by a different version of the game")
    ch = new_character()
    ch["name"] = "".join(NAME_ALPHABET[get(5)] for _ in range(8)).rstrip()
    ch["race"] = get(5)
    ch["class"] = get(4)
    ch["level"] = get(7)
    ch["xp"] = get(7)
    ch["stats"] = [get(7) for _ in range(6)]
    ch["stat_points"] = get(8)
    ch["skill_points"] = get(8)
    ch["debt"] = get(16)
    ch["flags"] = get(7)
    tags = get(12)
    ch["tags"] = [s for s in range(12) if tags >> s & 1]
    # The lists hold only what a character can have (docs/passport-spec.md, "What's
    # refused"): reading stops at the first rule broken, as the C engine's does, and the
    # Passport is refused; the numbers in range are checked after the checksum.
    def refuse(broken):
        if broken:
            raise PassportError("checksum doesn't match")

    n = get(4)
    refuse(n > SKILLS)
    for _ in range(n):
        s = get(4)
        refuse(s >= SKILLS or s in ch["training"])
        ch["training"][s] = get(7)
        refuse(ch["training"][s] == 0)
    n = get(4)
    refuse(n > POWER_SLOTS)
    for _ in range(n):
        pid = get(8)
        ch["powers"].append((pid, get(7)))
        refuse(pid == 0)
    for key in ("equipped", "pack"):
        n = get(3)
        refuse(n > ITEM_SLOTS)
        for _ in range(n):
            slot = get(3)
            refuse(slot >= ITEM_SLOTS or slot in ch[key])
            ch[key][slot] = get(10)
            refuse(ch[key][slot] == 0)
    n = get(4)
    refuse(n > ECHO_SLOTS)
    for _ in range(n):
        eid = get(10)
        ch["echoes"].append((eid, get(2)))
        refuse(eid == 0)

    while pos % 8:
        if get(1):
            raise PassportError("checksum doesn't match")
    payload_end = pos
    stored = get(16)
    payload = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, payload_end, 8))
    if stored != crc16(payload):
        raise PassportError("checksum doesn't match")
    if len(bits) - pos >= 5:
        raise PassportError("wrong length")
    if any(bits[pos:]):
        raise PassportError("checksum doesn't match")
    refuse(not 1 <= ch["level"] <= 100 or ch["xp"] >= 100
           or any(v > 100 for v in ch["stats"]) or any(v > 100 for v in ch["training"].values())
           or any(rank > 100 for _, rank in ch["powers"]))
    return ch


def create(name, race, cls, stats, extra_tag, reg=None):
    """A new level-1 character, by the creation rules in docs/rules-v0.md.

    Written from the rules, independently of core/src/rules.c, so tests can check one
    against the other. stats: six base values (bought or rolled and arranged).
    """
    reg = reg or _REG
    if race not in reg["races"] or cls not in reg["classes"]:
        raise PassportError("unknown race or class")
    if extra_tag not in reg["skills"]:
        raise PassportError("unknown skill")
    c = reg["classes"][cls]
    tag = reg["skills"][extra_tag]["id"]
    if tag in c["tags"]:
        raise PassportError("the extra tag repeats a class tag")
    ch = new_character()
    ch["name"] = name.upper()
    ch["race"] = reg["races"][race]["id"]
    ch["class"] = c["id"]
    ch["stats"] = [min(100, v) for v in stats]
    r = reg["races"][race]["bonus"]
    ch["stats"][r] = min(100, ch["stats"][r] + 10)
    ch["stats"][c["bonus"]] = min(100, ch["stats"][c["bonus"]] + 5)
    ch["tags"] = sorted(c["tags"] + [tag])
    ch["training"] = {s: 20 for s in ch["tags"]}
    return ch


def pointbuy_ok(stats):
    return all(25 <= v <= 70 for v in stats) and sum(v - 25 for v in stats) == 150


def describe(ch):
    out = dict(ch)
    out["race"] = RACES[ch["race"]] if ch["race"] < len(RACES) else ch["race"]
    out["class"] = CLASSES[ch["class"]] if ch["class"] < len(CLASSES) else ch["class"]
    out["stats"] = dict(zip(STATS, ch["stats"]))
    out["tags"] = [SKILLS[s] for s in ch["tags"]]
    out["training"] = {SKILLS[s]: t for s, t in ch["training"].items()}
    for key in ("equipped", "pack"):
        out[key] = {slot: ITEMS.get(i, f"item {i}") for slot, i in ch[key].items()}
    out["echoes"] = [f"{ECHOES[i]['name']}: {ECHOES[i]['states'][st - 1]}"
                     if i in ECHOES and 1 <= st <= len(ECHOES[i]["states"]) else f"echo {i}: {st}"
                     for i, st in ch["echoes"]]
    return out


if __name__ == "__main__":
    if len(sys.argv) >= 7 and sys.argv[1] == "new":
        _, _, name, race, cls, stats, tag, *rest = sys.argv
        values = [int(v) for v in stats.split(",")]
        if len(values) != 6 or not pointbuy_ok(values):
            sys.exit("stats must be six point-buy values: 25..70 each, 150 points spent")
        ch = create(name, race, cls, values, tag)
        if rest and "=" not in rest[0]:
            if rest[0] != "-":
                ch["equipped"] = {i: _REG["items"][name]["id"]
                                  for i, name in enumerate(rest[0].split(","))}
            rest = rest[1:]
        for planted in rest:
            echo, _, state = planted.partition("=")
            e = _REG["echoes"][echo]
            ch["echoes"].append((e["id"], e["states"].index(state) + 1))
        print("\n".join(lines(encode(ch))))
    elif len(sys.argv) == 3 and sys.argv[1] == "decode":
        try:
            print(json.dumps(describe(decode(sys.argv[2])), indent=2))
        except PassportError as e:
            sys.exit(f"Not a valid Passport: {e}")
    else:
        sys.exit(__doc__)
