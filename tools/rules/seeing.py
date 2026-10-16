"""Reference for seeing and being seen (docs/open-floors.md, Being seen), written from the
doc, independently of core/next/seeing.c, so the two can check each other.

The looker rolls d100 + its Notice; whoever might be seen sets the TN: 50 + Stealth if
it's sneaking or hiding, 80 if not; light, distance, cover and alertness move it. A party
is a group: sneaking, its TN is 50 + its best Stealth, each of the others rolling
Stealth against 100 to put 10 on or take 10 off; looking, its best rolls, each of the
others first rolling against the same TN to take 10 off or put 10 on.

    python3 tools/rules/seeing.py CASE.txt      (an approach, its log: tests/seeing/)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import combat  # noqa: E402

FAIL, COST, SUCCESS, CRIT = combat.FAIL, combat.COST, combat.SUCCESS, combat.CRIT
RESULT = ["fail", "cost", "success", "crit"]
DAY, DUSK, NIGHT = 0, 1, 2
LIGHTS = ["day", "dusk", "night"]
WALL, PIT, COVER = 1, 2, 4

OPEN_TN = 80            # Easy: not sneaking, not hiding
BASE = 50               # a defense's TN: 50 + the rating
HELP = 10               # what each of a group's others moves the TN


def dist(ax, ay, bx, by):
    """The battle's distance: the larger gap, across or down."""
    return max(abs(ax - bx), abs(ay - by))


def sight(tiles, ax, ay, bx, by):
    """The line from (ax, ay) to (bx, by), the battle engine's (Bresenham's, its
    tie-break): None if a wall stops it, else whether a cover square is on it (not
    either end). tiles[y][x] are the battle's terrain numbers."""
    dx, dy = abs(bx - ax), abs(by - ay)
    sx, sy = (1 if ax < bx else -1), (1 if ay < by else -1)
    err = dx - dy
    x, y, cover = ax, ay, False
    while True:
        if (x, y) == (bx, by):
            return cover
        if (x, y) != (ax, ay):
            if tiles[y][x] == WALL:
                return None
            if tiles[y][x] == COVER:
                cover = True
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy


def sight_range(notice, light):
    """Notice / 5 squares, doubled by day, halved at night (rounded down), at least 1."""
    r = notice // 5
    if light == DAY:
        r *= 2
    elif light == NIGHT:
        r //= 2
    return max(1, r)


