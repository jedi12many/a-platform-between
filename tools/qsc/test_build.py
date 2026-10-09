"""Tests for the code generator, text compression and image verifier.

- A small script must compile to bytecode assembled by hand from docs/vm-spec.md.
- Every clean fixture and every Departure in content/ must build, pass the verifier, and
  have every string decompress to exactly what the compiler meant to store.
- Compression must round-trip and obey the pair rules.
- The verifier must refuse damaged images with BadImage, never crash.
- Limits only the code generator can see (flags, car size) must be reported.
- Reward manifests: The Fare's is checked against a hand reading of the script, receipts
  that claim too much are refused, and more than 32 reward commands is an error.
"""

import glob
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "registry"))

import registry  # noqa: E402
from codegen import CompileError, compile_departure, crc16  # noqa: E402
from image import BadImage, read_car, split_apd, verify  # noqa: E402
from manifest import ManifestError, fits, manifest  # noqa: E402
from parse import parse  # noqa: E402
from textpack import compress, expand  # noqa: E402

REG = registry.load()
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def build(source, name="test.qs"):
    dep, diag = parse(name, source, REG)
    if diag.errors:
        raise AssertionError(f"{name}: {diag.errors}")
    return compile_departure(dep, REG)


# ---------------------------------------------------------------- hand-assembled

TINY = """title: Tiny
id: 901
kind: branch
realm: tl 1, ml 2
levels: 1-2
start: a

flag f

== a
Hi {name}.
* {f} [Go] -> b
+ [Stay]
    ~ set f

== b
check TECH hard
    success: Yes.
~ end complete
"""

# Car 0 code, assembled by hand from docs/vm-spec.md. Flag 0 is f; flag 1 is the
# compiler's once-only flag for "* [Go]". Strings: 0 "Hi {name}.", 1 "Go", 2 "Stay",
# 3 "Yes.". TECH is skill 6, so RATING 16 + 6 = 22; 'hard' is TN 120.
TINY_CODE = [
    # scene a at 0
    "05 00",            # 0   menu offset: the menu block is at 0 + 5
    "10 00 00",         # 2   TEXT "Hi {name}."
    "18",               # 5   MENU_CLEAR
    "22 01 00",         # 6   FLAG 1          once-only flag for "Go"
    "38",               # 9   NOT
    "02 18 00",         # 10  JZ 24           already picked: skip
    "22 00 00",         # 13  FLAG 0          {f}
    "02 18 00",         # 16  JZ 24
    "19 01 00 1E 00",   # 19  OPTION "Go" -> 30
    "19 02 00 24 00",   # 24  OPTION "Stay" -> 36
    "1A",               # 29  MENU
    "40 01 00",         # 30  SET 1           "Go" is used up
    "03 01 00",         # 33  GOTO scene 1
    "40 00 00",         # 36  SET 0           ~ set f
    "01 05 00",         # 39  JMP 5           back to the menu
    # scene b at 42
    "FF FF",            # 42  no menu
    "39 16 78",         # 44  CHECK skill TECH, TN 120
    "04 3E 00 3E 00 38 00 38 00",  # 47 SWITCH4 fail->62 cost->62 success->56 crit->56
    "10 03 00",         # 56  TEXT "Yes."
    "01 3E 00",         # 59  JMP 62
    "05 00",            # 62  END complete
]


def test_hand_assembled():
    image = build(TINY)
    want = bytes.fromhex(" ".join(TINY_CODE))
    car = read_car(image.cars[0], 0, image.pairs)
    if car["code"] != want:
        fail("Tiny: code differs from the hand assembly\n"
             f"  want {want.hex(' ')}\n  got  {car['code'].hex(' ')}")
    if car["strings"] != [b"Hi \x01.", b"Go", b"Stay", b"Yes."]:
        fail(f"Tiny strings: {car['strings']}")
    d = image.depot
    # magic, version, kind=branch, id 901, season 0, TL 1, ML 2, levels 1-2,
    # 2 flags, 0 vars, 2 scenes, start 0
    head = struct.unpack_from("<2sBBHBBBBBHBHH", d, 0)
    if head != (b"DP", 0, 1, 901, 0, 1, 2, 1, 2, 2, 0, 2, 0):
        fail(f"Tiny depot header: {head}")
    if len(image.cars) != 1 or car["title"] != 0xFFFF:
        fail("Tiny: one untitled car")


# ------------------------------------------------------------- whole images

