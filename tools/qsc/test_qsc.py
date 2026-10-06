"""Tests for the Quest Script parser.

tests/qsc/ok/*.qs must parse with no errors or warnings. tests/qsc/errors/*.qs mark
each expected message in a comment on the line it belongs to:

    ~ gve PULSE_RIFLE      // error: Did you mean 'give'?
    flag never             // warning: never used

Every marked message must be reported on its line, and nothing unmarked may be.
The Fare itself must parse cleanly too.
"""

import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "registry"))

import qs_ast as A  # noqa: E402
import registry  # noqa: E402
from parse import parse  # noqa: E402

REG = registry.load()
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def load(path):
    with open(path, encoding="utf-8") as f:
        source = f.read()
    return source, parse(path, source, REG)


def markers(source):
    found = {"error": [], "warning": []}
    for no, line in enumerate(source.splitlines(), 1):
        for kind, text in re.findall(r"//\s*(error|warning):\s*(.*?)\s*(?=//|$)", line):
            found[kind].append((no, text))
    return found


def check_clean(path):
    _, (dep, diag) = load(path)
    for line, msg in diag.errors + diag.warnings:
        fail(f"{os.path.relpath(path, ROOT)}:{line}: unexpected: {msg}")
    return dep


def check_errors(path):
    source, (dep, diag) = load(path)
    expected = markers(source)
    rel = os.path.relpath(path, ROOT)
    for kind, got in (("error", diag.errors), ("warning", diag.warnings)):
        remaining = list(got)
        for no, text in expected[kind]:
            match = next((g for g in remaining if g[0] == no and text in g[1]), None)
            if match:
                remaining.remove(match)
            else:
                near = [m for line, m in got if line == no]
                fail(f"{rel}:{no}: expected {kind} containing '{text}', got {near or 'nothing'}")
        for line, msg in remaining:
            fail(f"{rel}:{line}: unexpected {kind}: {msg}")


def flat(text):
    return "".join(p if isinstance(p, str) else "{" + (p.var or p.what) + "}" for p in text.parts)


def check_shapes():
    """Pin down what the parser builds, not just that it doesn't complain."""
    dep = check_clean(os.path.join(ROOT, "tests", "qsc", "ok", "everything.qs"))
    scenes = {s.name: s for s in dep.scenes()}
    hall = scenes["hall"].body
    texts = [flat(s) for s in hall if isinstance(s, A.Text)]
    want = [
        "+ This line starts with a plus and is plain text.",
        "First line of a paragraph, second line of the same paragraph.",
        "A new paragraph for {name} the {race} {class}, level {level}, owing {debt}."
        "\nFIXED LINE ONE\nFIXED  LINE TWO\nBack to prose.",
    ]
    if texts[:3] != want:
        fail(f"everything.qs paragraphs: {texts[:3]!r}")
    cmds = [(s.name, s.args) for s in hall if isinstance(s, A.Command)]
    if cmds[:3] != [("picture", ["hall"]), ("set", ["alarm"]), ("add", ["loops", 1])]:
        fail(f"everything.qs commands: {cmds[:3]}")
    if_stmt = next(s for s in hall if isinstance(s, A.If))
    if len(if_stmt.branches) != 4 or if_stmt.branches[-1][0] is not None:
        fail("everything.qs: if / else if / else if / else")
    first = if_stmt.branches[0][0]
    if not (isinstance(first, A.And) and isinstance(first.left, A.Or)
            and isinstance(first.right, A.Not)):
        fail("everything.qs: (a or b) and not c")
    check = next(s for s in hall if isinstance(s, A.Check))
    if check.rating != ("skill", REG["skills"]["TECH"]["id"]) or check.tn != 145:
        fail(f"everything.qs: check TECH vs 145 -> {check.rating} {check.tn}")
    cost = check.outcomes["cost"]
    if not (isinstance(cost[-1], A.Goto) and cost[-1].scene == "vault"
            and cost[-2].name == "set"):
        fail("everything.qs: 'cost: text ~ set alarm -> vault'")
    choices = scenes["hall"].choices
    if [c.sticky for c in choices] != [False, True, True]:
        fail("everything.qs: * then + then +")
    if not isinstance(choices[1].cond, A.Visited):
        fail("everything.qs: {visited vault}")
    if dep.pictures != ["hall"] or (dep.tl, dep.ml, dep.season) != (5, 5, 1):
        fail("everything.qs: header and pictures")
    vault = [s.name for s in scenes["vault"].body if isinstance(s, A.Command)]
    if vault != ["echo", "give", "take", "xp", "debt", "let", "sub", "clear", "pause", "end"]:
        fail(f"everything.qs vault commands: {vault}")

    fare = check_clean(os.path.join(ROOT, "content", "s1", "00-the-fare", "the-fare.qs"))
    if sum(1 for _ in fare.scenes()) != 12 or fare.start != "static":
        fail("the-fare.qs: 12 scenes starting at 'static'")


for path in sorted(glob.glob(os.path.join(ROOT, "tests", "qsc", "ok", "*.qs"))):
    check_clean(path)
for path in sorted(glob.glob(os.path.join(ROOT, "tests", "qsc", "errors", "*.qs"))):
    check_errors(path)
check_shapes()

print(f"qsc tests: {failures} failed")
sys.exit(1 if failures else 0)
