from collections import defaultdict
from typing import Dict, Set

from synth.flow.lattice import Lattice
from synth.flow.logic_util import ExternalOutput, def_inputs, UseDef
from synth.logic.logic_list import LogicList, Signal, LUT, FF


def optimize_logic(logic: LogicList):
    logic.check_finished()

    while True:
        changed = False

        changed |= const_propagation(logic)
        changed |= remove_dead(logic)
        changed |= deduplicate(logic)
        changed |= simplify(logic)

        # TODO remove buffers (LUTS with table [01])
        # TODO fuse luts (including through FFs, we can retime later)
        # TODO more complex expression simplification, eg. "a & a" -> "a"
        #   consider using a SAT solver for this?

        if not changed:
            break


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
    todo: Set[Signal] = set(logic.external_inputs | logic.external_outputs)

    while todo:
        signal = todo.pop()
        if signal in live:
            continue
        live.add(signal)

        for d in use_def.defs[signal]:
            todo.update(def_inputs(d))

    # delete non-live
    orig_count = len(logic.luts) + len(logic.ffs) + len(logic.signals)

    logic.ffs = [ff for ff in logic.ffs if ff.output in live]
    logic.luts = [lut for lut in logic.luts if lut.output in live]
    logic.signals = [signal for signal in logic.signals if signal in live]

    new_count = len(logic.luts) + len(logic.ffs) + len(logic.signals)
    return new_count < orig_count


def deduplicate(logic: LogicList) -> bool:
    replaced = 0

    ffs = {}
    ffs_to_delete = set()

    for ff in logic.ffs:
        # find identical
        key = ff.operands_tuple()
        if key not in ffs:
            ffs[key] = ff
            continue
        # replace
        replaced += logic.replace_signal(ff.output, ffs[key].output)
        ffs_to_delete.add(ff)

    luts = {}
    luts_to_delete = set()
    for lut in logic.luts:
        # find identical
        key = lut.operands_tuple()
        if key not in luts:
            luts[key] = lut
            continue
        # replace
        replaced += logic.replace_signal(lut.output, luts[key].output)
        luts_to_delete.add(lut)

    logic.ffs = [ff for ff in logic.ffs if ff not in ffs_to_delete]
    logic.luts = [lut for lut in logic.luts if lut not in luts_to_delete]

    return replaced > 0


def simplify(logic: LogicList) -> bool:
    changed = False
    luts_to_remove = set()

    for lut in logic.luts:
        if lut.table == [False, True]:
            logic.replace_signal(lut.output, lut.inputs[0])
            luts_to_remove.add(lut)
            changed = True

    logic.luts = [lut for lut in logic.luts if lut not in luts_to_remove]

    return changed
