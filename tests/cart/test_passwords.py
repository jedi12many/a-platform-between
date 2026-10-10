"""The cartridge's Passports and Boarding Passes against the Python reference
(cart/password.s, cart/passport.s; tools/passport/passport.py and boarding.py).

    python3 tests/cart/test_passwords.py IMAGE LABELS [--cases N]

The cartridge boots on the emulator (tests/cart/run_cart.py) to its first wait for a key;
then its routines are called as the game calls them. For random travelers (every field
anywhere in its bits, every list from empty to full) and Boarding Passes, the reference's
password must decode to the reference's fields, and the cartridge must write a Passport the
reference writes, symbol for symbol. Typed the forgiving way (small letters, dashes,
spaces, O for 0, I and L for 1), they must read the same. Damaged ones (a symbol changed,
one that isn't in the alphabet, a line or the last symbols gone, two lines swapped) must
be refused as the reference refuses them: a typo on the right line, an unknown symbol,
too short, a checksum, a different version. So must travelers no game has, with right
checksums (a list too long, a repeat, an empty entry, a number out of range: the spec's
"What's refused"). And a traveler with a field too big must not be written.
"""

import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests", "cart"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
sys.path.insert(0, os.path.join(ROOT, "tests", "passport"))
import run_cart  # noqa: E402
import passport  # noqa: E402
from cases import damaged, impossible, random_traveler, reference  # noqa: E402
import boarding  # noqa: E402

STOP = 0x0300                       # a routine "returns" here: the run stops
TEXT, OUT = 0xA000, 0xA800          # RAM the game doesn't use yet
PW = {"ok": 0, "symbol": 1, "line": 2, "length": 3, "checksum": 4, "version": 5, "too big": 6}
NAMES = {v: k for k, v in PW.items()}

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


class Cart:
    def __init__(self, image, labels):
        self.c = run_cart.C64(open(image, "rb").read(), run_cart.labels(labels))
        self.c.boot()
        self.c.run()                                        # to its first wait for a key
        self.s = self.c.syms

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
        return m.a

    def text(self, at, s):
        for i, ch in enumerate(s.encode("ascii") + b"\0"):
            self.c.ram[at + i] = ch

    def read_text(self, at):
        out = bytearray()
        while self.c.ram[at + len(out)]:
            out.append(self.c.ram[at + len(out)])
        return out.decode("ascii")

    def decode(self, s):
        self.text(TEXT, s)
        return self.call("password_decode", TEXT & 0xFF, TEXT >> 8)

    def record(self):
        t = self.s["traveler"]
        return bytes(self.c.ram[t:t + 150])


def record_of(ch):
    """The cartridge's record of a traveler (cart/char.inc), from the reference's fields."""
    r = bytearray(150)
    r[0:8] = ch["name"].upper()[:8].ljust(8).encode("ascii")
    r[8], r[9], r[10], r[11] = ch["race"], ch["class"], ch["level"], ch["xp"]
    r[12:18] = bytes(ch["stats"])
    r[18], r[19] = ch["stat_points"], ch["skill_points"]
    r[20:22] = ch["debt"].to_bytes(2, "little")
    r[22] = ch["flags"]
    r[23:25] = sum(1 << s for s in ch["tags"]).to_bytes(2, "little")
    for s, t in ch["training"].items():
        r[25 + s] = t
    r[41] = len(ch["powers"])
    for i, (pid, rank) in enumerate(ch["powers"]):
        r[42 + 2 * i], r[43 + 2 * i] = pid, rank
    for at, key in ((72, "equipped"), (88, "pack")):
        r[at:at + 16] = b"\xff" * 16
        for slot, item in ch[key].items():
            r[at + 2 * slot:at + 2 * slot + 2] = item.to_bytes(2, "little")
    r[104] = len(ch["echoes"])
    for i, (eid, state) in enumerate(ch["echoes"]):
        r[105 + 3 * i:107 + 3 * i] = eid.to_bytes(2, "little")
        r[107 + 3 * i] = state
    return bytes(r)


def check_one(cart, text, what):
    want = reference(text)
    got = cart.decode(text)
    if want[0] != NAMES.get(got):
        fail(f"{what}: the reference says {want[0]}, the cartridge {NAMES.get(got, got)}: {text!r}")
        return False
    if want[0] == "line":
        line = cart.c.ram[cart.s["pw_bad_line"]]
        if line != want[1]:
            fail(f"{what}: a typo on line {want[1]}, the cartridge says {line}")
            return False
    if want[0] != "ok":
        return True
    if cart.record() != record_of(want[1]):
        fail(f"{what}: the traveler differs:\n  got  {cart.record().hex()}\n  want {record_of(want[1]).hex()}")
        return False
    kind = cart.c.ram[cart.s["password_kind"]]
    if want[2] is not None:
        p = want[2]
        at = cart.s["pass"]
        got_pass = bytes(cart.c.ram[at:at + 9])
        want_pass = (p["departure"].to_bytes(2, "little") + p["ticket"].to_bytes(4, "little")
                     + p["seed"].to_bytes(2, "little") + bytes([int(p["rewind"])]))
        if kind != 8 or got_pass != want_pass:
            fail(f"{what}: the pass differs: {got_pass.hex()} vs {want_pass.hex()}")
            return False
    elif kind != 2:
        fail(f"{what}: a Passport read as kind {kind}")
        return False
    return True


