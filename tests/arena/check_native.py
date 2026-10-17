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
    want_list = ["E14"] + scenarios.PLAYING + ([] if code in scenarios.PLAYING else [code])
    if out["intro"]["listed"] != want_list:
        fail(f"{code}: the intro lists {out['intro']['listed']}, not the scenarios to play now "
             f"{scenarios.PLAYING} (and the one linked), after exploring")
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
            "type": item["damage"], "attack": arena.rating(ch, "RANGED"),
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


def check_first():
    """R-05: the first traveler attacks from where they stand, and the turn goes on: a step, then
    Enter ends it (docs/turn.md, Actions: either order)."""
    out = page("first", "R-05", "4")
    if not out:
        return
    me = out["me"]
    start = out["turn"]["st"]["fighters"][me]
    mid = out["acted"]["st"]["fighters"][me]
    end = out["after"]["st"]["fighters"][me]
    shots = [line for line in out["acted"]["log"] if " → " in line]
    labels = [b for b in out["acted"]["buttons"] if b]
    if not out["targets"]:
        fail("the first traveler has nobody to attack from where they start in R-05")
    elif out["acted"]["mode"] != "turn" or not out["flag"] or not shots:
        fail(f"attacking first: the page went to {out['acted']['mode']}, acted {out['flag']}, log {shots[:2]}")
    elif (mid["x"], mid["y"]) != (start["x"], start["y"]) or any(l.startswith("Attack") for l in labels):
        fail(f"after attacking first they are at {mid['x']},{mid['y']} (was {start['x']},{start['y']}), "
             f"buttons {labels}")
    elif (end["x"], end["y"]) != (out["plan"]["x"], out["plan"]["y"]) or (end["x"], end["y"]) == (start["x"], start["y"]):
        fail(f"then a step to {out['plan']}: they are at {end['x']},{end['y']}")
    else:
        ok(f"either order: the traveler attacks from {start['x']},{start['y']}, the turn goes on (no "
           f"second action), and they step to {end['x']},{end['y']}")


def check_rules():
    """R-07: hovering each of the Channeler's powers (keys 1-4, and on her card) shows its
    rule at its tier and roll, as docs/turn.md says; moving away hides it."""
    out = page("rules", "R-07")
    if not out:
        return
    cards, pw = out["cards"], out["powers"]
    by_id = {p["id"]: p for p in scenarios.arena.POWERS.values()}
    want = {"FIREBOLT": ["Damage {d}", "Fire: a hit burns", "At will"],
            "FIREBALL": ["3×3", "Damage {d}", "on fire", "1 of 1 charge left"],
            "ICE_WALL": ["A line of {n} squares", "ice (rough ground"],
            "SHIELD": ["On yourself: no roll", "warded"]}
    bad = []
    for k, p in enumerate(pw):
        name = by_id[p[0]]["name"]
        text = cards[k] or ""
        tier, rating = p[3], p[4]
        if not text.startswith(f"{by_id[p[0]]['display']} · tier {tier}"):
            bad.append(f"key {k + 1}: the card starts '{text[:40]}'")
        if name in ("FIREBOLT", "FIREBALL") and f"rolls {rating}" not in text:
            bad.append(f"{name}: the card doesn't say it rolls {rating}")
        for w in want.get(name, []):
            if w.format(d=5 * tier, n=tier + 2) not in text:
                bad.append(f"{name}: the card doesn't say '{w.format(d=5 * tier, n=tier + 2)}'")
    if out["gone"]:
        bad.append("the card stays up after the mouse leaves")
    if not out["chip"] or not out["chip"].startswith(by_id[pw[0][0]]["display"]):
        bad.append(f"the card's first power shows {out['chip']!r} on hover")
    if bad:
        fail("power rules on hover: " + "; ".join(bad))
    else:
        ok("power rules on hover: each of the Channeler's four powers (button and card) shows its "
           "rule at its tier and roll, and goes when the mouse does")


