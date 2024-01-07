from synth.flow.opt_util import canonicalize
from synth.net.components import Bridge
from synth.net.net_list import NetList


def optimize_net(net: NetList):
    while True:
        changed = False

        changed |= combine_connections(net)
        changed |= const_propagation(net)
        changed |= remove_dead(net)

        if not changed:
            break


def combine_connections(net: NetList) -> bool:
    # take out all bridges
    connections = [(c.a, c.b) for c in net.components if isinstance(c, Bridge)]
    net.components = [c for c in net.components if not isinstance(c, Bridge)]

    replacements = canonicalize(connections, lambda a, b: a.unique_id < b.unique_id)
    count = 0

    for a, b in replacements.items():
        count += net.replace_wire(a, b)

    print(f"combined {count} wires")
    return count > 0


def const_propagation(_: NetList) -> bool:
    # TODO
    return False


def remove_dead(_: NetList) -> bool:
    # TODO
    return False
