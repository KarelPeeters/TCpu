from typing import Dict

from synth.logic.logic_list import LogicList, Signal


def optimize_logic(logic: LogicList):
    while True:
        changed = False

        changed |= combine_connections(logic)
        changed |= const_propagation(logic)
        changed |= remove_dead(logic)

        if not changed:
            break


def combine_connections(logic: LogicList) -> bool:
    # map each signal to the wire with the lowest unique_index
    # to get the true canonical wire, recursively follow the canonical "next" dict
    canonical_next: Dict[Signal, Signal] = {}

    for a, b in logic.connections:
        # follow until currently lowest known
        if a in canonical_next:
            a = canonical_next[a]
        if b in canonical_next:
            b = canonical_next[b]
        assert a not in canonical_next and b not in canonical_next

        # decide the new lowest known
        if a.unique_id < b.unique_id:
            canonical_next[b] = a
        else:
            canonical_next[a] = b

    logic.connections.clear()
    count = 0

    for a in canonical_next:
        # find final canonical
        b = canonical_next[a]
        while b in canonical_next:
            b = canonical_next[b]

        count += logic.replace_signal(a, b)

    print(f"combined {count} wires")
    return count > 0


def const_propagation(_: LogicList) -> bool:
    # TODO
    return False


def remove_dead(_: LogicList) -> bool:
    # TODO
    return False