def check_explore():
    """Exploring (docs/open-floors.md): yard 48213's first open floor, a party of four. The
    floor is the reference's (tools/rooms/rooms.py's build_open), you start where it says;
    the view is the C64's, 19 x 12 squares at its scale, on the floor and on C64 pixels,
    you inside it; holding a key walks smoothly with no grid, and the others follow the
    leader's trail in marching order, a gap apart."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "rooms"))
    import rooms
    out = page("explore", "48213:warden,rogue,channeler,medic")
    if not out:
        return
    o = rooms.build_open(48213, 1)
    start, held, mid, rest = out["start"], out["held"], out["mid"], out["rest"]
    bad = []
    if start["map"] != o["rows"] or [start["x"], start["y"]] != o["start"]:
        bad.append("the floor or the start isn't the reference's")
    if start["view"] != [19, 12] or not start["c64"]:
        bad.append(f"the view is {start['view']}, the C64's scale {start['c64']}: not the C64's 19 x 12")
    if start["grid"] != 0 or held["grid"] != 0:
        bad.append(f"the grid shows while exploring ({start['grid']}, {held['grid']})")
    if not (start["px"] + 0.3 < held["px"] < start["px"] + 2.2) or held["px"] == round(held["px"]):
        bad.append(f"holding right a third of a second took you from {start['px']} to {held['px']}, "
                   f"not smoothly about 1.5 squares (4.5 a second)")
    for v in (start, held, mid, rest):
        c, (w, h) = v["cam"], v["view"]
        if not (0 <= c["x"] <= o["w"] - w and 0 <= c["y"] <= o["h"] - h):
            bad.append(f"the view at {c} runs off the floor")
        elif any(abs(t * 16 - round(t * 16)) > 1e-9 for t in c.values()):
            bad.append(f"the view stands between C64 pixels: {c}")
        elif not (c["x"] <= v["px"] + 0.5 <= c["x"] + w and c["y"] <= v["py"] + 0.5 <= c["y"] + h):
            bad.append(f"you're out of the view at {c}")
    if mid["party"] != ["WARDEN", "ROGUE", "CHANNELER", "MEDIC"]:
        bad.append(f"the party is {mid['party']}")
    lead = mid["shown"][0]
    for k, (x, y, alpha) in enumerate(mid["shown"][1:], 1):
        d = ((x - lead[0]) ** 2 + (y - lead[1]) ** 2) ** 0.5
        if alpha < 1 or not (0.3 < d <= k * 0.85 + 0.01):
            bad.append(f"walking, number {k + 1} is {d:.2f} from the leader (seen {alpha}), not on the trail {k} gaps back")
    if any(b and ("View:" in b) for b in start["buttons"]):
        bad.append("there's still a choice of view")
    if out["errors"]:
        bad.append(f"the page threw {out['errors'][:2]}")
    if bad:
        fail("explore: " + "; ".join(bad))
    else:
        ok(f"explore: yard 48213's first open floor as the reference builds it, seen 19 x 12 at the "
           f"C64's scale, on C64 pixels; walked smoothly with no grid (a key held a third of a second: "
           f"{held['px'] - start['px']:.2f} squares), the party following the leader's trail")


def check_zoom():
    """Exploring, zoomed out (docs/open-floors.md): Z steps the view from the C64's 19 x 12
    to the whole floor and back; the view kept on the floor and on C64 pixels, about you."""
    out = page("zoom", "48213:warden")
    if not out:
        return
    bad = []
    fw, fh = out["floor"]
    sizes = [v["view"] for v in out["views"]]
    if sizes != [[19, 12], [fw, fh], [19, 12], [fw, fh]]:
        bad.append(f"Z gave the views {sizes}")
    for v in out["views"]:
        w, h = v["view"]
        c = v["cam"]
        if not (0 <= c["x"] <= fw - w and 0 <= c["y"] <= fh - h):
            bad.append(f"the {w} x {h} view at {c} runs off the floor")
        elif any(abs(t * 16 - round(t * 16)) > 1e-9 for t in c.values()):
            bad.append(f"the {w} x {h} view stands between C64 pixels: {c}")
        elif not (c["x"] <= v["px"] + 0.5 <= c["x"] + w and c["y"] <= v["py"] + 0.5 <= c["y"] + h):
            bad.append(f"you're out of the {w} x {h} view")
        if v["button"] != f"Zoom: {w} x {h} squares":
            bad.append(f"the zoom button says {v['button']!r} at {w} x {h}")
    if bad:
        fail("explore, zoomed out: " + "; ".join(bad))
    else:
        ok(f"explore, zoomed out: Z steps the view from the C64's 19 x 12 to the whole {fw} x {fh} floor "
           "and back, kept on the floor and on C64 pixels")


def check_minimap():
    """Exploring: the side panel's minimap (docs/open-floors.md): the floor at 4 pixels a
    square; black but where the party's been within its sight (at the start, exactly the
    squares that near), more seen after a walk and nothing seen lost; the view's rectangle
    drawn where the view is."""
    out = page("minimap", "48213:warden")
    if not out:
        return
    bad = []
    s_, w = out["start"], out["walked"]
    fw, fh, r = s_["w"], s_["h"], s_["sight"]
    if s_["size"] != [fw * 4, fh * 4]:
        bad.append(f"the minimap is {s_['size']}, not {fw * 4} x {fh * 4}")
    want = [1 if (x - s_["x"]) ** 2 + (y - s_["y"]) ** 2 <= r * r else 0 for y in range(fh) for x in range(fw)]
    if s_["fog"] != want:
        bad.append(f"at the start {sum(s_['fog'] or [])} squares are seen, not the {sum(want)} within {r} of the party")
    elif not w["fog"] or sum(w["fog"]) <= sum(s_["fog"]) or any(a and not b for a, b in zip(s_["fog"], w["fog"])):
        bad.append("walking didn't clear more of the fog (or covered some again)")
    for v in (s_, w):
        if v["corner"] != [255, 255, 255]:
            bad.append(f"no rectangle at the view's corner {v['cam']}: {v['corner']}")
            break
    if bad:
        fail("explore, the minimap: " + "; ".join(bad))
    else:
        ok(f"explore, the minimap: fog cleared within the party's sight ({r} squares: {sum(s_['fog'])} at "
           f"the start, {sum(w['fog'])} after a walk), the view's rectangle where the view is")


def check_talk():
    """Talk while exploring (docs/rooms.md, Talk): the story VM playing
    content/sidings/yards-talk/. Yard 326: clicking Vell walks you up to her and opens her
    words and choices as the script has them, a question gets its answer, Move on ends it
    and you walk again, next to her. Its band 2, ash rats who talk first when they see you:
    the parley's check is rolled and shown, and its end is the story's: a failure starts
    the fight, a success clears the band."""
    out = page("talk", "-")
    if not out:
        return
    bad = []
    if not out["before"]["waiting"]:
        bad.append("the story isn't waiting when you arrive")
    if max(abs(a - b) for a, b in zip(out["near"], out["vellAt"])) > 1:
        bad.append(f"talking to Vell, you're at {out['near']}, not next to her at {out['vellAt']}")
    vell = out["vell"]
    if (vell["mode"], vell["who"]) != ("talk", "Vell") or not vell["lines"] or not vell["lines"][0].startswith("A camp"):
        bad.append(f"clicking Vell: {vell['mode']}, {vell['who']!r}, {vell['lines'][:1]}")
    if vell["choices"] != ["What have you got?", "What's on this floor?", "Seen anyone else down here?", "Move on"]:
        bad.append(f"Vell's choices are {vell['choices']}")
    if not any(line.startswith('"Rats on the first floors') for line in out["rumour"]["lines"]):
        bad.append("asking what's on the floor didn't get the rumour")
    after = out["after"]
    if after["mode"] != "explore" or after["open"] or not after["waiting"]:
        bad.append(f"after Move on: {after['mode']}, the panel {'open' if after['open'] else 'shut'}")
    parley = out["parley"]
    if parley["mode"] != "talk" or not parley["who"].startswith("Ash rat") or "Shout them down" not in parley["choices"]:
        bad.append(f"the ash rats' parley: {parley['mode']}, {parley['who']!r}, {parley['choices']}")
    rolls = [line for line in out["shout"]["lines"] if line.startswith("Presence check: rolled")]
    then = out["then"]
    if len(rolls) != 1:
        bad.append(f"shouting, the check shown is {rolls}")
    else:
        failed = rolls[0].endswith(": fail.")
        if failed and then["mode"] != "turn":
            bad.append(f"the shout failed, and then the page is in {then['mode']}, not the fight")
        if not failed and (then["mode"] != "explore" or not then["cleared"][1]):
            bad.append(f"the shout worked, and then the page is in {then['mode']}, cleared {then['cleared']}")
    if out["errors"]:
        bad.append(f"the page threw {out['errors'][:2]}")
    if bad:
        fail("talk: " + "; ".join(bad))
    else:
        ok(f"talk: walked up to Vell, her words and choices as the script has them, a question "
           f"answered and back to walking; the ash rats talk first, the shout rolled ({rolls[0]}) and "
           f"the story's ending kept ({then['mode']})")


def check_looks():
    """The looks while exploring (docs/rooms.md, Looks; docs/art.md): yard 48213's first
    open floor in each look (and by floor: floor 1 is the forest). Every square is drawn with a
    tile of that look's file: its terrain's, or a variant of that terrain, or, on open
    ground with no foe, stairs or crate on it, scenery; some squares get a variant or
    scenery; and the same every time it's drawn."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import art
    out = page("looks", "48213")
    if not out:
        return
    bad = []
    for name, got in out["looks"].items():
        look = "forest" if name == "by floor" else name
        if got["look"] != look:
            bad.append(f"{name}: the board's look is {got['look']}")
            continue
        names = [e.name for e in art.load(art.tiles_file(32, look)).entries]
        r, dressed = got["room"], 0
        taken = {(f["x"], f["y"]) for f in r["foes"]}
        if r["stairs"]:
            taken.add(tuple(r["stairs"]))
        if r["cache"]:
            taken.add((r["cache"]["x"], r["cache"]["y"]))
        for y, row in enumerate(got["tiles"]):
            for x, tile in enumerate(row):
                terrain = art.TERRAIN[int(r["rows"][y][x])]
                if tile not in names:
                    bad.append(f"{look}: {x},{y} is drawn as {tile}, not a tile of the look")
                elif tile != terrain and art.variant_of(tile) != terrain and not (
                        art.variant_of(tile) is None and tile not in art.TERRAIN
                        and terrain == "open" and (x, y) not in taken):
                    bad.append(f"{look}: {x},{y} ({terrain}) is drawn as {tile}")
                dressed += tile != terrain
        if not dressed:
            bad.append(f"{look}: no square has a variant or scenery")
        if got["again"] != got["tiles"]:
            bad.append(f"{look}: drawn twice, the tiles differ")
    if sorted(out["looks"]) != sorted(art.LOOKS + ["by floor"]):
        bad.append(f"the page has the looks {sorted(out['looks'])}, not art.py's {art.LOOKS}")
    if out["errors"]:
        bad.append(f"the page threw {out['errors'][:2]}")
    if bad:
        fail("looks: " + "; ".join(bad[:6]))
    else:
        ok(f"looks: exploring in each look ({', '.join(art.LOOKS)}; and by floor, the forest "
           "first) draws each square with its look's tile for the terrain, a variant of it, or "
           "scenery on open ground, the same every time")


