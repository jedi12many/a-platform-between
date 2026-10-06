"""Reference implementation of applying a receipt to a character.

Written from docs/boarding.md ("Applying a receipt") and docs/rules-v0.md (levels),
independently of core/src/receipt.c, so the two can check each other. This is what the
Waystation website will run when a receipt or Travel Stamp comes home.

A character is a dict as tools/passport/passport.py decodes it. A receipt is a dict:

    {"departure": 0, "outcome": 0, "xp": 5, "debt_paid": 0, "debt_added": 50000,
     "gained": [item ids], "lost": [item ids],
     "echoes": [(id, state, state at boarding)]}
"""

import copy

PACK_SLOTS = 6
EQUIP_SLOTS = 6
ECHO_SLOTS = 8
LEVEL_MAX = 100
XP_PER_LEVEL = 100
WITS = 3


def gain_xp(ch, amount):
    """docs/rules-v0.md, Levels: 100 XP a level; each gives 1 stat point and
    1 + Wits / 20 skill points (an unspent pool tops out at 255)."""
    levels = 0
    if ch["level"] >= LEVEL_MAX:
        ch["xp"] = 0
        return 0
    total = ch["xp"] + amount
    while total >= XP_PER_LEVEL and ch["level"] < LEVEL_MAX:
        total -= XP_PER_LEVEL
        ch["level"] += 1
        levels += 1
        ch["stat_points"] = min(255, ch["stat_points"] + 1)
        ch["skill_points"] = min(255, ch["skill_points"] + 1 + ch["stats"][WITS] // 20)
    ch["xp"] = 0 if ch["level"] >= LEVEL_MAX else total
    return levels


def _remove(slots, item, count):
    for slot in range(count):
        if slots.get(slot) == item:
            del slots[slot]
            return True
    return False


def apply(character, receipt):
    """Returns (the character after the receipt, a report of what happened)."""
    ch = copy.deepcopy(character)
    report = {"levels": 0, "stored": [], "gone": 0, "shifted": [], "legend": []}

    report["levels"] = gain_xp(ch, receipt["xp"])
    ch["debt"] = max(0, min(65535, ch["debt"] - receipt["debt_paid"] + receipt["debt_added"]))

    # Lost items go first, so they make room for gained ones; the pack is searched
    # before what's equipped. Something already gone (sold, traded) is just counted.
    for item in receipt["lost"]:
        if not (_remove(ch["pack"], item, PACK_SLOTS) or _remove(ch["equipped"], item, EQUIP_SLOTS)):
            report["gone"] += 1
    for item in receipt["gained"]:
        free = [s for s in range(PACK_SLOTS) if s not in ch["pack"]]
        if free:
            ch["pack"][free[0]] = item
        else:
            report["stored"].append(item)      # the lost-and-found keeps it

    # Echoes: the receipt wins. If someone changed the Echo elsewhere since boarding,
    # the player is told the timeline shifted. A full Passport pushes its oldest Echo
    # out to the Legend (docs/echoes.md).
    for eid, state, was in receipt["echoes"]:
        now = dict(ch["echoes"]).get(eid, 0)
        if now not in (was, state):
            report["shifted"].append(eid)
        held = [i for i, (e, _) in enumerate(ch["echoes"]) if e == eid]
        if held:
            ch["echoes"][held[0]] = (eid, state)
            continue
        if len(ch["echoes"]) >= ECHO_SLOTS:
            report["legend"].append(ch["echoes"].pop(0))
        ch["echoes"].append((eid, state))
    return ch, report
