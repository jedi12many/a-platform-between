"""Decode the password the C demo printed, with the Python reference, and check it.

Usage: python3 check_against_demo.py <demo output file>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import passport  # noqa: E402

lines = open(sys.argv[1]).read().splitlines()
start = lines.index("PASSPORT:") + 1
pw = ""
for line in lines[start:]:
    if not line.strip():
        break
    pw += line.strip()

ch = passport.decode(pw)
assert ch["name"] == "KESTREL", ch["name"]
assert passport.RACES[ch["race"]] == "Salvaged"
assert passport.CLASSES[ch["class"]] == "Warden"
assert ch["level"] == 3, ch["level"]
assert ch["echoes"] == [(4, 1)], ch["echoes"]      # WOLF_PUP: SAVED
assert ch["equipped"] == {0: 1}, ch["equipped"]    # PULSE_RIFLE
assert passport.encode(ch) == pw, "re-encoding differs"
print(f"python reference: decoded and re-encoded the C password ({len(pw)} symbols)")
