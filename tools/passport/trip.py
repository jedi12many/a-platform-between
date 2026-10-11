"""Reference implementation of the trip code (docs/boarding.md, "Trip code format").

Written from the docs, independently of cart/trip.s. A trip code is a trip saved as a
password, where there's nowhere else to save it: the cartridge shows one at a menu, and
takes it back after boarding with the same pass.

    python3 tools/passport/trip.py decode "CODE" IMAGE.apd|SPLITDIR
    python3 tools/passport/trip.py from-save SAVE IMAGE.apd|SPLITDIR

A trip is a dict: "boarded" (the CRC-16 the pass or Passport ends in), "image" (the image's
hash), "seed", "scene", "flags" (a list of 0/1), "vars", "dice", "tune" (None or an index),
"health", "gives", "debt", "paid" (a list of (car, offset)), "xp", "gained", "lost",
"echoes" (a list of (id, state, was)).
"""

import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "qsc"))
from passport import PASS_LONGEST, PassportError, crc16, read_symbols, symbols, to_bits, to_bytes  # noqa: E402

KIND = 9
NO_TUNE = 63
PAID_MAX = 32                   # APB_VM_REWARD_SITES
RECEIPT_MAX = 8                 # APB_RECEIPT_MAX
LONGEST = 255                   # symbols: a code is this long at most (the cartridge's room)


def encode(t):
    bits = (to_bits(KIND, 4) + to_bits(t["boarded"], 16) + to_bits(t["image"], 16)
            + to_bits(t["seed"], 16) + to_bits(t["scene"], 12))
    bits += [int(bool(f)) for f in t["flags"]]
    for v in t["vars"]:
        bits += to_bits(v, 8)
    bits += to_bits(t["dice"], 16)
    bits += to_bits(NO_TUNE if t["tune"] is None else t["tune"], 6)
    bits += to_bits(t["health"], 8) + to_bits(t["gives"], 2) + to_bits(t["debt"], 16)
    bits += to_bits(len(t["paid"]), 6)
    for car, at in t["paid"]:
        bits += to_bits(car, 6) + to_bits(at, 13)
    bits += to_bits(t["xp"], 16)
    for key in ("gained", "lost"):
        bits += to_bits(len(t[key]), 4)
        for item in t[key]:
            bits += to_bits(item, 10)
    bits += to_bits(len(t["echoes"]), 4)
    for eid, state, was in t["echoes"]:
        bits += to_bits(eid, 10) + to_bits(state, 2) + to_bits(was, 2)
    data = to_bytes(bits)
    out = [(b >> (7 - i)) & 1 for b in data for i in range(8)]
    code = symbols(out + to_bits(crc16(data), 16))
    if len(code) > LONGEST:
        raise PassportError("too long to save: a trip code is 255 symbols at most")
    return code


def decode(text, image, boarded=None):
    """The trip in a code, for the image (as image_facts gives it). With `boarded`, a code
    for another pass is refused. PassportError says what's wrong, as the game does."""
    bits = read_symbols(text, "trip code", LONGEST)
    pos = 0

    def get(n):
        nonlocal pos
        if pos + n > len(bits):
            raise PassportError("wrong length")
        v = int("".join(map(str, bits[pos:pos + n])), 2)
        pos += n
        return v

    def broken():
        return PassportError("the checksum doesn't match")

    if get(4) != KIND:
        raise PassportError("that isn't a trip code")
    t = {"boarded": get(16), "image": get(16), "seed": get(16), "scene": get(12)}
    t["flags"] = [get(1) for _ in range(image["flags"])]
    t["vars"] = [get(8) for _ in range(image["vars"])]
    t["dice"] = get(16)
    tune = get(6)
    t["tune"] = None if tune == NO_TUNE else tune
    t["health"], t["gives"], t["debt"] = get(8), get(2), get(16)
    n = get(6)
    if n > PAID_MAX:
        raise broken()
    t["paid"] = [(get(6), get(13)) for _ in range(n)]
    t["xp"] = get(16)
    for key in ("gained", "lost"):
        n = get(4)
        if n > RECEIPT_MAX:
            raise broken()
        t[key] = [get(10) for _ in range(n)]
    n = get(4)
    if n > RECEIPT_MAX:
        raise broken()
    t["echoes"] = [(get(10), get(2), get(2)) for _ in range(n)]
    while pos % 8:
        if get(1):
            raise broken()
    end = pos
    stored = get(16)
    payload = bytes(int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, end, 8))
    if stored != crc16(payload):
        raise broken()
    if len(bits) - pos >= 5 or any(bits[pos:]):
        raise PassportError("wrong length")
    # What's checked against the image, once the code itself is sound.
    if t["image"] != image["hash"]:
        raise PassportError("that code is for another Departure")
    if boarded is not None and t["boarded"] != boarded:
        raise PassportError("that code is for another Boarding Pass")
    if (t["scene"] >= len(image["scenes"]) or t["dice"] == 0
            or (t["tune"] is not None and t["tune"] >= image["tunes"])):
        raise broken()
    return t


