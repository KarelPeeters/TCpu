from synth.logic.builder import LogicBuilder
from synth.logic.logic_list import LogicList

COMPONENT_COST = {
    "NMos": 0.0062,
    "Resistor": 0.0005,
}


def main():
    logic = LogicList()
    build = LogicBuilder(logic)

    a = build.new_unsigned(4, "a")
    b = build.new_unsigned(4, "b")
    logic.mark_external_input(*a.signals, *b.signals)

    # r_and = a & b
    # r_or = a | b
    # logic.mark_external_output(*r_and.signals, *r_or.signals)

    sum = a + b
    print(sum.signals)
    logic.mark_external_output(*sum.signals)

    logic.validate(warn_unused=True, warn_undriven=True, warn_unconnected=True)
    print(logic)

    # net.print(component_cost)
    # net.render()


if __name__ == '__main__':
    main()