def check_image(path):
    with open(path, encoding="utf-8") as f:
        image = build(f.read(), path)
    data = image.apd()
    rel = os.path.relpath(path, ROOT)
    try:
        d, cars = verify(data, REG)
    except BadImage as e:
        fail(f"{rel}: verifier refused it: {e}")
        return
    for car, compiled in zip(cars, image.compiler.cars):
        if car["strings"] != compiled.strings:
            fail(f"{rel}: car {car['index']} strings don't survive compression")
    files = image.files()
    if split_apd(data) != (files["DEPOT"], [files[f"CAR{i:02d}"] for i in range(len(cars))]):
        fail(f"{rel}: the split files differ from the .apd")


# -------------------------------------------------------------- compression

def test_compression():
    rng = random.Random(7)
    strings = [bytes(rng.choice(b"etaoin shrdlu.,'") for _ in range(rng.randint(0, 80)))
               for _ in range(300)]
    strings += [b"", b"a" * 200, b"ab" * 100, b"\x05\x01 {var}", b"\x01\x02\x03\x0a"]
    pairs, packed = compress(strings)
    for i, (a, b) in enumerate(pairs):
        if a >= 0x80 + i or b >= 0x80 + i:
            fail(f"pair {i} refers forward")
    if any(expand(p, pairs) != s for p, s in zip(packed, strings)):
        fail("compression doesn't round-trip")
    if any(b"\x00" in p for p in packed):
        fail("compressed text contains a 0x00 byte")
    # A long run nests pairs deeply; depth must stay within the limit.
    pairs, packed = compress([b"x" * 5000], max_depth=4)
    if expand(packed[0], pairs, max_depth=4) != b"x" * 5000:
        fail("deep nesting round-trip")
    try:
        expand(packed[0], pairs, max_depth=3)
        fail("expand should refuse nesting deeper than its limit")
    except ValueError:
        pass


# ------------------------------------------------------------------- limits

def test_limits():
    header = ("title: Limits\nid: 960\nkind: branch\nrealm: tl 1, ml 1\nlevels: 1-1\n"
              "start: a\n\n")
    flags = "".join(f"flag f{i}\n" for i in range(511))
    uses = "".join(f"~ set f{i}\n" for i in range(511))
    src = header + flags + "\n== a\n" + uses + "* [One] -> a\n* [Two] -> a\n"
    try:
        build(src)
        fail("511 flags + 2 once-only choices should run out of flags")
    except CompileError as e:
        if "more than 512 flags" not in str(e):
            fail(f"flag limit message: {e}")

    rng = random.Random(3)
    junk = "".join(" ".join("".join(rng.choice("bcdfghjkmpqvwxz") for _ in range(9))
                            for _ in range(8)) + "\n\n" for _ in range(300))
    try:
        build(header + "=== Huge\n\n== a\n" + junk + "~ end complete\n")
        fail("a chapter of 20 KB of text should be too big")
    except CompileError as e:
        if "Split it into two chapters" not in str(e):
            fail(f"car size message: {e}")


# ----------------------------------------------------------------- the verifier

def test_verifier_never_crashes():
    with open(os.path.join(ROOT, "content", "s1", "00-the-fare", "the-fare.qs")) as f:
        good = build(f.read()).apd()
    rng = random.Random(11)
    for _ in range(400):
        data = bytearray(good)
        for _ in range(rng.randint(1, 4)):
            data[rng.randrange(len(data))] = rng.randrange(256)
        repaired = rng.random() < 0.5
        if repaired:
            # Fix up the hash, so damage deeper in is reached too.
            try:
                depot, cars = split_apd(bytes(data))
                from image import read_depot
                at = read_depot(depot)["hash_at"]
                z = bytearray(depot)
                struct.pack_into("<H", z, at, 0)
                struct.pack_into("<H", z, at, crc16(bytes(z) + b"".join(cars)))
                start = 8 + 2 * len(cars)
                data[start:start + len(depot)] = z
            except BadImage:
                pass
        try:
            verify(bytes(data), REG)
            # With the hash repaired, damage can leave a valid image (one letter of
            # text changed into another). Without it, any change must be caught.
            if not repaired and bytes(data) != good:
                fail("a damaged image with a stale hash was accepted")
        except BadImage:
            pass
        except Exception as e:  # noqa: BLE001
            fail(f"verifier crashed on a damaged image: {type(e).__name__}: {e}")
            return

    # A Branch Line image may not contain official-only opcodes.
    official = build(TINY.replace("kind: branch", "kind: official\nseason: 1")
                     .replace("~ end complete", "~ debt - 5\n~ end complete")).apd()
    depot, cars = split_apd(official)
    z = bytearray(depot)
    z[3] = 1                                   # kind := branch
    from image import read_depot
    at = read_depot(bytes(z))["hash_at"]
    struct.pack_into("<H", z, at, 0)
    struct.pack_into("<H", z, at, crc16(bytes(z) + b"".join(cars)))
    tampered = official[:8 + 2 * len(cars)] + bytes(z) + b"".join(cars)
    try:
        verify(tampered, REG)
        fail("a Branch Line image with DEBT should be refused")
    except BadImage as e:
        if "DEBT" not in str(e):
            fail(f"wrong reason: {e}")


