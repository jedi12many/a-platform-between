"""Quest Script parser: source text to a checked Departure (see qs_ast.py).

Implements docs/quest-script.md. Errors are collected, not raised, so an author
sees every problem at once, each with a line number and, where we can guess, a
"did you mean".
"""

import difflib
import re

import qs_ast as A

HEADER_KEYS = ["title", "id", "kind", "season", "realm", "levels", "start", "linear"]
INSERTS = ["name", "race", "class", "debt", "level", "yard"]
KEYWORDS = {"if", "else", "check", "flag", "var", "and", "or", "not", "has", "echo",
            "visited", "level", "race", "class", "name", "debt", "vs"}
COMMANDS = ["set", "clear", "let", "add", "sub", "echo", "give", "take", "xp", "debt",
            "heal", "picture", "music", "pause", "end", "pick"]
OUTCOMES = ["crit", "success", "cost", "fail"]
TN_WORDS = {"easy": 80, "routine": 90, "normal": 100, "tricky": 110, "hard": 120,
            "very_hard": 130}
OPS = ["<=", ">=", "!=", "=", "<", ">"]
STATS = ["MIGHT", "GRACE", "GRIT", "WITS", "PRESENCE", "FATE"]

MAX_FLAGS = 512
MAX_MUSIC = 32
MAX_VARS = 128
MAX_CHOICES = 9
MAX_LABEL = 37
MAX_TITLE = 40
MAX_FIXED_LINE = 38    # a | line on a 40-column screen
# Battle maps (docs/combat.md).
MAP_TILES = ".#O~+^=>"
MAP_W_MAX = 16
MAP_H_MAX = 10
PARTY_MAX = 4
FIGHTERS_MAX = 8
FIGHT_OUTCOMES = ["won", "lost", "fled"]
YARD_POOL_MAX = 7          # a pool's foes stand in a row beside one start (docs/deep-yards.md)
MAX_PICKS = 255
SURPRISE = {"ambush": 1, "sneak": 2}

LOWER_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
UPPER_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
TYPOGRAPHY = {"‘": "'", "’": "'", "“": '"', "”": '"',
              "—": "--", "–": "-", "…": "...", " ": " "}


class Diagnostics:
    def __init__(self, path):
        self.path = path
        self.errors = []      # (line, message)
        self.warnings = []

    def error(self, line, msg):
        self.errors.append((line, msg))

    def warn(self, line, msg):
        self.warnings.append((line, msg))


def suggest(name, candidates):
    match = difflib.get_close_matches(name, list(candidates), n=1, cutoff=0.6)
    return f" Did you mean '{match[0]}'?" if match else ""


class Line:
    def __init__(self, no, indent, text, tabbed=False):
        self.no = no
        self.indent = indent
        self.text = text
        self.tabbed = tabbed      # already reported; don't complain about its indent too

    @property
    def blank(self):
        return self.text == ""


def first_indent(lines):
    for ln in lines:
        if not ln.blank:
            return ln.indent
    return 0


def split_lines(source, diag):
    lines = []
    for no, raw in enumerate(source.splitlines(), 1):
        body = raw.lstrip(" \t")
        lead = raw[:len(raw) - len(body)]
        if "\t" in lead:
            diag.error(no, "a tab in the indentation: use spaces (tabs look the same "
                           "but count differently)")
        cut = body.find("//")
        if cut >= 0:
            body = body[:cut]
        body = body.rstrip()
        lines.append(Line(no, len(lead.replace("\t", "    ")), body, "\t" in lead))
    return lines


