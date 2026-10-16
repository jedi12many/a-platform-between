"""x64sc, VICE's cycle-exact C64, driven through its remote monitor, for checks that need
the real VIC-II's timing (tests/walk/vice_walk.py).

VICE's Debian package comes without Commodore's ROMs, and the programs checked here take
the whole machine, so it's given stand-ins: a KERNAL whose reset sets the CPU's port and
stack and waits, and an empty BASIC and character ROM. The program is loaded and started
from the monitor."""

import os
import re
import shutil
import socket
import subprocess
import tempfile
import time

PALETTE_FILE = "/usr/share/vice/C64/colodore.vpl"


def available():
    return shutil.which("x64sc") and shutil.which("xvfb-run") and os.path.exists(PALETTE_FILE)


def palette():
    """The palette the screenshots are in: RGB -> colour 0-15."""
    rgb = [tuple(int(v, 16) for v in line.split()[:3])
           for line in open(PALETTE_FILE) if line.strip() and not line.startswith("#")]
    return {c: i for i, c in enumerate(rgb[:16])}


def stand_in_roms(where):
    k = bytearray(8192)
    reset = [0x78, 0xA2, 0xFF, 0x9A, 0xA9, 0x2F, 0x85, 0x00, 0xA9, 0x37, 0x85, 0x01,
             0x4C, 0x0C, 0xE0]                   # sei, ldx #$ff, txs, $00/$01, jmp *
    k[:len(reset)] = bytes(reset)
    k[0x1FF0] = 0x40                             # $FFF0: rti
    for vector, at in ((0x1FFA, 0xFFF0), (0x1FFC, 0xE000), (0x1FFE, 0xFFF0)):
        k[vector], k[vector + 1] = at & 255, at >> 8
    for name, data in (("kernal", k), ("basic", bytes(8192)), ("chargen", bytes(4096))):
        open(os.path.join(where, name + ".bin"), "wb").write(data)


class Vice:
    """One x64sc, stopped and started through its monitor."""

    def __init__(self, port=None):
        if port is None:                         # a free one
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
        self.dir = tempfile.mkdtemp(prefix="vice-")
        stand_in_roms(self.dir)
        d = self.dir
        self.proc = subprocess.Popen(
            ["xvfb-run", "-a", "x64sc", "-default", "-kernal", f"{d}/kernal.bin",
             "-basic", f"{d}/basic.bin", "-chargen", f"{d}/chargen.bin",
             "-sounddev", "dummy", "+confirmonexit", "-warp", "-VICIIborders", "2",
             "-VICIIfilter", "0", "-VICIIextpal", "-VICIIpalette", PALETTE_FILE,
             "-remotemonitor", "-remotemonitoraddress", f"ip4://127.0.0.1:{port}"],
            stdout=open(f"{d}/vice.log", "w"), stderr=subprocess.STDOUT)
        for _ in range(300):
            try:
                self.s = socket.create_connection(("127.0.0.1", port))
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("x64sc's monitor never answered")
        self.s.settimeout(300)
        self.running = True

    PROMPT = rb"\(C:\$[0-9a-f]{4}\) $"

    def _read(self, pattern, quiet=0.03):
        """Until pattern has come and then nothing more for a moment: the monitor drops a
        line sent while it's still answering, and its prompts come one or two at a time."""
        buf = b""
        while not re.search(pattern, buf):
            data = self.s.recv(65536)
            if not data:
                raise RuntimeError("x64sc's monitor closed")
            buf += data
        self.s.settimeout(quiet)
        try:
            while True:
                data = self.s.recv(65536)
                if not data:
                    break
                buf += data
        except socket.timeout:
            pass
        finally:
            self.s.settimeout(300)
        return buf.decode("latin-1")

    def cmd(self, command):
        """A monitor command (the machine stops for it); what it said."""
        self.s.sendall(command.encode() + b"\n")
        out = self._read(rb"(?s)\(C:.*\(C:\$[0-9a-f]{4}\) $" if self.running else self.PROMPT)
        self.running = False
        return out

    def go(self, command="x"):
        """Run on (x, or g ADDR) until a breakpoint stops the machine."""
        self.s.sendall(command.encode() + b"\n")
        self.running = False
        return self._read(rb"(?s)Stop on.*\(C:\$[0-9a-f]{4}\) $")

    def peek(self, addr, n=1):
        out = self.cmd(f"m {addr:04x} {addr + n - 1:04x}")
        vals = []
        for line in out.splitlines():
            m = re.match(r">C:([0-9a-f]{4})\s+((?:[0-9a-f]{2}\s+)+)", line)
            if m:
                vals += [int(v, 16) for v in m.group(2).split()]
        return vals[:n]

    def screenshot(self, path):
        if os.path.exists(path):
            os.remove(path)
        self.cmd(f'screenshot "{path}" 2')
        for _ in range(100):                     # (it's written as the machine runs on)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                return
            time.sleep(0.02)
        raise RuntimeError("no screenshot")

    def quit(self):
        try:
            self.s.sendall(b"quit\n")
        except OSError:
            pass
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        shutil.rmtree(self.dir, ignore_errors=True)
