"""The music compiler (docs/music.md): a Departure's tunes, written as text, into the file
every player plays.

    python3 tools/music/musicc.py check NAME.music
    python3 tools/music/musicc.py build NAME.music -o MUSIC [--prg ADDR]

--prg writes it as a C64 program file that loads at ADDR (hex), for a disk.
Messages are for musicians: they say what's wrong and where, in plain words.
"""

import re
import sys

MAX_FILE = 1536
MAX_TUNES, MAX_INSTRUMENTS, MAX_STEPS, MAX_PATTERNS = 32, 32, 128, 128
MAX_ROWS = 64

WAVES = {"tri": 0x10, "saw": 0x20, "pulse": 0x40, "noise": 0x80, "ring": 0x04, "sync": 0x02}
NOTE_NAMES = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
NAME = re.compile(r"^[a-z0-9_]+$")


class MusicError(Exception):
    def __init__(self, line, msg):
        super().__init__(f"line {line}: {msg}" if line else msg)


def note_number(text, line):
    """'c4', 'f#3', 'bb2' to 0-95 (C-0 is 0)."""
    m = re.fullmatch(r"([a-g])([#b]?)([0-7])", text)
    if not m:
        raise MusicError(line, f"'{text}' isn't a note: write it like c4, f#3 or bb2 (octaves 0-7)")
    n = NOTE_NAMES[m.group(1)] + (1 if m.group(2) == "#" else -1 if m.group(2) == "b" else 0)
    n += 12 * int(m.group(3))
    if not 0 <= n <= 95:
        raise MusicError(line, f"'{text}' is outside the notes the player has (c0 to b7)")
    return n


def hexbyte(text, line, what, low=0, high=255):
    try:
        v = int(text, 16)
    except ValueError:
        raise MusicError(line, f"{what} should be a hex number, not '{text}'")
    if not low <= v <= high:
        raise MusicError(line, f"{what} should be {low:X} to {high:X} (hex), not '{text}'")
    return v


class Instrument:
    def __init__(self, name, line):
        self.name, self.line = name, line
        self.steps = []             # (control, pitch byte)
        self.loop = None
        self.ad, self.sr = 0x09, 0x00
        self.pulse = (0x80, 0, 0x80, 0x80)
        self.vibrato = (0, 0, 1)


def parse(text):
    instruments, patterns, tunes = {}, {}, {}
    order_i, order_p, order_t = [], [], []
    current = None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#")[0].rstrip()
        if not line.strip():
            continue
        words = line.split()
        head = words[0]
        if not raw[0].isspace():
            current = None
            if head == "instrument":
                if len(words) != 2 or not NAME.match(words[1]):
                    raise MusicError(n, "write 'instrument NAME', the name in small letters, digits and _")
                if words[1] in instruments:
                    raise MusicError(n, f"there's already an instrument called {words[1]}")
                current = ("i", Instrument(words[1], n))
                instruments[words[1]] = current[1]
                order_i.append(words[1])
            elif head == "pattern":
                if len(words) != 3 or not NAME.match(words[1]):
                    raise MusicError(n, "write 'pattern NAME INSTRUMENT'")
                if words[1] in patterns:
                    raise MusicError(n, f"there's already a pattern called {words[1]}")
                current = ("p", {"name": words[1], "instrument": words[2], "line": n, "tokens": []})
                patterns[words[1]] = current[1]
                order_p.append(words[1])
            elif head == "tune":
                if len(words) != 4 or words[2] != "tempo" or not NAME.match(words[1]):
                    raise MusicError(n, "write 'tune NAME tempo N' (N frames a row, 2-31)")
                if words[1] in tunes:
                    raise MusicError(n, f"there's already a tune called {words[1]}")
                try:
                    tempo = int(words[3])
                except ValueError:
                    tempo = 0
                if not 2 <= tempo <= 31:
                    raise MusicError(n, "a tune's tempo is 2 to 31 frames a row")
                current = ("t", {"name": words[1], "tempo": tempo, "line": n, "voices": {}})
                tunes[words[1]] = current[1]
                order_t.append(words[1])
            else:
                raise MusicError(n, f"'{head}' isn't something a music file has: "
                                    "it has instruments, patterns and tunes")
            continue
        if current is None:
            raise MusicError(n, "this line is indented, but there's no instrument, pattern or tune above it")
        kind, obj = current
        if kind == "i":
            instrument_line(obj, words, n)
        elif kind == "p":
            obj["tokens"] += [(w, n) for w in words]
        else:
            m = re.fullmatch(r"([123]):", head)
            if not m:
                raise MusicError(n, "a tune's lines start with a voice, 1: 2: or 3:")
            v = int(m.group(1))
            if v in obj["voices"]:
                raise MusicError(n, f"voice {v} is written twice in this tune")
            obj["voices"][v] = (words[1:], n)
    if not tunes:
        raise MusicError(0, "there are no tunes in this file")
    return instruments, order_i, patterns, order_p, tunes, order_t


