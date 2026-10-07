"""Reference implementation of the combat rules (docs/combat.md) and the core roll
(docs/rules-v0.md), written from the docs, independently of core/src/combat.c and
core/src/rules.c, so the two can check each other. The Waystation and tabletop tools can
use it too.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "registry"))
import registry  # noqa: E402

REG = registry.load()
ITEMS = {e["id"]: e for e in REG["items"].values()}
MIGHT, GRACE = 0, 1
ARMOR = registry.ARCHETYPES.index("armor")

FAIL, COST, SUCCESS, CRIT = 0, 1, 2, 3
UNARMED = 2


def d100s(seed):
    """The rules' dice: xorshift16 (7, 9, 8), seed 0 meaning 0xACE1; the top seven bits,
    0..99 kept, plus one."""
    x = seed or 0xACE1
    while True:
        x ^= (x << 7) & 0xFFFF
        x ^= x >> 9
        x ^= (x << 8) & 0xFFFF
        if x >> 9 < 100:
            yield (x >> 9) + 1


def resolve(roll, total, tn):
    """docs/rules-v0.md: a natural 01 fails, a natural 100 crits; beat the TN to succeed
    (crit on doubles); 1 to 20 short of beating it (81..100 against 100) is a cost."""
    if roll == 1:
        return FAIL
    if roll == 100:
        return CRIT
    if total > tn:
        return CRIT if roll % 11 == 0 else SUCCESS
    return COST if tn - total < 20 else FAIL


def dodge(ch):
    return ch["stats"][GRACE] // 5


def speed(ch):
    return 4 + ch["stats"][GRACE] // 25


def armor(ch):
    tiers = [ITEMS[i]["tier"] for i in ch["equipped"].values()
             if i in ITEMS and ITEMS[i]["archetype"] == ARMOR]
    return 10 * max(tiers, default=0)


def melee_bonus(ch):
    return ch["stats"][MIGHT] // 20


def weapon_damage(item):
    return 5 * ITEMS[item]["tier"] if item in ITEMS else UNARMED


def hit_tn(dodge_, defense, bonus=0, reduce=0):
    return 50 + max(0, dodge_ + defense + bonus - reduce)


def damage(roll, total, tn, weapon, stat_bonus, soak):
    result = resolve(roll, total, tn)
    if result == FAIL:
        return 0
    if result == COST:
        dmg = weapon // 2
    else:
        dmg = weapon + stat_bonus + max(0, total - tn) // 10
        if result == CRIT:
            dmg *= 2
    return max(0, dmg - soak)


def in_area(dx, dy, area):
    return max(abs(dx), abs(dy)) <= area


def flee_tn(adjacent):
    return 100 + 10 * adjacent