def test_encounters():
    """An encounter record assembled by hand from docs/vm-spec.md."""
    src = TINY.replace("flag f\n", "flag f\n\nmap pen\n    @.a\n    #.>\n    a = ASH_RAT\n") \
        .replace("+ [Stay]\n    ~ set f", "+ [Stay]\n    ~ set f\n    fight pen ambush\n        won: Done.")
    img = build(src)
    # 3 x 2; squares @ . a / # . > are open open open / wall open exit: 0 0 0 1 0 7,
    # two to a byte. One start at 0,0. One foe at 2,0: the ash rat's numbers from
    # registry/foes.txt, Dodge = Grace 50 / 5 = 10, no weakness (255), charge, coward;
    # then its name, "Ash rat", length first.
    want = bytes([3, 2, 0x00, 0x01, 0x07, 1, 0, 0, 1, 2, 0,
                  6, 50, 10, 0, 0, 0, 6, 30, 2, 0, 0, 0, 0, 255, 0, 1]) + b"\x07Ash rat"
    from image import read_depot
    tail = img.depot[-(len(want) + 3):]
    if tail != bytes([1]) + struct.pack("<H", len(want)) + want:
        fail(f"encounter record: {tail.hex()} instead of 01 {len(want):02x}00 {want.hex()}")
    code = bytes(img.cars[0])
    if bytes([0x3A, 0, 1]) not in code:
        fail("FIGHT 0, ambush (3A 00 01) isn't in the code")
    healed = bytes(build(TINY.replace("~ set f", "~ set f ~ heal full ~ heal 7")).cars[0])
    if bytes([0x4D, 255, 0x4D, 7]) not in healed:
        fail("~ heal full and ~ heal 7 aren't HEAL 255 and HEAL 7 (4D FF 4D 07)")
    e = read_depot(img.depot)["encounters"][0]
    if (e["w"], e["h"], e["starts"], e["foes"][0]["x"]) != (3, 2, [(0, 0)], 2):
        fail(f"encounter read back as {e}")


def test_yards():
    """The Deep Yards' instructions, assembled by hand from docs/vm-spec.md."""
    src = (TINY.replace("kind: branch", "kind: siding")
           .replace("flag f\n", "flag f\nvar floor = 3\nvar room = 0\n\nyard pit\n    ASH_RAT\n")
           .replace("Hi {name}.", "Yard {yard}.")
           .replace("+ [Stay]\n    ~ set f",
                    "+ [Stay]\n    ~ set f ~ pick room 4 on floor ~ pick room 9\n"
                    "    fight yard pit on floor sneak\n        won: Done."))
    img = build(src)
    code = bytes(img.cars[0])
    # PICK var 1 (room), from 4, keyed by var 0 (floor), salt 0; then from 9, no key
    # (FF), salt 1. FIGHT_YARD encounter 0, sneak (2), floor in var 0.
    for what, want in (("PICK 1, 4, 0, 0", "45 01 04 00 00"), ("PICK 1, 9, FF, 1", "45 01 09 ff 01"),
                       ("FIGHT_YARD 0, 2, 0", "3b 00 02 00")):
        if bytes.fromhex(want) not in code:
            fail(f"{what} ({want}) isn't in the code")
    # The depot says Siding (kind 2), and "{yard}" is insert 07.
    if img.depot[3] != 2:
        fail(f"a Siding's depot kind is {img.depot[3]}, not 2")
    from image import read_depot, read_car
    d = read_depot(img.depot)
    strings = read_car(bytes(img.cars[0]), 0, d["pairs"])["strings"]
    if not any(s.startswith(b"Yard \x07") for s in strings):
        fail("'Yard {yard}.' doesn't start 'Yard ' 07")
    # The pool: one start, then the rat, in a row on a 2 x 1 map.
    e = d["encounters"][0]
    if (e["w"], e["h"], e["starts"], [f["name"] for f in e["foes"]]) != (2, 1, [(0, 0)], ["Ash rat"]):
        fail(f"the yard's pool read back as {e}")


