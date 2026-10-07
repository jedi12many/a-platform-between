"""Applying receipts: the C rules core must agree with the Python reference.

Random characters (made with tools/passport/passport.py, then aged: levels, debt, items,
Echoes) get random receipts. build/apply (core/src/receipt.c) and
tools/passport/receipt.py must produce the same Passport and the same report, natively
for every case and on sim65 for a sample. A few hand-worked cases pin the rules down. The C core's Travel Stamp
of each receipt must match tools/passport/stamp.py's, and decode back to the receipt. And
the C core's stamp decoder (apb_stamp_decode, for the Waystation) must read every stamp
the reference writes the way the reference does, and refuse the same damaged ones.

    python3 tests/receipts/check_apply.py
"""

import os
import random
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
sys.path.insert(0, os.path.join(ROOT, "tools", "registry"))

import passport  # noqa: E402
import receipt  # noqa: E402
import stamp  # noqa: E402

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def lst(xs):
    return ",".join(map(str, xs)) or "-"


def args(ch, r):
    return ([passport.encode(ch), str(r["xp"]), str(r["debt_paid"]), str(r["debt_added"]),
             lst(r["gained"]), lst(r["lost"]),
             ",".join(f"{e}:{s}:{w}" for e, s, w in r["echoes"]) or "-"]
            + (["rewind", str(r["departure"])] if r.get("rewind") else []))


def as_stamped(r):
    """The receipt build/apply stamps: Departure 7 (or the Rewind's), ticket 123456789."""
    return {"departure": r["departure"] if r.get("rewind") else 7, "ticket": 123456789,
            "outcome": 0, "xp": r["xp"], "debt_paid": r["debt_paid"],
            "debt_added": r["debt_added"], "gained": r["gained"], "lost": r["lost"],
            "echoes": r["echoes"]}


def expected(ch, r):
    after, rep = receipt.apply(ch, r, rewind=bool(r.get("rewind")))
    return (passport.encode(after) + "\n"
            + f"levels {rep['levels']} gone {rep['gone']} stored"
            + "".join(f" {i}" for i in rep["stored"]) + " shifted"
            + "".join(f" {i}" for i in rep["shifted"]) + " legend"
            + "".join(f" {e}={s}" for e, s in rep["legend"]) + "\n"
            + stamp.encode(as_stamped(r)) + "\n")


def run(binary, ch, r):
    cmd = (["sim65", binary] if binary.endswith(".sim") else [binary]) + args(ch, r)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=120).stdout


def random_character(rng):
    reg = passport._REG
    race = rng.choice(sorted(reg["races"]))
    cls = rng.choice(sorted(reg["classes"]))
    tags = reg["classes"][cls]["tags"]
    extra = rng.choice([s for s in sorted(reg["skills"]) if reg["skills"][s]["id"] not in tags])
    while True:
        stats = [25] * 6
        for _ in range(150):
            i = rng.randrange(6)
            if stats[i] < 70:
                stats[i] += 1
        if passport.pointbuy_ok(stats):
            break
    ch = passport.create("T" + str(rng.randrange(1000)), race, cls, stats, extra)
    ch["level"] = rng.choice([1, 2, 50, 98, 99, 100, rng.randint(1, 100)])
    ch["xp"] = 0 if ch["level"] == 100 else rng.randrange(100)
    ch["stat_points"] = rng.choice([0, 3, 250, 255])
    ch["skill_points"] = rng.choice([0, 7, 250, 255])
    ch["debt"] = rng.choice([0, 1, 50000, 65535, rng.randrange(65536)])
    for key, slots in (("equipped", 6), ("pack", 6)):
        for s in range(slots):
            if rng.random() < 0.5:
                ch[key][s] = rng.randint(1, 1023)
    # Often Echoes from the registry (ids 1..9, planted by Departures 1..3), so a Rewind
    # has something to forget.
    ids = rng.sample(list(range(1, 10)) + rng.sample(range(10, 1024), 12), rng.randint(0, 8))
    ch["echoes"] = [(i, rng.randint(1, 3)) for i in ids]
    return ch


def random_receipt(rng, ch):
    carried = list(ch["equipped"].values()) + list(ch["pack"].values())
    paid = rng.choice([0, 0, 1, 500, 65535])
    added = 0 if paid else rng.choice([0, 0, 50000, 65535])
    lost = [rng.choice(carried) if carried and rng.random() < 0.7 else rng.randint(1, 1023)
            for _ in range(rng.randint(0, 8))]
    gained = [rng.randint(1, 1023) for _ in range(rng.randint(0, 8))]
    held = dict(ch["echoes"])
    ids = rng.sample(sorted(set(held) | set(rng.sample(range(1, 1024), 8))), rng.randint(0, 8))
    echoes = []
    for e in ids:
        was = held.get(e, 0) if rng.random() < 0.7 else rng.randint(0, 3)
        echoes.append((e, rng.randint(1, 3), was))
    r = {"xp": rng.choice([0, 5, 99, 100, 250, 9999, 65535, rng.randrange(400)]),
         "debt_paid": paid, "debt_added": added,
         "gained": gained, "lost": lost, "echoes": echoes, "departure": 7}
    if rng.random() < 0.3:
        r["rewind"] = True
        r["departure"] = rng.randint(1, 3)
    return r


