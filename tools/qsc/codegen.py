"""Code generation: a checked Departure (qs_ast) to a Departure image (docs/vm-spec.md).

One car per chapter. Each scene is laid out as:

    u16 menu offset (relative to the scene, or NO_MENU)
    [chapter title, the first time this chapter is entered]
    entry code: text, commands, ifs, checks
    SET visited                      (before every way out of the entry code)
    menu block: MENU_CLEAR, OPTION..., MENU
    choice bodies, each ending in JMP back to the menu block (or leaving the scene)
"""

import struct

import qs_ast as A
from opcodes import (COMPARE, FOE_NAME_MAX, MAP_TILES, MAX_CAR, MAX_DEPOT, MAX_ENCOUNTERS,
                     NO_MENU,
                     NO_TITLE,
                     OFFICIAL_ONLY, OPS,
                     SKILL_RATING_BASE, STACK_DEPTH, TXT_CLASS, TXT_DEBT, TXT_LEVEL,
                     TXT_NAME, TXT_NEWLINE, TXT_RACE, TXT_VAR, WIDTH)
from parse import terminates
from registry import REACH
from textpack import compress

IMAGE_VERSION = 0
MAX_FLAGS = 512
MAX_STRINGS = 1024
MAX_SCENES = 1024
MAX_PICTURES = 255


class CompileError(Exception):
    def __init__(self, line, msg):
        super().__init__(msg)
        self.line = line


class Label:
    pass


class Asm:
    """Bytecode for one car, with labels resolved at the end."""

    def __init__(self):
        self.code = bytearray()
        self.labels = {}
        self.fixups = []        # (position, label, base): write label - base as u16

    def pos(self):
        return len(self.code)

    def mark(self, label):
        self.labels[label] = self.pos()

    def u8(self, v):
        self.code.append(v & 0xFF)

    def u16(self, v):
        self.code += struct.pack("<H", v & 0xFFFF)

    def ref(self, label, base=0):
        self.fixups.append((self.pos(), label, base))
        self.u16(0)

    def op(self, name, *args):
        code, kinds = OPS[name]
        assert len(args) == len(kinds), name
        self.u8(code)
        for kind, arg in zip(kinds, args):
            if kind == "addr":
                self.ref(arg)
            elif WIDTH[kind] == 1:
                self.u8(arg)
            else:
                self.u16(arg)

    def resolve(self):
        for at, label, base in self.fixups:
            struct.pack_into("<H", self.code, at, self.labels[label] - base)


class Car:
    def __init__(self, index, title):
        self.index = index
        self.title = title
        self.asm = Asm()
        self.strings = []       # encoded strings, before compression
        self.string_ids = {}

    def string(self, data):
        if data not in self.string_ids:
            self.string_ids[data] = len(self.strings)
            self.strings.append(data)
        return self.string_ids[data]


