"""The music player's reference (docs/music.md), written from the doc: what the SID's 25
registers hold after each frame. The C player (client/music.c) and the 6502 player
(fe/c64/music.s) must give the same, frame by frame.

    python3 tools/music/player.py MUSIC TUNE FRAMES      the registers, a frame a line (hex)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

PAL_CLOCK = 985248

NOTES = [min(0xFFFF, round(440 * 2 ** ((n - 57) / 12) * (1 << 24) / PAL_CLOCK)) for n in range(96)]

# client/sfx.c's table, as the doc says it is (waveform, pitch, slide, AD, SR, frames).
EFFECTS = None


def effects():
    """The sound effects, read from client/sfx.c (the one table, for every machine)."""
    global EFFECTS
    if EFFECTS is None:
        import re
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                                "client", "sfx.c")).read()
        body = src.split("apb_sfx[APB_SFX_COUNT][6] = {", 1)[1].split("};", 1)[0]
        EFFECTS = [[int(v, 16) if v.startswith("0x") else int(v) for v in
                    re.findall(r"0x[0-9A-Fa-f]+|\d+", row)]
                   for row in re.findall(r"\{([^}]*)\}", body)]
    return EFFECTS


class Voice:
    def __init__(self):
        self.stopped = True
        self.has_note = False
        self.seq = self.seq_start = 0
        self.loop = None
        self.pat = 0
        self.transpose = 0
        self.length = 1
        self.instrument = 0
        self.frames = 0
        self.note = 0
        self.slur_next = False
        self.slur = False
        self.gate = 0
        self.step = 0
        self.control = 0
        self.pitch = 0
        self.pulse = 0
        self.sweep = 0
        self.vib_count = 0
        self.vib_phase = 0
        self.vib_offset = 0
        self.vib_step = 0


class Player:
    def __init__(self, data):
        self.d = bytes(data)
        self.ok = (8 <= len(self.d) <= 1536 and self.d[:3] == b"MU\x01" and 1 <= self.d[3] <= 32
                   and self.d[4] <= 32 and self.d[5] <= 128 and self.d[6] <= 128
                   and len(self.d) >= 8 + 8 * self.d[3] + 10 * self.d[4] + 2 * self.d[5]
                   + 2 * self.d[6])
        self.voices = [Voice() for _ in range(3)]
        self.regs = [0] * 25
        self.volume = 15
        self.target = 15
        self.fade_count = 0
        self.next_tune = None
        self.tempo = 2
        self.commands = []
        self.fx = None              # [effect, frames left, release frames left, pitch]
        self.v3_restart = False

    # ------------------------------------------------------------- the file
    def byte(self, at):
        """A byte of the file, or None past its end."""
        return self.d[at] if 0 <= at < len(self.d) else None

    def word(self, at):
        lo, hi = self.byte(at), self.byte(at + 1)
        return None if lo is None or hi is None else lo | hi << 8

    def counts(self):
        return self.d[3], self.d[4], self.d[5], self.d[6]

    def instrument_at(self, i):
        T, N, W, P = self.counts()
        return 8 + 8 * T + 10 * i

    def steps_at(self):
        T, N, W, P = self.counts()
        return 8 + 8 * T + 10 * N

    def patterns_at(self):
        T, N, W, P = self.counts()
        return 8 + 8 * T + 10 * N + 2 * W

    # ------------------------------------------------------------- commands
    def start(self, t):
        self.commands.append(("start", t))

    def change(self, t):
        self.commands.append(("change", t))

    def effect(self, e):
        self.commands.append(("effect", e))

    def set_volume(self, v):
        self.commands.append(("volume", v))

    def do_start(self, t):
        self.voices = [Voice() for _ in range(3)]
        self.volume = self.target = 15
        self.next_tune = None
        if not self.ok or t >= self.d[3]:
            return
        at = 8 + 8 * t
        self.tempo = self.d[at]
        if not 2 <= self.tempo <= 31:
            return
        for i, v in enumerate(self.voices):
            seq = self.word(at + 2 + 2 * i)
            if seq is None:
                continue
            v.stopped = False
            v.seq = seq
            if not self.next_pattern(v):
                v.stopped = True

    def next_pattern(self, v):
        """On through the sequence to the next pattern. False: the voice stops."""
        for _ in range(63):
            b = self.byte(v.seq)
            if b is None:
                return False
            v.seq += 1
            if b == 0xFE:
                v.loop = v.seq
            elif b == 0xFF:
                if v.loop is None:
                    return False
                v.seq = v.loop
            elif b >= 0xC0:
                return False
            elif b >= 0x80:
                v.transpose = b - 0xA0
            else:
                T, N, W, P = self.counts()
                if b >= P:
                    return False
                at = self.word(self.patterns_at() + 2 * b)
                if at is None:
                    return False
                v.pat = at
                return True
        return False

    def stop(self, v):
        v.stopped = True
        v.gate = 0

    def fetch(self, v):
        """The next event. False: the voice stopped."""
        for _ in range(255):
            b = self.byte(v.pat)
            if b is None:
                return False
            v.pat += 1
            if b == 0xFF:
                if not self.next_pattern(v):
                    return False
            elif b == 0xE0:
                v.slur_next = True
            elif 0xC0 <= b <= 0xDF:
                if (b & 0x1F) >= self.d[4]:
                    return False
                v.instrument = b & 0x1F
            elif 0x80 <= b <= 0xBF:
                v.length = (b & 0x3F) + 1
            elif b <= 0x61:
                legato = v.slur
                v.slur = v.slur_next
                v.slur_next = False
                v.frames = v.length * self.tempo
                if b == 0x60:
                    v.gate = 0
                elif b <= 0x5F:
                    v.note = min(95, max(0, b + v.transpose))
                    ins = self.instrument_at(v.instrument)
                    if self.byte(ins + 9) is None or not self.d[4]:
                        return False
                    if not (legato and v.has_note):
                        v.has_note = True
                        v.gate = 1
                        v.step = self.d[ins + 2]
                        v.pulse = self.d[ins + 3] << 4
                        v.sweep = self.d[ins + 4] - 256 if self.d[ins + 4] >= 128 else self.d[ins + 4]
                        v.vib_count = 0
                        v.vib_phase = 0
                        v.vib_offset = 0
                    depth = self.d[ins + 8]
                    nxt = min(95, v.note + 1)
                    v.vib_step = (NOTES[nxt] - NOTES[v.note]) >> depth if depth else 0
                return True
            else:
                return False
        return False

    # ---------------------------------------------------------------- a frame
    def frame(self):
        """One frame; returns the 25 registers."""
        for cmd, arg in self.commands:
            if cmd == "start":
                self.do_start(arg)
            elif cmd == "change":
                self.next_tune = arg
                self.target = 0
                self.fade_count = 0
            elif cmd == "effect":
                fx = effects()
                if arg < len(fx):
                    self.fx = [arg, fx[arg][5], 12, fx[arg][1], True]
            elif cmd == "volume":
                self.volume = self.target = arg & 15
        self.commands = []
        # Fading.
        if self.volume != self.target:
            self.fade_count += 1
            if self.fade_count >= 2:
                self.fade_count = 0
                self.volume += 1 if self.target > self.volume else -1
        if self.volume == 0 and self.target == 0 and self.next_tune is not None:
            t = self.next_tune
            if t == 255:
                self.voices = [Voice() for _ in range(3)]
                self.next_tune = None
            else:
                self.do_start(t)
        for i, v in enumerate(self.voices):
            self.voice_frame(v)
            self.write(i, v)
        if self.fx is not None:
            self.effect_frame()
        self.regs[21] = self.regs[22] = self.regs[23] = 0
        self.regs[24] = self.volume
        return list(self.regs)

    def voice_frame(self, v):
        if v.stopped:
            return
        if v.frames:
            v.frames -= 1
        if v.frames == 0:
            if not self.fetch(v):
                self.stop(v)
                return
        if v.frames == 1 and not v.slur and v.has_note:
            v.gate = 0
        if not v.has_note:
            return
        ins = self.instrument_at(v.instrument)
        # The waveform table.
        W = self.d[5]
        base = self.steps_at()
        if v.step < W:
            c, p = self.d[base + 2 * v.step], self.d[base + 2 * v.step + 1]
            if c == 0xFF:
                v.step = p
                if v.step < W and self.d[base + 2 * v.step] != 0xFF:
                    v.control = self.d[base + 2 * v.step]
                    v.pitch = self.d[base + 2 * v.step + 1]
                    v.step += 1
            else:
                v.control, v.pitch = c, p
                v.step += 1
        # The pulse width.
        if self.d[ins + 4]:
            v.pulse += v.sweep
            high, low = self.d[ins + 6] << 4, self.d[ins + 5] << 4
            if v.pulse > high:
                v.pulse = high
                v.sweep = -v.sweep
            elif v.pulse < low:
                v.pulse = low
                v.sweep = -v.sweep
        # Vibrato.
        depth, delay, speed = self.d[ins + 8], self.d[ins + 7], self.d[ins + 9]
        if depth:
            if v.vib_count < 255:
                v.vib_count += 1
            if v.vib_count > delay:
                if v.vib_phase < speed or v.vib_phase >= 3 * speed:
                    v.vib_offset += v.vib_step
                else:
                    v.vib_offset -= v.vib_step
                v.vib_phase += 1
                if v.vib_phase >= 4 * speed:
                    v.vib_phase = 0

    def write(self, i, v):
        if i == 2 and self.fx is not None:
            return                      # voice 3 is the effect's
        r = 7 * i
        if v.has_note:
            ins = self.instrument_at(v.instrument)
            if v.pitch & 0x80:
                n = min(95, v.pitch & 0x7F)
            else:
                rel = v.pitch - 128 if v.pitch & 0x40 else v.pitch
                n = min(95, max(0, v.note + rel))
            f = (NOTES[n] + v.vib_offset) & 0xFFFF
            self.regs[r], self.regs[r + 1] = f & 0xFF, f >> 8
            self.regs[r + 2], self.regs[r + 3] = v.pulse & 0xFF, (v.pulse >> 8) & 0x0F
            self.regs[r + 5], self.regs[r + 6] = self.d[ins], self.d[ins + 1]
            self.regs[r + 4] = (v.control & 0xFE) | v.gate
        else:
            self.regs[r + 4] &= 0xFE

    def effect_frame(self):
        e = effects()[self.fx[0]]
        first = self.fx[4]
        self.fx[4] = False
        if not first:
            if self.fx[1]:
                self.fx[1] -= 1
                if self.fx[1]:
                    self.fx[3] = (self.fx[3] + e[2]) & 0xFF
            else:
                self.fx[2] -= 1
                if self.fx[2] == 0:
                    self.fx = None
                    v = self.voices[2]
                    v.gate = 0
                    self.write(2, v)
                    return
        gate = 1 if self.fx[1] else 0
        self.regs[14], self.regs[15] = 0, self.fx[3]
        self.regs[16], self.regs[17] = 0, 8
        self.regs[18] = (e[0] & 0xFE) | gate
        self.regs[19], self.regs[20] = e[3], e[4]


def trace(data, tune, frames, commands=None):
    """The registers for each frame of a tune; commands: {frame: [(cmd, arg)]}."""
    p = Player(data)
    p.start(tune)
    out = []
    for f in range(frames):
        for cmd, arg in (commands or {}).get(f, []):
            getattr(p, {"start": "start", "change": "change", "effect": "effect",
                        "volume": "set_volume"}[cmd])(arg)
        out.append(p.frame())
    return out


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    data = open(argv[1], "rb").read()
    for regs in trace(data, int(argv[2]), int(argv[3])):
        print(" ".join(f"{r:02x}" for r in regs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
