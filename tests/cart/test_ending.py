"""A trip's end on the cartridge (cart/stamp.s, qr.s, qrview.s; the ending asset) against
the references.

    python3 tests/cart/test_ending.py IMAGE LABELS [--cases N]

The cartridge boots on the emulator (tests/cart/run_cart.py) to its first wait for a key;
the ending asset is fetched into the staging RAM, as play.s fetches it, and its routines
called. For random receipts (every field anywhere in its range, every list from empty to
full), the Travel Stamp the cartridge writes must read back, field for field, through the
Python reference (tools/passport/stamp.py). For random stamps of every length a QR code
holds (versions 1 to 4), the code's modules must be the qrcode library's (alphanumeric,
level L, mask 0) and, drawn in the view, scan back (OpenCV) to the text; and a text too
long, or with a character alphanumeric mode hasn't, must be refused.
"""

import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests", "cart"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
import run_cart  # noqa: E402
import passport  # noqa: E402
import stamp  # noqa: E402
from test_passwords import Cart  # noqa: E402

TEXT, OUT = 0xA0A5, 0xA800          # RAM the game doesn't use here
ASSET_ENDING = 1
R_DEPARTURE, R_TICKET, R_OUTCOME, R_XP = 0, 2, 6, 7     # cart/receipt.inc
R_DEBT_PAID, R_DEBT_ADDED, R_GAINED, R_LOST, R_ECHOES = 9, 11, 13, 30, 47

failures = 0


def fail(msg):
    global failures
    failures += 1
    print(f"FAIL: {msg}")


def random_receipt(rnd):
    r = {"departure": rnd.randrange(65536), "ticket": rnd.randrange(1, 1 << 32),
         "outcome": rnd.randrange(2), "xp": rnd.randrange(65536)}
    amount = rnd.randrange(65536)
    r["debt_added"], r["debt_paid"] = (amount, 0) if rnd.random() < 0.5 else (0, amount)
    full = rnd.random() < 0.3
    r["gained"] = [rnd.randrange(1024) for _ in range(8 if full else rnd.randint(0, 3))]
    r["lost"] = [rnd.randrange(1024) for _ in range(8 if full else rnd.randint(0, 3))]
    r["echoes"] = [(rnd.randrange(1024), rnd.randrange(4), rnd.randrange(4))
                   for _ in range(8 if full else rnd.randint(0, 3))]
    return r


def put_receipt(cart, r):
    at = cart.s["receipt"]
    data = bytearray(80)
    data[R_DEPARTURE:R_DEPARTURE + 2] = r["departure"].to_bytes(2, "little")
    data[R_TICKET:R_TICKET + 4] = r["ticket"].to_bytes(4, "little")
    data[R_OUTCOME] = r["outcome"]
    data[R_XP:R_XP + 2] = r["xp"].to_bytes(2, "little")
    data[R_DEBT_PAID:R_DEBT_PAID + 2] = r["debt_paid"].to_bytes(2, "little")
    data[R_DEBT_ADDED:R_DEBT_ADDED + 2] = r["debt_added"].to_bytes(2, "little")
    for key, base in (("gained", R_GAINED), ("lost", R_LOST)):
        data[base] = len(r[key])
        for i, item in enumerate(r[key]):
            data[base + 1 + 2 * i:base + 3 + 2 * i] = item.to_bytes(2, "little")
    data[R_ECHOES] = len(r["echoes"])
    for i, (eid, state, was) in enumerate(r["echoes"]):
        data[R_ECHOES + 1 + 4 * i:R_ECHOES + 5 + 4 * i] = (eid.to_bytes(2, "little")
                                                          + bytes([state, was]))
    cart.c.ram[at:at + 80] = data


def idle(cart, frames):
    """The machine left to run for a few frames, in a loop of its own (JMP to itself)."""
    c, m = cart.c, cart.c.mpu
    loop = TEXT + 0x200
    c.ram[loop:loop + 3] = bytes([0x4C, loop & 0xFF, loop >> 8])
    m.pc = loop
    end = m.processorCycles + frames * run_cart.FRAME
    while m.processorCycles < end:
        c.start, c.op, c.pc0 = m.processorCycles, c.mem[m.pc], m.pc
        m.step()
        c.raster()


def check_qr(cart, text, what):
    """The cartridge's code for `text` (qr_make, qr_show) against qrcode's and OpenCV's."""
    import qrcode
    import numpy
    cart.text(TEXT, text)
    m = cart.c.mpu
    cart.call("qr_make", TEXT & 0xFF, TEXT >> 8)
    refused = m.p & m.CARRY
    fits = len(text) <= 114 and all(ch in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" for ch in text)
    if not fits:
        if not refused:
            fail(f"{what}: {text!r} should be refused")
        return refused
    if refused:
        fail(f"{what}: {text!r} refused")
        return False
    version = next(v for v, top in ((1, 25), (2, 47), (3, 77), (4, 114)) if len(text) <= top)
    qr = qrcode.QRCode(version=version, error_correction=qrcode.constants.ERROR_CORRECT_L,
                       mask_pattern=0, border=0)
    qr.add_data(qrcode.util.QRData(text, mode=qrcode.util.MODE_ALPHA_NUM))
    qr.make(fit=False)
    want = [[1 if v else 0 for v in row] for row in qr.get_matrix()]
    size = cart.c.ram[cart.s["qr_size"]]
    got = [[cart.c.ram[run_cart.QR_MATRIX + y * size + x] & 1 for x in range(size)]
           for y in range(size)]
    if got != want:
        fail(f"{what}: version {version}'s modules for {text!r} aren't qrcode's")
        return False
    cart.call("qr_show")
    idle(cart, 2)                           # two frames: line 250 sets the view
    read = run_cart.scan(numpy.array(run_cart.view_image(cart.c).convert("L")))
    if read != text:
        fail(f"{what}: version {version}'s code for {text!r} scans as {read!r}")
        return False
    return True


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cases = int(argv[argv.index("--cases") + 1]) if "--cases" in argv else 40
    cart = Cart(argv[1], argv[2])
    cart.call("asset_fetch", ASSET_ENDING)
    rnd = random.Random(1983)
    stamps = 0
    for k in range(cases):
        r = random_receipt(rnd)
        put_receipt(cart, r)
        cart.call("stamp_encode", OUT & 0xFF, OUT >> 8)
        text = cart.read_text(OUT)
        try:
            back = stamp.decode(text)
        except passport.PassportError as e:
            fail(f"receipt {k}: the stamp {text!r} doesn't read: {e}")
            continue
        if back != r:
            fail(f"receipt {k}: the stamp reads {back}, not {r}")
            continue
        stamps += 1
    print(f"ok   {stamps} Travel Stamps read back as written, by tools/passport/stamp.py")
    codes = 0
    lengths = [1, 2, 25, 26, 47, 48, 77, 78, 114] + [rnd.randint(1, 114) for _ in range(3)]
    for k, n in enumerate(lengths):
        text = "".join(rnd.choice(passport.SYMBOLS) for _ in range(n))
        codes += check_qr(cart, text, f"code {k}")
    refused = sum(check_qr(cart, text, "a text no code holds") for text in
                  ("0" * 115, "ABC-1", "abc"))
    print(f"ok   {codes} QR codes of {len(lengths)} (versions 1-4) qrcode's, module for "
          f"module, and scanned back off the screen; {refused} of 3 texts refused")
    print(f"cart ending: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
