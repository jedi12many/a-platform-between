"""The modern front end plays the same game as the C64 (milestone E6, fe/modern/).

    python3 tests/modern/check_modern.py [--web]

Each route the C64 is tested on (tests/c64/*.choices) is played on the desktop build
(build/apb-modern, from a choices file, with no window) and must give the C64's reviewed
transcript (tests/c64/*.expected), except where the two machines are meant to differ:
the C64 has no ~ (its chapter titles read "- The Static -"), and it names its pictures
by their files (pic00, ...). A trip without a Boarding Pass takes its dice from the
clock, which reads 0 in the C64's emulator, so the desktop plays with --seed 0. So the
Travel Stamps are the C64's, and the terminal's. A
save is made on the desktop, the program stops, and a new one picks up the trip.

The sound effects (client/sfx.c, fe/modern/sound.c), written as WAV files with
--sounds, must each sound and fade out within two seconds, all differ, and have the
pitch the SID gives them: a steady tone's frequency register is its pitch byte times
256, and a PAL C64's SID plays register value F at F x 985248 / 2^24 Hz.

With --web, the browser build (build/web/, in headless Chromium through Playwright,
tests/modern/check_web.cjs) must give the desktop's transcript, line for line, on the
same routes; its save survives the page being reloaded. Then real keys and clicks.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "qsc"))
from image import read_depot  # noqa: E402

# (name, Departure, choices, choices after switching off, the C64's transcript)
ROUTES = [
    ("fare-edge", "the-fare", "fare-edge.choices", None, "fare-edge.expected"),
    ("fare-fight", "the-fare", "fare-fight.choices", "fare-resume.choices", "fare-fight.expected"),
    ("e18-loop", "eighteen-minutes", "e18-loop.choices", None, "e18-loop.expected"),
    ("yards", "deep-yards", "yards.choices", None, "yards.expected"),
]
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def desktop(departure, choices, then):
    """The desktop build's transcript, in a copy of the Departure (saves land there)."""
    with tempfile.TemporaryDirectory() as tmp:
        where = os.path.join(tmp, departure)
        shutil.copytree(os.path.join(ROOT, "build", "modern", departure), where)
        out = []
        for i, f in enumerate([choices] + ([then] if then else [])):
            if i:
                out.append("[switched off and on again]\n")
            p = subprocess.run([os.path.join(ROOT, "build", "apb-modern"), "--seed", "0",
                                "--choices", os.path.join(ROOT, "tests", "c64", f), where],
                               capture_output=True, text=True, timeout=120)
            if p.returncode:
                fail(f"apb-modern stopped with {p.returncode}: {p.stderr.strip()}")
            out.append(p.stdout)
        return "".join(out)


def like_the_c64(text, departure):
    """The desktop's transcript as the C64 shows it: '-' for '~', pictures by file."""
    with open(os.path.join(ROOT, "build", "modern", departure, "DEPOT"), "rb") as f:
        names = read_depot(f.read()).get("pictures", [])
    lines = []
    for line in text.splitlines():
        m = re.fullmatch(r"\[picture (\w+)\]", line)
        if m:
            line = f"[picture pic{names.index(m.group(1)):02d}]"
        elif line == "[the trip is over]":
            line = "[the program ended]"
        lines.append(line.replace("~", "-"))
    return lines


def sounds():
    import struct
    import wave
    with tempfile.TemporaryDirectory() as tmp:
        p = subprocess.run([os.path.join(ROOT, "build", "apb-modern"), "--sounds", tmp],
                           capture_output=True, text=True, timeout=60)
        if p.returncode:
            fail(f"apb-modern --sounds: {p.stderr.strip()}")
            return
        heard = []
        for n in range(8):
            with wave.open(os.path.join(tmp, f"sfx{n}.wav")) as w:
                rate, count = w.getframerate(), w.getnframes()
                data = struct.unpack(f"<{count}h", w.readframes(count))
            heard.append(data)
            if not 0.02 < count / rate < 2 or max(abs(v) for v in data) < 1000:
                fail(f"sound {n}: {count / rate:.3f} s, peak {max(abs(v) for v in data)}")
            elif max(abs(v) for v in data[-3:]) > 300:
                fail(f"sound {n} stops with a click, not a fade")
        if len(set(heard)) != 8:
            fail("two sound effects are the same")
        # Steady tones: select (triangle, pitch $28) and no (sawtooth, pitch $06). Their
        # pitch, counted from the samples: how often the wave rises through its middle.
        for n, pitch in ((6, 0x28), (7, 0x06)):
            data = heard[n]
            ups = [i for i in range(1, len(data)) if data[i - 1] < 0 <= data[i]]
            if len(ups) < 3:
                fail(f"sound {n}: too short to hear its pitch")
                continue
            got = (len(ups) - 1) * 44100 / (ups[-1] - ups[0])
            want = pitch * 256 * 985248 / 2 ** 24
            if abs(got - want) > want * 0.03:
                fail(f"sound {n}: {got:.1f} Hz, where the SID plays {want:.1f} Hz")
    print("ok  the sound effects: eight, each fading out, at the SID's pitches")


def main(argv):
    web = "--web" in argv
    sounds()
    for name, departure, choices, then, expected in ROUTES:
        got = desktop(departure, choices, then)
        with open(os.path.join(ROOT, "tests", "c64", expected)) as f:
            c64 = f.read().splitlines()
        mine = like_the_c64(got, departure)
        if mine != c64:
            diff = next(i for i, (a, b) in enumerate(zip(mine + [""] * len(c64), c64 + [""] * len(mine)))
                        if a != b)
            fail(f"{name}: the desktop differs from tests/c64/{expected} at line {diff + 1}: "
                 f"{mine[diff] if diff < len(mine) else '(nothing)'!r} against "
                 f"{c64[diff] if diff < len(c64) else '(nothing)'!r}")
        elif any(len(line) > 40 for line in mine):
            fail(f"{name}: a line over 40 columns")
        else:
            print(f"ok  {name}: the desktop plays it as the C64 does ({len(mine)} lines)")
        if not web:
            continue
        p = subprocess.run(["node", os.path.join(ROOT, "tests", "modern", "check_web.cjs"), "play",
                            departure, os.path.join(ROOT, "tests", "c64", choices)]
                           + ([os.path.join(ROOT, "tests", "c64", then)] if then else []),
                           capture_output=True, text=True, timeout=900)
        if p.returncode:
            fail(f"{name}: the browser build: {p.stderr.strip()}")
        elif p.stdout != got:
            fail(f"{name}: the browser's transcript differs from the desktop's")
        else:
            print(f"ok  {name}: the browser plays it as the desktop does")
    if web:
        p = subprocess.run(["node", os.path.join(ROOT, "tests", "modern", "check_web.cjs"), "keys"],
                           capture_output=True, text=True, timeout=600)
        sys.stdout.write(p.stdout)
        if p.returncode:
            fail(p.stderr.strip())
    print(f"modern tests: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