class Parser:
    def __init__(self, path, source, registry):
        self.diag = Diagnostics(path)
        self.reg = registry
        self.dep = A.Departure(path=path)
        self.lines = split_lines(source, self.diag)
        self.scene_refs = []          # (name, line) to check once all scenes are known
        self.used_flags = set()
        self.used_vars = set()
        self.picks = 0                # `~ pick`s so far: each gets the next salt
        self.skills = {name: e["id"] for name, e in registry["skills"].items()}

    # -------------------------------------------------------------- helpers

    def err(self, line, msg):
        self.diag.error(line, msg)

    def ascii_text(self, text, line):
        out = []
        for c in text:
            c = TYPOGRAPHY.get(c, c)
            if all(" " <= ch <= "~" for ch in c):
                out.append(c)
            else:
                self.err(line, f"the character '{c}' can't be shown on the old machines; "
                               "use plain ASCII")
        return "".join(out)

    def text_parts(self, text, line):
        """Split text into strings and Inserts, checking {...} names."""
        text = self.ascii_text(text, line)
        parts = []
        pos = 0
        for m in re.finditer(r"\{([^{}]*)\}", text):
            if m.start() > pos:
                parts.append(text[pos:m.start()])
            word = m.group(1).strip()
            if word in INSERTS:
                parts.append(A.Insert(word))
            elif word in self.dep.vars:
                self.used_vars.add(word)
                parts.append(A.Insert("var", word))
            else:
                self.err(line, f"'{{{word}}}' isn't something text can show. Use {{name}}, "
                               f"{{race}}, {{class}}, {{debt}}, {{level}} or a variable."
                               + suggest(word, INSERTS + list(self.dep.vars)))
            pos = m.end()
        rest = text[pos:]
        if "{" in rest or "}" in rest or any("{" in p or "}" in p
                                             for p in parts if isinstance(p, str)):
            self.err(line, "a '{' or '}' without its partner; inserts look like {name}")
        if rest:
            parts.append(rest)
        return parts

    def lower_name(self, word, line, what):
        if not LOWER_NAME.match(word):
            self.err(line, f"{what} '{word}' should be lower_case_with_underscores")
            return False
        if word in KEYWORDS:
            self.err(line, f"'{word}' is a Quest Script word and can't be a {what}")
            return False
        return True

    def number(self, word, line, lo, hi, what):
        if not re.fullmatch(r"\d+", word or ""):
            self.err(line, f"{what} should be a whole number, not '{word}'")
            return lo
        v = int(word)
        if not lo <= v <= hi:
            self.err(line, f"{what} {v} is out of range: it must be {lo} to {hi}")
            return max(lo, min(hi, v))
        return v

    def registry_name(self, table, word, line, what):
        if word not in self.reg[table]:
            self.err(line, f"there's no {what} called '{word}' in the registry."
                           + suggest(word, self.reg[table]))
            return False
        return True

    def flag_ref(self, name, line, in_command=False):
        if name in self.dep.flags:
            self.used_flags.add(name)
            return True
        if name in self.dep.vars:
            how = (f"'~ let {name} = 1' or '~ add {name} 1'" if in_command
                   else f"compare it, like '{name} >= 1'")
            self.err(line, f"'{name}' is a variable, not a flag: {how}")
            return False
        self.err(line, f"there's no flag called '{name}'. Declare it at the top with "
                       f"'flag {name}'." + suggest(name, self.dep.flags))
        return False

    def var_ref(self, name, line):
        if name in self.dep.vars:
            self.used_vars.add(name)
            return True
        self.err(line, f"there's no variable called '{name}'. Declare it at the top with "
                       f"'var {name} = 0'." + suggest(name, self.dep.vars))
        return False

    # ----------------------------------------------------------- top level

    def parse(self):
        lines = self.lines
        i = self.parse_header(0)
        i = self.parse_declarations(i)
        self.parse_chapters(i)
        self.check_departure()
        return self.dep, self.diag

    def parse_header(self, i):
        seen = {}
        lines = self.lines
        while i < len(lines):
            ln = lines[i]
            if ln.blank:
                i += 1
                continue
            m = re.match(r"^([a-z_]+):\s*(.*)$", ln.text)
            if not m or ln.indent != 0:
                break
            key, value = m.group(1), m.group(2).strip()
            if key not in HEADER_KEYS:
                self.err(ln.no, f"unknown header line '{key}:'." + suggest(key, HEADER_KEYS))
            elif key in seen:
                self.err(ln.no, f"'{key}:' is already set on line {seen[key]}")
            else:
                seen[key] = ln.no
                self.header_value(key, value, ln.no)
            i += 1
        first = lines[i].no if i < len(lines) else (lines[-1].no if lines else 1)
        for key in ("title", "id", "kind", "realm", "levels", "start"):
            if key not in seen:
                self.err(first, f"the header is missing '{key}:'")
        if self.dep.kind == "official" and "season" not in seen and "kind" in seen:
            self.err(first, "official Departures need 'season:' in the header")
        if self.dep.kind != "official" and "season" in seen:
            self.err(seen["season"], "'season:' is only for official Departures")
        return i

    def header_value(self, key, value, line):
        d = self.dep
        if key == "title":
            d.title = self.ascii_text(value, line)
            if not d.title:
                self.err(line, "the title is empty")
            if len(d.title) > MAX_TITLE:
                self.err(line, f"the title is {len(d.title)} characters; the most is {MAX_TITLE}")
        elif key == "id":
            d.id = self.number(value, line, 0, 65535, "id")
        elif key == "kind":
            if value not in ("official", "branch", "siding"):
                self.err(line, f"kind must be 'official', 'branch' or 'siding', not '{value}'")
            else:
                d.kind = value
        elif key == "season":
            d.season = self.number(value, line, 1, 255, "season")
        elif key == "realm":
            m = re.fullmatch(r"tl\s*(\d+)\s*,\s*ml\s*(\d+)", value)
            if not m:
                self.err(line, f"realm should look like 'tl 5, ml 5', not '{value}'")
            else:
                d.tl = self.number(m.group(1), line, 0, 9, "TL")
                d.ml = self.number(m.group(2), line, 0, 9, "ML")
        elif key == "levels":
            m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", value)
            if not m:
                self.err(line, f"levels should look like '2-5', not '{value}'")
            else:
                d.level_min = self.number(m.group(1), line, 1, 100, "lowest level")
                d.level_max = self.number(m.group(2), line, 1, 100, "highest level")
                if d.level_min > d.level_max:
                    self.err(line, "the level band runs backwards")
        elif key == "linear":
            if value not in ("yes", "no"):
                self.err(line, f"linear must be 'yes' or 'no', not '{value}'")
            else:
                d.linear = value == "yes"
        elif key == "start":
            if self.lower_name(value, line, "scene name"):
                d.start = value
                self.scene_refs.append((value, line))

    def parse_declarations(self, i):
        lines = self.lines
        while i < len(lines):
            ln = lines[i]
            if ln.blank:
                i += 1
                continue
            if ln.text.startswith("==") and ln.indent == 0:
                break
            words = ln.text.split()
            if words[0] == "map":
                kids, nxt = self.children(lines, i, ln.indent)
                self.parse_map(ln, kids)
                i = nxt
                continue
            if words[0] == "yard":
                kids, nxt = self.children(lines, i, ln.indent)
                self.parse_yard(ln, kids)
                i = nxt
                continue
            if words[0] == "flag" and len(words) == 2:
                self.declare(words[1], ln.no, None)
            elif words[0] == "var":
                m = re.fullmatch(r"var\s+(\S+)\s*=\s*(\S+)", ln.text)
                if not m:
                    self.err(ln.no, "a variable is declared like 'var loops = 0'")
                else:
                    self.declare(m.group(1), ln.no,
                                 self.number(m.group(2), ln.no, 0, 255, "a variable's value"))
            else:
                self.err(ln.no, "expected 'flag name', 'var name = 0', 'map name', 'yard name', "
                                "a '=== Chapter' or a '== scene' here")
            i += 1
        if len(self.dep.flags) > MAX_FLAGS:
            self.err(1, f"{len(self.dep.flags)} flags; the most is {MAX_FLAGS}")
        if len(self.dep.vars) > MAX_VARS:
            self.err(1, f"{len(self.dep.vars)} variables; the most is {MAX_VARS}")
        return i

    def parse_map(self, ln, kids):
        words = ln.text.split()
        if len(words) != 2:
            self.err(ln.no, "a battle map is declared like 'map scrapyard', with its rows "
                            "indented underneath")
            return
        name = words[1]
        if not self.lower_name(name, ln.no, "map name"):
            return
        if name in self.dep.maps:
            self.err(ln.no, f"there's already a map called '{name}', on line "
                            f"{self.dep.maps[name].line}")
            return
        rows, row_lines, foes = [], [], {}
        for k in kids:
            if k.blank:
                continue
            m = re.fullmatch(r"([a-z])\s*=\s*(\S+)", k.text)
            if m:
                letter, foe = m.groups()
                if letter in foes:
                    self.err(k.no, f"'{letter}' is already given a foe on this map")
                elif foe not in self.reg["foes"]:
                    self.err(k.no, f"there's no foe called '{foe}' in the bestiary "
                                   f"(registry/foes.txt)." + suggest(foe, self.reg["foes"]))
                foes[letter] = foe
            elif foes:
                self.err(k.no, "the map's rows come first, then a line like 'a = RUST_GUARD' "
                               "for each letter")
            else:
                rows.append(k.text)
                row_lines.append(k.no)
        if not rows:
            self.err(ln.no, f"map '{name}' has no rows: indent them under 'map {name}'")
            return
        if len(rows) > MAP_H_MAX:
            self.err(row_lines[MAP_H_MAX], f"a map has at most {MAP_H_MAX} rows")
        width = len(rows[0])
        if width > MAP_W_MAX:
            self.err(row_lines[0], f"this row is {width} squares; a map is at most "
                                   f"{MAP_W_MAX} wide")
        starts = 0
        letters = []
        for r, at in zip(rows, row_lines):
            if len(r) != width:
                self.err(at, f"every row of a map must be the same width: this one is "
                             f"{len(r)} squares, the first is {width}")
            for c in r:
                if c == "@":
                    starts += 1
                elif "a" <= c <= "z":
                    letters.append(c)
                elif c not in MAP_TILES:
                    self.err(at, f"'{c}' isn't a square on a battle map: use . # O ~ + ^ = >, "
                                 "@ where travelers start, or a letter for a foe")
        if starts == 0:
            self.err(ln.no, f"map '{name}' needs at least one '@', where the travelers start")
        elif starts > PARTY_MAX:
            self.err(ln.no, f"map '{name}' has {starts} '@'s; a party is at most {PARTY_MAX}")
        if not letters:
            self.err(ln.no, f"map '{name}' has no foes: put a letter where each one starts")
        if starts + len(letters) > FIGHTERS_MAX:
            self.err(ln.no, f"map '{name}' has {starts} '@'s and {len(letters)} foes; a fight "
                            f"holds at most {FIGHTERS_MAX} in all")
        for c in sorted(set(letters)):
            if c not in foes:
                self.err(ln.no, f"'{c}' stands on map '{name}' but isn't given a foe: add a "
                                f"line like '{c} = RUST_GUARD'")
        for c in foes:
            if c not in letters:
                self.diag.warn(ln.no, f"'{c}' is given a foe but isn't on map '{name}'")
        self.dep.maps[name] = A.Map(name, rows, foes, ln.no)

    def parse_yard(self, ln, kids):
        """`yard depths` and the bestiary's foes under it, weakest first: a pool for the
        Deep Yards' generated maps (docs/deep-yards.md)."""
        words = ln.text.split()
        if len(words) != 2:
            self.err(ln.no, "a yard's foes are declared like 'yard depths', with the bestiary's "
                            "foes indented underneath, weakest first")
            return
        name = words[1]
        if not self.lower_name(name, ln.no, "yard name"):
            return
        if name in self.dep.maps:
            self.err(ln.no, f"there's already a map or yard called '{name}', on line "
                            f"{self.dep.maps[name].line}")
            return
        foes = []
        for k in kids:
            for foe in k.text.replace(",", " ").split():
                if foe not in self.reg["foes"]:
                    self.err(k.no, f"there's no foe called '{foe}' in the bestiary "
                                   f"(registry/foes.txt)." + suggest(foe, self.reg["foes"]))
                foes.append(foe)
        if not foes:
            self.err(ln.no, f"yard '{name}' has no foes: list them under it, weakest first")
            return
        if len(foes) > YARD_POOL_MAX:
            self.err(ln.no, f"yard '{name}' lists {len(foes)} foes; a yard holds at most "
                            f"{YARD_POOL_MAX}")
            return
        import codegen
        rows, by_letter = codegen.pool_rows(foes)
        self.dep.maps[name] = A.Map(name, rows, by_letter, ln.no, yard=True)

    def declare(self, name, line, value):
        if not self.lower_name(name, line, "flag or variable name"):
            return
        if name in self.dep.flags or name in self.dep.vars:
            first = self.dep.flags.get(name) or self.dep.vars[name][1]
            self.err(line, f"'{name}' is already declared on line {first}")
            return
        if value is None:
            self.dep.flags[name] = line
        else:
            self.dep.vars[name] = (value, line)

    def parse_chapters(self, i):
        lines = self.lines
        chapter = None
        scene_name = None
        scene_line = 0
        skipping = False          # inside a scene whose heading was bad: stay quiet
        body = []
        seen = {}

        def finish_scene():
            if scene_name is None:
                return
            if chapter is None:
                return
            stmts, choices = self.parse_scene_body(body)
            chapter.scenes.append(A.Scene(scene_name, stmts, choices, scene_line))

        while i < len(lines):
            ln = lines[i]
            if ln.indent == 0 and ln.text.startswith("==="):
                finish_scene()
                scene_name, body, skipping = None, [], False
                title = self.ascii_text(ln.text[3:].strip().rstrip("=").strip(), ln.no)
                if not title:
                    self.err(ln.no, "a chapter needs a title: '=== The Static'")
                chapter = A.Chapter(title, [], ln.no)
                self.dep.chapters.append(chapter)
            elif ln.indent == 0 and ln.text.startswith("=="):
                finish_scene()
                name = ln.text[2:].strip()
                body = []
                if chapter is None:
                    chapter = A.Chapter("", [], ln.no)
                    self.dep.chapters.append(chapter)
                scene_name, skipping = None, True
                if self.lower_name(name, ln.no, "scene name"):
                    if name in seen:
                        self.err(ln.no, f"there's already a scene called '{name}' "
                                        f"(line {seen[name]})")
                    else:
                        seen[name] = ln.no
                        scene_name, scene_line, skipping = name, ln.no, False
            elif ln.text.startswith("==") and not ln.blank:
                self.err(ln.no, "chapter and scene headings must start at the left edge")
            elif scene_name is not None:
                body.append(ln)
            elif not ln.blank and not skipping:
                self.err(ln.no, "this line isn't inside a scene: add '== scene_name' above it")
            i += 1
        finish_scene()
        if not any(True for _ in self.dep.scenes()) and not self.diag.errors:
            self.err(1, "this Departure has no scenes")

    # -------------------------------------------------------------- scenes

    def parse_scene_body(self, lines):
        return self.parse_block(lines, 0, allow_choices=True)

    def children(self, lines, i, indent):
        """The lines after lines[i] that are indented deeper than `indent`."""
        j = i + 1
        while j < len(lines) and (lines[j].blank or lines[j].indent > indent):
            j += 1
        kids = lines[i + 1:j]
        while kids and kids[-1].blank:
            kids.pop()
        # Blank lines after the children belong to the enclosing block: they end a
        # paragraph there.
        return kids, i + 1 + len(kids)

    def parse_block(self, lines, indent, allow_choices=False):
        stmts = []
        choices = []
        para = None                     # [parts, line, last line was a | line]

        def flush():
            nonlocal para
            if para is not None and para[0]:
                stmts.append(A.Text(para[0], para[1]))
            para = None

        def add_text(parts, line, fixed=False):
            nonlocal para
            if not parts:
                return
            if para is None:
                para = [list(parts), line, fixed]
            else:
                para[0].append("\n" if fixed or para[2] else " ")
                para[0].extend(parts)
                para[2] = fixed

        i = 0
        while i < len(lines):
            ln = lines[i]
            if ln.blank:
                flush()
                i += 1
                continue
            if ln.indent > indent:
                if not ln.tabbed:
                    self.err(ln.no, "this line is indented more than the line above it, "
                                    "but nothing above opens a block")
                _, i = self.children(lines, i, ln.indent - 1)
                continue
            t = ln.text
            kids, nxt = self.children(lines, i, indent)

            if t[0] in "+*" and (len(t) == 1 or t[1] in " {["):
                flush()
                if not allow_choices:
                    self.err(ln.no, "choices go at the end of a scene, not inside another "
                                    "block. To make a choice conditional, write "
                                    "'+ {condition} [label]'")
                else:
                    choices.append(self.parse_choice(ln, kids))
                i = nxt
                continue

            if choices:
                self.err(ln.no, "only choices can come after a scene's choices: move this "
                                "above them, or into a choice")
                i = nxt
                continue

            if t == "if" or t.startswith("if "):
                flush()
                stmt, i = self.parse_if(lines, i, indent)
                stmts.append(stmt)
                continue
            if t == "else" or t.startswith("else "):
                flush()
                self.err(ln.no, "'else' without an 'if' above it at the same indentation")
                i = nxt
                continue
            if t == "check" or t.startswith("check "):
                flush()
                stmts.append(self.parse_check(ln, kids))
                i = nxt
                continue
            if t == "fight" or t.startswith("fight "):
                flush()
                stmts.append(self.parse_fight(ln, kids))
                i = nxt
                continue
            if t.startswith("=="):
                flush()
                self.err(ln.no, "chapter and scene headings must start at the left edge")
                i = nxt
                continue
            if t.startswith("{"):
                self.err(ln.no, "a line can't start with '{': start it with \\ to print it "
                                "as text, or put conditions on a choice or an 'if'")
                i = nxt
                continue

            if t.startswith("|"):
                fixed = t[1:][1:] if t[1:2] == " " else t[1:]
                if len(fixed) > MAX_FIXED_LINE:
                    self.diag.warn(ln.no, f"this | line is {len(fixed)} characters; it will "
                                          f"wrap on a 40-column screen (keep it to "
                                          f"{MAX_FIXED_LINE})")
                add_text(self.text_parts(fixed, ln.no), ln.no, fixed=True)
                i = nxt
                continue

            if kids:
                self.err(next(k for k in kids if not k.blank).no,
                         "this line is indented under text, which doesn't open "
                                     "a block")
            parts, cmds, goto = self.parse_line(t, ln.no)
            add_text(parts, ln.no)
            if cmds or goto:
                flush()
                stmts.extend(cmds)
                if goto:
                    stmts.append(goto)
            i = nxt
        flush()
        if allow_choices:
            return stmts, choices
        return stmts

    def parse_line(self, t, line):
        """A text line, possibly ending in '~ commands' and/or '-> scene'."""
        goto = None
        m = re.search(r"(?:^|\s)->\s*(\S+)\s*$", t)
        if m:
            target = m.group(1)
            if self.lower_name(target, line, "scene name"):
                goto = A.Goto(target, line)
                self.scene_refs.append((target, line))
            t = t[:m.start()].rstrip()
        cmds = []
        m = re.search(r"(?:^|\s)~(?=\s|$)", t)
        if m:
            for piece in re.split(r"(?:^|\s)~(?=\s|$)", t[m.start():]):
                piece = piece.strip()
                if piece:
                    cmd = self.parse_command(piece, line)
                    if cmd:
                        cmds.append(cmd)
            t = t[:m.start()].rstrip()
        if t.startswith("\\"):
            t = t[1:]
        elif t.startswith("->"):
            self.err(line, f"'{t}' isn't a scene to go to")
            t = ""
        return (self.text_parts(t, line) if t else []), cmds, goto

    # ------------------------------------------------------------- choices

    def parse_choice(self, ln, kids):
        m = re.fullmatch(r"([+*])\s*(?:\{(.*?)\})?\s*\[(.*?)\]\s*(?:->\s*(\S+))?", ln.text)
        if not m:
            self.err(ln.no, "a choice looks like '+ [Label] -> scene' or "
                            "'* {condition} [Label]'")
            return A.Choice(True, None, "?", None, [], ln.no)
        sticky = m.group(1) == "+"
        cond = self.parse_cond(m.group(2), ln.no) if m.group(2) is not None else None
        label = self.ascii_text(m.group(3).strip(), ln.no)
        if not label:
            self.err(ln.no, "the choice's label is empty")
        if len(label) > MAX_LABEL:
            self.err(ln.no, f"the label is {len(label)} characters; the most is {MAX_LABEL} "
                            "so it fits a C64 line")
        target = m.group(4)
        if target is not None:
            if self.lower_name(target, ln.no, "scene name"):
                self.scene_refs.append((target, ln.no))
            else:
                target = None
        body = []
        if kids:
            if target is not None:
                self.err(ln.no, "a choice can jump straight to a scene or have lines under "
                                "it, not both: put the '-> scene' at the end of its lines")
            body = self.parse_block(kids, first_indent(kids))
        return A.Choice(sticky, cond, label, target, body, ln.no)

    # ------------------------------------------------------------------ if

    def parse_if(self, lines, i, indent):
        ln = lines[i]
        branches = []
        cond_text = ln.text[2:].strip()
        if not cond_text:
            self.err(ln.no, "'if' needs a condition, like 'if met_fen'")
        cond = self.parse_cond(cond_text, ln.no) if cond_text else None
        kids, i = self.children(lines, i, indent)
        if not kids:
            self.err(ln.no, "nothing is indented under this 'if'")
        branches.append((cond, self.parse_block(kids, first_indent(kids)) if kids else []))
        while i < len(lines):
            k = i
            while k < len(lines) and lines[k].blank:
                k += 1
            if k >= len(lines) or lines[k].indent != indent or \
                    not (lines[k].text == "else" or lines[k].text.startswith("else")):
                break
            i = k
            nxt = lines[i]
            t = nxt.text
            if t.startswith("else if "):
                c = self.parse_cond(t[8:].strip(), nxt.no)
            elif t == "else":
                c = None
            elif t.startswith("else"):
                self.err(nxt.no, "write 'else' alone, or 'else if condition'")
                c = None
            else:
                break
            if branches[-1][0] is None:
                self.err(nxt.no, "nothing can follow a plain 'else'")
            kids, i = self.children(lines, i, indent)
            if not kids:
                self.err(nxt.no, "nothing is indented under this 'else'")
            branches.append((c, self.parse_block(kids, first_indent(kids)) if kids else []))
        return A.If(branches, ln.no), i

    # --------------------------------------------------------------- check

    def parse_check(self, ln, kids):
        words = ln.text.split()
        rating = None
        tn = 100
        if len(words) < 2:
            self.err(ln.no, "'check' needs a stat or skill, like 'check TECH hard'")
        else:
            name = words[1]
            if name in STATS:
                rating = ("stat", STATS.index(name))
            elif name in self.skills:
                rating = ("skill", self.skills[name])
            else:
                self.err(ln.no, f"'{name}' isn't a stat or skill."
                                + suggest(name, STATS + list(self.skills)))
            rest = words[2:]
            if rest:
                if rest[0] == "vs" and len(rest) == 2:
                    tn = self.number(rest[1], ln.no, 50, 250, "the TN")
                elif len(rest) == 1 and rest[0] in TN_WORDS:
                    tn = TN_WORDS[rest[0]]
                else:
                    self.err(ln.no, f"after the skill, write a difficulty "
                                    f"({', '.join(TN_WORDS)}) or 'vs' and a number."
                                    + suggest(rest[0], list(TN_WORDS) + ["vs"]))
        outcomes = {}
        if not kids:
            self.err(ln.no, "nothing is indented under this 'check': add crit:, success:, "
                            "cost: or fail: lines")
        j = 0
        while j < len(kids):
            k = kids[j]
            if k.blank:
                j += 1
                continue
            sub, nj = self.children(kids, j, k.indent)
            m = re.match(r"^([a-z_]+)\s*:\s*(.*)$", k.text)
            if not m or m.group(1) not in OUTCOMES:
                word = m.group(1) if m else k.text.split()[0]
                self.err(k.no, "under a check, each line starts with crit:, success:, cost: "
                               "or fail:." + suggest(word, OUTCOMES))
                j = nj
                continue
            which, inline = m.group(1), m.group(2)
            if which in outcomes:
                self.err(k.no, f"'{which}:' appears twice in this check")
            block = list(sub)
            if inline:
                at = block[0].indent if block else k.indent + 4
                block.insert(0, Line(k.no, at, inline))
            if not block:
                self.err(k.no, f"'{which}:' is empty")
            outcomes[which] = self.parse_block(block, block[0].indent) if block else []
            j = nj
        return A.Check(rating, tn, outcomes, ln.no)

    def parse_fight(self, ln, kids):
        words = ln.text.split()
        name, surprise, floor = None, 0, None
        # `fight yard POOL on VAR`; but `fight yard` alone, or `fight yard ambush`, is an
        # ordinary map that happens to be called yard.
        in_yard = (len(words) >= 3 and words[1] == "yard"
                   and ("on" in words or (words[2] in self.dep.maps
                                          and self.dep.maps[words[2]].yard)))
        if in_yard:
            # fight yard POOL on VAR [ambush|sneak]
            if len(words) not in (5, 6) or words[3] != "on":
                self.err(ln.no, "a fight in the Deep Yards is written like 'fight yard depths on "
                                "floor': the yard's foes, and the variable that holds the floor")
                words = []
            else:
                floor = words[4]
                if self.var_ref(floor, ln.no) is False:
                    floor = None
                yard = words[2]
                if yard not in self.dep.maps or not self.dep.maps[yard].yard:
                    self.err(ln.no, f"there's no yard called '{yard}': declare it before the "
                                    "first chapter with 'yard " + yard + "' and its foes."
                                    + suggest(yard, [m for m in self.dep.maps
                                                     if self.dep.maps[m].yard]))
                words = ["fight", yard] + words[5:]
        if not words:
            pass
        elif len(words) < 2 or len(words) > 3:
            self.err(ln.no, "a fight is written like 'fight scrapyard', or 'fight scrapyard "
                            "ambush' (the foes go first) or 'fight scrapyard sneak' (you do)")
        else:
            name = words[1]
            if not in_yard and name in self.dep.maps and self.dep.maps[name].yard:
                self.err(ln.no, f"'{name}' is a yard: its maps are built for each floor. "
                                f"Write 'fight yard {name} on floor'")
            if name not in self.dep.maps:
                self.err(ln.no, f"there's no map called '{name}': declare it before the "
                                "first chapter with 'map " + name + "'."
                                + suggest(name, self.dep.maps))
            if len(words) == 3:
                if words[2] in SURPRISE:
                    surprise = SURPRISE[words[2]]
                else:
                    self.err(ln.no, f"after the map, write 'ambush' or 'sneak', or nothing."
                                    + suggest(words[2], list(SURPRISE)))
        outcomes = {}
        j = 0
        while j < len(kids):
            k = kids[j]
            if k.blank:
                j += 1
                continue
            sub, nj = self.children(kids, j, k.indent)
            m = re.match(r"^([a-z_]+)\s*:\s*(.*)$", k.text)
            if not m or m.group(1) not in FIGHT_OUTCOMES:
                word = m.group(1) if m else k.text.split()[0]
                self.err(k.no, "under a fight, each line starts with won:, lost: or fled:."
                               + suggest(word, FIGHT_OUTCOMES))
                j = nj
                continue
            which, inline = m.group(1), m.group(2)
            if which in outcomes:
                self.err(k.no, f"'{which}:' appears twice in this fight")
            block = list(sub)
            if inline:
                at = block[0].indent if block else k.indent + 4
                block.insert(0, Line(k.no, at, inline))
            if not block:
                self.err(k.no, f"'{which}:' is empty")
            outcomes[which] = self.parse_block(block, block[0].indent) if block else []
            j = nj
        return A.Fight(name, surprise, outcomes, ln.no, floor)

    # ------------------------------------------------------------ commands

    def parse_command(self, text, line):
        words = text.split()
        name = words[0]
        args = words[1:]
        official = self.dep.kind == "official"
        others = "Sidings" if self.dep.kind == "siding" else "Branch Lines"

        def need(n, usage):
            if len(args) != n:
                self.err(line, f"'~ {name}' is written '~ {usage}'")
                return False
            return True

        if name in ("set", "clear"):
            if need(1, f"{name} flag_name") and self.flag_ref(args[0], line, True):
                return A.Command(name, [args[0]], line)
        elif name == "let":
            m = re.fullmatch(r"(\S+)\s*=\s*(\S+)", " ".join(args))
            if not m:
                self.err(line, "'~ let' is written '~ let loops = 3'")
            elif self.var_ref(m.group(1), line):
                return A.Command("let", [m.group(1), self.number(m.group(2), line, 0, 255,
                                                                  "the value")], line)
        elif name in ("add", "sub"):
            if need(2, f"{name} loops 1") and self.var_ref(args[0], line):
                return A.Command(name, [args[0], self.number(args[1], line, 0, 255,
                                                              "the amount")], line)
        elif name == "echo":
            if not official:
                self.err(line, f"{others} can't change Echoes: they can read them in "
                               "conditions, but not plant them")
                return None
            m = re.fullmatch(r"(\S+)\s*=\s*(\S+)", " ".join(args))
            if not m:
                self.err(line, "'~ echo' is written '~ echo WOLF_PUP = SAVED'")
            elif self.echo_state(m.group(1), m.group(2), line):
                return A.Command("echo", [m.group(1), m.group(2)], line)
        elif name in ("give", "take"):
            if need(1, f"{name} ITEM_NAME") and self.registry_name("items", args[0], line,
                                                                   "item"):
                item = self.reg["items"][args[0]]
                if name == "give" and not official and item["tier"] > 3:
                    self.err(line, f"Branch Lines can only give items of tier 3 or lower; "
                                   f"{args[0]} is tier {item['tier']}")
                return A.Command(name, [args[0]], line)
        elif name == "xp":
            if need(1, "xp 10"):
                return A.Command("xp", [self.number(args[0], line, 1, 255, "XP")], line)
        elif name == "heal":
            if need(1, "heal 10' or '~ heal full"):
                if args[0] == "full":
                    return A.Command("heal", [255], line)
                return A.Command("heal", [self.number(args[0], line, 1, 254, "healing")], line)
        elif name == "debt":
            if not official:
                self.err(line, f"{others} can't change Debt")
                return None
            m = re.fullmatch(r"([-+=])\s*(\d+)", " ".join(args))
            if not m:
                self.err(line, "'~ debt' is written '~ debt - 500', '~ debt + 500' or "
                               "'~ debt = 50000'")
            else:
                mode = {"=": "set", "+": "add", "-": "sub"}[m.group(1)]
                return A.Command("debt", [mode, self.number(m.group(2), line, 0, 65535,
                                                            "Debt")], line)
        elif name == "pick":
            # ~ pick room 4 [on floor]
            m = re.fullmatch(r"(\S+)\s+(\S+)(?:\s+on\s+(\S+))?", " ".join(args))
            if not m:
                self.err(line, "'~ pick' is written '~ pick room 4', or '~ pick room 4 on floor' "
                               "to pick again for each floor")
            elif self.var_ref(m.group(1), line) and (m.group(3) is None
                                                     or self.var_ref(m.group(3), line)):
                if self.picks >= MAX_PICKS:
                    self.err(line, f"more than {MAX_PICKS} picks in one Departure")
                    return None
                self.picks += 1
                return A.Command("pick", [m.group(1), self.number(m.group(2), line, 1, 255,
                                                                  "the number to pick from"),
                                          m.group(3), self.picks - 1], line)
        elif name == "picture":
            if need(1, "picture name") and self.lower_name(args[0], line, "picture name"):
                if args[0] not in self.dep.pictures:
                    self.dep.pictures.append(args[0])
                return A.Command("picture", [args[0]], line)
        elif name == "music":
            if need(1, "music NAME' or '~ music off"):
                if args[0] == "off":
                    return A.Command("music", [None], line)
                if not self.lower_name(args[0], line, "tune name"):
                    return None
                if len(args[0]) > 20:
                    self.err(line, f"the tune name '{args[0]}' is too long: 20 letters at most")
                    return None
                if args[0] not in self.dep.music:
                    if len(self.dep.music) >= MAX_MUSIC:
                        self.err(line, f"more than {MAX_MUSIC} tunes in one Departure")
                        return None
                    self.dep.music[args[0]] = line
                return A.Command("music", [args[0]], line)
        elif name == "pause":
            if need(0, "pause"):
                return A.Command("pause", [], line)
        elif name == "end":
            if need(1, "end complete"):
                if args[0] not in ("complete", "failed"):
                    self.err(line, f"'~ end' takes 'complete' or 'failed', not '{args[0]}'")
                else:
                    return A.Command("end", [args[0]], line)
        else:
            self.err(line, f"there's no command '~ {name}'." + suggest(name, COMMANDS))
        return None

    def echo_state(self, echo, state, line):
        if not self.registry_name("echoes", echo, line, "Echo"):
            return False
        states = self.reg["echoes"][echo]["states"]
        if state not in states:
            self.err(line, f"{echo} has no state '{state}'; its states are "
                           f"{', '.join(states)}." + suggest(state, states))
            return False
        return True

    # ---------------------------------------------------------- conditions

    def parse_cond(self, text, line):
        tokens = re.findall(r"<=|>=|!=|[=<>()]|[A-Za-z_][A-Za-z0-9_]*|\d+|\S", text or "")
        if not tokens:
            self.err(line, "an empty condition")
            return None
        self.toks = tokens
        self.pos = 0
        self.cline = line
        cond = self.cond_or()
        if self.pos < len(self.toks):
            self.err(line, f"didn't understand '{' '.join(self.toks[self.pos:])}' in the "
                           "condition")
        return cond

    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def take(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def cond_or(self):
        left = self.cond_and()
        while self.peek() == "or":
            self.take()
            left = A.Or(left, self.cond_and(), self.cline)
        return left

    def cond_and(self):
        left = self.cond_not()
        while self.peek() == "and":
            self.take()
            left = A.And(left, self.cond_not(), self.cline)
        return left

    def cond_not(self):
        if self.peek() == "not":
            self.take()
            return A.Not(self.cond_not(), self.cline)
        return self.cond_atom()

    def compare_value(self):
        op = self.take()
        if op not in OPS:
            self.err(self.cline, f"expected a comparison ({' '.join(OPS)}) here, not "
                                 f"'{op or 'the end'}'")
            return "=", 0
        value = self.take()
        return op, self.number(value, self.cline, 0, 255, "the number")

    def cond_atom(self):
        line = self.cline
        tok = self.take()
        if tok is None:
            self.err(line, "the condition ends too soon")
            return None
        if tok == "(":
            inner = self.cond_or()
            if self.take() != ")":
                self.err(line, "a '(' without its ')'")
            return inner
        if tok == "has":
            item = self.take() or ""
            self.registry_name("items", item, line, "item")
            return A.Has(item, line)
        if tok == "echo":
            echo, op, state = self.take() or "", self.take(), self.take() or ""
            if op not in ("=", "!="):
                self.err(line, "an Echo condition looks like 'echo WOLF_PUP = SAVED'")
            self.echo_state(echo, state, line)
            return A.EchoIs(echo, op, state, line)
        if tok == "race":
            race = self.take() or ""
            self.registry_name("races", race, line, "race")
            return A.IsRace(race, line)
        if tok == "class":
            cls = self.take() or ""
            self.registry_name("classes", cls, line, "class")
            return A.IsClass(cls, line)
        if tok == "visited":
            scene = self.take() or ""
            if self.lower_name(scene, line, "scene name"):
                self.scene_refs.append((scene, line))
            return A.Visited(scene, line)
        if tok == "level":
            op, value = self.compare_value()
            return A.Compare(("level",), op, value, line)
        if UPPER_NAME.match(tok):
            if tok in STATS:
                subject = ("stat", STATS.index(tok))
            elif tok in self.skills:
                subject = ("skill", self.skills[tok])
            else:
                self.err(line, f"'{tok}' isn't a stat or skill. Items need 'has {tok}'."
                               + suggest(tok, STATS + list(self.skills)))
                subject = ("stat", 0)
            op, value = self.compare_value()
            return A.Compare(subject, op, value, line)
        if LOWER_NAME.match(tok):
            if self.peek() in OPS:
                self.var_ref(tok, line)
                op, value = self.compare_value()
                return A.Compare(("var", tok), op, value, line)
            self.flag_ref(tok, line)
            return A.Flag(tok, line)
        self.err(line, f"didn't understand '{tok}' in the condition")
        return None

    # ------------------------------------------------------- whole program

    def check_departure(self):
        scenes = {s.name: s for s in self.dep.scenes()}
        for name, line in self.scene_refs:
            if name not in scenes:
                self.err(line, f"there's no scene called '{name}'." + suggest(name, scenes))
        for s in scenes.values():
            if len(s.choices) > MAX_CHOICES:
                self.err(s.choices[MAX_CHOICES].line,
                         f"scene '{s.name}' has {len(s.choices)} choices; a menu holds at "
                         f"most {MAX_CHOICES}")
            if not s.choices and not terminates(s.body):
                self.err(s.line, f"scene '{s.name}' has no choices and doesn't end with "
                                 "'-> scene' or '~ end': the player would be stuck")
        for name, line in self.dep.flags.items():
            if name not in self.used_flags:
                self.diag.warn(line, f"flag '{name}' is declared but never used")
        for name, (_, line) in self.dep.vars.items():
            if name not in self.used_vars:
                self.diag.warn(line, f"variable '{name}' is declared but never used")
        if self.dep.start in scenes and not self.diag.errors:
            import routes
            start_line = scenes[self.dep.start].line
            common, ends = routes.bottlenecks(self.dep)
            on_every_route = set(common) | {self.dep.start} | (set(ends) if len(ends) == 1 else set())
            for name in sorted(on_every_route & set(scenes), key=lambda n: scenes[n].line):
                for f in unavoidable_fights(scenes[name]):
                    self.diag.warn(f.line, "every road to the end goes through this fight: "
                                           "give players a way around it (another route, a "
                                           "check, a parley), like any roadblock")
            if not ends:
                self.diag.warn(start_line, "no route from the start reaches '~ end complete'")
            elif common and not self.dep.linear:
                shown = ", ".join(f"'{n}'" for n in common[:3])
                more = f" and {len(common) - 3} more" if len(common) > 3 else ""
                self.diag.warn(start_line, f"only one road to victory: every route to an "
                                           f"ending passes through {shown}{more}. Add "
                                           "another way, or put 'linear: yes' in the header "
                                           "if that's deliberate")
        if self.dep.start in scenes:
            reached = reachable(self.dep.start, scenes)
            for s in scenes.values():
                if s.name not in reached:
                    self.diag.warn(s.line, f"scene '{s.name}' can never be reached from "
                                           f"'{self.dep.start}'")


def terminates(stmts):
    """True if every way through these statements ends in a '->' or '~ end'."""
    if not stmts:
        return False
    last = stmts[-1]
    if isinstance(last, A.Goto):
        return True
    if isinstance(last, A.Command) and last.name == "end":
        return True
    if isinstance(last, A.If):
        return last.branches[-1][0] is None and all(terminates(b) for _, b in last.branches)
    if isinstance(last, A.Check):
        o = last.outcomes
        crit = o.get("crit", o.get("success"))
        return all(terminates(b) if b is not None else False
                   for b in (crit, o.get("success"), o.get("cost"), o.get("fail")))
    if isinstance(last, A.Fight):
        # Losing with no lost: branch ends the Departure (failed).
        o = last.outcomes
        return all(terminates(o[k]) if k in o else k == "lost" for k in FIGHT_OUTCOMES)
    return False


def fights_in(stmts):
    for st in stmts:
        if isinstance(st, A.Fight):
            yield st
        elif isinstance(st, A.If):
            for _, body in st.branches:
                yield from fights_in(body)
        elif isinstance(st, A.Check):
            for body in st.outcomes.values():
                yield from fights_in(body)


def unavoidable_fights(scene):
    """Fights a player can't avoid once in this scene: in its own text, or behind its only
    choice."""
    yield from fights_in(scene.body)
    if len(scene.choices) == 1:
        yield from fights_in(scene.choices[0].body)


def targets(stmts):
    for st in stmts:
        if isinstance(st, A.Goto):
            yield st.scene
        elif isinstance(st, A.If):
            for _, body in st.branches:
                yield from targets(body)
        elif isinstance(st, (A.Check, A.Fight)):
            for body in st.outcomes.values():
                yield from targets(body)


def reachable(start, scenes):
    seen = {start}
    todo = [start]
    while todo:
        s = scenes.get(todo.pop())
        if s is None:
            continue
        nxt = list(targets(s.body))
        for c in s.choices:
            if c.target:
                nxt.append(c.target)
            nxt.extend(targets(c.body))
        for n in nxt:
            if n not in seen:
                seen.add(n)
                todo.append(n)
    return seen


def parse(path, source, registry):
    """Parse and check one Departure. Returns (Departure, Diagnostics)."""
    return Parser(path, source, registry).parse()
