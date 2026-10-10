"""Reference implementation of the Boarding Pass (docs/boarding.md, "Boarding passes").

Written from the docs, independently of core/src/passport.c. The Waystation website
issues passes; this makes them for tests and tools:

    python3 tools/passport/boarding.py issue "PASSPORT" DEPARTURE TICKET SEED [rewind]
    python3 tools/passport/boarding.py decode "PASS"

A pass is the trip and the character in one password, in the Passport alphabet and lines:
kind (4 bits, 8), Departure (16), ticket (32), the dice seed (16), a Rewind bit (1: a
replay of a Departure they have played), then the character exactly as a Passport holds
it, from its version on; zero bits to a whole byte, and a CRC-16 over all of it.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import passport  # noqa: E402
from passport import PassportError, to_bits  # noqa: E402

KIND = 8


def encode(departure, ticket, seed, rewind, ch):
    bits = (to_bits(KIND, 4) + to_bits(departure, 16) + to_bits(ticket, 32)
            + to_bits(seed, 16) + [int(bool(rewind))] + passport.field_bits(ch))
    data = passport.to_bytes(bits)
    out = [(b >> (7 - i)) & 1 for b in data for i in range(8)]
    return passport.symbols(out + to_bits(passport.crc16(data), 16))


def issue(passport_text, departure, ticket, seed, rewind=False):
    """What the Waystation hands out: a pass carrying this character, as they are now."""
    return encode(departure, ticket, seed, rewind, passport.decode(passport_text))


def decode(text):
    """The trip, and the character it carries (under "character")."""
    bits = passport.read_symbols(text, "Boarding Pass")

    def field(start, n):
        if start + n > len(bits):
            raise PassportError("password is too short")
        return int("".join(map(str, bits[start:start + n])), 2)

    if field(0, 4) != KIND:
        raise PassportError("that isn't a Boarding Pass, or it's from a different version "
                            "of the game")
    return {"departure": field(4, 16), "ticket": field(20, 32), "seed": field(52, 16),
            "rewind": bool(bits[68]), "character": passport.read_character(bits, 69)}


if __name__ == "__main__":
    if len(sys.argv) in (6, 7) and sys.argv[1] == "issue":
        rewind = len(sys.argv) == 7 and sys.argv[6] == "rewind"
        print(issue(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]),
                    rewind))
    elif len(sys.argv) == 3 and sys.argv[1] == "decode":
        try:
            p = decode(sys.argv[2])
        except PassportError as e:
            sys.exit(f"Not a valid Boarding Pass: {e}")
        p["character"] = passport.encode(p["character"])
        print(p)
    else:
        sys.exit(__doc__)