def instrument_line(ins, words, n):
    what = words[0]
    if what == "wave":
        if len(words) not in (2, 3):
            raise MusicError(n, "write 'wave WAVEFORM [PITCH]', like 'wave pulse +7' or 'wave noise =c5'")
        control = 0
        for w in words[1].split("+"):
            if w not in WAVES:
                raise MusicError(n, f"'{w}' isn't a waveform: tri, saw, pulse, noise (and ring, sync)")
            control |= WAVES[w]
        pitch = 0
        if len(words) == 3:
            p = words[2]
            if p.startswith("="):
                pitch = 0x80 | note_number(p[1:], n)
            else:
                try:
                    rel = int(p)
                except ValueError:
                    raise MusicError(n, f"a pitch is +n, -n or =NOTE, not '{p}'")
                if not -64 <= rel <= 63:
                    raise MusicError(n, "a step's pitch is -64 to +63 semitones from the note")
                pitch = rel & 0x7F
        ins.steps.append((control, pitch))
    elif what == "loop":
        if len(words) != 2 or not words[1].isdigit():
            raise MusicError(n, "write 'loop N', N the step to go back to (0 is the first)")
        ins.loop = int(words[1])
    elif what == "adsr":
        if len(words) != 5 or any(len(w) != 1 for w in words[1:]):
            raise MusicError(n, "write 'adsr A D S R', one hex digit each, like 'adsr 0 9 a 6'")
        a, d, s, r = (hexbyte(w, n, "an envelope digit", 0, 15) for w in words[1:])
        ins.ad, ins.sr = a << 4 | d, s << 4 | r
    elif what == "pulse":
        if len(words) != 5:
            raise MusicError(n, "write 'pulse START SPEED LOW HIGH': hex widths / 16, the speed in signed decimal")
        start = hexbyte(words[1], n, "the pulse start")
        try:
            speed = int(words[2])
        except ValueError:
            raise MusicError(n, "the pulse speed is a signed whole number, like 3 or -2")
        if not -128 <= speed <= 127:
            raise MusicError(n, "the pulse speed is -128 to 127")
        low, high = hexbyte(words[3], n, "the pulse low limit"), hexbyte(words[4], n, "the pulse high limit")
        if low > high:
            raise MusicError(n, "the pulse low limit is above the high one")
        ins.pulse = (start, speed & 0xFF, low, high)
    elif what == "vibrato":
        if len(words) != 4 or not all(w.isdigit() for w in words[1:]):
            raise MusicError(n, "write 'vibrato DELAY DEPTH SPEED' (whole numbers)")
        delay, depth, speed = (int(w) for w in words[1:])
        if delay > 255 or depth > 15 or not 1 <= speed <= 63:
            raise MusicError(n, "vibrato: a delay up to 255 frames, a depth 0-15, a speed 1-63")
        ins.vibrato = (delay, depth, speed)
    else:
        raise MusicError(n, f"'{what}' isn't part of an instrument: wave, loop, adsr, pulse, vibrato")


