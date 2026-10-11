"""The art desk (tools/artdesk/, docs/art.md) in headless Chromium, on a copy of the art.

    NODE_PATH=$(npm root -g) python3 tests/artdesk/check_artdesk.py     (make test-art)

1. content/art/ keeps every rule (tools/art.py), and the battle graphics build from it.
2. Opened and saved untouched, every file comes back byte for byte.
3. Each edit (a dot painted, painted and undone, a colour chosen, a new tile with a box
   drawn on it, a flood fill, flips and shifts that cancel out, art pasted as text: a new
   figure trimmed or squeezed to size, and pasted into one) lands in the file exactly as
   worked out here from the file's own text, and nothing else changes; the result is one
   tools/art.py accepts, and the graphics still build from it.
4. The server writes nothing that breaks a rule, and nothing but the art files.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import art  # noqa: E402

PORT = 8073
URL = f"http://localhost:{PORT}/"
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def ok(msg):
    print("ok  ", msg)


def desk(*args):
    out = subprocess.run(["node", os.path.join(ROOT, "tests", "artdesk", "desk.cjs"), URL] +
                         [str(a) for a in args], capture_output=True, text=True, timeout=120)
    text = out.stdout + out.stderr
    if out.returncode or "page error" in text or "error:" in text:
        fail(f"desk {' '.join(map(str, args))}: {text.strip()}")
    return text


def read(folder, name):
    with open(os.path.join(folder, name + ".txt")) as f:
        return f.read()


def with_dot(text, name, entry, x, y, c):
    """The file's text with one dot of an entry changed: worked out on the text itself."""
    lines = text.split("\n")
    at = next(i for i, ln in enumerate(lines) if ln.split()[1:2] == [entry]
              and not ln.startswith("#") and len(ln.split()) == 3) + 1 + y
    lines[at] = lines[at][:x] + c + lines[at][x + 1:]
    return "\n".join(lines)


def builds(folder):
    """The battle graphics build from the art in `folder`."""
    out = tempfile.mkdtemp()
    env = dict(os.environ, APB_ART=folder)
    p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "battlegfx.py"),
                        os.path.join(out, "b.bgfx"), "--cart16", os.path.join(out, "t16")],
                       capture_output=True, text=True, env=env)
    shutil.rmtree(out)
    return p.returncode == 0, p.stdout + p.stderr


def put(name, text):
    req = urllib.request.Request(URL + "art/" + name, data=text.encode(), method="PUT")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    problems = art.check_all()
    if problems:
        fail("content/art/: " + "; ".join(problems))
    built, said = builds(art.ART)
    if not built:
        fail(f"the battle graphics don't build from content/art/: {said}")
    if not problems and built:
        ok("content/art/ keeps every rule, and the battle graphics build from it")

    folder = tempfile.mkdtemp()
    for name in art.FILES:
        shutil.copy(art.path_of(name), folder)
    server = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "artdesk", "serve.py"),
                               "--port", str(PORT), "--art", folder],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(URL + "meta.json").read()
                break
            except OSError:
                time.sleep(0.1)
        run(folder)
    finally:
        server.terminate()
        server.wait()
        shutil.rmtree(folder)
    print(f"art desk: {failures} failed")
    return 1 if failures else 0


