"""Reference implementation of the Passport password, format version 2.

Written from docs/passport-spec.md, independently of core/src/passport.c, so the
two can check each other. Also the starting point for the character-sheet printer
and the web Passport Office.

    python3 tools/passport/passport.py decode "<password>"
"""

import json
import sys

VERSION = 2
NAME_ALPHABET = " ABCDEFGHIJKLMNOPQRSTUVWXYZ-'.!?"
SYMBOLS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
LINE_DATA = 19

STATS = ["might", "grace", "grit", "wits", "presence", "fate"]
SKILLS = ["melee", "athletics", "ranged", "stealth", "endurance", "survival",
          "tech", "medicine", "lore", "persuade", "channel", "intuition"]
RACES = ["Human", "Hollowborn", "Glassfolk", "Rad-Dryad", "Chronomite",
         "Salvaged", "Moth-folk"]
CLASSES = ["Warden", "Rogue", "Tinker", "Channeler", "Medic"]


class PassportError(ValueError):
    pass


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


def encode(ch):
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

    while len(bits) % 8:
        bits.append(0)
    payload = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8))
    put(crc16(payload), 16)
    while len(bits) % 5:
        bits.append(0)

    values = [int("".join(map(str, bits[i:i + 5])), 2) for i in range(0, len(bits), 5)]
    out = ""
    for start in range(0, len(values), LINE_DATA):
        line = values[start:start + LINE_DATA]
        out += "".join(SYMBOLS[v] for v in line) + SYMBOLS[line_check(line)]
    return out


def lines(password):
    """Split a password into its display lines of up to 20 symbols."""
    return [password[i:i + 20] for i in range(0, len(password), 20)]


def decode(text):
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
            raise PassportError(f"'{c}' isn't a Passport symbol")
        values.append(SYMBOLS.index(u))

    data = []
    for n, start in enumerate(range(0, len(values), 20), 1):
        line = values[start:start + 20]
        if len(line) < 2:
            raise PassportError("wrong length")
        if line_check(line[:-1]) != line[-1]:
            raise PassportError(f"line {n} has a typo")
        data.extend(line[:-1])

    bits = [(v >> (4 - i)) & 1 for v in data for i in range(5)]
    pos = 0

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
    for _ in range(get(4)):
        s = get(4)
        ch["training"][s] = get(7)
    for _ in range(get(4)):
        pid = get(8)
        ch["powers"].append((pid, get(7)))
    for key in ("equipped", "pack"):
        for _ in range(get(3)):
            slot = get(3)
            ch[key][slot] = get(10)
    for _ in range(get(4)):
        eid = get(10)
        ch["echoes"].append((eid, get(2)))

    while pos % 8:
        if get(1):
            raise PassportError("checksum doesn't match")
    payload_end = pos
    stored = get(16)
    payload = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, payload_end, 8))
    if stored != crc16(payload) or any(bits[pos:]) or len(bits) - pos >= 5:
        raise PassportError("checksum doesn't match")
    return ch


def describe(ch):
    out = dict(ch)
    out["race"] = RACES[ch["race"]] if ch["race"] < len(RACES) else ch["race"]
    out["class"] = CLASSES[ch["class"]] if ch["class"] < len(CLASSES) else ch["class"]
    out["stats"] = dict(zip(STATS, ch["stats"]))
    out["tags"] = [SKILLS[s] for s in ch["tags"]]
    out["training"] = {SKILLS[s]: t for s, t in ch["training"].items()}
    return out


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "decode":
        try:
            print(json.dumps(describe(decode(sys.argv[2])), indent=2))
        except PassportError as e:
            sys.exit(f"Not a valid Passport: {e}")
    else:
        sys.exit(__doc__)
