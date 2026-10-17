"""The walking engine on x64sc, VICE's cycle-exact C64, held to the harness frame by frame
(docs/walk.md, "Tested"): the program is run with the same joystick as tests/walk/run_walk.py
plays it (set in A where the loop reads the port, wk_joy), and every few frames x64sc's
picture, the whole raster with its borders, is compared pixel for pixel with the frame as
the harness says the VIC showed it: each row of characters as read at its bad line, with
the fine scroll, and each sprite from the line after its Y, as the VIC-II starts one.

    python3 tests/walk/vice_walk.py PRG LABELS [--yard Y --floor F] [--open] [--frames N]
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
EDGE_LINES = (55, 247)      # the band's edges: the view's first line, the band's
EDGE_MOST = 104             # ...and how far into the line a late edge may come: the border
                            # and 8 characters (docs/walk.md, "The border": the limit)
CHARSET, SHAPES = 0xC800, 0xD000
READER = 0x0200                   # spare RAM: the joystick script's reader, and its table

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  ", msg)


def render(c64, rows, snaps, border=0):
    """The picture as it's meant to be (docs/walk.md, "The border"), from the harness's
    snapshot of each line (run_walk.C64.snapshot): colours 0-15, COLS x LINES.

    The view, lines 55-246: each line as the VIC draws it from the rows the harness saw
    read at their bad lines, the fine scroll, the idle byte ($FFFF) where no row is shown;
    the figures' sprites over it, sprite 0 on top, each in its own shape (the first it
    showed in the view: the harness's lines are too coarse to say on which side of a line
    a pointer's write fell, which is what x64sc is for), and only in the view, but when
    the fine scroll is 6: then the figures crossing its top (their Y under 54) come in a
    line late (56), and
    its last line (246) has none. Outside it everything's black (the border's open: sprite
    X 31-334 is the 38 columns' window, the main border outside it) but the HUD's sprites."""
    io, ram = c64.io, c64.ram
    bg, mc1, mc2 = io[0x21] & 15, io[0x22] & 15, io[0x23] & 15
    smc1, smc2 = io[0x25] & 15, io[0x26] & 15
    img = [[border] * COLS for _ in range(LINES)]
    x_lo, x_hi = 31, 334
    first, last = walk.FIRST_VIEW, walk.LAST_VIEW
    ys = next(d011 for line, d011, *_ in snaps if line == 150) & 7
    blank = walk.SHAPE_POINTER + walk.BLANK
    # Each sprite's showing (its number and the line before its first): its own shape.
    own = {}
    for line, d011, d016, d018, row, sprites in snaps:
        for n, x, srow, ptr, colour, multi in sprites:
            key = (n, line - srow - 1)
            hud = key[1] > last
            if key not in own and ptr != blank and (hud and srow >= 1 or first <= line <= last):
                own[key] = ptr
    for line, d011, d016, d018, row, sprites in snaps:
        out = img[line]
        if first <= line <= last:
            xs = d016 & 7
            for x in range(x_lo, x_hi + 1):
                p = (x - 24 - xs) % 8
                if row is None:
                    colour = 0 if ram[0xFFFF] >> (7 - p) & 1 else bg
                    out[x + X0] = colour
                    continue
                chars, cols = rows[row[0]]
                c = (x - 24 - xs) // 8
                if not 0 <= c < 40:
                    out[x + X0] = bg
                    continue
                byte, col = ram[CHARSET + chars[c] * 8 + row[1]], cols[c] & 15
                if col & 8:
                    v = (byte >> (6 - (p & 6))) & 3
                    out[x + X0] = (bg, mc1, mc2, col & 7)[v]
                else:
                    out[x + X0] = col if byte >> (7 - p) & 1 else bg
        for n, x, srow, ptr, colour, multi in sorted(sprites, key=lambda s: -s[0]):
            start = line - srow - 1
            if (n, start) not in own or not 0 <= srow < 21:
                continue
            if start < last:                    # a figure's
                if not first <= line <= last:
                    continue
                if ys == 6 and (line == last or start < first - 1 and line == first):
                    continue
            ptr = own[(n, start)]
            data = ram[SHAPES + (ptr - 0x40) * 64 + srow * 3:SHAPES + (ptr - 0x40) * 64 + srow * 3 + 3]
            for p in range(24):
                byte = data[p // 8]
                if multi:
                    v = (byte >> (6 - (p % 8 & 6))) & 3
                    c = (None, smc1, colour, smc2)[v]
                else:
                    c = colour if byte >> (7 - p % 8) & 1 else None
                if c is not None and x_lo <= x + p <= x_hi:
                    out[x + p + X0] = c
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
    ap.add_argument("--open", action="store_true", help="an open floor (docs/open-floors.md)")
    ap.add_argument("--unseen", action="store_true", help="its foes all shown, none looking")
    ap.add_argument("--frames", type=int, default=0, help="how many (default: the walk)")
    ap.add_argument("--every", type=int, default=7, help="compare every Kth frame")
    ap.add_argument("--shots", help="save each compared frame's two pictures here")
    args = ap.parse_args()
    if not vice.available():
        print("ok   (x64sc or xvfb-run not here: the VICE check skipped)")
        return 0
    sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))

    floor = walk.Floor(args.yard, args.floor, open_floor=args.open, unseen=args.unseen)
    script = run_walk.sticks(floor)
    frames = args.frames or len(script)
    syms = run_walk.labels(args.labels)
    c64 = run_walk.C64(open(args.prg, "rb").read(), syms, script + [0xFF] * 10)
    c64.snap = {p for p in range(frames + 2) if (p + 1) % args.every == 0}
    c64.run(frames + 2)
    records = {rec[0]: rec for rec in c64.frames}

    pal = vice.palette()
    v = vice.Vice()
    compared = bad = edged = edge_most = 0
    try:
        # The program; the joystick's script in spare RAM ($0200: the frames it changes on,
        # and what it is then), and the loop's read of the port a call to a reader of it.
        v.cmd("bank ram")
        v.cmd(f'l "{os.path.abspath(args.prg)}" 0')
        changes = [(1, script[0])] + [(i + 1, script[i]) for i in range(1, len(script))
                                        if script[i] != script[i - 1]]
        changes.append((len(script) + 1, 0xFF))
        changes.append((0xFFFF, 0xFF))
        assert len(changes) <= 64
        lo = bytes(f & 255 for f, _ in changes).ljust(64, b"\xff")
        hi = bytes(f >> 8 for f, _ in changes).ljust(64, b"\xff")
        val = bytes(s for _, s in changes).ljust(64, b"\xff")
        frame_at = syms["wk_frame"]
        TAB = READER + 0x40
        reader = [0xAC, (READER + 0x3F) & 255, (READER + 0x3F) >> 8,   # ldy idx
                  0xAD, frame_at & 255, frame_at >> 8,                # @chk: lda wk_frame
                  0xD9, (TAB + 1) & 255, (TAB + 1) >> 8,              # cmp lo + 1, y
                  0xAD, (frame_at + 1) & 255, (frame_at + 1) >> 8,    # lda wk_frame + 1
                  0xF9, (TAB + 65) & 255, (TAB + 65) >> 8,            # sbc hi + 1, y
                  0x90, 0x03,                                         # bcc @have
                  0xC8, 0xD0, 0xEF,                                   # iny, bne @chk
                  0x8C, (READER + 0x3F) & 255, (READER + 0x3F) >> 8,  # @have: sty idx
                  0xB9, (TAB + 128) & 255, (TAB + 128) >> 8,          # lda val, y
                  0x60]                                               # rts
        assert len(reader) < 0x3F
        image = bytes(reader).ljust(0x3F, b"\0") + b"\0" + lo + hi + val
        table = os.path.join(v.dir, "sticks.prg")
        open(table, "wb").write(bytes([READER & 255, READER >> 8]) + image)
        v.cmd(f'l "{table}" 0')
        port_read = syms["wk_joy"] - 3                         # its lda CIA1_PRA
        v.cmd(f"> {port_read:04x} 20 {READER & 255:02x} {READER >> 8:02x}")
        # Stopped at the world's interrupt (line 288), the screenshot is the picture
        # begun at line 0, its frame number one less than the count now.
        v.cmd(f"break {syms['world_irq']:04x}")
        v.go("g 080d")                           # (the BASIC line's SYS 2061)
        while True:
            lo_, hi_ = v.peek(frame_at, 2)
            f = lo_ | hi_ << 8
            if f > frames:
                break
            p = f - 1
            if p in c64.snaps and p in records:
                path = os.path.join(v.dir, "shot.png")
                v.screenshot(path)
                got = shot(path, pal)
                want = render(c64, records[p][3], c64.snaps[p])
                diff = [(x - X0, y) for y in range(LINES) for x in range(COLS)
                        if got[y][x] != want[y][x]]
                # The band's edge may come a few cycles into its line, in its first
                # characters: when figures cross the view's edge, the VIC stops the CPU
                # for their fetches, and the write after the stops is late (docs/walk.md,
                # "The border": up to 4 characters with an open floor's crowd crossing at
                # once). Counted, not failed.
                edge = [(x, y) for x, y in diff if y in EDGE_LINES and x < EDGE_MOST]
                diff = [d for d in diff if d not in edge]
                if edge:
                    edged += 1
                    edge_most = max(edge_most, len(edge))
                compared += 1
                if diff:
                    bad += 1
                    if bad <= 5:
                        lines = sorted({y for _, y in diff})
                        fail(f"picture {p}: {len(diff)} pixels differ from the harness's, on "
                             f"lines {lines[:8]}{'...' if len(lines) > 8 else ''}, the first "
                             f"at X {diff[0][0]}")
                if args.shots and (diff or compared <= 3):
                    os.makedirs(args.shots, exist_ok=True)
                    save(got, os.path.join(args.shots, f"{p:05d}-vice.png"))
                    save(want, os.path.join(args.shots, f"{p:05d}-want.png"))
            v.cmd(f"ignore 1 {args.every - 1:x}")       # (the monitor reads hex)
            v.go("x")
    finally:
        v.quit()
    if not bad:
        ok(f"{compared} pictures on x64sc, every {args.every}th of {frames}: each as meant, pixel "
           f"for pixel, the borders and all (in {edged} the band's edge late by up to "
           f"{edge_most} pixels, in its line's first characters)")
    else:
        fail(f"{bad} of {compared} frames differ on x64sc")
    print(f"walk on VICE: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
