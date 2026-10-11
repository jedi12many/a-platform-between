"""The cartridge's fight (cart/combat.s, cart/battle.s) against the C engine's reviewed
logs, and its rules against the Python reference.

    python3 tests/cart/test_battle.py IMAGE LABELS [--cases N]

The cartridge boots on the emulator (tests/cart/run_cart.py) to its first wait for a key,
stages the fight's asset (asset 2) as the game does, and its routines are called as the
battle screen calls them. Each scenario in tests/battle/*.txt (the format is
tests/battle/battle.c's) is played: travelers boarded from their Passports
(password_decode, fighter_from), foes added, the map laid, the actions taken; every event
it tells through battle_event is written as battle.c writes it, and the log must be
tests/battle/expected/NAME.log, line for line (the logs tests/battle/run_battles.py holds
the C engine to, reviewed by hand). Then, at random: hit_tn, damage and flee_tn must give
what tools/rules/combat.py gives; fighter_from must make the fighter docs/combat.md makes
of random travelers and weapons; and random battles (random maps, fighters and actions,
many not allowed) must play out the same as the C engine (build/battle), event for event.
"""

import glob
import os
import random
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tests", "cart"))
sys.path.insert(0, os.path.join(ROOT, "tests", "battle"))
sys.path.insert(0, os.path.join(ROOT, "tools", "rules"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))
sys.path.insert(0, os.path.join(ROOT, "tests", "passport"))
import run_cart  # noqa: E402
import combat  # noqa: E402
import passport  # noqa: E402
from cases import random_traveler  # noqa: E402
from test_passwords import record_of  # noqa: E402
from run_battles import random_battle  # noqa: E402

STOP = 0x0300                       # a routine "returns" here: the run stops
HEARD = 0x0303                      # the event hook: an RTS, each visit an event
TEXT = 0xA0A5                       # RAM the game doesn't use yet
ASSET_BATTLE = 2
RESULTS = ["fail", "cost", "success", "crit"]
ENDINGS = ["on", "won", "lost", "fled"]
TILES = {"#": 1, "O": 2, "~": 3, "+": 4, "^": 5, "=": 6, ">": 7}
SURPRISE = {"none": 0, "foes": 1, "travelers": 2}

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


