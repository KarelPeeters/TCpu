from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Union, Set

from synth.flow.lattice import Lattice
from synth.logic.logic_list import LogicList, Signal, LUT, FF


def optimize_logic(logic: LogicList):
    logic.check_finished()

    while True:
        changed = False

        changed |= const_propagation(logic)
        print("After const prop:")
        print(logic)
        changed |= remove_dead(logic)
        print("After dead removal:")
        print(logic)
        changed |= deduplicate(logic)

        if not changed:
            break


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


def const_propagation(logic: LogicList) -> bool:
    use_def = UseDef.from_logic(logic)

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
        elif isinstance(component, ExternalOutput):
            continue
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
            todo.update(use_def.users[signal])

    # apply simplifications
    # TODO: replace constants? or just immediately mutate users?
    # TODO what to do about undef? just pick 0? report warning?
    #   or actually cleverly pick the best value depending on the users?
    luts_updated = set()
    ffs_deleted = set()

    for signal, signal_value in lattice.items():
        if signal_value.is_undef:
            print(f"Warning: {signal} is undef")
        if signal_value.is_def:
            print(f"Replacing {signal} with {signal_value}")
            for user in use_def.users[signal]:
                if isinstance(user, LUT):
                    if user in luts_updated:
                        continue
                    luts_updated.add(user)

                    inputs = []
                    for input in user.inputs:
                        input_value = lattice[input]
                        inputs.append(input_value.value if input_value.is_def else None)
                    user.replace_consts(inputs)
                if isinstance(user, FF):
                    if user in ffs_deleted:
                        continue
                    ffs_deleted.add(user)

                    const_lut = LUT(inputs=[], output=user.output, table=[signal_value.value])
                    logic.push_lut(const_lut)

                    dummy_signal = logic.new_signal("dummy")
                    user.output = dummy_signal

    return len(luts_updated) > 0 or len(ffs_deleted) > 0


def eval_lut(lut: LUT, lattice: Dict[Signal, Lattice[bool]]) -> Lattice[bool]:
    result = Lattice.undef()

    for inputs, output in lut.lines():
        if all(lattice[lut.inputs[i]].can_be(value) for i, value in enumerate(inputs)):
            result = result.merge(Lattice.new_def(output))
            if result.is_overdef:
                break

    return result


def remove_dead(logic: LogicList) -> bool:
    use_def = UseDef.from_logic(logic)

    # collect live
    live: Set[Signal] = set()
    todo: Set[Signal] = set(logic.external_outputs)

    while todo:
        signal = todo.pop()
        if signal in live:
            continue
        live.add(signal)

        for d in use_def.defs[signal]:
            todo.update(def_inputs(d))

    # delete non-live
    print(f"Live signals: {live}")

    orig_count = len(logic.luts) + len(logic.ffs)

    logic.ffs = [ff for ff in logic.ffs if ff.output in live]
    logic.luts = [lut for lut in logic.luts if lut.output in live]

    new_count = len(logic.luts) + len(logic.ffs)
    return new_count < orig_count


def deduplicate(_: LogicList) -> bool:
    # TODO
    return False
