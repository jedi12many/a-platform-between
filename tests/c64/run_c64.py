"""Play a C64 disk image without a C64 (milestone E4, docs/c64.md).

The real program from the .d64 (the same machine code a C64 runs) runs on a 6502
emulator (py65). There are no ROMs: when the program calls into the KERNAL, Python
answers instead, from the disk image: the screen (CHROUT), the keyboard (GETIN and the
key buffer that conio's cgetc reads), and the 1541 (SETLFS, SETNAM, OPEN, CHKIN, CHRIN,
READST, CHKOUT, CLOSE, CLRCHN, LOAD). Any other ROM call stops the run, loudly.

Keys come from a choices file like the terminal's (tests/term/*.choices), one line per
answer: at a "> " prompt (a typed line) the whole line and RETURN; at a menu the line's
first character; at "-- more --" a space, without using a line. The 40-column screen
is written out as the transcript.

    python3 tests/c64/run_c64.py DISK.d64 CHOICES [--then CHOICES2] [--max-steps N]

With --then, the machine is switched off and on again after the first run, with the
disk as the first run left it (a save, say), and plays CHOICES2.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import d64  # noqa: E402

from py65.devices.mpu6502 import MPU  # noqa: E402
from py65.memory import ObservableMemory  # noqa: E402

COLS = 40
STOP_AT = 0xFF00            # where the program returns to when main ends
KEY_COUNT = 0xC6
KBDREAD = 0xE5B4            # the KERNAL's "take a key from the buffer"


def to_ascii(c):
    if 0x41 <= c <= 0x5A:
        return chr(c + 0x20)
    if 0xC1 <= c <= 0xDA:
        return chr(c - 0x80)
    if 0x20 <= c < 0x7F:
        return chr(c)
    return "?"


class Screen:
    def __init__(self):
        self.lines = [""]

    def put(self, c):
        if c == 0x0D:
            self.lines.append("")
        elif c == 0x14:
            self.lines[-1] = self.lines[-1][:-1]
        elif c in (0x93, 0x0E, 0x08, 0x12, 0x92) or c < 0x20 or 0x80 <= c < 0xA0:
            pass                                            # control codes and colours
        else:
            if len(self.lines[-1]) == COLS:
                self.lines.append("")
            self.lines[-1] += to_ascii(c)
            if len(self.lines[-1]) == COLS:
                self.lines.append("")                       # the cursor wraps

    def text(self):
        return "\n".join(line.rstrip() for line in self.lines).rstrip() + "\n"


class C64:
    def __init__(self, image, choices):
        self.files = {name: data for name, (kind, data) in d64.read_files(image).items()}
        self.choices = list(choices)
        self.screen = Screen()
        self.keys = []
        self.mem = ObservableMemory()
        self.mem.subscribe_to_read([KEY_COUNT], self.key_count)
        self.mpu = MPU(memory=self.mem)
        self.lfs = (0, 0, 0)
        self.name = b""
        self.open = {}              # logical file: {"name", "data", "pos", "write"}
        self.chan_in = None
        self.chan_out = None
        self.status = 0
        self.overlays = 0
        self.ended = None

    # ------------------------------------------------------------ keyboard

    def next_answer(self):
        """The keys for whatever the program is waiting for now."""
        line = self.screen.lines[-1]
        if line.endswith("-- more --"):
            return [0x20]
        if not self.choices:
            self.ended = "[end of input]"
            return []
        answer = self.choices.pop(0)
        if line == "> ":
            return [self.petscii(ch) for ch in answer] + [0x0D]
        return [self.petscii(answer[0]) if answer else 0x0D]

    @staticmethod
    def petscii(ch):
        c = ord(ch)
        if 0x61 <= c <= 0x7A:
            return c - 0x20
        if 0x41 <= c <= 0x5A:
            return c + 0x80
        return c

    def key_count(self, address):
        if not self.keys:
            self.keys = self.next_answer()
        return len(self.keys)

    # -------------------------------------------------------------- KERNAL

    def rts(self):
        m = self.mpu
        lo = self.mem[0x100 + ((m.sp + 1) & 0xFF)]
        hi = self.mem[0x100 + ((m.sp + 2) & 0xFF)]
        m.sp = (m.sp + 2) & 0xFF
        m.pc = ((hi << 8) | lo) + 1

    def carry(self, on):
        if on:
            self.mpu.p |= self.mpu.CARRY
        else:
            self.mpu.p &= ~self.mpu.CARRY

    def file_name(self):
        raw = self.name
        write = False
        if raw.startswith(b"@0:"):
            raw = raw[3:]
        parts = raw.split(b",")
        if len(parts) > 2 and parts[2] in (b"w", b"W", b"\xd7"):
            write = True
        return d64.ascii_name(parts[0]), write

    def kernal(self, pc):
        m = self.mpu
        if pc == 0xFFD2:                                    # CHROUT
            if self.chan_out is None:
                self.screen.put(m.a)
            else:
                self.open[self.chan_out]["data"].append(m.a)
            self.carry(False)
        elif pc == KBDREAD or pc == 0xFFE4:                 # take a key
            if not self.keys:
                self.keys = self.next_answer()
            m.a = self.keys.pop(0) if self.keys else 0
            self.mem[KEY_COUNT] = len(self.keys)
        elif pc == 0xFFBA:                                  # SETLFS
            self.lfs = (m.a, m.x, m.y)
        elif pc == 0xFFBD:                                  # SETNAM
            at = m.x | (m.y << 8)
            self.name = bytes(self.mem[at + i] for i in range(m.a))
        elif pc == 0xFFC0:                                  # OPEN
            name, write = self.file_name()
            lfn = self.lfs[0]
            if write:
                self.open[lfn] = {"name": name, "data": bytearray(), "write": True}
            elif name in self.files:
                self.open[lfn] = {"name": name, "data": self.files[name], "pos": 0,
                                  "write": False}
            else:
                self.open[lfn] = {"name": name, "data": b"", "pos": 0, "write": False}
            self.status = 0
            self.carry(False)
        elif pc == 0xFFC3:                                  # CLOSE
            f = self.open.pop(m.a, None)
            if f and f["write"]:
                self.files[f["name"]] = bytes(f["data"])
            self.carry(False)
        elif pc == 0xFFC6:                                  # CHKIN
            self.chan_in = m.x
            self.carry(m.x not in self.open)
        elif pc == 0xFFC9:                                  # CHKOUT
            self.chan_out = m.x
            self.carry(m.x not in self.open)
        elif pc == 0xFFCC:                                  # CLRCHN
            self.chan_in = self.chan_out = None
        elif pc == 0xFFCF:                                  # CHRIN
            f = self.open.get(self.chan_in)
            if not f or f["pos"] >= len(f["data"]):
                m.a = 0x0D
                self.status = 0x42                          # end of file, nothing there
            else:
                m.a = f["data"][f["pos"]]
                f["pos"] += 1
                self.status = 0x40 if f["pos"] >= len(f["data"]) else 0
            self.carry(False)
        elif pc == 0xFFB7:                                  # READST
            m.a = self.status
        elif pc == 0xFFD5:                                  # LOAD
            name, _ = self.file_name()
            data = self.files.get(name)
            if data is None or len(data) < 2:
                m.a = 4                                     # FILE NOT FOUND
                self.carry(True)
            else:
                at = data[0] | (data[1] << 8) if self.lfs[2] else m.x | (m.y << 8)
                for i, b in enumerate(data[2:]):
                    self.mem[at + i] = b
                end = at + len(data) - 2
                m.x, m.y = end & 0xFF, end >> 8
                self.overlays += 1
                self.carry(False)
        else:
            raise RuntimeError(f"the program called ${pc:04X} in the ROM, which isn't emulated")
        self.rts()

    # ----------------------------------------------------------------- run

    def boot(self):
        prg = self.files.get("apb")
        if not prg:
            raise RuntimeError("no program called apb on the disk")
        at = prg[0] | (prg[1] << 8)
        for i, b in enumerate(prg[2:]):
            self.mem[at + i] = b
        self.mem[0x01] = 0x37
        m = self.mpu
        m.sp = 0xFF
        ret = STOP_AT - 1                                   # main's RTS comes here
        self.mem[0x1FF], self.mem[0x1FE] = ret >> 8, ret & 0xFF
        m.sp = 0xFD
        m.pc = 0x080D                                       # past the BASIC SYS line

    def run(self, max_steps):
        m = self.mpu
        steps = 0
        while steps < max_steps and not self.ended:
            pc = m.pc
            if pc == STOP_AT:
                self.ended = "[the program ended]"
                break
            if pc >= 0xE000:
                self.kernal(pc)
            else:
                m.step()
            steps += 1
        if not self.ended:
            self.ended = f"[still running after {steps} steps]"
        return steps


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    max_steps = 400_000_000
    if "--max-steps" in argv:
        max_steps = int(argv[argv.index("--max-steps") + 1])
    with open(argv[1], "rb") as f:
        image = f.read()
    with open(argv[2]) as f:
        choices = [line.rstrip("\n") for line in f]
    runs = [choices]
    if "--then" in argv:
        with open(argv[argv.index("--then") + 1]) as f:
            runs.append([line.rstrip("\n") for line in f])
    files = None
    for n, script in enumerate(runs):
        c64 = C64(image, script)
        if files is not None:
            c64.files = files                               # the same disk, as it was left
        c64.boot()
        try:
            steps = c64.run(max_steps)
            tail = c64.ended
        except RuntimeError as e:
            steps, tail = 0, f"[stopped: {e}]"
        if n:
            print("[switched off and on again]")
        sys.stdout.write(c64.screen.text())
        print(tail)
        print(f"[{steps} 6502 steps, {c64.overlays} files loaded with LOAD]", file=sys.stderr)
        files = c64.files
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
