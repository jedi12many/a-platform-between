"""Story VM tests.

1. Playthroughs (tests/vm/cases.txt): each Departure is compiled, played with fixed
   picks and a fixed seed, and the transcript must match tests/vm/expected/NAME.txt
   (reviewed by hand against the script; dice checked against an independent
   xorshift16). The sim65 (6502) build must produce the same transcript. A pick of
   '@name' boards a traveler from tests/vm/travelers.txt at the boarding desk.
2. Coverage: together, the playthroughs of each Departure in COVERED must run every
   instruction in it, so every route, check outcome and race or class passage has been
   played and reviewed. The only code exempt is the chapter-title preamble of a scene
   that never opens its chapter.
   Every receipt must fit its Departure's reward manifest (tools/qsc/manifest.py).
   Every check in a playthrough is also re-rolled here, from the rules in
   docs/rules-v0.md and the traveler's Passport as tools/passport reads it: the die, the
   rating and the result must all agree.
3. Damage: hundreds of corrupted copies of The Fare, half with the image hash repaired
   so the damage reaches deeper, are played by a build with AddressSanitizer and
   UndefinedBehaviorSanitizer. The VM must refuse them or stop cleanly: no crash, no
   sanitizer report, no hang.

    python3 tests/vm/run_tests.py [--update]    --update rewrites the expected files
"""

import os
import random
import re
import struct
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "qsc"))
sys.path.insert(0, os.path.join(ROOT, "tools", "registry"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))

from codegen import crc16  # noqa: E402
from image import decode, read_car, read_depot  # noqa: E402
import passport  # noqa: E402
import registry  # noqa: E402
from manifest import fits, manifest  # noqa: E402
from parse import parse  # noqa: E402

# Departures whose playthroughs must, together, run every instruction.
COVERED = ["content/s1/00-the-fare/the-fare.qs"]

BUILD = os.path.join(ROOT, "build", "vm")
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def run(cmd, timeout=60):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    return p.returncode, p.stdout, p.stderr


def compile_split(src, out):
    code, _, err = run([sys.executable, "tools/qsc/qsc.py", "build", src, "--split", out])
    if code:
        fail(f"{src} didn't compile: {err}")


def travelers():
    out = {}
    for line in open(os.path.join(ROOT, "tests", "vm", "travelers.txt")):
        if line.strip() and not line.startswith("#"):
            name, *lines = line.split()
            out[name] = lines
    return out


def cases(with_traveler=False):
    """(name, source, seed, picks) for each playthrough, with '@name' expanded.

    with_traveler: also yield who boards: a traveler's name, "kestrel" (the harness's
    built-in traveler), or None when the case types its own Passport lines.
    """
    known = travelers()
    for line in open(os.path.join(ROOT, "tests", "vm", "cases.txt")):
        if not line.strip() or line.startswith("#"):
            continue
        name, src, seed, picks = line.split()
        tokens = []
        who = None if picks.startswith(":") else "kestrel"
        for t in picks.split(","):
            if t.startswith("@"):
                if t[1:] not in known:
                    fail(f"{name}: no traveler {t[1:]} in tests/vm/travelers.txt")
                    continue
                tokens += [":" + p for p in known[t[1:]]] + [":", "1"]   # then Board
                who = t[1:]
            else:
                tokens.append(t)
        if with_traveler:
            yield name, src, seed, ",".join(tokens), who
        else:
            yield name, src, seed, ",".join(tokens)


def d100s(seed):
    """The rules' dice: xorshift16 (7, 9, 8), the top seven bits, 0..99 kept, plus one."""
    x = seed or 0xACE1
    while True:
        x ^= (x << 7) & 0xFFFF
        x ^= x >> 9
        x ^= (x << 8) & 0xFFFF
        if x >> 9 < 100:
            yield (x >> 9) + 1


def outcome(roll, total, tn):
    """docs/rules-v0.md, the core roll."""
    if roll == 1:
        return "fail"
    if total > tn:
        return "crit" if roll == 100 or (roll < 100 and roll % 11 == 0) else "success"
    if roll == 100:
        return "crit"
    return "cost" if total >= tn - 20 else "fail"


