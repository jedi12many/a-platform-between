"""Byte-pair text compression (docs/vm-spec.md, "Text encoding").

Code 0x80 + i stands for the two bytes in pair i. Pair i may only contain bytes below
0x80 + i, so expansion always ends, and no pair nests deeper than BPE_MAX_DEPTH.
"""

from opcodes import BPE_MAX_DEPTH, BPE_MAX_PAIRS


def compress(strings, max_pairs=BPE_MAX_PAIRS, max_depth=BPE_MAX_DEPTH):
    """Compress a list of byte strings (no terminators) with one shared pair table.

    Returns (pairs, packed): pairs is a list of (a, b); packed the compressed strings.
    """
    seqs = [list(s) for s in strings]
    depth = {b: 0 for b in range(0x80)}
    pairs = []
    while len(pairs) < max_pairs:
        counts = {}
        for seq in seqs:
            prev = None
            for i in range(len(seq) - 1):
                pair = (seq[i], seq[i + 1])
                # Don't count an overlapping repeat (aaa holds one aa, not two).
                if pair == prev and pair[0] == pair[1]:
                    prev = None
                    continue
                counts[pair] = counts.get(pair, 0) + 1
                prev = pair
        best = None
        for pair, n in counts.items():
            if max(depth[pair[0]], depth[pair[1]]) + 1 > max_depth:
                continue
            # A pair costs 2 bytes in the table, and saves 1 byte per use.
            if n < 3:
                continue
            if best is None or n > best[1] or (n == best[1] and pair < best[0]):
                best = (pair, n)
        if best is None:
            break
        pair = best[0]
        code = 0x80 + len(pairs)
        pairs.append(pair)
        depth[code] = max(depth[pair[0]], depth[pair[1]]) + 1
        for k, seq in enumerate(seqs):
            out = []
            i = 0
            while i < len(seq):
                if i + 1 < len(seq) and seq[i] == pair[0] and seq[i + 1] == pair[1]:
                    out.append(code)
                    i += 2
                else:
                    out.append(seq[i])
                    i += 1
            seqs[k] = out
    return pairs, [bytes(s) for s in seqs]


def expand(data, pairs, max_depth=BPE_MAX_DEPTH):
    """Undo compress() for one string, the way the VM's decoder does: with a small stack."""
    out = []
    for b in data:
        stack = [(b, 0)]
        while stack:
            c, d = stack.pop()
            if c < 0x80:
                out.append(c)
                continue
            i = c - 0x80
            if i >= len(pairs) or d >= max_depth:
                raise ValueError(f"bad pair code 0x{c:02x}")
            a, b2 = pairs[i]
            stack.append((b2, d + 1))
            stack.append((a, d + 1))
    return bytes(out)
