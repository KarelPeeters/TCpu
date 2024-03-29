from design.tiny import build_counter
from synth.flow.grid_to_sch import grid_to_phys
from synth.flow.logic_opt import optimize_logic
from synth.flow.logic_sim import logic_sim
from synth.flow.logic_to_net import lower_logic_to_net
from synth.flow.net_opt import optimize_net
from synth.flow.net_to_grid import net_to_place
from synth.logic.builder import LogicBuilder
from synth.logic.logic_list import LogicList

COMPONENT_COST = {
    # double both for PCB area used
    "NMos": 0.0062 * 2,
    "Resistor": 0.0005 * 2,
}


def main():
    logic = LogicList()
    build = LogicBuilder(logic)

    # curr = build_counter(build, 4)

    input = build.new_unsigned(3, "input")
    shamt = build.new_unsigned(2, "shamt")
    output = input << shamt
    output_named = build.new_unsigned(len(input), "output")
    output_named %= output

    build.mark_external_input(input, shamt)
    build.mark_external_output(output)

    # new = build.new_bitvec(2, "new")
    # curr = build.new_bitvec(2, "curr")
    # curr %= (curr & new).delay()
    # logic.mark_external_input(*new.signals)
    # logic.mark_external_output(*curr.signals)

    # interface = build_cpu_serv(build)
    # for b in interface.inputs:
    #     logic.mark_external_input(b.signal)
    # for b in interface.outputs:
    #     logic.mark_external_output(b.signal)

    build.finish()

    sim_steps = 32

    print("====================")
    print("Raw:")
    print(logic)
    logic.validate(warn_unused=True, warn_undriven=True, warn_unconnected=True)
    raw_sim = logic_sim(logic, sim_steps)
    raw_sim.print()
    raw_net = lower_logic_to_net(logic)
    raw_net.print_cost(COMPONENT_COST)
    print("\n")

    print("====================")
    print("Logic opt:")
    optimize_logic(logic)
    print(logic)
    logic.validate(warn_unused=True, warn_undriven=True, warn_unconnected=True)
    opt_sim = logic_sim(logic, sim_steps)
    opt_sim.print()
    opt_net = lower_logic_to_net(logic)
    opt_net.print_cost(COMPONENT_COST)
    if raw_sim.outputs() != opt_sim.outputs():
        print("WARNING: Raw and optimized logic sims do not match!")

    print("\n")

    print("====================")
    print("Net opt:")
    optimize_net(opt_net)
    opt_net.print_cost(COMPONENT_COST)

    # sch = net_to_phys(net)
    # sch.to_file("ignored/output.kicad_sch")

    print("====================")
    print("Place:")
    grid = net_to_place(opt_net)
    grid_to_phys(opt_net, grid).to_file(r"../OutputProject/OutputProject.kicad_sch")


if __name__ == '__main__':
    main()
