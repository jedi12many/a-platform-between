"""The cartridge's trip codes against the Python reference (cart/trip.s;
tools/passport/trip.py, docs/boarding.md "Trip code format").

    python3 tests/cart/test_trips.py IMAGE LABELS DEPARTURE [--cases N]

The cartridge boots on the emulator (tests/cart/run_cart.py) to the boarding desk, where
the Departure (DEPARTURE: its split files) is open and asset 1 staged; then its routines are
called as the game calls them. For random trips through that image (every flag and var,
the dice, the tune, health, rewards paid, the receipt's lists from empty to full), the
cartridge must write the reference's code, symbol for symbol, from the trip's state
(trip_make), or refuse to when the reference can't (over 255 symbols); and read the
reference's code back to the same state (trip_decode). Typed the forgiving way, the same.
Damaged codes (a symbol changed, one not in the alphabet, the last symbols gone, a line
gone), codes for another image or another pass, and codes that break a rule with a right
checksum, must be refused as the reference refuses them.
"""

import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests", "cart"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
import run_cart  # noqa: E402
import trip  # noqa: E402
from passport import SYMBOLS, PassportError  # noqa: E402

STOP = 0x0300
TEXT = 0xA0A5                       # RAM the desk doesn't use (a car's, on a trip)
CODE_AT = 0xA009                    # a car's code (cart/mem.inc's CAR_AT + 9)
HASH_AT = 0xB800 + 18               # the depot's image hash
R_XP, R_GAINED, R_LOST, R_ECHOES = 7, 13, 30, 47
CH_DEBT = 20
PW = {0: "ok", 1: "symbol", 2: "line", 3: "length", 4: "checksum", 5: "version",
      7: "image", 8: "pass"}

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def verdict(e):
    """The reference's refusal, as the cartridge's PW_ code names it."""
    s = str(e)
    for words, name in (("has a typo", "line"), ("symbol", "symbol"), ("wrong length", "length"),
                        ("checksum", "checksum"), ("isn't a trip code", "version"),
                        ("another Departure", "image"), ("another Boarding Pass", "pass")):
        if words in s:
            return name
    raise AssertionError(f"a refusal the test doesn't know: {s}")


def exports(path):
    """The linker's exports (its map file): names other modules see, which the labels
    file may have twice (a module's own of the same name)."""
    out, words = {}, None
    for line in open(path):
        if line.startswith("Exports list"):
            words = []
        elif words is not None:
            if line.startswith("Imports list"):
                break
            parts = line.split()
            for i in range(0, len(parts) - 2, 3):
                out[parts[i]] = int(parts[i + 1], 16)
    return out