def hand_worked():
    """Small cases worked out on paper from docs/boarding.md."""
    ch = passport.create("Kestrel", "SALVAGED", "WARDEN", [70, 40, 60, 45, 35, 50], "ATHLETICS")
    ch["equipped"] = {0: 7}
    ch["pack"] = {s: 100 + s for s in range(6)}          # a full pack
    ch["echoes"] = [(4, 2)]                                # WOLF_PUP: LEFT
    ch["debt"] = 50000
    # 150 XP from level 1, 0 XP: one level, so level 2 with 50 XP. Debt 50000 - 2000 = 48000.
    # Lost 101 (pack slot 1) and 7 (equipped), 999 isn't carried. Gained 200 goes into
    # slot 1, 201 has no room. WOLF_PUP was LEFT at boarding and still is: no shift.
    # Echo 9 was 0 at boarding but is 0 now too: no shift.
    r = {"xp": 150, "debt_paid": 2000, "debt_added": 0, "gained": [200, 201],
         "lost": [101, 7, 999], "echoes": [(4, 1, 2), (9, 2, 0)]}
    after, rep = receipt.apply(ch, r)
    want = (2, 50, 48000, {}, {0: 100, 1: 200, 2: 102, 3: 103, 4: 104, 5: 105},
            [(4, 1), (9, 2)], {"levels": 1, "stored": [201], "gone": 1, "shifted": [], "legend": []})
    got = (after["level"], after["xp"], after["debt"], after["equipped"], after["pack"],
           after["echoes"], rep)
    if got != want:
        fail(f"hand-worked case: Python reference gives {got}, expected {want}")
    # Kestrel's Wits is 45 (no race or class bonus), so 1 + 45 // 20 = 3 skill points a level.
    if (after["stat_points"], after["skill_points"]) != (1, 3):
        fail(f"hand-worked case: points {after['stat_points']}, {after['skill_points']}")
    if run("build/apply", ch, r) != expected(ch, r):
        fail("hand-worked case: the C core disagrees with the reference")
    # Changed elsewhere since boarding: a co-op game set WOLF_PUP to SWORN (3) while a
    # solo Rewind, boarded with it LEFT (2), sets it SAVED (1). The receipt wins; shifted.
    ch["echoes"] = [(4, 3)]
    after, rep = receipt.apply(ch, {"xp": 0, "debt_paid": 0, "debt_added": 0, "gained": [],
                                    "lost": [], "echoes": [(4, 1, 2)]})
    if after["echoes"] != [(4, 1)] or rep["shifted"] != [4]:
        fail(f"timeline shift: {after['echoes']} {rep}")


def hand_worked_rewind():
    """A Rewind of Departure 02, worked out from docs/seasons.md."""
    ch = passport.create("Kestrel", "SALVAGED", "WARDEN", [70, 40, 60, 45, 35, 50], "ATHLETICS")
    ch["debt"] = 50000
    # MERIDIAN (planted by 01) FREED; WOLF_PUP (02) SWORN; JACE_CUTTER (02) SPARED.
    ch["echoes"] = [(1, 1), (4, 3), (5, 1)]
    # This time she left the pup (WOLF_PUP = LEFT, unset when she boarded: a Rewind
    # forgets its own Echoes) and never met Jace. 101 XP and 1001 Debt paid down.
    r = {"departure": 2, "xp": 101, "debt_paid": 1001, "debt_added": 0, "gained": [],
         "lost": [], "echoes": [(4, 2, 0)], "rewind": True}
    after, rep = receipt.apply(ch, r, rewind=True)
    # Half of 101 XP is 50; half of 1001 paid is 500, and the fee adds 500: Debt 50000.
    # MERIDIAN stays; WOLF_PUP is LEFT, not SWORN; JACE_CUTTER is unset again (so its
    # canon default applies). Nothing changed elsewhere, so no timeline shift.
    want = (1, 50, 50000, [(1, 1), (4, 2)], [])
    got = (after["level"], after["xp"], after["debt"], after["echoes"], rep["shifted"])
    if got != want:
        fail(f"hand-worked Rewind: Python reference gives {got}, expected {want}")
    if run("build/apply", ch, r) != expected(ch, r):
        fail("hand-worked Rewind: the C core disagrees with the reference")