def ratings(who):
    """Every stat and skill rating of a traveler, from their Passport."""
    if who == "kestrel":
        ch = passport.create("Kestrel", "SALVAGED", "WARDEN", [70, 40, 60, 45, 35, 50],
                             "ATHLETICS")
    else:
        ch = passport.decode("".join(travelers()[who]))
    reg = passport._REG
    out = {s.upper(): v for s, v in zip(passport.STATS, ch["stats"])}
    for e in reg["skills"].values():
        out[e["display"]] = ch["stats"][e["stat"]] // 2 + ch["training"].get(e["id"], 0)
    return out


def dice(name, seed, transcript, who):
    """Re-roll every check in a transcript; returns how many there were."""
    rolls = d100s(int(seed))
    rated = ratings(who)
    n = 0
    for line in transcript.splitlines():
        m = re.match(r"\[check (\S+): (\d+)\+(-?\d+)=(-?\d+) vs (\d+): (\w+)\]$", line)
        if not m:
            continue
        n += 1
        what, roll, rating, total, tn, result = m.groups()
        want_roll = next(rolls)
        want = (want_roll, rated[what], want_roll + rated[what])
        got = (int(roll), int(rating), int(total))
        if got != want or result != outcome(want[0], want[2], int(tn)):
            fail(f"{name}: check {n} ({what}) printed {line}, but the rules give "
                 f"{want[0]}+{want[1]}={want[2]}: {outcome(want[0], want[2], int(tn))}")
    return n


def rewards(src):
    with open(os.path.join(ROOT, src), encoding="utf-8") as f:
        reg = registry.load()
        dep, _ = parse(src, f.read(), reg)
    return manifest(dep, reg)


def receipt_fits(name, src, transcript):
    """The receipt a playthrough ends with must fit its Departure's reward manifest."""
    m = re.search(r"^\[receipt: departure (\d+), \w+, xp (\d+), debt paid (\d+) added (\d+), "
                  r"gained([\d ]*), lost([\d ]*), echoes([\d= ]*)\]\n\[level \d+, xp \d+, debt (\d+)\]",
                  transcript, re.M)
    if not m:
        return 0
    dep, xp, paid, added, gained, lost, echoes, final = m.groups()
    r = {"departure": int(dep), "xp": int(xp), "debt_paid": int(paid), "debt_added": int(added),
         "gained": [int(i) for i in gained.split()], "lost": [int(i) for i in lost.split()],
         "echoes": [(int(e.split("=")[0]), int(e.split("=")[1]), 0) for e in echoes.split()]}
    why = fits(rewards(src), r, int(final) + int(paid) - int(added))
    if why:
        fail(f"{name}: the receipt claims more than the Departure can give: {why}")
    return 1


def playthroughs(update):
    for name, src, seed, picks, who in cases(with_traveler=True):
        out = os.path.join(BUILD, name)
        compile_split(src, out)
        code, native, err = run(["build/harness", out, seed, picks])
        if code or err:
            fail(f"{name}: native harness exited {code}: {err}")
            continue
        expected_path = os.path.join(ROOT, "tests", "vm", "expected", name + ".txt")
        if update:
            with open(expected_path, "w") as f:
                f.write(native)
        else:
            with open(expected_path) as f:
                expected = f.read()
            if native != expected:
                fail(f"{name}: transcript differs from tests/vm/expected/{name}.txt")
        rerolled = dice(name, seed, native, who) if who else 0
        receipt_fits(name, src, native)
        code, sim, err = run(["sim65", "build/harness.sim", out, seed, picks], timeout=600)
        if sim != native:
            fail(f"{name}: the 6502 transcript differs from the native one")
        else:
            print(f"ok  {name}: native and 6502 transcripts match"
                  + (f", {rerolled} check{'s' * (rerolled != 1)} re-rolled by the rules"
                     if rerolled else ""))


def instructions(split_dir):
    """{(car, offset): (opcode name, exempt)} for every instruction in a split image.

    Exempt: the SET and CHAPTER of a scene's chapter-title preamble (FLAG f, NOT, JZ,
    SET f, CHAPTER), which run only in the scene that opens its chapter.
    """
    with open(os.path.join(split_dir, "DEPOT"), "rb") as f:
        d = read_depot(f.read())
    out = {}
    for index in range(len({car for car, _ in d["directory"]})):
        with open(os.path.join(split_dir, f"CAR{index:02d}"), "rb") as f:
            code = read_car(f.read(), index, d["pairs"])["code"]
        starts = {off for car, off in d["directory"] if car == index}
        pos, recent = 0, []
        while pos < len(code):
            if pos in starts:
                pos, recent = pos + 2, []
                continue
            op, _, nxt = decode(code, pos)
            recent.append((pos, op))
            out[(index, pos)] = (op, False)
            if [o for _, o in recent] == ["FLAG", "NOT", "JZ", "SET", "CHAPTER"]:
                out[(index, recent[3][0])] = ("SET", True)
                out[(index, pos)] = ("CHAPTER", True)
            pos = nxt
    return out