def test_manifests():
    path = os.path.join(ROOT, "content", "s1", "00-the-fare", "the-fare.qs")
    with open(path, encoding="utf-8") as f:
        dep, _ = parse(path, f.read(), REG)
    m = manifest(dep, REG)
    # Read off the script: `~ xp 5` once, `~ give TICKET_STUB` on the edge's crit,
    # `~ give PORTERS_HOOK` in Lost Property, `~ debt = 50000` at the ledger, no Echoes.
    want = {"departure": 0, "title": "The Fare", "kind": "official", "levels": [1, 1],
            "xp": 5, "items": [{"id": REG["items"]["TICKET_STUB"]["id"], "name": "TICKET_STUB",
                                "most": 1},
                               {"id": REG["items"]["PORTERS_HOOK"]["id"], "name": "PORTERS_HOOK",
                                "most": 1}],
            "echoes": [], "debt": {"set": [50000], "add": 0, "pay": 0}}
    if m != want:
        fail(f"The Fare's manifest: {m}")
    stub = REG["items"]["TICKET_STUB"]["id"]
    hook = REG["items"]["PORTERS_HOOK"]["id"]
    sabre = REG["items"]["RUSTED_SABRE"]["id"]
    ok = {"departure": 0, "xp": 5, "debt_paid": 0, "debt_added": 50000, "gained": [stub, hook],
          "lost": [], "echoes": []}
    if fits(m, ok, 0):
        fail(f"a fair receipt for The Fare was refused: {fits(m, ok, 0)}")
    for why, change, boarded in (
            ("more XP", {"xp": 6}, 0),
            ("a second stub", {"gained": [stub, stub]}, 0),
            ("a second hook", {"gained": [stub, hook, hook]}, 0),
            ("an item it never gives", {"gained": [sabre]}, 0),
            ("an Echo it never sets", {"echoes": [(4, 1, 0)]}, 0),
            ("Debt paid it can't pay", {"debt_added": 0, "debt_paid": 100}, 50000),
            ("Debt beyond the ledger", {"debt_added": 50001}, 0),
            ("another Departure", {"departure": 1}, 0)):
        bad = dict(ok, **change)
        if not fits(m, bad, boarded):
            fail(f"a receipt with {why} should be refused")
    # Setting Debt to 50000 from 60000 pays 10000: that fits.
    if fits(m, dict(ok, debt_added=0, debt_paid=10000), 60000):
        fail("setting Debt down to the fare should fit")

    many = TINY.replace("+ [Stay]\n    ~ set f", "+ [Stay]\n" + "    ~ xp 1\n" * 33)
    dep, diag = parse("many.qs", many, REG)
    try:
        manifest(dep, REG)
        fail("33 reward commands should be refused")
    except ManifestError as e:
        if "the most is 32" not in str(e):
            fail(f"wrong message for too many rewards: {e}")


def test_music():
    """`~ music`, assembled by hand from docs/vm-spec.md: MUSIC (14) takes the tune's index
    in the depot's music list, or FF for off; a Departure with music has a v1 depot,
    whose music list follows the encounters."""
    src = TINY.replace("+ [Stay]\n    ~ set f",
                       "+ [Stay]\n    ~ set f ~ music night_train ~ music off ~ music dawn"
                       " ~ music night_train")
    img = build(src)
    code = bytes(img.cars[0])
    if bytes.fromhex("14 00 14 ff 14 01 14 00") not in code:
        fail(f"MUSIC 0, FF, 1, 0 isn't in the code: {code.hex(' ')}")
    d = img.depot
    if d[2] != 1:
        fail(f"a Departure with music has depot version {d[2]}, not 1")
    tail = bytes([2, 11]) + b"night_train" + bytes([4]) + b"dawn"
    if not d.endswith(b"\x00" + tail):
        fail(f"the depot should end with no encounters, then the music list: {d[-24:].hex(' ')}")
    if build(TINY).depot[2] != 0:
        fail("a Departure without music should keep a v0 depot")
    data = img.apd()
    try:
        verify(data, REG)
    except BadImage as e:
        fail(f"the verifier refused an image with music: {e}")


test_hand_assembled()
test_music()
test_encounters()
test_yards()
test_manifests()
for p in sorted(glob.glob(os.path.join(ROOT, "tests", "qsc", "ok", "*.qs")) +
                glob.glob(os.path.join(ROOT, "content", "**", "*.qs"), recursive=True)):
    check_image(p)
test_compression()
test_limits()
test_verifier_never_crashes()

print(f"build tests: {failures} failed")
sys.exit(1 if failures else 0)
