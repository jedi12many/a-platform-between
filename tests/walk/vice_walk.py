"""The walking engine on x64sc, VICE's cycle-exact C64, held to the harness frame by frame
(docs/walk.md, "Tested"): the program is run with the same joystick as tests/walk/run_walk.py
plays it (set in A where the loop reads the port, wk_joy), and every few frames x64sc's
picture, the whole raster with its borders, is compared pixel for pixel with the frame as
the harness says the VIC showed it: each row of characters as read at its bad line, with
the fine scroll, and each sprite from the line after its Y, as the VIC-II starts one.

    python3 tests/walk/vice_walk.py PRG LABELS [--yard Y --floor F] [--frames N]
            [--every K] [--shots DIR]

Needs x64sc (apt-get install vice) and xvfb-run; without them it says so and passes."""

import argparse
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools", "walk"))
import run_walk  # noqa: E402
import vice  # noqa: E402
import walk  # noqa: E402

COLS, LINES = 504, 312
X0 = 112                    # the screenshot's column of sprite X 0
VIEW = (31, 334, 55, 246)   # the 38 x 24 window: sprite X, raster lines
CHARSET, SHAPES = 0xC800, 0xD000
READER, STICKS = 0xF400, 0xF500   # spare RAM (walk.inc): the joystick script's reader, and it

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  ", msg)


