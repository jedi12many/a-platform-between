"""Tests for the registry loader: the real files load, and mistakes give clear errors."""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry  # noqa: E402

failures = 0


def check(cond, what):
    global failures
    if not cond:
        failures += 1
        print(f"FAIL: {what}")


def broken(filename, text, expect):
    """Copy the real registry, replace one file, and expect an error mentioning `expect`."""
    tmp = tempfile.mkdtemp()
    try:
        for f in os.listdir(registry.ROOT):
            shutil.copy(os.path.join(registry.ROOT, f), tmp)
        with open(os.path.join(tmp, filename), "w") as f:
            f.write(text)
        try:
            registry.load(tmp)
            check(False, f"{filename}: expected an error about '{expect}'")
        except registry.RegistryError as e:
            check(expect in str(e) and filename in str(e) and "line" in str(e),
                  f"{filename}: error '{e}' should mention '{expect}'")
    finally:
        shutil.rmtree(tmp)


reg = registry.load()
check(reg["races"]["SALVAGED"]["display"] == "Salvaged", "race names")
check(reg["classes"]["WARDEN"]["tags"] == [0, 4], "class tags are skill ids")
check(reg["items"]["PULSE_RIFLE"]["tier"] == 4, "item tier")
check(reg["echoes"]["WOLF_PUP"]["states"] == ["SAVED", "LEFT", "SWORN"], "echo states")
check(reg["echoes"]["WOLF_PUP"]["default"] == 2, "echo default is LEFT")

broken("items.txt", '1 A ranged 4 energy 8 0 "A"\n1 B ranged 4 energy 8 0 "B"\n',
       "append-only")
broken("items.txt", '1 A ranged 4 energy 8 0 "A"\n2 A ranged 4 energy 8 0 "B"\n',
       "already used")
broken("items.txt", '1 A blaster 4 energy 8 0 "A"\n', "archetype 'blaster'")
broken("items.txt", '1 A ranged 12 energy 8 0 "A"\n', "tier 12")
broken("items.txt", '1 A ranged 4 energy 8 0 "Café"\n', "plain ASCII")
broken("races.txt", '0 HUMAN FATE "Human"\n2 ELF WITS "Elf"\n', "can't have gaps")
broken("races.txt", '0 HUMAN LUCK "Human"\n', "stat 'LUCK'")
broken("classes.txt", '0 WARDEN MIGHT MELEE MELEE "Warden"\n', "two different skills")
broken("classes.txt", '0 WARDEN MIGHT MELEE SWORDS "Warden"\n', "no skill called 'SWORDS'")
broken("echoes.txt", "1 WOLF ally 02 SAVED LEFT SWORN\n", "exactly one state")
broken("echoes.txt", "1 WOLF ally 02 SAVED* LEFT SWORN GONE\n", "at most 3 states")
broken("echoes.txt", "1 WOLF friend 02 SAVED* LEFT\n", "kind 'friend'")
broken("skills.txt", "".join(f'{i} S{i} MIGHT "S{i}"\n' for i in range(13)), "id 12")

check(reg["foes"]["RUST_GUARD"]["weak"] == 1 and reg["foes"]["ASH_RAT"]["coward"], "foes")
FOE = '1 RAT 6 50 0 0 0 6 30 2 kinetic melee 0 - {} "Rat"\n'
broken("foes.txt", FOE.format("charge+brave"), "+coward")
broken("foes.txt", FOE.format("lurk"), "behavior 'lurk'")
broken("foes.txt", FOE.format("charge").replace("melee", "thrown"), "reach 'thrown'")
broken("foes.txt", FOE.format("charge").replace(" 6 50", " 0 50", 1), "health 0")
broken("foes.txt", FOE.format("charge") + FOE.format("shoot"), "append-only")

print(f"registry tests: {failures} failed")
sys.exit(1 if failures else 0)
