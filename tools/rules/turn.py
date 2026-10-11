"""Reference for rules v1's turn (docs/turn.md), written from the doc, independently of the
rules lab's engine (core/next/battle.c), so the two can check each other: Speed, a
fighter's numbers with its conditions, putting conditions on (the same twice, opposites,
immunity, the limit of four), damage through weaknesses and a barrier, and the bonuses
to a roll. The arena's tools and the tabletop can use it too.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "registry"))
import registry  # noqa: E402

REG = registry.load()
CONDS = registry.load_conditions(races=REG["races"])
POWERS = registry.load_powers(classes=REG["classes"], conditions=CONDS)
POWER_BY_ID = {p["id"]: p for p in POWERS.values()}
BY_ID = {c["id"]: c for c in CONDS.values()}
STATS = registry.STATS
TRAIT_SLOTS, OTHER_SLOTS = 2, 4


def speed_v1(grace, armor_tier):
    """5, +1 at Grace 60, +1 more at 90; heavy armor (tier 3 and up) costs 1."""
    return 5 + (grace >= 60) + (grace >= 90) - (armor_tier >= 3)


def traits(race):
    """A race's two traits, by name."""
    return [c["name"] for c in sorted(CONDS.values(), key=lambda c: c["id"])
            if c["effects"].get("race") == race]


class Fighter:
    """A fighter's conditions: its traits (for good) and four slots for the others, each
    [name, rounds left] (None: no countdown) or None. On a tie for the fewest rounds left,
    the first slot goes."""

    def __init__(self, race=None, speed=5, dodge=0, armor=0, ward=0, soak=0):
        self.base = {"speed": speed, "dodge": dodge, "armor": armor, "ward": ward, "soak": soak}
        self.traits = traits(race) if race else []
        self.slots = [None] * OTHER_SLOTS
        self.barrier = 0
        self.said = []                                  # what happened, for checking

    def names(self):
        return self.traits + [o[0] for o in self.slots if o]

    def effects(self):
        return [CONDS[n]["effects"] for n in self.names()]

    def immune(self, name):
        return any(name in e.get("immune", []) for e in self.effects())

    def put(self, name, tier=1):
        """docs/turn.md, Getting one: immune, it never lands; its opposite ends; the same
        again keeps the longer time (and the higher tier); a fifth replaces the one with
        fewest rounds left. A tiered one's numbers are its tier times its tier-1 numbers."""
        c = CONDS[name]
        tier = tier if c["effects"].get("tiered") else 1
        if self.immune(name):
            self.said.append(("immune", name))
            return
        if c["opposite"]:
            self.take_off(c["opposite"])
        if name in self.traits:
            return
        for o in self.slots:
            if o and o[0] == name:
                if o[1] is not None and c["rounds"] and c["rounds"] > o[1]:
                    o[1] = c["rounds"]
                o[2] = max(o[2], tier)
                if c["effects"].get("barrier"):
                    self.barrier = c["effects"]["barrier"] * o[2]
                return
        if None not in self.slots:
            least = min(range(OTHER_SLOTS), key=lambda i: (self.slots[i][1] or 254, i))
            self.take_off(self.slots[least][0])
        self.slots[self.slots.index(None)] = [name, c["rounds"], tier]
        if c["effects"].get("barrier"):
            self.barrier = c["effects"]["barrier"] * tier
        self.said.append(("on", name))

    def take_off(self, name):
        for i, o in enumerate(self.slots):
            if o and o[0] == name:
                self.slots[i] = None
                if CONDS[name]["effects"].get("barrier"):
                    self.barrier = 0
                self.said.append(("off", name))

    def tiers(self):
        """Each condition's effects and its tier (a trait's: 1)."""
        return [(CONDS[n]["effects"], 1) for n in self.traits] + \
            [(CONDS[o[0]]["effects"], o[2]) for o in self.slots if o]

    def total(self, key):
        return sum(e.get(key, 0) * (t if e.get("tiered") else 1) for e, t in self.tiers())

    def speed(self):
        """Only the worst penalty and the best bonus count; never below 0; stopped is 0."""
        if any(e.get("speed0") for e in self.effects()):
            return 0
        mods = [e.get("speed", 0) for e in self.effects()]
        return max(0, self.base["speed"] + min([0] + mods) + max([0] + mods))

    def dodge(self):
        if any(e.get("dodge0") for e in self.effects()):
            return 0
        return max(0, self.base["dodge"] + self.total("dodge"))

    def armor(self):
        return max(0, self.base["armor"] + self.total("armor"))

    def ward(self):
        return max(0, self.base["ward"] + self.total("ward"))

    def soak(self):
        return max(0, self.base["soak"] + self.total("soak"))

    def flying(self):
        return any(e.get("fly") for e in self.effects())

    def attack_bonus(self, melee):
        """Added to an attack roll: rolls, attacks, the next attack, and melee if melee."""
        return self.total("rolls") + self.total("attacks") + self.total("next") + \
            (self.total("melee") if melee else 0)

    def shake_bonus(self):
        return self.total("shake") + self.total("rolls")

    def through(self, dmg, kind):
        """Damage past Soak (or that Soak doesn't touch), of a type or None: doubled by a
        weakness to it, then a barrier takes what it can. Returns (to health, absorbed)."""
        if kind is not None and any(e.get("vulnerable") == kind for e in self.effects()):
            dmg *= 2
        took = min(dmg, self.barrier)
        self.barrier -= took
        if took and not self.barrier:
            for n in [o[0] for o in self.slots if o and CONDS[o[0]]["effects"].get("barrier")]:
                self.take_off(n)
        return dmg - took, took


def stand_up_move(speed):
    """Standing up takes half your Speed, rounded up: what's left to move."""
    return speed - (speed + 1) // 2


SLAM = 3                    # pushed into a wall or another fighter (Soak counts)
HAZARD = 5                  # a hazard's damage, unless the map says otherwise


# ---------------------------------------------------------------- powers (docs/turn.md)

def power_tier(rank):
    """1 + rank / 20: rank 0-19 is tier 1, 100 is tier 6."""
    return 1 + min(rank, 100) // 20


def power_rating(stat, rank):
    """A power's roll: half its class's stat, plus its rank (as a skill's training)."""
    return stat // 2 + rank


def burst_area(tier):
    return 2 if tier >= 6 else 1


def field_length(tier):
    return tier + 2


def power_damage(tier):
    """A bolt's or a burst's: 5 x tier, as a weapon's."""
    return 5 * tier


def hex_damage(tier):
    """A hex's: half a bolt's, rounded up."""
    return (5 * tier + 1) // 2


def mend(tier):
    return 5 * tier


def shift_reach(tier):
    return tier + 2
