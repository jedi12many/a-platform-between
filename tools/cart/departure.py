"""A Departure as the cartridge's assets (docs/cartridge.md, "The story").

    python3 tools/cart/departure.py SPLIT_DIR PICTURE_DIR OUT_DIR FIRST [MUSIC]

SPLIT_DIR is a Departure as `qsc.py build --split` writes it: DEPOT, CAR00, CAR01, ...;
PICTURE_DIR has its pictures, NAME.png (160 x 96), named as the depot names them.

MUSIC is the Departure's tune file, compiled (tools/music/musicc.py build NAME.music).

Asset FIRST is the depot, FIRST + 1 + k is car k; after the cars, the music, if there is
any; then a picture each, in the depot's order. Each is staged at $8000 like any asset
(cart/assets.s):

- the depot: its length (2 bytes, low first), the asset of its first picture (1 byte),
  the music's asset (1 byte: 255 if there's no music), then the file;
- a car: its length (2 bytes), then the file;
- the music: the tune file's length (2 bytes), the file padded to 1536 bytes, then the
  player's note table and sound effects (the C64 disk's MUSIC file, tools/music/musicc.py
  --c64, without its load address), all copied to MUSIC_AT (cart/tune.s);
- a picture: its length (2 bytes: 4801, or 0 if it has no PNG), then the picture as
  tools/c64pic.py converts it for the C64 version, in the order cart/picture.s shows it:
  the bitmap's 12 rows (3840 bytes), each cell's two screen colours (480), each cell's
  colour-RAM colour (480), the background (1).

Each is written twice, as OUT_DIR/aNN (8 KB, for the cartridge's chips: tools/crt.py)
and as OUT_DIR/aNN.prg (with its load address, $8000, for the disk). NN is hex.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qsc"))
import c64pic  # noqa: E402
import image  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music"))
import musicc  # noqa: E402

ASSET = 8192
STAGING = 0x8000
PICTURE_SIZE = 3840 + 480 + 480 + 1


def cars(split_dir):
    names = []
    k = 0
    while os.path.exists(os.path.join(split_dir, f"CAR{k:02d}")):
        names.append(f"CAR{k:02d}")
        k += 1
    return names


def picture(png):
    """A picture asset's data, from the C64 version's picture file."""
    pic, _ = c64pic.convert(c64pic.load(png))
    data = pic[2:]

    def at(address, n):
        return data[address - c64pic.LOAD_AT:address - c64pic.LOAD_AT + n]

    return (at(c64pic.BITMAP, 3840) + at(c64pic.SCREEN, 480) + at(c64pic.CELLS, 480)
            + at(c64pic.BACK, 1))


def write(out_dir, n, body, what):
    if len(body) > ASSET:
        raise SystemExit(f"{what}: {len(body)} bytes, more than an asset holds")
    with open(os.path.join(out_dir, f"a{n:02x}"), "wb") as f:
        f.write(body + bytes(ASSET - len(body)))
    with open(os.path.join(out_dir, f"a{n:02x}.prg"), "wb") as f:
        f.write(STAGING.to_bytes(2, "little") + body)
    print(f"asset {n}: {what}, {len(body)} bytes")


def main(argv):
    if len(argv) not in (5, 6):
        print(__doc__)
        return 2
    split_dir, pic_dir, out_dir, first = argv[1], argv[2], argv[3], int(argv[4])
    os.makedirs(out_dir, exist_ok=True)
    depot = open(os.path.join(split_dir, "DEPOT"), "rb").read()
    names = cars(split_dir)
    music = first + 1 + len(names) if len(argv) == 6 else 255
    first_picture = first + 1 + len(names) + (music != 255)
    write(out_dir, first, len(depot).to_bytes(2, "little") + bytes([first_picture, music])
          + depot, "DEPOT")
    for k, name in enumerate(names):
        data = open(os.path.join(split_dir, name), "rb").read()
        write(out_dir, first + 1 + k, len(data).to_bytes(2, "little") + data, name)
    if music != 255:
        tunes = open(argv[5], "rb").read()
        write(out_dir, music, musicc.c64_file(tunes)[2:], f"the music, {os.path.basename(argv[5])}")
    for i, name in enumerate(image.read_depot(depot).get("pictures", [])):
        png = os.path.join(pic_dir, name + ".png")
        data = picture(png) if os.path.exists(png) else b""
        assert len(data) in (0, PICTURE_SIZE)
        write(out_dir, first_picture + i, len(data).to_bytes(2, "little") + data,
              f"picture {i}, {name}" + ("" if data else " (no PNG)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
