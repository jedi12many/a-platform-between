"""Combat rules: the C core must agree with the Python reference written from the docs.

Random attacks (any rating, bonus, TN, weapon, stat bonus and Soak, with the dice running
on from the seed) and random characters' combat numbers (dodge, speed, armor, melee bonus,
weapon damage) from build/attack must match tools/rules/combat.py, natively and, for a
sample, on sim65.

    python3 tests/combat/check_combat.py
"""

import os
import random
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "rules"))
sys.path.insert(0, os.path.join(ROOT, "tools", "passport"))

import combat  # noqa: E402
import passport  # noqa: E402

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL:", msg)


def run(sim, *args):
    cmd = (["sim65", "build/attack.sim"] if sim else ["build/attack"]) + [str(a) for a in args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, timeout=600).stdout


def attacks(rng, sim):
    seed = rng.randrange(65536)
    n = 30
    rating, bonus = rng.randint(0, 100), rng.choice([0, 0, 10, 20, -20, rng.randint(-40, 40)])
    tn = rng.choice([50, 74, 88, 100, 140, rng.randint(50, 250)])
    weapon, stat, soak = rng.choice([2, 5, 20, 45, rng.randint(0, 45)]), rng.randint(0, 5), \
        rng.choice([0, 0, 2, 10, rng.randint(0, 60)])
    dice = combat.d100s(seed)
    want = ""
    for _ in range(n):
        roll = next(dice)
        total = roll + rating + bonus
        want += (f"{roll} {total} {combat.resolve(roll, total, tn)} "
                 f"{combat.damage(roll, total, tn, weapon, stat, soak)}\n")
    got = run(sim, "attacks", seed, n, rating, bonus, tn, weapon, stat, soak)
    if got != want:
        fail(f"attacks seed {seed} rating {rating} bonus {bonus} TN {tn} weapon {weapon} "
             f"stat {stat} soak {soak}{' on the 6502' if sim else ''}")


def sheet(rng, sim):
    reg = passport._REG
    race = rng.choice(sorted(reg["races"]))
    cls = rng.choice(sorted(reg["classes"]))
    tags = reg["classes"][cls]["tags"]
    extra = rng.choice([s for s in sorted(reg["skills"]) if reg["skills"][s]["id"] not in tags])
    stats = [25] * 6
    for _ in range(150):
        i = rng.choice([s for s in range(6) if stats[s] < 70])
        stats[i] += 1
    ch = passport.create("T", race, cls, stats, extra)
    ch["stats"] = [rng.randint(0, 100) if rng.random() < 0.3 else v for v in ch["stats"]]
    items = sorted(combat.ITEMS)
    ch["equipped"] = {s: rng.choice(items) for s in range(6) if rng.random() < 0.5}
    want = (f"{combat.dodge(ch)} {combat.speed(ch)} {combat.armor(ch)} {combat.melee_bonus(ch)}"
            + "".join(f" {combat.weapon_damage(ch['equipped'][s])}" for s in sorted(ch["equipped"]))
            + "\n")
    got = run(sim, "sheet", passport.encode(ch))
    if got != want:
        fail(f"sheet {ch['stats']} {ch['equipped']}: C {got!r}, Python {want!r}"
             f"{' on the 6502' if sim else ''}")


def main():
    rng = random.Random(1985)
    count, sample = 300, 10
    for i in range(count):
        attacks(rng, False)
        sheet(rng, False)
        if i < sample:
            attacks(rng, True)
            sheet(rng, True)
    print(f"combat: {count} random fights of {30} attacks and {count} random sheets checked "
          f"against the reference ({sample} of each on the 6502), {failures} failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
