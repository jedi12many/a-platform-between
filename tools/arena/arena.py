"""The arena (docs/arena.md): travelers against foes, fought many times on the real battle
engine (build/arena, core/src/battle.c), both sides played by the computer, to see how the
rules balance.

    python3 tools/arena/arena.py MATCHUP.txt
    python3 tools/arena/arena.py "Warden 3" vs RUST_GUARD [--fights 1000]
    python3 tools/arena/arena.py "Warden 3" "Channeler 3" vs "ASH_RAT x4" --sweep level 1-10
    python3 tools/arena/arena.py "Warden 3" vs RUST_GUARD --show 0     (one fight, blow by blow)

A matchup file is lines (# starts a comment):

    fights 1000                      how many fights (each with its own dice)
    seed 1                           the first fight's seed
    traveler [RACE] CLASS LEVEL [weapon ARCH TIER [TYPE]] [armor TIER] [name NAME]
    foe NAME [x COUNT]               from registry/foes.txt
    sweep level FIRST-LAST           every traveler's level, one run each
    sweep count FIRST-LAST           the last foe line's count, one run each
    map                              then rows (docs/combat.md), then: end; @ and a-z for
                                     where travelers and foes start (else they line up)

A traveler is built by the quick builder (build), the rules' own way: point-buy, then a
level-up at a time.
"""

import os
import re
import statistics
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "registry"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
import registry  # noqa: E402
import passport  # noqa: E402

REG = registry.load()
STAT = {s: i for i, s in enumerate(registry.STATS)}
ARENA = os.path.join(ROOT, "build", "arena")

# ------------------------------------------------------------------------ the quick builder
# What each class puts first: its stats (point-buy fills them in order, to 70), the skill
# it fights with (and so its weapon), and the extra skill it tags.

PLANS = {
    "WARDEN":    {"stats": ["MIGHT", "GRIT", "GRACE", "WITS"], "fights": "MELEE", "arch": "melee",
                  "tag": "ATHLETICS", "armor": 0},
    "ROGUE":     {"stats": ["GRACE", "GRIT", "WITS", "MIGHT"], "fights": "RANGED", "arch": "ranged",
                  "tag": "ATHLETICS", "armor": -1},
    "TINKER":    {"stats": ["WITS", "GRACE", "GRIT", "MIGHT"], "fights": "RANGED", "arch": "ranged",
                  "tag": "RANGED", "armor": -1},
    "CHANNELER": {"stats": ["PRESENCE", "GRACE", "GRIT", "WITS"], "fights": "CHANNEL", "arch": "focus",
                  "tag": "ATHLETICS", "armor": -1},
    "MEDIC":     {"stats": ["WITS", "GRACE", "GRIT", "MIGHT"], "fights": "RANGED", "arch": "ranged",
                  "tag": "RANGED", "armor": -1},
}
# The race each class takes if none is given: the one whose +10 is the class's +5's stat.
DEFAULT_RACE = {"WARDEN": "SALVAGED", "ROGUE": "CHRONOMITE", "TINKER": "GLASSFOLK",
                "CHANNELER": "RAD_DRYAD", "MEDIC": "GLASSFOLK"}
RAISE_COST = [(50, 1), (75, 2), (90, 3), (101, 4)]   # rules-v0.md: a raise's cost by rating


def rating(ch, skill):
    s = REG["skills"][skill]
    return ch["stats"][s["stat"]] // 2 + ch["training"].get(s["id"], 0)


