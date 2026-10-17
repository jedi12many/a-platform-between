"""Walking a floor on the C64 (docs/walk.md): the reference the cartridge's walking engine
(cart/walk/) is held to, frame by frame.

    import walk
    floor = walk.Floor(yard, floor_number)          # the area, its look, where you start
    data = floor.asset()                            # what the C64 is given (docs/walk.md)
    frames = walk.play(floor, sticks)               # each frame: the leader and the camera

    python3 tools/walk/walk.py asset YARD FLOOR DIR [unseen]   write the floor's asset:
                                                    DIR/floor.bin and DIR/squares.bin
    python3 tools/walk/walk.py show YARD FLOOR      draw the area, the start marked

The floor is the explore prototype's: an open floor (docs/open-floors.md: build_open in
tools/rooms/rooms.py, 48 x 24 to 80 x 40), in the look the prototype gives its floor, each
square dressed as rooms.js dresses it (a variant, or scenery). Walking and the camera follow the prototype's
rules, in whole numbers a C64 can do: see docs/walk.md, "The rules".
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "rooms"))
sys.path.insert(0, os.path.join(HERE, "..", "rules"))
sys.path.insert(0, os.path.join(HERE, "..", "registry"))
import art  # noqa: E402
import battlegfx  # noqa: E402
import registry  # noqa: E402
import rooms  # noqa: E402
import seeing  # noqa: E402

LOOKS = ["forest", "mountain", "town", "dungeon"]
# A floor's size: any, up to 80 x 48 squares (the engine keeps a row of squares in a page:
# its colours, two bytes a square, then the squares, a byte each: 3 x 80 <= 256).
SQUARES_X_MAX, SQUARES_Y_MAX = 80, 48
BLOCKED = 0x80                  # a square's byte: its tile (0-31), and this if you can't stand there
WALL, PIT, HAZARD = 1, 2, 5

# The screen: 38 columns and 24 rows show (the VIC's narrower window, so the fine scroll's
# edges don't), of 40 x 25 in the screen's memory.
VIEW_W, VIEW_H = 38 * 8, 24 * 8                                         # 304 x 192 pixels

# Walking: a position is in sixteenths of a pixel (16-bit); 23 of them a frame, 1.44 pixels,
# 72 a second: the prototype's 4.5 squares a second. On a diagonal, 16 each way.
SUB = 16
SPEED, SPEED_DIAG = 23, 16
BODY_LO, BODY_HI = 3, 12        # the body: pixels 3-12 of its 16-pixel square, both ways
NUDGE = 7                       # round a corner: within 7 pixels of the way through

# The joystick: port 2's bits, as CIA 1 reads them (0: pushed).
UP, DOWN, LEFT, RIGHT, FIRE = 1, 2, 4, 8, 16

# The scroller's stages (docs/walk.md, "The scroller").
IDLE, HALF, SHIFTED, SHADED, COLOURED = 0, 1, 2, 3, 4

# The figures (docs/walk.md, "The figures"): the party, in marching order (the explore
# prototype's four, by their races), and the floor's foes and people, as sprites.
PARTY = ["SALVAGED", "CHRONOMITE", "RAD_DRYAD", "GLASSFOLK"]   # Warden, Rogue, Channeler, Medic
PEOPLE = {"trader": "GLASSFOLK", "courier": "HUMAN"}
KINDS_MAX, FIGURES_MAX = 12, 80
BANDS_MAX = 24                  # seeing's bands (docs/open-floors.md)
SEE_LOG = 0xAC00                # each step's checks, for the tests (walk.inc)
PLACE_SPEED = 2                 # a traveler's walk to their place in a fight: pixels a frame
SEE_SHOWN = 8                   # a step's checks shown this many frames on (watch.s)
NO_BAND = 0xFF                  # a figure that's no band's: a person
# A floor's light by its look (the arena's explore prototype has the same): seeing's ranges
# and modifiers.
LIGHT_OF = {"forest": seeing.DAY, "mountain": seeing.DAY, "town": seeing.DUSK, "dungeon": seeing.NIGHT}
GAP = 9                         # trail entries between travelers in marching order (~13 pixels)
TRAIL = 32                      # the leader's trail kept
SHAPE_POINTER = 0x40            # shape s is at $D000 + 64 s: the VIC's pointer $40 + s
SPRITE_DX, SPRITE_DY = 27, 47   # a figure's sprite, from its square's pixel less the camera
SPRITE_X_MIN, SPRITE_X_MAX = 8, 334
SPRITE_Y_MIN, SPRITE_Y_MAX = 35, 245     # (a sprite at 246 would still be on at the HUD's start)
REUSE = 23                      # a sprite reused: the next one at least 23 lines below
EVENTS_MAX = 26                 # reuses a frame (the C64's program has room for no more)
FIRST_VIEW, LAST_VIEW = 55, 246  # the view's lines (24 rows); the border's black outside them
EVENT_LAST = 238                # no reuse set on a line after this (the bottom's interrupt next)

# The HUD (docs/walk.md, "The HUD"): in the bottom border, lines 268-288, two sprites a
# traveler: their portrait (their kind's shape facing right, multicolour) and their health
# (hires: the number, a bar, their class's first three letters), from the explore
# prototype's travelers at level 1.
PARTY_CLASSES = ["WARDEN", "ROGUE", "CHANNELER", "MEDIC"]
HUD_Y = 11                      # line 267's low byte: shown from 268
HUD_FIRST_X, HUD_STEP = 39, 80  # traveler k's portrait at 39 + 80 k, their health 24 on
HUD_COLOUR = 13                 # light green
HUD_SHAPES = 24                 # the health's shapes: 24-27 (31 is the empty one)
BLANK = 31
SPRITE_MC1, SPRITE_MC2 = 0, 15  # black (the outline), light grey: as the cartridge sets them


# A 3 x 5 font for the HUD: each character five rows of three bits.
FONT = {
    "0": "111 101 101 101 111", "1": "010 110 010 010 111", "2": "111 001 111 100 111",
    "3": "111 001 011 001 111", "4": "101 101 111 001 001", "5": "111 100 111 001 111",
    "6": "111 100 111 101 111", "7": "111 001 010 010 010", "8": "111 101 111 101 111",
    "9": "111 101 111 001 111", "/": "001 001 010 100 100",
    "A": "010 101 111 101 101", "C": "011 100 100 100 011", "D": "110 101 101 101 110",
    "E": "111 100 110 100 111", "G": "011 100 101 101 011", "H": "101 101 111 101 101",
    "M": "101 111 111 101 101", "N": "110 101 101 101 101", "O": "010 101 101 101 010",
    "R": "110 101 110 101 101", "W": "101 101 111 111 101",
}


def text(rows, x, y, s):
    """Write s into rows (of 0/1) at (x, y), 4 pixels a character."""
    for ch in s:
        for r, bits in enumerate(FONT[ch].split()):
            for i, b in enumerate(bits):
                if b == "1":
                    rows[y + r][x + i] = 1
        x += 4


def dress_hash(yard, floor, room, x, y):
    """rooms.js's dress hash: 0-255 for a room's square."""
    n = ((floor * 9 + room) * 8 + y) * 16 + x
    return (((n ^ (yard << 4)) & 0xFFFFFFFF) * 0x9E3779B1 & 0xFFFFFFFF) >> 24


class Floor:
    def __init__(self, yard, number, look=None, unseen=False):
        self.yard, self.number = yard, number
        self.look = look or LOOKS[(number - 1) % len(LOOKS)]
        self.art = art.load(art.tiles_file(16, self.look))
        names = [e.name for e in self.art.entries]
        self.names = names
        scenery = [n for n in names[8:] if art.variant_of(n) is None]
        variants = {t: [n for n in names[8:] if art.variant_of(n) == t] for t in art.TERRAIN}
        self.kinds = list(PARTY)
        self.figures = []
        self.bands = []                             # seeing's
        self.light = LIGHT_OF[self.look]
        self.seed = ((yard * 31 + number * 977) & 0xFFFF) or 1
        self.notice, self.stealth = self.senses()
        self._open(scenery, variants, unseen)

    def _open(self, scenery, variants, unseen):
        """An open floor (docs/open-floors.md): build_open's, each square dressed as rooms.js
        dresses an open floor's (one area, no room: the stairs not dressed), its bands' foes
        and its people standing where they stand; its bands hidden till spotted, and
        looking for the party (seeing), unless unseen: every foe shown, none looking (the
        engine's test of a crowd)."""
        o = self.f = rooms.build_open(self.yard, self.number)
        self.w, self.h = o["w"], o["h"]
        assert self.w <= SQUARES_X_MAX and self.h <= SQUARES_Y_MAX
        standing = [(f["x"], f["y"], f["name"], NO_BAND if unseen else k)
                    for k, b in enumerate(o["bands"]) for f in b["foes"]]
        standing += [(p["x"], p["y"], PEOPLE[p["who"]], NO_BAND) for p in o["people"]]
        taken = {(x, y) for x, y, _, _ in standing}
        senses = registry.load_senses()
        assert len(o["bands"]) <= BANDS_MAX
        self.bands = [{"x": b["x"], "y": b["y"], "hiding": b["hiding"],
                       "sense": max(senses[f["name"]]["sense"] for f in b["foes"]),
                       "stealth": max(senses[f["name"]]["stealth"] for f in b["foes"])}
                      for b in o["bands"]] if not unseen else []
        stairs = tuple(o["stairs"])
        self.squares = [[0] * self.w for _ in range(self.h)]
        for y in range(self.h):
            for x in range(self.w):
                t = int(o["rows"][y][x])
                base = art.TERRAIN[t]
                h = dress_hash(self.yard, self.number, 0, x, y)
                if t == 0 and scenery and h < 16 and (x, y) != stairs:
                    name = scenery[h % len(scenery)]
                elif variants[base] and h & 7 == 0:
                    name = variants[base][(h >> 3) % len(variants[base])]
                else:
                    name = base
                blocked = t in (WALL, PIT, HAZARD) or (x, y) in taken
                self.squares[y][x] = self.names.index(name) | (BLOCKED if blocked else 0)
        for x, y, name, band in standing:
            if name not in self.kinds:
                self.kinds.append(name)
            self.figures.append((x, y, self.kinds.index(name), band))
        self.figures.sort(key=lambda f: f[1])     # (stable: the bands' order, then the people)
        assert len(self.kinds) <= KINDS_MAX and len(self.figures) <= FIGURES_MAX
        self.start, self.goal = tuple(o["start"]), stairs

    def senses(self):
        """The party's Notice (Wits or Intuition, the better) and Stealth, in marching
        order, as the explore prototype's travelers have them (tools/arena/scenarios.py)."""
        sys.path.insert(0, os.path.join(HERE, "..", "arena"))
        import arena
        notice, stealth = [], []
        for cls in PARTY_CLASSES:
            ch = arena.build(cls, 1)
            notice.append(max(ch["stats"][arena.STAT["WITS"]], arena.rating(ch, "INTUITION")))
            stealth.append(arena.rating(ch, "STEALTH"))
        return notice, stealth

    def watch(self):
        """Seeing on this floor (tools/rules/seeing.py's Watch), or None: a rooms floor's
        foes don't hide."""
        if not self.bands:
            return None
        tiles = [[int(c) for c in row] for row in self.f["rows"]]
        return seeing.Watch({"tiles": tiles, "light": self.light, "seed": self.seed,
                             "bands": self.bands,
                             "party": {"sneaking": False, "light": False,
                                       "travelers": [{"notice": n, "stealth": s}
                                                     for n, s in zip(self.notice, self.stealth)]}})

    @property
    def cam_most(self):
        """The camera's most, across and down: the screen's 40 x 25 characters on the area."""
        return (2 * self.w - 40) * 8 + 7, (2 * self.h - 25) * 8 + 7

    def free(self, sx, sy):
        return 0 <= sx < self.w and 0 <= sy < self.h and not self.squares[sy][sx] & BLOCKED

    def char(self, cx, cy):
        """The character on the area's character (cx, cy), and its colour RAM's value."""
        if not (0 <= cx < 2 * self.w and 0 <= cy < 2 * self.h):
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

    def shapes(self):
        """Each kind's sprite shapes, the cartridge's (battlegfx.py --cart16: the body with
        its outline drawn in): 2 k as drawn (facing right), 2 k + 1 mirrored (left); and
        each kind's own colour."""
        data = battlegfx.build16()
        order = battlegfx.RACES + ["STRANGER"] + battlegfx.FOES
        out, colours = bytearray(), []
        for name in self.kinds:
            n = order.index(name)
            body = data[2176 + 128 * n:2176 + 128 * n + 64]
            out += body + mirrored(body)
            colours.append(data[4224 + n])
        return bytes(out), colours

    def squares_asset(self):
        """The squares, a row at a time (w x h bytes): the floor's second file, squares.bin."""
        return b"".join(bytes(row) for row in self.squares)

    def asset(self):
        """What the C64 is given (docs/walk.md, "The floor's asset"), besides the squares
        (squares_asset):

            0      the background and the two shared colours (3)
            3      the number of tiles (1)
            4      each tile's colour RAM value (32)
            36     where you start: square x, square y (2)
            38     the floor's width and height, in squares (2)
            40     the party's kinds, in marching order (4)
            44     how many kinds (1), then each one's colour (12)
            57     how many figures (1), then each one's square x, y and kind (80 x 3), in order
                   down
            304    the characters, 8 bytes each, 0 blank then 4 a tile (8 + 32 a tile)
            2000   the HUD's sprites
            2048   the sprite shapes, 64 bytes each: kind k's 2 k (facing right), 2 k + 1 (left)"""
        out = bytearray([self.art.background, *self.art.shared, len(self.art.entries)])
        cols = [e.colour | 8 for e in self.art.entries]
        out += bytes(cols + [0] * (32 - len(cols)))
        out += bytes(self.start) + bytes([self.w, self.h])
        shapes, colours = self.shapes()
        out += bytes(range(len(PARTY)))
        out += bytes([len(self.kinds)] + colours + [0] * (KINDS_MAX - len(colours)))
        figs = bytearray([len(self.figures)])
        for x, y, k, _ in self.figures:
            figs += bytes([x, y, k])
        out += figs + bytes(1 + 3 * FIGURES_MAX - len(figs))
        assert len(out) == 298
        terrain = [art.TERRAIN.index(art.variant_of(e.name) or e.name) if (art.variant_of(e.name) or e.name)
                   in art.TERRAIN else 0 for e in self.art.entries]
        out += bytes(terrain + [0] * (32 - len(terrain)))
        out += bytes([b for _, _, _, b in self.figures] + [NO_BAND] * (FIGURES_MAX - len(self.figures)))
        out += bytes([len(self.bands)])
        for b in self.bands + [None] * (BANDS_MAX - len(self.bands)):
            out += bytes([b["x"], b["y"], b["sense"], b["stealth"], int(b["hiding"])] if b else [0] * 5)
        out += bytes(self.notice) + bytes(self.stealth) + bytes([self.light, self.seed & 255, self.seed >> 8])
        assert len(out) == 542
        out += bytes(576 - len(out))
        out += self.charset()
        assert len(out) <= 2000
        out += bytes(2000 - len(out))
        hud = self.hud()
        out += bytes([x & 255 for x, _, _, _ in hud] + [c for _, _, c, _ in hud])
        out += bytes([sum(1 << n for n, (x, _, _, _) in enumerate(hud) if x > 255),
                      sum(1 << n for n, (_, _, _, m) in enumerate(hud) if m)])
        out += bytes(2048 - len(out)) + shapes
        out += bytes(64 * HUD_SHAPES - len(shapes))
        for k in range(len(PARTY)):
            out += self.health_shape(k)
        return bytes(out)

    def travelers(self):
        """The party's classes, level 1, with their health: (class, health, most)."""
        sys.path.insert(0, os.path.join(HERE, "..", "arena"))
        import arena
        out = []
        for cls in PARTY_CLASSES:
            ch = arena.build(cls, 1)
            most = 10 + ch["stats"][2] // 4 + 2 * ch["level"]     # rules-v0.md: Health
            out.append((cls, most, most))
        return out

    def hud(self):
        """The HUD's 8 sprites: (x, shape, colour, multicolour); sprite 2 k is traveler k's
        portrait, 2 k + 1 their health."""
        _, colours = self.shapes()
        out = []
        for k in range(len(PARTY)):
            x = HUD_FIRST_X + HUD_STEP * k
            out.append((x, 2 * k, colours[k], True))
            out.append((x + 24, HUD_SHAPES + k, HUD_COLOUR, False))
        return out

    def health_shape(self, k):
        """Traveler k's health, a hires sprite (24 x 21): the number (health/most) on rows 1-5,
        a bar on 8-11, the class's first three letters on 14-18, in a 3 x 5 font."""
        cls, health, most = self.travelers()[k]
        rows = [[0] * 24 for _ in range(21)]
        text(rows, 1, 1, f"{health}/{most}")
        for x in range(1, 23):
            rows[8][x] = rows[11][x] = 1
        rows[9][1] = rows[10][1] = rows[9][22] = rows[10][22] = 1
        for x in range(2, 2 + 20 * health // most):
            rows[9][x] = rows[10][x] = 1
        text(rows, 1, 14, cls[:3])
        out = bytearray()
        for r in rows:
            for b in range(3):
                out.append(sum(r[8 * b + i] << (7 - i) for i in range(8)))
        return bytes(out) + b"\0"


def mirrored(shape):
    """A multicolour sprite facing the other way: its 12 pairs of bits reversed, each pair
    kept."""
    out = bytearray()
    for y in range(21):
        bits = shape[3 * y] << 16 | shape[3 * y + 1] << 8 | shape[3 * y + 2]
        flip = 0
        for i in range(12):
            flip = flip << 2 | (bits >> (2 * i)) & 3
        out += bytes([flip >> 16, (flip >> 8) & 255, flip & 255])
    return bytes(out) + bytes(64 - len(out))


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

def target(floor, pos):
    """Where the camera wants to be: the leader's middle (pos in sixteenths: its square's
    pixel + 8) in the view's, kept on the area."""
    return aim(floor, (pos[0] >> 4) + 8, (pos[1] >> 4) + 8)


def aim(floor, mx_px, my_px):
    """The camera with this pixel in the view's middle, kept on the area."""
    tx = mx_px - VIEW_W // 2
    ty = my_px - VIEW_H // 2
    mx, my = floor.cam_most
    return max(0, min(mx, tx)), max(0, min(my, ty))


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


class Fight:
    """A fight's setup on an open floor (docs/walk.md, "The fight"): band (0-based) has seen
    the party, the leader on square (lx, ly). The window (rooms.fight_window), its squares'
    terrain, where the party stands (rooms.fight_places), and the band's foes on it:
    .record as the engine keeps it (FIGHT_REC); the camera's middle; the band's middle
    across, the travelers' places in pixels."""

    def __init__(self, floor, band, lx, ly):
        foes = [(x, y, kind) for x, y, kind, b in floor.figures if b == band]
        self.window = wx, wy = rooms.fight_window([{"x": x, "y": y} for x, y, _ in foes], (lx, ly),
                                                  floor.w, floor.h)
        rows = [floor.f["rows"][wy + j][wx:wx + rooms.W] for j in range(rooms.H)]
        room = {"rows": rows, "foes": [{"x": x - wx, "y": y - wy} for x, y, _ in foes]}
        places = rooms.fight_places(room, (lx - wx, ly - wy), len(PARTY))
        self.record = bytes([wx, wy] + [int(c) for row in rows for c in row]
                            + [v for p in places for v in p]
                            + [len(foes)] + [v for x, y, kind in foes for v in (x - wx, y - wy, kind)])
        self.places = [((wx + x) * 16, (wy + y) * 16) for x, y in places]
        self.middle = ((2 * wx + rooms.W) * 8, (2 * wy + rooms.H) * 8)
        xs = [x for x, _, _ in foes]
        self.band_x = (min(xs) + max(xs)) * 8           # a traveler right of it faces left


def toward(v, to):
    """A frame's walk to a place, on one axis: up to PLACE_SPEED pixels."""
    return v + max(-PLACE_SPEED, min(PLACE_SPEED, to - v))


class Party:
    """The party as it's drawn (docs/walk.md, "The figures"): the leader's trail, how many
    frames they've moved, whether they moved this one, and where each traveler was last
    drawn and which way they face."""

    def __init__(self, pos):
        self.trail = [(pos[0] >> 4, pos[1] >> 4)]
        self.steps, self.moved = 0, False
        self.last_x = [pos[0] >> 4] * len(PARTY)
        self.left = [False] * len(PARTY)
        self.fight, self.at = None, None                # a fight's: where each stands now

    def take_places(self, fight):
        """A fight begins: each traveler from where they were drawn (or the trail's oldest,
        if not out yet) walks to their place."""
        self.fight = fight
        self.at = [list(self.trail[-1 - GAP * k] if len(self.trail) > GAP * k else self.trail[0])
                   for k in range(len(PARTY))]
        self.moved = False

    def to_places(self):
        """A frame's walk toward their places; True once everyone's there."""
        for k, (x, y) in enumerate(self.fight.places):
            self.at[k] = [toward(self.at[k][0], x), toward(self.at[k][1], y)]
        return all(tuple(a) == p for a, p in zip(self.at, self.fight.places))

    def step(self, pos):
        at = (pos[0] >> 4, pos[1] >> 4)
        self.moved = at != self.trail[-1]
        if self.moved:
            self.trail = (self.trail + [at])[-TRAIL:]
            self.steps = (self.steps + 1) & 255


def figures(floor, party, cam, shown=None):
    """The frame's figures as sprites: the party (each traveler GAP trail entries behind
    the one before, not drawn until the trail is that long), then the floor's foes and
    people; those in sight, with their shapes and colours, sorted down the screen and
    given the VIC's sprites (allocate). Changes party: who faces which way."""
    shapes = len(floor.kinds)
    _, colours = floor.shapes()
    figs = []
    lead_x = party.trail[-1][0]
    for k in range(len(PARTY)):
        if party.fight:                             # taking their places: facing the band
            x, y = party.at[k]
            figs.append((x, y, 2 * k + (x > party.fight.band_x), colours[k]))
            continue
        if len(party.trail) <= GAP * k:
            continue
        x, y = party.trail[-1 - GAP * k]
        if x < party.last_x[k]:
            party.left[k] = True
        elif x > party.last_x[k]:
            party.left[k] = False
        party.last_x[k] = x
        if party.moved and (party.steps + 4 * k) & 8:
            y -= 1                                  # a step's bob
        figs.append((x, y, 2 * k + party.left[k], colours[k]))
    for sx, sy, kind, band in floor.figures:
        if band != NO_BAND and not shown[band]:
            continue                                # a band not shown spotted isn't drawn
        x, y = sx * 16, sy * 16
        figs.append((x, y, 2 * kind + (lead_x + 8 < x), colours[kind]))
    shown = []
    for x, y, shape, colour in figs:
        px, py = x - cam[0] + SPRITE_DX, y - cam[1] + SPRITE_DY
        if SPRITE_X_MIN <= px <= SPRITE_X_MAX and SPRITE_Y_MIN <= py <= SPRITE_Y_MAX:
            shown.append((px, py, SHAPE_POINTER + shape, colour))
    assert shapes * 2 <= 32
    shown.sort(key=lambda f: f[1])                  # (stable: party first, then the floor's)
    return allocate(shown)


def allocate(shown):
    """The VIC's 8 sprites shared down the screen: each figure, in order down it, takes the
    next sprite in turn (0 to 7, then round again), if it's free by its top line; a sprite
    is free REUSE lines below the top of the last figure it showed. (Since the figures come
    in order down, the next in turn is always one free soonest.) A figure whose sprite
    isn't free in time is left out, and so is a reuse past EVENTS_MAX or set on a line after
    EVENT_LAST; the turn stays.
    Returns (sprite, x, y, pointer, colour, line it's set on: None for the first 8, set at
    the frame's start), and how many were left out."""
    free, out, left, n, events = [0] * 8, [], 0, 0, 0
    last = [None] * 8
    for px, py, ptr, colour in shown:
        if free[n] > py or (last[n] is not None and (events == EVENTS_MAX
                                                      or last[n] + 21 > EVENT_LAST)):
            left += 1
            continue
        out.append((n, px, py, ptr, colour, None if last[n] is None else last[n] + 21))
        events += last[n] is not None
        last[n], free[n] = py, py + REUSE
        n = (n + 1) % 8
    return out, left


def play(floor, sticks):
    """Each frame from the first shown: (leader x, leader y in sixteenths, camera x, camera y,
    the scroller's stage, the figures as sprites and how many were left out). sticks[n] is
    the joystick as frame n's main loop reads it; what it decides is shown from frame n + 1
    (docs/walk.md, "A frame")."""
    pos = [floor.start[0] * 16 * SUB, floor.start[1] * 16 * SUB]
    cam = list(target(floor, pos))
    party = Party(pos)
    stage, dirs, out = IDLE, (0, 0), []
    # Seeing (docs/open-floors.md; docs/walk.md, "Seeing"): a check of every band at the
    # start, and each time the leader's square (its middle's) changes, shown SEE_SHOWN
    # frames on (the C64 makes them in the time to spare meanwhile); the leader's steps
    # while they're under way wait. A band shown to have seen the party stops the walk.
    watch = play.watch = floor.watch()
    play.steps = []                                 # the frame each step's checks came in
    # And a fight (docs/walk.md, "The fight"): once a band's shown to have seen the party,
    # the camera eases to the fight's window and the travelers walk to their places;
    # play.ready is the frame it's all still (the battle begins), or None.
    play.fight = play.ready = None
    square, wait, shown, shown_fight = tuple(floor.start), 0, None, None

    def show():
        return [st["spotted"] or st["seen"] for st in watch.state], watch.fight

    def begin_fight():
        play.fight = Fight(floor, shown_fight[0], *square)
        party.take_places(play.fight)
    if watch:
        watch.step(*square)
        play.steps.append(-1)
        shown, shown_fight = show()
        if shown_fight is not None:
            begin_fight()
    for n, stick in enumerate(sticks):
        out.append((pos[0], pos[1], cam[0], cam[1], stage, figures(floor, party, cam, shown)))
        if shown_fight is not None:
            stick = 0xFF                            # stopped: the band's seen the party
        walk(floor, pos, stick)
        placed = party.to_places() if party.fight else party.step(pos)
        if watch:
            if wait:
                wait -= 1
                if not wait:
                    shown, shown_fight = show()
                    if shown_fight is not None:
                        begin_fight()
            now = ((pos[0] + 128) >> 8, (pos[1] + 128) >> 8)
            if not wait and shown_fight is None and now != square:
                square, wait = now, SEE_SHOWN
                watch.step(*square)
                play.steps.append(n)
        want = aim(floor, *play.fight.middle) if play.fight else target(floor, pos)
        nxt = [ease(cam[0], want[0]), ease(cam[1], want[1])]
        if stage == IDLE:
            d = tuple((nxt[i] >> 3) - (cam[i] >> 3) for i in range(2))
            d = tuple(max(-1, min(1, v)) for v in d)
            if d != (0, 0):
                dirs, stage = d, HALF                   # the screen's top half shifted
            nxt = [clamp_cell(nxt[i], cam[i] >> 3) for i in range(2)]
        elif stage == HALF:
            stage = SHIFTED                             # its bottom half, and the edges
            nxt = [clamp_cell(nxt[i], cam[i] >> 3) for i in range(2)]
        elif stage == SHIFTED:
            stage = SHADED                              # the shadow's first half shifted
            nxt = [clamp_cell(nxt[i], cam[i] >> 3) for i in range(2)]
        elif stage == SHADED:
            stage = COLOURED                            # the rest, its edges; swap next
            nxt = [clamp_cell(nxt[i], (cam[i] >> 3) + dirs[i]) for i in range(2)]
        else:
            stage = IDLE                                # the swap frame: nothing heavy
            nxt = [clamp_cell(nxt[i], cam[i] >> 3) for i in range(2)]
        cam = nxt
        if play.fight and placed and play.ready is None and stage == IDLE and cam == list(want):
            play.ready = n                              # the camera and the party still
    return out


# ------------------------------------------------------------------ the command line

def main(argv):
    if len(argv) in (5, 6) and argv[1] == "asset" and argv[5:] in ([], ["unseen"]):
        fl = Floor(int(argv[2]), int(argv[3]), unseen=argv[5:] == ["unseen"])
        with open(os.path.join(argv[4], "floor.bin"), "wb") as f:
            f.write(fl.asset())
        with open(os.path.join(argv[4], "squares.bin"), "wb") as f:
            f.write(fl.squares_asset())
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
