"""Pictures for the modern front end (fe/modern/, milestone E6): any PNG into an APIC file,
in full colour.

    python3 tools/apic.py convert IN.png OUT.apic          one picture
    python3 tools/apic.py render IN.apic OUT.png           read one back
    python3 tools/apic.py dir DEPOT PICDIR OUTDIR          picNN.apic for each picture in
                                                           a Departure that has a PNG

The modern screen shows a picture on rows 1-12, 640 x 192 pixels, stretched to fill
them: a 160 x 96 picture, like the C64's, gets pixels four wide and two high, the same
shape as on a C64. A picture can be up to 640 x 384 and use up to 256 colours; a PNG
with more is reduced to 256.

An APIC file: "APIC"; the width and the height (16 bits each, low byte first); the
number of colours (one byte, 0 meaning 256); the palette, three bytes (red, green, blue)
a colour; then a palette index for every pixel, row by row.
"""

import os
import struct
import sys

from PIL import Image

MAX_W, MAX_H = 640, 384


def rgb_pixels(img):
    data = img.tobytes()
    return [tuple(data[i:i + 3]) for i in range(0, len(data), 3)]


def convert(png_path):
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    if w > MAX_W or h > MAX_H:
        raise SystemExit(f"{png_path}: {w} x {h} is bigger than {MAX_W} x {MAX_H}")
    rgb = rgb_pixels(img)
    colours = sorted(set(rgb))
    if len(colours) > 256:
        img = img.quantize(256, dither=Image.Dither.NONE).convert("RGB")
        rgb = rgb_pixels(img)
        colours = sorted(set(rgb))
    index = {c: i for i, c in enumerate(colours)}
    pixels = bytes(index[c] for c in rgb)
    return (b"APIC" + struct.pack("<HHB", w, h, len(colours) % 256)
            + b"".join(bytes(c) for c in colours) + pixels)


def read(data):
    if data[:4] != b"APIC":
        raise ValueError("not an APIC picture")
    w, h, n = struct.unpack("<HHB", data[4:9])
    n = n or 256
    palette = [tuple(data[9 + 3 * i:12 + 3 * i]) for i in range(n)]
    pixels = data[9 + 3 * n:]
    if len(pixels) != w * h or max(pixels) >= n:
        raise ValueError("a damaged APIC picture")
    return Image.frombytes("RGB", (w, h), b"".join(bytes(palette[p]) for p in pixels))


def departure(depot_path, pic_dir, out_dir):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "qsc"))
    import image
    with open(depot_path, "rb") as f:
        names = image.read_depot(f.read()).get("pictures", [])
    os.makedirs(out_dir, exist_ok=True)
    for i, name in enumerate(names):
        png = os.path.join(pic_dir, name + ".png")
        if os.path.exists(png):
            with open(os.path.join(out_dir, f"pic{i:02d}.apic"), "wb") as f:
                f.write(convert(png))


def main(argv):
    if len(argv) == 4 and argv[1] == "convert":
        data = convert(argv[2])
        with open(argv[3], "wb") as f:
            f.write(data)
        print(f"{argv[3]}: {len(data)} bytes")
        return 0
    if len(argv) == 4 and argv[1] == "render":
        with open(argv[2], "rb") as f:
            read(f.read()).save(argv[3])
        return 0
    if len(argv) == 5 and argv[1] == "dir":
        departure(argv[2], argv[3], argv[4])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