def coverage():
    for src in COVERED:
        ran = set()
        played = 0
        for name, case_src, seed, picks in cases():
            if case_src != src:
                continue
            played += 1
            code, _, err = run(["build/harness.cov", os.path.join(BUILD, name), seed, picks])
            ran |= {tuple(map(int, line.split())) for line in err.split("\n") if line}
        listing = instructions(os.path.join(BUILD, next(n for n, s, _, _ in cases() if s == src)))
        missed = sorted(k for k, (op, exempt) in listing.items() if k not in ran and not exempt)
        chapters = {car for (car, pc), (op, _) in listing.items() if op == "CHAPTER" and (car, pc) in ran}
        cars = {car for car, _ in listing}
        for car in sorted(cars - chapters):
            fail(f"{src}: no playthrough shows car {car}'s chapter title")
        if missed:
            fail(f"{src}: {len(missed)} instructions never ran in {played} playthroughs; "
                 f"`qsc.py dump` shows them:\n    "
                 + "\n    ".join(f"car {c} at {pc}: {listing[(c, pc)][0]}" for c, pc in missed))
        else:
            print(f"ok  coverage: {played} playthroughs of {os.path.basename(src)} run every "
                  f"instruction ({len(listing)} in all)")


def damaged(rng, files):
    """Corrupt one file of a split image; sometimes repair the hash afterwards."""
    files = dict(files)
    name = rng.choice(sorted(files))
    data = bytearray(files[name])
    if rng.random() < 0.15 and len(data) > 4:
        data = data[:rng.randrange(len(data))]                 # truncated
    else:
        for _ in range(rng.randint(1, 4)):
            data[rng.randrange(len(data))] = rng.randrange(256)
    files[name] = bytes(data)
    if rng.random() < 0.5:
        try:
            d = read_depot(files["DEPOT"])
            depot = bytearray(files["DEPOT"])
            struct.pack_into("<H", depot, d["hash_at"], 0)
            cars = b"".join(files[k] for k in sorted(files) if k.startswith("CAR"))
            struct.pack_into("<H", depot, d["hash_at"], crc16(bytes(depot) + cars))
            files["DEPOT"] = bytes(depot)
        except Exception:  # noqa: BLE001 - a depot too broken to repair stays broken
            pass
    return files


def damage(count):
    src_dir = os.path.join(BUILD, "fare-edge")
    files = {}
    for n in os.listdir(src_dir):
        with open(os.path.join(src_dir, n), "rb") as f:
            files[n] = f.read()
    rng = random.Random(1985)
    out = os.path.join(BUILD, "damaged")
    os.makedirs(out, exist_ok=True)
    picks = ",".join(str(rng.randint(1, 3)) for _ in range(40))
    outcomes = {}
    env = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:abort_on_error=0",
               UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1")
    for i in range(count):
        for n in os.listdir(out):
            os.remove(os.path.join(out, n))
        for n, data in damaged(rng, files).items():
            with open(os.path.join(out, n), "wb") as f:
                f.write(data)
        try:
            p = subprocess.run(["build/harness.asan", out, "7", picks], capture_output=True,
                               text=True, timeout=20, cwd=ROOT, env=env)
        except subprocess.TimeoutExpired:
            fail(f"damaged image {i}: the VM hung")
            continue
        if p.returncode != 0 or "runtime error" in p.stderr or "Sanitizer" in p.stderr:
            fail(f"damaged image {i}: exit {p.returncode}\n{p.stderr[-2000:]}")
            continue
        last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else ""
        kind = last.split(":")[0].strip("[") if last.startswith("[") else "text"
        outcomes[kind] = outcomes.get(kind, 0) + 1
    print(f"ok  damage: {count} corrupted images, none crashed: "
          + ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items())))


def main():
    update = "--update" in sys.argv
    os.makedirs(BUILD, exist_ok=True)
    playthroughs(update)
    coverage()
    damage(int(os.environ.get("APB_DAMAGE_RUNS", "300")))
    print(f"vm tests: {failures} failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
