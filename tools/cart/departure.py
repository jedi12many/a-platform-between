"""A Departure as the cartridge's assets (docs/cartridge.md, "The story").

    python3 tools/cart/departure.py SPLIT_DIR OUT_DIR FIRST

SPLIT_DIR is a Departure as `qsc.py build --split` writes it: DEPOT, CAR00, CAR01, ...
Asset FIRST is the depot, FIRST + 1 + k is car k. Each asset is the file's length (2
bytes, low first) and then the file, staged at $8000 like any asset (cart/assets.s):
written twice, as OUT_DIR/aNN (8 KB, for the cartridge's chips: tools/crt.py) and as
OUT_DIR/aNN.prg (with its load address, $8000, for the disk). NN is hex.
"""

import os
import sys

ASSET = 8192
STAGING = 0x8000


def assets(split_dir):
    files = ["DEPOT"]
    k = 0
    while os.path.exists(os.path.join(split_dir, f"CAR{k:02d}")):
        files.append(f"CAR{k:02d}")
        k += 1
    return files


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    split_dir, out_dir, first = argv[1], argv[2], int(argv[3])
    os.makedirs(out_dir, exist_ok=True)
    for n, name in enumerate(assets(split_dir), first):
        data = open(os.path.join(split_dir, name), "rb").read()
        body = len(data).to_bytes(2, "little") + data
        if len(body) > ASSET:
            raise SystemExit(f"{name}: {len(data)} bytes, more than an asset holds")
        with open(os.path.join(out_dir, f"a{n:02x}"), "wb") as f:
            f.write(body + bytes(ASSET - len(body)))
        with open(os.path.join(out_dir, f"a{n:02x}.prg"), "wb") as f:
            f.write(STAGING.to_bytes(2, "little") + body)
        print(f"asset {n}: {name}, {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
