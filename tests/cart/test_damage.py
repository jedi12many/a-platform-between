"""Damaged Departures must never crash the cartridge's story VM (cart/vm.s, depot.s,
expand.s): never trust the image.

    python3 tests/cart/test_damage.py build/apb.crt build/cart/apb.lbl CHOICES [--cases N]
                                      [--fights]

Each case breaks a few bytes of the depot, a car or a picture, as the cartridge holds
them (assets 4, 5-7 and 8 on: tools/cart/departure.py), or its length, and plays CHOICES
on the emulated C64 (tests/cart/run_cart.py) till they run out. With --fights, it's the
bytes of the fight's encounter record (CHOICES must go into the fight). The VM may play on (the
damage was in a string it never reached, or it spoiled a picture) or stop ("The train
has derailed", "This Departure can't be boarded"); either way the program must only ever
run its own code (the resident engine, once it's started; the ending asset while it's
staged and called; the fight's two while a fight is on), never read a ROM it shouldn't,
and always come back for keys.
The damage is random but seeded, so a failure can be run again.
"""

import random
import sys

import run_cart

FRAMES = 2500                   # a case that's still running after this has hung


def damaged(chips, rnd, fights=False):
    """A copy of the chips with one asset of the Departure damaged (with `fights`, the
    bytes of its fight's encounter record); and what was done."""
    chips = dict(chips)
    asset = rnd.choice([4, 5, 6, 7, 8, 10])
    key = (1 + asset // 2, "LH"[asset % 2])
    data = bytearray(chips[key])
    length = data[0] | data[1] << 8
    how = rnd.choice(["bytes", "bytes", "bytes", "length", "header"])
    if fights:                                  # the fight's encounter, in the depot
        asset, how = 4, "encounter"
        key = (3, "L")
        data = bytearray(chips[key])
    if how == "encounter":
        names = data.index(b"\x07Ash rat")    # its record ends with its foes' names
        ats = sorted(names - 80 + rnd.randrange(96) for _ in range(rnd.randint(1, 3)))
        for at in ats:
            data[at] = rnd.randrange(256)
        said = f"the encounter's bytes {', '.join(str(a - names) for a in ats)} from its names"
    elif how == "length":
        at = rnd.choice([0, 1])
        data[at] = rnd.randrange(256)
        said = f"asset {asset}'s length byte {at} = {data[at]}"
    elif how == "header":
        at = 2 + rnd.randrange(min(24, length))
        data[at] = rnd.randrange(256)
        said = f"asset {asset}'s header byte {at - 2} = {data[at]}"
    else:
        ats = sorted(2 + rnd.randrange(length) for _ in range(rnd.randint(1, 6)))
        for at in ats:
            data[at] = rnd.randrange(256)
        said = f"asset {asset}'s bytes {', '.join(str(a - 2) for a in ats)}"
    chips[key] = bytes(data)
    return chips, said


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    image = open(argv[1], "rb").read()
    syms = run_cart.labels(argv[2])
    choices = [line.rstrip("\n") for line in open(argv[3])]
    cases = int(argv[argv.index("--cases") + 1]) if "--cases" in argv else 12
    resident = range(syms["__RESIDENT_RUN__"], syms["__RESIDENT_RUN__"] + syms["__RESIDENT_SIZE__"])
    ending = range(syms["__ENDING_RUN__"], syms["__ENDING_RUN__"] + syms["__ENDING_SIZE__"])
    battle = range(syms["__BATTLE_RUN__"], syms["__BATTLE_RUN__"] + syms["__BATTLE_SIZE__"])
    fight = range(syms["__FIGHT_RUN__"], syms["__FIGHT_RUN__"] + syms["__FIGHT_SIZE__"])
    fights = "--fights" in argv
    rnd = random.Random(1985)
    clean = run_cart.C64(image, syms).chips
    failures = derails = 0
    for n in range(cases):
        c = run_cart.C64(image, syms)
        c.chips, said = damaged(clean, rnd, fights)
        c.choices = list(choices)
        c.boot()
        wild = []
        step = c.mpu.step

        def watched():
            pc = c.mpu.pc
            if pc == syms["main"]:
                c.started = True
            if pc == syms["ending"]:                # the ending asset, run where it's staged
                c.ending = True
            elif pc == syms["fight"]:               # the fight's two, staged and copied
                c.fighting = True
            elif pc == syms["asset_fetch"]:
                c.ending = c.fighting = False
            if (c.started and pc not in resident and not (pc in ending and c.ending)
                    and not ((pc in battle or pc in fight) and c.fighting)):
                wild.append(pc)
            step()

        c.started = c.ending = c.fighting = False
        c.mpu.step = watched
        try:
            ended = c.run(max_frames=FRAMES)
        except RuntimeError as e:
            ended = f"stopped: {e}"
        told = " ".join(c.lines)
        stopped = "derailed" in told or "can't be boarded" in told
        derails += stopped
        if wild or ended != "[end of input]":
            failures += 1
            where = f", ran at ${wild[0]:04X}" if wild else ""
            print(f"FAIL: case {n} ({said}): {ended}{where}")
            for ln in c.lines[-6:]:
                print(f"      {ln}")
        else:
            why = told[max(told.find("derailed"), told.find("can't be boarded")):]
            why = why[:why.find(" (press")]
            print(f"ok   case {n} ({said}): " + (why if stopped else "played on"))
    print(f"{cases} damaged Departures: {derails} stopped the train, "
          f"{cases - derails - failures} played on, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