def render(c64, rec, sprites, border=0):
    """The frame as the harness says the VIC showed it: colours 0-15, COLS x LINES."""
    frame, d016, d011, rows = rec
    io, ram = c64.io, c64.ram
    bg, mc1, mc2 = io[0x21] & 15, io[0x22] & 15, io[0x23] & 15
    smc1, smc2 = io[0x25] & 15, io[0x26] & 15
    img = [[border] * COLS for _ in range(LINES)]
    x_lo, x_hi, l_lo, l_hi = VIEW
    xs, ys = d016 & 7, d011 & 7
    for r, (chars, cols) in enumerate(rows):
        for rc in range(8):
            line = 48 + ys + 8 * r + rc
            if not l_lo <= line <= l_hi:
                continue
            out = img[line]
            for c in range(40):
                byte, col = ram[CHARSET + chars[c] * 8 + rc], cols[c] & 15
                x0 = 24 + xs + 8 * c
                for p in range(8):
                    if col & 8:
                        v = (byte >> (6 - (p & 6))) & 3
                        colour = (bg, mc1, mc2, col & 7)[v]
                    else:
                        colour = col if byte >> (7 - p) & 1 else bg
                    x = x0 + p
                    if x_lo <= x <= x_hi:
                        out[x + X0] = colour
    # Sprites: the higher numbered first, so sprite 0 comes out on top; multicolour, over
    # the characters, shown from the line after their Y, inside the window.
    for x, y, ptr, colour, n in sorted(sprites, key=lambda s: -s[4]):
        data = ram[SHAPES + (ptr - 0x40) * 64:SHAPES + (ptr - 0x40) * 64 + 63]
        for row in range(21):
            line = y + 1 + row
            if not l_lo <= line <= l_hi:
                continue
            for p in range(24):
                byte = data[row * 3 + p // 8]
                v = (byte >> (6 - (p % 8 & 6))) & 3
                if v and x_lo <= x + p <= x_hi:
                    img[line][x + p + X0] = (0, smc1, colour, smc2)[v]
    return img


def shot(path, pal):
    im = Image.open(path).convert("RGB")
    if im.size != (COLS, LINES):
        raise RuntimeError(f"a screenshot of {im.size}, not {COLS} x {LINES}")
    px = im.load()
    return [[pal.get(px[x, y], -1) for x in range(COLS)] for y in range(LINES)]


def save(img, path):
    from c64pic import PALETTE
    im = Image.new("RGB", (COLS, LINES))
    im.putdata([tuple(PALETTE[v]) if v >= 0 else (255, 0, 255) for row in img for v in row])
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prg")
    ap.add_argument("labels")
    ap.add_argument("--yard", type=int, default=48213)
    ap.add_argument("--floor", type=int, default=1)
    ap.add_argument("--frames", type=int, default=0, help="how many (default: the walk)")
    ap.add_argument("--every", type=int, default=7, help="compare every Kth frame")
    ap.add_argument("--shots", help="save each compared frame's two pictures here")
    args = ap.parse_args()
    if not vice.available():
        print("ok   (x64sc or xvfb-run not here: the VICE check skipped)")
        return 0
    sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

    floor = walk.Floor(args.yard, args.floor)
    script = run_walk.sticks(floor)
    frames = args.frames or len(script)
    syms = run_walk.labels(args.labels)
    c64 = run_walk.C64(open(args.prg, "rb").read(), syms, script + [0xFF] * 10)
    c64.run(frames + 2)
    records = {rec[0]: rec for rec in c64.frames}

    pal = vice.palette()
    v = vice.Vice()
    compared = bad = 0
    try:
        # The program; the joystick's script in spare RAM, and the loop's read of the
        # port made a call to a reader of it (script[wk_frame - 1]).
        v.cmd("bank ram")
        v.cmd(f'l "{os.path.abspath(args.prg)}" 0')
        table = os.path.join(v.dir, "sticks.prg")
        sticks_bytes = bytes(script + [0xFF] * 16)
        assert STICKS + len(sticks_bytes) <= 0xFF00
        open(table, "wb").write(bytes([STICKS & 255, STICKS >> 8]) + sticks_bytes)
        v.cmd(f'l "{table}" 0')
        frame_at = syms["wk_frame"]
        reader = [0xAD, frame_at & 255, frame_at >> 8,          # lda wk_frame
                  0x18, 0x69, 0xFF,                             # clc, adc #$ff (- 1)
                  0x8D, (READER + 18) & 255, (READER + 18) >> 8,
                  0xAD, (frame_at + 1) & 255, (frame_at + 1) >> 8,
                  0x69, (STICKS >> 8) - 1,
                  0x8D, (READER + 19) & 255, (READER + 19) >> 8,
                  0xAD, 0, 0,                                   # lda script[frame - 1]
                  0x60]
        v.cmd(f"> {READER:04x} " + " ".join(f"{b:02x}" for b in reader))
        port_read = syms["wk_joy"] - 3                         # its lda CIA1_PRA
        v.cmd(f"> {port_read:04x} 20 {READER & 255:02x} {READER >> 8:02x}")
        v.cmd(f"break {syms['wk_joy']:04x}")
        v.go("g 080d")                           # (the BASIC line's SYS 2061)
        while True:
            lo, hi = v.peek(frame_at, 2)
            f = lo | hi << 8
            if f > frames:
                break
            if f - 1 in records and f > 1:
                path = os.path.join(v.dir, "shot.png")
                v.screenshot(path)
                got = shot(path, pal)
                want = render(c64, records[f - 1], [
                    s + (n,) for s, n in zip(c64.shown.get(f - 1, []), c64.shown_n.get(f - 1, []))])
                diff = [(x - X0, y) for y in range(LINES) for x in range(COLS)
                        if got[y][x] != want[y][x]]
                compared += 1
                if diff:
                    bad += 1
                    if bad <= 5:
                        fail(f"frame {f - 1}: {len(diff)} pixels differ from the harness's, the "
                             f"first at X {diff[0][0]}, line {diff[0][1]}")
                if args.shots and (diff or compared <= 3):
                    os.makedirs(args.shots, exist_ok=True)
                    save(got, os.path.join(args.shots, f"{f - 1:05d}-vice.png"))
                    save(want, os.path.join(args.shots, f"{f - 1:05d}-want.png"))
            v.cmd(f"ignore 1 {args.every - 1}")
            v.go("x")
    finally:
        v.quit()
    if not bad:
        ok(f"{compared} frames on x64sc, every {args.every}th of {frames}: each the harness's "
           f"picture pixel for pixel, the borders and all")
    else:
        fail(f"{bad} of {compared} frames differ on x64sc")
    print(f"walk on VICE: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