class Cart:
    def __init__(self, image, labels):
        self.c = run_cart.C64(open(image, "rb").read(), run_cart.labels(labels))
        self.c.boot()
        self.c.run()                                        # to its first wait for a key
        self.s = self.c.syms
        self.c.ram[HEARD] = 0x60
        self.log = []
        self.call("asset_fetch", ASSET_BATTLE)

    def call(self, routine, a=0, x=0, y=0):
        c, m = self.c, self.c.mpu
        ret = STOP - 1
        for b in (ret >> 8, ret & 0xFF):
            c.ram[0x100 + m.sp] = b
            m.sp = (m.sp - 1) & 0xFF
        m.a, m.x, m.y, m.pc = a, x, y, self.s[routine]
        steps = 0
        while m.pc != STOP:
            if m.pc == HEARD:
                self.heard()
            c.start, c.op, c.pc0 = m.processorCycles, c.mem[m.pc], m.pc
            m.step()
            c.raster()
            steps += 1
            if steps > 20_000_000:
                raise RuntimeError(f"{routine} never returned")
        return m.a

    def byte(self, name, at=0):
        return self.c.ram[self.s[name] + at]

    def word(self, name):
        return self.byte(name) | self.byte(name, 1) << 8

    def poke(self, name, *values, at=0):
        for i, v in enumerate(values):
            self.c.ram[self.s[name] + at + i] = v & 0xFF

    def signed(self, v):
        return v - 0x10000 if v & 0x8000 else v

    def heard(self):
        """The event in ev_*, written as tests/battle/battle.c writes it."""
        kind, actor, target = self.byte("ev_kind"), self.byte("ev_actor"), self.byte("ev_target")
        x, y, value = self.byte("ev_x"), self.byte("ev_y"), self.word("ev_value")
        roll, total, tn = self.byte("ev_roll"), self.signed(self.word("ev_total")), self.signed(self.word("ev_tn"))
        result = RESULTS[self.byte("ev_result") & 3]
        out = {
            0: lambda: f"round {value}: {actor}'s turn",
            1: lambda: f"  {actor} moves to {x},{y}",
            2: lambda: f"  {actor} attacks {target}: {roll}+{total - roll}={total} vs {tn}: {result}, "
                       f"{value} damage",
            3: lambda: f"  {target} is down",
            4: lambda: f"  {actor} takes {value} from the ground",
            5: lambda: f"  {actor} guards",
            6: lambda: f"  {actor} waits",
            7: lambda: (f"  {actor} tries to flee: {roll}+{total - roll}={total} vs {tn}: {result}"
                        if roll else f"  {actor} takes the exit"),
            8: lambda: f"  {actor} is gone",
            9: lambda: f"the fight is {ENDINGS[value & 3]}",
            10: lambda: f"  {actor} gets a free attack on {target}",
        }.get(kind, lambda: f"  (event {kind})")()
        self.log.append(out)

    def decode(self, s):
        for i, ch in enumerate(s.encode("ascii") + b"\0"):
            self.c.ram[TEXT + i] = ch
        return self.call("password_decode", TEXT & 0xFF, TEXT >> 8)

    def play(self, path):
        """A scenario, as tests/battle/battle.c plays it. After: its log."""
        self.log = []
        rows, in_map, started, travelers, surprise = [], False, False, 0, 0
        self.call("rng_seed", 1, 0)
        n = lambda: self.byte("fighter_count")                          # noqa: E731

        def find(c, k):
            for j, row in enumerate(rows[:self.byte("map_h")]):
                for i, ch in enumerate(row[:self.byte("map_w")]):
                    if ch == c:
                        if k == 0:
                            return i, j
                        k -= 1
            return 0, 0

        def add():
            if self.call("battle_add") == 0xFF:
                self.log.append("couldn't place it")

        for line in open(path):
            line = line.rstrip("\r\n")
            if in_map:
                if line == "end":
                    in_map = False
                    w = max(len(r) for r in rows) if rows else 0
                    self.call("battle_init", min(w, 16), len(rows))
                    self.poke("event_hook", HEARD & 0xFF, HEARD >> 8)
                    for j in range(self.byte("map_h")):
                        for i in range(self.byte("map_w")):
                            ch = rows[j][i] if i < len(rows[j]) else "\0"
                            self.call("battle_set_tile", TILES.get(ch, 0), i, j)
                elif len(rows) < 10:
                    rows.append(line[:16])
                continue
            w = line.split()
            if not w or line.startswith("#"):
                continue
            if w[0] == "seed":
                seed = int(w[1]) & 0xFFFF
                self.call("rng_seed", seed & 0xFF, seed >> 8)
            elif w[0] == "surprise":
                surprise = SURPRISE["foes" if "foes" in line else "travelers" if "travelers" in line
                                    else "none"]
            elif w[0] == "map":
                in_map, rows = True, []
            elif w[0] == "traveler":
                if self.decode(w[1]) != 0:
                    self.log.append(f"bad traveler: {line}")
                    return self.log
                item = int(w[2])
                self.call("fighter_from", item & 0xFF, item >> 8)
                if len(w) > 3:
                    self.poke("new_fighter", int(w[3]), at=4)
                x, y = find("@", travelers)
                travelers += 1
                self.poke("new_fighter", x, y, at=2)
                self.call("hit_tn", self.byte("new_fighter", 7), self.byte("new_fighter", 8), 0)
                self.log.append(f"{n()}: traveler at {x},{y}, health {self.byte('new_fighter', 4)}, "
                                f"attack {self.byte('new_fighter', 12)}, TN to hit {self.word('chk_tn')}")
                add()
            elif w[0] == "foe":
                v = [int(t) for t in w[2:18]]
                x, y = find(w[1], 0)
                # apb_fighter: side state x y health health_max grace dodge armor ward soak
                # speed attack athletics weapon stat_bonus ranged power dmg_type area
                # weak_type behavior coward guarding waited
                fields = [1, 0, x, y, v[0], v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], 0,
                          v[8], 0, v[9], v[10], v[11], v[12], v[13], v[14], v[15], 0, 0]
                self.poke("new_fighter", *fields)
                self.log.append(f"{n()}: foe {w[1]} at {x},{y}, health {v[0]}")
                add()
            elif w[0] == "act":
                if not started:
                    self.call("battle_start", surprise)
                    started = True
                who = self.call("battle_next")
                if who == 0xFF:
                    break
                if line.strip() == "act q":
                    self.call("battle_quick", who)
                    self.log.append(f"  (quick: act {self.byte('act_x')} {self.byte('act_y')} "
                                    f"{self.byte('act_kind')} {self.byte('act_target')})")
                else:
                    v = [int(t) for t in w[1:5]]
                    self.poke("act_x", v[0])
                    self.poke("act_y", v[1])
                    self.poke("act_kind", v[2])
                    self.poke("act_target", v[3])
                if self.call("battle_act", who) == 0:
                    self.log.append(f"  (not allowed: {line})")
        if not started:
            self.call("battle_start", surprise)
        if self.call("battle_next") != 0xFF:
            self.log.append("out of actions")
        return self.log


