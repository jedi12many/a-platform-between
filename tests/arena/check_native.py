"""The native arena (docs/arena.md, "The native arena"), in headless Chromium through the
studio's server: tools/arena/web/ on the rules lab's battle engine (rules v1, docs/turn.md)
as WebAssembly (make arena-web).

- Every scenario's intro shows, and its fight starts with the fighters the scenario says,
  and the buttons for each moment are always on screen.
- A fight played on Auto, with fixed dice, ends as the arena's own runner (build/arena-next,
  the same battle engine natively) says that fight ends: who won, after how many rounds,
  with how much health each. The rules lab's scenarios (R-01...) too: hazards, foes'
  conditions, races.
- Dash and Shove, by keys: a Dash goes where it was pointed; a Shove next to a pit drops
  the foe in it, by the roll the engine made.
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
sys.path.insert(0, os.path.join(ROOT, "tools", "rules"))
import turn  # noqa: E402

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


ALL = [(f"A-{n:02d}", s) for n, s in enumerate(scenarios.SCENARIOS, 1)] + \
      [(f"R-{n:02d}", s) for n, s in enumerate(scenarios.LAB, 1)]


def by_rules(s, seed):
    """One fight of the scenario on the rules lab's engine natively, both sides on quick."""
    m = scenarios.matchup(s, "next")
    m.fights, m.seed = 1, seed
    results, _ = arena.fight(m)
    return results[0]


def check_start(code, s):
    out = page("start", code)
    if not out:
        return
    if "Start the fight" not in out["intro"]["buttons"]:
        fail(f"{code}: the intro has no Start button")
    want_list = scenarios.PLAYING + ([] if code in scenarios.PLAYING else [code])
    if out["intro"]["listed"] != want_list:
        fail(f"{code}: the intro lists {out['intro']['listed']}, not the scenarios to play now "
             f"{scenarios.PLAYING} (and the one linked)")
    st = out["turn"]["st"]
    sides = [f["side"] for f in st["fighters"]]
    team = 1 + len(s.get("allies", []))
    if sides != [0] * team + [1] * len(s["foes"]):
        fail(f"{code}: the fight has sides {sides}, not {team} traveler(s) and {len(s['foes'])} foes")
        return
    trav = st["fighters"][0]
    weapon = arena.REG["items"][s["weapon"]]
    # Rules v1's gear (docs/turn.md, Levels and gear).
    want_armor = turn.gear_armor(arena.REG["items"][s["armor"]]["tier"]) if s["armor"] else 0
    if trav["item"] != weapon["id"] or trav["weapon"] != turn.gear_damage(weapon["tier"]) or trav["armor"] != want_armor:
        fail(f"{code}: the traveler holds {trav['item']} ({trav['weapon']} damage, Armor {trav['armor']}), "
             f"not the {s['weapon']} and Armor {want_armor}")
    for i, name in enumerate(s["foes"], team):
        f, want = st["fighters"][i], arena.REG["foes"][scenarios.foe_name(name)]
        got = (f["health_max"], f["armor"], f["ward"], f["attack"], f["weapon"], f["level"])
        need = (want["health"], want["armor"], want["ward"], want["attack"], want["damage"],
                scenarios.foe_level(name))
        if got != need:
            fail(f"{code}: foe {i} is {got}, but registry/foes.txt's {name} is {need}")
    for b in ("Attack", "Shove", "Dash", "Guard", "Pack", "Flee", "End turn", "Quick turn", "Leave"):
        if not any(x and x.startswith(b) for x in out["turn"]["buttons"]):
            fail(f"{code}: on your turn there's no {b} button")
    return True


def check_fight(code, s, seed):
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
    want = {"item": take, "weapon": turn.gear_damage(item["tier"]), "ranged": 1, "power": 0,
            "type": item["damage"], "attack": arena.rating(ch, "RANGED") + turn.level_bonus(ch["level"]),
            "stat_bonus": 0}
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


def check_dash():
    """R-06: a Dash five squares east of the start, on the first turn."""
    out = page("dash", "R-06", "3", "5")
    if not out:
        return
    start = out["turn"]["st"]["fighters"][0]
    end = out["after"]["st"]["fighters"][0]
    if (end["x"], end["y"]) != (start["x"] + 5, start["y"]) or out["planned"] != {"x": start["x"] + 5, "y": start["y"]}:
        fail(f"a Dash 5 east from {start['x']},{start['y']} ended at {end['x']},{end['y']}")
    elif not any("dashes" in line for line in out["after"]["log"]):
        fail("a Dash isn't in the log")
    else:
        ok("Dash: pointed five squares east by keys, the traveler ends there, in the log")


