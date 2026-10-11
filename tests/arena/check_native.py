"""The native arena (docs/arena.md, "The native arena"), in headless Chromium through the
studio's server: tools/arena/web/ on the battle engine as WebAssembly (make arena-web).

- Every scenario's intro shows, and its fight starts with the fighters the scenario says,
  and the buttons for each moment are always on screen.
- A fight played on Auto, with fixed dice, ends as the arena's own runner (build/arena, the
  same battle engine natively) says that fight ends: who won, after how many rounds, with
  how much health each.
- The pack: taking up an item from it makes the traveler fight with that item, by the
  rules (its damage, its kind, the skill it rolls); putting the armor away takes its Armor
  off; what was held goes back in the pack; and none of it uses the turn.

    python3 tests/arena/check_native.py        (make test-arena-web)
"""

import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))
import arena  # noqa: E402
import scenarios  # noqa: E402

PORT = 8067
URL = f"http://127.0.0.1:{PORT}/arena/"
SEEDS = [1, 7, 4242]
failures = 0


def fail(msg):
    global failures
    failures += 1
    print(f"FAIL {msg}")


def ok(msg):
    print(f"ok   {msg}")


def page(*args):
    p = subprocess.run(["node", os.path.join(ROOT, "tests", "arena", "native.cjs"), URL, *args],
                       capture_output=True, text=True, timeout=300)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        out = {"failed": (p.stdout + p.stderr).strip()[-400:]}
    if out.get("failed"):
        fail(f"{' '.join(args)}: {out['failed']}")
        return None
    if out.get("errors"):
        fail(f"{' '.join(args)}: the page said {out['errors']}")
    return out


def by_rules(s, seed):
    """One fight of the scenario on the battle engine natively, both sides on quick."""
    m = arena.Matchup()
    item = arena.REG["items"][s["weapon"]]
    arch = arena.registry.ARCHETYPES[item["archetype"]]
    armor = arena.REG["items"][s["armor"]]["tier"] if s["armor"] else 0
    m.travelers.append(arena.Traveler([s["cls"], str(s["level"]), "weapon", arch, str(item["tier"]),
                                       arena.registry.DAMAGE[item["damage"]], "armor", str(armor)]))
    for f in s["foes"]:
        m.add_foe(f)
    m.map = scenarios.ring(s)
    m.fights, m.seed = 1, seed
    results, _ = arena.fight(m)
    return results[0]


def check_start(n, s):
    code = f"A-{n:02d}"
    out = page("start", code)
    if not out:
        return
    if "Start the fight" not in out["intro"]["buttons"]:
        fail(f"{code}: the intro has no Start button")
    st = out["turn"]["st"]
    sides = [f["side"] for f in st["fighters"]]
    if sides != [0] + [1] * len(s["foes"]):
        fail(f"{code}: the fight has sides {sides}, not a traveler and {len(s['foes'])} foes")
        return
    trav = st["fighters"][0]
    weapon = arena.REG["items"][s["weapon"]]
    want_armor = 10 * arena.REG["items"][s["armor"]]["tier"] if s["armor"] else 0
    if trav["item"] != weapon["id"] or trav["weapon"] != 5 * weapon["tier"] or trav["armor"] != want_armor:
        fail(f"{code}: the traveler holds {trav['item']} ({trav['weapon']} damage, Armor {trav['armor']}), "
             f"not the {s['weapon']} and Armor {want_armor}")
    for i, name in enumerate(s["foes"], 1):
        f, want = st["fighters"][i], arena.REG["foes"][name]
        got = (f["health_max"], f["armor"], f["ward"], f["attack"], f["weapon"])
        need = (want["health"], want["armor"], want["ward"], want["attack"], want["damage"])
        if got != need:
            fail(f"{code}: foe {i} is {got}, but registry/foes.txt's {name} is {need}")
    for b in ("Attack", "Guard", "Pack", "Flee", "End turn", "Quick turn", "Leave"):
        if not any(x and x.startswith(b) for x in out["turn"]["buttons"]):
            fail(f"{code}: on your turn there's no {b} button")
    return True


def check_fight(n, s, seed):
    code = f"A-{n:02d}"
    out = page("fight", code, str(seed))
    if not out:
        return False
    want = by_rules(s, seed)
    st = out["end"]["st"]
    result = ["on", "won", "lost", "fled"][st["result"]]
    health = [f["health"] if f["state"] != 1 else 0 for f in st["fighters"]]
    native = [f[0] for f in want["fighters"]]
    if (result, st["round"], health) != (want["result"], want["rounds"], native):
        fail(f"{code}, dice {seed}: the page's fight ended {result} in round {st['round']} with "
             f"health {health}; the battle engine's ended {want['result']} in round "
             f"{want['rounds']} with {native}")
        return False
    if "End turn" in out["end"]["buttons"] or "Fight again" not in out["end"]["buttons"]:
        fail(f"{code}: the end shows {out['end']['buttons']}")
    return True


def check_pack():
    s = scenarios.SCENARIOS[0]
    pack = scenarios.pack(s)
    take = pack[1]                                     # the arc pistol: ranged, energy
    item = next(v for v in arena.REG["items"].values() if v["id"] == take)
    out = page("pack", "A-01", "2")
    if not out:
        return
    ch = scenarios.traveler(s)
    before, taken = out["open"]["st"]["fighters"][0], out["taken"]["st"]["fighters"][0]
    unworn = out["unworn"]["st"]["fighters"][0]
    want = {"item": take, "weapon": 5 * item["tier"], "ranged": 1, "power": 0,
            "type": item["damage"], "attack": arena.rating(ch, "RANGED"), "stat_bonus": 0}
    got = {k: taken[k] for k in want}
    if got != want:
        fail(f"the pack: holding the {item['display']}, the traveler is {got}, not {want}")
    elif out["taken"]["pack"] != [x for x in pack if x != take] + [before["item"]]:
        fail(f"the pack: after the swap it holds {out['taken']['pack']}")
    elif unworn["armor"] != 0 or unworn["armor_item"] != 0:
        fail(f"the pack: with the coat put away, Armor is {unworn['armor']}")
    elif out["closed"]["mode"] != "turn" or out["closed"]["st"]["whose"] != 0 \
            or out["closed"]["round"] != out["open"]["round"]:
        fail("the pack: swapping used the turn")
    else:
        ok(f"the pack: the {item['display']} taken up fights as the rules say (Ranged "
           f"{want['attack']}, {want['weapon']} energy); the coat put away takes its Armor off; "
           "the turn is still yours")


def main():
    if not os.path.exists(os.path.join(ROOT, "build", "arena-web", "rules.js")):
        print("check_native: run make arena-web first")
        return 2
    server = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "artdesk", "serve.py"),
                               "--port", str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(URL + "scenarios.json").read()
                break
            except OSError:
                time.sleep(0.1)
        started = sum(bool(check_start(n, s)) for n, s in enumerate(scenarios.SCENARIOS, 1))
        if started == len(scenarios.SCENARIOS):
            ok(f"all {started} scenarios show their brief and start with the fighters they say, "
               "every button in view")
        played = 0
        for n, s in enumerate(scenarios.SCENARIOS, 1):
            for seed in SEEDS:
                played += check_fight(n, s, seed)
        if played == len(SEEDS) * len(scenarios.SCENARIOS):
            ok(f"{played} fights on Auto end as the battle engine's own arena runner says, "
               "round for round and health for health")
        check_pack()
    finally:
        server.terminate()
        server.wait()
    print(f"native arena: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
