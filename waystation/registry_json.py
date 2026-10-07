"""The registry as JSON, for the Waystation website's names (`make waystation`).

    python3 waystation/registry_json.py OUT.json

The site gets the rules from the rules core (waystation/ws.c); this gives it the names
to show: stats, races, classes, skills, items and Echoes, by id.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools", "registry"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))

import registry  # noqa: E402
from passport import STATS  # noqa: E402


def title(name):
    return name.replace("_", " ").title()


def main(out):
    reg = registry.load()
    data = {
        "stats": [s.title() for s in STATS],
        "races": {e["id"]: {"name": e["display"], "bonus": e["bonus"]} for e in reg["races"].values()},
        "classes": {e["id"]: {"name": e["display"], "bonus": e["bonus"], "tags": e["tags"]}
                    for e in reg["classes"].values()},
        "skills": {e["id"]: {"name": e["display"], "stat": e["stat"]} for e in reg["skills"].values()},
        "items": {e["id"]: e["display"] for e in reg["items"].values()},
        "echoes": {e["id"]: {"name": title(e["name"]), "states": [title(s) for s in e["states"]]}
                   for e in reg["echoes"].values()},
    }
    with open(out, "w") as f:
        json.dump(data, f, indent=1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
