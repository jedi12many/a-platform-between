"""Reference implementation of the Travel Stamp (docs/boarding.md, "Travel Stamp format").

Written from the docs, independently of core/src/passport.c. A Travel Stamp is a receipt
as a password: retro and tabletop players type it in at the Waystation website, which
decodes it with this, checks it against the ticket and the reward manifest, and applies it
with tools/passport/receipt.py.

    python3 tools/passport/stamp.py decode "STAMP"

Receipts are dicts as receipt.py takes them, plus "departure", "ticket" and "outcome".
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from passport import (STAMP_LONGEST, LINE_DATA, SYMBOLS, PassportError, crc16, line_check,  # noqa: E402
                      symbols, to_bits)

VERSION = 1


RECEIPT_MAX = 8                 # entries a receipt list holds (APB_RECEIPT_MAX)


def encode(r):
    bits = to_bits(VERSION, 4) + to_bits(r["departure"], 16) + to_bits(r["ticket"], 32)
    bits += to_bits(r["outcome"], 1) + to_bits(r["xp"], 16)
    added = r["debt_added"] > 0
    bits += to_bits(int(added), 1) + to_bits(r["debt_added"] if added else r["debt_paid"], 16)
    for key in ("gained", "lost"):
        bits += to_bits(len(r[key]), 4)
        for item in r[key]:
            bits += to_bits(item, 10)
    bits += to_bits(len(r["echoes"]), 4)
    for eid, state, was in r["echoes"]:
        bits += to_bits(eid, 10) + to_bits(state, 2) + to_bits(was, 2)
    while len(bits) % 8:
        bits.append(0)
    payload = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8))
    return symbols(bits + to_bits(crc16(payload), 16))


def decode(text):
    """The receipt in a stamp. PassportError names the line of a typo."""
    values = []
    for c in text:
        if c in " -\n\r\t":
            continue
        u = {"O": "0", "I": "1", "L": "1"}.get(c.upper(), c.upper())
        if u not in SYMBOLS:
            raise PassportError(f"'{c}' isn't a Travel Stamp symbol")
        if len(values) == STAMP_LONGEST:
            raise PassportError("the stamp is the wrong length")
        values.append(SYMBOLS.index(u))
    data = []
    for n, start in enumerate(range(0, len(values), LINE_DATA + 1), 1):
        line = values[start:start + LINE_DATA + 1]
        if len(line) < 2:
            raise PassportError("the stamp is the wrong length")
        if line_check(line[:-1]) != line[-1]:
            raise PassportError(f"line {n} has a typo")
        data += line[:-1]
    bits = [(v >> (4 - i)) & 1 for v in data for i in range(5)]
    pos = 0

    def get(n):
        nonlocal pos
        if pos + n > len(bits):
            raise PassportError("the stamp is too short")
        v = int("".join(map(str, bits[pos:pos + n])), 2)
        pos += n
        return v

    if get(4) != VERSION:
        raise PassportError("made by a different version of the game")
    r = {"departure": get(16), "ticket": get(32), "outcome": get(1), "xp": get(16)}
    added, amount = get(1), get(16)
    r["debt_added"], r["debt_paid"] = (amount, 0) if added else (0, amount)
    # A receipt's lists hold 8 at most (docs/boarding.md): a longer one is refused as it's
    # read, as the C engine refuses it.
    for key in ("gained", "lost"):
        n = get(4)
        if n > RECEIPT_MAX:
            raise PassportError("the stamp's checksum doesn't match")
        r[key] = [get(10) for _ in range(n)]
    r["echoes"] = []
    n = get(4)
    if n > RECEIPT_MAX:
        raise PassportError("the stamp's checksum doesn't match")
    for _ in range(n):
        r["echoes"].append((get(10), get(2), get(2)))
    while pos % 8:
        if get(1):
            raise PassportError("the stamp's checksum doesn't match")
    end = pos
    stored = get(16)
    payload = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, end, 8))
    if stored != crc16(payload):
        raise PassportError("the stamp's checksum doesn't match")
    if len(bits) - pos >= 5:
        raise PassportError("the stamp is the wrong length")
    if any(bits[pos:]):
        raise PassportError("the stamp's checksum doesn't match")
    return r


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "decode":
        try:
            print(json.dumps(decode(sys.argv[2])))
        except PassportError as e:
            sys.exit(f"Not a valid Travel Stamp: {e}")
    else:
        sys.exit(__doc__)
