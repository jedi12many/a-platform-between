"""The Waystation website (W1, docs/waystation-web.md) does what the rules say.

The site (build/waystation/) is played in headless Chromium by tests/waystation/site.cjs,
and everything it shows is checked against the Python references, which were written
from the docs, independently of the C core the site runs:

1. A traveler made in the browser has the Passport tools/passport/passport.py makes from
   the same choices, and boards The Fare in the terminal (build/apb) with a Boarding
   Pass; the trip ends in a Travel Stamp.
2. That stamp, landed in the browser, gives the Passport tools/passport/receipt.py gives;
   so does the same stamp as a Rewind.
3. Points spent in the browser give the Passport the levelling rules give, worked out
   here by hand (docs/rules-v0.md, "Levels").
4. Rolled stats: a set and three re-rolls, each 15..90 in steps of 5, and the traveler
   made from the last set has it, with the race and class bonuses.
5. A Passport with a typo is refused, naming the line; the tabletop sheet shows the
   numbers the rules give.
6. Your travelers: a Passport saved with a note is kept, chosen from the list to land a
   stamp, and replaced by the stamped one (the old one kept too). On the site (build/site/),
   signed in (claude.ai's store, stood in for), it's kept in the player's own place in the
   store, shown on the platform, and boards the train from the list under the screen.

    python3 tests/waystation/check_site.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for sub in ("passport", "registry", "qsc"):
    sys.path.insert(0, os.path.join(ROOT, "tools", sub))

import boarding  # noqa: E402
import passport  # noqa: E402
import receipt  # noqa: E402
import stamp  # noqa: E402

SITE = os.path.join(ROOT, "tests", "waystation", "site.cjs")
FARE_PICKS = ["1", "1", "1", "1", "1", "2", "2", "2", "3", "1", "1", "2", "2"]
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  " + msg)


def site(*args):
    p = subprocess.run(["node", SITE] + list(args), capture_output=True, text=True, timeout=300)
    if p.returncode:
        fail(f"site.cjs {args[0]}: {p.stderr.strip()}")
        return None
    return p.stdout.strip()


def made(name, race, cls, stats, tag):
    """The Passport the reference makes for these choices."""
    return passport.encode(passport.create(name, race, cls, stats, tag))


def board_the_fare(text):
    """Play The Fare in the terminal with this Passport and a pass; its Travel Stamp."""
    with tempfile.TemporaryDirectory() as tmp:
        apd = os.path.join(tmp, "fare.apd")
        subprocess.run([sys.executable, "tools/qsc/qsc.py", "build",
                        "content/s1/00-the-fare/the-fare.qs", "-o", apd],
                       cwd=ROOT, check=True, capture_output=True)
        typed_pass = boarding.issue(text, 0, 424242, 1985)
        choices = os.path.join(tmp, "choices")
        with open(choices, "w") as f:
            f.write("\n".join(passport.lines(typed_pass) + ["", "1"] + FARE_PICKS) + "\n")
        out = subprocess.run(["build/apb", "--choices", choices, apd], cwd=ROOT,
                             capture_output=True, text=True, timeout=60).stdout
    m = re.search(r"into your Passport:\n\n((?:  \w+\n)+)", out)
    return out, ("".join(m.group(1).split()) if m else None)


def raise_by_hand(ch, clicks):
    """Spend points by the rules in docs/rules-v0.md, worked out here."""
    for kind, i in clicks:
        if kind == "stat":
            if ch["stat_points"] and ch["stats"][i] < 100:
                ch["stat_points"] -= 1
                ch["stats"][i] += 1
            continue
        governing = [s for s in passport._REG["skills"].values() if s["id"] == i][0]["stat"]
        training = ch["training"].get(i, 0)
        rating = min(100, ch["stats"][governing] // 2 + training)
        cost = 1 if rating < 50 else 2 if rating < 75 else 3 if rating < 90 else 4
        if ch["skill_points"] >= cost and training < 100:
            ch["skill_points"] -= cost
            ch["training"][i] = min(100, training + (2 if i in ch["tags"] else 1))
    return ch


def main():
    # 1. Made in the browser, boarded in the terminal.
    choices = ("Wren", "Glassfolk", "Tinker", "45,40,55,60,40,60", "Persuade")
    wren = site("create", *choices)
    want = made("Wren", "GLASSFOLK", "TINKER", [45, 40, 55, 60, 40, 60], "PERSUADE")
    if wren != want:
        fail(f"the browser's Passport for Wren is {wren}, the reference's {want}")
        return 1
    ok("a traveler made in the browser has the reference's Passport")
    out, s = board_the_fare(wren)
    if "Wren, Glassfolk Tinker, level 1" not in out or not s:
        fail(f"Wren didn't board The Fare in the terminal, or got no Travel Stamp:\n{out[-600:]}")
        return 1
    ok("she boards The Fare in the terminal, and comes back with a Travel Stamp")

    # 2. The stamp lands in the browser as the reference lands it.
    for rewind in (False, True):
        got = site("stamp", wren, s, *(["rewind"] if rewind else []))
        if got is None:
            continue
        got = json.loads(got)
        after, _ = receipt.apply(passport.decode(wren), stamp.decode(s), rewind=rewind)
        if got.get("passport") != passport.encode(after):
            fail(f"the stamp{' as a Rewind' if rewind else ''} lands as {got}, "
                 f"not {passport.encode(after)}")
        else:
            ok(f"her Travel Stamp lands{' as a Rewind' if rewind else ''} as the reference lands it"
               f" ({' '.join(got['said'][:2])})")
    # Your travelers: saved with a note, kept over a reload, chosen to land the stamp, and the
    # stamped Passport kept in place of the old one, which is kept too.
    got = site("keep", wren, s, "Dock 3")
    if got is not None:
        got = json.loads(got)
        after, _ = receipt.apply(passport.decode(wren), stamp.decode(s), rewind=False)
        kept = got["kept"]
        if (len(kept) != 1 or kept[0]["passport"] != passport.encode(after)
                or kept[0]["previous"][:1] != [wren] or kept[0]["note"] != "Dock 3"
                or kept[0]["name"] != "WREN" or not got["label"].startswith("WREN")):
            fail(f"Your travelers kept {got}")
        else:
            ok("saved with a note, Wren is chosen to land her stamp, and her new Passport is kept"
               " (the old one too)")
    got = site("shell", wren)
    if got is not None:
        got = json.loads(got)
        docs = got["docs"]
        mine = [k for k in docs if k.startswith("data/users/u_test/")]
        if (len(mine) != 1 or docs[mine[0]]["passport"] != wren
                or docs[mine[0]]["note"] != "Off to Dock 3" or not got["shown"]
                or "Off to Dock 3" not in got["shown"][0] or not got["choices"]
                or not got["choices"][0].startswith("WREN") or not got["typed"]):
            fail(f"the signed-in site: {got}")
        else:
            ok("signed in, Wren is kept on her player's account, shown on the platform, and"
               " boards the train from the list")
    bad = s[:5] + ("0" if s[5] != "0" else "1") + s[6:]
    got = site("stamp", wren, bad)
    if got is None or "line 1" not in json.loads(got).get("error", ""):
        fail(f"a stamp with a typo wasn't refused by its line: {got}")
    else:
        ok("a Travel Stamp with a typo is refused, naming the line")

    # 3. Spending points.
    ch = passport.create("Sable", "HUMAN", "TINKER", [40, 45, 45, 70, 25, 25], "STEALTH")
    ch.update(level=4, stat_points=2, skill_points=9)
    ch["training"][6] = 40                        # Tech, tagged: a rating over 50
    clicks = [("stat", 3), ("stat", 3), ("stat", 3), ("skill", 6), ("skill", 6), ("skill", 0),
              ("skill", 9), ("skill", 6), ("skill", 6), ("skill", 6)]
    got = site("spend", passport.encode(ch), *[f"{k}:{i}" for k, i in clicks])
    want = passport.encode(raise_by_hand(passport.decode(passport.encode(ch)), clicks))
    if got != want:
        fail(f"points spent in the browser give {got}, the rules {want}")
    else:
        ok("points spent in the browser give the Passport the levelling rules give")

    # 4. Rolling.
    got = site("roll")
    if got:
        got = json.loads(got)
        sets = [[int(v) for v in s.split(", ")] for s in got["sets"]]
        last = sets[-1][:]
        ch = passport.decode(got["passport"])
        last[5] += 10                             # the defaults: a Human (Fate) Warden (Might)
        last[0] += 5
        if (len(sets) != 4 or any(not 15 <= v <= 90 or v % 5 for s in sets for v in s)
                or ch["stats"] != [min(100, v) for v in last]):
            fail(f"rolling: sets {sets}, the traveler's stats {ch['stats']}")
        else:
            ok("rolled stats: a set and three re-rolls, 3d6 x 5, and the last set stands")

    # 5. Typos and the sheet.
    typo = wren[:25] + ("0" if wren[25] != "0" else "1") + wren[26:]
    got = site("read", typo)
    if not got or "line 2" not in got:
        fail(f"a Passport with a typo on line 2: {got}")
    else:
        ok("a Passport with a typo is refused, naming the line")
    sheet = site("sheet", wren)
    w = passport.decode(wren)
    health = 10 + w["stats"][2] // 4 + 2 * w["level"]
    if not sheet or "WREN" not in sheet or f"Health\t{health}" not in sheet:
        fail(f"the tabletop sheet doesn't show Wren with {health} health:\n{sheet}")
    else:
        ok(f"the tabletop sheet shows Wren, with {health} health as the rules give")

    print(f"waystation tests: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
