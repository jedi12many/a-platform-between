"""Load and check the registry: races, classes, skills, items, Echoes and foes.

The files in registry/ are the single source of truth. The C header and tables
(tools/registry/gen.py), the Passport tools and the Quest Script compiler all
read them through this module, so they can never disagree.

    from registry import load
    reg = load()                       # reads <repo>/registry/
    reg["items"]["PULSE_RIFLE"]["id"]  # 1
"""

import os
import shlex

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "registry")

STATS = ["MIGHT", "GRACE", "GRIT", "WITS", "PRESENCE", "FATE"]
ARCHETYPES = ["melee", "ranged", "armor", "tool", "focus", "vehicle"]
DAMAGE = ["kinetic", "energy", "fire", "cold", "mind"]
ECHO_KINDS = ["ally", "nemesis", "debt", "mark", "key"]
REACH = ["melee", "ranged", "power"]
BEHAVIORS = ["charge", "shoot", "guard"]

# Limits set by the Passport format (docs/passport-spec.md).
MAX_RACES = 32
MAX_CLASSES = 16
MAX_SKILLS = 12
MAX_ITEM_ID = 1023
MAX_ECHO_ID = 1023
MAX_ECHO_STATES = 3
MAX_FOE_ID = 1023


class RegistryError(ValueError):
    pass


def _rows(path):
    """Yield (line number, fields) for each non-blank, non-comment line."""
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            try:
                fields = shlex.split(line, comments=True)
            except ValueError as e:
                raise RegistryError(f"{path} line {n}: {e}") from None
            if fields:
                yield n, fields


def _fail(path, n, msg):
    raise RegistryError(f"{os.path.relpath(path)} line {n}: {msg}")


def _name(path, n, text, seen):
    if not text.replace("_", "").isalnum() or not text.isupper() or text[0].isdigit():
        _fail(path, n, f"'{text}' should be UPPER_CASE letters, digits and underscores")
    if text in seen:
        _fail(path, n, f"'{text}' is already used on line {seen[text]['line']}")
    return text


def _display(path, n, text):
    if not text or any(not (" " <= c <= "~") for c in text):
        _fail(path, n, f"'{text}': names shown to players must be plain ASCII")
    if len(text) > 24:
        _fail(path, n, f"'{text}' is longer than 24 characters")
    return text


def _int(path, n, text, lo, hi, what):
    try:
        v = int(text)
    except ValueError:
        _fail(path, n, f"{what} '{text}' isn't a number")
    if not lo <= v <= hi:
        _fail(path, n, f"{what} {v} must be {lo}..{hi}")
    return v


def _one_of(path, n, text, options, what):
    if text not in options:
        _fail(path, n, f"{what} '{text}' isn't one of: {', '.join(options)}")
    return options.index(text)


def _table(path, columns, parse, lo_id, hi_id, contiguous):
    """Read a file whose rows start with an id and a NAME; ids must increase."""
    entries = {}
    last = lo_id - 1
    for n, f in _rows(path):
        if len(f) != columns:
            _fail(path, n, f"expected {columns} columns, found {len(f)}")
        eid = _int(path, n, f[0], lo_id, hi_id, "id")
        if eid <= last:
            _fail(path, n, f"id {eid} must come after {last} (registries are append-only)")
        if contiguous and eid != last + 1:
            _fail(path, n, f"id {eid} skips {last + 1}; these ids can't have gaps")
        last = eid
        name = _name(path, n, f[1], entries)
        entry = {"id": eid, "name": name, "line": n}
        entry.update(parse(path, n, f))
        entries[name] = entry
    return entries


