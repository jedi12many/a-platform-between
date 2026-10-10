"""A prototype of the Waystation website's side of a trip (docs/boarding.md).

The website issues Boarding Passes and remembers each ticket: who it was issued to, for
which Departure, and the character as they boarded. When a Travel Stamp comes back, it
checks the stamp against that ticket and the Departure's reward manifest, then applies the
receipt to the character as they are now. Until the website exists (milestone W2), this is
what tests and early players use; the real one will keep its ledger in a database.

    python3 tools/waystation/station.py issue LEDGER CHARACTER "PASSPORT" DEPARTURE [TICKET SEED]
    python3 tools/waystation/station.py land LEDGER CHARACTER "PASSPORT" "STAMP" MANIFEST.json

LEDGER is a JSON file (made if missing). CHARACTER names the character on the account.
`land` prints the new Passport, then what happened, in plain words.
"""

import json
import os
import secrets
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "passport"))
sys.path.insert(0, os.path.join(HERE, "..", "qsc"))
sys.path.insert(0, os.path.join(HERE, "..", "registry"))

import boarding  # noqa: E402
import passport  # noqa: E402
import receipt  # noqa: E402
import stamp  # noqa: E402
from manifest import fits  # noqa: E402


class Refused(Exception):
    """A stamp the Waystation won't apply, with the reason in plain words."""


def load(path):
    if not os.path.exists(path):
        return {"tickets": {}}
    with open(path) as f:
        return json.load(f)


def save(path, ledger):
    with open(path, "w") as f:
        json.dump(ledger, f, indent=1)


def played(ledger, character, departure):
    """Has this character already brought a stamp home from this Departure?"""
    return any(t["used"] and t["character"] == character and t["departure"] == departure
               for t in ledger["tickets"].values())


def issue(ledger, character, passport_text, departure, ticket=None, seed=None):
    """A Boarding Pass carrying this character as they are now. Tickets are random and never
    reused, so a stamp can't be forged or borrowed without guessing a live one. A
    Departure they've already played is a Rewind (docs/seasons.md)."""
    passport.decode(passport_text)                       # refuse a bad Passport now
    while ticket is None or ticket == 0 or str(ticket) in ledger["tickets"]:
        ticket = secrets.randbits(32)
    if seed is None:
        seed = secrets.randbits(16)
    rewind = played(ledger, character, departure)
    ledger["tickets"][str(ticket)] = {"character": character, "departure": departure,
                                      "boarded": passport_text, "used": False,
                                      "rewind": rewind}
    return boarding.issue(passport_text, departure, ticket, seed, rewind)


def land(ledger, character, passport_text, stamp_text, manifest):
    """Apply a Travel Stamp. Returns (new Passport text, report); raises Refused."""
    try:
        r = stamp.decode(stamp_text)
    except passport.PassportError as e:
        raise Refused(f"That isn't a Travel Stamp the Waystation can read: {e}.")
    t = ledger["tickets"].get(str(r["ticket"]))
    if t is None:
        raise Refused("The Waystation never issued that ticket.")
    if t["character"] != character:
        raise Refused("That ticket was issued to another character.")
    if t["used"]:
        raise Refused("That trip has already been stamped.")
    if t["departure"] != r["departure"]:
        raise Refused("That stamp is for a different Departure than its ticket.")
    boarded = passport.decode(t["boarded"])
    why = fits(manifest, r, boarded["debt"])
    if why:
        raise Refused(f"That stamp claims more than the Departure can give ({why}).")
    after, report = receipt.apply(passport.decode(passport_text), r, rewind=t["rewind"])
    report["rewind"] = t["rewind"]
    t["used"] = True
    return passport.encode(after), report


def describe(report):
    out = []
    if report.get("rewind"):
        out.append(f"A Rewind: half the XP, and {receipt.REWIND_FEE} Debt for the second ticket.")
    if report["levels"]:
        out.append(f"Level up! +{report['levels']}. Spend the points at the Waystation.")
    if report["stored"]:
        out.append(f"{len(report['stored'])} item(s) wouldn't fit: the lost-and-found has them.")
    if report["gone"]:
        out.append(f"{report['gone']} item(s) the trip took were already gone.")
    if report["shifted"]:
        out.append("The timeline shifted: an Echo changed elsewhere while you travelled.")
    if report["legend"]:
        out.append(f"{len(report['legend'])} old Echo(es) passed into your Legend.")
    return out or ["Stamped."]


def main(argv):
    if len(argv) in (6, 8) and argv[1] == "issue":
        path, character, text, departure = argv[2], argv[3], argv[4], int(argv[5])
        ticket, seed = (int(argv[6]), int(argv[7])) if len(argv) == 8 else (None, None)
        ledger = load(path)
        print(issue(ledger, character, text, departure, ticket, seed))
        save(path, ledger)
        return 0
    if len(argv) == 7 and argv[1] == "land":
        path, character, text, stamp_text, manifest_path = argv[2:7]
        ledger = load(path)
        with open(manifest_path) as f:
            manifest = json.load(f)
        try:
            new, report = land(ledger, character, text, stamp_text, manifest)
        except Refused as e:
            print(e, file=sys.stderr)
            return 1
        save(path, ledger)
        print("\n".join(passport.lines(new)))
        print("\n".join(describe(report)))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
