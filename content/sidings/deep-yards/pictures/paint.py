"""The Deep Yards' pictures, painted in code with tools/paint.py.

    python3 content/sidings/deep-yards/pictures/paint.py

Like The Fare's (content/s1/00-the-fare/pictures/paint.py): one 160x96 PNG per picture,
in the C64's colours, each checked against the C64's rules.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tools"))
from paint import (Canvas, report, W, H, BLACK, WHITE, RED, CYAN, PURPLE, GREEN,  # noqa: E402
                   BLUE, YELLOW, ORANGE, BROWN, PINK, DGREY, GREY, LGREEN, LBLUE, LGREY)


def yards():
    """The end of the freight lines: the last lamp, the cage lift hanging over a shaft
    that goes down further than the Waystation does, and its operator, a man made
    mostly of rust and patience.
    Shared: black, dark grey, grey. Own: yellow (the lamp), red (rust)."""
    c = Canvas(BLACK)
    # The yard's far wall in the dark, and the rails running out to it.
    c.rect(0, 30, W - 1, 62, GREY, BLACK, 4)
    c.rect(0, 62, W - 1, 95, DGREY)
    for x0, x1 in ((-40, 20), (-10, 36), (150, 106), (190, 124)):
        c.line(x0, 95, x1, 62, GREY, width=1)
    for y in (66, 72, 80, 90):
        c.hline(0, 44, y, BLACK)
        c.hline(118, W - 1, y, BLACK)
    # The last lamp.
    c.rect(16, 18, 17, 70, GREY)
    c.rect(12, 14, 21, 18, GREY)
    c.glow(16, 30, 44, 26, YELLOW, steps=((1.0, 2), (0.7, 4), (0.4, 8)), only={BLACK, DGREY})
    c.rect(14, 19, 19, 22, YELLOW)
    # The shaft: a black square in the ground, and its headframe.
    c.poly([(52, 66), (108, 66), (118, 95), (42, 95)], BLACK)
    for y in range(70, 96, 6):
        c.hline(52 - (y - 66) // 3, 108 + (y - 66) // 3, y, DGREY)
    c.line(54, 0, 50, 66, GREY, width=2)
    c.line(106, 0, 110, 66, GREY, width=2)
    c.hline(48, 112, 4, GREY)
    c.hline(48, 112, 5, GREY)
    c.ellipse(80, 8, 10, 4, GREY)                      # the winding wheel
    # The cage, rusted, hanging on its cable over the drop.
    c.vline(80, 8, 30, GREY)
    c.rect(64, 30, 96, 72, RED)
    c.rect(66, 32, 94, 70, BLACK)
    for x in range(68, 94, 4):
        c.vline(x, 32, 70, RED)
    c.rect(66, 46, 94, 47, RED)
    c.rect(74, 36, 86, 40, GREY)                       # the brass plate
    c.text(75, 36, "YARD", BLACK) if False else c.hline(76, 84, 38, BLACK)
    # The operator, on his stool by the gate: rust and patience.
    c.rect(126, 74, 134, 76, GREY)                     # the stool
    c.vline(127, 76, 88, GREY)
    c.vline(133, 76, 88, GREY)
    c.poly([(124, 74), (126, 56), (134, 56), (136, 74)], RED)
    c.ellipse(130, 51, 10, 5, RED)
    c.rect(127, 50, 129, 51, BLACK)                    # one eye, not looking up
    c.line(126, 60, 120, 70, RED, width=2)
    c.rect(118, 70, 121, 73, RED)
    return c


def bottom():
    """The tenth floor: no stair down, only a buffer stop, and painted on it in letters
    older than the Waystation: YOU CAME A LONG WAY.
    Shared: black, dark grey, grey. Own: red (the buffer stop), white (the letters, on a
    grey board of their own), yellow (the cage's lamp)."""
    c = Canvas(BLACK)
    # A vault of old brick, going up out of the light.
    c.rect(0, 0, W - 1, 70, GREY, BLACK, 6)
    for y in range(4, 70, 8):
        c.hline(0, W - 1, y, BLACK)
        for x in range((y // 8) % 2 * 8, W, 16):
            c.vline(x, y - 3, y, BLACK)
    c.arc((-20, 6, 180, 150), 180, 360, GREY, width=2)
    # The rails, running in and stopping.
    c.rect(0, 70, W - 1, 95, DGREY)
    for x0, x1 in ((20, 60), (140, 100)):
        c.line(x0, 95, x1, 70, GREY, width=2)
    for y in (74, 80, 88):
        c.hline(40 - (y - 70), 120 + (y - 70), y, BLACK)
    # The buffer stop, and its words.
    c.rect(40, 24, 120, 66, RED)
    c.rect(40, 24, 120, 47, GREY)                      # the board the words are on
    c.rect(40, 24, 120, 25, BLACK)
    c.rect(40, 46, 120, 47, BLACK)
    c.rect(44, 66, 52, 78, BLACK)
    c.rect(108, 66, 116, 78, BLACK)
    for x in (52, 108):                                # the buffers
        c.ellipse(x, 56, 12, 6, GREY)
        c.ellipse(x, 56, 6, 3, BLACK)
    c.text(62, 31, "YOU CAME", WHITE)
    c.text(58, 40, "A LONG WAY", WHITE)
    # The cage, waiting, its lamp lit.
    c.rect(138, 30, 156, 70, GREY)
    c.rect(140, 32, 154, 68, BLACK)
    for x in range(142, 154, 4):
        c.vline(x, 32, 68, GREY)
    c.rect(145, 26, 149, 29, YELLOW)
    c.glow(147, 27, 30, 10, YELLOW, steps=((1.0, 2), (0.6, 6)), only={BLACK, DGREY})
    return c


PICTURES = (("yards", yards), ("bottom", bottom))


def main():
    paths = []
    for name, draw in PICTURES:
        path = os.path.join(HERE, name + ".png")
        draw().save(path)
        paths.append(path)
    return 0 if report(paths) else 1


if __name__ == "__main__":
    sys.exit(main())