def build(cls, level, race=None, name=None):
    """A character of this class and level, made by the rules: point-buy (150 points into
    the class's stats in order, 70 at most), the class's tags and one more; then each
    level's stat point into its first stat (then the next, to 100), and its skill points
    (1 + Wits / 20) into the skill it fights with, then Athletics, at the rules' costs."""
    cls, race = cls.upper(), (race or DEFAULT_RACE[cls.upper()]).upper()
    plan = PLANS[cls]
    stats = [25] * 6
    left = 150
    for s in plan["stats"]:
        add = min(45, left)
        stats[STAT[s]] += add
        left -= add
    tag = plan["tag"]
    if REG["skills"][tag]["id"] in REG["classes"][cls]["tags"]:
        tag = "ATHLETICS" if tag != "ATHLETICS" else "SURVIVAL"
    ch = passport.create(name or cls[:8], race, cls, stats, tag)
    for lv in range(2, level + 1):
        ch["level"] = lv
        for s in plan["stats"]:                              # the stat point
            if ch["stats"][STAT[s]] < 100:
                ch["stats"][STAT[s]] += 1
                break
        points = 1 + ch["stats"][STAT["WITS"]] // 20         # the skill points
        for skill in (plan["fights"], "ATHLETICS"):
            sid = REG["skills"][skill]["id"]
            step = 2 if sid in ch["tags"] else 1
            while True:
                have = ch["training"].get(sid, 0)
                if rating(ch, skill) >= 100 or have >= 100:      # skills run to 100
                    break
                cost = next(c for top, c in RAISE_COST if rating(ch, skill) < top)
                if cost > points:
                    break
                ch["training"][sid] = min(100, have + step)
                points -= cost
            if not points:
                break
    return ch


