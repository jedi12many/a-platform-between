"""registry/conditions.txt and registry/powers.txt as C, for the rules lab's engine
(core/next/, docs/turn.md): apb_conds[] and apb_powers[], indexed by id, and the races'
traits.

    python3 tools/rules/conditions_c.py OUT.c

It's built, not kept: the registry is the one place the conditions are written down.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "registry"))
import registry  # noqa: E402

FLAGS = {"speed0": "APB_CF_SPEED0", "dodge0": "APB_CF_DODGE0", "lose_turn": "APB_CF_LOSE_TURN",
         "down": "APB_CF_DOWN", "ends_when_hit": "APB_CF_ENDS_HIT", "ends_on_heal": "APB_CF_ENDS_HEAL",
         "no_powers": "APB_CF_NO_POWERS", "no_heal": "APB_CF_NO_HEAL", "fly": "APB_CF_FLY",
         "first": "APB_CF_FIRST", "tiered": "APB_CF_TIERED", "must_attack": "APB_CF_MUST_ATTACK",
         "hidden": "APB_CF_HIDDEN", "at_random": "APB_CF_AT_RANDOM", "phased": "APB_CF_PHASED"}
NUMBERS = ["speed", "dodge", "armor", "ward", "soak", "rolls", "attacks", "melee", "next", "shake"]


def row(c, conds, races):
    e = c["effects"]
    flags = " | ".join(["APB_CF_DEFINED"] + [v for k, v in FLAGS.items() if e.get(k)])
    ids = lambda name: conds[name]["id"] if name else 0
    typ = lambda t: "APB_NO_TYPE" if t is None else str(t)
    dot, dot_type = e.get("dot", (0, None))
    thorns, thorns_type = e.get("thorns", (0, None))
    immune = [conds[n]["id"] for n in e.get("immune", [])] + [0] * 4
    if len(e.get("immune", [])) > 4:
        raise SystemExit(f"conditions.txt: {c['name']} is immune to more than 4")
    race = races[e["race"]]["id"] if "race" in e else 0xFF
    fields = [flags, str(c["rounds"] or 0), str(c["shake"] or 0),
              str(ids(c["opposite"])), str(ids(c["then"]))]
    fields += [str(e.get(k, 0)) for k in NUMBERS]
    fields += [str(e.get("heal", 0)), str(e.get("barrier", 0)), str(dot), typ(dot_type),
               str(thorns), typ(thorns_type), typ(e.get("vulnerable")), typ(e.get("immune_hazard")),
               "{ " + ", ".join(map(str, immune[:4])) + " }", str(race), '"' + c["tag"] + '"',
               '"' + c["name"] + '"']
    return "    /* %3d %-14s */ { %s }," % (c["id"], c["name"], ", ".join(fields))


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    reg = registry.load()
    conds = registry.load_conditions(races=reg["races"])
    by_id = {c["id"]: c for c in conds.values()}
    lines = ["/* Generated from registry/conditions.txt by tools/rules/conditions_c.py: don't edit. */",
             '#include "apb_battle.h"', "", "const apb_cond_def apb_conds[] = {"]
    for i in range(max(by_id) + 1):
        lines.append(row(by_id[i], conds, reg["races"]) if i in by_id else "    { 0 },")
    lines += ["};", f"const uint8_t apb_cond_count = {max(by_id) + 1};"]
    traits = {}
    for c in sorted(conds.values(), key=lambda c: c["id"]):
        if "race" in c["effects"]:
            traits.setdefault(reg["races"][c["effects"]["race"]]["id"], []).append(c["id"])
    n = max(r["id"] for r in reg["races"].values()) + 1
    lines += ["", f"static const uint8_t traits[{n}][2] = {{"]
    for r in range(n):
        t = (traits.get(r, []) + [0, 0])[:2]
        lines.append(f"    {{ {t[0]}, {t[1]} }},")
    lines += ["};", "",
              "uint8_t apb_race_trait(uint8_t race, uint8_t which)",
              "{",
              f"    return (uint8_t)(race < {n} && which < 2 ? traits[race][which] : 0);",
              "}", ""]
    powers = registry.load_powers(classes=reg["classes"], conditions=conds)
    by_pid = {p["id"]: p for p in powers.values()}
    lines += ["", "const apb_power_def apb_powers[] = {"]
    for i in range(max(by_pid) + 1):
        p = by_pid.get(i)
        if not p:
            lines.append("    { 0 },")
            continue
        cls = reg["classes"][p["cls"]]["id"] if p["cls"] != "ANY" else 0xFF
        lines.append("    /* %3d %-12s */ { 1, %d, %d, %s, %d, %d, %d, %d, \"%s\" }," % (
            i, p["name"], cls, p["shape"], "APB_NO_TYPE" if p["element"] is None else p["element"],
            p["uses"] or 0, p["target"], int(p["near"]), conds[p["cond"]]["id"] if p["cond"] else 0,
            p["name"]))
    lines += ["};", f"const uint8_t apb_power_count = {max(by_pid) + 1};", ""]
    os.makedirs(os.path.dirname(os.path.abspath(argv[1])), exist_ok=True)
    with open(argv[1], "w") as f:
        f.write("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
