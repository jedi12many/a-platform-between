"""Travelers and passwords for testing the decoders against each other: any traveler the
spec allows, travelers no game has (docs/passport-spec.md, "What's refused"), and what
the Python reference (tools/passport/) makes of a typed password. Used by
tests/passport/check_refusals.py (the C engine) and tests/cart/test_passwords.py (the
cartridge).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
import passport  # noqa: E402
import boarding  # noqa: E402
from passport import PassportError  # noqa: E402


def random_traveler(rnd):
    """Any traveler the spec allows: every field anywhere in its range, every list from
    empty to full (docs/passport-spec.md)."""
    ch = passport.new_character()
    ch["name"] = "".join(rnd.choice(passport.NAME_ALPHABET) for _ in range(rnd.randint(1, 8))).rstrip()
    ch["race"], ch["class"] = rnd.randrange(32), rnd.randrange(16)
    ch["level"], ch["xp"] = rnd.randint(1, 100), rnd.randrange(100)
    ch["stats"] = [rnd.randint(0, 100) for _ in range(6)]
    ch["stat_points"], ch["skill_points"] = rnd.randrange(256), rnd.randrange(256)
    ch["debt"], ch["flags"] = rnd.randrange(65536), rnd.randrange(128)
    ch["tags"] = sorted(rnd.sample(range(12), rnd.randint(0, 12)))
    big = rnd.random() < 0.3                                    # now and then, everything
    ch["training"] = {s: rnd.randint(1, 100) for s in rnd.sample(range(12), 12 if big else rnd.randint(0, 6))}
    ch["powers"] = [(rnd.randint(1, 255), rnd.randint(0, 100)) for _ in range(8 if big else rnd.randint(0, 4))]
    for key in ("equipped", "pack"):
        ch[key] = {slot: rnd.randint(1, 1023) for slot in rnd.sample(range(6), 6 if big else rnd.randint(0, 3))}
    ch["echoes"] = [(rnd.randint(1, 1023), rnd.randrange(4)) for _ in range(8 if big else rnd.randint(0, 4))]
    return ch


def impossible(rnd):
    """A traveler no game has, one rule broken (docs/passport-spec.md, "What's refused"),
    with a right checksum: and what was broken."""
    ch = random_traveler(rnd)
    rule = rnd.choice(["level 0", "level 101", "xp 100", "stat 101", "training 101",
                       "skill 12", "rank 101", "power 0", "9 powers",
                       "item slot 6", "item 0", "7 items", "Echo 0", "9 Echoes"])
    if rule == "level 0":
        ch["level"] = 0
    elif rule == "level 101":
        ch["level"] = rnd.randint(101, 127)
    elif rule == "xp 100":
        ch["xp"] = rnd.randint(100, 127)
    elif rule == "stat 101":
        ch["stats"][rnd.randrange(6)] = rnd.randint(101, 127)
    elif rule.startswith("training"):
        ch["training"][rnd.randrange(12)] = rnd.randint(101, 127)
    elif rule == "skill 12":
        ch["training"][rnd.randint(12, 15)] = rnd.randint(1, 100)
    elif rule == "rank 101":
        ch["powers"].append((rnd.randint(1, 255), rnd.randint(101, 127)))
        ch["powers"] = ch["powers"][-8:]
    elif rule == "power 0":
        ch["powers"] = (ch["powers"] + [(0, rnd.randint(0, 100))])[-8:]
    elif rule == "9 powers":
        ch["powers"] = [(rnd.randint(1, 255), rnd.randint(0, 100)) for _ in range(rnd.randint(9, 15))]
    elif rule == "item slot 6":
        ch[rnd.choice(["equipped", "pack"])][rnd.choice([6, 7])] = rnd.randint(1, 1023)
    elif rule == "item 0":
        ch[rnd.choice(["equipped", "pack"])][rnd.randrange(6)] = 0
    elif rule == "7 items":
        ch["pack"] = {slot: rnd.randint(1, 1023) for slot in rnd.sample(range(8), 7)}
    elif rule == "Echo 0":
        ch["echoes"] = (ch["echoes"] + [(0, rnd.randrange(4))])[-8:]
    else:
        ch["echoes"] = [(rnd.randint(1, 1023), rnd.randrange(4)) for _ in range(rnd.randint(9, 15))]
    return ch, rule


def reference(text):
    """What the reference makes of a typed password: ("ok", fields, pass) or (error, line).
    Its first symbol's top 4 bits say which it is, a Boarding Pass or a Passport, as a
    game tells them apart at one prompt."""
    first = next((c.upper() for c in text if c not in " -\n\r\t"), "0")
    first = {"O": "0", "I": "1", "L": "1"}.get(first, first)
    is_pass = first in passport.SYMBOLS and passport.SYMBOLS.index(first) >> 1 == boarding.KIND
    try:
        if is_pass:
            p = boarding.decode(text)
            return ("ok", p["character"], p)
        return ("ok", passport.decode(text), None)
    except PassportError as e:
        msg = str(e)
        if "isn't a" in msg:
            return ("symbol", 0)
        if "typo" in msg:
            return ("line", int(msg.split()[1]))
        if "too short" in msg or "length" in msg:
            return ("length", 0)
        if "version" in msg:
            return ("version", 0)
        return ("checksum", 0)


def damaged(rnd, text):
    kind = rnd.randrange(5)
    lines = passport.lines(text)
    if kind == 0:                                           # a symbol changed
        i = rnd.randrange(len(text))
        return text[:i] + rnd.choice([c for c in passport.SYMBOLS if c != text[i]]) + text[i + 1:]
    if kind == 1:                                           # one not in the alphabet
        i = rnd.randrange(len(text))
        return text[:i] + rnd.choice("U#*") + text[i + 1:]
    if kind == 2 and len(lines) > 1:                        # a line gone
        del lines[rnd.randrange(len(lines))]
        return "".join(lines)
    if kind == 3 and len(lines) > 1:                        # two lines swapped
        i = rnd.randrange(len(lines) - 1)
        lines[i], lines[i + 1] = lines[i + 1], lines[i]
        return "".join(lines)
    return text[:-rnd.randint(1, 3)]                         # the last symbols gone
