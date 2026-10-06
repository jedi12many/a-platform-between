"""qsc: the Quest Script compiler.

    python3 tools/qsc/qsc.py check FILE.qs     report errors and warnings

E1.2 parses and checks a Departure. Building the compiled image (`build`) comes in E1.3.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "registry"))

import registry  # noqa: E402
from parse import parse  # noqa: E402


def report(diag, source_lines, out=sys.stderr):
    """Print errors and warnings like 'the-fare.qs:42: error: ...' with the line below."""
    name = os.path.basename(diag.path)
    for kind, items in (("error", diag.errors), ("warning", diag.warnings)):
        for line, msg in sorted(items, key=lambda e: e[0]):
            print(f"{name}:{line}: {kind}: {msg}", file=out)
            if 1 <= line <= len(source_lines):
                print(f"    | {source_lines[line - 1].rstrip()}", file=out)


def check(path):
    with open(path, encoding="utf-8") as f:
        source = f.read()
    dep, diag = parse(path, source, registry.load())
    report(diag, source.splitlines())
    if diag.errors:
        print(f"{len(diag.errors)} error(s), {len(diag.warnings)} warning(s)", file=sys.stderr)
        return 1
    scenes = sum(1 for _ in dep.scenes())
    print(f"{os.path.basename(path)}: ok. '{dep.title}', {len(dep.chapters)} chapter(s), "
          f"{scenes} scenes, {len(dep.flags)} flags, {len(dep.vars)} variables, "
          f"{len(diag.warnings)} warning(s)")
    return 0


def main(argv):
    if len(argv) == 3 and argv[1] == "check":
        return check(argv[2])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