def run(folder):
    # Untouched, every file comes back as it was.
    out = desk("roundtrip")
    try:
        texts = json.loads(out.splitlines()[0])
    except (ValueError, IndexError):
        texts = {}
    bad = [n for n in art.FILES if texts.get(n) != read(folder, n)]
    if bad:
        fail(f"opened and saved as is, {', '.join(bad)} would change")
    else:
        ok("every file opened and written back untouched, byte for byte")

    def edit(what, args, name, want, said):
        before = read(folder, name)
        desk(what, *args)
        got = read(folder, name)
        want_text = want(before)
        if got != want_text:
            import difflib
            fail(f"{said}: the file isn't what it should be:\n" + "".join(difflib.unified_diff(
                want_text.splitlines(True), got.splitlines(True), "should be", "saved", n=0)))
            return
        try:
            art.parse(name, got)
        except art.Problem as e:
            fail(f"{said}: saved a file art.py refuses: {e}")
            return
        ok(said)

    # A dot painted: HUMAN's top-left dot made its own colour (c, the 4th dot).
    edit("paint", ["figures", "HUMAN", 4, 0, 0], "figures",
         lambda t: with_dot(t, "figures", "HUMAN", 0, 0, "c"),
         "a figure's dot painted (HUMAN, 0,0: its own colour), and only that")
    # Painted and undone: as it was.
    edit("undo", ["figures", "GLASSFOLK", 2, 5, 20], "figures", lambda t: t,
         "a dot painted and undone: the file as it was")
    # A colour chosen.
    edit("colour", ["figures", "ASH_RAT", "red"], "figures",
         lambda t: t.replace("figure ASH_RAT grey", "figure ASH_RAT red"),
         "a figure's own colour chosen (ASH_RAT: red)")
    # A new scenery tile, a box drawn round it in its own colour.
    def boxed(t):
        rows = ["o" * 8] + ["o" + "k" * 6 + "o" for _ in range(14)] + ["o" * 8]
        return t + "\ntile crate black\n" + "\n".join(rows) + "\n"
    edit("box", ["tiles16", "crate", 4, 0, 0, 7, 15], "tiles16", boxed,
         "a new scenery tile (crate) with a box drawn round it, after the terrain")
    # A flood fill: the crate's inside filled with shared 1 (d).
    def filled(t):
        lines = t.split("\n")
        at = lines.index("tile crate black") + 1
        for y in range(1, 15):
            lines[at + y] = "o" + "d" * 6 + "o"
        return "\n".join(lines)
    edit("fill", ["tiles16", "crate", 2, 3, 7], "tiles16", filled,
         "a flood fill inside the box, stopping at its edge")
    # Art pasted as text (tests/artdesk/enforcer.txt: 16 x 21, five characters), as the
    # art desk's Paste says: a new figure named by its first line, its colour by its second;
    # each character mapped; what's drawn (columns 1-14, rows 1-20) fitted to 12 x 21, feet
    # on the bottom row: trimmed (one column off each side) or squeezed (12 of the 14
    # columns, each the one under the middle of its twelfth).
    pasted = os.path.join(ROOT, "tests", "artdesk", "enforcer.txt")
    grid = [ln for ln in open(pasted).read().split("\n")[2:] if ln]
    to = {"0": ".", "1": "a", "2": "c", "3": "b", "4": "b"}

    def figure(name, colour, cols):
        rows = ["".join(to[grid[y][x]] for x in cols) for y in range(21)]
        return lambda t: t + f"\nfigure {name} {colour}\n" + "\n".join(rows) + "\n"
    edit("paste", ["figures", pasted, "trim", "0=.,1=a,2=c,3=b,4=b", "new"], "figures",
         figure("ENFORCER", "red", range(2, 14)),
         "art pasted as text: a new figure, ENFORCER, red, trimmed to 12 wide")
    squeezed = [1 + (2 * i + 1) * 14 // 24 for i in range(12)]
    edit("paste", ["figures", pasted, "squeeze", "0=.,1=a,2=c,3=b,4=b", "ENFORCER"], "figures",
         lambda t: t.replace(figure("ENFORCER", "red", range(2, 14))(""),
                             figure("ENFORCER", "red", squeezed)("")),
         "art pasted into a figure, squeezed: 14 columns into 12")
    # Flips and shifts that cancel out.
    edit("flip", ["tiles32", "hazard"], "tiles32", lambda t: t,
         "flipped twice, shifted right and back: the file as it was")
    built, said = builds(folder)
    if built:
        ok("the battle graphics build from the edited art (the scenery kept, not yet used)")
    else:
        fail(f"the edited art doesn't build: {said}")

    # The server's own checks.
    before = read(folder, "tiles16")
    lines = before.split("\n")
    at = lines.index("tile wall black")
    broken = "\n".join(lines[:at] + lines[at + 17:])          # the wall gone
    code, said = put("tiles16.txt", broken)
    if code != 400 or "terrain" not in said or read(folder, "tiles16") != before:
        fail(f"a tiles file without its wall was written, or not refused for it: {code} {said}")
    else:
        ok(f"a file that breaks a rule isn't written: {said}")
    code, said = put("../../Makefile", "x")
    code2, _ = put("notes.txt", "x")
    if code != 403 or code2 != 403:
        fail(f"the server let something else be written: {code}, {code2}")
    else:
        ok("nothing but the art files can be written")


if __name__ == "__main__":
    sys.exit(main())