def pattern_bytes(p, instrument_index, line_of):
    """A pattern's events as bytes. Durations over 64 rows become tied notes."""
    out = []
    ins = p["instrument"]
    if ins not in instrument_index:
        raise MusicError(p["line"], f"pattern {p['name']} plays instrument '{ins}', which isn't in this file")
    out.append(0xC0 | instrument_index[ins])
    length = 1
    events = []                 # [kind, value, rows, slur]
    slur = False
    for tok, n in p["tokens"]:
        if tok.startswith("@"):
            if tok[1:] not in instrument_index:
                raise MusicError(n, f"there's no instrument called '{tok[1:]}'")
            events.append(["i", instrument_index[tok[1:]], 0, False])
            continue
        if tok.startswith(">"):
            slur = True
            tok = tok[1:]
        what, _, rows = tok.partition("/")
        if rows:
            if not rows.isdigit() or int(rows) < 1:
                raise MusicError(n, f"'/{rows}' isn't a length: rows are 1 or more, like /4")
            length = int(rows)
        if what == "r":
            events.append(["r", 0, length, False])
            slur = False
        elif what == "~":
            if not any(e[0] in "nt" for e in events):
                raise MusicError(n, "a tie (~) needs a note before it in the same pattern")
            events.append(["t", 0, length, slur])
        else:
            events.append(["n", note_number(what, n), length, slur])
        slur = False
    if slur:
        raise MusicError(p["line"], f"pattern {p['name']} ends with a slur (>) that has nothing to slur")
    # Long notes and ties: split into 64-row pieces, tied and slurred.
    flat = []
    for e in events:
        if e[0] == "i":
            flat.append(e)
            continue
        rows = e[2]
        first = True
        while rows > 0:
            take = min(rows, MAX_ROWS)
            rows -= take
            kind = e[0] if first or e[0] == "r" else "t"
            flat.append([kind, e[1], take, e[3] if rows == 0 else (e[0] != "r")])
            first = False
    # A note or tie followed by a tie must not shut its gate: slur it.
    for i, e in enumerate(flat):
        if e[0] in "nt":
            nxt = next((f for f in flat[i + 1:] if f[0] != "i"), None)
            if nxt is not None and nxt[0] == "t":
                e[3] = True
    current = 1
    for e in flat:
        if e[0] == "i":
            out.append(0xC0 | e[1])
            continue
        if e[2] != current:
            out.append(0x80 | (e[2] - 1))
            current = e[2]
        if e[3]:
            out.append(0xE0)
        out.append(e[1] if e[0] == "n" else 0x60 if e[0] == "r" else 0x61)
    out.append(0xFF)
    return out


