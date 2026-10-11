"""An EasyFlash cartridge image (.crt) from its chips (docs/cartridge.md).

    python3 tools/crt.py OUT.crt NAME FILE:BANK:L|H|LH ... [--assets DIR]

Each FILE is an 8 KB chip: L is the bank's ROML ($8000), H its ROMH ($A000; at $E000 when
the cartridge boots in Ultimax mode); or, with LH, 16 KB, both, ROML first. The image is
the CRT format's: a 64-byte header (hardware type 32, EasyFlash: EXROM 1, GAME 0, so it boots in Ultimax mode), then a CHIP
packet for each chip, in bank order. Banks with no chip are left out.

--assets DIR adds every file aNN in DIR (NN in hex: tools/cart/departure.py) as asset NN:
bank 1 + NN/2, ROML for NN even, ROMH for odd (cart/assets.s).
"""

import os
import struct
import sys

EASYFLASH = 32
CHIP = 0x2000


def build(name, chips):
    head = (b"C64 CARTRIDGE   " + struct.pack(">IHHBB", 0x40, 0x0100, EASYFLASH, 1, 0)
            + bytes(6) + name.encode("ascii")[:32].ljust(32, b"\0"))
    out = bytearray(head)
    for bank, half, data in sorted(chips, key=lambda c: (c[0], c[1])):
        if len(data) != CHIP:
            raise SystemExit(f"crt: bank {bank} {half}: {len(data)} bytes, not 8192")
        if not 0 <= bank < 64:
            raise SystemExit(f"crt: bank {bank}: an EasyFlash has banks 0-63")
        address = 0x8000 if half == "L" else 0xA000
        out += b"CHIP" + struct.pack(">IHHHH", 0x10 + CHIP, 2, bank, address, CHIP) + data
    return bytes(out)


def read(path):
    """The chips of a .crt file: {(bank, "L" or "H"): data}, and its hardware type."""
    return read_bytes(open(path, "rb").read())


def read_bytes(data):
    """The chips of a .crt image, as read()."""
    if data[:16] != b"C64 CARTRIDGE   ":
        raise ValueError("not a CRT file")
    length, _, kind = struct.unpack(">IHH", data[16:24])
    chips = {}
    at = length
    while at < len(data):
        if data[at:at + 4] != b"CHIP":
            raise ValueError(f"no CHIP packet at {at}")
        size, _, bank, address, n = struct.unpack(">IHHHH", data[at + 4:at + 16])
        chips[(bank, "L" if address == 0x8000 else "H")] = data[at + 16:at + 16 + n]
        at += size
    return chips, kind


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    chips = []
    args = argv[3:]
    if "--assets" in args:
        i = args.index("--assets")
        folder = args[i + 1]
        del args[i:i + 2]
        for name in sorted(os.listdir(folder)):
            if len(name) == 3 and name[0] == "a":
                n = int(name[1:], 16)
                chips.append((1 + n // 2, "LH"[n % 2], open(os.path.join(folder, name), "rb").read()))
    for spec in args:
        path, bank, half = spec.rsplit(":", 2)
        data = open(path, "rb").read()
        if half == "LH":                            # 16 KB: ROML, then ROMH
            chips.append((int(bank), "L", data[:0x2000]))
            chips.append((int(bank), "H", data[0x2000:]))
        else:
            chips.append((int(bank), half, data))
    with open(argv[1], "wb") as f:
        f.write(build(argv[2], chips))
    print(f"{argv[1]}: {len(chips)} chips")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
