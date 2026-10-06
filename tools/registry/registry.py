"""Load and check the registry: races, classes, skills, items and Echoes.

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

# Limits set by the Passport format (docs/passport-spec.md).
MAX_RACES = 32
MAX_CLASSES = 16
MAX_SKILLS = 12
MAX_ITEM_ID = 1023
MAX_ECHO_ID = 1023
MAX_ECHO_STATES = 3


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
            "states": clean,                  # state number = index + 1
            "default": defaults[0],
        }

    return {"skills": skills, "races": races, "classes": classes,
            "items": items, "echoes": echoes}


def by_id(table):
    """{id: entry} for one table of a loaded registry."""
    return {e["id"]: e for e in table.values()}


if __name__ == "__main__":
    reg = load()
    for key, table in reg.items():
        print(f"{key}: {len(table)}")
