"""The playable arena (docs/arena.md, "Playing it"): ten scenarios that show where the rules
stand, played by hand on the website's battle screen, as the computer plays them a
thousand times in tools/arena/arena.py.

    python3 tools/arena/scenarios.py OUT

writes, for each scenario, OUT/arena-NN.qs (a tiny Siding: the fight, its notes, "fight
again" and "leave"), and OUT/scenarios.json for the arena page (site/arena.html): each
scenario's code (A-01...: playtesters' feedback names it, so keep a code with its
scenario), notes, its traveler's Passport (built by the arena's quick builder, with the
scenario's gear), its foes, and what a thousand fights on the battle engine say. Each
scenario also carries what the native arena (tools/arena/web/, docs/arena.md) needs to set
the fight up without a story: the map, the fighters' lines for its battle engine, the
figures to draw, and a pack of gear to try.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import arena  # noqa: E402

FIRST_ID = 1101             # the arena's Departures: 1101-1110 (Sidings, like the Deep Yards' 1000)

OPEN = ["############",
        "#.........a#",
        "#..........#",
        "#@.........#",
        "#.........b#",
        "#..........#",
        "#.........c#",
        "############"]

CORRIDOR = ["#######",
            "#@..a.#",
            "#######"]

COVER = ["############",
         "#..+.....a.#",
         "#@.+.......#",
         "#..+.....b.#",
         "############"]

# Each scenario: what it shows, the traveler (class, level, gear as registry items), the
# foes (the map's letters, in order), the map, and what to watch for.
SCENARIOS = [
    {"title": "A fair fight",
     "issue": "The model every other fight is measured against: a new Warden, a rusted sabre "
              "and a padded coat, against one rust-guard. It should be close, and usually won.",
     "watch": "How many hits it takes each way, and how much health you have left.",
     "cls": "WARDEN", "level": 1, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["RUST_GUARD"], "map": OPEN},
    {"title": "Magic is safe",
     "issue": "A new Channeler with an ember wand against the same rust-guard. Powers are "
              "aimed at Ward, not Armor, and the rust-guard's Ward (10) is half its Armor (20).",
     "watch": "How often your bolts land compared with the Warden's sword, and how many free "
              "shots you get while it walks over.",
     "cls": "CHANNELER", "level": 1, "weapon": "EMBER_WAND", "armor": None,
     "foes": ["RUST_GUARD"], "map": OPEN},
    {"title": "Magic up close",
     "issue": "The same Channeler and rust-guard, in a corridor three squares long: no room "
              "to shoot it as it comes.",
     "watch": "Whether the Channeler still wins easily when distance is taken away.",
     "cls": "CHANNELER", "level": 1, "weapon": "EMBER_WAND", "armor": None,
     "foes": ["RUST_GUARD"], "map": CORRIDOR},
    {"title": "The right weakness",
     "issue": "A new Rogue with an arc pistol (energy) against a rust-guard, which is weak to "
              "energy: a weakness ignores Armor altogether.",
     "watch": "How easy the right damage type makes it.",
     "cls": "ROGUE", "level": 1, "weapon": "ARC_PISTOL", "armor": None,
     "foes": ["RUST_GUARD"], "map": OPEN},
    {"title": "Two of them",
     "issue": "The new Warden against two rust-guards: one is a fair fight, two is a wall.",
     "watch": "How fast it turns once you're flanked.",
     "cls": "WARDEN", "level": 1, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["RUST_GUARD", "RUST_GUARD"], "map": OPEN},
    {"title": "Level 4: still a wall",
     "issue": "A level 4 Warden, the same sabre and coat, against two rust-guards. Three levels "
              "have added 6 health and a few points of Melee.",
     "watch": "Whether those levels feel like they count.",
     "cls": "WARDEN", "level": 4, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["RUST_GUARD", "RUST_GUARD"], "map": OPEN},
    {"title": "Level 5: new gear",
     "issue": "One level more, with an iron sword and a chain coat (tier 2): the same two "
              "rust-guards. Gear outweighs levels.",
     "watch": "The jump from the last scenario: one level, one tier of gear.",
     "cls": "WARDEN", "level": 5, "weapon": "IRON_SWORD", "armor": "CHAIN_COAT",
     "foes": ["RUST_GUARD", "RUST_GUARD"], "map": OPEN},
    {"title": "The swarm",
     "issue": "The new Warden against four ash rats: each is nothing, together they're a lot. "
              "Two are easy, three usually, four is a coin toss.",
     "watch": "How quickly small hits add up, and the rats running off when they're hurt.",
     "cls": "WARDEN", "level": 1, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["ASH_RAT", "ASH_RAT", "ASH_RAT", "ASH_RAT"],
     "map": ["############",
             "#.........a#",
             "#.........b#",
             "#@.........#",
             "#.........c#",
             "#.........d#",
             "############"]},
    {"title": "A lone shooter",
     "issue": "A new Rogue with a scrap pistol against one scrap gunner: 15 health, nowhere to "
              "hide. A shooter alone is no threat.",
     "watch": "Whether a gunner on its own feels like a fight at all.",
     "cls": "ROGUE", "level": 1, "weapon": "SCRAP_PISTOL", "armor": None,
     "foes": ["SCRAP_GUNNER"], "map": OPEN},
    {"title": "Shooters in a pair",
     "issue": "The new Warden against two scrap gunners behind a line of cover. Shooters are "
              "meant to come in groups: two beat a new Warden more often than not.",
     "watch": "Crossing open ground under fire, and whether cover helps you.",
     "cls": "WARDEN", "level": 1, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["SCRAP_GUNNER", "SCRAP_GUNNER"], "map": COVER},
]


# The rules lab's scenarios (docs/turn.md): rules v1's movement and conditions, played only
# in the modern arena (tools/arena/web/), as the game itself is still on v0. Codes R-01...
# Each may name a race, its foes' hits (FOE:CONDITION), and what its hazards do.
LAB = [
    {"title": "Through the fire",
     "issue": "A new Warden against a scrap gunner on the far side of a band of fire. Every "
              "square of fire you step into burns you (5 fire damage) and sets you on fire; "
              "there's no way round.",
     "watch": "What crossing costs you, whether a Dash (D) to get through in one turn is worth "
              "it, and whether shaking off the flames feels fair.",
     "cls": "WARDEN", "level": 1, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["SCRAP_GUNNER"], "hazard": [5, "fire", "ON_FIRE"],
     "map": ["############",
             "#...^^^....#",
             "#@..^^^...a#",
             "#...^^^....#",
             "############"]},
    {"title": "Over the edge",
     "issue": "A new Warden against two rust-guards on a ledge between two pits. Shove (S) one "
              "off and it's out of the fight; they can't do it back.",
     "watch": "Whether Shove is too strong next to a pit, and how often it works (Athletics "
              "against the guard's TN).",
     "cls": "WARDEN", "level": 1, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["RUST_GUARD", "RUST_GUARD"],
     "map": ["############",
             "#OOOOOOOOOO#",
             "#.....a....#",
             "#@.........#",
             "#.....b....#",
             "#OOOOOOOOOO#",
             "############"]},
    {"title": "Venom",
     "issue": "A new Warden against three ash rats whose bites poison: 3 damage at the start "
              "of each of your turns, until you shake it off (Grit, TN 100) or five rounds pass.",
     "watch": "How much the poison adds, and whether shaking it off comes often enough.",
     "cls": "WARDEN", "level": 1, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["ASH_RAT:POISONED", "ASH_RAT:POISONED", "ASH_RAT:POISONED"],
     "map": ["############",
             "#.........a#",
             "#@.........#",
             "#.........b#",
             "#.........c#",
             "############"]},
    {"title": "Cold shot",
     "issue": "A new Warden against two scrap gunners behind cover whose shots chill you "
              "(Speed -1). Crossing to them is slower each time they hit.",
     "watch": "Whether being chilled makes the walk miserable, or just a little slower.",
     "cls": "WARDEN", "level": 1, "weapon": "RUSTED_SABRE", "armor": "PADDED_COAT",
     "foes": ["SCRAP_GUNNER:CHILLED", "SCRAP_GUNNER:CHILLED"],
     "map": ["############",
             "#..+.....a.#",
             "#@.+.......#",
             "#..+.....b.#",
             "############"]},
    {"title": "Wings",
     "issue": "A Moth-folk Rogue, who flies (Winged), against a rust-guard, with pits between "
              "them. The guard has to walk round; the Rogue can hang over a pit and shoot.",
     "watch": "Whether flying over pits is too strong, and what the guard can do about it.",
     "cls": "ROGUE", "level": 1, "weapon": "SCRAP_PISTOL", "armor": None, "race": "MOTH_FOLK",
     "foes": ["RUST_GUARD"],
     "map": ["############",
             "#...OOOO...#",
             "#@..OOOO..a#",
             "#...OOOO...#",
             "#..........#",
             "############"]},
    {"title": "Run and gun",
     "issue": "A new Channeler against a rust-guard on an open floor. Dash (D) moves you twice "
              "instead of attacking: you can keep away, but you don't shoot that turn.",
     "watch": "Whether running away with Dash is too strong, or never worth a lost shot.",
     "cls": "CHANNELER", "level": 1, "weapon": "EMBER_WAND", "armor": None,
     "foes": ["RUST_GUARD"],
     "map": ["##############",
             "#............#",
             "#............#",
             "#@..........a#",
             "#............#",
             "#............#",
             "##############"]},
]


def foe_name(f):
    return f.split(":")[0]


def foe_hit(f):
    return f.split(":")[1] if ":" in f else None


def ring(s):
    """The scenario's map, its foes' letters only (a spare letter becomes open ground)."""
    used = "abcdefgh"[:len(s["foes"])]
    return ["".join("." if c.islower() and c not in used else c for c in r) for r in s["map"]]


def item_id(name):
    return arena.REG["items"][name]["id"]


def traveler(s):
    """The scenario's traveler: built by the arena's quick builder, gear equipped."""
    ch = arena.build(s["cls"], s["level"], s.get("race"), name=s["cls"][:8])
    ch["equipped"] = {0: item_id(s["weapon"])}
    if s["armor"]:
        ch["equipped"][1] = item_id(s["armor"])
    return ch


def qs(n, s):
    """The scenario as a tiny Siding: notes, the fight, and again or leave."""
    letters = "abcdefgh"
    rows = ["    " + r for r in ring(s)]
    foes = [f"    {letters[i]} = {f}" for i, f in enumerate(s["foes"])]
    issue = s["issue"]
    return f"""// The arena, scenario {n} (generated by tools/arena/scenarios.py: edit it there).

