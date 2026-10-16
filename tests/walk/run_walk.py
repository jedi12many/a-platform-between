"""The walking engine (cart/walk/, docs/walk.md) on an emulated C64, held to its reference
(tools/walk/walk.py) frame by frame.

    python3 tests/walk/run_walk.py PRG LABELS [--yard Y --floor F] [--frames N] [--shot FRAME FILE.png]

PRG is the walking engine built for yard Y's floor F (48213's first, unless said).

The program runs on py65 with the C64 around it played in Python: the memory as the PLA
maps it (the I/O apart from the RAM under it, the colour RAM its own four bits), CIA 1's
port A as the joystick in port 2, and the VIC-II's raster: 63 cycles a line, 312 lines a
frame (PAL), the raster interrupt at $D012's line, and the bad lines, where the VIC stops
the 6502 for 40 cycles to read a row of characters: on each, the row the screen shows is
read as the VIC reads it then (the screen $D018 points at, and the colour RAM, at that
moment), so a frame is checked as it was seen, not as memory is afterwards.

The joystick follows a script (SCRIPT below: right, down, the diagonals, into walls and
round corners), then walks to the floor's stairs, through its doors (route). Checks:

- every frame's leader, camera and scroller stage are the reference's (walk.play);
- every frame shown is the area as the reference's camera sees it: each character and
  colour on the screen's visible 38 x 24 (and the edges the fine scroll shows), and the
  fine scroll's registers;
- every frame's figures as the VIC showed them: each sprite as it started showing (its
  x, y, shape pointer and colour, read when the raster reaches its y) is the reference's,
  the party on the leader's trail and the floor's foes and people, shared out among the 8
  sprites; and each sprite showing takes its 2 cycles a line from the 6502;
- no frame is late (the frame loop always done before the next frame's interrupt), and
  the busiest frame's cycles, the loop's and the interrupt's, are reported.
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "walk"))
import walk  # noqa: E402

from py65.devices.mpu6502 import MPU  # noqa: E402
from py65.memory import ObservableMemory  # noqa: E402

LINE, LINES = 63, 312
FRAME = LINE * LINES
BADLINE_STEAL = 40
FIRST_DMA_LINE, LAST_DMA_LINE = 0x30, 0xF7
YARD, FLOOR = 48213, 1

R, L, U, D = walk.RIGHT, walk.LEFT, walk.UP, walk.DOWN
# The joystick, a frame at a time: (bits pushed, frames).
SCRIPT = [(0, 10), (R, 140), (D, 40), (R | D, 60), (U, 30), (L, 90), (U | L, 40), (R, 60),
          (D, 90), (R | U, 40), (L | D, 50), (0, 20)]

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  ", msg)


def sticks(floor):
    """The script, then a walk to the stairs (route)."""
    out = []
    for bits, n in SCRIPT:
        out += [0xFF & ~bits] * n
    return out + route(floor, out)


def route(floor, before):
    """The joystick that walks the leader, from where SCRIPT leaves them, along a shortest
    way (4 ways, square to square) to the floor's stairs: each frame, toward the middle of
    the next square on the way, a pixel's slack each way. Only the joystick comes from here:
    the C64 and the reference walk it the same."""
    f = floor.f
    s = f["stairs"]
    goal = ((s % 3) * 16 + 7, (s // 3) * 8 + 3)
    pos = [floor.start[0] * 256, floor.start[1] * 256]
    for st in before:
        walk.walk(floor, pos, st)
    here = (pos[0] + 128) >> 8, (pos[1] + 128) >> 8
    prev, todo = {here: None}, [here]
    while todo:
        c = todo.pop(0)
        if c == goal:
            break
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c[0] + d[0], c[1] + d[1])
            if n not in prev and floor.free(*n):
                prev[n] = c
                todo.append(n)
    way, c = [], goal
    while c is not None:
        way.append(c)
        c = prev[c]
    way.reverse()
    out = []
    for sq in way[1:]:
        for _ in range(200):
            px, py = pos[0] >> 4, pos[1] >> 4
            tx, ty = sq[0] * 16, sq[1] * 16
            bits = (R if tx > px + 1 else L if tx < px - 1 else 0) | (D if ty > py + 1 else U if ty < py - 1 else 0)
            if not bits:
                break
            out.append(0xFF & ~bits)
            walk.walk(floor, pos, out[-1])
    return out


def labels(path):
    out = {}
    for line in open(path):
        parts = line.split()
        if len(parts) == 3 and parts[0] == "al":
            out[parts[2].lstrip(".")] = int(parts[1], 16)
    return out


class C64:
    def __init__(self, prg, syms, script):
        self.syms, self.script = syms, script
        self.mem = ObservableMemory()
        self.ram = self.mem._subject
        self.io = bytearray(0x1000)
        self.colour = bytearray(1024)
        self.mpu = MPU(memory=self.mem)
        at = prg[0] | prg[1] << 8
        for i, b in enumerate(prg[2:]):
            self.ram[at + i] = b
        self.ram[0], self.ram[1] = 0x2F, 0x37
        self.mpu.sp = 0xF6
        self.mpu.pc = syms["walk_start"]
        self.line = 0
        self.badrow = 0
        self.sprite_until = [0] * 8
        self.shown = {}                     # frame: the sprites that started showing in it
        self.shown_n = {}                   # ...and their numbers
        self.most_on = 0
        self.frames = []                    # each frame shown: (wk_frame, d016, d011, rows)
        self.seen = None
        self.states = []                    # each loop's: (frame, pos x, pos y, cam x, cam y, stage)
        self.loop_cycles = []               # each loop's cycles, awake to done
        self.irq_cycles = []
        self.awake_at = None
        self.irq_at = None
        self.mem.subscribe_to_read(range(0xD000, 0xE000), self.read_io)
        self.mem.subscribe_to_write(range(0xD000, 0xE000), self.write_io)

    def io_in(self):
        ddr, port = self.ram[0], self.ram[1]
        p = ((port & ddr) | (~ddr & 0xFF)) & 7
        return p & 4 and p & 3

    def read_io(self, a):
        if not self.io_in():
            return None
        if a == 0xD012:
            return self.line & 0xFF
        if a == 0xD011:
            return (self.io[0x11] & 0x7F) | (self.line >> 8) << 7
        if 0xD800 <= a < 0xDC00:
            return self.colour[a - 0xD800] | 0xF0
        if a == 0xDC00:
            f = self.frame()
            return self.script[f - 1] if 0 < f <= len(self.script) else 0xFF
        return self.io[a - 0xD000]

    def write_io(self, a, v):
        if not self.io_in():
            return None
        if a == 0xD019:
            self.io[0x19] &= ~v & 0xFF
        elif 0xD800 <= a < 0xDC00:
            self.colour[a - 0xD800] = v & 0x0F
        else:
            self.io[a - 0xD000] = v
        return self.ram[a]

    def screen_base(self):
        bank = 3 - (self.io[0xD00] & 3)
        return bank * 0x4000 + (self.io[0x18] >> 4) * 0x400

    def new_line(self):
        """The raster moves on a line: the interrupt's compare, and a bad line's theft."""
        self.line = (self.line + 1) % LINES
        if self.line == 0 and self.seen:
            self.frames.append(self.seen)
            self.seen = None
        target = self.io[0x12] | (self.io[0x11] & 0x80) << 1
        if self.line == target:
            self.io[0x19] |= 0x81
        self.sprites_line()
        ys = self.io[0x11] & 7
        if FIRST_DMA_LINE <= self.line <= LAST_DMA_LINE and self.line & 7 == ys and self.io[0x11] & 0x10:
            if self.seen is None:
                self.seen = (self.frame(), self.io[0x16], self.io[0x11], [])
                self.badrow = 0
            base = self.screen_base() + 40 * self.badrow
            self.seen[3].append((bytes(self.ram[base:base + 40]),
                                 bytes(self.colour[40 * self.badrow:40 * self.badrow + 40])))
            self.badrow += 1
            self.mpu.processorCycles += BADLINE_STEAL

    def sprites_line(self):
        """The VIC's sprites on this line: one not showing starts when its y is this line
        (it's on); it shows 21 lines, its x, pointer and colour as they are when it starts
        (recorded, by frame); each showing takes 2 of the 6502's cycles on each line."""
        on = 0
        for n in range(8):
            if self.sprite_until[n] > self.line:
                on += 1
            elif self.io[0x15] >> n & 1 and self.io[1 + 2 * n] == self.line:
                self.sprite_until[n] = self.line + 21
                x = self.io[2 * n] | (self.io[0x10] >> n & 1) << 8
                ptr = self.ram[self.screen_base() + 0x3F8 + n]
                self.shown.setdefault(self.frame(), []).append((x, self.line, ptr, self.io[0x27 + n] & 15))
                self.shown_n.setdefault(self.frame(), []).append(n)
                on += 1
            if self.line == 0:
                self.sprite_until[n] = 0
        self.most_on = max(self.most_on, on)
        self.mpu.processorCycles += 2 * on

    def irq(self):
        m = self.mpu
        if self.io[0x19] & self.io[0x1A] & 1 and not m.p & m.INTERRUPT:
            for b in (m.pc >> 8, m.pc & 0xFF, (m.p & ~m.BREAK) | m.UNUSED):
                self.ram[0x100 + m.sp] = b
                m.sp = (m.sp - 1) & 0xFF
            m.p |= m.INTERRUPT
            m.processorCycles += 7
            m.pc = self.ram[0xFFFE] | self.ram[0xFFFF] << 8
            self.irq_at = m.processorCycles - 7

    def frame(self):
        a = self.syms["wk_frame"]
        return self.ram[a] | self.ram[a + 1] << 8

    def state(self):
        r, s = self.ram, self.syms
        p, c = s["wk_pos"], s["wk_cam"]
        word = lambda a: r[a] | r[a + 1] << 8
        return (self.frame(), word(p), word(p + 2), word(c), word(c + 2), r[s["wk_stage"]])

    def run(self, frames):
        m = self.mpu
        awake, irq, nmi = self.syms["wk_awake"], self.syms["irq"], self.syms["nmi"]
        done = self.syms["wk_done"]
        last = 0
        while len(self.states) < frames:
            pc = m.pc
            if pc == awake:
                self.states.append(self.state())
                self.awake_at = m.processorCycles
            elif pc == done and self.awake_at is not None:
                self.loop_cycles.append(m.processorCycles - self.awake_at)
                self.awake_at = None
            elif pc == nmi and self.irq_at is not None:          # the interrupt's RTI
                self.irq_cycles.append(m.processorCycles - self.irq_at)
                self.irq_at = None
            m.step()
            while m.processorCycles // LINE != last:
                last += 1
                self.new_line()
            self.irq()
            if m.processorCycles > 400 * FRAME + frames * FRAME * 2:
                raise RuntimeError("it never settled into frames")


def expected_rows(floor, cam):
    cc, cr = cam[0] >> 3, cam[1] >> 3
    return [[floor.char(cc + c, cr + r) for c in range(40)] for r in range(25)]


def check(c64, floor, ref):
    # The loop's state, frame by frame.
    bad = 0
    for st in c64.states:
        f = st[0]
        if f < 1 or f > len(ref):
            continue
        want = ref[f - 1][:5]
        if st[1:] != want:
            if bad < 5:
                fail(f"frame {f}: the leader at {st[1:3]}, the camera at {st[3:5]}, stage {st[5]}; "
                     f"the reference has {want[:2]}, {want[2:4]}, stage {want[4]}")
            bad += 1
    if not bad:
        far = max(abs(s[1] - c64.states[0][1]) + abs(s[2] - c64.states[0][2]) for s in c64.states) // 256
        steps = sum(1 for s in c64.states if s[5] == walk.SHIFTED)
        ok(f"{len(c64.states)} frames: the leader, the camera and the scroller as the reference's, "
           f"frame by frame (as far as {far} squares from the start, {steps} coarse steps)")
    # Each frame as the VIC showed it.
    bad = 0
    for f, d016, d011, rows in c64.frames:
        if f < 1 or f > len(ref):
            continue
        cam = ref[f - 1][2:4]
        xs, ys = 7 - (cam[0] & 7), 7 - (cam[1] & 7)
        problems = []
        if d016 & 7 != xs or d011 & 7 != ys or d016 & 0x18 != 0x10 or d011 & 0x78 != 0x10:
            problems.append(f"registers ${d016:02X} ${d011:02X} for fine scroll {xs}, {ys}")
        want = expected_rows(floor, cam)
        if len(rows) != 25:
            problems.append(f"{len(rows)} rows read")
        for r, (chars, cols) in enumerate(rows[:25]):
            if r == 24 and ys == 7:
                continue                                # (out of sight)
            for c in range(39 if xs < 7 else 38):
                ch, col = want[r][c]
                if chars[c] != ch or cols[c] != col & 0x0F:
                    problems.append(f"row {r} column {c}: {chars[c]}/{cols[c]}, not {ch}/{col & 15}")
                    break
            if len(problems) > 2:
                break
        if problems:
            if bad < 5:
                fail(f"frame {f} as shown (camera {cam}): " + "; ".join(problems[:3]))
            bad += 1
    if not bad:
        ok(f"{len(c64.frames)} frames as the VIC showed them, each row read at its bad line: the "
           f"area as the reference's camera sees it, character for character and colour for colour")
    # The figures as the VIC showed them.
    bad, figs, most, left = 0, 0, 0, 0
    for f in sorted({fr[0] for fr in c64.frames}):
        if f < 1 or f > len(ref):
            continue
        sprites, dropped = ref[f - 1][5]
        want = sorted((x & 511, y, ptr, col) for _, x, y, ptr, col, _ in sprites)
        got = sorted(c64.shown.get(f, []))
        figs += len(want)
        most = max(most, len(want))
        left += dropped
        if got != want:
            if bad < 5:
                fail(f"frame {f}: the sprites shown were {got}, not {want}")
            bad += 1
    if not bad:
        ok(f"every frame's figures as the VIC showed them, sprite by sprite (x, y, shape, colour) "
           f"as the reference places and shares them: {figs} in all, up to {most} a frame, "
           f"{left} left out")
    late = c64.ram[c64.syms["wk_late"]]
    if late:
        fail(f"{late} frames late: the loop wasn't done when the next frame began")
    busiest = max(c64.loop_cycles) if c64.loop_cycles else 0
    irq = max(c64.irq_cycles) if c64.irq_cycles else 0
    if not late:
        ok(f"no frame late: the busiest loop {busiest} cycles, the busiest interrupt {irq} "
           f"(a frame is {FRAME}, less 25 bad lines' {25 * BADLINE_STEAL})")


def shot(c64, floor, index, path):
    """Frame `index` as shown, in the VIC's colours (tools/vic.py), its fine scroll applied."""
    from vic import Screen
    f, d016, d011, rows = c64.frames[index]
    charset = bytes(c64.ram[0xC800:0xD000]) + bytes(2048)
    s = Screen(charset, c64.io[0x21] & 15, c64.io[0x22] & 15, c64.io[0x23] & 15, 0, 0)
    for r, (chars, cols) in enumerate(rows):
        for c in range(40):
            s.put(c, r, chars[c], cols[c])
    img = s.image(None) if "border" in Screen.image.__code__.co_varnames else s.image()
    xs, ys = d016 & 7, d011 & 7
    img = img.crop((7 - xs, 7 - ys, 7 - xs + 304, 7 - ys + 192))
    img = img.resize((304 * 3, 192 * 3))
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prg")
    ap.add_argument("labels")
    ap.add_argument("--frames", type=int, default=0, help="(all the script's, if 0)")
    ap.add_argument("--shot", nargs=2, metavar=("FRAME", "FILE"))
    ap.add_argument("--yard", type=int, default=YARD)
    ap.add_argument("--floor", type=int, default=FLOOR)
    args = ap.parse_args()
    floor = walk.Floor(args.yard, args.floor)
    script = sticks(floor)
    args.frames = args.frames or len(script)
    script += [0xFF] * (args.frames + 2 - len(script))
    ref = walk.play(floor, script)
    syms = labels(args.labels)
    c64 = C64(open(args.prg, "rb").read(), syms, script)
    c64.run(args.frames)
    check(c64, floor, ref)
    s = floor.f["stairs"]
    goal = ((s % 3) * 16 + 7, (s // 3) * 8 + 3)
    end = ((ref[-1][0] + 128) >> 8, (ref[-1][1] + 128) >> 8)
    if end != goal:
        fail(f"the walk ends on square {end}, not the stairs' {goal}")
    else:
        ok(f"the walk reaches the stairs, square {goal}, through the floor's doors")
    if args.shot:
        shot(c64, floor, int(args.shot[0]), args.shot[1])
    print(f"walk: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
