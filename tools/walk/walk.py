"""Walking a floor on the C64 (docs/walk.md): the reference the cartridge's walking engine
(cart/walk/) is held to, frame by frame.

    import walk
    floor = walk.Floor(yard, floor_number)          # the area, its look, where you start
    data = floor.asset()                            # what the C64 is given (docs/walk.md)
    frames = walk.play(floor, sticks)               # each frame: the leader and the camera

    python3 tools/walk/walk.py asset YARD FLOOR OUT  write the floor's asset
    python3 tools/walk/walk.py show YARD FLOOR       draw the area, the start marked

The floor is the explore prototype's (tools/rooms/rooms.py): its nine rooms side by side
as one area of 48 x 24 squares, in the look the prototype gives its floor, each square
dressed as rooms.js dresses it (a variant, or scenery). Walking and the camera follow the
prototype's rules, in whole numbers a C64 can do: see docs/walk.md, "The rules".
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "rooms"))
import art  # noqa: E402
import rooms  # noqa: E402

LOOKS = ["forest", "mountain", "town", "dungeon"]
SQUARES_X, SQUARES_Y = rooms.COLS * rooms.W, rooms.ROWS * rooms.H      # 48 x 24
CHARS_X, CHARS_Y = 2 * SQUARES_X, 2 * SQUARES_Y                        # 96 x 48
BLOCKED = 0x80                  # a square's byte: its tile (0-31), and this if you can't stand there
WALL, PIT, HAZARD = 1, 2, 5

# The screen: 38 columns and 24 rows show (the VIC's narrower window, so the fine scroll's
# edges don't), of 40 x 25 in the screen's memory.
VIEW_W, VIEW_H = 38 * 8, 24 * 8                                         # 304 x 192 pixels
CAM_X_MAX = (CHARS_X - 40) * 8 + 7                                      # 455
CAM_Y_MAX = (CHARS_Y - 25) * 8 + 7                                      # 191

# Walking: a position is in sixteenths of a pixel (16-bit); 23 of them a frame, 1.44 pixels,
# 72 a second: the prototype's 4.5 squares a second. On a diagonal, 16 each way.
SUB = 16
SPEED, SPEED_DIAG = 23, 16
BODY_LO, BODY_HI = 3, 12        # the body: pixels 3-12 of its 16-pixel square, both ways
NUDGE = 7                       # round a corner: within 7 pixels of the way through

# The joystick: port 2's bits, as CIA 1 reads them (0: pushed).
UP, DOWN, LEFT, RIGHT, FIRE = 1, 2, 4, 8, 16

# The scroller's stages (docs/walk.md, "The scroller").
IDLE, SHIFTED, COLOURED = 0, 1, 2


def dress_hash(yard, floor, room, x, y):
    """rooms.js's dress hash: 0-255 for a room's square."""
    n = ((floor * 9 + room) * 8 + y) * 16 + x
    return (((n ^ (yard << 4)) & 0xFFFFFFFF) * 0x9E3779B1 & 0xFFFFFFFF) >> 24


class Floor:
    def __init__(self, yard, number, look=None):
        self.yard, self.number = yard, number
        self.f = rooms.build(yard, number)
        self.look = look or LOOKS[(number - 1) % len(LOOKS)]
        self.art = art.load(art.tiles_file(16, self.look))
        names = [e.name for e in self.art.entries]
        self.names = names
        scenery = [n for n in names[8:] if art.variant_of(n) is None]
        variants = {t: [n for n in names[8:] if art.variant_of(n) == t] for t in art.TERRAIN}
        self.squares = [[0] * SQUARES_X for _ in range(SQUARES_Y)]
        for r in self.f["rooms"]:
            ox, oy = (r["i"] % rooms.COLS) * rooms.W, (r["i"] // rooms.COLS) * rooms.H
            taken = {(e["x"], e["y"]) for e in r["foes"]}
            if r["stairs"]:
                taken.add(tuple(r["stairs"]))
            if r["cache"]:
                taken.add((r["cache"]["x"], r["cache"]["y"]))
            standing = {(e["x"], e["y"]) for e in r["foes"]}           # foes and people block
            if r.get("talk"):
                standing.add((r["talk"]["x"], r["talk"]["y"]))
            for y in range(rooms.H):
                for x in range(rooms.W):
                    t = int(r["rows"][y][x])
                    base = art.TERRAIN[t]
                    h = dress_hash(yard, number, r["i"], x, y)
                    if t == 0 and scenery and h < 16 and (x, y) not in taken:
                        name = scenery[h % len(scenery)]
                    elif variants[base] and h & 7 == 0:
                        name = variants[base][(h >> 3) % len(variants[base])]
                    else:
                        name = base
                    blocked = t in (WALL, PIT, HAZARD) or (x, y) in standing
                    self.squares[oy + y][ox + x] = names.index(name) | (BLOCKED if blocked else 0)
        # Where you start: the start room's (7, 3), as the prototype puts you, or its door.
        s = self.f["start"]
        sx, sy = (s % rooms.COLS) * rooms.W + 7, (s // rooms.COLS) * rooms.H + 3
        self.start = (sx, sy)

    def free(self, sx, sy):
        return 0 <= sx < SQUARES_X and 0 <= sy < SQUARES_Y and not self.squares[sy][sx] & BLOCKED

    def char(self, cx, cy):
        """The character on the area's character (cx, cy), and its colour RAM's value."""
        if not (0 <= cx < CHARS_X and 0 <= cy < CHARS_Y):
            return 0, 0
        t = self.squares[cy >> 1][cx >> 1] & 0x1F
        return 1 + t * 4 + (cy & 1) * 2 + (cx & 1), self.art.entries[t].colour | 8

    def charset(self):
        """The look's tiles as characters, seamless (the last column and row the ones beside
        them again, as the prototype draws a room while you walk): 0 blank, then each
        tile's four, top left, top right, bottom left, bottom right."""
        code = {"k": 0, "d": 1, "g": 2, "o": 3}
        out = bytearray(8)
        for e in self.art.entries:
            rows = [r[:-1] + r[-2] for r in e.rows[:-1]]
            rows.append(rows[-1])
            for cy in range(2):
                for cx in range(2):
                    for y in range(8):
                        b = 0
                        for x in range(4):
                            b = (b << 2) | code[rows[cy * 8 + y][cx * 4 + x]]
                        out.append(b)
        return bytes(out)

    def asset(self):
        """What the C64 is given (docs/walk.md, "The floor's asset"):

            0      the background and the two shared colours (3)
            3      the number of tiles (1)
            4      each tile's colour RAM value (32)
            36     where you start: square x, square y (2)
            38     the squares, 48 x 24, a row at a time (1152)
            1190   the characters, 8 bytes each, 0 blank then 4 a tile (8 + 32 a tile)"""
        out = bytearray([self.art.background, *self.art.shared, len(self.art.entries)])
        cols = [e.colour | 8 for e in self.art.entries]
        out += bytes(cols + [0] * (32 - len(cols)))
        out += bytes(self.start)
        for row in self.squares:
            out += bytes(row)
        out += self.charset()
        return bytes(out)