def check_shove():
    """R-02: the Warden steps next to the rust-guard by the pit, and shoves it."""
    out = page("shove", "R-02", "9", "RRRRR")
    if not out:
        return
    a = out["after"]["st"]["fighters"][1]
    said = [line for line in out["after"]["log"] if "shoves" in line]
    if not said:
        fail("the Shove isn't in the log")
    elif "fail" in said[0]:
        fail(f"the Shove failed with these dice ({said[0]}); pick dice where it lands")
    elif a["state"] != 1 or not any("falls into the pit" in line for line in out["after"]["log"]):
        fail(f"shoved toward the pit, the rust-guard is at {a['x']},{a['y']}, state {a['state']}")
    else:
        ok(f"Shove: next to a pit, the rust-guard goes in ({said[0].split(': ')[1]})")


def check_blink():
    """R-10: the Rogue blinks (key 1) as her move, and still shoots from where she lands."""
    out = page("blink", "R-10", "4")
    if not out:
        return
    start = out["turn"]["st"]["fighters"][0]
    end = out["after"]["st"]["fighters"][0]
    blink = [p for p in end["powers"] if scenarios.arena.POWERS["BLINK"]["id"] == p[0]]
    used = [line for line in out["after"]["log"] if "uses Blink" in line]
    shots = [line for line in out["after"]["log"] if " → " in line and "Blink" not in line]
    if out["chose"] != "cast" or out["blink"] != 1 or not out["targets"]:
        fail(f"Blink from key 1: the page went to {out['chose']}, blink {out['blink']}, "
             f"targets {out['targets']}")
    elif (end["x"], end["y"]) != (out["plan"]["x"], out["plan"]["y"]) or (end["x"], end["y"]) == (start["x"], start["y"]):
        fail(f"blinked to {out['plan']}, the Rogue is at {end['x']},{end['y']}")
    elif not used or not shots or not blink or blink[0][2] != 1:
        fail(f"Blink then a shot: the log says {used + shots[:2]}, Blink's charges {blink}")
    else:
        ok(f"Blink is the move: key 1 takes the Rogue to {end['x']},{end['y']}, a charge spent, "
           "and she still shoots from there")


def check_powers():
    """R-07: the Channeler's Fireball (2), on the square the page offers first; R-08: the
    Medic stims the Warden (2: one ally next to her)."""
    out = page("power", "R-07", "12", "2")
    if out:
        f = out["after"]["st"]["fighters"][0]
        fireball = [p for p in f["powers"] if scenarios.arena.POWERS["FIREBALL"]["id"] == p[0]]
        said = [line for line in out["after"]["log"] if "uses Fireball" in line]
        hits = [line for line in out["after"]["log"] if line.startswith("Fireball →")]
        if out["chose"] != "cast" or not said or not hits or not fireball or fireball[0][2] != 0:
            fail(f"a Fireball from key 2: the page went to {out['chose']}, the log says {said + hits}, "
                 f"its charges {fireball}")
        else:
            ok(f"powers: key 2 picks a square for the Fireball, it blasts ({len(hits)} rolls) and "
               "its one charge is spent")
    out = page("power", "R-08", "5", "2")
    if out:
        st = out["after"]["st"]
        medic = st["fighters"][1]
        warden = st["fighters"][0]
        stim = scenarios.arena.CONDS["STIMMED"]["id"]
        if not any(c[0] == stim for c in warden["conds"]):
            fail(f"the Medic's Stim on the Warden: his conditions are {warden['conds']}")
        else:
            ok("powers on an ally: the Medic's Stim (key 2) lands on the Warden next to her")
    return


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
        started = sum(bool(check_start(code, s)) for code, s in ALL)
        if started == len(ALL):
            ok(f"all {started} scenarios show their brief and start with the fighters they say, "
               f"every button in view; the list is the {len(scenarios.PLAYING)} to play now "
               f"({', '.join(scenarios.PLAYING)}), and one opened by its link")
        played = 0
        for code, s in ALL:
            for seed in SEEDS:
                played += check_fight(code, s, seed)
        if played == len(SEEDS) * len(ALL):
            ok(f"{played} fights on Auto end as the rules lab's own arena runner says, "
               "round for round and health for health")
        check_pack()
        check_dash()
        check_shove()
        check_powers()
        check_blink()
    finally:
        server.terminate()
        server.wait()
    print(f"native arena: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