def load(root=ROOT):
    root = os.path.abspath(root)

    def path(name):
        return os.path.join(root, name)

    skills = _table(path("skills.txt"), 4, lambda p, n, f: {
        "stat": _one_of(p, n, f[2], STATS, "stat"),
        "display": _display(p, n, f[3]),
    }, 0, MAX_SKILLS - 1, True)

    def skill(p, n, text):
        if text not in skills:
            _fail(p, n, f"no skill called '{text}'")
        return skills[text]["id"]

    races = _table(path("races.txt"), 4, lambda p, n, f: {
        "bonus": _one_of(p, n, f[2], STATS, "stat"),
        "display": _display(p, n, f[3]),
    }, 0, MAX_RACES - 1, True)

    def class_row(p, n, f):
        tags = [skill(p, n, f[3]), skill(p, n, f[4])]
        if tags[0] == tags[1]:
            _fail(p, n, "a class must tag two different skills")
        return {"bonus": _one_of(p, n, f[2], STATS, "stat"), "tags": tags,
                "display": _display(p, n, f[5])}

    classes = _table(path("classes.txt"), 6, class_row, 0, MAX_CLASSES - 1, True)

    items = _table(path("items.txt"), 8, lambda p, n, f: {
        "archetype": _one_of(p, n, f[2], ARCHETYPES, "archetype"),
        "tier": _int(p, n, f[3], 1, 9, "tier"),
        "damage": _one_of(p, n, f[4], DAMAGE, "damage"),
        "tl": _int(p, n, f[5], 0, 9, "TL"),
        "ml": _int(p, n, f[6], 0, 9, "ML"),
        "display": _display(p, n, f[7]),
    }, 1, MAX_ITEM_ID, False)

    echoes = {}
    p = path("echoes.txt")
    last = 0
    for n, f in _rows(p):
        if len(f) < 5:
            _fail(p, n, "expected: id NAME kind departure STATE STATE*...")
        eid = _int(p, n, f[0], 1, MAX_ECHO_ID, "id")
        if eid <= last:
            _fail(p, n, f"id {eid} must come after {last} (registries are append-only)")
        last = eid
        name = _name(p, n, f[1], echoes)
        states = f[4:]
        if len(states) > MAX_ECHO_STATES:
            _fail(p, n, f"at most {MAX_ECHO_STATES} states")
        defaults = [i + 1 for i, s in enumerate(states) if s.endswith("*")]
        if len(defaults) != 1:
            _fail(p, n, "mark exactly one state with * as the canon default")
        clean = [s.rstrip("*") for s in states]
        seen = {}
        for s in clean:
            _name(p, n, s, seen)
            seen[s] = {"line": n}
        echoes[name] = {
            "id": eid, "name": name, "line": n,
            "kind": _one_of(p, n, f[2], ECHO_KINDS, "kind"),
            "departure": f[3],
            "departure_id": _int(p, n, f[3], 0, 65535, "departure"),
            "states": clean,                  # state number = index + 1
            "default": defaults[0],
        }

    def foe_row(p, n, f):
        behavior, _, coward = f[14].partition("+")
        if coward not in ("", "coward"):
            _fail(p, n, f"behavior '{f[14]}': add +coward, or nothing")
        return {
            "health": _int(p, n, f[2], 1, 255, "health"),
            "grace": _int(p, n, f[3], 0, 100, "grace"),
            "armor": _int(p, n, f[4], 0, 100, "armor"),
            "ward": _int(p, n, f[5], 0, 100, "ward"),
            "soak": _int(p, n, f[6], 0, 100, "soak"),
            "speed": _int(p, n, f[7], 0, 12, "speed"),
            "attack": _int(p, n, f[8], 0, 200, "attack"),
            "damage": _int(p, n, f[9], 0, 99, "damage"),
            "type": _one_of(p, n, f[10], DAMAGE, "damage type"),
            "reach": _one_of(p, n, f[11], REACH, "reach"),
            "area": _int(p, n, f[12], 0, 4, "area"),
            "weak": None if f[13] == "-" else _one_of(p, n, f[13], DAMAGE, "weakness"),
            "behavior": _one_of(p, n, behavior, BEHAVIORS, "behavior"),
            "coward": coward == "coward",
            "display": _display(p, n, f[15]),
        }

    foes = _table(path("foes.txt"), 16, foe_row, 1, MAX_FOE_ID, False)

    return {"skills": skills, "races": races, "classes": classes,
            "items": items, "echoes": echoes, "foes": foes}


# Conditions (registry/conditions.txt, docs/turn.md): read on their own, as only the
# rules lab (core/next/) uses them yet.
MAX_CONDITION_ID = 127
CONDITION_FLAGS = ["speed0", "dodge0", "lose_turn", "down", "ends_when_hit", "ends_on_heal",
                   "no_powers", "no_heal", "fly", "first", "tiered"]
CONDITION_NUMBERS = ["speed", "dodge", "armor", "ward", "soak", "rolls", "attacks", "melee",
                     "next", "shake", "heal", "barrier"]