# ------------------------------------------------------------------ walking

def fits(floor, px, py):
    """The body, at pixel (px, py) (its square's top left), on squares you can stand on."""
    x0, x1 = (px + BODY_LO) >> 4, (px + BODY_HI) >> 4
    y0, y1 = (py + BODY_LO) >> 4, (py + BODY_HI) >> 4
    return all(floor.free(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))


def slide(floor, pos, axis, d):
    """Move pos (sixteenths of a pixel, [x, y]) by d along axis (0 x, 1 y). Blocked, and
    within NUDGE pixels of a way through on the other axis, step toward it instead."""
    moved = list(pos)
    moved[axis] += d
    if fits(floor, moved[0] >> 4, moved[1] >> 4):
        pos[axis] = moved[axis]
        return
    other = 1 - axis
    p = pos[other] >> 4
    c = (p + 8) & ~15                                   # the nearest square's edge
    if abs(p - c) > NUDGE:
        return
    test = list(moved)
    test[other] = c * SUB
    if not fits(floor, test[0] >> 4, test[1] >> 4):
        return
    gap = c * SUB - pos[other]
    step = min(abs(d), abs(gap))
    pos[other] += step if gap > 0 else -step


def walk(floor, pos, stick):
    """One frame's walk: the joystick's bits (0 pushed) move pos."""
    dx = (1 if not stick & RIGHT else 0) - (1 if not stick & LEFT else 0)
    dy = (1 if not stick & DOWN else 0) - (1 if not stick & UP else 0)
    sp = SPEED_DIAG if dx and dy else SPEED
    if dx:
        slide(floor, pos, 0, dx * sp)
    if dy:
        slide(floor, pos, 1, dy * sp)


