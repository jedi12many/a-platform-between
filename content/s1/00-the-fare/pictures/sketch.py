"""Placeholder pictures for The Fare: simple shapes, to be replaced by real art.

    python3 content/s1/00-the-fare/pictures/sketch.py

Writes one 160x96 PNG per picture the Departure shows (its `~ picture` names), in the
C64's colours. Draw over them, or replace them: tools/c64pic.py turns any 160x96 PNG
into what the C64 shows (docs/c64.md). Pixels are twice as wide as they are tall on
the screen.
"""

import os
import random

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 160, 96

BLACK, WHITE, RED, CYAN, PURPLE, GREEN, BLUE, YELLOW = (
    (0x00, 0x00, 0x00), (0xFF, 0xFF, 0xFF), (0x68, 0x37, 0x2B), (0x70, 0xA4, 0xB2),
    (0x6F, 0x3D, 0x86), (0x58, 0x8D, 0x43), (0x35, 0x28, 0x79), (0xB8, 0xC7, 0x6F))
ORANGE, BROWN, PINK, DGREY, GREY, LGREEN, LBLUE, LGREY = (
    (0x6F, 0x4F, 0x25), (0x43, 0x39, 0x00), (0x9A, 0x67, 0x59), (0x44, 0x44, 0x44),
    (0x6C, 0x6C, 0x6C), (0x9A, 0xD2, 0x84), (0x6C, 0x5E, 0xB5), (0x95, 0x95, 0x95))


def new(background):
    img = Image.new("RGB", (W, H), background)
    return img, ImageDraw.Draw(img)


def static():
    img, d = new(BLACK)
    rng = random.Random(1985)
    for y in range(H):
        for x in range(0, W, 2):
            v = rng.random()
            if v < 0.18:
                d.rectangle((x, y, x + 1, y), fill=LGREY)
            elif v < 0.24:
                d.rectangle((x, y, x + 1, y), fill=DGREY)
    # A hand, reaching in through the static.
    d.polygon([(96, 0), (112, 0), (110, 30), (104, 44), (96, 46), (92, 40), (94, 24)], fill=WHITE)
    for fx in (90, 95, 100, 105):
        d.rectangle((fx, 44, fx + 3, 58 + (fx % 7)), fill=WHITE)
    return img


def platform_bench():
    img, d = new(BLUE)
    for y in range(0, 60, 6):                           # the grey shimmer past the roof
        d.line((0, y + 30, W, y + 26), fill=LBLUE)
    for x in range(0, W, 40):                           # green iron arches and glass
        d.arc((x - 6, -30, x + 46, 40), 180, 360, fill=GREEN, width=3)
        d.line((x, 0, x, 40), fill=GREEN, width=2)
    d.rectangle((0, 0, W, 4), fill=GREEN)
    d.rectangle((0, 66, W, H), fill=DGREY)              # the platform
    d.line((0, 66, W, 66), fill=GREY)
    d.rectangle((60, 14, 100, 22), fill=WHITE)          # ARRIVALS -- ALL LINES
    d.line((80, 4, 80, 14), fill=GREY)
    for x in range(63, 98, 4):
        d.rectangle((x, 17, x + 2, 19), fill=BLACK)
    d.rectangle((52, 56, 108, 60), fill=BROWN)          # the bench
    d.rectangle((52, 48, 108, 51), fill=BROWN)
    for x in (56, 102):
        d.rectangle((x, 60, x + 2, 70), fill=BROWN)
    return img


def concourse():
    img, d = new(BLACK)
    d.rectangle((0, 70, W, H), fill=DGREY)              # tiled floor
    for x in range(0, W, 8):
        d.line((x, 70, x - 20, H), fill=GREY)
    for x in range(-20, W, 50):                         # iron arches
        d.arc((x, 0, x + 60, 120), 180, 360, fill=GREY, width=3)
    d.rectangle((44, 10, 116, 34), fill=BLACK, outline=GREY)   # the departure board
    for row in range(3):
        for x in range(48, 112, 4):
            if (x + row * 3) % 7:
                d.rectangle((x, 14 + row * 7, x + 1, 17 + row * 7), fill=YELLOW)
    d.rectangle((126, 40, 150, 70), fill=ORANGE)        # The Buffer Stop's warm door
    d.rectangle((130, 44, 146, 70), fill=YELLOW)
    d.rectangle((124, 32, 152, 38), fill=RED)           # its sign: a red barrier
    return img


def buffer_stop():
    img, d = new(BROWN)
    d.rectangle((0, 0, W, 10), fill=BLACK)
    d.rectangle((0, 62, W, H), fill=ORANGE)             # the bar
    d.rectangle((0, 60, W, 63), fill=YELLOW)
    for x in range(8, 70, 9):                           # bottles
        d.rectangle((x, 30, x + 3, 42), fill=(GREEN, CYAN, PURPLE, RED)[x % 4])
    d.line((4, 43, 74, 43), fill=YELLOW)
    d.rectangle((96, 26, 104, 62), fill=BROWN, outline=ORANGE)  # Fen: bark,
    d.ellipse((84, 8, 116, 34), fill=GREEN)                    # leaves,
    d.ellipse((94, 14, 106, 24), fill=LGREEN)                  # and the glow
    d.rectangle((108, 36, 114, 40), fill=RED)                  # a rag on fire
    d.rectangle((132, 30, 158, 62), fill=PURPLE)        # the corner booth
    d.rectangle((142, 18, 150, 40), fill=BLACK)         # someone tall in it
    return img


def stationmaster():
    img, d = new(BLACK)
    d.rectangle((0, 70, W, H), fill=BROWN)              # the table
    d.polygon([(56, 96), (64, 24), (96, 24), (104, 96)], fill=PURPLE)   # the velvet coat
    d.ellipse((66, 2, 94, 30), fill=DGREY)              # a polite arrangement of shadow
    d.rectangle((64, 76, 96, 90), fill=YELLOW)          # the brass ledger
    d.line((80, 76, 80, 90), fill=ORANGE)
    d.rectangle((20, 40, 26, 70), fill=DGREY)           # a lamp
    d.ellipse((12, 30, 34, 44), fill=GREEN)
    return img


def main():
    for name, draw in (("static", static), ("platform_bench", platform_bench),
                       ("concourse", concourse), ("buffer_stop", buffer_stop),
                       ("stationmaster", stationmaster)):
        draw().save(os.path.join(HERE, name + ".png"))
        print("wrote", name + ".png")


if __name__ == "__main__":
    main()
