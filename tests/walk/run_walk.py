"""The walking engine (cart/walk/, docs/walk.md) on an emulated C64, held to its reference
(tools/walk/walk.py) frame by frame.

    python3 tests/walk/run_walk.py PRG LABELS [--yard Y --floor F] [--unseen] [--frames N] [--shot FRAME FILE.png]

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
UNUSED_BITS = {0x16: 0xC0, 0x18: 0x01, 0x19: 0x70, 0x1A: 0xF0,
               **{r: 0xF0 for r in range(0x20, 0x2F)}, 0x2F: 0xFF}
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
    goal = floor.goal
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
        self.hud_shown = {}                 # frame: the HUD's sprites as they started
        self.sprite_start = [None] * 8      # each sprite on: the line its DMA began, its frame,
                                            # and whether it's been recorded
        self.last_bad = None                # the last bad line, and its row
        self.steal_bad = self.steal_sprites = 0     # cycles the VIC will take: tick
        self.ticked = 0
        self.snap = set()                   # frames whose lines are kept (vice_walk.py)...
        self.snaps = {}                     # ...frame: [each line's VIC state]
        self.most_on = 0
        self.frames = []                    # each frame shown: (wk_frame, d016, d011, rows)
        self.seen = None
        self.states = []                    # each loop's: (frame, pos x, pos y, cam x, cam y, stage)
        self.ready = None                   # the frame the fight's setup was done (wk_ready)
        self.see_begun = []                 # the frame each step's checks began
        self.see_steps = []                 # each step's checks (the log) and the frame done
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
        if a & 0x3F in UNUSED_BITS:                 # (the VIC's unused bits read as 1s)
            return self.io[a - 0xD000] | UNUSED_BITS[a & 0x3F]
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
        if self.line == 0:
            self.last_bad = None
            self.picture = self.frame()
        self.sprites_line()
        ys = self.io[0x11] & 7
        if FIRST_DMA_LINE <= self.line <= LAST_DMA_LINE and self.line & 7 == ys and self.io[0x11] & 0x10:
            if self.seen is None:
                self.seen = (self.frame(), self.io[0x16], self.io[0x11], [])
                self.badrow = 0
            base = self.screen_base() + 40 * self.badrow
            self.seen[3].append((bytes(self.ram[base:base + 40]),
                                 bytes(self.colour[40 * self.badrow:40 * self.badrow + 40])))
            self.last_bad = (self.line, self.badrow)
            self.badrow += 1
            self.steal_bad = BADLINE_STEAL          # (taken at the line's cycle 12: tick)
        if getattr(self, "picture", None) in self.snap:
            self.snaps.setdefault(self.picture, []).append(self.snapshot())

    def sprites_line(self):
        """The VIC's sprites on this line, as x64sc has them (tests/walk/vice_walk.py): a
        sprite's DMA starts on the line whose low byte is its Y, if it's on and not showing
        already, and it shows the 21 lines after. Each is recorded, by the frame it started
        in, on its first line in the view with a shape (the empty one is the border's): its
        x, the line it started on, its pointer and colour then; a sprite started under the
        view (the HUD's) on its first line. Each showing takes 2 of the 6502's cycles a line."""
        on = 0
        blank = walk.SHAPE_POINTER + walk.BLANK
        for n in range(8):
            st = self.sprite_start[n]
            if st is not None:
                st[3] += 1                          # (its lines: it may run past line 311)
                if st[3] > 21:
                    st = self.sprite_start[n] = None
            if st is None and self.io[0x15] >> n & 1 and self.io[1 + 2 * n] == self.line & 0xFF:
                st = self.sprite_start[n] = [self.line, self.frame(), False, 0]
            if st is None or st[3] == 0:
                continue
            on += 1
            if st[2]:
                continue
            x = self.io[2 * n] | (self.io[0x10] >> n & 1) << 8
            ptr = self.ram[self.screen_base() + 0x3F8 + n]
            colour = self.io[0x27 + n] & 15
            if st[0] >= walk.LAST_VIEW:
                if st[3] == 2:          # (its second line: the harness's lines
                    self.hud_shown.setdefault(st[1], []).append((x, st[0], ptr, colour))
                    st[2] = True                    # are too coarse for its first fetch)
            elif walk.FIRST_VIEW <= self.line <= walk.LAST_VIEW and ptr != blank:
                self.shown.setdefault(st[1], []).append((x, st[0], ptr, colour))
                self.shown_n.setdefault(st[1], []).append(n)
                st[2] = True
        self.most_on = max(self.most_on, on)
        self.steal_sprites = 2 * on                 # (for the next line: from this one's 55)

    def snapshot(self):
        """This line's VIC state, for drawing it (vice_walk.py): the registers, the row shown
        and its line in it (None: idle), and each sprite showing: x, its line in its shape,
        pointer, colour, multicolour."""
        io = self.io
        row = None
        if self.last_bad is not None and 0 <= self.line - self.last_bad[0] < 8:
            row = (self.last_bad[1], self.line - self.last_bad[0])
        sprites = []
        for n in range(8):
            st = self.sprite_start[n]
            if st is not None and st[3] > 0:
                sprites.append((n, io[2 * n] | (io[0x10] >> n & 1) << 8, st[3] - 1,
                                self.ram[self.screen_base() + 0x3F8 + n], io[0x27 + n] & 15,
                                io[0x1C] >> n & 1))
        return (self.line, io[0x11], io[0x16], io[0x18], row, sprites)

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

    def see_log(self):
        """The step's checks as seeing.s logged them (SEE_LOG): (who looks, band, distance,
        [(roll, total, tn, outcome) of every die]); None if the log overflowed."""
        ram, L = self.ram, self.syms
        if ram[L["see_log_full"]]:
            return None
        checks, a = [], walk.SEE_LOG
        for _ in range(ram[L["see_log_n"]]):
            kind, band, d, _out, n = ram[a:a + 5]
            dice = []
            for j in range(n):
                r, tl, th, nl, nh, res = ram[a + 5 + 6 * j:a + 11 + 6 * j]
                tn = nl | nh << 8
                dice.append((r, tl | th << 8, tn - 65536 if tn & 0x8000 else tn, res))
            checks.append(("band" if kind & 1 else "party", band, d, dice))
            a += 5 + 6 * n
        return checks

    def state(self):
        r, s = self.ram, self.syms
        p, c = s["wk_pos"], s["wk_cam"]
        word = lambda a: r[a] | r[a + 1] << 8
        return (self.frame(), word(p), word(p + 2), word(c), word(c + 2), r[s["wk_stage"]])

    def tick(self):
        """After each instruction: the raster's lines passed, the VIC's cycles taken where
        it takes them (a bad line's from its cycle 12, the sprites' fetches from 55, for the
        next line: the stops the 6502 sees), and the interrupt."""
        m = self.mpu
        while m.processorCycles // LINE != self.ticked:
            self.ticked += 1
            self.new_line()
        cycle = m.processorCycles % LINE
        if self.steal_bad and cycle >= 12:
            m.processorCycles += self.steal_bad
            self.steal_bad = 0
        if self.steal_sprites and cycle >= 55:
            m.processorCycles += self.steal_sprites
            self.steal_sprites = 0
            while m.processorCycles // LINE != self.ticked:
                self.ticked += 1
                self.new_line()
        self.irq()

    def run(self, frames):
        m = self.mpu
        awake, irq, nmi = self.syms["wk_awake"], self.syms["irq"], self.syms["nmi"]
        done = self.syms["wk_done"]
        begin, seen = self.syms.get("wk_begin"), self.syms.get("wk_seen")
        while len(self.states) < frames:
            pc = m.pc
            if pc == begin:
                self.see_begun.append(len(self.states) - 1)
            elif pc == seen:
                self.see_steps.append((self.see_log(), len(self.states) - 1))
            elif pc == awake:
                ready = self.syms.get("wk_ready")
                if ready and self.ready is None and self.ram[ready]:
                    self.ready = len(self.states) - 1
                self.states.append(self.state())
                self.awake_at = m.processorCycles
            elif pc == done and self.awake_at is not None:
                self.loop_cycles.append(m.processorCycles - self.awake_at)
                self.awake_at = None
            elif pc == nmi and self.irq_at is not None:          # the interrupt's RTI
                self.irq_cycles.append(m.processorCycles - self.irq_at)
                self.irq_at = None
            m.step()
            self.tick()
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
        if d016 & 7 != xs or d011 & 7 != ys or d016 & 0x18 != 0x10 or not d011 & 0x10:
            # (the first bad line may be in the band above the view: the mode's the
            # border's there; tests/walk/vice_walk.py holds the picture to x64sc's)
            problems.append(f"registers ${d016:02X} ${d011:02X} for fine scroll {xs}, {ys}")
        want = expected_rows(floor, cam)
        if len(rows) != (24 if ys == 7 else 25):     # (ys 7: row 24, all under the view, isn't)
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
    # The HUD: every frame its 8 sprites, from line 267 (their Y 11), as the floor's asset has
    # them.
    hud = sorted((x, 256 + walk.HUD_Y, walk.SHAPE_POINTER + shape, colour)
                 for x, shape, colour, _ in floor.hud())
    bad = 0
    frames_hud = sorted(f for f in c64.hud_shown if 1 <= f <= len(ref))
    for f in frames_hud:
        if sorted(c64.hud_shown[f]) != hud:
            if bad < 3:
                fail(f"frame {f}: the HUD's sprites were {sorted(c64.hud_shown[f])}, not {hud}")
            bad += 1
    if len(frames_hud) < len(c64.frames) - 2:
        fail(f"the HUD shown in {len(frames_hud)} frames of {len(c64.frames)}")
    elif not bad:
        ok(f"the HUD in every frame ({len(frames_hud)}): its 8 sprites from line 267, the "
           f"travelers' portraits and health")
    late = c64.ram[c64.syms["wk_late"]]
    if late:
        fail(f"{late} frames late: the loop wasn't done when the next frame began")
    busiest = max(c64.loop_cycles) if c64.loop_cycles else 0
    irq = max(c64.irq_cycles) if c64.irq_cycles else 0
    if not late:
        ok(f"no frame late: the busiest loop {busiest} cycles, the busiest interrupt {irq} "
           f"(a frame is {FRAME}, less 25 bad lines' {25 * BADLINE_STEAL})")


def walk_frames(floor, script):
    """How many frames a test walks: the script's, or with a fight on till it's ready (the
    camera and the party still), and a little."""
    if floor.bands:
        walk.play(floor, script + [0xFF] * 2000)
        if walk.play.ready is not None:
            return max(len(script), walk.play.ready + 25)
    return len(script)


def check_fight(c64, fight, ready):
    """The fight's setup (setup.s) as the reference's (walk.Fight): its record (the window,
    its terrain, the party's places, the band's foes) and the frame it was all still. (The
    camera's ease to the window and the travelers' walk to their places are in the frames
    held to the reference above.)"""
    a = c64.syms["fight_rec"]
    got = bytes(c64.ram[a:a + len(fight.record)])
    if got != fight.record:
        first = next(i for i in range(len(got)) if got[i] != fight.record[i])
        fail(f"the fight's record differs at byte {first}: {list(got[first:first + 8])}, the "
             f"reference's {list(fight.record[first:first + 8])}")
    elif c64.ready != ready:
        fail(f"the fight ready at frame {c64.ready}, the reference's {ready}")
    else:
        n = fight.record[2 + 128 + 8]
        ok(f"the fight set up as tools/rooms/rooms.py's: its window at {tuple(fight.window)} (16 x 8, "
           f"its terrain), the party's places {[tuple(fight.record[130 + 2 * k:132 + 2 * k]) for k in range(4)]}, "
           f"the band's {n} foes on it; the camera eased there and the travelers walked to their "
           f"places, all still at frame {ready}")


def check_setups(c64, floor):
    """setup.s on its own, after the walk: every band, the leader on squares near it and
    far (too far for the window to hold both, too), each record as walk.Fight's."""
    import random
    m, ram, L = c64.mpu, c64.ram, c64.syms
    rnd = random.Random(floor.yard * 100 + floor.number)
    stop = 0x0300                               # (free RAM: a JSR and where it returns)
    bad = cases = outside = 0
    for band, b in enumerate(floor.bands):
        for k in range(12):
            if k < 9:
                lx = max(0, min(floor.w - 1, b["x"] + rnd.randrange(-9, 10)))
                ly = max(0, min(floor.h - 1, b["y"] + rnd.randrange(-6, 7)))
            else:
                lx, ly = rnd.randrange(floor.w), rnd.randrange(floor.h)
            ram[L["see_fight"]], ram[L["see_x"]], ram[L["see_y"]] = band + 1, lx, ly
            ram[L["task_on"]] = 0                   # (see_yield: carry on)
            ram[stop:stop + 3] = [0x20, L["fight_setup"] & 255, L["fight_setup"] >> 8]
            m.pc, n = stop, 0
            while m.pc != stop + 3:
                m.step()
                n += 1
                if n > 1_000_000:
                    raise RuntimeError("fight_setup ran away")
            want = walk.Fight(floor, band, lx, ly)
            a = L["fight_rec"]
            cases += 1
            wx, wy = want.window
            outside += not (wx <= lx < wx + 16 and wy <= ly < wy + 8)
            if bytes(ram[a:a + len(want.record)]) != want.record:
                if bad < 3:
                    fail(f"band {band + 1}, the leader at {lx},{ly}: fight_rec "
                         f"{list(ram[a:a + 10])}..., the reference's {list(want.record[:10])}...")
                bad += 1
    if not bad:
        ok(f"setup.s on its own: {cases} fights (every band, the leader near and far: {outside} "
           f"too far for the window to hold both), each record walk.Fight's")


def check_seeing(c64, floor, watch, frames):
    """Seeing (watch.s, seeing.s) as the reference's (walk.play): each step's checks begun
    on the frame its are, every check and die as tools/rules/seeing.py's, all finished in
    time to be shown, and the fight the reference's."""
    want = {}
    for step, who, band, d, dice in watch.checks:
        want.setdefault(step, []).append((who, band, d, dice))
    begun = [-1] + c64.see_begun
    steps = [s for s in walk.play.steps if s < frames - 1]
    if begun[:len(steps)] != steps:
        first = next((i for i, (a, b) in enumerate(zip(begun, steps)) if a != b), min(len(begun), len(steps)))
        fail(f"step {first}'s checks begun on frame {begun[first:first + 1]}, the reference's on "
             f"{steps[first:first + 1]} ({len(begun)} steps against {len(steps)})")
        return
    bad, dice, slowest = 0, 0, 0
    for i, (log, done) in enumerate(c64.see_steps):
        if i >= len(steps):
            break
        slowest = max(slowest, done - begun[i] if i else 0)
        got = log if log is not None else "the log overflowed"
        if got != want.get(i, []):
            if bad < 3:
                fail(f"step {i} (frame {begun[i]}): checks {got}, the reference's {want.get(i, [])}")
            bad += 1
        dice += sum(len(c[3]) for c in want.get(i, []))
    late = c64.ram[c64.syms["see_late"]]
    if late:
        fail(f"{late} steps' checks not finished by the frame they were to be shown")
    fight = c64.ram[c64.syms["shown_fight"]]
    wfight = watch.fight[0] + 1 if watch.fight else 0
    if fight != wfight:
        fail(f"the fight shown: band {fight} (0: none), the reference's {wfight}")
    if not bad and not late and fight == wfight:
        ok(f"seeing: {len(steps)} steps' checks ({sum(map(len, want.values()))} checks, {dice} dice) "
           f"as tools/rules/seeing.py's, die for die, each begun on the reference's frame and "
           f"finished within {slowest} frames (shown after {walk.SEE_SHOWN}); "
           f"{sum(1 for st in watch.state if st['spotted'])} of {len(watch.state)} bands spotted")


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
    ap.add_argument("--unseen", action="store_true", help="its foes all shown, none looking")
    args = ap.parse_args()
    floor = walk.Floor(args.yard, args.floor, unseen=args.unseen)
    script = sticks(floor)
    args.frames = args.frames or walk_frames(floor, script)
    script += [0xFF] * (args.frames + 2 - len(script))
    ref = walk.play(floor, script)
    syms = labels(args.labels)
    c64 = C64(open(args.prg, "rb").read(), syms, script)
    c64.run(args.frames)
    check(c64, floor, ref)
    watch = walk.play.watch
    if watch:
        check_seeing(c64, floor, watch, args.frames)
    goal = floor.goal
    end = ((ref[-1][0] + 128) >> 8, (ref[-1][1] + 128) >> 8)
    if watch and watch.fight is not None:
        band, ambush = watch.fight
        ok(f"band {band + 1} sees the party (" + ("an ambush" if ambush else "spotted first")
           + f"): the walk stops on square {end}, its joystick let go")
        check_fight(c64, walk.play.fight, walk.play.ready)
    if floor.bands:
        check_setups(c64, floor)
    elif end != goal:
        fail(f"the walk ends on square {end}, not the stairs' {goal}")
    else:
        ok(f"the walk reaches the stairs, square {goal}, "
           + f"across the open floor ({floor.w} x {floor.h})")
    if args.shot:
        shot(c64, floor, int(args.shot[0]), args.shot[1])
    print(f"walk: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
