"""Placeholder pictures for Eighteen Minutes: simple shapes, to be replaced by real art.

    python3 content/s1/01-eighteen-minutes/pictures/sketch.py

Writes one 160x96 PNG per picture the Departure shows, in the C64's colours, like The
Fare's (content/s1/00-the-fare/pictures/sketch.py, whose Waystation pictures this one
draws again: the concourse, the platform and the Static).
"""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "fare_sketch", os.path.join(HERE, "..", "..", "00-the-fare", "pictures", "sketch.py"))
fare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fare)

W, H, new = fare.W, fare.H, fare.new
BLACK, WHITE, RED, CYAN, PURPLE, GREEN, BLUE, YELLOW = (
    fare.BLACK, fare.WHITE, fare.RED, fare.CYAN, fare.PURPLE, fare.GREEN, fare.BLUE, fare.YELLOW)
ORANGE, BROWN, DGREY, GREY, LGREEN, LBLUE, LGREY = (
    fare.ORANGE, fare.BROWN, fare.DGREY, fare.GREY, fare.LGREEN, fare.LBLUE, fare.LGREY)


def countdown(d, x, y, colour=RED):
    """A screen saying 18:00, in blocks."""
    d.rectangle((x, y, x + 30, y + 12), fill=BLACK, outline=GREY)
    for cx in (x + 3, x + 9, x + 17, x + 23):
        d.rectangle((cx, y + 3, cx + 4, y + 9), outline=colour)
    d.rectangle((x + 14, y + 4, x + 15, y + 5), fill=colour)
    d.rectangle((x + 14, y + 7, x + 15, y + 8), fill=colour)


def dock():
    img, d = new(DGREY)
    d.rectangle((0, 0, W, 12), fill=RED)                # the klaxon light
    d.rectangle((0, 74, W, H), fill=GREY)               # the deck
    for x in range(0, W, 16):
        d.line((x, 74, x - 24, H), fill=LGREY)
    for x in range(0, W, 32):                           # white panels
        d.rectangle((x + 2, 16, x + 29, 70), fill=LGREY, outline=WHITE)
    d.ellipse((96, 22, 150, 64), fill=BLACK, outline=WHITE)    # the viewport
    d.ellipse((128, 30, 144, 46), fill=RED)             # the swollen sun
    d.polygon([(104, 50), (116, 42), (120, 48), (108, 56)], fill=GREY)   # the freighter
    countdown(d, 20, 30)
    return img


def medbay():
    img, d = new(WHITE)
    d.rectangle((0, 70, W, H), fill=LGREY)
    d.rectangle((30, 50, 130, 58), fill=GREY)           # the bed
    for x in (34, 124):
        d.rectangle((x, 58, x + 2, 74), fill=DGREY)
    d.ellipse((34, 42, 48, 52), fill=fare.PINK)         # the engineer
    d.rectangle((48, 44, 120, 52), fill=CYAN)           # in cooling gel
    d.rectangle((90, 16, 102, 50), fill=LGREY)          # Dr Kerr's stained coat
    d.ellipse((90, 4, 102, 16), fill=fare.PINK)
    d.rectangle((94, 30, 98, 34), fill=RED)
    d.rectangle((136, 10, 156, 40), fill=BLACK)         # a monitor
    d.line((138, 28, 144, 28, 146, 18, 148, 34, 150, 26, 154, 26), fill=LGREEN)
    return img