def gear_tier(level):
    """The weapon a traveler of this level carries, if the matchup doesn't say: tier 1, and
    one more every 5 levels (9 at most)."""
    return min(9, 1 + level // 5)


# ------------------------------------------------------------------------ matchups

class Traveler:
    def __init__(self, words):
        w = [x for x in words]
        self.race = None
        if w and w[0].upper() in REG["races"]:
            self.race = w.pop(0).upper()
        if not w or w[0].upper() not in PLANS:
            raise SystemExit(f"arena: '{' '.join(words)}': give a class ({', '.join(PLANS)}) and a level")
        self.cls = w.pop(0).upper()
        self.level = int(w.pop(0)) if w and w[0].isdigit() else 1
        self.arch = PLANS[self.cls]["arch"]
        self.tier = None
        self.type = "kinetic" if self.arch != "focus" else "energy"
        self.armor = None
        self.name = None
        while w:
            k = w.pop(0).lower()
            if k == "weapon":
                self.arch, self.tier = w.pop(0).lower(), int(w.pop(0))
                if w and w[0].lower() in registry.DAMAGE:
                    self.type = w.pop(0).lower()
            elif k == "armor":
                self.armor = int(w.pop(0))
            elif k == "name":
                self.name = w.pop(0)
            else:
                raise SystemExit(f"arena: '{' '.join(words)}': what's '{k}'?")

    def label(self):
        return f"{self.name + ' ' if self.name else ''}({REG['classes'][self.cls]['display']} {self.level})"

    def line(self, x, y):
        ch = build(self.cls, self.level, self.race, self.name)
        tier = self.tier if self.tier is not None else gear_tier(self.level)
        armor = self.armor if self.armor is not None else max(0, tier + PLANS[self.cls]["armor"])
        self.health = 10 + ch["stats"][STAT["GRIT"]] // 4 + 2 * ch["level"]
        return (f"traveler {x} {y} {passport.encode(ch)} {self.arch} {tier} "
                f"{registry.DAMAGE.index(self.type)} {armor}")


def foe_line(name, x, y):
    f = REG["foes"][name]
    weak = 255 if f["weak"] is None else f["weak"]
    return (f"foe {x} {y} {f['health']} {f['grace']} {f['grace'] // 5} {f['armor']} {f['ward']} "
            f"{f['soak']} {f['speed']} {f['attack']} {f['damage']} {int(f['reach'] >= 1)} "
            f"{int(f['reach'] == 2)} {f['type']} {f['area']} {weak} {f['behavior']} {int(f['coward'])}")


class Matchup:
    def __init__(self):
        self.fights, self.seed, self.rounds = 1000, 1, 50
        self.travelers, self.foes = [], []          # foes: [name, count]
        self.sweep = None
        self.map = None

    def read(self, text):
        lines = iter(text.split("\n"))
        for ln in lines:
            ln = ln.split("#")[0].strip() if not ln.lstrip().startswith("#") else ""
            if not ln:
                continue
            w = ln.split()
            k = w[0].lower()
            if k == "fights":
                self.fights = int(w[1])
            elif k == "seed":
                self.seed = int(w[1])
            elif k == "traveler":
                self.travelers.append(Traveler(w[1:]))
            elif k == "foe":
                self.add_foe(" ".join(w[1:]))
            elif k == "sweep":
                self.set_sweep(w[1], w[2])
            elif k == "map":
                self.map = []
                for row in lines:
                    if row.strip() == "end":
                        break
                    self.map.append(row.rstrip())
            else:
                raise SystemExit(f"arena: what's '{ln}'?")

    def add_foe(self, text):
        m = re.fullmatch(r"(\w+)(?:\s*x\s*(\d+))?", text.strip())
        if not m or m.group(1).upper() not in REG["foes"]:
            raise SystemExit(f"arena: '{text}': not a foe in registry/foes.txt "
                             f"({', '.join(REG['foes'])})")
        self.foes.append([m.group(1).upper(), int(m.group(2) or 1)])

    def set_sweep(self, what, span):
        if what not in ("level", "count"):
            raise SystemExit("arena: sweep level or sweep count")
        a, _, b = span.partition("-")
        self.sweep = (what, int(a), int(b or a))

    def file(self):
        """The fights, as build/arena reads them."""
        rows = self.map or ["." * 12] * 8
        h, w = len(rows), max(len(r) for r in rows)
        out = [f"fights {self.fights}", f"seed {self.seed}", f"rounds {self.rounds}", f"map {w} {h}"]
        out += [r.ljust(w, ".") for r in rows]
        starts = [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "@"]
        foes = [name for name, n in self.foes for _ in range(n)]
        if len(self.travelers) + len(foes) > 8:
            raise SystemExit("arena: 8 fighters at most (the battle engine's limit)")
        lefts = self.line_up(len(self.travelers), 1, h) if not starts else starts
        foe_starts = [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c.islower()]
        rights = foe_starts if len(foe_starts) >= len(foes) else self.line_up(len(foes), w - 2, h)
        if len(lefts) < len(self.travelers):
            raise SystemExit("arena: the map hasn't an @ for every traveler")
        for t, (x, y) in zip(self.travelers, lefts):
            out.append(t.line(x, y))
        for name, (x, y) in zip(foes, rights):
            out.append(foe_line(name, x, y))
        return "\n".join(out) + "\n", foes

    @staticmethod
    def line_up(n, x, h):
        """n squares down column x, spread out round the middle."""
        top = max(0, (h - 2 * n + 1) // 2)
        ys = [top + 2 * i for i in range(n)] if 2 * n - 1 <= h else list(range(n))
        return [(x, y) for y in ys]


# ------------------------------------------------------------------------ fighting

def fight(m, show=None):
    text, foes = m.file()
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text)
        path = f.name
    try:
        if show is not None:
            one = text.replace(f"fights {m.fights}", "fights 1").replace(f"seed {m.seed}", f"seed {m.seed + show}")
            with open(path, "w") as f:
                f.write(one)
            p = subprocess.run([ARENA, "-v", path], capture_output=True, text=True)
            return p.stdout + p.stderr, foes
        p = subprocess.run([ARENA, path], capture_output=True, text=True)
    finally:
        os.unlink(path)
    if p.returncode:
        raise SystemExit(p.stderr.strip())
    results = []
    for ln in p.stdout.split("\n"):
        w = ln.split()
        if len(w) < 4:
            continue
        nums = list(map(int, w[4:]))
        results.append({"result": w[2], "rounds": int(w[3]),
                        "fighters": [tuple(nums[i:i + 3]) for i in range(0, len(nums), 3)]})
    return results, foes


def summary(m, results, foes):
    n = len(results)
    pct = lambda k: 100 * sum(r["result"] == k for r in results) / n
    rounds = [r["rounds"] for r in results]
    labels = [t.label() for t in m.travelers] + [REG["foes"][f]["display"] for f in foes]
    healths = [t.health for t in m.travelers] + [REG["foes"][f]["health"] for f in foes]
    out = {"won": pct("won"), "lost": pct("lost"), "fled": pct("fled"), "draw": pct("draw"),
           "rounds": statistics.mean(rounds), "fighters": []}
    for i, (label, hp) in enumerate(zip(labels, healths)):
        left = [r["fighters"][i][0] for r in results]
        out["fighters"].append({
            "label": label, "health": hp,
            "left": statistics.mean(left), "dealt": statistics.mean(r["fighters"][i][1] for r in results),
            "down": 100 * sum(r["fighters"][i][2] > 0 for r in results) / n})
    return out


def report(m, s):
    who = " and ".join(t.label() for t in m.travelers)
    them = ", ".join(f"{REG['foes'][f]['display']}{' x' + str(c) if c > 1 else ''}" for f, c in m.foes)
    print(f"{who} against {them}: {m.fights} fights")
    print(f"  the travelers win {s['won']:.0f}%, lose {s['lost']:.0f}%"
          + (f", flee {s['fled']:.0f}%" if s["fled"] else "")
          + (f", draw {s['draw']:.0f}% (still on after {m.rounds} rounds)" if s["draw"] else "")
          + f"; {s['rounds']:.1f} rounds on average")
    for f in s["fighters"]:
        print(f"  {f['label']:<26} health {f['health']:>3}, {f['left']:5.1f} left on average, "
              f"down in {f['down']:3.0f}%, deals {f['dealt']:5.1f}")


def sweep(m):
    what, a, b = m.sweep
    print(f"{'level' if what == 'level' else 'count':>5}  win%  lose%  rounds  travelers' health left")
    for v in range(a, b + 1):
        if what == "level":
            for t in m.travelers:
                t.level = v
        else:
            m.foes[-1][1] = v
        results, foes = fight(m)
        s = summary(m, results, foes)
        left = sum(f["left"] for f in s["fighters"][:len(m.travelers)])
        most = sum(t.health for t in m.travelers)
        print(f"{v:>5}  {s['won']:4.0f}  {s['lost']:5.0f}  {s['rounds']:6.1f}  {100 * left / most:5.0f}%")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    args = argv[1:]
    opts = {}
    for k in ("--fights", "--sweep", "--show", "--seed"):
        if k in args:
            i = args.index(k)
            n = 3 if k == "--sweep" else 2
            opts[k] = args[i + 1:i + n]
            del args[i:i + n]
    m = Matchup()
    if len(args) == 1 and os.path.exists(args[0]):
        m.read(open(args[0]).read())
    elif "vs" in args:
        i = args.index("vs")
        for t in args[:i]:
            m.travelers.append(Traveler(t.split()))
        for f in args[i + 1:]:
            m.add_foe(f)
    else:
        print(__doc__)
        return 2
    if "--fights" in opts:
        m.fights = int(opts["--fights"][0])
    if "--seed" in opts:
        m.seed = int(opts["--seed"][0])
    if "--sweep" in opts:
        m.set_sweep(*opts["--sweep"])
    if not m.travelers or not m.foes:
        raise SystemExit("arena: a fight needs travelers and foes")
    if not os.path.exists(ARENA):
        raise SystemExit("arena: build/arena isn't built: make build/arena")
    if "--show" in opts:
        log, _ = fight(m, int(opts["--show"][0]))
        print(log, end="")
    elif m.sweep:
        sweep(m)
    else:
        results, foes = fight(m)
        report(m, summary(m, results, foes))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
