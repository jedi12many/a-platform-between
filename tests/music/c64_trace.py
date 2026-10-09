"""The C64's music player (fe/c64/music.s, in build/c64/apb.prg) on py65, a frame at a time:
the registers it leaves in music_ghost, as tools/music/player.py writes them.

    python3 tests/music/c64_trace.py APB.PRG APB.DBG MUSIC TUNE FRAMES [FRAME:COMMAND:ARG ...]
"""

import os
import re
import sys

from py65.devices.mpu6502 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools", "music"))
import player  # noqa: E402

DATA, NOTES, EFFECTS = 0xD800, 0xDE00, 0xDEC0
STOP = 0xFF00
COMMANDS = {"start": 1, "change": 2, "effect": 3, "volume": 4}


def symbols(dbg):
    out = {}
    for line in open(dbg):
        if line.startswith("sym"):
            name = re.search(r'name="([^"]+)"', line)
            val = re.search(r"val=0x([0-9A-Fa-f]+)", line)
            if name and val:
                out[name.group(1)] = int(val.group(1), 16)
    return out


class C64Player:
    def __init__(self, prg, dbg, data):
        self.sym = symbols(dbg)
        self.mpu = MPU()
        mem = self.mpu.memory
        code = open(prg, "rb").read()
        at = code[0] | code[1] << 8
        mem[at:at + len(code) - 2] = list(code[2:])
        mem[DATA:DATA + len(data)] = list(data)
        mem[NOTES:NOTES + 96] = [n & 0xFF for n in player.NOTES]
        mem[NOTES + 96:NOTES + 192] = [n >> 8 for n in player.NOTES]
        flat = [b for e in player.effects() for b in e]
        mem[EFFECTS:EFFECTS + len(flat)] = flat
        self.cycles = 0
        self.call("music_init", len(data) & 0xFF, len(data) >> 8)

    def call(self, name, a=0, x=0):
        m = self.mpu
        m.a, m.x, m.y = a, x, 0
        m.sp = 0xFF
        ret = STOP - 1
        m.memory[0x1FF], m.memory[0x1FE] = ret >> 8, ret & 0xFF
        m.sp = 0xFD
        m.pc = self.sym[name]
        start = m.processorCycles
        for _ in range(200000):
            if m.pc == STOP:
                break
            m.step()
        else:
            raise RuntimeError(f"{name} never returned")
        self.cycles = m.processorCycles - start
        return m.a

    def frame(self):
        self.call("music_frame")
        g = self.sym["music_ghost"]
        return [self.mpu.memory[g + i] for i in range(25)]


def main(argv):
    if len(argv) < 6:
        print(__doc__)
        return 2
    data = open(argv[3], "rb").read()
    p = C64Player(argv[1], argv[2], data)
    p.call("music_command", 1, int(argv[4]))
    script = []
    for c in argv[6:]:
        f, what, arg = c.split(":")
        script.append((int(f), COMMANDS[what], int(arg)))
    most = 0
    for f in range(int(argv[5])):
        for at, what, arg in script:
            if at == f:
                p.call("music_command", what, arg)
        regs = p.frame()
        most = max(most, p.cycles)
        print(" ".join(f"{r:02x}" for r in regs))
    print(f"most cycles in a frame: {most}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
