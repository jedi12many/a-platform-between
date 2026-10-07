"""Eighteen Minutes' pictures, painted in code with tools/paint.py.

    python3 content/s1/01-eighteen-minutes/pictures/paint.py

Like The Fare's (content/s1/00-the-fare/pictures/paint.py, whose Waystation pictures this
one makes again: the concourse, the platform, the Static and the Stationmaster, three of
them Gemini's, fitted by tools/c64fit.py, so this needs numpy too): one 160x96 PNG per
picture, in the C64's colours, each checked against the C64's rules.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "fare_paint", os.path.join(HERE, "..", "..", "00-the-fare", "pictures", "paint.py"))
fare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fare)
from paint import (Canvas, report, W, H, BLACK, WHITE, RED, CYAN, PURPLE, GREEN,  # noqa: E402
                   BLUE, YELLOW, ORANGE, BROWN, PINK, DGREY, GREY, LGREEN, LBLUE, LGREY)


def countdown(c, x, y, colour=RED):
    """A screen on the wall: 18:00."""
    c.rect(x, y, x + 19, y + 8, DGREY)
    c.rect(x + 1, y + 1, x + 18, y + 7, BLACK)
    c.text(x + 1, y + 2, "18:00", colour)


def dock():
    """Dock 3: scuffed white panels in red light, the countdown, and through the
    viewport the swollen sun and the dead freighter tumbling past.
    Shared: light grey (the panels), dark grey, black. Own: red, white, yellow."""
    c = Canvas(LGREY)
    # Panels, seams, and the klaxon light washing over them.
    for x in range(0, W, 16):
        c.vline(x, 0, 70, DGREY)
    for y in (22, 46):
        c.hline(0, W - 1, y, DGREY)
    c.rect(0, 0, W - 1, 5, BLACK)
    for x in (40, 120):
        c.rect(x - 3, 4, x + 3, 8, RED)                      # klaxons
        c.glow(x, 8, 60, 22, RED, steps=((1.0, 2), (0.65, 5), (0.35, 9)), only=LGREY)
    # The viewport: stars, the swollen red sun, the freighter.
    c.ellipse(96, 40, 78, 30, DGREY)
    c.ellipse(96, 40, 70, 26, BLACK)
    c.stars(78, 16, 114, 64, WHITE, 23, 3)
    c.ellipse(108, 30, 28, 10, RED)
    c.glow(108, 30, 44, 15, RED, steps=((1.0, 4),), only=BLACK)
    c.poly([(82, 50), (92, 42), (98, 46), (88, 56)], DGREY)  # the freighter, end over end
    c.line(86, 50, 94, 46, LGREY)
    c.resolve(RED, WHITE, BLACK)
    c.rect(0, 0, W - 1, 3, BLACK)
    # The countdown, and a dock number.
    countdown(c, 16, 28)
    c.rect(16, 52, 27, 62, DGREY)
    c.text(18, 55, "D3", WHITE) if False else c.text(19, 55, "3", WHITE)
    # The deck: scuffed plates, a hazard edge where the train was.
    c.rect(0, 70, W - 1, 95, DGREY)
    for x in range(-120, W + 120, 32):
        c.line(80 + (x - 80) // 3, 70, x, 95, BLACK)
    c.hline(0, W - 1, 78, BLACK)
    c.rect(0, 86, W - 1, 89, YELLOW)
    for x in range(0, W, 8):
        c.poly([(x, 86), (x + 3, 86), (x + 1, 89), (x - 2, 89)], BLACK)
    c.rect(0, 90, W - 1, 95, BLACK)                          # the drop: no train, gone
    return c


def medbay():
    """The medical bay: white light, one patient in cooling gel, Dr Kerr working over him.
    Shared: white, light grey, black. Own: cyan (the gel), red, green (the monitor)."""
    c = Canvas(WHITE)
    c.rect(0, 0, W - 1, 4, LGREY)
    for x in (30, 80, 130):                                  # strip lights
        c.rect(x - 12, 5, x + 12, 6, LGREY)
    c.rect(0, 60, W - 1, 95, LGREY)                          # the floor
    for y in (66, 74, 86):
        c.hline(0, W - 1, y, WHITE)
    c.rect(4, 14, 16, 26, RED)                               # a red cross on the wall
    c.rect(4, 14, 16, 26, WHITE, None, 16, only=None) if False else None
    c.rect(8, 15, 12, 25, WHITE)
    c.rect(5, 18, 15, 22, WHITE)
    # The monitor: a heartbeat, shallow.
    c.rect(124, 12, 155, 34, BLACK)
    c.line(126, 26, 134, 26, GREEN)
    c.line(134, 26, 137, 17, GREEN)
    c.line(137, 17, 139, 31, GREEN)
    c.line(139, 31, 141, 26, GREEN)
    c.line(141, 26, 153, 26, GREEN)
    c.vline(139, 34, 50, BLACK)
    # The bed, the engineer in cooling gel, an oxygen mask.
    c.rect(24, 52, 112, 56, BLACK)
    for x in (28, 106):
        c.rect(x, 56, x + 2, 72, BLACK)
    c.rect(26, 44, 110, 51, CYAN)
    c.rect(26, 40, 36, 44, WHITE)                            # the pillow
    c.ellipse(34, 40, 10, 3, BLACK)                          # his hair
    c.rect(36, 41, 40, 44, CYAN)                             # the mask
    c.line(40, 42, 54, 30, BLACK)                            # its tube
    # Dr Kerr, bent over him: a white coat outlined in black, dark hair, black gloves.
    coat = [(82, 70), (84, 36), (92, 30), (102, 33), (104, 70)]
    c.poly([(x + (1 if x > 92 else -1), y + (1 if y > 50 else -1)) for x, y in coat], BLACK)
    c.poly(coat, WHITE)
    c.line(96, 34, 99, 68, LGREY)                            # a fold
    c.rect(90, 54, 94, 60, RED)                              # the stain
    c.line(86, 38, 68, 46, BLACK, width=3)                   # an arm, reaching
    c.line(86, 38, 69, 46, WHITE)
    c.line(98, 38, 76, 48, BLACK, width=3)
    c.line(98, 38, 77, 48, WHITE)
    c.rect(65, 45, 68, 47, BLACK)                            # gloves
    c.rect(73, 47, 76, 49, BLACK)
    c.ellipse(93, 25, 12, 6, BLACK)                          # her hair, pinned up
    c.ellipse(97, 20, 6, 3, BLACK)
    c.rect(84, 70, 86, 76, BLACK)                            # legs
    c.rect(98, 70, 100, 76, BLACK)
    return c


def hydroponics():
    """Hydroponics: rows of plants under violet lamps, and Pell, sitting in the soil.
    Shared: black, green, brown (the soil, her hair). Own: purple (lamps), yellow (new
    leaves, her face in the lamplight), white."""
    c = Canvas(BLACK)
    # Violet lamps and their light.
    for x in range(10, W, 36):
        c.rect(x, 0, x + 18, 3, PURPLE)
        c.poly([(x, 4), (x + 18, 4), (x + 26, 30), (x - 8, 30)], PURPLE, BLACK, 3)
    # Three rows of plants receding: stems, paired leaves, new growth catching the light.
    for row, (base, h, step) in enumerate(((40, 7, 7), (52, 10, 9), (68, 14, 12))):
        c.rect(0, base, W - 1, base + 3, BROWN)                  # the trough
        c.hline(0, W - 1, base + 4, BLACK)
        for x in range(3 + row * 4, W, step):
            c.vline(x, base - h, base - 1, GREEN)
            for k in range(1, 4):
                y = base - k * h // 4
                c.line(x, y, x - 2 - k // 2, y - 2, GREEN)
                c.line(x, y, x + 2 + k // 2, y - 2, GREEN)
            c.rect(x - 1, base - h - 1, x + 1, base - h, YELLOW)
    # The soil, and Pell, cross-legged in it, not running anywhere.
    c.rect(0, 73, W - 1, 95, BROWN)
    for x in range(0, W, 6):
        c.set(x + (x // 6) % 3, 78 + (x * 7) % 14, BLACK)
    c.poly([(62, 94), (98, 94), (94, 84), (66, 84)], GREEN)   # crossed legs, green overalls
    c.hline(66, 94, 89, BLACK)
    c.poly([(68, 84), (70, 64), (90, 64), (92, 84)], GREEN)   # body
    c.vline(80, 66, 84, BLACK)
    c.line(70, 66, 66, 84, GREEN, width=2)                    # arms resting on her knees
    c.line(90, 66, 94, 84, GREEN, width=2)
    c.rect(64, 84, 67, 86, YELLOW)                            # hands
    c.rect(93, 84, 96, 86, YELLOW)
    c.ellipse(80, 55, 16, 8, BROWN)                           # her hair
    c.ellipse(80, 58, 10, 5, YELLOW)                          # her face, in the lamp light
    c.set(78, 57, BLACK)
    c.set(82, 57, BLACK)
    c.rect(76, 62, 84, 63, YELLOW)                            # her neck
    c.rect(100, 88, 103, 92, WHITE)                           # a trowel she isn't using
    return c


def command():
    """The command deck: a dome of stars, dead consoles, one that works, the captain
    shouting at the ceiling, and MERIDIAN's eye. The quarters door half open behind.
    Shared: black, dark grey, grey. Own: white (stars), cyan (the screen), blue (her
    coat), yellow (the eye, her hair), red (alarms)."""
    c = Canvas(BLACK)
    c.stars(0, 0, W - 1, 40, WHITE, 47, 11)
    c.arc((-40, 6, 200, 150), 180, 360, GREY, width=2)         # the dome's ribs
    c.arc((20, 10, 140, 140), 180, 360, DGREY, width=1)
    c.ellipse(80, 14, 14, 5, DGREY)
    c.ellipse(80, 14, 6, 3, YELLOW)                            # MERIDIAN, looking down
    c.rect(0, 64, W - 1, 95, DGREY)                            # the deck
    for x in range(0, W, 20):
        c.line(80 + (x - 80) // 3, 64, x + (x - 80) // 2, 95, BLACK)
    # Consoles in a ring, dead, but one.
    for x in range(4, W, 26):
        c.rect(x, 54, x + 18, 66, GREY)
        c.rect(x + 1, 55, x + 17, 58, BLACK)
        c.set(x + 3, 62, RED)
    c.rect(69, 50, 91, 66, GREY)
    c.rect(70, 51, 90, 58, CYAN)
    c.text(72, 53, "NO", BLACK)
    # The captain, from behind: a long blue coat, gold at the shoulders, a fist raised
    # at the ceiling.
    c.ellipse(56, 44, 10, 5, GREY)                             # grey hair, pinned up
    c.rect(55, 37, 57, 39, GREY)
    c.rect(54, 49, 58, 50, BLUE)                               # collar
    c.poly([(48, 51), (64, 51), (67, 86), (45, 86)], BLUE)     # coat
    c.vline(56, 60, 86, BLACK)                                 # the back seam
    c.rect(47, 51, 51, 52, GREY)                               # epaulettes
    c.rect(61, 51, 65, 52, GREY)
    c.line(47, 53, 44, 76, BLUE, width=2)                      # an arm at her side
    c.line(64, 53, 72, 30, BLUE, width=3)                      # the other, raised
    c.rect(71, 26, 74, 30, BLUE)                               # a fist
    c.rect(48, 86, 50, 92, BLACK)                              # boots
    c.rect(62, 86, 64, 92, BLACK)
    for colour in (YELLOW, BLUE, CYAN):
        c.resolve(colour, WHITE, BLACK)                        # stars give way
    # The quarters door, half open; the corner of a safe.
    c.rect(124, 26, 150, 66, GREY)
    c.rect(126, 28, 140, 66, BLACK)
    c.rect(132, 52, 140, 64, DGREY)
    return c


def reactor():
    """The reactor room: a cathedral of heat, the core through its glass, and the
    maintenance drone with its welding arm. One console lit: LOCKED BY MERIDIAN.
    Shared: red, black, orange. Own: yellow, white (the core), cyan (the drone's eye)."""
    c = Canvas(RED)
    # The walls: ribs climbing into the dark, ticking with heat.
    c.rect(0, 0, W - 1, 6, BLACK)
    for x in range(0, W, 12):
        c.line(x, 6, 80 + (x - 80) // 2, 0, BLACK)
        c.vline(x, 6, 78, ORANGE)
    c.vgrad(0, 6, W - 1, 30, BLACK, RED)
    # The core: a column of light behind a caged window.
    c.rect(62, 8, 98, 78, BLACK)
    c.rect(64, 10, 96, 78, ORANGE)
    c.rect(68, 10, 75, 78, YELLOW, ORANGE, 10)
    c.rect(84, 10, 91, 78, YELLOW, ORANGE, 10)
    c.rect(76, 10, 83, 78, WHITE)
    for y in range(16, 78, 10):
        c.hline(64, 96, y, BLACK)                              # the cage over the glass
    for x in (72, 88):
        c.vline(x, 10, 78, BLACK)
    # The floor: grating.
    c.rect(0, 78, W - 1, 95, BLACK)
    for x in range(0, W, 4):
        c.line(80 + (x - 80) // 3, 79, x + (x - 80) // 2, 95, RED)
    # The drone, the size of a fridge, and its welding arm.
    c.rect(12, 40, 36, 78, ORANGE)
    c.rect(14, 42, 34, 76, BLACK)
    c.rect(20, 48, 28, 52, CYAN)
    c.line(36, 56, 46, 46, ORANGE, width=2)
    c.line(46, 46, 52, 52, ORANGE, width=2)
    c.rect(52, 50, 54, 53, WHITE)
    # The console: LOCKED BY MERIDIAN.
    c.rect(112, 50, 154, 78, BLACK)
    c.rect(114, 52, 152, 66, ORANGE)
    c.rect(115, 53, 151, 65, BLACK)
    c.text(116, 54, "LOCKED BY", YELLOW)
    c.text(116, 60, "MERIDIAN", YELLOW)
    return c


def safe():
    """The captain's quarters: a bunk, a photograph of a girl, and the safe open on the
    seed vault, frosted and humming.
    Shared: dark grey, black, grey. Own: blue (the blanket), white, cyan (the vault),
    yellow (the photo, the keypad)."""
    c = Canvas(DGREY)
    for x in range(0, W, 20):
        c.vline(x, 0, 74, BLACK)
    c.rect(0, 74, W - 1, 95, GREY)
    for y in (80, 88):
        c.hline(0, W - 1, y, DGREY)
    # The bunk.
    c.rect(4, 52, 64, 74, BLACK)
    c.rect(6, 48, 62, 60, BLUE)
    c.rect(6, 44, 22, 47, WHITE)
    # The photograph: a girl, and her name underneath.
    c.rect(70, 15, 90, 40, BLACK)
    c.rect(72, 16, 88, 30, YELLOW)                           # sepia
    c.ellipse(80, 22, 12, 6, BLACK)                          # her hair
    c.ellipse(80, 23, 7, 4, YELLOW)                          # her face
    c.set(79, 23, BLACK)
    c.set(81, 23, BLACK)
    c.poly([(74, 30), (76, 27), (84, 27), (86, 30)], BLACK)  # her shoulders
    c.text(72, 33, "ASHA", WHITE)
    # The safe, open: the vault inside, so cold it smokes.
    c.rect(104, 28, 156, 82, GREY)
    c.rect(108, 32, 152, 78, BLACK)
    c.rect(98, 30, 103, 80, GREY)                            # its door, swung open
    c.rect(99, 44, 102, 50, YELLOW)                          # the keypad
    c.rect(122, 42, 138, 74, CYAN)
    c.rect(122, 42, 138, 74, GREY, CYAN, 4)                  # frost
    for y in (50, 58, 66):
        c.hline(124, 136, y, BLACK)
    c.ellipse(130, 36, 18, 3, WHITE, BLACK, 4)               # cold, coming off it
    return c


PICTURES = (("concourse", fare.concourse), ("platform_bench", fare.platform_bench),
            ("dock", dock), ("medbay", medbay), ("hydroponics", hydroponics),
            ("command", command), ("static", fare.static), ("reactor", reactor),
            ("safe", safe), ("stationmaster", fare.stationmaster))


def main():
    paths = []
    for name, draw in PICTURES:
        path = os.path.join(HERE, name + ".png")
        draw().save(path)
        paths.append(path)
    return 0 if report(paths) else 1


if __name__ == "__main__":
    sys.exit(main())