def check_scale():
    """The board is drawn at whole screen pixels to an art pixel (arena.js, resize), so every
    dot is the same size, unless that would shrink it by more than a quarter; and it's
    placed on whole pixels."""
    out = page("scale", "-")
    if not out:
        return
    bad = []
    for s in out["scales"]:
        fit, scale = s["fit"], s["scale"]
        want = int(fit) if int(fit) >= 0.75 * fit else fit
        if abs(scale - want) > 1e-9 or s["ox"] != int(s["ox"]) or s["oy"] != int(s["oy"]):
            bad.append(f"fitting {fit:.3f}, the board is at {scale} from {s['ox']},{s['oy']} (want {want})")
    if bad:
        fail("the board's scale: " + "; ".join(bad))
    else:
        ok("the board's scale: whole pixels to an art pixel ("
           + ", ".join(f"{s['fit']:.2f} fits, {s['scale']:g} drawn" for s in out["scales"]) + "), on whole pixels")


def reference_checks(start, trace):
    """The approach the page walked (the first step to the fight), played by the seeing
    reference (tools/rules/seeing.py): its checks as (step, who looks, band, distance,
    [(roll, total, tn, result) of every die, helpers first]), and how it ended."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "rules"))
    import re
    import seeing
    o = start["o"]
    case = {"seed": ((o["yard"] * 31 + o["floor"] * 977) & 0xFFFF) or 1,
            "light": seeing.LIGHTS.index(start["light"]),
            "tiles": [[int(c) for c in row] for row in o["rows"]],
            "party": {"sneaking": start["sneak"], "light": False,
                      "travelers": [{"stealth": t["stealth"], "notice": t["notice"]} for t in start["party"]]},
            "bands": [{"x": b["x"], "y": b["y"], "sense": b["sense"], "stealth": b["stealth"],
                       "hiding": b["hiding"]} for b in start["bands"]],
            "start": (trace[0]["x"], trace[0]["y"]),
            "path": [(t["x"], t["y"]) for t in trace[1:]]}
    checks, step, end = [], 0, None
    for ln in seeing.approach(case):
        m = re.match(r"step (\d+):", ln)
        if m:
            step = int(m.group(1))
        m = re.match(r"  band (\d+) at \d+,\d+, (\d+) away: (the party|band \d+) looks", ln)
        if m:
            checks.append([step, "party" if m.group(3) == "the party" else "band", int(m.group(1)) - 1,
                           int(m.group(2)), []])
        m = re.search(r"rolls (\d+) = (-?\d+) against (-?\d+): (\w+)", ln)
        if m:
            checks[-1][4].append((int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                  seeing.RESULT.index(m.group(4))))
        m = re.match(r"the fight: band (\d+)(, an ambush)?", ln)
        if m:
            end = (int(m.group(1)), bool(m.group(2)))
    return checks, end


def page_checks(trace):
    """The same, from the page's trace of the seeing engine (rooms.js, seeStep)."""
    checks, end = [], None
    for step, t in enumerate(trace):
        for e in t["events"]:
            dice = []
            if not e["automatic"]:
                for h in e["sneak"] + e["help"]:
                    dice.append((h["roll"], h["roll"] + h["rating"], h["tn"], h["result"]))
                dice.append((e["roll"], e["total"], e["look_tn"], e["result"]))
            checks.append([step, e["kind"], e["band"], e["d"], dice])
        if t["fight"]:
            end = (t["fight"], bool(t["ambush"]))
    return checks, end


