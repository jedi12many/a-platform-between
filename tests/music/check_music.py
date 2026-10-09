"""make test-music (docs/music.md): the three music players must write the same registers.

The Python reference (tools/music/player.py) plays every tune in content/ and in
tests/music/, alone and under a script of commands (change, fade out, effects, volume);
the C player (client/music.c, built with the sanitizers as build/music_trace) and the
6502 player (fe/c64/music.s, from build/c64/apb.prg, on py65) must write the same 25
registers, frame by frame. Damaged files must agree too, and never crash the C player.
No frame of a real tune may take the 6502 more than BUDGET cycles: the raster interrupt
plays it, under the screen.
"""

import glob
import os
import random
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "music"))
sys.path.insert(0, HERE)
import musicc  # noqa: E402
import player  # noqa: E402
import c64_trace  # noqa: E402

TRACE = os.path.join(ROOT, "build", "music_trace")
PRG = os.path.join(ROOT, "build", "c64", "apb.prg")
DBG = os.path.join(ROOT, "build", "c64", "apb.dbg")
FRAMES = 400
BUDGET = 10000      # 6502 cycles a frame a real tune may take: half a PAL frame (docs/c64.md)


def scripts(tunes):
    """Command scripts for a file with this many tunes: {frame: [(command, arg)]}."""
    other = 1 % tunes
    return [
        {},
        {60: [("effect", 0)], 70: [("effect", 2)], 150: [("volume", 6)], 200: [("volume", 15)]},
        {80: [("change", other)], 81: [("effect", 1)]},
        {40: [("change", 255)], 45: [("effect", 3)], 150: [("start", 0)]},
        {30: [("change", 255)], 33: [("change", other)], 200: [("start", tunes)]},
        {0: [("volume", 0)], 10: [("effect", 5)], 11: [("effect", 4)], 90: [("start", 255)]},
    ]


def c_trace(path, tune, frames, script):
    args = [TRACE, path, str(tune), str(frames)]
    for f, cmds in script.items():
        args += [f"{f}:{c}:{a}" for c, a in cmds]
    out = subprocess.run(args, capture_output=True, text=True)
    if out.returncode:
        raise RuntimeError(f"music_trace failed ({out.returncode}): {out.stderr.strip()}")
    return [[int(x, 16) for x in line.split()] for line in out.stdout.splitlines()]


def c64_run(data, tune, frames, script):
    p = c64_trace.C64Player(PRG, DBG, data)
    p.call("music_command", 1, tune)
    out, most = [], 0
    for f in range(frames):
        for c, a in script.get(f, []):
            p.call("music_command", c64_trace.COMMANDS[c], a)
        out.append(p.frame())
        most = max(most, p.cycles)
    return out, most


def first_difference(a, b):
    for f, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f, x, y
    if len(a) != len(b):
        return min(len(a), len(b)), None, None
    return None


def compare(name, data, tune, frames, script, tmp, failures, worst, budget=None):
    path = os.path.join(tmp, "t.mu")
    with open(path, "wb") as f:
        f.write(data)
    ref = player.trace(data, tune, frames, script)
    try:
        c = c_trace(path, tune, frames, script)
    except RuntimeError as e:
        failures.append(f"{name}: {e}")
        return
    six, most = c64_run(data, tune, frames, script)
    worst[0] = max(worst[0], most)
    if budget and most > budget:
        failures.append(f"{name}: a frame takes the 6502 {most} cycles; the most is {budget}")
    for who, got in (("C", c), ("6502", six)):
        d = first_difference(ref, got)
        if d:
            f, x, y = d
            failures.append(f"{name}: the {who} player differs at frame {f}:\n"
                            f"  reference {' '.join(f'{r:02x}' for r in x or [])}\n"
                            f"  {who:9} {' '.join(f'{r:02x}' for r in y or [])}")
            return


def damaged(data, rng):
    d = bytearray(data)
    how = rng.randrange(4)
    if how == 0:
        return bytes(d[:rng.randrange(len(d))])
    if how == 1:
        for _ in range(rng.randint(1, 4)):
            d[rng.randrange(len(d))] = rng.randrange(256)
        return bytes(d)
    if how == 2:
        i = rng.randrange(8, len(d))
        d[i] = rng.choice([0x00, 0x7F, 0x80, 0xC0, 0xE0, 0xFE, 0xFF])
        return bytes(d)
    return bytes(d) + bytes(rng.randrange(256) for _ in range(rng.randint(1, 40)))


def main():
    sources = sorted(glob.glob(os.path.join(ROOT, "content", "**", "*.music"), recursive=True)
                     + glob.glob(os.path.join(HERE, "*.music"))
                     + glob.glob(os.path.join(ROOT, "tools", "music", "*.music")))
    failures, worst, runs = [], [0], 0
    files = []
    with tempfile.TemporaryDirectory() as tmp:
        for src in sources:
            name = os.path.relpath(src, ROOT)
            try:
                data, _ = musicc.build(open(src).read())
            except musicc.MusicError as e:
                failures.append(f"{name}: {e}")
                continue
            if not player.Player(data).ok:
                failures.append(f"{name}: the reference player refuses the compiled file")
                continue
            files.append((name, data))
            for tune in range(data[3]):
                for k, script in enumerate(scripts(data[3])):
                    compare(f"{name} tune {tune} script {k}", data, tune, FRAMES, script, tmp,
                            failures, worst, BUDGET)
                    runs += 1
        real = worst[0]
        rng = random.Random(1541)
        for name, data in files:
            # Many damaged copies of the tests' file, written to reach every rule; fewer
            # of each Departure's.
            for n in range(150 if name.startswith("tests") else 40):
                bad = damaged(data, rng)
                tune = rng.randrange(max(1, data[3]))
                script = scripts(max(1, data[3]))[n % 6]
                compare(f"{name} damaged #{n} ({len(bad)} bytes)", bad, tune, 200, script, tmp,
                        failures, worst)
                runs += 1
    if failures:
        for f in failures[:10]:
            print("FAIL", f)
        print(f"{len(failures)} of {runs} runs failed")
        return 1
    print(f"test-music: {runs} runs from {len(files)} files: Python, C and 6502 agree "
          f"(most 6502 cycles in a frame: {real}; on a damaged file, {worst[0]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
