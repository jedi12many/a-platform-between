"""The rules core reads and refuses passwords as the Python reference does
(core/src/passport.c; tools/passport/passport.py and boarding.py).

    python3 tests/passport/check_refusals.py DECODER [--cases N]

DECODER is tests/passport/decode.c, built: a password a line in, what the core makes of
it a line out. For random travelers the spec allows (Passports and Boarding Passes),
travelers no game has with right checksums, ones longer than any there can be, and
damaged ones, the core's answer must be the reference's: ok, or the same refusal (a typo
on the same line, an unknown symbol, the wrong length, a checksum, a different version).
"""

import random
import subprocess
import sys

import cases
import boarding
import passport


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    n = int(argv[argv.index("--cases") + 1]) if "--cases" in argv else 200
    rnd = random.Random(2024)
    texts = []
    for k in range(n):
        ch = cases.random_traveler(rnd)
        texts += [passport.encode(ch),
                  boarding.encode(rnd.randrange(65536), rnd.randrange(1 << 32),
                                  rnd.randrange(65536), rnd.random() < 0.5, ch)]
        texts.append(cases.damaged(rnd, rnd.choice(texts[-2:])))
        bad, _ = cases.impossible(rnd)
        texts.append(rnd.choice([passport.encode, lambda c: boarding.encode(1, 2, 3, False, c)])(bad))
        if k % 10 == 0:
            long = texts[-1]
            while len(long) <= (passport.PASS_LONGEST if long[0] in "GH" else passport.PASSPORT_LONGEST):
                long += "0" * 20
            texts.append(long)
    got = subprocess.run([argv[1]], input="\n".join(texts) + "\n", capture_output=True,
                         text=True, check=True).stdout.split("\n")
    failures = 0
    tally = {}
    for text, core in zip(texts, got):
        want = cases.reference(text)
        want = f"line {want[1]}" if want[0] == "line" else want[0]
        tally[want] = tally.get(want, 0) + 1
        if core != want:
            failures += 1
            if failures <= 5:
                print(f"FAIL: the reference says {want}, the core {core}: {text!r}")
    print(f"ok   {len(texts) - failures} of {len(texts)} passwords read or refused as the reference "
          f"does ({', '.join(f'{v} {k}' for k, v in sorted(tally.items()) if not k.startswith('line'))}, "
          f"{sum(v for k, v in tally.items() if k.startswith('line'))} typos)"
          if not failures else f"{failures} of {len(texts)} differ")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