# ------------------------------------------------------------------ the camera

def target(pos):
    tx = (pos[0] >> 4) + 8 - VIEW_W // 2
    ty = (pos[1] >> 4) + 8 - VIEW_H // 2
    return max(0, min(CAM_X_MAX, tx)), max(0, min(CAM_Y_MAX, ty))


def ease(cam, want):
    """A frame's step of the camera toward where it should be: an eighth of the way
    (rounded toward it), at least a pixel, at most two."""
    d = want - cam
    if d == 0:
        return cam
    s = abs(d) >> 3
    s = max(1, min(2, s))
    return cam + (s if d > 0 else -s)


def clamp_cell(v, cell):
    return max(cell * 8, min(cell * 8 + 7, v))


def play(floor, sticks):
    """Each frame from the first shown: (leader x, leader y in sixteenths, camera x, camera y,
    the scroller's stage). sticks[n] is the joystick as frame n's main loop reads it; the
    camera it decides is shown from frame n + 1 (docs/walk.md, "A frame")."""
    pos = [floor.start[0] * 16 * SUB, floor.start[1] * 16 * SUB]
    cam = list(target(pos))
    stage, dirs, out = IDLE, (0, 0), []
    for stick in sticks:
        out.append((pos[0], pos[1], cam[0], cam[1], stage))
        walk(floor, pos, stick)
        want = target(pos)
        nxt = [ease(cam[0], want[0]), ease(cam[1], want[1])]
        if stage == IDLE:
            d = tuple((nxt[i] >> 3) - (cam[i] >> 3) for i in range(2))
            d = tuple(max(-1, min(1, v)) for v in d)
            if d != (0, 0):
                dirs, stage = d, SHIFTED                # the screen shifted into the back buffer
            nxt = [clamp_cell(nxt[i], cam[i] >> 3) for i in range(2)]
        elif stage == SHIFTED:
            stage = COLOURED                            # the colours shifted; swap next
            nxt = [clamp_cell(nxt[i], (cam[i] >> 3) + dirs[i]) for i in range(2)]
        else:
            stage = IDLE                                # the swap frame: nothing heavy
            nxt = [clamp_cell(nxt[i], cam[i] >> 3) for i in range(2)]
        cam = nxt
    return out


# ------------------------------------------------------------------ the command line

def main(argv):
    if len(argv) == 5 and argv[1] == "asset":
        with open(argv[4], "wb") as f:
            f.write(Floor(int(argv[2]), int(argv[3])).asset())
        return 0
    if len(argv) == 4 and argv[1] == "show":
        fl = Floor(int(argv[2]), int(argv[3]))
        print(f"yard {fl.yard}, floor {fl.number}, the {fl.look}: you start at {fl.start}")
        for y, row in enumerate(fl.squares):
            print("".join("@" if (x, y) == fl.start else "#" if v & BLOCKED else "."
                          for x, v in enumerate(row)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
