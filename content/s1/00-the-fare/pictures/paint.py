"""The Fare's pictures, made with tools/paint.py.

    python3 content/s1/00-the-fare/pictures/paint.py

Writes one 160x96 PNG per picture the Departure shows (its `~ picture` names), in the
C64's colours, and checks that each comes through the C64's rules unchanged
(docs/c64.md, "Pictures"). Pixels are twice as wide as they are tall on the screen.

Three are Gemini's (gemini/*.jpg, from the prompts in docs/art-prompts.md), fitted to the
C64 by tools/c64fit.py, which needs numpy. Two are painted in code: each keeps to three
colours everywhere and one more of the first eight in any 4 x 8 cell, as the comment
above it says.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tools"))
from paint import (Canvas, report, W, H, BLACK, WHITE, RED, CYAN, PURPLE, GREEN,  # noqa: E402
                   BLUE, YELLOW, ORANGE, BROWN, PINK, DGREY, GREY, LGREEN, LBLUE, LGREY)


def gemini(name, box):
    """One of the pictures drawn by an image model (Gemini, from the prompts in
    docs/art-prompts.md), from gemini/NAME.jpg, fitted to the C64 by tools/c64fit.py:
    `box` is the part of it kept, as fractions of its width and height."""
    return Canvas.fitted(os.path.join(HERE, "gemini", name + ".jpg"), box)


def static():
    """The end of everything, and a hand reaching through it. (Gemini.)"""
    return gemini("static", [0, 0, 1, 1])


def concourse():
    """The Waystation's great hall at night: green iron, lamps, travellers, and the Buffer
    Stop's lit door under its sign. The lower half of Gemini's square picture: the
    departure board above it doesn't fit the strip."""
    return gemini("concourse", [0, 0.38, 1, 0.86])


def stationmaster():
    """The Stationmaster among its pigeonholes: velvet coat, a face of shadow, the clock,
    the green lamp, the ledger. (Gemini.) The C64's only purple is lighter than the
    velvet Gemini drew, so the coat fits to blue: it's put back to purple."""
    c = gemini("stationmaster", [0.08, 0.06, 0.92, 0.98])
    c.recolour(BLUE, PURPLE, 50, 0, 110, 95)
    return c