def two_overlapping():
    """docs/engine-plan.md, E2: two receipts from overlapping Departures both land."""
    ch = passport.create("Kestrel", "SALVAGED", "WARDEN", [70, 40, 60, 45, 35, 50], "ATHLETICS")
    ch["debt"] = 50000                    # her fare, so neither order clamps at 0
    solo = {"xp": 60, "debt_paid": 100, "debt_added": 0, "gained": [11], "lost": [],
            "echoes": [(1, 1, 0)]}
    coop = {"xp": 70, "debt_paid": 0, "debt_added": 300, "gained": [12], "lost": [],
            "echoes": [(4, 3, 0)]}
    a, _ = receipt.apply(receipt.apply(ch, solo)[0], coop)
    b, _ = receipt.apply(receipt.apply(ch, coop)[0], solo)
    for name, got in (("solo then co-op", a), ("co-op then solo", b)):
        if (got["level"], got["xp"], got["debt"]) != (2, 30, 50200) \
           or sorted(got["pack"].values()) != [11, 12] or sorted(got["echoes"]) != [(1, 1), (4, 3)]:
            fail(f"overlapping receipts, {name}: {got}")
    after_c = run("build/apply", passport.decode(run("build/apply", ch, solo).split()[0]), coop)
    if after_c.split()[0] != passport.encode(a):
        fail("overlapping receipts: the C core disagrees with the reference")


def described(r):
    """A receipt as build/apply decode prints it."""
    return (f"departure {r['departure']} ticket {r['ticket']} outcome {r['outcome']} xp {r['xp']} "
            f"paid {r['debt_paid']} added {r['debt_added']} gained {lst(r['gained'])} "
            f"lost {lst(r['lost'])} echoes "
            + (",".join(f"{e}:{s}:{w}" for e, s, w in r["echoes"]) or "-"))


def decoded(binary, text):
    cmd = (["sim65", binary] if binary.endswith(".sim") else [binary]) + ["decode", text]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=120).stdout.strip()


def stamps(rng, count, sample):
    """Random receipts as stamps, whole and damaged: the C decoder against the reference."""
    damaged = refused = 0
    for i in range(count):
        ch = random_character(rng)
        r = as_stamped(random_receipt(rng, ch))
        r.update(departure=rng.randrange(65536), ticket=rng.randrange(1 << 32),
                 outcome=rng.randrange(2))
        text = stamp.encode(r)
        tries = [text]
        for _ in range(3):
            pos = rng.randrange(len(text))
            kind = rng.randrange(3)
            if kind == 0:
                bad = text[:pos] + rng.choice(passport.SYMBOLS) + text[pos + 1:]
            elif kind == 1:
                bad = text[:pos] + text[pos + 1:]
            else:
                bad = text[:pos] + rng.choice(passport.SYMBOLS) + text[pos:]
            tries.append(bad)
        for j, t in enumerate(tries):
            try:
                want = described(stamp.decode(t))
            except passport.PassportError:
                want = None
            for binary in (["build/apply", "build/apply.sim"] if i < sample and j == 0
                           else ["build/apply"]):
                got = decoded(binary, t)
                if want is None and not got.startswith("refused"):
                    fail(f"stamp {i}.{j} on {binary}: the reference refuses {t}, the C core reads {got}")
                elif want is not None and got != want:
                    fail(f"stamp {i}.{j} on {binary}: {t}\n  C:      {got}\n  Python: {want}")
            damaged += j > 0
            refused += j > 0 and want is None
    print(f"stamps: {count} decoded by the C core as by the reference ({sample} also on the "
          f"6502); {damaged} damaged copies, {refused} refused by both")


def main():
    hand_worked()
    hand_worked_rewind()
    two_overlapping()
    rng = random.Random(2026)
    count, sample = int(os.environ.get("APB_RECEIPT_RUNS", "400")), 25
    for i in range(count):
        ch = random_character(rng)
        r = random_receipt(rng, ch)
        want = expected(ch, r)
        for binary in (["build/apply", "build/apply.sim"] if i < sample else ["build/apply"]):
            got = run(binary, ch, r)
            if got.splitlines()[-1:] and binary == "build/apply":
                back = stamp.decode(got.splitlines()[-1])
                if back != as_stamped(r):
                    fail(f"case {i}: the stamp decodes to {back}, not the receipt {r}")
            if got != want:
                fail(f"case {i} on {binary}: {' '.join(args(ch, r))}\n"
                     f"  C:      {got!r}\n  Python: {want!r}")
                break
    stamps(rng, int(os.environ.get("APB_STAMP_RUNS", "300")), 10)
    print(f"receipts: {count} random receipts checked against the reference "
          f"({sample} also on the 6502), {failures} failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