def scenarios(cart):
    for path in sorted(glob.glob(os.path.join(ROOT, "tests", "battle", "*.txt"))):
        name = os.path.basename(path)[:-4]
        got = cart.play(path)
        want = open(os.path.join(ROOT, "tests", "battle", "expected", name + ".log")).read().splitlines()
        if got != want:
            at = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
            fail(f"{name}: line {at + 1} differs from tests/battle/expected/{name}.log:\n"
                 f"  cart: {got[at] if at < len(got) else '(the end)'}\n"
                 f"  C:    {want[at] if at < len(want) else '(the end)'}")
        else:
            print(f"ok  {name}: the cartridge's log is the reviewed one, {len(got)} lines")


def rules(cart, cases, rnd):
    """hit_tn, damage and flee_tn against tools/rules/combat.py."""
    bad = 0
    for _ in range(cases):
        dodge, defense, bonus = rnd.randrange(256), rnd.randrange(256), rnd.choice([0, 20, rnd.randrange(256)])
        cart.call("hit_tn", dodge, defense, bonus)
        want = combat.hit_tn(dodge, defense, bonus)
        if cart.word("chk_tn") != want:
            bad += 1
            fail(f"hit_tn({dodge}, {defense}, {bonus}) = {cart.word('chk_tn')}, the rules say {want}")
        roll = rnd.randint(1, 100)
        total = roll + rnd.randrange(256)
        tn = rnd.randrange(50, 560)
        weapon, stat, soak = rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)
        cart.poke("chk_roll", roll)
        cart.poke("chk_total", total & 0xFF, total >> 8)
        cart.poke("chk_tn", tn & 0xFF, tn >> 8)
        cart.call("resolve")
        if cart.byte("chk_result") != combat.resolve(roll, total, tn):
            bad += 1
            fail(f"resolve({roll}, {total}, {tn}) = {cart.byte('chk_result')}")
        cart.call("damage", weapon, stat, soak)
        want = combat.damage(roll, total, tn, weapon, stat, soak)
        if cart.word("dmg") != want:
            bad += 1
            fail(f"damage({roll}, {total}, {tn}, {weapon}, {stat}, {soak}) = {cart.word('dmg')}, "
                 f"the rules say {want}")
        foes = rnd.randint(0, 8)
        if cart.call("flee_tn", foes) != combat.flee_tn(foes):
            bad += 1
            fail(f"flee_tn({foes})")
        if bad > 5:
            return
    print(f"ok  rules: {cases} random hit_tn, resolve, damage and flee_tn as tools/rules/combat.py says")


