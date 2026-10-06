"""Reference implementation of the Boarding Pass (docs/boarding.md, "Boarding passes").

Written from the docs, independently of core/src/passport.c. The Waystation website
issues passes; until it exists, this makes them for testing:

    python3 tools/passport/boarding.py issue "PASSPORT" DEPARTURE TICKET SEED
    python3 tools/passport/boarding.py decode PASS

A pass is one line of 18 symbols in the Passport alphabet: version (4 bits), Departure
(16), ticket (32), the Passport's check of the character as boarded (16), the dice seed
(16), a zero bit, then the line's check symbol.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import passport  # noqa: E402
from passport import PassportError, SYMBOLS, line_check, to_bits  # noqa: E402

VERSION = 1
LENGTH = 18


def encode(departure, ticket, check, seed):
    bits = (to_bits(VERSION, 4) + to_bits(departure, 16) + to_bits(ticket, 32)
            + to_bits(check, 16) + to_bits(seed, 16) + [0])
    return passport.symbols(bits)


def issue(passport_text, departure, ticket, seed):
    """What the Waystation hands out: a pass for this character, as they are now."""
    return encode(departure, ticket, passport.check(passport.decode(passport_text)), seed)


def decode(text):
    values = []
    for c in text:
        if c in " -\n\r\t":
            continue
        u = {"O": "0", "I": "1", "L": "1"}.get(c.upper(), c.upper())
        if u not in SYMBOLS:
            raise PassportError(f"'{c}' isn't a Boarding Pass symbol")
        values.append(SYMBOLS.index(u))
    if len(values) != LENGTH:
        raise PassportError(f"a Boarding Pass has {LENGTH} symbols, not {len(values)}")
    if line_check(values[:-1]) != values[-1]:
        raise PassportError("there's a typo")
    bits = [(v >> (4 - i)) & 1 for v in values[:-1] for i in range(5)]

    def field(start, n):
        return int("".join(map(str, bits[start:start + n])), 2)

    if field(0, 4) != VERSION:
        raise PassportError("made by a different version of the game")
    if bits[84]:
        raise PassportError("there's a typo")
    return {"departure": field(4, 16), "ticket": field(20, 32), "check": field(52, 16),
            "seed": field(68, 16)}


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "issue":
        print(issue(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])))
    elif len(sys.argv) == 3 and sys.argv[1] == "decode":
        try:
            print(decode(sys.argv[2]))
        except PassportError as e:
            sys.exit(f"Not a valid Boarding Pass: {e}")
    else:
        sys.exit(__doc__)
