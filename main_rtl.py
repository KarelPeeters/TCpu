from synth.flow.logic_opt import optimize_logic
from synth.flow.logic_to_net import lower_logic_to_net
from synth.flow.net_opt import optimize_net
from synth.flow.net_to_place import net_to_place
from synth.logic.builder import LogicBuilder, Unsigned
from synth.logic.logic_list import LogicList

COMPONENT_COST = {
    # double both for PCB area used
    "NMos": 0.0062 * 2,
    "Resistor": 0.0005 * 2,
}


def build_counter(build: LogicBuilder, bits: int) -> Unsigned:
    curr = build.new_unsigned(bits)
    curr %= curr.add_trunc(1).delay()
    return curr


def main():
    logic = LogicList()
    build = LogicBuilder(logic)

    # curr = build_counter(build, 16)

    curr = build.new_bitvec(2)
    curr %= curr & curr.delay()
    logic.mark_external_output(*curr.signals)

    # interface = build_cpu_serv(build)
    # for b in interface.inputs:
    #     logic.mark_external_input(b.signal)
    # for b in interface.outputs:
    #     logic.mark_external_output(b.signal)

    build.finish()

    print("====================")
    print("Raw:")
    print(logic)
    logic.print_counts()
    logic.validate(warn_unused=True, warn_undriven=True, warn_unconnected=True)
    net_unopt = lower_logic_to_net(logic)
    net_unopt.print_cost(COMPONENT_COST)

    print("====================")
    print("Logic opt:")
    optimize_logic(logic)

    return

    logic.validate(warn_unused=True, warn_undriven=True, warn_unconnected=True)
    logic.print_counts()
    net = lower_logic_to_net(logic)
    net.print_cost(COMPONENT_COST)

    print("====================")
    print("Net opt:")
    optimize_net(net)
    net.print_cost(COMPONENT_COST)

    # sch = net_to_phys(net)
    # sch.to_file("ignored/output.kicad_sch")

    net_to_place(net)


if __name__ == '__main__':
    main()
