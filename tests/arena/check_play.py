"""The playable arena (docs/arena.md, "Playing it"; tools/arena/scenarios.py, site/arena.html).

1. Each scenario's traveler is what the page says: by the Python reference, its Passport
   decodes to that class and level, built as the arena's quick builder builds one, with
   the scenario's weapon and armor equipped.
2. Each scenario's Departure compiles clean, and its map holds a traveler's start and
   exactly the scenario's foes.
3. The page's numbers are the arena's: the same matchup, run again by tools/arena/arena.py,
   gives the same win rate.
4. In headless Chromium, the page lists all ten, and every Play boards its scenario's
   Departure, reaches its menu, and starts the fight.

    NODE_PATH=$(npm root -g) python3 tests/arena/check_play.py    (make test-waystation)
"""

import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))
sys.path.insert(0, os.path.join(ROOT, "tools", "qsc"))
import arena  # noqa: E402
import scenarios  # noqa: E402

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  ", msg)


def main():
    data = json.load(open(os.path.join(ROOT, "build", "arena-play", "scenarios.json")))
    if len(data) != 10:
        fail(f"{len(data)} scenarios, not 10")
    bad = 0
    for s, spec in zip(data, scenarios.SCENARIOS):
        ch = arena.passport.decode(s["passport"])
        want = arena.build(spec["cls"], spec["level"], name=spec["cls"][:8])
        gear = [arena.REG["items"][spec["weapon"]]["id"]]
        if spec["armor"]:
            gear.append(arena.REG["items"][spec["armor"]]["id"])
        if (ch["class"] != arena.REG["classes"][spec["cls"]]["id"] or ch["level"] != spec["level"]
                or ch["stats"] != want["stats"] or ch["training"] != want["training"]
                or sorted(ch["equipped"].values()) != sorted(gear)):
            fail(f"scenario {s['n']}: its traveler isn't the {spec['cls']} {spec['level']} the page says")
            bad += 1
        qs = os.path.join(ROOT, "build", "arena-play", f"arena-{s['n']:02d}.qs")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "qsc", "qsc.py"), "check", qs],
                           capture_output=True, text=True)
        rows = scenarios.ring(spec)
        letters = sorted(c for r in rows for c in r if c.islower())
        if p.returncode or "0 warning" not in p.stdout or "".join(r.count("@") and "@" or "" for r in rows) != "@" \
                or len(letters) != len(spec["foes"]):
            fail(f"scenario {s['n']}: {p.stdout.strip()} {p.stderr.strip()}")
            bad += 1
        again = scenarios.measured(spec)
        if again != s["arena"]:
            fail(f"scenario {s['n']}: the page says {s['arena']}, the arena now {again}")
            bad += 1
    if not bad:
        ok("ten scenarios: each traveler the page's class, level and gear, built by the rules; "
           "each Departure compiles clean; each number the arena's")

    p = subprocess.run(["node", os.path.join(ROOT, "tests", "arena", "play.cjs")]
                       + [str(n) for n in range(1, 11)], capture_output=True, text=True, timeout=900)
    out = p.stdout.split("\n")
    fights = out.count("fighting")
    want = [f"departure arena-{n:02d}" for n in range(1, 11)]
    if p.returncode or any("page error" in ln or "error:" in ln for ln in out) \
            or [ln for ln in out if ln.startswith("departure ")] != want or fights != 10 \
            or out.count("listed 10") != 10:
        fail("the arena page in Chromium:\n" + p.stdout + p.stderr)
    else:
        ok("in Chromium the page lists ten, and every Play boards its scenario and starts the fight")
    print(f"arena page: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
