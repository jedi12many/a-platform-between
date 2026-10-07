"""Check the C64 overlays never reach into each other (docs/c64.md).

The overlays all load at the same address, so a call from one overlay to a function in
another links without a murmur and jumps into whatever happens to be loaded there. An
address can't tell them apart (every overlay has something at its first byte), but the
linker's debug file (build/c64/apb.dbg) can: it lists, for every symbol, the lines that
use it, and for every line the segment its code is in. This refuses any use of an
overlay's symbol from a different overlay. The main program may use an overlay, but
only after asking for it (APB_NEED); the 6502 playthroughs (make test-c64) cover that.

    python3 fe/c64/check_overlays.py build/c64/apb.dbg
"""

import re
import sys


def records(path):
    for line in open(path):
        kind, _, rest = line.rstrip("\n").partition("\t")
        yield kind, dict(re.findall(r'(\w+)=("[^"]*"|[^,]+)', rest))


def overlay_of(name):
    m = re.match(r"OVERLAY(\d)$|OVL(\d)DATA$", name)
    return int(m.group(1) or m.group(2)) if m else None


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    segs, spans, lines, syms, files = {}, {}, {}, [], {}
    for kind, f in records(argv[1]):
        if kind == "seg":
            segs[f["id"]] = f["name"].strip('"')
        elif kind == "span":
            spans[f["id"]] = f["seg"]
        elif kind == "line" and "span" in f:
            lines[f["id"]] = (f["span"].split("+"), f.get("file"), f.get("line"))
        elif kind == "file":
            files[f["id"]] = f["name"].strip('"')
        elif kind == "sym" and "seg" in f and "ref" in f:
            syms.append(f)
    problems = []
    checked = 0
    from_main = 0
    for sym in syms:
        home = overlay_of(segs.get(sym["seg"], ""))
        if not home:
            continue
        name = sym["name"].strip('"')
        for ref in sym["ref"].split("+"):
            span_ids, file_id, line_no = lines.get(ref, ([], None, None))
            for span in span_ids:
                where = segs.get(spans.get(span), "")
                user = overlay_of(where)
                checked += 1
                if user is None:
                    from_main += 1
                elif user != home:
                    problems.append(f"{name} is in OVERLAY{home}, but {where} uses it "
                                    f"({files.get(file_id, '?')} line {line_no})")
    for p in sorted(set(problems)):
        print("FAIL:", p)
    print(f"overlays: {checked} uses of overlay code and data checked "
          f"({from_main} from the main program), {len(set(problems))} from another overlay")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
