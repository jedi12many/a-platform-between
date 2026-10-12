"""The class power lists in docs/items.md ("Power lists") must say what registry/powers.txt
says: every power there, under its class, with its shape, its element, its charges and the
condition it puts on; and nothing the registry hasn't got (but rows marked "not built yet").

    python3 tools/rules/check_power_docs.py

Run by `make test-rules-next`, so the rules people read can't drift from the ones the
engine plays.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "..", "registry"))
import registry  # noqa: E402


def doc_rows():
    """{display name (lower case): (class, effect, condition)} from the table."""
    text = open(os.path.join(ROOT, "docs", "items.md")).read()
    table = text.split("## Power lists", 1)[1].split("\n## ", 1)[0]
    rows, cls = {}, None
    for line in table.splitlines():
        cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[1] in ("Power", "---") or set(cells[1]) <= set("-"):
            continue
        cls = cells[0] or cls
        if "not built yet" not in cells[2]:
            rows[cells[1].lower()] = (cls.upper(), cells[2], cells[3])
    return rows


def main():
    reg = registry.load()
    conds = registry.load_conditions(races=reg["races"])
    powers = registry.load_powers(classes=reg["classes"], conditions=conds)
    rows = doc_rows()
    bad = []
    for p in powers.values():
        row = rows.pop(p["display"].lower(), None)
        if row is None:
            bad.append(f"{p['display']} ({p['name']}) isn't in docs/items.md's power lists")
            continue
        cls, effect, cond = row
        shape = registry.SHAPES[p["shape"]].capitalize()
        el = registry.DAMAGE[p["element"]] if p["element"] is not None else None
        uses = "at will" if p["uses"] is None else f"{p['uses']} charge"
        want_cond = conds[p["cond"]]["display"].lower() if p["cond"] else ""
        if cls != p["cls"]:
            bad.append(f"{p['display']}: listed under {cls}, the registry says {p['cls']}")
        if not effect.startswith(shape):
            bad.append(f"{p['display']}: the effect should start with its shape, {shape}")
        if el and f"+ {el}" not in effect:
            bad.append(f"{p['display']}: the effect should say its element (+ {el})")
        if not el and re.search(r"\+ (fire|cold|kinetic|energy|mind)", effect):
            bad.append(f"{p['display']}: the effect names an element it hasn't got")
        if uses not in effect:
            bad.append(f"{p['display']}: the effect should say '{uses}'")
        if not cond.lower().startswith(want_cond) or (not want_cond and cond):
            bad.append(f"{p['display']}: its condition is '{want_cond or 'none'}', the doc says '{cond}'")
    for name in rows:
        bad.append(f"docs/items.md lists '{name}', which registry/powers.txt hasn't got")
    for b in bad:
        print("FAIL: " + b)
    print(f"power docs: {len(powers)} powers, {len(bad)} wrong")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