def load_conditions(root=ROOT, races=None):
    """{NAME: condition}, each with its rounds (None: no countdown), shake (its number,
    to which the Resist of whoever put it on is added; or None), opposite, then (names or None), tag, display, and effects: a dict of numbers and
    flags, dot/thorns as (n, type or None), vulnerable/immune_hazard as a type, immune as
    a list of names, race as a race's name."""
    path = os.path.join(root, "conditions.txt")
    if races is None:
        races = load(root)["races"]
    out = {}
    later = []
    last = 0
    for n, f in _rows(path):
        if len(f) < 8:
            _fail(path, n, f"expected at least 8 columns, found {len(f)}")
        cid = _int(path, n, f[0], 1, MAX_CONDITION_ID, "id")
        if cid <= last:
            _fail(path, n, f"id {cid} must come after {last} (registries are append-only)")
        last = cid
        name = _name(path, n, f[1], out)
        rounds = None if f[2] == "-" else _int(path, n, f[2], 1, 9, "rounds")
        shake = None if f[3] == "-" else _int(path, n, f[3], 1, 150, "shake")
        tag = f[6]
        if not (1 <= len(tag) <= 4 and tag.isalpha() and tag.isupper()):
            _fail(path, n, f"tag '{tag}' should be 1 to 4 capital letters")
        c = {"id": cid, "name": name, "line": n, "rounds": rounds, "shake": shake,
             "opposite": None if f[4] == "-" else f[4], "then": None if f[5] == "-" else f[5],
             "tag": tag, "display": _display(path, n, f[7]), "effects": {}}
        for word in f[8:]:
            key, _, val = word.partition("=")
            e = c["effects"]
            if key in CONDITION_FLAGS and not val:
                e[key] = True
            elif key in CONDITION_NUMBERS and val:
                e[key] = _int(path, n, val, -100, 100, key)
            elif key in ("dot", "thorns") and val:
                amount, _, kind = val.partition(":")
                e[key] = (_int(path, n, amount, 1, 50, key),
                          _one_of(path, n, kind, DAMAGE, "damage type") if kind else None)
            elif key in ("vulnerable", "immune_hazard") and val:
                e[key] = _one_of(path, n, val, DAMAGE, "damage type")
            elif key == "immune" and val:
                e[key] = val.split(",")
                later.append((n, val.split(",")))
            elif key == "race" and val:
                if val not in races:
                    _fail(path, n, f"race '{val}' isn't in races.txt")
                e[key] = val
            else:
                _fail(path, n, f"'{word}' isn't an effect (see the list at the top of the file)")
        out[name] = c
    for c in out.values():
        for key in ("opposite", "then"):
            if c[key] is not None and c[key] not in out:
                _fail(path, c["line"], f"{key} '{c[key]}' isn't a condition")
    for n, names in later:
        for x in names:
            if x not in out:
                _fail(path, n, f"immune to '{x}', which isn't a condition")
    return out


# Powers (registry/powers.txt, docs/items.md): read on their own, as only the rules lab
# plays them yet.
MAX_POWER_ID = 127
SHAPES = ["bolt", "burst", "ward", "field", "mend", "hex", "shift"]
TARGETS = ["self", "ally", "foe", "square", "around"]


def load_powers(root=ROOT, classes=None, conditions=None):
    """{NAME: power}: its class (a class's name, or ANY), shape, element (a damage type's
    index, or None), uses (None: at will), target, near (a foe next to you), condition (a
    name, or None) and display."""
    path = os.path.join(root, "powers.txt")
    if classes is None or conditions is None:
        reg = load(root)
        classes = classes or reg["classes"]
        conditions = conditions or load_conditions(root, reg["races"])
    out = {}
    last = 0
    for n, f in _rows(path):
        near = "near" in f
        f = [x for x in f if x != "near"]
        if len(f) != 9:
            _fail(path, n, f"expected 9 columns, found {len(f)}")
        pid = _int(path, n, f[0], 1, MAX_POWER_ID, "id")
        if pid <= last:
            _fail(path, n, f"id {pid} must come after {last} (registries are append-only)")
        last = pid
        name = _name(path, n, f[1], out)
        if f[2] != "ANY" and f[2] not in classes:
            _fail(path, n, f"class '{f[2]}' isn't in classes.txt (or ANY)")
        if f[7] != "-" and f[7] not in conditions:
            _fail(path, n, f"condition '{f[7]}' isn't in conditions.txt")
        out[name] = {"id": pid, "name": name, "line": n, "cls": f[2],
                     "shape": _one_of(path, n, f[3], SHAPES, "shape"),
                     "element": None if f[4] == "-" else _one_of(path, n, f[4], DAMAGE, "element"),
                     "uses": None if f[5] == "-" else _int(path, n, f[5], 1, 9, "uses"),
                     "target": _one_of(path, n, f[6], TARGETS, "target"), "near": near,
                     "cond": None if f[7] == "-" else f[7], "display": _display(path, n, f[8])}
    return out


def by_id(table):
    """{id: entry} for one table of a loaded registry."""
    return {e["id"]: e for e in table.values()}


if __name__ == "__main__":
    reg = load()
    for key, table in reg.items():
        print(f"{key}: {len(table)}")
