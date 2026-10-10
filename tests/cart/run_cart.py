"""Play the cartridge, or its disk, without a C64 (docs/cartridge.md, "Building and testing").

    python3 tests/cart/run_cart.py IMAGE LABELS CHOICES EXPECTED [--shot FILE.png] [--update]

IMAGE is the EasyFlash cartridge (build/apb.crt) or the disk (build/apb-disk.d64); LABELS
the linker's label file (ld65 -Ln). The machine code runs on a 6502 emulator (py65), with
the C64 around it played in Python:

- the memory as the C64's PLA maps it, from the CPU's port ($00/$01) and, with the
  cartridge, the EasyFlash's mode ($DE02) and bank ($DE00): Ultimax at power-on (bank 0's
  ROMH at $E000, the reset vector), then 16 KB (ROML at $8000, ROMH at $A000) while
  LORAM and HIRAM say so; the I/O apart from the RAM under it; the EasyFlash's RAM at
  $DF00. A read of a ROM the game should never read (the KERNAL, BASIC, the character
  ROM) stops the run;
- the raster: 63 cycles a line, 312 lines a frame, PAL. Each register access happens on
  its instruction's last cycle, as the 6502's absolute loads and stores do; the raster
  interrupt comes at the start of $D012's line, after the instruction that's running, 7
  cycles to get in, through the 6502's vector in RAM, or, while the KERNAL is in, through
  the KERNAL's own handler (A, X and Y pushed, 29 cycles) and $0314. Bad lines and
  sprites' cycles aren't played: the split's lines (176-178) have neither;
- the disk: the program APB loaded at its address and started at disk_start (as RUN
  would), and the KERNAL's SETNAM, SETLFS and LOAD answered from the .d64. A load takes
  its time all at once, so the frame it ends in isn't held to the split's timing (on a
  real C64 the KERNAL's serial routines hold interrupts off at times too).

- the keyboard: CIA 1's matrix, as the C64's is wired (port A's bit selects a row, port B
  reads its columns, SHIFT where it is), each key held down for two frames and let go
  for two. Keys come from CHOICES, one line an answer, as the C64's tests have them:
  each time the game waits for a key (key_wait), the command row says what for: at
  "-- more --" a space, without using a line; at "> " (a line to type) the whole line and
  RETURN; at anything else (a menu) the line's first character.

The transcript is the story log's bottom row, read each time it scrolls (log_newline), and
each roll's record. It must match EXPECTED (--update writes it: read the diff). The run
ends when CHOICES does, and checks: every change to the frames' registers lands between
line 178's last character and line 179's fetch of row 16 (cycles 56 of line 178 to 11 of
line 179), and the view's in the bottom border; the font, the map's characters and tiles
are where they go (against tools/c64font.py and tools/battlegfx.py's files); the view
shows the map; the frames have their line, the party, the dice; every paragraph of the
transcript is word-wrapped at 25 columns as docs/frames.md says (wrapped again here, it
comes out the same); and no row went off the top of the log unread (never more than 8
rows printed between keys). --shot saves the screen at the end as the VIC-II would show it
(tools/vic.py).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import crt  # noqa: E402
import d64  # noqa: E402

from py65.devices.mpu6502 import MPU  # noqa: E402
from py65.memory import ObservableMemory  # noqa: E402

LINE = 63
LINES = 312
FRAME = LINE * LINES
SPLIT_FIRST = (178, 56)             # the frames' registers change in here...
SPLIT_LAST = (179, 11)              # ...and no later (line 179's bad line stops the 6502)

TEXT, VIEW, CHARS, FONT, STAGING = 0xC000, 0xC400, 0xC800, 0xD000, 0x8000
MEM_FRAMES, MEM_VIEW = 0x04, 0x12
LOG_TOP, LOG_ROWS, LOG_COLS = 16, 8, 25

failures = 0

# The C64's keyboard: MATRIX[row][column], row the bit of $DC00 written 0, column the bit of
# $DC01 read 0 (the C64 Programmer's Reference Guide's table). SHIFT is the left one.
MATRIX = [
    ["DEL", "RETURN", "RIGHT", "F7", "F1", "F3", "F5", "DOWN"],
    ["3", "w", "a", "4", "z", "s", "e", "LSHIFT"],
    ["5", "r", "d", "6", "c", "f", "t", "x"],
    ["7", "y", "g", "8", "b", "h", "u", "v"],
    ["9", "i", "j", "0", "m", "k", "o", "n"],
    ["+", "p", "l", "-", ".", ":", "@", ","],
    ["POUND", "*", ";", "HOME", "RSHIFT", "=", "^", "/"],
    ["1", "LEFTARROW", "CTRL", "2", " ", "C=", "q", "STOP"],
]
SHIFTED = {"!": "1", '"': "2", "#": "3", "$": "4", "%": "5", "&": "6", "'": "7", "(": "8",
           ")": "9", "<": ",", ">": ".", "?": "/", "[": ":", "]": ";"}
LSHIFT = (1, 7)


def key_of(ch):
    """The matrix positions to hold down for an ASCII character (or "RETURN")."""
    shift = False
    if ch in SHIFTED:
        ch, shift = SHIFTED[ch], True
    elif len(ch) == 1 and ch.isupper():
        ch, shift = ch.lower(), True
    for r, row in enumerate(MATRIX):
        if ch in row:
            return [(r, row.index(ch))] + ([LSHIFT] if shift else [])
    raise ValueError(f"no key for {ch!r}")


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  ", msg)


def labels(path):
    out = {}
    for line in open(path):
        parts = line.split()
        if len(parts) == 3 and parts[0] == "al":
            out[parts[2].lstrip(".")] = int(parts[1], 16)
    return out


def screen_ascii(code):
    """Our font's screen code (tools/c64font.py), as ASCII; the frames' glyphs as #, -, =."""
    code &= 0x7F
    if code == 0:
        return "@"
    if 1 <= code <= 26:
        return chr(code + 0x60)
    if 27 <= code <= 31:
        return chr(code + 0x40)
    if 32 <= code <= 63 or 65 <= code <= 90:
        return chr(code)
    if code == 64:
        return "`"
    if 91 <= code <= 94:
        return chr(code + 0x20)
    return {0x60: "|", 0x61: "-", 0x62: "=", 0x63: "#"}.get(code, "?")