def platform_bench():
    """A bench on Platform 0, under green iron and cracked glass, no sky beyond.
    Shared: grey, dark grey, green (the iron). Own: white (the shimmer, the sign, the
    platform edge), red (the bench's wood), black."""
    c = Canvas(GREY)
    # Beyond the glass: a slow grey shimmer, like rain that forgot which way is down.
    # (Four tiles of it, repeated, so the C64 has characters to spare.)
    tiles = [[(0, 6), (1, 5), (2, 4)], [(2, 2), (3, 1)], [(1, 7), (2, 6)], [(0, 3), (1, 2), (2, 1)]]
    for cy in range(5):
        for cx in range(40):
            for x, y in tiles[(cx * 3 + cy * 2) % 4]:
                c.set(cx * 4 + x, cy * 8 + y, WHITE)
    c.vgrad(0, 34, W - 1, 50, GREY, DGREY)
    # The roof: green iron columns and arched braces, glazing bars between.
    for x in range(0, W + 1, 40):
        c.arc((x, 6, x + 40, 62), 180, 360, GREEN, width=2)
        c.rect(x - 1, 0, x + 1, 60, GREEN)
        c.ellipse(x + 20, 24, 8, 3, GREEN)               # a cast-iron rosette
    c.rect(0, 0, W - 1, 3, GREEN)
    c.hline(0, W - 1, 34, GREEN)
    for x in range(10, W, 10):
        c.vline(x, 4, 12, DGREY) if x % 40 else None
    c.line(128, 4, 134, 14, DGREY)                         # a cracked pane
    c.line(134, 14, 131, 21, DGREY)
    c.line(134, 14, 139, 18, DGREY)
    # The sign, hanging from the ironwork.
    c.vline(46, 4, 12, DGREY)
    c.vline(113, 4, 12, DGREY)
    c.rect(40, 12, 119, 20, WHITE)
    c.text(42, 14, "ARRIVALS--ALL LINES", DGREY)
    # The far wall under the canopy, then the platform.
    c.rect(0, 50, W - 1, 60, DGREY)
    for x in range(4, W, 40):
        c.rect(x, 52, x + 30, 58, WHITE, DGREY, 3)      # posters, too faded to read
    c.rect(0, 61, W - 1, 95, DGREY)
    c.rect(0, 61, W - 1, 62, WHITE)
    for x in range(-200, W + 200, 32):                # paving joints, in perspective
        c.line(80 + (x - 80) // 4, 63, x, 95, GREY)
    for y in (66, 72, 81, 93):
        c.hline(0, W - 1, y, GREY)
    # The bench: slatted wood on black iron, and its shadow.
    c.rect(36, 89, 124, 91, GREY, DGREY, 6)
    for y in (64, 69):
        c.rect(42, y, 118, y + 2, RED)
    c.rect(38, 76, 122, 77, RED)
    c.rect(38, 79, 122, 80, RED)
    c.rect(38, 82, 122, 82, RED)
    for x in (44, 80, 115):
        c.rect(x, 63, x + 1, 75, GREY)
    for x in (38, 120):
        c.rect(x, 74, x + 2, 89, GREY)
        c.rect(x - 1, 89, x + 3, 89, GREY)
    return c


def buffer_stop():
    """The Buffer Stop: a knight arguing with moths, Fen behind the bar with a rag on
    fire, something made of glass drinking light.
    Shared: brown (the panelling), black, orange (polished wood). Own: one per cell of
    green, yellow, red, white, cyan, purple."""
    c = Canvas(BROWN)
    # Panelled walls, a beam, two lamps.
    for x in range(0, W, 8):
        c.vline(x, 4, 60, BLACK)
    c.rect(0, 0, W - 1, 3, BLACK)
    for x in (64, 150):
        c.vline(x, 4, 7, BLACK)
        c.glow(x, 9, 26, 5, YELLOW, steps=((1.0, 2), (0.6, 6)), only=BROWN)
        c.rect(x - 1, 8, x + 1, 10, YELLOW)
    # Shelves of bottles from every world, one bottle to a cell.
    for y in (14, 32):
        c.rect(52, y + 11, 83, y + 12, ORANGE)
        for i, cx in enumerate(range(13, 21)):
            colour = (GREEN, CYAN, PURPLE, RED, YELLOW, WHITE, GREEN, RED)[(i + y) % 8]
            colour = GREEN if cx == 20 else colour             # next to Fen's leaves
            x = cx * 4
            c.rect(x + 1, y + 4, x + 3, y + 10, colour)
            c.rect(x + 2, y + 2, x + 2, y + 3, colour)
    # Fen: a tree behind the bar, bark faintly glowing, a twig-hand, a rag on fire.
    c.glow(103, 30, 38, 22, GREEN, steps=((1.0, 2), (0.7, 4)), only=BROWN)
    c.rect(84, 48, 120, 60, BROWN, only=GREEN)
    c.poly([(94, 60), (96, 30), (92, 22), (100, 26), (104, 18), (108, 26), (114, 22),
            (110, 32), (112, 60)], ORANGE)                                  # the trunk
    for x in (98, 103, 108):
        c.line(x, 32, x - 1, 60, BLACK)                                      # bark
    c.rect(99, 36, 100, 37, GREEN)                                           # eyes
    c.rect(106, 36, 107, 37, GREEN)
    c.hline(101, 105, 42, BLACK)
    for (x, y, rx, ry) in ((104, 10, 40, 9), (96, 14, 20, 7), (113, 14, 20, 7)):
        c.ellipse(x, y, rx, ry, GREEN)                                       # the crown
        c.ellipse(x, y + 3, rx * 0.7, ry * 0.5, GREEN, BLACK, 6, only=GREEN)
    c.line(111, 46, 124, 42, ORANGE, width=2)                                # an arm
    c.rect(124, 41, 127, 45, WHITE)                                          # the rag...
    c.rect(124, 34, 127, 39, YELLOW)                                         # ...on fire
    c.rect(125, 32, 126, 33, YELLOW)
    # The knight in rusted plate, arguing with a cloud of moths.
    c.ellipse(20, 20, 20, 8, RED)                                            # helm
    c.rect(15, 20, 25, 27, RED)
    c.rect(16, 22, 24, 22, BLACK)                                            # visor slit
    c.vline(20, 12, 14, BLACK)                                               # crest
    c.rect(8, 28, 31, 33, RED)                                               # pauldrons
    c.hline(8, 31, 33, BLACK)
    c.poly([(11, 34), (29, 34), (26, 60), (14, 60)], RED)                    # breastplate
    c.vline(20, 36, 58, BLACK)
    c.hline(13, 27, 48, BLACK)                                               # a belt
    c.rect(6, 34, 9, 52, RED)                                                # one arm down
    c.line(31, 32, 36, 24, RED, width=3)                                     # one raised at them
    c.rect(35, 20, 37, 23, RED)
    for x, y in ((41, 14), (45, 18), (42, 22), (47, 24), (43, 28), (48, 16), (45, 10),
                 (41, 30), (47, 30)):                                         # moths
        c.rect(x, y, x + 1, y, WHITE)
    # Something made of glass, drinking something made of light.
    c.ellipse(148, 26, 14, 6, CYAN, BROWN, 10)                              # head
    c.poly([(140, 60), (142, 36), (154, 36), (156, 60)], CYAN, BROWN, 10)   # body
    c.line(142, 40, 137, 32, CYAN, width=2)                                  # an arm, lifting
    c.rect(132, 26, 135, 32, YELLOW)                                         # a glass of light
    # The bar: a polished top, panels, a brass rail.
    c.rect(0, 60, W - 1, 63, ORANGE)
    c.hline(0, W - 1, 64, BLACK)
    c.rect(0, 65, W - 1, 95, BROWN)
    for x in range(4, W, 20):
        c.rect(x, 68, x + 15, 86, ORANGE)
        c.rect(x + 1, 69, x + 14, 85, BROWN)
    c.rect(0, 89, W - 1, 90, YELLOW)
    c.rect(44, 56, 47, 59, CYAN)                                             # a glass
    c.rect(100, 57, 103, 59, WHITE)                                          # glasses Fen wiped
    c.rect(108, 57, 111, 59, WHITE)
    return c


PICTURES = (("static", static), ("platform_bench", platform_bench), ("concourse", concourse),
            ("buffer_stop", buffer_stop), ("stationmaster", stationmaster))


def main():
    paths = []
    for name, draw in PICTURES:
        path = os.path.join(HERE, name + ".png")
        draw().save(path)
        paths.append(path)
    return 0 if report(paths) else 1


if __name__ == "__main__":
    sys.exit(main())
