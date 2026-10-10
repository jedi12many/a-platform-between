"""The round trip, through the real terminal front end (docs/engine-plan.md, E2.5).

1. Kestrel, fresh from the character creator, is issued a Boarding Pass for The Fare by
   the Waystation prototype (tools/waystation/station.py), plays it in build/apb, and
   her Travel Stamp lands on her Passport.
2. Her new Passport is issued a pass for a test Departure (tests/vm/loop.qs), which she
   plays and stamps too. Her Passport ends up with both trips on it.
3. A stamp can't land twice. Playing the second Departure again is a Rewind: half the
   XP, and the fee.
4. Two overlapping trips: two passes issued before either stamp comes home both land, in
   either order. (A pass carries the character as they were when it was issued, so one
   kept back and played after another trip is just such an overlap.)

    python3 tests/term/check_roundtrip.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "waystation"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
sys.path.insert(0, os.path.join(ROOT, "tools", "qsc"))
sys.path.insert(0, os.path.join(ROOT, "tools", "registry"))

import passport  # noqa: E402
import station  # noqa: E402

failures = 0
TMP = tempfile.mkdtemp(prefix="apb-roundtrip-")
KESTREL = "4PB794AR0A0105AM7HDT8V4000000000K60M2A4A50200810HJB"
FARE_PICKS = ["1", "1", "1", "1", "1", "2", "2", "2", "3", "1", "1", "2", "2"]
LOOP_PICKS = ["1", "1", "2"]                     # ring the bell three times, then leave


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def build(src, name):
    apd = os.path.join(TMP, name + ".apd")
    man = os.path.join(TMP, name + ".json")
    subprocess.run([sys.executable, "tools/qsc/qsc.py", "build", src, "-o", apd,
                    "--manifest", man], cwd=ROOT, check=True, capture_output=True)
    with open(man) as f:
        return apd, json.load(f)


def play(apd, typed_pass, picks):
    """Board in the terminal with this Boarding Pass; returns (transcript, stamp)."""
    lines = passport.lines(typed_pass) + ["", "1"] + picks
    path = os.path.join(TMP, "choices")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    out = subprocess.run(["build/apb", "--choices", path, apd], cwd=ROOT,
                         capture_output=True, text=True, timeout=60).stdout
    m = re.search(r"into your Passport:\n\n((?:  \w+\n)+)", out)
    return out, ("".join(m.group(1).split()) if m else None)


def main():
    fare, fare_m = build("content/s1/00-the-fare/the-fare.qs", "fare")
    loop, loop_m = build("tests/vm/loop.qs", "loop")
    ledger = {"tickets": {}}

    # 1. The Fare, from a fresh character.
    p1 = station.issue(ledger, "kestrel", KESTREL, 0, ticket=1985, seed=1985)
    out, s1 = play(fare, p1, FARE_PICKS)
    if not s1:
        fail(f"The Fare printed no Travel Stamp:\n{out[-800:]}")
        return
    after_fare, _ = station.land(ledger, "kestrel", KESTREL, s1, fare_m)
    k = passport.decode(after_fare)
    if (k["level"], k["xp"], k["debt"]) != (1, 5, 50000):
        fail(f"after The Fare: level {k['level']}, xp {k['xp']}, debt {k['debt']}")

    # 3. The same stamp can't land twice.
    try:
        station.land(ledger, "kestrel", after_fare, s1, fare_m)
        fail("a stamp landed twice")
    except station.Refused as e:
        if "already been stamped" not in str(e):
            fail(f"wrong reason for a second landing: {e}")

    # 2. Carried into the next Departure, on a pass carrying her as she is now.
    fresh = station.issue(ledger, "kestrel", after_fare, 902, ticket=222, seed=5)
    if passport.encode(station.boarding.decode(fresh)["character"]) != after_fare:
        fail("the pass doesn't carry her Passport as it is now")
    out, s2 = play(loop, fresh, LOOP_PICKS)
    if not s2:
        fail(f"the loop printed no Travel Stamp:\n{out[-800:]}")
        return
    after_loop, _ = station.land(ledger, "kestrel", after_fare, s2, loop_m)
    k = passport.decode(after_loop)
    stub = passport._REG["items"]["TICKET_STUB"]["id"]
    if (k["level"], k["xp"], k["debt"], list(k["pack"].values())) != (1, 15, 50100, [stub]):
        fail(f"after both trips: {k}")

    # Played again, the loop is a Rewind: the Waystation marks the pass, and landing
    # pays half its 10 XP and charges the fee (+100 from the loop, +500 for the Rewind).
    again = station.issue(ledger, "kestrel", after_loop, 902, ticket=555, seed=5)
    if not station.boarding.decode(again)["rewind"]:
        fail("a pass for a Departure she has played wasn't marked as a Rewind")
    out, s3 = play(loop, again, LOOP_PICKS)
    after_rewind, report = station.land(ledger, "kestrel", after_loop, s3, loop_m)
    k = passport.decode(after_rewind)
    if (k["xp"], k["debt"], report["rewind"]) != (20, 50700, True):
        fail(f"after a Rewind of the loop: xp {k['xp']}, debt {k['debt']}, {report}")

    # A stamp edited to claim more than the Departure gives is refused, even on a live
    # ticket; one quoting a ticket that was never issued is refused too.
    station.issue(ledger, "kestrel", after_loop, 902, ticket=333, seed=5)
    for change, reason in (({"ticket": 333, "xp": 99}, "claims more"),
                           ({"ticket": 444}, "never issued")):
        forged = station.stamp.encode(dict(station.stamp.decode(s2), **change))
        try:
            station.land(ledger, "kestrel", after_loop, forged, loop_m)
            fail(f"a forged stamp ({change}) was accepted")
        except station.Refused as e:
            if reason not in str(e):
                fail(f"wrong reason for a forged stamp ({change}): {e}")

    # 4. Overlapping trips: both passes issued from the same Passport, both land.
    for order in ("fare first", "loop first"):
        ledger = {"tickets": {}}
        pa = station.issue(ledger, "kestrel", KESTREL, 0, ticket=10, seed=1985)
        pb = station.issue(ledger, "kestrel", KESTREL, 902, ticket=20, seed=5)
        _, sa = play(fare, pa, FARE_PICKS)
        _, sb = play(loop, pb, LOOP_PICKS)
        first, second = ((sa, fare_m), (sb, loop_m)) if order == "fare first" else ((sb, loop_m), (sa, fare_m))
        now, _ = station.land(ledger, "kestrel", KESTREL, first[0], first[1])
        now, _ = station.land(ledger, "kestrel", now, second[0], second[1])
        k = passport.decode(now)
        # Receipts are changes, not snapshots: The Fare's "+50000 from where she boarded"
        # and the loop's "+100" add up to 50100 in either order.
        if (k["xp"], k["debt"], list(k["pack"].values())) != (15, 50100, [stub]):
            fail(f"overlapping trips, {order}: {k}")

    print(f"round trip: The Fare and a second Departure stamped onto one Passport, "
          f"{failures} failed")


if __name__ == "__main__":
    main()
    sys.exit(1 if failures else 0)