def wrap(text, width):
    """The story log's rows (docs/frames.md): a word that doesn't fit goes to the next row,
    one longer than a row is cut; a space between words only where it fits; a newline
    ends the row. The last row is the one the cursor is on."""
    rows, row = [], ""
    i = 0
    while i < len(text):
        c = text[i]
        if c == " ":
            i += 1
            continue
        if c == "\n":
            rows.append(row)
            row = ""
            i += 1
            continue
        j = i
        while j < len(text) and text[j] not in " \n" and j - i < width:
            j += 1
        word = text[i:j]
        if row and len(row) + 1 + len(word) <= width:
            row += " " + word
        elif row:
            rows.append(row)
            row = word
        else:
            row = word
        i = j
    return rows + [row]


class C64:
    def __init__(self, image, syms):
        self.syms = syms
        self.mem = ObservableMemory()
        self.ram = self.mem._subject
        self.io = bytearray(0x1000)
        self.mpu = MPU(memory=self.mem)
        self.chips, self.files = {}, {}
        self.mode = None                    # the EasyFlash's ($DE02), or None: no cartridge
        self.bank = 0
        self.start = self.op = 0            # the instruction running: its first cycle, opcode
        self.line = 0
        self.writes = []                    # (register, value, cycle) of the VIC's
        self.loads = []
        self.held = []                      # matrix positions down now
        self.presses = []                   # [(positions, first frame, last frame)]
        self.lines = []                     # the transcript
        self.choices = []
        self.printed = 0                    # rows into the log since the last key wait
        self.most_printed = 0
        self.mores = 0
        self.ended = None
        self.load_spans = []                # (first, last cycle) of each KERNAL load
        if image[:16] == b"C64 CARTRIDGE   ":
            self.chips, kind = crt.read_bytes(image)
            if kind != crt.EASYFLASH:
                raise RuntimeError(f"cartridge type {kind}, not an EasyFlash")
            self.mode = 5
        else:
            self.files = {n: data for n, (_, data) in d64.read_files(image).items()}
        self.mem.subscribe_to_read(range(0x8000, 0xC000), self.read_cart)
        self.mem.subscribe_to_read(range(0xD000, 0xE000), self.read_io)
        self.mem.subscribe_to_read(range(0xE000, 0x10000), self.read_high)
        self.mem.subscribe_to_write(range(0xD000, 0xE000), self.write_io)

    # ------------------------------------------------------------- the memory map

    def port(self):
        ddr, port = self.ram[0], self.ram[1]
        return ((port & ddr) | (~ddr & 0xFF)) & 7

    def ultimax(self):
        return self.mode == 5

    def io_in(self):
        p = self.port()
        return self.ultimax() or (p & 3 and p & 4)

    def kernal_in(self):
        return not self.ultimax() and self.port() & 2

    def chip(self, half, offset):
        data = self.chips.get((self.bank, half))
        return data[offset] if data else 0xFF

    def read_cart(self, a):
        p = self.port()
        if self.mode in (5, 6, 7) and (self.ultimax() or p & 3 == 3) and a < 0xA000:
            return self.chip("L", a - 0x8000)
        if a >= 0xA000:
            if self.mode == 7 and p & 2:
                return self.chip("H", a - 0xA000)
            if self.mode in (None, 4, 6) and p & 3 == 3:
                raise RuntimeError(f"read ${a:04X}: BASIC's ROM")
        return None

    def read_high(self, a):
        if self.ultimax():
            return self.chip("H", a - 0xE000)
        if self.kernal_in() and not self.kernal_call:
            raise RuntimeError(f"read ${a:04X}: the KERNAL's ROM (pc ${self.mpu.pc:04X})")
        return None

    def access(self):
        """The cycle the running instruction reads or writes on: its last."""
        return self.start + self.mpu.cycletime[self.op] - 1

    def read_io(self, a):
        if not self.io_in():
            if self.port() & 3:
                raise RuntimeError(f"read ${a:04X}: the character ROM")
            return None
        i = a - 0xD000
        if a == 0xD012:
            return (self.access() // LINE) % LINES & 0xFF
        if a == 0xD011:
            return (self.io[i] & 0x7F) | (((self.access() // LINE) % LINES) >> 8) << 7
        if a == 0xDC01:                                     # the columns of the rows selected
            frame = self.access() // FRAME
            rows = ~self.io[0xC00] & 0xFF
            value = 0xFF
            for keys, first, last in self.presses:
                if first <= frame <= last:
                    for r, col in keys:
                        if rows >> r & 1:
                            value &= ~(1 << col) & 0xFF
            return value
        if a == 0xDC00:
            return 0xFF
        return self.io[i]

    def write_io(self, a, v):
        if not self.io_in():
            return None                                     # the RAM under it
        i = a - 0xD000
        if a == 0xD019:
            self.io[i] &= ~v & 0xFF
        elif a == 0xDE00 and self.mode is not None:
            self.bank = v & 0x3F
        elif a == 0xDE02 and self.mode is not None:
            self.mode = v & 7 if v & 4 else 5
        else:
            self.io[i] = v
        if a in (0xD011, 0xD016, 0xD018):
            self.writes.append((a, v, self.access()))
        return self.ram[a]                                  # the RAM keeps its own

    # ------------------------------------------------------------- the raster

    def raster(self):
        m = self.mpu
        line = (m.processorCycles // LINE) % LINES
        if line != self.line:
            target = self.io[0x12] | (self.io[0x11] & 0x80) << 1
            while self.line != line:
                self.line = (self.line + 1) % LINES
                if self.line == target:
                    self.io[0x19] |= 0x81
        if self.io[0x19] & self.io[0x1A] & 1 and not m.p & m.INTERRUPT:
            pc = m.pc
            for b in (pc >> 8, pc & 0xFF, (m.p & ~m.BREAK) | m.UNUSED):
                self.ram[0x100 + m.sp] = b
                m.sp = (m.sp - 1) & 0xFF
            m.p |= m.INTERRUPT
            m.processorCycles += 7
            if self.ultimax():
                m.pc = self.chip("H", 0x1FFE) | self.chip("H", 0x1FFF) << 8
            elif self.kernal_in():                          # the KERNAL's handler: A, X, Y
                for b in (m.a, m.x, m.y):
                    self.ram[0x100 + m.sp] = b
                    m.sp = (m.sp - 1) & 0xFF
                m.processorCycles += 29
                m.pc = self.ram[0x314] | self.ram[0x315] << 8
            else:
                m.pc = self.ram[0xFFFE] | self.ram[0xFFFF] << 8

    # ------------------------------------------------------------- the KERNAL (disks)

    kernal_call = False

    def kernal(self, pc):
        m = self.mpu
        if pc == 0xFFBA:                                    # SETLFS
            self.lfs = (m.a, m.x, m.y)
        elif pc == 0xFFBD:                                  # SETNAM
            at = m.x | (m.y << 8)
            self.name = d64.ascii_name(bytes(self.ram[at + i] for i in range(m.a)))
        elif pc == 0xFFD5:                                  # LOAD, to X/Y with SA 0
            data = self.files.get(self.name)
            if data is None or len(data) < 2:
                m.a = 4
                m.p |= m.CARRY
            else:
                at = data[0] | data[1] << 8 if self.lfs[2] else m.x | (m.y << 8)
                for i, b in enumerate(data[2:]):
                    self.ram[at + i] = b
                self.loads.append(self.name)
                start = m.processorCycles
                m.processorCycles += 20 * len(data)         # (it takes its time)
                self.load_spans.append((start, m.processorCycles))
                m.p &= ~m.CARRY
        else:
            raise RuntimeError(f"the program called ${pc:04X} in the KERNAL, not emulated")
        lo = self.ram[0x100 + ((m.sp + 1) & 0xFF)]
        hi = self.ram[0x100 + ((m.sp + 2) & 0xFF)]
        m.sp = (m.sp + 2) & 0xFF
        m.pc = ((hi << 8) | lo) + 1

    # ------------------------------------------------------------- running

    def boot(self):
        m = self.mpu
        if self.mode is not None:                           # power-on, Ultimax
            m.pc = self.chip("H", 0x1FFC) | self.chip("H", 0x1FFD) << 8
            return
        prg = self.files["apb"]
        at = prg[0] | prg[1] << 8
        for i, b in enumerate(prg[2:]):
            self.ram[at + i] = b
        self.ram[0], self.ram[1] = 0x2F, 0x37
        self.ram[0xBA] = 8
        m.sp = 0xF6
        m.pc = self.syms["disk_start"]

    def row23(self):
        return self.screen(TEXT, 23, LOG_COLS).rstrip()

    def command_row(self):
        return self.screen(TEXT, 24).rstrip()

    def answer(self):
        """The keys for what the game waits for now (the command row says), pressed from
        the next frame on: each held two frames, let go two."""
        row = self.command_row()
        self.most_printed = max(self.most_printed, self.printed)
        if row.endswith("-- more --"):
            keys = [" "]
            self.mores += 1
        else:
            if not self.choices:
                self.ended = "[end of input]"
                return
            line = self.choices.pop(0)
            keys = list(line) + ["RETURN"] if row.startswith(">") else [line[:1] or "RETURN"]
        self.printed = 0
        frame = self.mpu.processorCycles // FRAME + 1
        for k in keys:
            self.presses.append((key_of(k), frame, frame + 1))
            frame += 4
        self.answer_until = frame * FRAME

    answer_until = 0

    def run(self, max_frames=3000):
        m = self.mpu
        wait, wait_end = self.syms["key_wait"], self.syms["log_more"]
        newline = self.syms["log_newline"]
        while not self.ended:
            pc = m.pc
            if wait <= pc < wait_end and m.processorCycles >= self.answer_until:
                self.answer()                               # (key_wait, waiting)
            elif pc == newline:
                self.lines.append(self.row23())
                self.printed += 1
            if m.processorCycles > max_frames * FRAME:
                self.ended = f"[still running after {max_frames} frames]"
            if pc >= 0xE000 and self.kernal_in():
                self.kernal(pc)
                continue
            self.start, self.op = m.processorCycles, self.mem[pc]
            m.step()
            self.raster()
        return self.ended

    def screen(self, base, row, n=40, at=0):
        return "".join(screen_ascii(self.ram[base + row * 40 + at + i]) for i in range(n))


def shot(c, path):
    import vic
    from PIL import Image
    import c64pic
    io = c.io
    scr = vic.Screen(bytes(c.ram[CHARS:CHARS + 2048]), io[0x21] & 15, io[0x22] & 15,
                     io[0x23] & 15, io[0x25] & 15, io[0x26] & 15)
    for i in range(1000):
        if i < 640:
            scr.put(i % 40, i // 40, c.ram[VIEW + i], io[0x800 + i] & 15)
        else:
            scr.put(i % 40, i // 40, 0, 0)
    img = scr.image()
    font = bytes(c.ram[FONT:FONT + 2048])
    for row in range(16, 25):
        for x in range(40):
            code = c.ram[TEXT + row * 40 + x]
            ink = c64pic.PALETTE[io[0x800 + row * 40 + x] & 15]
            for y in range(8):
                bits = font[code * 8 + y]
                for dx in range(8):
                    img.putpixel((x * 8 + dx, row * 8 + y), ink if bits >> (7 - dx) & 1 else (0, 0, 0))
    framed = Image.new("RGB", (384, 264), vic.PALETTE[io[0x20] & 15])
    framed.paste(img, (32, 32))
    framed.resize((768, 528), Image.NEAREST).save(path)


def check(c):
    syms = c.syms
    disk = c.mode is None
    what = "the disk" if disk else "the cartridge"
    # While the KERNAL loads, its serial routines hold interrupts off at times, so the
    # frame a load ends in may split late: those aren't counted.
    c.writes = [w for w in c.writes
                if not any(a <= w[2] <= b + FRAME for a, b in c.load_spans)]
    # The split, every frame.
    frames_regs = [w for w in c.writes if (w[0] == 0xD018 and w[1] == MEM_FRAMES)
                   or (w[0] == 0xD016 and w[1] == 0x08) or (w[0] == 0xD011 and w[1] == 0x1B
                                                            and (w[2] // LINE) % LINES > 100
                                                            and (w[2] // LINE) % LINES < 200)]
    late = [(hex(a), (cyc // LINE) % LINES, cyc % LINE) for a, v, cyc in frames_regs
            if not SPLIT_FIRST <= ((cyc // LINE) % LINES, cyc % LINE) <= SPLIT_LAST]
    n = sum(1 for a, v, _ in frames_regs if a == 0xD018)
    if late or n < 20:
        fail(f"{what}: the split's writes out of the gap: {late[:6]} ({n} splits)")
    else:
        cycles = sorted({cyc % LINE for a, v, cyc in frames_regs if a == 0xD018})
        ok(f"{what}: {n} splits, each write between line 178's last character and line 179's "
           f"fetch ($D018 at cycles {cycles[0]}-{cycles[-1]} of line 178)")
    views = [((cyc // LINE) % LINES) for a, v, cyc in c.writes if a == 0xD018 and v == MEM_VIEW]
    if not views or any(not 250 <= ln <= 260 for ln in views):
        fail(f"{what}: the view's registers outside the bottom border: {sorted(set(views))}")
    else:
        ok(f"{what}: the view's registers set in the bottom border (lines {min(views)}-{max(views)})")
    # Where the game left the machine.
    if c.ram[1] != 0x35 or (not disk and (c.io[0xF00] != 0 or c.bank != 0)):
        fail(f"{what}: at rest, $01 = ${c.ram[1]:02X}, bank {c.bank}, its shadow {c.io[0xF00]}")
    else:
        ok(f"{what}: at rest with $01 = $35" + ("" if disk else ", bank 0 (and its shadow)"))
    # The graphics, against the tools' own files.
    font = open(os.path.join(ROOT, "build", "cart", "font"), "rb").read()[2:]
    gfx = open(os.path.join(ROOT, "build", "battle.bgfx"), "rb").read()
    tables, charset = gfx[:640], gfx[640:640 + 2048]
    tile_table = tables[8:8 + 256]
    if bytes(c.ram[FONT:FONT + 2048]) != font:
        fail(f"{what}: the font under the I/O isn't tools/c64font.py's")
    elif bytes(c.ram[CHARS:CHARS + 2048]) != charset:
        fail(f"{what}: the map's characters aren't tools/battlegfx.py's")
    elif bytes(c.ram[syms["tiles"]:syms["tiles"] + 256]) != tile_table:
        fail(f"{what}: the tiles' table isn't tools/battlegfx.py's")
    else:
        ok(f"{what}: the font, the map's characters and its tiles, from asset 0, where they go")
    if disk and c.loads != ["a00", "a01"]:
        fail(f"the disk: loaded {c.loads}, not a00 then a01")
    elif disk:
        ok("the disk: assets 0 and 1 loaded as files a00 and a01")
    # The view: the demo's map, 4 x 4 characters a square.
    themap = bytes(c.ram[syms["demo_map"]:syms["demo_map"] + 40])
    bad = []
    for sq in range(40):
        t = themap[sq]
        for k in range(16):
            row, col = (sq // 10) * 4 + k // 4, (sq % 10) * 4 + k % 4
            want_ch, want_col = tile_table[t * 32 + k], tile_table[t * 32 + 16 + k]
            if c.ram[VIEW + row * 40 + col] != want_ch or c.io[0x800 + row * 40 + col] & 15 != want_col & 15:
                bad.append((sq, k))
    if bad:
        fail(f"{what}: the view's tiles differ from the map at {bad[:5]}")
    else:
        ok(f"{what}: the view shows the map, 10 x 4 squares of 4 x 4 characters")
    # The frames.
    line = "".join(c.screen(TEXT, r, 1, 25) for r in range(16, 24))
    party = c.screen(TEXT, 16, 14, 26)
    dice = (c.screen(TEXT, 22, 14, 26), c.screen(TEXT, 23, 14, 26))
    if line != "|" * 8:
        fail(f"{what}: the line between the frames: {line!r}")
    elif party != ">Kestrel ####=":
        fail(f"{what}: the party frame: {party!r}")
    elif dice != ("Kestrel 94    ", "vs 60: hit 23 "):
        fail(f"{what}: the dice log: {dice!r}")
    else:
        ok(f"{what}: the frames: their line, the party ({party.strip()}), the dice ({' / '.join(d.strip() for d in dice)})")
    # The transcript's paragraphs, wrapped again here: the same.
    bad = []
    para = []
    for line in c.lines + [""]:
        menu = line[:1].isdigit() and line[1:2] == "."
        if line and not line.startswith("[") and not line.startswith(">") and not menu:
            para.append(line)
            continue
        if para and wrap(" ".join(para), LOG_COLS) != para:
            bad.append(para)
        para = []
    if bad:
        fail(f"{what}: paragraphs not wrapped at 25 as docs/frames.md says: {bad[:2]}")
    else:
        ok(f"{what}: every paragraph word-wrapped at 25 columns")
    if c.most_printed > LOG_ROWS or not c.mores:
        fail(f"{what}: {c.most_printed} rows printed between keys, {c.mores} -- more --")
    else:
        ok(f"{what}: nothing scrolled off unread (at most {c.most_printed} rows between keys; "
           f"{c.mores} times -- more --)")


def main(argv):
    if len(argv) < 5:
        print(__doc__)
        return 2
    image = open(argv[1], "rb").read()
    syms = labels(argv[2])
    c = C64(image, syms)
    c.choices = [line.rstrip("\n") for line in open(argv[3])]
    c.boot()
    try:
        ended = c.run()
    except RuntimeError as e:
        fail(f"{argv[1]}: stopped: {e}")
        return 1
    got = "\n".join(c.lines + [ended]) + "\n"
    if "--update" in argv:
        with open(argv[4], "w") as f:
            f.write(got)
    if got != open(argv[4]).read():
        import difflib
        fail(f"{argv[1]}: the transcript differs from {argv[4]}:\n" + "".join(
            difflib.unified_diff(open(argv[4]).read().splitlines(True), got.splitlines(True),
                                 "expected", "got", n=1)))
    else:
        ok(f"{argv[1]}: the transcript is {argv[4]}'s ({len(c.lines)} lines)")
    check(c)
    if "--shot" in argv:
        shot(c, argv[argv.index("--shot") + 1])
    print(f"{argv[1]}: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
