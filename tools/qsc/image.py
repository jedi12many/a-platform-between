"""Read, verify and disassemble Departure images (docs/vm-spec.md).

The verifier here applies the same checks the VM's load-time verifier will, so the
compiler's output is checked against the spec independently of the code that wrote it.
"""

import struct

from opcodes import (BY_CODE, MAX_CAR, MAX_OPTIONS, NO_MENU, NO_TITLE, OFFICIAL_ONLY,
                     SKILL_RATING_BASE, TXT_CLASS, TXT_DEBT, TXT_END, TXT_LEVEL, TXT_NAME,
                     TXT_NEWLINE, TXT_RACE, TXT_VAR, WIDTH)
from textpack import expand


class BadImage(ValueError):
    pass


class Reader:
    def __init__(self, data, where):
        self.data = data
        self.pos = 0
        self.where = where

    def take(self, fmt):
        size = struct.calcsize(fmt)
        if self.pos + size > len(self.data):
            raise BadImage(f"{self.where}: ends early")
        values = struct.unpack_from(fmt, self.data, self.pos)
        self.pos += size
        return values if len(values) > 1 else values[0]

    def bytes(self, n):
        if self.pos + n > len(self.data):
            raise BadImage(f"{self.where}: ends early")
        out = self.data[self.pos:self.pos + n]
        self.pos += n
        return out


def ascii_name(raw, what):
    if any(not 0x20 <= b <= 0x7E for b in raw):
        raise BadImage(f"{what} isn't plain ASCII")
    return raw.decode("ascii")


def split_apd(data):
    r = Reader(data, "container")
    if r.bytes(4) != b"APD1":
        raise BadImage("not a Departure image (no APD1)")
    depot_len, ncars, _ = r.take("<HBB")
    if not 1 <= ncars <= 64:
        raise BadImage(f"car count {ncars}")
    lens = [r.take("<H") for _ in range(ncars)]
    depot = r.bytes(depot_len)
    cars = [r.bytes(n) for n in lens]
    if r.pos != len(data):
        raise BadImage("container has trailing bytes")
    return depot, cars


def read_depot(depot):
    r = Reader(depot, "depot")
    if r.bytes(2) != b"DP":
        raise BadImage("depot magic")
    d = {}
    (d["version"], d["kind"], d["id"], d["season"], d["tl"], d["ml"], d["level_min"],
     d["level_max"], d["flags"], d["vars"], d["scenes"], d["start"], d["hash"]) = \
        r.take("<BBHBBBBBHBHHH")
    d["hash_at"] = 2 + struct.calcsize("<BBHBBBBBHBHH")
    d["title"] = ascii_name(r.bytes(r.take("<B")), "the title")
    d["var_init"] = list(r.bytes(d["vars"]))
    d["directory"] = [r.take("<BH") for _ in range(d["scenes"])]
    d["pairs"] = [tuple(r.bytes(2)) for _ in range(r.take("<B"))]
    d["pictures"] = [ascii_name(r.bytes(r.take("<B")), "a picture name")
                     for _ in range(r.take("<B"))]
    if r.pos != len(depot):
        raise BadImage("depot has trailing bytes")
    return d


def read_car(data, index, pairs):
    r = Reader(data, f"car {index}")
    if r.bytes(2) != b"CR":
        raise BadImage(f"car {index} magic")
    c = {}
    c["index"], c["title"], code_len, nstrings = r.take("<BHHH")
    c["code"] = r.bytes(code_len)
    offsets = [r.take("<H") for _ in range(nstrings)]
    blob = data[r.pos:]
    c["strings"] = []
    for i, o in enumerate(offsets):
        end = blob.find(b"\x00", o)
        if o >= len(blob) or end < 0:
            raise BadImage(f"car {index} string {i} runs off the end")
        try:
            c["strings"].append(expand(blob[o:end], pairs))
        except ValueError as e:
            raise BadImage(f"car {index} string {i}: {e}") from None
    return c


