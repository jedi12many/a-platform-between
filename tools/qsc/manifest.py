"""Reward manifests: the most a Departure can ever give (docs/boarding.md).

Every `~ xp`, `~ give` and `~ debt` command pays at most once per trip (the VM keeps
track), so the most a Departure can award is simply what all of them add up to. The
Waystation refuses a receipt that claims more.

    {"departure": 0, "title": "The Fare", "kind": "official", "levels": [1, 1],
     "xp": 5,                                   # before fading for the level band
     "items": [{"id": 9, "name": "TICKET_STUB", "most": 1}],
     "echoes": [{"id": 4, "name": "WOLF_PUP", "states": [1, 3]}],
     "debt": {"set": [50000], "add": 0, "pay": 0}}
"""

import qs_ast as A

REWARD_SITES = 32          # vm/apb_vm.h, APB_VM_REWARD_SITES
REWARDS = ("xp", "give", "debt")


def commands(dep):
    """Every command in the Departure, wherever it sits."""
    def walk(stmts):
        for st in stmts:
            if isinstance(st, A.Command):
                yield st
            elif isinstance(st, A.If):
                for _, body in st.branches:
                    yield from walk(body)
            elif isinstance(st, (A.Check, A.Fight)):
                for body in st.outcomes.values():
                    yield from walk(body)

    for scene in dep.scenes():
        yield from walk(scene.body)
        for choice in scene.choices:
            yield from walk(choice.body)


class ManifestError(Exception):
    def __init__(self, line, msg):
        super().__init__(msg)
        self.line = line


def manifest(dep, reg):
    cmds = list(commands(dep))
    rewards = [c for c in cmds if c.name in REWARDS]
    if len(rewards) > REWARD_SITES:
        raise ManifestError(rewards[REWARD_SITES].line,
                            f"this Departure has {len(rewards)} '~ xp', '~ give' and '~ debt' "
                            f"commands; the most is {REWARD_SITES}. Award XP in fewer, larger "
                            f"steps, or split the Departure.")
    items, echoes = {}, {}
    debt = {"set": [], "add": 0, "pay": 0}
    xp = 0
    for c in rewards:
        if c.name == "xp":
            xp += c.args[0]
        elif c.name == "give":
            e = reg["items"][c.args[0]]
            items.setdefault(c.args[0], {"id": e["id"], "name": c.args[0], "most": 0})["most"] += 1
        elif c.name == "debt":
            mode, n = c.args
            if mode == "set":
                debt["set"].append(n)
            else:
                debt["add" if mode == "add" else "pay"] += n
    for c in cmds:
        if c.name == "echo":
            name, state = c.args
            e = reg["echoes"][name]
            entry = echoes.setdefault(name, {"id": e["id"], "name": name, "states": []})
            n = e["states"].index(state) + 1
            if n not in entry["states"]:
                entry["states"].append(n)
    debt["set"] = sorted(set(debt["set"]))
    for e in echoes.values():
        e["states"].sort()
    return {"departure": dep.id, "title": dep.title, "kind": dep.kind,
            "levels": [dep.level_min, dep.level_max], "xp": xp,
            "items": sorted(items.values(), key=lambda i: i["id"]),
            "echoes": sorted(echoes.values(), key=lambda e: e["id"]),
            "debt": debt}


def fits(m, receipt, boarded_debt):
    """Why a receipt claims more than the manifest allows, or None if it fits.

    receipt: the fields of docs/boarding.md, as tools/passport/receipt.py takes them.
    """
    if receipt["departure"] != m["departure"]:
        return f"it's for Departure {receipt['departure']}, not {m['departure']}"
    if receipt["xp"] > m["xp"]:
        return f"{receipt['xp']} XP, but the Departure gives at most {m['xp']}"
    most = {i["id"]: i["most"] for i in m["items"]}
    for item in set(receipt["gained"]):
        if receipt["gained"].count(item) > most.get(item, 0):
            return f"item {item} gained {receipt['gained'].count(item)} times, at most {most.get(item, 0)}"
    states = {e["id"]: e["states"] for e in m["echoes"]}
    for eid, state, _ in receipt["echoes"]:
        if state not in states.get(eid, []):
            return f"Echo {eid} set to state {state}, which the Departure never sets"
    # Debt: the lowest and highest it could end at, whatever order the commands ran in.
    d = m["debt"]
    high = min(65535, max([boarded_debt] + d["set"]) + d["add"])
    low = max(0, min([boarded_debt] + d["set"]) - d["pay"])
    final = boarded_debt - receipt["debt_paid"] + receipt["debt_added"]
    if not low <= final <= high:
        return f"Debt ends at {final}, outside {low}..{high}"
    return None