def forgiving(rnd, text):
    """The password typed as a player might: small letters, dashes, O, I and L."""
    out = []
    for i, ch in enumerate(text):
        if i and i % 4 == 0 and rnd.random() < 0.5:
            out.append(rnd.choice(" -"))
        if ch == "0" and rnd.random() < 0.5:
            ch = "O"
        elif ch == "1" and rnd.random() < 0.5:
            ch = rnd.choice("IL")
        out.append(ch.lower() if rnd.random() < 0.5 else ch)
    return "".join(out)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cases = int(argv[argv.index("--cases") + 1]) if "--cases" in argv else 60
    cart = Cart(argv[1], argv[2])
    rnd = random.Random(1979)
    n = {"travelers": 0, "passes": 0, "typed": 0, "damaged": 0, "written": 0, "impossible": 0, "long": 0}
    for k in range(cases):
        ch = random_traveler(rnd)
        text = passport.encode(ch)
        if check_one(cart, text, f"Passport {k}"):
            n["travelers"] += 1
        # Written back: the reference's text, symbol for symbol.
        status = cart.call("passport_encode", OUT & 0xFF, OUT >> 8)
        if status != 0 or cart.read_text(OUT) != text:
            fail(f"Passport {k}: written as {cart.read_text(OUT)!r} ({NAMES.get(status)}), not {text!r}")
        else:
            n["written"] += 1
        p = boarding.encode(rnd.randrange(65536), rnd.randrange(1 << 32), rnd.randrange(65536),
                            rnd.random() < 0.5, ch)
        if check_one(cart, p, f"pass {k}"):
            n["passes"] += 1
        if check_one(cart, forgiving(rnd, rnd.choice([text, p])), f"typed {k}"):
            n["typed"] += 1
        for _ in range(3):
            if check_one(cart, damaged(rnd, rnd.choice([text, p])), f"damaged {k}"):
                n["damaged"] += 1
    # Travelers no game has, with right checksums: refused as the reference refuses them.
    for k in range(cases // 2):
        ch, rule = impossible(rnd)
        text = passport.encode(ch)
        p = boarding.encode(1, 2, 3, False, ch)
        if (check_one(cart, text, f"impossible Passport {k} ({rule})")
                and check_one(cart, p, f"impossible pass {k} ({rule})")
                and reference(text)[0] in ("checksum", "length")):
            n["impossible"] += 1
        else:
            fail(f"impossible traveler {k} ({rule}) not refused by both")
    # Longer than any there can be (a line of zeros added, its check right): the wrong
    # length, as the reference says.
    for k in range(10):
        text = rnd.choice([passport.encode, lambda ch: boarding.encode(1, 2, 3, False, ch)])(
            random_traveler(rnd))
        while len(text) <= (passport.PASS_LONGEST if text[0] in "GH" else passport.PASSPORT_LONGEST):
            text += "0" * 20
        if check_one(cart, text, f"too long {k}") and reference(text)[0] == "length":
            n["long"] += 1
        else:
            fail(f"too long {k}: not the wrong length")
    # The real thing: Kestrel's pass, as the C64's tests type it.
    kestrel = "G0000000FG87R49CPEJZ 8NG0M020AN8F2THP800E 00000016C184M8A0400W G0FZKR7"
    if check_one(cart, kestrel, "Kestrel's pass"):
        n["passes"] += 1
    # Too big to write: a stat of 200.
    cart.decode(passport.encode(random_traveler(rnd)))
    cart.c.ram[cart.s["traveler"] + 12] = 200
    if cart.call("passport_encode", OUT & 0xFF, OUT >> 8) != PW["too big"]:
        fail("a stat of 200 was written into a Passport")
    else:
        print("ok   a traveler with a field too big for its bits isn't written")
    print(f"ok   {n['travelers']} Passports and {n['passes']} Boarding Passes read as the reference "
          f"reads them; {n['written']} Passports written as it writes them; {n['typed']} typed the "
          f"forgiving way; {n['damaged']} damaged ones refused as it refuses them; "
          f"{n['impossible']} travelers no game has refused by both; {n['long']} too long")
    print(f"cart passwords: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
