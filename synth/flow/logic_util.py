from collections import defaultdict
from dataclasses import dataclass
from typing import Union, Set, Dict

from synth.logic.logic_list import FF, LUT, Signal, LogicList


@dataclass(frozen=True)
class ExternalInput:
    index: int


@dataclass(frozen=True)
class ExternalOutput:
    index: int


User = Union[FF, LUT, ExternalOutput]
Def = Union[FF, LUT, ExternalInput]


def def_inputs(d: Def) -> Set[Signal]:
    if isinstance(d, FF):
        return {d.input}
    elif isinstance(d, LUT):
        return set(d.inputs)
    elif isinstance(d, ExternalInput):
        return set()
    else:
        raise TypeError(f"Unknown def type {type(d)}")


@dataclass
class UseDef:
    users: Dict[Signal, Set[User]]
    defs: Dict[Signal, Set[Def]]

    @staticmethod
    def from_logic(logic: LogicList) -> 'UseDef':
        defs = defaultdict(lambda: set())
        users = defaultdict(lambda: set())

        for i, signal in enumerate(logic.external_inputs):
            defs[signal].add(ExternalInput(i))
        for i, signal in enumerate(logic.external_outputs):
            users[signal].add(ExternalOutput(i))

        for lut in logic.luts:
            for input in lut.inputs:
                users[input].add(lut)
            defs[lut.output].add(lut)
        for ff in logic.ffs:
            users[ff.input].add(ff)
            defs[ff.output].add(ff)

        return UseDef(users=users, defs=defs)
