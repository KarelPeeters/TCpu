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
        # TODO deduplicate luts and ffs

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
        for signal in lut.inputs:
            users[signal].add(lut)
    for ff in logic.ffs:
        if ff.output in single_def:
            single_def[ff.output] = None
        else:
            single_def[ff.output] = ff
        users[ff.input].add(ff)

    # initialize lattice
    lattice: Dict[Signal, Lattice[bool]] = defaultdict(lambda: Lattice.UNDEF)
    for signal in logic.external_inputs:
        lattice[signal] = Lattice.OVERDEF
    for ff in logic.ffs:
        lattice[ff.output] = Lattice.new_def(ff.init)

    # main loop
    todo = set(logic.ffs + logic.luts)

    while todo:
        component = todo.pop()

        # eval
        if isinstance(component, FF):
            signal = component.output
            output_new = lattice[component.input]
        elif isinstance(component, LUT):
            signal = component.output
            output_new = eval_lut(component, lattice)
        else:
            raise TypeError(f"Unknown user type {type(component)}")

        output_prev = lattice[signal]
        output_new = output_prev.merge(output_new)

        if output_prev.is_overdef:
            assert output_new.is_overdef
        if output_prev.is_def:
            assert output_new.is_def or output_new.is_overdef

        if output_new != output_prev:
            lattice[signal] = output_new
            todo.update(users[signal])

    # apply simplifications
    # TODO: replace constants? or just immediately mutate users?
    # TODO what to do about undef? just pick 0? report warning?
    #   or actually cleverly pick the best value depending on the users?
    luts_updated = set()

    for signal, signal_value in lattice.items():
        if signal_value.is_undef:
            print(f"Warning: {signal} is undef")
        if signal_value.is_def:
            print(f"Found constant {signal} = {signal_value}")
            for user in users[signal]:
                if isinstance(user, LUT):
                    if user in luts_updated:
                        continue
                    luts_updated.add(user)

                    inputs = []
                    for input in user.inputs:
                        input_value = lattice[input]
                        inputs.append(input_value.value if input_value.is_def else None)
                    user.replace_consts(inputs)

    return len(luts_updated) > 0


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