def check_open():
    """Walking an open floor (docs/open-floors.md, step 3 of Building it): the page's checks,
    step by step, are the seeing reference's on the same floor, party and way, roll for
    roll, walking, sneaking and at night; a band spotted is drawn, one not spotted isn't; the
    band that sees you starts the fight (an ambush, theirs, if you hadn't spotted it), or
    you fall on one you've spotted (yours); the fight is on a 16 x 8 window of the floor
    holding the band, its foes where they stood; then walking again, the band gone."""
    runs = [("48213:WARDEN,ROGUE", "walk"), ("48213:WARDEN,ROGUE,CHANNELER,MEDIC", "sneak"),
            ("7602:ROGUE,MEDIC:look=dungeon", "walk"), ("48213:WARDEN,ROGUE,CHANNELER,MEDIC", "ambush")]
    for code, how in runs:
        out = page("open", code, how)
        if not out:
            continue
        bad, start, met = [], out["start"], out["met"]
        trace = met["trace"]
        if start["sneak"] != (how != "walk"):
            bad.append(f"S didn't set sneaking ({start['sneak']})")
        if "dungeon" in code and start["light"] != "night":
            bad.append(f"a dungeon floor is lit {start['light']}, not night")
        want, want_end = reference_checks(start, trace)
        got, got_end = page_checks(trace)
        if got != want:
            first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
            bad.append(f"check {first} isn't the reference's: {got[first:first + 1]} against {want[first:first + 1]} "
                       f"({len(got)} checks against {len(want)})")
        elif got_end != want_end:
            bad.append(f"the walk ended in {got_end}, the reference's in {want_end}")
        spotted = [b for b, v in enumerate(met["spotted"]) if v]
        fought = None
        if out["ambushed"]:
            fought = met["fightBand"]
            d = out["drawn"]
            if d["foes"] != d["spotted"] or not d["foes"]:
                bad.append(f"walking, the foes drawn are {d['foes']}, not the spotted bands' {d['spotted']}")
            if "surprise travelers" not in (met["spec"] or ""):
                bad.append("A fell on a band, but the first round isn't the travelers'")
        elif got_end:
            fought = got_end[0] - 1
            if ("surprise foes" in (met["spec"] or "")) != got_end[1]:
                bad.append("an ambush by the band" + (" isn't" if got_end[1] else " is wrongly") + " the foes' first round")
        if fought is not None and met["mode"] != "talk":
            b = start["bands"][fought]
            wx, wy = met["win"]
            o = start["o"]
            window = [row[wx:wx + 16] for row in o["rows"][wy:wy + 8]]
            foes = sorted([f["x"] - wx, f["y"] - wy] for f in b["foes"])
            got_foes = sorted(f[1:] for f in met["fighters"] if f[0] == 1)
            if met["map"] != window or not (0 <= wx <= o["w"] - 16 and 0 <= wy <= o["h"] - 8):
                bad.append(f"the fight's map isn't the floor's 16 x 8 window at {wx},{wy}")
            elif got_foes != foes:
                bad.append(f"the band's foes stand at {got_foes} in the fight, not where they stood, {foes}")
            else:
                sys.path.insert(0, os.path.join(ROOT, "tools", "rooms"))
                import rooms
                room = {"rows": window, "foes": [{"x": f["x"] - wx, "y": f["y"] - wy} for f in b["foes"]]}
                places = rooms.fight_places(room, (met["x"] - wx, met["y"] - wy), met["party"])
                got_places = [f[1:] for f in met["fighters"] if f[0] == 0]
                if [wx, wy] != rooms.fight_window(b["foes"], (met["x"], met["y"]), o["w"], o["h"]):
                    bad.append(f"the window at {wx},{wy} isn't rooms.py's fight_window")
                elif got_places != places:
                    bad.append(f"the party stands at {got_places}, not fight_places' {places}")
            after = out.get("after") or {}
            if after.get("mode") not in ("explore", "lost"):
                bad.append("the fight didn't end back in walking")
            elif after["mode"] == "explore" and not after["cleared"][fought]:
                bad.append("won, the band is still on the floor")
        if out["errors"]:
            bad.append(f"the page threw {out['errors'][:2]}")
        if bad:
            fail(f"open floor {code} {how}: " + "; ".join(bad))
        else:
            ok(f"open floor {code}, {how}: {len(got)} checks over {len(trace)} steps, the seeing reference's "
               f"roll for roll; {len(spotted)} band(s) spotted"
               + (f"; fell on band {fought + 1}, the first round the party's" if out["ambushed"]
                  else f"; band {fought + 1} saw the party" + (", an ambush" if got_end[1] else "") if fought is not None
                  else "") + ("; its fight on a 16 x 8 window of the floor, then walking again" if fought is not None else ""))


