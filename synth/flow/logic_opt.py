from synth.flow.opt_util import canonicalize
from synth.logic.logic_list import LogicList


def optimize_logic(logic: LogicList):
    while True:
        changed = False

        changed |= combine_connections(logic)
        changed |= const_propagation(logic)
        changed |= remove_dead(logic)

        if not changed:
            break


def combine_connections(logic: LogicList) -> bool:
    replacements = canonicalize(logic.connections, lambda a, b: a.unique_id < b.unique_id)

    count = 0
    for a, b in replacements.items():
        count += logic.replace_signal(a, b)

    logic.connections.clear()

    print(f"combined {count} wires")
    return count > 0


def const_propagation(_: LogicList) -> bool:
    # TODO
    return False


def remove_dead(_: LogicList) -> bool:
    # TODO
    return False