def show_text(s):
    out = []
    i = 0
    while i < len(s):
        b = s[i]
        if b == TXT_NAME:
            out.append("{name}")
        elif b == TXT_RACE:
            out.append("{race}")
        elif b == TXT_CLASS:
            out.append("{class}")
        elif b == TXT_DEBT:
            out.append("{debt}")
        elif b == TXT_LEVEL:
            out.append("{level}")
        elif b == TXT_NEWLINE:
            out.append("\\n")
        elif b == TXT_VAR:
            i += 1
            out.append(f"{{var {s[i] - 1}}}")
        else:
            out.append(chr(b))
        i += 1
    return "".join(out)


def decode(code, pos):
    """One instruction at pos: (name, [(kind, value)], next position)."""
    op = code[pos]
    if op not in BY_CODE:
        raise BadImage(f"unknown opcode 0x{op:02x}")
    name, kinds = BY_CODE[op]
    args = []
    p = pos + 1
    for k in kinds:
        w = WIDTH[k]
        if p + w > len(code):
            raise BadImage(f"{name} runs off the end of the code")
        v = code[p] if w == 1 else struct.unpack_from("<h" if k == "s16" else "<H", code, p)[0]
        args.append((k, v))
        p += w
    return name, args, p


def verify(data, registry=None):
    """Check an .apd image the way the VM's verifier does. Returns the parsed image."""
    from codegen import crc16
    depot, cars = split_apd(data)
    d = read_depot(depot)
    if d["version"] != 0:
        raise BadImage(f"image version {d['version']}")
    for i, (a, b) in enumerate(d["pairs"]):
        if a >= 0x80 + i or b >= 0x80 + i:
            raise BadImage(f"pair {i} refers forward")
    zeroed = bytearray(depot)
    struct.pack_into("<H", zeroed, d["hash_at"], 0)
    if crc16(bytes(zeroed) + b"".join(cars)) != d["hash"]:
        raise BadImage("image hash doesn't match")
    if d["start"] >= d["scenes"]:
        raise BadImage("start scene out of range")
    parsed = []
    for i, raw in enumerate(cars):
        if len(raw) > MAX_CAR:
            raise BadImage(f"car {i} is {len(raw)} bytes")
        c = read_car(raw, i, d["pairs"])
        if c["index"] != i:
            raise BadImage(f"car {i} says it is car {c['index']}")
        if c["title"] != NO_TITLE and c["title"] >= len(c["strings"]):
            raise BadImage(f"car {i} title string out of range")
        parsed.append(c)
    for n, (car, off) in enumerate(d["directory"]):
        if car >= len(parsed) or off + 2 > len(parsed[car]["code"]):
            raise BadImage(f"scene {n} directory entry out of range")
    for c in parsed:
        for n, s in enumerate(c["strings"]):
            verify_string(s, d, f"car {c['index']} string {n}")
        verify_code(c, d, registry)
    return d, parsed


def verify_string(s, d, where):
    """Only printable ASCII, the insert codes, and line breaks; variable inserts in range."""
    i = 0
    while i < len(s):
        b = s[i]
        if b == TXT_VAR:
            i += 1
            if i >= len(s) or not 1 <= s[i] <= d["vars"]:
                raise BadImage(f"{where}: variable insert out of range")
        elif not (0x20 <= b <= 0x7E or b in (TXT_NAME, TXT_RACE, TXT_CLASS, TXT_DEBT,
                                               TXT_LEVEL, TXT_NEWLINE)):
            raise BadImage(f"{where}: byte 0x{b:02x} isn't text")
        i += 1


def scene_starts(d, car_index):
    return {off for car, off in d["directory"] if car == car_index}