def check_c64():
    """The C64's scale (C, arena.js): exploring starts at it, the board drawn with the
    cartridge's 16-pixel tiles (each dot as the look's tiles16 file says, in its colours),
    the figures with their shared colour a black, as the cartridge has them; C turns it
    off, the choice kept after a reload, and C again turns it on."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import art
    from c64pic import PALETTE
    out = page("c64", "-")
    if not out:
        return
    bad = []
    hexes = ["#%02x%02x%02x" % c for c in PALETTE]
    look = art.load("tiles16-forest2")
    on = out["on"]
    if not on["c64"] or "Scale: the C64's" not in on["buttons"]:
        bad.append(f"exploring didn't start at the C64's scale ({on['c64']}, {on['buttons']})")
    for name, got in on["tiles"].items():
        e = look.entry(name)
        colour = {"k": look.background, "d": look.shared[0], "g": look.shared[1], "o": e.colour}
        # (seamless: the last row and column are the ones before them again)
        rows = [r[:-1] + r[-2] for r in e.rows[:-1]]
        rows.append(rows[-1])
        want = [[hexes[colour[c]] for c in r] for r in rows]
        if got != want:
            bad.append(f"forest2's {name} isn't its tiles16 art")
    figs = art.load("figures")
    e = figs.entry("HUMAN2")
    colour = {"a": 0, "b": figs.shared[1], "c": e.colour}
    for y, row in enumerate(e.rows):
        for x, c in enumerate(row):
            if c != "." and on["figure"][y][x] != hexes[colour[c]]:
                bad.append(f"HUMAN2's dot {x},{y} ({c}) is {on['figure'][y][x]}, not {hexes[colour[c]]}")
                break
    if out["off"] or out["reloaded"] or not out["again"]:
        bad.append(f"C made the C64's scale {out['off']}, after a reload {out['reloaded']}, and C again {out['again']}")
    if out["errors"]:
        bad.append(f"the page threw {out['errors'][:2]}")
    if bad:
        fail("the C64's scale: " + "; ".join(bad[:6]))
    else:
        ok("the C64's scale: exploring draws the look's tiles16 art (forest2's open, wall, pit and cover, "
           "dot for dot) and the figures with a black as the cartridge has them; C's choice kept after a reload")


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
        check_first()
        check_rules()
        check_explore()
        check_zoom()
        check_minimap()
        check_looks()
        check_talk()
        check_scale()
        check_c64()
        check_open()
    finally:
        server.terminate()
        server.wait()
    print(f"native arena: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