title: Arena {n}: {s['title']}
id: {FIRST_ID + n - 1}
kind: siding
realm: tl 5, ml 5
levels: 1-10
start: ready
linear: yes

map ring
{chr(10).join(rows)}
{chr(10).join(foes)}

=== {s['title']}

== ready
{issue}

Watch for: {s['watch']}

+ [Fight] -> fight
+ [Leave the arena] -> leave

== fight
~ heal full
fight ring
    won:  You won. -> after
    fled: You got out. -> after
    lost: You went down. -> after

== after
+ [Fight again] -> fight
+ [Leave the arena] -> leave

== leave
~ end complete
"""


# The arena's gear: a scenario's pack is every one of these up to its weapon's tier, but
# what it already wears or holds (the pack holds 6: docs/races.md).
ARENA_GEAR = ["RUSTED_SABRE", "IRON_SWORD", "SCRAP_PISTOL", "ARC_PISTOL", "EMBER_WAND",
              "PADDED_COAT", "CHAIN_COAT"]
PACK_SIZE = 6


def pack(s):
    tier = arena.REG["items"][s["weapon"]]["tier"]
    held = {s["weapon"], s["armor"]}
    return [item_id(i) for i in ARENA_GEAR
            if i not in held and arena.REG["items"][i]["tier"] <= tier][:PACK_SIZE]


def native(s, ch):
    """The fight, for the native arena: the map without its letters, a line for each
    fighter (tools/arena/web/arena.c's spec), and the figure each is drawn with."""
    rows = ring(s)
    spots = {c: (x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c != "." and
             (c == "@" or c.islower())}
    clean = ["".join("." if (c == "@" or c.islower()) else c for c in r) for r in rows]
    x, y = spots["@"]
    lines = [f"map {len(clean[0])} {len(clean)}"] + clean
    if s.get("hazard"):
        d, t, c = s["hazard"]
        lines.append(f"hazard {d} {t or 'none'} {c or '-'}")
    lines.append(f"traveler {x} {y} {arena.passport.encode(ch)} {item_id(s['weapon'])}")
    figures = [s.get("race") or arena.DEFAULT_RACE[s["cls"]]]
    names = [arena.REG["classes"][s["cls"]]["display"]]
    plain = [foe_name(f) for f in s["foes"]]
    for i, f in enumerate(s["foes"]):
        fx, fy = spots["abcdefgh"[i]]
        hit = foe_hit(f)
        lines.append(arena.foe_line(foe_name(f), fx, fy) + (f" hit {hit}" if hit else ""))
        figures.append(foe_name(f))
        same = plain.count(foe_name(f)) > 1
        names.append(arena.REG["foes"][foe_name(f)]["display"]
                     + (f" {plain[:i + 1].count(foe_name(f))}" if same else ""))
    return {"spec": "\n".join(lines) + "\n", "figures": figures, "names": names,
            "pack": pack(s), "skills": {k: arena.rating(ch, k.upper()) for k in
                                        ("melee", "ranged", "channel", "athletics")}}


def items():
    """What the native arena's pack shows of each item."""
    out = {}
    for name in ARENA_GEAR + ["PULSE_RIFLE", "BALLISTIC_WEAVE"]:
        it = arena.REG["items"][name]
        arch = arena.registry.ARCHETYPES[it["archetype"]]
        out[it["id"]] = {"name": name, "display": it["display"], "kind": arch, "tier": it["tier"],
                         "type": arena.registry.DAMAGE[it["damage"]],
                         "damage": 5 * it["tier"] if arch != "armor" else 0,
                         "armor": 10 * it["tier"] if arch == "armor" else 0}
    return out


def matchup(s, rules="v0"):
    """The scenario as an arena matchup, by rules v0 or the rules lab's (next)."""
    m = arena.Matchup()
    m.set_rules(rules)
    item = arena.REG["items"][s["weapon"]]
    arch = arena.registry.ARCHETYPES[item["archetype"]]
    armor = arena.REG["items"][s["armor"]]["tier"] if s["armor"] else 0
    m.travelers.append(arena.Traveler(([s["race"]] if s.get("race") else [])
                                      + [s["cls"], str(s["level"]), "weapon", arch,
                                         str(item["tier"]), arena.registry.DAMAGE[item["damage"]],
                                         "armor", str(armor)]))
    for f in s["foes"]:
        m.add_foe(foe_name(f) + (f" hit {foe_hit(f)}" if foe_hit(f) else ""))
    if s.get("hazard"):
        d, t, c = s["hazard"]
        m.set_hazard([str(d), t or "none", c or "-"])
    m.map = ring(s)
    return m


def conditions():
    """What the modern arena shows of each condition: its tag, its name, and what it does,
    in words (registry/conditions.txt)."""
    words = {"speed0": "can't move", "dodge0": "Dodge 0", "lose_turn": "loses its turn",
             "down": "knocked down: standing takes half its Speed", "ends_when_hit": "ends when hit",
             "ends_on_heal": "ends when healed", "no_powers": "no powers", "no_heal": "no healing",
             "fly": "flies", "first": "acts first"}
    out = {}
    for c in arena.CONDS.values():
        e, said = c["effects"], []
        for k, v in e.items():
            if k in words:
                said.append(words[k])
            elif k in ("dot", "thorns"):
                n, t = v
                kind = f" {arena.registry.DAMAGE[t]}" if t is not None else ""
                said.append(f"{n}{kind} damage each turn" if k == "dot" else f"thorns {n}{kind}")
            elif k in ("vulnerable", "immune_hazard"):
                t = arena.registry.DAMAGE[v]
                said.append(f"double {t} damage" if k == "vulnerable" else f"no {t} damage from hazards")
            elif k == "immune":
                said.append("immune: " + ", ".join(arena.CONDS[x]["display"].lower() for x in v))
            elif k == "race":
                continue
            elif k == "heal":
                said.append(f"heals {v} each turn")
            elif k == "barrier":
                said.append(f"absorbs the next {v} damage")
            elif k == "next":
                said.append(f"{v:+d} to its next attack")
            else:
                said.append(f"{k.capitalize()} {v:+d}")
        if c["rounds"]:
            said.append(f"{c['rounds']} round{'s' * (c['rounds'] > 1)}")
        if c["shake"]:
            said.append(f"shake off: {arena.registry.STATS[c['shake'][0]].capitalize()}, TN {c['shake'][1]}")
        out[c["id"]] = {"name": c["name"], "tag": c["tag"], "display": c["display"],
                        "what": "; ".join(said), "trait": "race" in e}
    return out


def measured(s, rules="v0"):
    """A thousand fights of the same scenario on the battle engine, both sides on quick."""
    m = matchup(s, rules)
    results, foes = arena.fight(m)
    sm = arena.summary(m, results, foes)
    return {"won": round(sm["won"]), "lost": round(sm["lost"]), "fled": round(sm["fled"]),
            "rounds": round(sm["rounds"], 1),
            "health_left": round(100 * sm["fighters"][0]["left"] / sm["fighters"][0]["health"])}


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = argv[1]
    os.makedirs(out, exist_ok=True)
    data = []
    for n, s in enumerate(SCENARIOS, 1):
        with open(os.path.join(out, f"arena-{n:02d}.qs"), "w") as f:
            f.write(qs(n, s))
        ch = traveler(s)
        weapon = arena.REG["items"][s["weapon"]]
        data.append({
            "n": n, "code": f"A-{n:02d}", "id": FIRST_ID + n - 1, "dir": f"arena-{n:02d}",
            "title": s["title"],
            "issue": s["issue"], "watch": s["watch"],
            "traveler": f"{arena.REG['classes'][s['cls']]['display']}, level {s['level']}",
            "gear": ", ".join(arena.REG["items"][i]["display"]
                              for i in (s["weapon"], s["armor"]) if i),
            "weapon_tier": weapon["tier"],
            "foes": [arena.REG["foes"][f]["display"] for f in s["foes"]],
            "passport": arena.passport.encode(ch),
            "arena": measured(s),
            "lab": measured(s, "next"),
            "native": native(s, ch)})
    with open(os.path.join(out, "scenarios.json"), "w") as f:
        json.dump(data, f, indent=1)
    lab = []
    for n, s in enumerate(LAB, 1):
        ch = traveler(s)
        lab.append({
            "n": n, "code": f"R-{n:02d}", "title": s["title"], "issue": s["issue"],
            "watch": s["watch"], "lab_only": True,
            "traveler": f"{arena.REG['classes'][s['cls']]['display']}, level {s['level']}",
            "foes": [arena.REG["foes"][foe_name(f)]["display"] for f in s["foes"]],
            "hazard": s.get("hazard"),
            "lab": measured(s, "next"),
            "native": native(s, ch)})
    with open(os.path.join(out, "lab.json"), "w") as f:
        json.dump(lab, f, indent=1)
    with open(os.path.join(out, "items.json"), "w") as f:
        json.dump(items(), f, indent=1)
    with open(os.path.join(out, "conditions.json"), "w") as f:
        json.dump(conditions(), f, indent=1)
    print(f"arena: {len(data)} scenarios and {len(lab)} of the rules lab's in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
