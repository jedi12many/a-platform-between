"""The playable arena (docs/arena.md, "Playing it"): ten scenarios that show where the rules
stand, played by hand on the website's battle screen, as the computer plays them a
thousand times in tools/arena/arena.py.

    python3 tools/arena/scenarios.py OUT

writes, for each scenario, OUT/arena-NN.qs (a tiny Siding: the fight, its notes, "fight
again" and "leave"), and OUT/scenarios.json for the arena page (site/arena.html): each
scenario's code (A-01...: playtesters' feedback names it, so keep a code with its
scenario), notes, its traveler's Passport (built by the arena's quick builder, with the
scenario's gear), its foes, and what a thousand fights on the battle engine say.
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


def ring(s):
    """The scenario's map, its foes' letters only (a spare letter becomes open ground)."""
    used = "abcdefgh"[:len(s["foes"])]
    return ["".join("." if c.islower() and c not in used else c for c in r) for r in s["map"]]


def item_id(name):
    return arena.REG["items"][name]["id"]


def traveler(s):
    """The scenario's traveler: built by the arena's quick builder, gear equipped."""
    ch = arena.build(s["cls"], s["level"], name=s["cls"][:8])
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


def measured(s):
    """A thousand fights of the same scenario on the battle engine, both sides on quick."""
    m = arena.Matchup()
    item = arena.REG["items"][s["weapon"]]
    arch = arena.registry.ARCHETYPES[item["archetype"]]
    armor = arena.REG["items"][s["armor"]]["tier"] if s["armor"] else 0
    m.travelers.append(arena.Traveler([s["cls"], str(s["level"]), "weapon", arch,
                                       str(item["tier"]), arena.registry.DAMAGE[item["damage"]],
                                       "armor", str(armor)]))
    for f in s["foes"]:
        m.add_foe(f)
    m.map = ring(s)
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
            "arena": measured(s)})
    with open(os.path.join(out, "scenarios.json"), "w") as f:
        json.dump(data, f, indent=1)
    print(f"arena: {len(data)} scenarios in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