def verify_code(c, d, registry):
    code = c["code"]
    starts = scene_starts(d, c["index"])
    boundaries = set()
    targets = []
    menus = []
    pos = 0
    while pos < len(code):
        if pos in starts:
            menu = struct.unpack_from("<H", code, pos)[0]
            if menu != NO_MENU:
                menus.append((pos, pos + menu))
            pos += 2
            continue
        boundaries.add(pos)
        name, args, pos = decode(code, pos)
        if d["kind"] == 1 and name in OFFICIAL_ONLY:
            raise BadImage(f"{name} in a Branch Line")
        for kind, v in args:
            limit = {"str": len(c["strings"]), "scene": d["scenes"], "flag": d["flags"],
                     "var": d["vars"], "pic": len(d["pictures"])}.get(kind)
            if limit is not None and v >= limit:
                raise BadImage(f"{name}: {kind} {v} out of range (< {limit})")
            if kind == "addr":
                targets.append((name, v))
            if kind == "rating" and not (v < 6 or SKILL_RATING_BASE <= v < SKILL_RATING_BASE + 12):
                raise BadImage(f"{name}: rating {v}")
            if registry is not None:
                if kind == "item" and v not in {e["id"] for e in registry["items"].values()}:
                    raise BadImage(f"{name}: item {v} isn't in the registry")
                if kind == "echo" and v not in {e["id"] for e in registry["echoes"].values()}:
                    raise BadImage(f"{name}: Echo {v} isn't in the registry")
    for name, t in targets:
        if t not in boundaries:
            raise BadImage(f"{name} jumps to {t}, which isn't an instruction")
    for scene_at, m in menus:
        if m not in boundaries or code[m] != 0x18:
            raise BadImage(f"scene at {scene_at}: menu offset doesn't point at MENU_CLEAR")


def disassemble(data, registry=None):
    """A readable listing of a whole image."""
    d, cars = verify(data, registry)
    names = {}
    if registry:
        names["item"] = {e["id"]: n for n, e in registry["items"].items()}
        names["echo"] = {e["id"]: n for n, e in registry["echoes"].items()}
    lines = [f"; '{d['title']}' id {d['id']} {'official' if d['kind'] == 0 else 'branch'}"
             f" TL{d['tl']} ML{d['ml']} levels {d['level_min']}-{d['level_max']}",
             f"; {d['scenes']} scenes, {d['flags']} flags, {d['vars']} vars, "
             f"{len(d['pairs'])} text pairs, start scene {d['start']}, hash {d['hash']:04x}"]
    scene_at = {(car, off): n for n, (car, off) in enumerate(d["directory"])}
    for c in cars:
        code = c["code"]
        title = show_text(c["strings"][c["title"]]) if c["title"] != NO_TITLE else ""
        lines.append(f"\n; car {c['index']} {title!r}: {len(code)} bytes of code, "
                     f"{len(c['strings'])} strings")
        pos = 0
        while pos < len(code):
            if (c["index"], pos) in scene_at:
                menu = struct.unpack_from("<H", code, pos)[0]
                note = "no menu" if menu == NO_MENU else f"menu at {pos + menu}"
                lines.append(f"\nscene {scene_at[(c['index'], pos)]}:  ; {note}")
                pos += 2
                continue
            name, args, nxt = decode(code, pos)
            shown = []
            for kind, v in args:
                if kind == "str":
                    shown.append(f'"{show_text(c["strings"][v])}"')
                elif kind in names and v in names[kind]:
                    shown.append(names[kind][v])
                elif kind == "rating" and v >= SKILL_RATING_BASE:
                    shown.append(f"skill {v - SKILL_RATING_BASE}")
                else:
                    shown.append(str(v))
            lines.append(f"  {pos:5d}  {name:<10} {', '.join(shown)}")
            pos = nxt
    return "\n".join(lines) + "\n"


__all__ = ["BadImage", "verify", "disassemble", "split_apd", "read_depot", "read_car",
           "show_text", "MAX_OPTIONS", "TXT_END"]
