"""The Fare's pictures, painted in code with tools/paint.py.

    python3 content/s1/00-the-fare/pictures/paint.py

Writes one 160x96 PNG per picture the Departure shows (its `~ picture` names), in the
C64's colours, and checks that each comes through the C64's rules unchanged
(docs/c64.md, "Pictures"). Pixels are twice as wide as they are tall on the screen.
Each picture keeps to three colours everywhere and one more of the first eight in any
4 x 8 cell; the comment above each says which.
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "tools"))
from paint import (Canvas, report, W, H, BLACK, WHITE, RED, CYAN, PURPLE, GREEN,  # noqa: E402
                   BLUE, YELLOW, ORANGE, BROWN, PINK, DGREY, GREY, LGREEN, LBLUE, LGREY)


def static():
    """The end of everything, and a hand reaching through it.
    Shared: black, dark grey, light grey. Own: white (the hand and its light)."""
    c = Canvas(BLACK)
    rng = random.Random(1985)
    # Static from a small set of 4x8 tiles, so the C64 has characters to spare.
    tiles = []
    for _ in range(16):
        t = []
        for _y in range(8):
            row = []
            for _x in range(4):
                v = rng.random()
                row.append(LGREY if v < 0.22 else DGREY if v < 0.42 else BLACK)
            t.append(row)
        tiles.append(t)
    bands = {2: 0.5, 3: 0.8, 7: 0.35, 8: 0.6}          # rows where the picture rolls
    for cy in range(12):
        for cx in range(40):
            t = tiles[rng.randrange(len(tiles))]
            dim = cy not in bands and rng.random() < 0.35
            for y in range(8):
                for x in range(4):
                    v = t[y][x]
                    if dim and v == LGREY:
                        v = DGREY
                    c.set(cx * 4 + x, cy * 8 + y, v)
    # The rolling bars: brighter, smeared sideways.
    for cy, amount in bands.items():
        for y in range(cy * 8 + 2, cy * 8 + 6):
            c.rect(0, y, W - 1, y, LGREY, None, 16, only=DGREY) if rng.random() < amount else None
    # Light around the hand, then the hand: from the top right, reaching down and in,
    # outlined in black so it stands out of the noise.
    c.glow(110, 34, 90, 46, WHITE, steps=((1.0, 1), (0.75, 3), (0.5, 6)))
    hand = [((116, 0), (134, 0), (130, 16), (126, 24)), ((104, 22), (128, 18), (130, 34),
            (124, 42), (104, 42), (100, 32))]
    fingers = ((104, 40, 96, 58), (109, 41, 104, 64), (115, 41, 113, 66), (121, 40, 122, 60))
    thumb = (127, 28, 136, 42)
    for points in hand:
        c.poly([(x - 1, y) for x, y in points] + [(x + 1, y) for x, y in reversed(points)], BLACK)
    for x0, y0, x1, y1 in fingers + (thumb,):
        c.line(x0, y0, x1, y1, BLACK, width=5)
    c.poly([(117, 0), (133, 0), (129, 16), (110, 24)], WHITE)                 # the wrist
    c.poly(list(hand[1]), WHITE)                                               # the palm
    for x0, y0, x1, y1 in fingers + (thumb,):
        c.line(x0, y0, x1, y1, WHITE, width=3)
    c.line(108, 30, 120, 28, GREY if False else LGREY)                         # a crease
    c.rect(0, 0, W - 1, 0, BLACK)
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


def concourse():
    """The Waystation's great hall at night: the board, the arches, the Buffer Stop.
    Shared: black, dark grey, grey. Own: yellow (light), red (the barrier), white."""
    c = Canvas(BLACK)
    # Glass roof: a faint grid of panes between the ribs.
    for x in range(-60, W + 60, 40):
        c.arc((x - 40, -30, x + 80, 110), 180, 360, GREY, width=2)
    # The back wall, with arches out to the platforms.
    c.rect(0, 42, W - 1, 68, DGREY)
    for i, x in enumerate((8, 34, 60)):
        c.rect(x, 50, x + 14, 68, BLACK)
        c.ellipse(x + 7, 50, 14, 5, BLACK)
        c.text(x + 6, 44, str(i), WHITE)
    # The departure board, hung on rods, letters flipping.
    c.vline(56, 0, 10, GREY)
    c.vline(104, 0, 10, GREY)
    c.rect(44, 10, 115, 36, GREY)
    c.rect(45, 11, 114, 35, BLACK)
    c.text(47, 13, "0 THE FARE  NOW", YELLOW)
    c.text(47, 20, "1 KEPLER-9  NOW", YELLOW)
    c.text(47, 27, "2 ---------", YELLOW)
    # Lamps hanging over the hall.
    for x in (20, 140):
        c.vline(x, 0, 24, GREY)
        c.glow(x, 26, 30, 12, YELLOW, steps=((1.0, 2), (0.6, 5)), only=BLACK)
        c.rect(x - 1, 25, x + 1, 28, YELLOW)
    c.rect(0, 32, W - 1, 47, BLACK, only=YELLOW)      # the light stops above the signs
    # The floor: tiles worn into paths, in perspective.
    c.rect(0, 69, W - 1, 95, DGREY)
    c.hline(0, W - 1, 68, GREY)
    for k in range(-7, 8):
        c.line(80 + k * 12, 69, 80 + k * 36, 95, GREY)
    for y in (73, 79, 87):
        c.hline(0, W - 1, y, GREY)
    c.poly([(70, 69), (90, 69), (110, 95), (60, 95)], GREY, DGREY, 5, only=DGREY)
    # The Buffer Stop: a warm doorway under its painted sign.
    c.rect(122, 36, 156, 68, DGREY)
    c.rect(124, 38, 154, 44, BLACK)
    c.hline(126, 146, 42, GREY)                   # the rail
    c.hline(126, 146, 40, GREY)
    c.rect(147, 38, 151, 43, RED)                 # ending in a red barrier
    c.rect(130, 47, 148, 68, GREY)
    c.rect(132, 49, 146, 68, YELLOW)
    c.figure(138, 68, BLACK, tall=13)             # someone in the light
    c.poly([(132, 69), (146, 69), (156, 95), (116, 95)], YELLOW, DGREY, 4, only=DGREY)
    # Travelers crossing the hall.
    c.figure(54, 84, BLACK, tall=13, bag=True)
    c.figure(66, 78, BLACK, tall=10)
    c.figure(98, 90, BLACK, tall=15)
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


def stationmaster():
    """The Stationmaster at its table: very tall, a velvet coat, a face that is a polite
    arrangement of shadow, the brass ledger open with your name half written.
    Shared: black, purple (velvet), dark grey. Own: yellow (brass), white, green."""
    c = Canvas(DGREY)
    # The office: racks of pigeonholes, a station clock, a lamp.
    for cy in range(0, 9):
        for cx in range(0, 40):
            if cx % 2 == 0:
                c.rect(cx * 4, cy * 8, cx * 4 + 7, cy * 8 + 7, BLACK)
                c.rect(cx * 4 + 1, cy * 8 + 1, cx * 4 + 6, cy * 8 + 6, DGREY)
                if (cx * 7 + cy * 3) % 5 == 0 and cx < 28:
                    c.rect(cx * 4 + 2, cy * 8 + 4, cx * 4 + 5, cy * 8 + 6, WHITE)  # a ticket
    c.ellipse(24, 20, 30, 14, BLACK)                                        # the clock
    c.ellipse(24, 20, 26, 12, WHITE)
    c.line(24, 20, 24, 11, BLACK)
    c.line(24, 20, 29, 22, BLACK)
    c.glow(136, 52, 56, 22, YELLOW, steps=((1.0, 1), (0.7, 3), (0.45, 6)), only=DGREY)
    c.rect(112, 40, 159, 47, DGREY, only=YELLOW)
    c.poly([(130, 47), (132, 40), (140, 40), (142, 47)], GREEN)            # a green shade
    c.rect(135, 37, 137, 39, BLACK)
    c.rect(100, 72, 159, 73, DGREY, only=YELLOW)
    c.rect(135, 48, 137, 70, YELLOW)                                        # brass
    c.rect(130, 69, 142, 71, YELLOW)
    # The figure, rising: velvet coat, high collar, brass buttons, a peaked cap.
    c.poly([(48, 96), (56, 34), (68, 24), (92, 24), (104, 34), (112, 96)], PURPLE)
    for x in (62, 98):
        c.line(x, 40, x + (4 if x < 80 else -4), 94, BLACK)                # folds
    c.poly([(70, 24), (80, 46), (90, 24)], BLACK)                          # the collar's shadow
    for y in range(32, 72, 8):
        c.rect(84, y, 85, y + 1, YELLOW)                                    # buttons
    c.rect(58, 30, 67, 32, YELLOW)                                          # epaulettes
    c.rect(93, 30, 102, 32, YELLOW)
    c.ellipse(80, 17, 22, 9, BLACK)                                         # the face: shadow
    c.rect(66, 4, 94, 9, BLACK)                                             # the cap
    c.rect(62, 9, 98, 10, BLACK)
    c.rect(78, 5, 81, 7, YELLOW)                                            # its badge
    c.set(76, 16, WHITE)                                                    # two points of light
    c.set(84, 16, WHITE)
    # The table, the ledger open, a pen in an inkwell, gloved hands.
    c.rect(0, 74, W - 1, 95, BLACK)
    c.hline(0, W - 1, 74, PURPLE)
    c.rect(54, 78, 79, 92, WHITE)
    c.rect(81, 78, 106, 92, WHITE)
    for y in (81, 84, 87, 90):
        c.hline(57, 76, y, DGREY)
    c.hline(84, 94, 81, DGREY)                                              # a name, half written
    c.rect(44, 74, 51, 79, WHITE)                                           # gloves
    c.rect(109, 74, 116, 79, WHITE)
    c.rect(120, 82, 125, 88, DGREY)                                         # the inkwell
    c.line(122, 82, 128, 74, WHITE)
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