class Cart:
    def __init__(self, image, labels):
        self.c = run_cart.C64(open(image, "rb").read(), run_cart.labels(labels))
        self.c.boot()
        self.c.run()                                        # to the desk's first key
        self.s = dict(self.c.syms)
        self.s.update(exports(labels.replace(".lbl", ".map")))
        self.ram = self.c.ram

    def call(self, routine, a=0, x=0, y=0):
        c, m = self.c, self.c.mpu
        ret = STOP - 1
        for b in (ret >> 8, ret & 0xFF):
            c.ram[0x100 + m.sp] = b
            m.sp = (m.sp - 1) & 0xFF
        m.a, m.x, m.y, m.pc = a, x, y, self.s[routine]
        steps = 0
        while m.pc != STOP:
            c.start, c.op, c.pc0 = m.processorCycles, c.mem[m.pc], m.pc
            m.step()
            c.raster()
            steps += 1
            if steps > 3_000_000:
                raise RuntimeError(f"{routine} never returned")
        return m.a, m.p & 1

    def w16(self, name, v, off=0):
        at = self.s[name] + off
        self.ram[at], self.ram[at + 1] = v & 0xFF, v >> 8

    def r16(self, name, off=0):
        at = self.s[name] + off
        return self.ram[at] | self.ram[at + 1] << 8

    def decode(self, text):
        for i, ch in enumerate(text.encode("ascii") + b"\0"):
            self.ram[TEXT + i] = ch
        a, _ = self.call("trip_decode", TEXT & 0xFF, TEXT >> 8)
        return PW.get(a, a)

    def state(self, image):
        """The trip's state as trip_decode left it, as the reference's dict."""
        r, s = self.ram, self.s
        flags = [r[s["flags"] + i // 8] >> (i % 8) & 1 for i in range(image["flags"])]
        rec = s["receipt"]

        def items(at):
            return [r[rec + at + 1 + 2 * i] | r[rec + at + 2 + 2 * i] << 8
                    for i in range(r[rec + at])]
        tune = r[s["music_now"]]
        return {"boarded": self.r16("trip_boarded"), "image": self.r16("trip_image"),
                "seed": self.r16("yard"), "scene": self.r16("trip_scene"), "flags": flags,
                "vars": [r[s["vars"] + i] for i in range(image["vars"])],
                "dice": self.r16("trip_dice"), "tune": None if tune == 0xFF else tune,
                "health": r[s["health"]], "gives": r[s["gives"]], "debt": self.r16("trip_debt"),
                "paid": [(r[s["paid_car"] + i],
                          (r[s["paid_lo"] + i] | r[s["paid_hi"] + i] << 8) - CODE_AT)
                         for i in range(r[s["paid_count"]])],
                "xp": r[rec + R_XP] | r[rec + R_XP + 1] << 8,
                "gained": items(R_GAINED), "lost": items(R_LOST),
                "echoes": [(r[rec + R_ECHOES + 1 + 4 * i] | r[rec + R_ECHOES + 2 + 4 * i] << 8,
                            r[rec + R_ECHOES + 3 + 4 * i], r[rec + R_ECHOES + 4 + 4 * i])
                           for i in range(r[rec + R_ECHOES])]}

    def make(self, t):
        """trip_make, from the trip's state set as t says. The code, or None (refused)."""
        r, s = self.ram, self.s
        r[s["vsp"]] = 0
        self.w16("boarded", t["boarded"])
        self.w16("yard", t["seed"])
        self.w16("scene_now", t["scene"])
        for i in range(64):
            r[s["flags"] + i] = 0
        for i, f in enumerate(t["flags"]):
            r[s["flags"] + i // 8] |= f << (i % 8)
        for i, v in enumerate(t["vars"]):
            r[s["vars"] + i] = v
        self.w16("rng", t["dice"])
        r[s["music_now"]] = 0xFF if t["tune"] is None else t["tune"]
        r[s["health"]], r[s["gives"]] = t["health"], t["gives"]
        self.w16("traveler", t["debt"], CH_DEBT)
        r[s["paid_count"]] = len(t["paid"])
        for i, (car, at) in enumerate(t["paid"]):
            r[s["paid_car"] + i] = car
            r[s["paid_lo"] + i], r[s["paid_hi"] + i] = (CODE_AT + at) & 0xFF, (CODE_AT + at) >> 8
        rec = s["receipt"]
        r[rec + R_XP], r[rec + R_XP + 1] = t["xp"] & 0xFF, t["xp"] >> 8
        for at, key in ((R_GAINED, "gained"), (R_LOST, "lost")):
            r[rec + at] = len(t[key])
            for i, item in enumerate(t[key]):
                r[rec + at + 1 + 2 * i], r[rec + at + 2 + 2 * i] = item & 0xFF, item >> 8
        r[rec + R_ECHOES] = len(t["echoes"])
        for i, (eid, state, was) in enumerate(t["echoes"]):
            r[rec + R_ECHOES + 1 + 4 * i:rec + R_ECHOES + 5 + 4 * i] = bytes(
                [eid & 0xFF, eid >> 8, state, was])
        _, carry = self.call("trip_make")
        if carry:
            return None
        at, out = self.s["code_text"], bytearray()
        while r[at + len(out)]:
            out.append(r[at + len(out)])
        return out.decode("ascii")


def random_trip(rng, image, boarded):
    """A trip through the image, every field anywhere in its bits."""
    return {"boarded": boarded, "image": image["hash"], "seed": rng.randrange(65536),
            "scene": rng.randrange(len(image["scenes"])),
            "flags": [rng.randrange(2) for _ in range(image["flags"])],
            "vars": [rng.randrange(256) for _ in range(image["vars"])],
            "dice": rng.randrange(1, 65536),
            "tune": rng.choice([None] + list(range(image["tunes"]))),
            "health": rng.randrange(256), "gives": rng.randrange(4), "debt": rng.randrange(65536),
            "paid": [(rng.randrange(64), rng.randrange(8192))
                     for _ in range(rng.choice([0, 1, 3, rng.randrange(33), 32]))],
            "xp": rng.randrange(65536),
            "gained": [rng.randrange(1024) for _ in range(rng.randrange(9))],
            "lost": [rng.randrange(1024) for _ in range(rng.randrange(9))],
            "echoes": [(rng.randrange(1024), rng.randrange(4), rng.randrange(4))
                       for _ in range(rng.randrange(9))]}


def forgiving(rng, code):
    """The code as a player might type it: in lines, small letters, dashes, O for 0..."""
    out = []
    for i, ch in enumerate(code):
        if i and i % 20 == 0:
            out.append(rng.choice([" ", "\n", " - "]))
        if ch == "0" and rng.random() < 0.3:
            ch = "O"
        elif ch == "1" and rng.random() < 0.3:
            ch = rng.choice("IL")
        out.append(ch.lower() if rng.random() < 0.5 else ch)
    return "".join(out)


def check_refusal(cart, image, boarded, text, what):
    try:
        trip.decode(text, image, boarded)
        want = "ok"
    except PassportError as e:
        want = verdict(e)
    cart.w16("boarded", boarded)                            # (boarded with this)
    got = cart.decode(text)
    if got != want:
        fail(f"{what}: the reference says {want}, the cartridge {got}: {text!r}")
    elif want == "line":
        line = cart.ram[cart.s["pw_bad_line"]]
        try:
            trip.decode(text, image, boarded)
        except PassportError as e:
            if f"line {line} " not in str(e):
                fail(f"{what}: the cartridge says line {line}; the reference: {e}")


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    cases = int(argv[argv.index("--cases") + 1]) if "--cases" in argv else 60
    cart = Cart(argv[1], argv[2])
    d, cars = trip.read_image(argv[3])
    image = trip.image_facts(d, cars)
    if cart.ram[HASH_AT] | cart.ram[HASH_AT + 1] << 8 != image["hash"]:
        fail("the cartridge's Departure isn't the one given")
        return 1
    rng = random.Random(64)
    made = read = refused = long_ones = 0
    big = dict(image, flags=300)            # an image with many flags: some trips too long
    for n in range(cases + cases // 4):
        boarded = rng.randrange(65536)
        if n == cases:                      # (the cartridge told so: the depot's count)
            image = big
            cart.w16("flag_count", 300)
        t = random_trip(rng, image, boarded)
        if image is big and n % 2:          # every list full: past 255 symbols
            t["paid"] = [(rng.randrange(64), rng.randrange(8192)) for _ in range(32)]
            for key in ("gained", "lost", "echoes"):
                t[key] = (t[key] * 9)[:8] or t[key]
        try:
            code = trip.encode(t)
        except PassportError:
            code = None
        got = cart.make(t)
        if got != code:
            fail(f"trip {n}: the cartridge writes {got}, the reference {code}")
            continue
        if code is None:
            long_ones += 1
            continue
        made += 1
        cart.w16("boarded", boarded)
        for text in (code, forgiving(rng, code)):
            if cart.decode(text) != "ok":
                fail(f"trip {n}: the cartridge refuses {text!r}: {cart.decode(text)}")
                break
            state = cart.state(image)
            if state != trip.decode(code, image, boarded):
                fail(f"trip {n}: the cartridge reads {state}, the reference "
                     f"{trip.decode(code, image, boarded)}")
                break
            read += 1
        # Damaged, or not this trip's.
        i = rng.randrange(len(code))
        damaged = [code[:i] + SYMBOLS[(SYMBOLS.index(code[i]) + rng.randrange(1, 32)) % 32]
                   + code[i + 1:],
                   code[:i] + rng.choice("U!*") + code[i + 1:],
                   code[:-rng.randrange(1, 4)],
                   code[:20] + code[40:] if len(code) > 40 else code[20:],
                   code + "00"]
        for k, text in enumerate(damaged):
            check_refusal(cart, image, boarded, text, f"trip {n}, damage {k}")
            refused += 1
        check_refusal(cart, image, boarded ^ 0x100, code, f"trip {n}, another pass")
        other = dict(t, image=t["image"] ^ 1)
        check_refusal(cart, image, boarded, trip.encode(other), f"trip {n}, another image")
        for key, bad in (("scene", 0xFFF), ("dice", 0), ("tune", 62)):
            check_refusal(cart, image, boarded, trip.encode(dict(t, **{key: bad})),
                          f"trip {n}, {key} {bad}")
        refused += 5
    if not failures:
        print(f"ok   trip codes: the cartridge writes the reference's ({made} trips, {long_ones} "
              f"too long for either), reads them back ({read}, typed every way), and refuses "
              f"as the reference refuses ({refused})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
