"""Commodore 1541 disk images (.d64): write one, read files back.

A .d64 is the 35 tracks of a 1541 floppy, 683 sectors of 256 bytes. Track 18 holds the
BAM (which sectors are used) and the directory; each file is a chain of sectors whose
first two bytes point to the next (track 0: the last, and the second byte is the last
used byte). Names are PETSCII, padded with $A0. See docs/c64.md.

    python3 tools/d64.py write OUT.d64 "DISK NAME" ID  FILE=NAME[,s] ...
    python3 tools/d64.py list IMAGE.d64

File names are given in ASCII and stored the way cc65 and c1541 store them: lower case
letters as $41-$5A (what an unshifted key types), capitals as $C1-$DA.
"""

import sys

TRACKS = 35
DIR_TRACK = 18
TYPES = {"del": 0x80, "seq": 0x81, "prg": 0x82, "usr": 0x83, "rel": 0x84}


def sectors_in(track):
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def offset(track, sector):
    return (sum(sectors_in(t) for t in range(1, track)) + sector) * 256


def petscii(name):
    out = bytearray()
    for ch in name:
        c = ord(ch)
        if 0x61 <= c <= 0x7A:
            c -= 0x20
        elif 0x41 <= c <= 0x5A:
            c += 0x80
        out.append(c)
    return bytes(out)


def ascii_name(raw):
    out = []
    for c in raw:
        if 0x41 <= c <= 0x5A:
            c += 0x20
        elif 0xC1 <= c <= 0xDA:
            c -= 0x80
        out.append(chr(c))
    return "".join(out)


class Disk:
    def __init__(self, name, disk_id):
        self.data = bytearray(offset(TRACKS + 1, 0))
        self.used = {t: set() for t in range(1, TRACKS + 1)}
        self.entries = []
        self.name = petscii(name)[:16]
        self.id = petscii(disk_id)[:2]
        self.used[DIR_TRACK].update({0, 1})

    def _free_sector(self, last):
        """The next free sector, 1541 style: interleave 10 on a track, then the tracks
        nearest the directory first."""
        order = [t for pair in zip(range(17, 0, -1), range(19, TRACKS + 1)) for t in pair]
        order += [t for t in range(1, TRACKS + 1) if t not in order and t != DIR_TRACK]
        if last:
            t, s = last
            n = sectors_in(t)
            for k in range(n):
                cand = (s + 10 + k) % n
                if cand not in self.used[t]:
                    return t, cand
            order = order[order.index(t) + 1:] + order[:order.index(t) + 1]
        for t in order:
            for s in range(sectors_in(t)):
                if s not in self.used[t]:
                    return t, s
        raise ValueError("the disk is full")

    def add(self, name, data, kind="prg"):
        if len(self.entries) >= 144:
            raise ValueError("the directory is full")
        chain = []
        last = None
        for i in range(max(1, (len(data) + 253) // 254)):
            t, s = self._free_sector(last)
            self.used[t].add(s)
            chain.append((t, s))
            last = (t, s)
        for i, (t, s) in enumerate(chain):
            part = data[i * 254:(i + 1) * 254]
            at = offset(t, s)
            if i + 1 < len(chain):
                self.data[at], self.data[at + 1] = chain[i + 1]
            else:
                self.data[at], self.data[at + 1] = 0, len(part) + 1
            self.data[at + 2:at + 2 + len(part)] = part
        self.entries.append((petscii(name)[:16], TYPES[kind], chain[0], len(chain)))

    def image(self):
        # Directory: track 18 from sector 1, 8 entries a sector, interleave 3.
        dir_sectors = [1]
        while len(dir_sectors) * 8 < len(self.entries):
            s = (dir_sectors[-1] + 3) % sectors_in(DIR_TRACK)
            while s in dir_sectors or s == 0:
                s = (s + 1) % sectors_in(DIR_TRACK)
            dir_sectors.append(s)
        self.used[DIR_TRACK].update(dir_sectors)
        for n, s in enumerate(dir_sectors):
            at = offset(DIR_TRACK, s)
            if n + 1 < len(dir_sectors):
                self.data[at], self.data[at + 1] = DIR_TRACK, dir_sectors[n + 1]
            else:
                self.data[at], self.data[at + 1] = 0, 0xFF
            for k, (name, kind, (t, s0), blocks) in enumerate(self.entries[n * 8:n * 8 + 8]):
                e = at + k * 32
                self.data[e + 2] = kind
                self.data[e + 3], self.data[e + 4] = t, s0
                self.data[e + 5:e + 21] = name.ljust(16, b"\xa0")
                self.data[e + 30], self.data[e + 31] = blocks & 0xFF, blocks >> 8
        # BAM: track 18 sector 0.
        bam = offset(DIR_TRACK, 0)
        self.data[bam:bam + 4] = bytes([DIR_TRACK, 1, 0x41, 0])
        for t in range(1, TRACKS + 1):
            n = sectors_in(t)
            bits = 0
            for s in range(n):
                if s not in self.used[t]:
                    bits |= 1 << s
            e = bam + 4 * t
            self.data[e] = bin(bits).count("1")
            self.data[e + 1:e + 4] = bytes([bits & 0xFF, (bits >> 8) & 0xFF, bits >> 16])
        self.data[bam + 0x90:bam + 0xA0] = self.name.ljust(16, b"\xa0")
        self.data[bam + 0xA0:bam + 0xA2] = b"\xa0\xa0"
        self.data[bam + 0xA2:bam + 0xA4] = self.id.ljust(2, b"\xa0")
        self.data[bam + 0xA4] = 0xA0
        self.data[bam + 0xA5:bam + 0xA7] = b"2A"
        self.data[bam + 0xA7:bam + 0xAB] = b"\xa0" * 4
        return bytes(self.data)


def read_files(image):
    """{ascii name: (type, bytes)} for every file on the disk."""
    files = {}
    t, s = DIR_TRACK, 1
    seen = set()
    while t and (t, s) not in seen:
        seen.add((t, s))
        at = offset(t, s)
        for k in range(8):
            e = at + k * 32
            kind = image[e + 2]
            if not kind & 0x80:
                continue
            name = ascii_name(image[e + 5:e + 21].rstrip(b"\xa0"))
            data = bytearray()
            ft, fs = image[e + 3], image[e + 4]
            hops = 0
            while ft and hops < 700:
                fa = offset(ft, fs)
                nt, ns = image[fa], image[fa + 1]
                data += image[fa + 2:fa + 256] if nt else image[fa + 2:fa + ns + 1]
                ft, fs = nt, ns
                hops += 1
            files[name] = (kind & 0x07, bytes(data))
        t, s = image[at], image[at + 1]
    return files


def main(argv):
    if len(argv) >= 4 and argv[1] == "write":
        disk = Disk(argv[3], argv[4])
        for spec in argv[5:]:
            path, name = spec.split("=", 1)
            kind = "prg"
            if name.endswith(",s"):
                name, kind = name[:-2], "seq"
            with open(path, "rb") as f:
                disk.add(name, f.read(), kind)
        with open(argv[2], "wb") as f:
            f.write(disk.image())
        return 0
    if len(argv) == 3 and argv[1] == "list":
        with open(argv[2], "rb") as f:
            image = f.read()
        for name, (kind, data) in read_files(image).items():
            print(f"{(len(data) + 253) // 254:4} {name:16} {'?spur'[kind] if kind < 5 else '?'}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