def rating(ch, name):
    """A skill's rating (docs/rules-v0.md): its stat / 2 + training, 100 at most."""
    s = passport._REG["skills"][name]
    return min(100, ch["stats"][s["stat"]] // 2 + ch["training"].get(s["id"], 0))


def fighter_ref(ch, item):
    """The traveler as a fighter (docs/combat.md), in apb_fighter's order."""
    arch, dmg_type = 0, 0
    if item in combat.ITEMS and combat.ITEMS[item]["tier"]:
        arch, dmg_type = combat.ITEMS[item]["archetype"], combat.ITEMS[item]["damage"]
    health = (10 + ch["stats"][2] // 4 + 2 * ch["level"]) & 0xFF
    ranged, power, bonus = arch in (1, 4), arch == 4, 0
    if arch == 1:
        attack = rating(ch, "RANGED")
    elif arch == 4:
        attack = rating(ch, "CHANNEL")
    else:
        attack, bonus = rating(ch, "MELEE"), combat.melee_bonus(ch)
    return [0, 0, 0, 0, health, health, ch["stats"][1], combat.dodge(ch), combat.armor(ch), 0, 0,
            combat.speed(ch), attack, rating(ch, "ATHLETICS"), combat.weapon_damage(item), bonus,
            int(ranged), int(power), dmg_type, 0, 0xFF, 1 if ranged else 0, 0, 0, 0]


def fighters(cart, cases, rnd):
    """fighter_from against the doc's rules, for random travelers and weapons."""
    items = sorted(combat.ITEMS)
    bad = 0
    for n in range(cases):
        ch = random_traveler(rnd)
        record = record_of(ch)
        for i, b in enumerate(record):
            cart.c.ram[cart.s["traveler"] + i] = b
        item = rnd.choice(items + [0, 0, rnd.randrange(65536)])
        cart.call("fighter_from", item & 0xFF, item >> 8)
        got = [cart.byte("new_fighter", i) for i in range(25)]
        want = fighter_ref(ch, item)
        if got != want:
            bad += 1
            fail(f"fighter_from, traveler {n}, item {item}:\n  got  {got}\n  want {want}")
            if bad > 3:
                return
    print(f"ok  fighters: {cases} random travelers and weapons made into fighters as docs/combat.md says")


def random_battles(cart, cases, rnd):
    """Random battles, the cartridge against the C engine (build/battle)."""
    path = os.path.join(ROOT, "build", "cart", "random-battle.txt")
    same = 0
    for i in range(cases):
        random_battle(rnd, path)
        want = subprocess.run([os.path.join(ROOT, "build", "battle"), path], capture_output=True,
                              text=True, timeout=20).stdout.splitlines()
        got = cart.play(path)
        if got != want:
            at = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), min(len(got), len(want)))
            os.replace(path, path.replace(".txt", f"-{i}.txt"))
            fail(f"random battle {i} (build/cart/random-battle-{i}.txt): line {at + 1} differs:\n"
                 f"  cart: {got[at] if at < len(got) else '(the end)'}\n"
                 f"  C:    {want[at] if at < len(want) else '(the end)'}")
            if failures > 3:
                return
        else:
            same += 1
    print(f"ok  random battles: {same} of {cases} played as the C engine plays them")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cases = int(argv[argv.index("--cases") + 1]) if "--cases" in argv else 60
    cart = Cart(argv[1], argv[2])
    rnd = random.Random(1985)
    scenarios(cart)
    rules(cart, cases * 10, rnd)
    fighters(cart, cases * 5, rnd)
    random_battles(cart, cases, rnd)
    print(f"cartridge fight: {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