class Compiler:
    def __init__(self, dep, registry):
        self.dep = dep
        self.reg = registry
        self.scenes = list(dep.scenes())
        self.scene_ids = {s.name: i for i, s in enumerate(self.scenes)}
        self.scene_car = {}
        self.scene_offset = {}
        self.var_ids = {name: i for i, name in enumerate(dep.vars)}
        self.pictures = list(dep.pictures)
        self.map_ids = {name: i for i, name in enumerate(dep.maps)}
        # Flags: declared ones first, then the compiler's own.
        self.flags = {name: i for i, name in enumerate(dep.flags)}
        self.visited_flags = {}
        self.chapter_flags = {}
        self.once_flags = {}
        for name in sorted(self.visited_scenes()):
            self.visited_flags[name] = self.new_flag(0)
        self.cars = []

    def new_flag(self, line):
        n = len(self.flags) + len(self.visited_flags) + len(self.chapter_flags) + \
            len(self.once_flags)
        if n >= MAX_FLAGS:
            raise CompileError(line, f"this Departure needs more than {MAX_FLAGS} flags "
                                     "(yours, plus one per once-only choice, visited scene "
                                     "and chapter)")
        return n

    def visited_scenes(self):
        found = set()

        def walk_cond(c):
            if isinstance(c, A.Visited):
                found.add(c.scene)
            elif isinstance(c, A.Not):
                walk_cond(c.operand)
            elif isinstance(c, (A.And, A.Or)):
                walk_cond(c.left)
                walk_cond(c.right)

        def walk(stmts):
            for st in stmts:
                if isinstance(st, A.If):
                    for c, body in st.branches:
                        if c is not None:
                            walk_cond(c)
                        walk(body)
                elif isinstance(st, (A.Check, A.Fight)):
                    for body in st.outcomes.values():
                        walk(body)

        for s in self.scenes:
            walk(s.body)
            for ch in s.choices:
                if ch.cond is not None:
                    walk_cond(ch.cond)
                walk(ch.body)
        return found

    # ------------------------------------------------------------- strings

    def encode_text(self, parts):
        out = bytearray()
        for p in parts:
            if isinstance(p, str):
                for c in p:
                    out.append(TXT_NEWLINE if c == "\n" else ord(c))
            elif p.what == "var":
                out += bytes([TXT_VAR, self.var_ids[p.var] + 1])
            else:
                out.append({"name": TXT_NAME, "race": TXT_RACE, "class": TXT_CLASS,
                            "debt": TXT_DEBT, "level": TXT_LEVEL}[p.what])
        return bytes(out)

    # ---------------------------------------------------------- conditions

    def cond(self, asm, c):
        """Emit code that pushes 1 or 0; returns the stack depth it needs."""
        if isinstance(c, A.Flag):
            asm.op("FLAG", self.flags[c.name])
            return 1
        if isinstance(c, A.Visited):
            asm.op("FLAG", self.visited_flags[c.scene])
            return 1
        if isinstance(c, A.Has):
            asm.op("HAS", self.reg["items"][c.item]["id"])
            return 1
        if isinstance(c, A.Compare):
            kind = c.subject[0]
            if kind == "var":
                asm.op("VAR", self.var_ids[c.subject[1]])
            elif kind == "stat":
                asm.op("RATING", c.subject[1])
            elif kind == "skill":
                asm.op("RATING", SKILL_RATING_BASE + c.subject[1])
            else:
                asm.op("LEVEL")
            asm.op("PUSH8", c.value)
            asm.op(COMPARE[c.op])
            return 2
        if isinstance(c, A.EchoIs):
            e = self.reg["echoes"][c.echo]
            asm.op("ECHO", e["id"], e["default"])
            asm.op("PUSH8", e["states"].index(c.state) + 1)
            asm.op(COMPARE[c.op])
            return 2
        if isinstance(c, A.IsRace):
            asm.op("RACE")
            asm.op("PUSH8", self.reg["races"][c.race]["id"])
            asm.op("EQ")
            return 2
        if isinstance(c, A.IsClass):
            asm.op("CLASS")
            asm.op("PUSH8", self.reg["classes"][c.cls]["id"])
            asm.op("EQ")
            return 2
        if isinstance(c, A.Not):
            d = self.cond(asm, c.operand)
            asm.op("NOT")
            return d
        if isinstance(c, (A.And, A.Or)):
            left = self.cond(asm, c.left)
            right = self.cond(asm, c.right)
            asm.op("AND" if isinstance(c, A.And) else "OR")
            return max(left, right + 1)
        raise AssertionError(c)

    def cond_jz(self, asm, c, label, line):
        depth = self.cond(asm, c)
        if depth > STACK_DEPTH:
            raise CompileError(line, "this condition is too complicated for the engine: "
                                     "split it into simpler ifs")
        asm.op("JZ", label)

    # ---------------------------------------------------------- statements

    def block(self, car, stmts, ctx):
        for st in stmts:
            self.stmt(car, st, ctx)

    def leave(self, car, ctx):
        """Before leaving a scene's entry code, mark the scene visited."""
        if ctx.get("visited") is not None:
            car.asm.op("SET", ctx["visited"])

    def stmt(self, car, st, ctx):
        asm = car.asm
        if isinstance(st, A.Text):
            asm.op("TEXT", car.string(self.encode_text(st.parts)))
        elif isinstance(st, A.Goto):
            self.leave(car, ctx)
            asm.op("GOTO", self.scene_ids[st.scene])
        elif isinstance(st, A.Command):
            self.command(car, st, ctx)
        elif isinstance(st, A.If):
            end = Label()
            for c, body in st.branches:
                nxt = Label()
                if c is not None:
                    self.cond_jz(asm, c, nxt, st.line)
                self.block(car, body, ctx)
                if not terminates(body):
                    asm.op("JMP", end)
                asm.mark(nxt)
            asm.mark(end)
        elif isinstance(st, A.Check):
            end = Label()
            kind, n = st.rating
            rating = n if kind == "stat" else SKILL_RATING_BASE + n
            asm.op("CHECK", rating, st.tn)
            labels = {k: Label() for k in st.outcomes}
            crit = "crit" if "crit" in st.outcomes else "success"
            asm.op("SWITCH4", labels.get("fail", end), labels.get("cost", end),
                   labels.get("success", end), labels.get(crit, end))
            for k, body in st.outcomes.items():
                asm.mark(labels[k])
                self.block(car, body, ctx)
                if not terminates(body):
                    asm.op("JMP", end)
            asm.mark(end)
        elif isinstance(st, A.Fight):
            # FIGHT pushes 0 won, 1 lost, 2 fled. Losing with no lost: branch ends the
            # Departure, failed.
            end = Label()
            labels = {k: Label() for k in st.outcomes}
            lost = labels.get("lost") or Label()
            asm.op("FIGHT", self.map_ids[st.map], st.surprise)
            # The fourth slot is never taken; it points at a real instruction anyway.
            asm.op("SWITCH4", labels.get("won", end), lost, labels.get("fled", end),
                   labels.get("won", end))
            for k, body in st.outcomes.items():
                asm.mark(labels[k])
                self.block(car, body, ctx)
                if not terminates(body):
                    asm.op("JMP", end)
            if "lost" not in st.outcomes:
                asm.mark(lost)
                self.leave(car, ctx)
                asm.op("END", 1)
            asm.mark(end)
        else:
            raise AssertionError(st)

    def command(self, car, cmd, ctx):
        asm = car.asm
        a = cmd.args
        if cmd.name in OFFICIAL_ONLY_COMMANDS and self.dep.kind != "official":
            raise CompileError(cmd.line, f"'~ {cmd.name}' isn't allowed in a Branch Line")
        if cmd.name == "set":
            asm.op("SET", self.flags[a[0]])
        elif cmd.name == "clear":
            asm.op("CLR", self.flags[a[0]])
        elif cmd.name == "let":
            asm.op("PUSH8", a[1])
            asm.op("LET", self.var_ids[a[0]])
        elif cmd.name == "add":
            asm.op("ADD", self.var_ids[a[0]], a[1])
        elif cmd.name == "sub":
            asm.op("SUB", self.var_ids[a[0]], a[1])
        elif cmd.name == "echo":
            e = self.reg["echoes"][a[0]]
            asm.op("ECHO_SET", e["id"], e["states"].index(a[1]) + 1)
        elif cmd.name == "give":
            asm.op("GIVE", self.reg["items"][a[0]]["id"])
        elif cmd.name == "take":
            asm.op("TAKE", self.reg["items"][a[0]]["id"])
        elif cmd.name == "xp":
            asm.op("XP", a[0])
        elif cmd.name == "heal":
            asm.op("HEAL", a[0])
        elif cmd.name == "debt":
            asm.op("DEBT", {"set": 0, "add": 1, "sub": 2}[a[0]], a[1])
        elif cmd.name == "picture":
            asm.op("PICTURE", self.pictures.index(a[0]))
        elif cmd.name == "pause":
            asm.op("PAUSE")
        elif cmd.name == "end":
            self.leave(car, ctx)
            asm.op("END", 0 if a[0] == "complete" else 1)
        else:
            raise AssertionError(cmd.name)

    # -------------------------------------------------------------- scenes

    def scene(self, car, chapter_flag, s):
        asm = car.asm
        start = asm.pos()
        self.scene_car[s.name] = car.index
        self.scene_offset[s.name] = start
        menu = Label()
        if s.choices:
            asm.ref(menu, base=start)
        else:
            asm.u16(NO_MENU)
        if chapter_flag is not None:
            shown = Label()
            asm.op("FLAG", chapter_flag)
            asm.op("NOT")
            asm.op("JZ", shown)
            asm.op("SET", chapter_flag)
            asm.op("CHAPTER")
            asm.mark(shown)
        ctx = {"visited": self.visited_flags.get(s.name)}
        self.block(car, s.body, ctx)
        if not s.choices:
            return
        self.leave(car, ctx)
        asm.mark(menu)
        asm.op("MENU_CLEAR")
        bodies = []
        for ch in s.choices:
            skip = Label()
            body = Label()
            once = None
            if not ch.sticky:
                once = self.new_flag(ch.line)
                self.once_flags[(s.name, ch.line)] = once
                asm.op("FLAG", once)
                asm.op("NOT")
                asm.op("JZ", skip)
            if ch.cond is not None:
                self.cond_jz(asm, ch.cond, skip, ch.line)
            asm.op("OPTION", car.string(self.encode_text([ch.label])), body)
            asm.mark(skip)
            bodies.append((ch, body, once))
        asm.op("MENU")
        for ch, body, once in bodies:
            asm.mark(body)
            if once is not None:
                asm.op("SET", once)
            if ch.target is not None:
                asm.op("GOTO", self.scene_ids[ch.target])
                continue
            self.block(car, ch.body, {"visited": None})
            if not terminates(ch.body):
                asm.op("JMP", menu)

    # ---------------------------------------------------------------- image

    def compile(self):
        if len(self.scenes) > MAX_SCENES:
            raise CompileError(1, f"{len(self.scenes)} scenes; the most is {MAX_SCENES}")
        if len(self.pictures) > MAX_PICTURES:
            raise CompileError(1, f"{len(self.pictures)} pictures; the most is {MAX_PICTURES}")
        if len(self.dep.maps) > MAX_ENCOUNTERS:
            raise CompileError(list(self.dep.maps.values())[MAX_ENCOUNTERS].line,
                               f"{len(self.dep.maps)} battle maps; the most is {MAX_ENCOUNTERS}")
        for index, chapter in enumerate(self.dep.chapters):
            if index >= 64:
                raise CompileError(chapter.line, "a Departure can have at most 64 chapters")
            car = Car(index, chapter.title)
            flag = None
            if chapter.title:
                flag = self.new_flag(chapter.line)
                self.chapter_flags[index] = flag
                car.title_id = car.string(self.encode_text([chapter.title]))
            else:
                car.title_id = NO_TITLE
            for s in chapter.scenes:
                self.scene(car, flag, s)
            car.asm.resolve()
            if len(car.strings) > MAX_STRINGS:
                raise CompileError(chapter.line, f"chapter '{chapter.title}' has "
                                                 f"{len(car.strings)} texts; the most is "
                                                 f"{MAX_STRINGS}")
            self.cars.append(car)

        all_strings = [s for car in self.cars for s in car.strings]
        pairs, packed = compress(all_strings)
        i = 0
        for car in self.cars:
            car.packed = packed[i:i + len(car.strings)]
            i += len(car.strings)

        car_bytes = [self.car_bytes(car) for car in self.cars]
        for car, data in zip(self.cars, car_bytes):
            if len(data) > MAX_CAR:
                ch = self.dep.chapters[car.index]
                raise CompileError(ch.line, f"chapter '{ch.title}' compiles to {len(data)} "
                                            f"bytes; the most is {MAX_CAR}. Split it into "
                                            "two chapters.")
        depot = self.depot_bytes(pairs, hash_value=0)
        if len(depot) > MAX_DEPOT:
            raise CompileError(1, f"the depot (scenes, text pairs, pictures and battle maps) "
                                  f"is {len(depot)} bytes; the most is {MAX_DEPOT}. Use "
                                  "fewer or smaller battle maps.")
        h = crc16(depot + b"".join(car_bytes))
        depot = self.depot_bytes(pairs, hash_value=h)
        return Image(depot, car_bytes, pairs, self)

    def car_bytes(self, car):
        code = bytes(car.asm.code)
        strings = b""
        offsets = []
        for s in car.packed:
            offsets.append(len(strings))
            strings += s + b"\x00"
        out = bytearray(b"CR")
        out += struct.pack("<BHHH", car.index, car.title_id, len(code), len(car.packed))
        out += code
        for o in offsets:
            out += struct.pack("<H", o)
        out += strings
        return bytes(out)

    def depot_bytes(self, pairs, hash_value):
        d = self.dep
        out = bytearray(b"DP")
        flag_count = len(self.flags) + len(self.visited_flags) + len(self.chapter_flags) + \
            len(self.once_flags)
        out += struct.pack("<BBHBBBBBHBHHH", IMAGE_VERSION,
                           0 if d.kind == "official" else 1, d.id,
                           d.season if d.kind == "official" else 0, d.tl, d.ml,
                           d.level_min, d.level_max, flag_count, len(self.var_ids),
                           len(self.scenes), self.scene_ids[d.start], hash_value)
        title = d.title.encode("ascii")
        out += bytes([len(title)]) + title
        out += bytes(v for v, _ in d.vars.values())
        for s in self.scenes:
            out += struct.pack("<BH", self.scene_car[s.name], self.scene_offset[s.name])
        out += bytes([len(pairs)])
        for a, b in pairs:
            out += bytes([a, b])
        out += bytes([len(self.pictures)])
        for p in self.pictures:
            name = p.encode("ascii")
            out += bytes([len(name)]) + name
        out += bytes([len(self.dep.maps)])
        for m in self.dep.maps.values():
            blob = self.encounter_bytes(m)
            out += struct.pack("<H", len(blob)) + blob
        return bytes(out)

    def encounter_bytes(self, m):
        """A battle map and its foes (docs/vm-spec.md, Encounters). Each foe's numbers are
        copied from the bestiary, so the image stands on its own."""
        w, h = len(m.rows[0]), len(m.rows)
        codes = [MAP_TILES.index(c) if c in MAP_TILES else 0 for r in m.rows for c in r]
        if len(codes) % 2:
            codes.append(0)
        out = bytearray([w, h])
        out += bytes((codes[i] << 4) | codes[i + 1] for i in range(0, len(codes), 2))
        starts = [(x, y) for y, r in enumerate(m.rows) for x, c in enumerate(r) if c == "@"]
        out += bytes([len(starts)])
        for x, y in starts:
            out += bytes([x, y])
        foes = [(x, y, c) for y, r in enumerate(m.rows) for x, c in enumerate(r) if "a" <= c <= "z"]
        out += bytes([len(foes)])
        for x, y, c in foes:
            f = self.reg["foes"][m.foes[c]]
            reach = REACH[f["reach"]]
            out += bytes([x, y, f["health"], f["grace"], f["grace"] // 5, f["armor"], f["ward"],
                          f["soak"], f["speed"], f["attack"], f["damage"], f["type"],
                          int(reach != "melee"), int(reach == "power"), f["area"],
                          255 if f["weak"] is None else f["weak"], f["behavior"],
                          int(f["coward"])])
        for x, y, c in foes:
            name = self.reg["foes"][m.foes[c]]["display"].encode("ascii")[:FOE_NAME_MAX]
            out += bytes([len(name)]) + name
        return bytes(out)


OFFICIAL_ONLY_COMMANDS = {"echo", "debt"}
assert {"DEBT", "ECHO_SET"} == OFFICIAL_ONLY


def crc16(data):
    """CRC-16/CCITT-FALSE, as used by the Passport."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


class Image:
    def __init__(self, depot, cars, pairs, compiler):
        self.depot = depot
        self.cars = cars
        self.pairs = pairs
        self.compiler = compiler

    def apd(self):
        """The single-file form: APD1 container, depot, then the cars."""
        out = bytearray(b"APD1")
        out += struct.pack("<HBB", len(self.depot), len(self.cars), 0)
        for c in self.cars:
            out += struct.pack("<H", len(c))
        out += self.depot
        for c in self.cars:
            out += c
        return bytes(out)

    def files(self):
        """The split form for disks: DEPOT, CAR00, CAR01, ..."""
        out = {"DEPOT": self.depot}
        for i, c in enumerate(self.cars):
            out[f"CAR{i:02d}"] = c
        return out


def compile_departure(dep, registry):
    """Returns an Image. Raises CompileError for limits only the code generator can see."""
    return Compiler(dep, registry).compile()
