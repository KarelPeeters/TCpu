from collections import defaultdict
from typing import Dict, Optional, Union, Set

from synth.flow.lattice import Lattice
from synth.logic.logic_list import LogicList, Signal, LUT, FF


def optimize_logic(logic: LogicList):
    logic.check_finished()

    while True:
        changed = False

        changed |= const_propagation(logic)
        changed |= remove_dead(logic)

        if not changed:
            break


def const_propagation(logic: LogicList) -> bool:
    # def map
    #   no key: no def
    #   None: multiple LUT defs
    single_def: Dict[Signal, Optional[Union[FF, LUT]]] = {}
    users: Dict[Signal, Set[Union[FF, LUT]]] = defaultdict(lambda: set())

    for lut in logic.luts:
        if lut.output in single_def:
            single_def[lut.output] = None
        else:
            single_def[lut.output] = lut
        for c in lut.inputs:
            users[c].add(lut)
    for ff in logic.ffs:
        if ff.output in single_def:
            single_def[ff.output] = None
        else:
            single_def[ff.output] = ff
        users[ff.input].add(ff)

    # initialize lattice
    lattice: Dict[Signal, Lattice[bool]] = defaultdict(lambda: Lattice.UNDEF)
    for c in logic.external_inputs:
        lattice[c] = Lattice.OVERDEF
    for ff in logic.ffs:
        lattice[ff.output] = Lattice.new_def(ff.init)

    # main loop
    todo = set(logic.ffs + logic.luts)

    while todo:
        c = todo.pop()
        print(f"Visiting {c}")

        # eval
        if isinstance(c, FF):
            signal = c.output
            output_new = lattice[c.input]
        elif isinstance(c, LUT):
            signal = c.output
            output_new = eval_lut(c, lattice)
        else:
            raise TypeError(f"Unknown user type {type(c)}")

        output_prev = lattice[signal]
        derp = output_new
        output_new = output_prev.merge(output_new)

        if output_prev.is_overdef:
            assert output_new.is_overdef

        if output_new != output_prev:
            lattice[signal] = output_new
            todo.update(users[signal])

    # apply simplifications
    # TODO: replace constants? or just immediately mutate users?
    # TODO what to do about undef? just pick 0? report warning?
    #   or actually cleverly pick the best value depending on the users?
    for c, x in lattice.items():
        if not x.is_overdef:
            print(f"Simplifying {c} to {x}")

    return False


def eval_lut(lut: LUT, lattice: Dict[Signal, Lattice[bool]]) -> Lattice[bool]:
    result = Lattice.undef()

    for inputs, output in lut.lines():
        if all(lattice[lut.inputs[i]].can_be(value) for i, value in enumerate(inputs)):
            result = result.merge(Lattice.new_def(output))
            if result.is_overdef:
                break

    return result


def remove_dead(_: LogicList) -> bool:
    # TODO
    return False
