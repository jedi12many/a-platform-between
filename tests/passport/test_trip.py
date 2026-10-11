"""The trip code reference (tools/passport/trip.py, docs/boarding.md "Trip code format"):
random trips come back as they went in; a typo names its line; a code for another image
or pass, a broken rule, a bad checksum and the wrong length are each refused."""

import os
import random
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
import trip  # noqa: E402
from passport import SYMBOLS, PassportError  # noqa: E402

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL", msg)


def random_image(rng):
    scenes = [(rng.randrange(3), rng.randrange(4000), rng.choice([0xFFFF, rng.randrange(400)]))
              for _ in range(rng.randrange(1, 60))]
    scenes[0] = (0, 0, 10)
    return {"flags": rng.randrange(0, 80), "vars": rng.randrange(0, 5), "hash": rng.randrange(65536),
            "cars": 3, "tunes": rng.randrange(0, 6), "scenes": scenes}


def random_trip(rng, image):
    menus = [i for i, s in enumerate(image["scenes"]) if s[2] != 0xFFFF]
    return {"boarded": rng.randrange(65536), "image": image["hash"], "seed": rng.randrange(65536),
            "scene": rng.choice(menus), "flags": [rng.randrange(2) for _ in range(image["flags"])],
            "vars": [rng.randrange(256) for _ in range(image["vars"])],
            "dice": rng.randrange(1, 65536),
            "tune": rng.choice([None] + list(range(image["tunes"]))),
            "health": rng.randrange(256), "gives": rng.randrange(4), "debt": rng.randrange(65536),
            "paid": [(rng.randrange(3), rng.randrange(8192)) for _ in range(rng.randrange(33))],
            "xp": rng.randrange(65536),
            "gained": [rng.randrange(1024) for _ in range(rng.randrange(9))],
            "lost": [rng.randrange(1024) for _ in range(rng.randrange(9))],
            "echoes": [(rng.randrange(1024), rng.randrange(4), rng.randrange(4))
                       for _ in range(rng.randrange(9))]}


def refused(code, image, boarded, want):
    try:
        trip.decode(code, image, boarded)
    except PassportError as e:
        if want not in str(e):
            fail(f"{code}: refused with '{e}', not '{want}'")
        return
    fail(f"{code}: not refused (wanted '{want}')")


rng = random.Random(9)
for n in range(400):
    image = random_image(rng)
    t = random_trip(rng, image)
    code = trip.encode(t)
    got = trip.decode(code, image, t["boarded"])
    got["paid"] = [tuple(p) for p in got["paid"]]
    if got != t:
        fail(f"trip {n} came back different: {t} / {got}")
    # spaces, dashes and line breaks don't matter; nor do O, I, L for 0, 1, 1
    spaced = "\n".join(code[i:i + 20] for i in range(0, len(code), 20)).lower()
    if trip.decode(spaced, image, t["boarded"])["scene"] != t["scene"]:
        fail(f"trip {n}: its lines weren't read")
    # a typo: one symbol changed, and its line is named
    i = rng.randrange(len(code))
    typo = code[:i] + SYMBOLS[(SYMBOLS.index(code[i]) + rng.randrange(1, 32)) % 32] + code[i + 1:]
    refused(typo, image, t["boarded"], f"line {i // 20 + 1} has a typo")
    refused(code, image, t["boarded"] ^ 1, "another Boarding Pass")
    other = dict(image, hash=image["hash"] ^ 1)
    refused(code, other, t["boarded"], "another Departure")
    fewer = dict(image, scenes=image["scenes"][:t["scene"]])
    refused(code, fewer, t["boarded"], "checksum")
    refused(code[:-1], image, None, "")
    refused(code + "00", image, None, "")
    refused(code[:-2] + "-?", image, None, "isn't a trip code symbol")

# Another kind of password isn't a trip code.
image = random_image(rng)
refused("8V40000000000K60M2A4A50200810HJB", image, None, "")
if failures:
    sys.exit(f"trip codes: {failures} failures")
print("ok  trip codes: 400 random trips round-trip, and every damaged one is refused")
