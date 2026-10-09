"""Play a C64 disk image without a C64 (milestone E4, docs/c64.md).

The real program from the .d64 (the same machine code a C64 runs) runs on a 6502
emulator (py65). There are no ROMs: when the program calls into the KERNAL, Python
answers instead, from the disk image: the screen (CHROUT), the keyboard (GETIN and the
key buffer that conio's cgetc reads), and the 1541 (SETLFS, SETNAM, OPEN, CHKIN, CHRIN,
READST, CHKOUT, CLOSE, CLRCHN, LOAD). Any other ROM call stops the run, loudly.

The front end writes text straight into screen memory, at the bottom row of its
window, and scrolls the window up in newline(). So the transcript is the bottom row,
read each time newline() starts (its address comes from the linker's debug file,
SYMBOLS). Loading a picture adds a line "[picture picNN]".

A fight is on the battle screen (fe/c64/scene.c): its words come from hal_scene_log,
which the harness reads (the C64 shows them nowhere), its waits for frames are skipped
(there are no interrupts here), and each line of the choices file is one key. The
picture the C64 loads again after a fight isn't a new picture, so isn't in the record.

Keys come from a choices file like the terminal's (tests/term/*.choices), one line per
answer: at a "> " prompt (a typed line) the whole line and RETURN; at a menu the line's
first character; at "-- more --" a space, without using a line.

The C stack is watched too: a run that uses more than STACK_LIMIT bytes of it fails,
as the memory map (fe/c64/apb.cfg) only has room for 512.

    python3 tests/c64/run_c64.py DISK.d64 SYMBOLS CHOICES [--then CHOICES2] [--max-steps N]
        [--shots DIR]           a PNG of the screen each time it waits for a key

With --then, the machine is switched off and on again after the first run, with the
disk as the first run left it (a save, say), and plays CHOICES2.

The music (fe/c64/tune.s) runs as it does on a C64: the I/O at $D000-$DFFF and the RAM
under it are kept apart, as the processor port ($01) says, so the tunes under the I/O
aren't the colour RAM; and the VIC-II's raster interrupt comes when the raster reaches
the line in $D012 (63 cycles a line, 312 lines a frame), through $0314, as the KERNAL
calls it, back by $EA31 or $EA81. Each tune the program starts or changes to is a line,
"[music NAME]" ("[music off]" to fade out), named from the disk's music file; and a run
that cues music must have opened the SID's gates (notes played).
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


SCREEN = 0xF800             # the text screen, in VIC bank 3 (fe/c64/split.s)
CYCLES_A_LINE = 63          # PAL
LINES = 312
COLS = 40
LAST_ROW = 24
STACK_TOP = None            # the C stack starts where the overlays do: from the map
STACK_LIMIT = 384


def screen_ascii(code):
    code &= 0x7F                                            # reverse or not
    if 1 <= code <= 26:
        return chr(code + 0x60)
    if 0x41 <= code <= 0x5A:
        return chr(code)
    if 0x20 <= code < 0x40:
        return chr(code)
    return {0x00: "@", 0x1B: "[", 0x1C: "\\", 0x1D: "]", 0x1E: "^", 0x1F: "_", 0x40: "`",
            0x5B: "{", 0x5C: "|", 0x5D: "}", 0x5E: "~"}.get(code, "?")


def tune_names(music):
    """The tunes' names in the disk's music file (tools/music/musicc.py --c64): after
    its load address and length, the tune file (docs/music.md)."""
    if not music or len(music) < 12:
        return []
    d = music[4:]
    t, n, w, p = d[3], d[4], d[5], d[6]
    at = 8 + 8 * t + 10 * n + 2 * w + 2 * p
    names = []
    for _ in range(t):
        names.append(d[at + 1:at + 1 + d[at]].decode("ascii", "replace"))
        at += 1 + d[at]
    return names


def segment_start(dbg, name):
    for line in open(dbg):
        if line.startswith("seg") and f'name="{name}"' in line:
            for field in line.split(","):
                if field.startswith("start="):
                    return int(field[6:], 16)
    raise RuntimeError(f"no segment {name} in {dbg}")


def symbol_cache(c64, name):
    if name not in c64.cache:
        c64.cache[name] = symbol(c64.dbg, name)
    return c64.cache[name]


def symbol(dbg, name):
    """A symbol's address from ld65's debug file."""
    for line in open(dbg):
        if line.startswith("sym") and f'name="{name}"' in line:
            for field in line.split(","):
                if field.startswith("val="):
                    return int(field[4:], 16)
    raise RuntimeError(f"{name} isn't in {dbg}")


class C64:
    def __init__(self, image, choices, dbg):
        self.files = {name: data for name, (kind, data) in d64.read_files(image).items()}
        self.choices = list(choices)
        self.lines = []
        self.shot_dir = None
        self.shots = 0
        self.dbg = dbg
        self.cache = {}
        self.newline_at = symbol(dbg, "_newline")
        self.stack_top = segment_start(dbg, "CARBUF")      # the stack ends where the car starts
        self.scene_wait = symbol(dbg, "_scene_wait")
        self.scene_log = symbol(dbg, "_hal_scene_log")
        self.scene_start = symbol(dbg, "_scene_start")
        self.scene_stop = symbol(dbg, "_scene_stop")
        self.overlay = None                                 # the overlay loaded
        self.in_scene = False
        self.after_scene = False
        self.last_picture = None
        self.stack_low = self.stack_top
        self.keys = []
        self.mem = ObservableMemory()
        self.mem.subscribe_to_read([KEY_COUNT], self.key_count)
        self.io = bytearray(0x1000)                         # $D000-$DFFF when it's I/O
        self.mem.subscribe_to_read(range(0xD000, 0xE000), self.io_read)
        self.mem.subscribe_to_write(range(0xD000, 0xE000), self.io_write)
        self.mpu = MPU(memory=self.mem)
        self.line = 0                                       # the raster's
        self.music_command = symbol(dbg, "music_command")
        self.tunes = tune_names(self.files.get("music"))
        self.cued = False
        self.notes = 0                                      # gates the SID saw open
        self.music_frames = 0
        self.lfs = (0, 0, 0)
        self.name = b""
        self.open = {}              # logical file: {"name", "data", "pos", "write"}
        self.chan_in = None
        self.chan_out = None
        self.status = 0
        self.overlays = 0
        self.ended = None

    # ------------------------------------------------------------ the I/O

    def io_seen(self):
        port = self.mem._subject[1]
        return port & 3 and port & 4

    def io_read(self, address):
        if not self.io_seen():
            return None
        if address in (0xD011, 0xD012):                     # where the raster is now
            line = (self.mpu.processorCycles // CYCLES_A_LINE) % LINES
            if address == 0xD012:
                return line & 0xFF
            return (self.io[0x11] & 0x7F) | (line >> 8) << 7
        return self.io[address - 0xD000]

    def io_write(self, address, value):
        if not self.io_seen():
            return None                                     # the RAM under it
        i = address - 0xD000
        if address == 0xD019:
            self.io[i] &= ~value & 0xFF                     # acknowledged
        else:
            if address in (0xD404, 0xD40B, 0xD412) and value & 1 and not self.io[i] & 1:
                self.notes += 1
            self.io[i] = value
        return self.mem._subject[address]                   # the RAM keeps its own

    def raster(self):
        """The raster moves on with the cycles; at $D012's line, its interrupt."""
        m = self.mpu
        line = (m.processorCycles // CYCLES_A_LINE) % LINES
        if line == self.line:
            return
        target = self.io[0x12] | (self.io[0x11] & 0x80) << 1
        while self.line != line:
            self.line = (self.line + 1) % LINES
            if self.line == target:
                self.io[0x19] |= 0x81
        if self.io[0x19] & 1 and self.io[0x1A] & 1 and not m.p & m.INTERRUPT:
            pc = m.pc
            for b in (pc >> 8, pc & 0xFF, (m.p & ~m.BREAK) | m.UNUSED, m.a, m.x, m.y):
                self.mem[0x100 + m.sp] = b
                m.sp = (m.sp - 1) & 0xFF
            m.p |= m.INTERRUPT
            m.pc = self.mem[0x314] | self.mem[0x315] << 8

    def irq_return(self):
        """$EA31 and $EA81: the KERNAL's end of an interrupt (its clock and keys are
        answered elsewhere): Y, X, A back, and RTI."""
        m = self.mpu
        pull = []
        for _ in range(6):
            m.sp = (m.sp + 1) & 0xFF
            pull.append(self.mem[0x100 + m.sp])
        m.y, m.x, m.a, m.p = pull[0], pull[1], pull[2], pull[3] | m.UNUSED
        m.pc = pull[4] | pull[5] << 8

    def music_cue(self):
        m = self.mpu
        if m.a in (1, 2):                                   # start, change
            self.cued = True
            if m.x == 255:
                self.lines.append("[music off]")
            else:
                name = self.tunes[m.x] if m.x < len(self.tunes) else f"#{m.x}"
                self.lines.append(f"[music {name}]")

    # ------------------------------------------------------------ keyboard

    def bottom_row(self):
        at = SCREEN + LAST_ROW * COLS
        return "".join(screen_ascii(self.mem[at + i]) for i in range(COLS)).rstrip()

    def scene_shot(self):
        """The battle screen, as the VIC-II draws it (tools/vic.py): bank 3's characters
        and screen, the colour RAM, and the sprites as scene.c planned them."""
        import vic
        m = self.mem
        r = lambda a: m[a] & 15                             # noqa: E731
        scr = vic.Screen(bytes(m[0xE000 + i] for i in range(2048)), r(0xD021), r(0xD022),
                         r(0xD023), r(0xD025), r(0xD026))
        for i in range(1000):
            scr.put(i % 40, i // 40, m[0xE800 + i], m[0xD800 + i] & 15)
        # The sprites as the raster interrupt puts them up (fe/c64/sprites.s): the plan's
        # first eight, then each event's, on its VIC sprite; a lower one is on top.
        plan = [m[symbol_cache(self, "_scene_next") + i] for i in range(180)]
        shown = []
        for s in range(8):
            if plan[34] >> s & 1:
                shown.append((s, plan[s], plan[8 + s], plan[16 + s], plan[24 + s],
                              plan[32] >> s & 1, plan[33] >> s & 1))
        for e in range(plan[35]):
            s = plan[52 + e]
            shown.append((s, plan[84 + e], plan[100 + e], plan[116 + e], plan[132 + e],
                          plan[148 + e] >> s & 1, plan[164 + e] >> s & 1))
        for s, x, y, ptr, colour, msb, multi in sorted(shown, key=lambda t: -t[0]):
            at = 0xC000 + 64 * ptr
            scr.sprite(x + 256 * msb - 24, y - 50, bytes(m[at + i] for i in range(63)),
                       colour & 15, multi)
        return scr.image(r(0xD020)).resize((768, 528))

    def shot(self):
        """What the screen shows now: the status bar, the picture (when the raster split
        is on) and the text window, as a PNG, for a person to look at, in the game's own
        font (the disk's file font: here the VIC's registers share its address)."""
        from PIL import Image
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
        import c64pic
        if self.in_scene:
            self.shots += 1
            self.scene_shot().save(os.path.join(self.shot_dir, f"screen{self.shots:03d}.png"))
            return
        img = Image.new("RGB", (320, 200))
        font = self.files.get("font", b"\0\0" + bytes(2048))[2:]
        split = self.mem[symbol_cache(self, "_split_picture")]
        if split:
            at = c64pic.LOAD_AT
            pic = bytes([at & 0xFF, at >> 8]) + bytes(self.mem[at + i] for i in range(c64pic.SIZE))
            img.paste(c64pic.render(pic), (0, 8))
        for row in range(25):
            if split and 1 <= row <= 12:
                continue
            for x in range(40):
                code = self.mem[SCREEN + row * COLS + x]
                ink = c64pic.PALETTE[self.mem[0xD800 + row * COLS + x] & 15]
                for y in range(8):
                    bits = font[code * 8 + y]
                    for dx in range(8):
                        img.putpixel((x * 8 + dx, row * 8 + y),
                                     ink if (bits >> (7 - dx)) & 1 else (0, 0, 0))
        img = img.resize((640, 400), Image.NEAREST)
        self.shots += 1
        img.save(os.path.join(self.shot_dir, f"screen{self.shots:03d}.png"))

    def next_answer(self):
        """The keys for whatever the program is waiting for now."""
        if self.shot_dir:
            self.shot()
        if self.in_scene:                                   # a key at a time
            if not self.choices:
                self.ended = "[end of input]"
                return []
            answer = self.choices.pop(0)
            return [self.petscii(answer[0]) if answer else 0x0D]
        line = self.bottom_row()
        if line.endswith("-- more --"):
            return [0x20]
        if not self.choices:
            self.ended = "[end of input]"
            return []
        answer = self.choices.pop(0)
        if line == ">":
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

    def line_pointers(self):
        at = SCREEN + self.mem[0xD6] * COLS
        self.mem[0xD1], self.mem[0xD2] = at & 0xFF, at >> 8
        self.mem[0xF3], self.mem[0xF4] = at & 0xFF, (at >> 8 & 0x03) | 0xD8

    def kernal(self, pc):
        m = self.mpu
        if pc == 0xFFD2:                                    # CHROUT
            if self.chan_out is not None:
                self.open[self.chan_out]["data"].append(m.a)
            self.carry(False)
        elif pc in (0xFFF0, 0xE50A):                        # PLOT: the cursor
            if self.mpu.p & self.mpu.CARRY:
                m.x, m.y = self.mem[0xD6], self.mem[0xD3]
            else:
                self.mem[0xD6], self.mem[0xD3] = m.x, m.y
                self.line_pointers()
        elif pc == 0xE56C:                                  # the cursor's line pointers
            self.line_pointers()
        elif pc == 0xEA24:                                  # the colour pointer, likewise
            self.mem[0xF3] = self.mem[0xD1]
            self.mem[0xF4] = (self.mem[0xD2] & 0x03) | 0xD8
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
                if name.startswith("ovl"):
                    self.overlay = name
                if name.startswith("pic"):
                    if not (self.after_scene and name == self.last_picture):
                        self.lines.append(f"[picture {name}]")
                    self.after_scene = False
                    self.last_picture = name
                self.carry(False)
        else:
            raise RuntimeError(f"the program called ${pc:04X} in the ROM, which isn't emulated")
        self.rts()

    def scene_call(self, pc):
        m = self.mpu
        if pc == self.scene_log:                            # hal_scene_log(ascii): A/X
            at = m.a | (m.x << 8)
            text = bytearray()
            while self.mem[at] and len(text) < 200:
                text.append(self.mem[at])
                at += 1
            self.lines.append(text.decode("ascii", "replace"))
            self.rts()
            return
        if pc == self.scene_start:
            self.in_scene = True
        elif pc == self.scene_stop:
            self.in_scene = False
            self.after_scene = True
        if pc == self.scene_wait:                           # no frames here: no waiting
            self.mem[symbol_cache(self, "_scene_pending")] = 0
            self.rts()
            return
        self.mpu.step()                                     # the rest runs as it is

    # ----------------------------------------------------------------- run

    def boot(self):
        prg = self.files.get("apb")
        if not prg:
            raise RuntimeError("no program called apb on the disk")
        at = prg[0] | (prg[1] << 8)
        for i, b in enumerate(prg[2:]):
            self.mem[at + i] = b
        self.mem[0x01] = 0x37
        self.mem[0xDC00] = 0xFF                             # no joystick in port 2
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
            if pc == self.newline_at:
                self.lines.append(self.bottom_row())
            if pc == self.music_command:
                self.music_cue()
            if self.overlay == "ovl3" and pc in (self.scene_wait, self.scene_log,
                                                 self.scene_start, self.scene_stop):
                self.scene_call(pc)
            elif pc in (0xEA31, 0xEA81):
                self.music_frames += pc == 0xEA31
                self.irq_return()
            elif pc >= 0xE000:
                self.kernal(pc)
            else:
                m.step()
                self.raster()
                sp = self.mem[2] | (self.mem[3] << 8)
                if self.stack_top - 0x400 < sp < self.stack_low:
                    self.stack_low = sp
            steps += 1
        if not self.ended:
            self.ended = f"[still running after {steps} steps]"
        return steps


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    max_steps = 400_000_000
    if "--max-steps" in argv:
        max_steps = int(argv[argv.index("--max-steps") + 1])
    with open(argv[1], "rb") as f:
        image = f.read()
    dbg = argv[2]
    with open(argv[3]) as f:
        choices = [line.rstrip("\n") for line in f]
    runs = [choices]
    if "--then" in argv:
        with open(argv[argv.index("--then") + 1]) as f:
            runs.append([line.rstrip("\n") for line in f])
    files = None
    failed = False
    for n, script in enumerate(runs):
        c64 = C64(image, script, dbg)
        if "--shots" in argv:
            c64.shot_dir = argv[argv.index("--shots") + 1]
            os.makedirs(c64.shot_dir, exist_ok=True)
            c64.shots = 100 * n
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
        for line in c64.lines:
            print(line)
        print(tail)
        used = c64.stack_top - c64.stack_low
        print(f"[{steps} 6502 steps, {c64.overlays} files loaded with LOAD, "
              f"{used} bytes of C stack, {c64.music_frames} frames, {c64.notes} notes]",
              file=sys.stderr)
        if c64.cued and not c64.notes:
            print("[music was cued, but the SID never played a note]")
            failed = True
        if used > STACK_LIMIT:
            print(f"[the C stack went {used} bytes deep, over {STACK_LIMIT}]")
            failed = True
        files = c64.files
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
