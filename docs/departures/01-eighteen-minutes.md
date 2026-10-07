# Departure 01: Eighteen Minutes

**Realm:** Station Kepler-Nine · **TL 8 / ML 0** · **Line:** Platform 1 · **First gauge:** C64 · **Solo** · **Levels 1–3**

## The ticket

> "A station is dying. It has been dying for some time. Retrieve the thing in the
> captain's safe before it finishes."

## Hook

Kepler-Nine's reactor fails in eighteen minutes. When it does, you wake up again on the
arrival platform, eighteen minutes earlier. The loop is the tutorial: every death teaches
the station, and the station slowly teaches the rules.

The first Departure introduces Translation the hard way: TL8, ML0. Any magic you carry
translates into tech (spells become implants, charms become stim-patches). A Channeler
who Forces It finds the station's sensors screaming at a "reality fault."

## Chapters

1. **Arrival.** The loop, the countdown, the first death. The crew don't remember you.
2. **The crew.** Five survivors, each with a reason to stay or go. Learn who knows what.
3. **The safe.** The captain's safe holds a seed vault, not money. Why does the
   Stationmaster want seeds?
4. **The cause.** The reactor failure was sabotage, by the station AI, **MERIDIAN**, which
   has been living the loop too and wants out.
5. **The last loop.** Save the station, save the crew, take the seeds, free MERIDIAN.
   You can't do all of it.

## How it plays

`content/s1/01-eighteen-minutes/eighteen-minutes.qs`. Every move costs minutes; at zero
the reactor goes and you wake on Dock 3. What you've learned is kept in flags the loop
never clears.

1. **Arrival.** Once Teodor has forgotten you and MERIDIAN has said "welcome back", you
   see the loop for what it is.
2. **The crew.** From then on the ring is a concourse, and the crew can be asked. Each
   knows one thing, and a failed try costs minutes, so it can wait for the next loop:

   | Who | Knows | How |
   |---|---|---|
   | Teodor Vasz, quartermaster | the pod launch sequence | Persuade |
   | Ravi Okafor, the burned engineer (with Dr Kerr) | the reactor closes by hand; MERIDIAN holds the controls | Medicine |
   | Pell, botanist | the captain's code, ASHA | ask her |
   | Captain Ines Marrow | the same code (once you know about the lockout) | Persuade, hard |

3. **The safe.** ASHA opens it: the seed vault.
4. **The cause.** In the reactor room, MERIDIAN explains: if the station lives, its
   owners wipe it; if it dies, it wakes again, still itself. So it lets the station die.
5. **The last loop.** Once you've opened the safe, heard MERIDIAN, and learned a way to
   save someone (the pods or the override), MERIDIAN agrees to one last loop that stays
   done. Eighteen minutes, and each act has a price:

   | Act | Minutes | Needs |
   |---|---|---|
   | Ask MERIDIAN to let go | 3 | |
   | Wipe MERIDIAN | 2 | |
   | Pull MERIDIAN's core (you carry it: `MERIDIAN_CORE`) | 6 | |
   | Close the reactor (a tricky Tech check; it may fail) | 8 | the controls free, the override |
   | Launch the pods | 4 | the controls free, the launch sequence, the reactor open |
   | Take the seeds | 5 | |
   | Let MERIDIAN go, into the signal | 4 | the controls free |

   Closing the reactor saves the crew too. The station and the seeds fit (16 minutes), and
   so do the station and a free MERIDIAN (15), or the pods, the seeds and a free or
   carried MERIDIAN (15 or 16). The station, the seeds and MERIDIAN together don't.
   Then the train, and the Waystation: hand the Stationmaster the seeds (Debt −5,000) or
   keep them.

## Echoes planted

| Echo | States | Kind |
|---|---|---|
| `MERIDIAN` | FREED / WIPED / CARRIED (you smuggle its core out as an item) | Ally / Nemesis |
| `KEPLER_CREW` | SAVED / LOST | Debt |
| `SEED_VAULT` | DELIVERED / KEPT / DESTROYED | Key |

- **`MERIDIAN`:** FREED if you let it go; CARRIED if you pulled its core; otherwise WIPED
  (by you, by its owners, or with the station).
- **`KEPLER_CREW`:** SAVED if the reactor is closed or the pods went; otherwise LOST.
- **`SEED_VAULT`:** DELIVERED or KEPT at the Waystation if you took them; KEPT if they stay
  on a station that lives; DESTROYED if they go with it.

## Echoes listened for

None specific (first Departure). General: none.

## Notes

- Ending choice is the moral weight: the Stationmaster only asked for the seeds.
- A carried MERIDIAN core is a tier-2 Focus that translates into a "talking skull" in
  high-magic realms. It will have opinions.
