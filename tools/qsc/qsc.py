"""qsc: the Quest Script compiler.

    python3 tools/qsc/qsc.py check FILE.qs                 report errors and warnings
    python3 tools/qsc/qsc.py build FILE.qs -o OUT.apd      compile to a Departure image
    python3 tools/qsc/qsc.py build FILE.qs --split DIR     ... as DEPOT, CAR00, ... files
    python3 tools/qsc/qsc.py build FILE.qs --manifest M.json   ... and its reward manifest
    python3 tools/qsc/qsc.py dump FILE.apd                 verify and disassemble an image
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "registry"))

import registry  # noqa: E402
from codegen import CompileError, compile_departure  # noqa: E402
from image import BadImage, disassemble, verify  # noqa: E402
from manifest import ManifestError, manifest  # noqa: E402
from parse import parse  # noqa: E402


def report(diag, source_lines, out=sys.stderr):
    """Print errors and warnings like 'the-fare.qs:42: error: ...' with the line below."""
    name = os.path.basename(diag.path)
    for kind, items in (("error", diag.errors), ("warning", diag.warnings)):
        for line, msg in sorted(items, key=lambda e: e[0]):
            print(f"{name}:{line}: {kind}: {msg}", file=out)
            if 1 <= line <= len(source_lines):
                print(f"    | {source_lines[line - 1].rstrip()}", file=out)


def load(path):
    with open(path, encoding="utf-8") as f:
        source = f.read()
    reg = registry.load()
    dep, diag = parse(path, source, reg)
    report(diag, source.splitlines())
    if diag.errors:
        print(f"{len(diag.errors)} error(s), {len(diag.warnings)} warning(s)", file=sys.stderr)
        return None, None, diag
    return dep, reg, diag


def check(path):
    dep, _, diag = load(path)
    if dep is None:
        return 1
    scenes = sum(1 for _ in dep.scenes())
    print(f"{os.path.basename(path)}: ok. '{dep.title}', {len(dep.chapters)} chapter(s), "
          f"{scenes} scenes, {len(dep.flags)} flags, {len(dep.vars)} variables, "
          f"{len(diag.warnings)} warning(s)")
    return 0


def build(path, out=None, split=None, manifest_out=None):
    dep, reg, _ = load(path)
    if dep is None:
        return 1
    try:
        image = compile_departure(dep, reg)
        rewards = manifest(dep, reg)
    except (CompileError, ManifestError) as e:
        print(f"{os.path.basename(path)}:{e.line}: error: {e}", file=sys.stderr)
        return 1
    if manifest_out:
        with open(manifest_out, "w") as f:
            json.dump(rewards, f, indent=1)
            f.write("\n")
    data = image.apd()
    verify(data, reg)       # never write an image the VM would refuse
    if out:
        with open(out, "wb") as f:
            f.write(data)
    if split:
        os.makedirs(split, exist_ok=True)
        for name, blob in image.files().items():
            with open(os.path.join(split, name), "wb") as f:
                f.write(blob)
    cars = ", ".join(str(len(c)) for c in image.cars)
    print(f"{os.path.basename(path)}: {len(data)} bytes (depot {len(image.depot)}, "
          f"cars {cars}), {len(image.pairs)} text pairs")
    return 0


def dump(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        print(disassemble(data, registry.load()), end="")
    except BadImage as e:
        print(f"{os.path.basename(path)}: bad image: {e}", file=sys.stderr)
        return 1
    return 0


def main(argv):
    args = argv[1:]
    if len(args) == 2 and args[0] == "check":
        return check(args[1])
    if len(args) == 2 and args[0] == "dump":
        return dump(args[1])
    if len(args) >= 2 and args[0] == "build":
        out = split = manifest_out = None
        rest = args[2:]
        while rest:
            if rest[0] == "-o" and len(rest) > 1:
                out, rest = rest[1], rest[2:]
            elif rest[0] == "--split" and len(rest) > 1:
                split, rest = rest[1], rest[2:]
            elif rest[0] == "--manifest" and len(rest) > 1:
                manifest_out, rest = rest[1], rest[2:]
            else:
                break
        if not rest:
            return build(args[1], out, split, manifest_out)
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