def hydroponics():
    img, d = new(BLACK)
    for x in range(0, W, 40):                           # violet lamps
        d.rectangle((x + 8, 0, x + 32, 4), fill=PURPLE)
        d.polygon([(x + 8, 4), (x + 32, 4), (x + 40, 40), (x, 40)], fill=BLUE)
    for row, y in enumerate((44, 64)):                  # rows of plants
        d.rectangle((0, y + 12, W, y + 16), fill=BROWN)
        for x in range(4 + row * 6, W, 12):
            d.ellipse((x, y, x + 10, y + 13), fill=(GREEN, LGREEN)[(x // 12) % 2])
    d.rectangle((0, 82, W, H), fill=BROWN)              # the soil
    d.ellipse((72, 66, 88, 80), fill=fare.PINK)         # Pell, cross-legged in it
    d.polygon([(66, 92), (94, 92), (88, 78), (72, 78)], fill=GREEN)
    return img


def command():
    img, d = new(BLACK)
    for x in range(0, W, 3):                            # stars through the dome
        if (x * 7) % 11 < 2:
            d.point((x, (x * 13) % 40), fill=WHITE)
    d.arc((-40, 10, 200, 160), 180, 360, fill=GREY, width=3)
    d.rectangle((0, 70, W, H), fill=DGREY)
    for x in range(4, W, 26):                           # the dead consoles
        d.rectangle((x, 60, x + 18, 72), fill=GREY)
    d.rectangle((70, 58, 90, 72), fill=GREY)
    d.rectangle((72, 60, 88, 66), fill=CYAN)            # the one that works
    d.polygon([(52, 92), (56, 42), (66, 42), (70, 92)], fill=BLUE)   # the captain's coat
    d.ellipse((54, 30, 68, 44), fill=fare.PINK)
    d.rectangle((126, 30, 154, 70), fill=BROWN)         # the quarters door, half open
    d.rectangle((140, 50, 152, 66), fill=LGREY)         # the corner of a safe
    d.ellipse((76, 8, 84, 16), fill=YELLOW)             # MERIDIAN's eye
    return img


def reactor():
    img, d = new(RED)
    d.rectangle((0, 0, W, 8), fill=BLACK)
    d.rectangle((0, 78, W, H), fill=DGREY)
    for x in range(0, W, 10):                           # the hot walls ticking
        d.line((x, 8, x, 78), fill=ORANGE)
    d.rectangle((60, 14, 100, 76), fill=DGREY, outline=GREY)     # the hatch
    d.ellipse((70, 30, 90, 50), fill=YELLOW)            # the reactor, through glass
    d.rectangle((20, 34, 44, 56), fill=GREY)            # the drone, the size of a fridge
    d.rectangle((24, 38, 30, 42), fill=CYAN)
    d.line((44, 46, 54, 40, 58, 46), fill=GREY, width=2)          # its welding arm
    d.ellipse((56, 42, 62, 48), fill=WHITE)
    return img


def safe():
    img, d = new(DGREY)
    d.rectangle((0, 76, W, H), fill=BROWN)              # the floor
    d.rectangle((6, 50, 60, 76), fill=BLUE)             # the bunk
    d.rectangle((6, 46, 30, 52), fill=WHITE)
    d.rectangle((70, 14, 90, 38), fill=LGREY, outline=WHITE)    # a photograph of a girl
    d.ellipse((76, 18, 84, 26), fill=fare.PINK)
    d.rectangle((76, 26, 84, 36), fill=YELLOW)
    d.rectangle((100, 30, 156, 80), fill=GREY, outline=LGREY)   # the safe, open
    d.rectangle((104, 34, 152, 76), fill=BLACK)
    d.rectangle((118, 44, 138, 72), fill=CYAN, outline=WHITE)   # the seed vault, frosted
    for y in (50, 58, 66):
        d.line((120, y, 136, y), fill=LBLUE)
    d.rectangle((92, 34, 98, 48), fill=LGREY)           # the keypad
    return img


def main():
    for name, draw in (("concourse", fare.concourse), ("platform_bench", fare.platform_bench),
                       ("dock", dock), ("medbay", medbay), ("hydroponics", hydroponics),
                       ("command", command), ("static", fare.static), ("reactor", reactor),
                       ("safe", safe), ("stationmaster", fare.stationmaster)):
        draw().save(os.path.join(HERE, name + ".png"))
        print("wrote", name + ".png")


if __name__ == "__main__":
    main()