def build(text):
    instruments, order_i, patterns, order_p, tunes, order_t = parse(text)
    if len(order_i) > MAX_INSTRUMENTS:
        raise MusicError(0, f"{len(order_i)} instruments: the most is {MAX_INSTRUMENTS}")
    if len(order_t) > MAX_TUNES:
        raise MusicError(0, f"{len(order_t)} tunes: the most is {MAX_TUNES}")
    instrument_index = {name: i for i, name in enumerate(order_i)}
    # Waveform steps, instrument by instrument.
    steps, first_step = [], {}
    for name in order_i:
        ins = instruments[name]
        if not ins.steps:
            raise MusicError(ins.line, f"instrument {name} has no 'wave' line")
        first_step[name] = len(steps)
        steps += ins.steps
        last = len(steps) - 1
        if ins.loop is not None:
            if not 0 <= ins.loop < len(ins.steps):
                raise MusicError(ins.line, f"instrument {name} loops to step {ins.loop}, "
                                           f"but it has steps 0 to {len(ins.steps) - 1}")
            steps.append((0xFF, first_step[name] + ins.loop))
        else:
            steps.append((0xFF, last + 1))      # a jump to itself: hold the last step
    if len(steps) > MAX_STEPS:
        raise MusicError(0, f"{len(steps)} waveform steps in all: the most is {MAX_STEPS}")
    # Patterns: the written ones, then rests made for 'rN'.
    pattern_list = [pattern_bytes(patterns[name], instrument_index, None) for name in order_p]
    pattern_index = {name: i for i, name in enumerate(order_p)}
    rests = {}

    def rest_pattern(rows):
        if rows not in rests:
            out = [0xC0]
            left = rows
            while left:
                take = min(left, MAX_ROWS)
                out += [0x80 | (take - 1), 0x60]
                left -= take
            out.append(0xFF)
            rests[rows] = len(pattern_list)
            pattern_list.append(out)
        return rests[rows]

    sequences = []
    for name in order_t:
        t = tunes[name]
        seqs = []
        for v in (1, 2, 3):
            words, n = t["voices"].get(v, ([], t["line"]))
            seq = []
            transpose = None
            for w in words:
                if w == "|":
                    if 0xFE in seq:
                        raise MusicError(n, "a voice has one loop point (|)")
                    seq.append(0xFE)
                    transpose = None
                    continue
                m = re.fullmatch(r"r(\d+)", w)
                if m:
                    rows = int(m.group(1))
                    if rows < 1:
                        raise MusicError(n, "a silence (rN) is 1 row or more")
                    ref, tr = rest_pattern(rows), 0
                else:
                    m = re.fullmatch(r"([a-z0-9_]+)([+-]\d+)?", w)
                    if not m or m.group(1) not in pattern_index:
                        raise MusicError(n, f"'{w}' isn't a pattern in this file (or a silence, like r8)")
                    ref, tr = pattern_index[m.group(1)], int(m.group(2) or 0)
                    if not -32 <= tr <= 31:
                        raise MusicError(n, "a transpose is -32 to +31 semitones")
                if tr != transpose:
                    seq.append(0xA0 + tr)
                    transpose = tr
                seq.append(ref)
            if words and not any(b < 0x80 for b in seq):
                raise MusicError(n, f"voice {v} of tune {name} plays no patterns")
            if seq and seq[-1] == 0xFE:
                raise MusicError(n, "the loop point (|) has nothing after it to loop")
            seq.append(0xFF)
            seqs.append(seq)
        sequences.append(seqs)
    if len(pattern_list) > MAX_PATTERNS:
        raise MusicError(0, f"{len(pattern_list)} patterns (with the silences): the most is {MAX_PATTERNS}")
    # Lay out the file.
    T, N, W, P = len(order_t), len(order_i), len(steps), len(pattern_list)
    names = b"".join(bytes([len(nm)]) + nm.encode("ascii") for nm in order_t)
    at = 8 + 8 * T + 10 * N + 2 * W + 2 * P + len(names)
    seq_at = []
    for seqs in sequences:
        offs = []
        for s in seqs:
            offs.append(at)
            at += len(s)
        seq_at.append(offs)
    pat_at = []
    for p in pattern_list:
        pat_at.append(at)
        at += len(p)
    if at > MAX_FILE:
        raise MusicError(0, f"the music comes to {at} bytes: the most is {MAX_FILE}. "
                            "Share patterns between tunes, or use fewer instruments")
    out = bytearray(b"MU\x01") + bytes([T, N, W, P, 0])
    for i, name in enumerate(order_t):
        out += bytes([tunes[name]["tempo"], 0])
        for o in seq_at[i]:
            out += o.to_bytes(2, "little")
    for name in order_i:
        ins = instruments[name]
        out += bytes([ins.ad, ins.sr, first_step[name], *ins.pulse, *ins.vibrato])
    for c, p in steps:
        out += bytes([c, p])
    for o in pat_at:
        out += o.to_bytes(2, "little")
    out += names
    for seqs in sequences:
        for s in seqs:
            out += bytes(s)
    for p in pattern_list:
        out += bytes(p)
    assert len(out) == at
    return bytes(out), order_t


def main(argv):
    if len(argv) >= 3 and argv[1] in ("check", "build"):
        try:
            data, names = build(open(argv[2]).read())
        except MusicError as e:
            print(f"{argv[2]}: {e}")
            return 1
        if argv[1] == "build":
            if "-o" not in argv:
                print(__doc__)
                return 2
            out = argv[argv.index("-o") + 1]
            if "--prg" in argv:
                at = int(argv[argv.index("--prg") + 1], 16)
                data = bytes([at & 0xFF, at >> 8]) + data
            with open(out, "wb") as f:
                f.write(data)
        print(f"{argv[2]}: {len(data)} bytes, tunes: {', '.join(names)}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