def resumable(t, image):
    """Whether the trip can go on: its scene has a menu. (Only once its car is loaded can
    a game know; one that can't goes on derails, as a damaged save does.)"""
    return image["scenes"][t["scene"]][2] != 0xFFFF


# ---- images and saves -------------------------------------------------------------------

def read_image(path):
    """An image's depot and cars: an .apd, or a directory of split files (qsc --split)."""
    import image as qimage
    if os.path.isdir(path):
        with open(os.path.join(path, "DEPOT"), "rb") as f:
            depot = f.read()
        d = qimage.read_depot(depot)
        cars = []
        for i in range(64):
            p = os.path.join(path, f"CAR{i:02d}")
            if not os.path.exists(p):
                break
            with open(p, "rb") as f:
                cars.append(f.read())
        return d, cars
    with open(path, "rb") as f:
        depot, cars = qimage.split_apd(f.read())
    return qimage.read_depot(depot), cars


def image_facts(d, cars):
    """What a trip code needs of an image: its counts, hash, and each scene's car, offset
    (in the car's code) and menu offset."""
    import image as qimage
    codes = [qimage.read_car(c, i, d["pairs"])["code"] for i, c in enumerate(cars)]
    scenes = []
    for car, at in d["directory"]:
        scenes.append((car, at, struct.unpack_from("<H", codes[car], at)[0]))
    return {"flags": d["flags"], "vars": d["vars"], "hash": d["hash"], "cars": len(cars),
            "tunes": len(d["music"]), "scenes": scenes}


def from_save(save, d, image, boarded):
    """The trip code a C engine save (vm.c's save_game, version 4) makes: the same trip, at
    the same menu. `boarded` is the CRC-16 the pass ended in."""
    import passport
    pos = 0

    def get(fmt):
        nonlocal pos
        v = struct.unpack_from("<" + fmt, save, pos)
        pos += struct.calcsize(fmt)
        return v[0]

    if save[:3] != b"AS\x04" or crc16(save[:-2]) != struct.unpack_from("<H", save, len(save) - 2)[0]:
        raise ValueError("not a version 4 save")
    pos = 3
    get("H")
    get("H")
    car, menu_at = get("B"), get("H")
    for _ in range(get("B")):
        get("HH")
    if get("B"):
        raise ValueError("the save has things on the expression stack")
    raw = [get("B") for _ in range((d["flags"] + 7) // 8)]
    flags = [(raw[i // 8] >> (i % 8)) & 1 for i in range(d["flags"])]
    vars_ = [get("B") for _ in range(d["vars"])]
    dice, seed, tune = get("H"), get("H"), get("B")
    get("H")                                    # Debt at boarding: the pass has it
    health, gives = get("B"), get("B")
    paid = [(get("B"), get("H")) for _ in range(get("B"))]
    get("H")
    get("I")
    get("B")
    xp = get("H")
    get("H")
    get("H")
    gained = [get("H") for _ in range(get("B"))]
    lost = [get("H") for _ in range(get("B"))]
    echoes = [(get("H"), get("B"), get("B")) for _ in range(get("B"))]
    # The Passport's text is in the platform's own characters: the C64's capitals are
    # PETSCII's $C1-$DA.
    text = "".join(chr(b - 0x80) if 0xC1 <= b <= 0xDA else chr(b)
                   for b in save[pos + 1:pos + 1 + save[pos]])
    ch = passport.decode(text)
    # The scene whose code holds the menu: the last one starting at or before it in its car.
    scene = max((s for s, (c, at, _) in enumerate(image["scenes"]) if c == car and at <= menu_at),
                key=lambda s: image["scenes"][s][1])
    return encode({"boarded": boarded, "image": image["hash"], "seed": seed, "scene": scene,
                   "flags": flags, "vars": vars_, "dice": dice,
                   "tune": None if tune == 0xFF else tune, "health": health, "gives": gives,
                   "debt": ch["debt"], "paid": paid, "xp": xp, "gained": gained, "lost": lost,
                   "echoes": echoes})


def boarded_crc(text):
    """The CRC-16 a pass or Passport ends in. Its bits are whole bytes, the CRC, then fewer
    than 5 bits of padding to a whole symbol."""
    bits = read_symbols(text, "Boarding Pass", PASS_LONGEST)
    end = len(bits) - len(bits) % 8
    return int("".join(map(str, bits[end - 16:end])), 2)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "decode":
        d, cars = read_image(sys.argv[3])
        try:
            print(json.dumps(decode(sys.argv[2], image_facts(d, cars))))
        except PassportError as e:
            sys.exit(f"Not a valid trip code: {e}")
    elif len(sys.argv) == 5 and sys.argv[1] == "from-save":
        d, cars = read_image(sys.argv[3])
        with open(sys.argv[2], "rb") as f:
            print(from_save(f.read(), d, image_facts(d, cars), int(sys.argv[4], 0)))
    else:
        sys.exit(__doc__)
