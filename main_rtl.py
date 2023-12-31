from synth.logic.logic_list import LogicList


def main():
    logic = LogicList()

    a = logic.new_signal("a")
    b = logic.new_signal("b")
    c = logic.new_signal("c")
    logic.mark_external_input(a)

    r = logic.new_lut(inputs=[a], table=[True, False])
    logic.mark_external_output(r)

    # r = gate_xor(net, a, b, c)
    # print(r)

    logic.validate(warn_unused=True, warn_undriven=True, warn_unconnected=True)

    # for i in range(10):
    #     r = gate_table(net, [0, 1], [a])
    #     print(r)
    #
    # component_cost = {
    #     "NMos": 0.0062,
    #     "Resistor": 0.0005,
    # }
    # net.print(component_cost)
    #
    # net.render()


if __name__ == '__main__':
    main()