def modifiers(light, d, through_cover, in_cover, alert, carried_light):
    """The TN's modifiers (docs/open-floors.md's table), as (amount, why), in the doc's
    order: light, distance, cover between, in cover, an alert looker, a light carried."""
    out = []
    if light == DUSK:
        out.append((10, "dusk"))
    elif light == NIGHT:
        out.append((20, "night"))
    if d >= 8:
        out.append((10 * ((d - 4) // 4), "distance"))
    if through_cover:
        out.append((20, "cover between"))
    if in_cover:
        out.append((10, "in cover"))
    if alert:
        out.append((-20, "alert"))
    if carried_light and light == NIGHT:
        out.append((-20, "a light"))
    return out


def helper_shift(roll, result, sneaking):
    """What one of a group's others does to the TN: looking, a success takes 10 off (a
    crit 20), a fail puts 10 on (a natural 01, 20); sneaking, the other way round. A
    success at a cost does nothing."""
    if roll == 1:
        v = 2 * HELP
    elif result == FAIL:
        v = HELP
    elif result == COST:
        v = 0
    elif result == CRIT:
        v = -2 * HELP
    else:
        v = -HELP
    return -v if sneaking else v


def best(ratings):
    """The first of the highest."""
    return ratings.index(max(ratings))


class Dice:
    def __init__(self, seed):
        self.gen = combat.d100s(seed)

    def roll(self):
        return next(self.gen)


def group_tn(dice, stealths, log):
    """A sneaking group's TN before modifiers: 50 + its best Stealth, each of the others
    rolling Stealth against 100 (in party order). The total the others move it."""
    b = best(stealths)
    shift = 0
    for i, s in enumerate(stealths):
        if i == b:
            continue
        r = dice.roll()
        res = combat.resolve(r, r + s, 100)
        v = helper_shift(r, res, True)
        shift += v
        log.append(f"    sneaking: Stealth {s} rolls {r} = {r + s} against 100: "
                   f"{RESULT[res]}, {v:+d}")
    return BASE + stealths[b], shift


def group_look(dice, notices, tn, log):
    """A looking group's roll: each of the others first rolls against the TN (party
    order), moving it; then the best rolls against what they leave. (roll, total, tn,
    result) of the best's roll."""
    b = best(notices)
    for i, n in enumerate(notices):
        if i == b:
            continue
        r = dice.roll()
        res = combat.resolve(r, r + n, tn)
        v = helper_shift(r, res, False)
        log.append(f"    helping: Notice {n} rolls {r} = {r + n} against {tn}: "
                   f"{RESULT[res]}, {v:+d}")
        tn += v
    r = dice.roll()
    n = notices[b]
    return r, r + n, tn, combat.resolve(r, r + n, tn)


def tn_line(base_terms, mods):
    terms = " ".join(base_terms + [f"{v:+d} {why}" for v, why in mods])
    total = sum(v for v, _ in mods)
    return terms, total


def approach(case):
    """Play an approach (a parsed case: parse()): the party's leader steps along its path;
    at each step every band is checked as the doc's *Precisely* says. Returns the log
    (a list of lines)."""
    tiles, light = case["tiles"], case["light"]
    party, bands = case["party"], case["bands"]
    dice = Dice(case["seed"])
    log = [f"light {LIGHTS[light]}; the party {'sneaks' if party['sneaking'] else 'walks'}"
           + (", carrying a light" if party["light"] else "")]
    notices = [t["notice"] for t in party["travelers"]]
    stealths = [t["stealth"] for t in party["travelers"]]
    state = [{"spotted": False, "seen": False, "alert": False, "party_last": None,
              "band_last": None} for _ in bands]
    x, y = case["start"]
    for step, (nx, ny) in enumerate([case["start"]] + case["path"]):
        x, y = nx, ny
        header = [f"step {step}: the party at {x},{y}"]

        def say(line):
            if header:
                log.append(header.pop())
            log.append(line)

        for bi, band in enumerate(bands):
            st = state[bi]
            bx, by = band["x"], band["y"]
            d = dist(x, y, bx, by)
            line = sight(tiles, x, y, bx, by)
            where = f"  band {bi + 1} at {bx},{by}, {d} away"
            # The party looks.
            if not st["spotted"] and line is not None and d <= sight_range(max(notices), light):
                if d <= 1:
                    st["spotted"] = True
                    say(f"{where}: the party looks: spotted, no roll")
                elif st["party_last"] is None or d <= st["party_last"] - 4:
                    st["party_last"] = d
                    say(f"{where}: the party looks")
                    if band["hiding"]:
                        base_terms, base = [f"{BASE} + {band['stealth']} hiding"], BASE + band["stealth"]
                    else:
                        base_terms, base = [f"{OPEN_TN} open"], OPEN_TN
                    mods = modifiers(light, d, line, tiles[by][bx] == COVER, False, False)
                    terms, m = tn_line(base_terms, mods)
                    tn = base + m
                    log.append(f"    TN {terms} = {tn}")
                    sub = []
                    r, total, tn2, res = group_look(dice, notices, tn, sub)
                    log.extend(sub)
                    what = {FAIL: "not yet", COST: "heard", SUCCESS: "spotted", CRIT: "spotted"}[res]
                    log.append(f"    looks: Notice {max(notices)} rolls {r} = {total} against {tn2}: "
                               f"{RESULT[res]}: {what}")
                    if res >= SUCCESS:
                        st["spotted"] = True
            # The band looks back.
            if line is not None and d <= sight_range(band["sense"], light):
                if d <= 1:
                    st["seen"] = True
                    say(f"{where}: band {bi + 1} looks: seen, no roll")
                elif st["band_last"] is None or d <= st["band_last"] - 4:
                    st["band_last"] = d
                    say(f"{where}: band {bi + 1} looks")
                    sub = []
                    if party["sneaking"]:
                        base, shift = group_tn(dice, stealths, sub)
                        base_terms = [f"{BASE} + {max(stealths)} sneaking"] + \
                            ([f"{shift:+d} the others"] if len(stealths) > 1 else [])
                        base += shift
                    else:
                        base_terms, base = [f"{OPEN_TN} walking"], OPEN_TN
                    log.extend(sub)
                    mods = modifiers(light, d, line, tiles[y][x] == COVER, st["alert"], party["light"])
                    terms, m = tn_line(base_terms, mods)
                    tn = base + m
                    log.append(f"    TN {terms} = {tn}")
                    r = dice.roll()
                    res = combat.resolve(r, r + band["sense"], tn)
                    what = {FAIL: "not yet", COST: "heard: alert", SUCCESS: "seen", CRIT: "seen"}[res]
                    log.append(f"    looks: Sense {band['sense']} rolls {r} = {r + band['sense']} "
                               f"against {tn}: {RESULT[res]}: {what}")
                    if res == COST:
                        st["alert"] = True
                    elif res >= SUCCESS:
                        st["seen"] = True
            if st["seen"]:
                log.append(f"the fight: band {bi + 1}" + ("" if st["spotted"] else ", an ambush"))
                return log
    log.append("the end of the way: not seen")
    return log


# ------------------------------------------------------------------ cases

def parse(path):
    """A case (tests/seeing/*.txt): seed, light, a map ('@' the party's leader, letters
    the bands, in the order they appear in `band` lines; '#' wall, '+' cover, '.' open,
    '~' rough, 'O' pit, '^' hazard, '=' high), the party (sneaking or walking; a light;
    each traveler's Stealth and Notice), each band (its letter, Sense, Stealth, hiding or
    open) and the path (steps: N S E W NE NW SE SW, with a count: E 6)."""
    case = {"seed": 1, "light": DAY, "path": [], "bands": []}
    marks = {}
    lines = iter(open(path).read().split("\n"))
    tiles = []
    for ln in lines:
        w = ln.split("#", 1)[0].split() if not ln.startswith("map") else ["map"]
        if not w:
            continue
        if w[0] == "seed":
            case["seed"] = int(w[1])
        elif w[0] == "light":
            case["light"] = LIGHTS.index(w[1])
        elif w[0] == "map":
            for row in lines:
                if row.strip() == "end":
                    break
                out = []
                for x, ch in enumerate(row):
                    if ch == "@" or ch.isalpha() and ch.islower():
                        marks[ch] = (x, len(tiles))
                        out.append(0)
                    else:
                        out.append(".#O~+^=>".index(ch))
                tiles.append(out)
        elif w[0] == "party":
            case["party"] = {"sneaking": w[1] == "sneaking", "light": "light" in w[2:], "travelers": []}
        elif w[0] == "traveler":
            case["party"]["travelers"].append({"stealth": int(w[1]), "notice": int(w[2])})
        elif w[0] == "band":
            x, y = marks[w[1]]
            case["bands"].append({"x": x, "y": y, "sense": int(w[2]), "stealth": int(w[3]),
                                  "hiding": w[4] == "hiding"})
        elif w[0] == "path":
            pos = case["path"][-1] if case["path"] else marks["@"]
            steps = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0),
                     "NE": (1, -1), "NW": (-1, -1), "SE": (1, 1), "SW": (-1, 1)}
            for k in range(1, len(w), 2):
                dx, dy = steps[w[k]]
                for _ in range(int(w[k + 1])):
                    pos = (pos[0] + dx, pos[1] + dy)
                    case["path"].append(pos)
        else:
            raise SystemExit(f"{path}: '{ln}'?")
    case["tiles"], case["start"] = tiles, marks["@"]
    for x, y in case["path"]:
        if not (0 <= y < len(tiles) and 0 <= x < len(tiles[y])) or tiles[y][x] in (WALL, PIT):
            raise SystemExit(f"{path}: the path goes to {x},{y}: a wall, a pit or off the map")
    return case


if __name__ == "__main__":
    print("\n".join(approach(parse(sys.argv[1]))))
