"""The parsed form of a Quest Script Departure.

The parser (parse.py) produces these; the code generator (E1.3) consumes them.
Every node keeps the source line it came from, for error messages.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union


# ------------------------------------------------------------ conditions

@dataclass
class Flag:
    name: str
    line: int


@dataclass
class Compare:
    """`subject op value`: subject is ('var', name), ('stat', i), ('skill', i) or ('level',)."""
    subject: tuple
    op: str               # = != < <= > >=
    value: int
    line: int


@dataclass
class Has:
    item: str
    line: int


@dataclass
class EchoIs:
    echo: str
    op: str               # = or !=
    state: str
    line: int


@dataclass
class IsRace:
    race: str
    line: int


@dataclass
class IsClass:
    cls: str
    line: int


@dataclass
class Visited:
    scene: str
    line: int


@dataclass
class Not:
    operand: "Cond"
    line: int


@dataclass
class And:
    left: "Cond"
    right: "Cond"
    line: int


@dataclass
class Or:
    left: "Cond"
    right: "Cond"
    line: int


Cond = Union[Flag, Compare, Has, EchoIs, IsRace, IsClass, Visited, Not, And, Or]


# ------------------------------------------------------------ statements

@dataclass
class Insert:
    """A value inserted into text: name, race, class, debt, level, or ('var', name)."""
    what: str
    var: Optional[str] = None


@dataclass
class Text:
    """One paragraph: plain ASCII strings and Inserts, in order."""
    parts: list
    line: int


@dataclass
class Command:
    """A `~` command. `args` depends on `name`:

    set/clear: [flag]            let: [var, value]       add/sub: [var, amount]
    echo: [ECHO, STATE]          give/take: [ITEM]       xp: [amount]
    debt: [mode, amount]         picture: [name]         pause: []
    end: ['complete' | 'failed']
    """
    name: str
    args: list
    line: int


@dataclass
class Goto:
    scene: str
    line: int


@dataclass
class If:
    branches: list        # [(Cond or None for else, [Stmt])]
    line: int


@dataclass
class Check:
    rating: tuple         # ('stat', i) or ('skill', i)
    tn: int
    outcomes: dict        # 'crit' | 'success' | 'cost' | 'fail' -> [Stmt]
    line: int


@dataclass
class Fight:
    """`fight MAP [ambush|sneak]` with won:/lost:/fled: branches (docs/combat.md)."""
    map: str
    surprise: int         # 0 none, 1 ambush (foes first), 2 sneak (travelers first)
    outcomes: dict        # 'won' | 'lost' | 'fled' -> [Stmt]
    line: int


Stmt = Union[Text, Command, Goto, If, Check, Fight]


@dataclass
class Map:
    """A battle map: rows of squares, and the foe each letter stands for."""
    name: str
    rows: List[str]
    foes: dict            # letter -> foe name in the bestiary
    line: int


@dataclass
class Choice:
    sticky: bool          # + stays on the menu; * disappears once picked
    cond: Optional[Cond]
    label: str
    target: Optional[str]  # `-> scene` on the choice line itself
    body: List[Stmt]
    line: int


@dataclass
class Scene:
    name: str
    body: List[Stmt]
    choices: List[Choice]
    line: int


@dataclass
class Chapter:
    title: str            # "" for scenes written before any chapter heading
    scenes: List[Scene]
    line: int


@dataclass
class Departure:
    path: str
    title: str = ""
    id: int = 0
    kind: str = "official"
    season: int = 0
    tl: int = 0
    ml: int = 0
    level_min: int = 1
    level_max: int = 1
    start: str = ""
    linear: bool = False        # deliberately one road: don't warn about it
    flags: dict = field(default_factory=dict)   # name -> line
    vars: dict = field(default_factory=dict)    # name -> (initial value, line)
    chapters: List[Chapter] = field(default_factory=list)
    pictures: List[str] = field(default_factory=list)
    maps: dict = field(default_factory=dict)    # name -> Map

    def scenes(self):
        for ch in self.chapters:
            yield from ch.scenes
