"""Story VM tests.

1. Playthroughs (tests/vm/cases.txt): each Departure is compiled, played with fixed
   picks and a fixed seed, and the transcript must match tests/vm/expected/NAME.txt
   (reviewed by hand against the script; dice checked against an independent
   xorshift16). The sim65 (6502) build must produce the same transcript.
2. Damage: hundreds of corrupted copies of The Fare, half with the image hash repaired
   so the damage reaches deeper, are played by a build with AddressSanitizer and
   UndefinedBehaviorSanitizer. The VM must refuse them or stop cleanly: no crash, no
   sanitizer report, no hang.

    python3 tests/vm/run_tests.py [--update]    --update rewrites the expected files
"""

import os
import random
import struct
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "qsc"))
sys.path.insert(0, os.path.join(ROOT, "tools", "registry"))

from codegen import crc16  # noqa: E402
from image import read_depot  # noqa: E402

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


def playthroughs(update):
    for line in open(os.path.join(ROOT, "tests", "vm", "cases.txt")):
        if not line.strip() or line.startswith("#"):
            continue
        name, src, seed, picks = line.split()
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
        code, sim, err = run(["sim65", "build/harness.sim", out, seed, picks], timeout=600)
        if sim != native:
            fail(f"{name}: the 6502 transcript differs from the native one")
        else:
            print(f"ok  {name}: native and 6502 transcripts match")


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
    damage(int(os.environ.get("APB_DAMAGE_RUNS", "300")))
    print(f"vm tests: {failures} failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
