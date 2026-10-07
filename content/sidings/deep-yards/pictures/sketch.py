"""Placeholder pictures for the Deep Yards: simple shapes, to be replaced by real art.

    python3 content/sidings/deep-yards/pictures/sketch.py

Like The Fare's (content/s1/00-the-fare/pictures/sketch.py, whose colours and canvas
this uses): one 160x96 PNG per picture, in the C64's colours.
"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "fare_sketch", os.path.join(HERE, "..", "..", "..", "s1", "00-the-fare", "pictures", "sketch.py"))
fare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fare)
W, H, new = fare.W, fare.H, fare.new


def yards():
    """The cage lift over the shaft, past the last lamp."""
    img, d = new(fare.BLACK)
    d.rectangle((0, 80, W, H), fill=fare.DGREY)             # the freight lines' end
    for x in range(0, 50, 10):
        d.line((x, 80, x + 30, H), fill=fare.GREY)
    d.rectangle((22, 20, 26, 80), fill=fare.BROWN)           # the last lamp
    d.ellipse((16, 10, 32, 24), fill=fare.YELLOW)
    d.rectangle((70, 0, 130, 96), fill=fare.BLACK, outline=fare.GREY)   # the shaft
    for y in range(0, 96, 8):
        d.line((70, y, 130, y + 4), fill=fare.DGREY)
    d.rectangle((84, 30, 116, 70), outline=fare.ORANGE)      # the cage
    for x in range(88, 116, 6):
        d.line((x, 30, x, 70), fill=fare.ORANGE)
    d.line((100, 0, 100, 30), fill=fare.LGREY)               # its cable
    d.rectangle((136, 50, 150, 80), fill=fare.RED)           # the operator, all rust
    d.ellipse((137, 40, 149, 52), fill=fare.ORANGE)
    return img


def bottom():
    """The buffer stop at the tenth floor."""
    img, d = new(fare.BLUE)
    d.rectangle((0, 70, W, H), fill=fare.DGREY)
    for x in range(10, W, 20):
        d.rectangle((x, 72, x + 10, 76), fill=fare.BROWN)    # sleepers
    d.line((0, 78, W, 78), fill=fare.LGREY)
    d.line((0, 86, W, 86), fill=fare.LGREY)
    d.rectangle((60, 40, 100, 70), fill=fare.RED)            # the buffer stop
    d.rectangle((64, 46, 96, 54), fill=fare.WHITE)           # YOU CAME A LONG WAY
    for x in range(66, 94, 4):
        d.rectangle((x, 48, x + 2, 52), fill=fare.BLACK)
    d.ellipse((20, 10, 40, 30), fill=fare.YELLOW)            # a lamp nobody lit
    return img


def main():
    for name, draw in (("yards", yards), ("bottom", bottom)):
        draw().save(os.path.join(HERE, name + ".png"))
        print("wrote", name + ".png")


if __name__ == "__main__":
    main()
