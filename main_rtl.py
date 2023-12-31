from synth.logic.builder import LogicBuilder, Unsigned
from synth.logic.logic_list import LogicList

COMPONENT_COST = {
    "NMos": 0.0062,
    "Resistor": 0.0005,
}


def counter(build: LogicBuilder, bits: int) -> Unsigned:
    curr = build.new_unsigned(bits)
    curr %= curr.delay(1).add_trunc(1)
    return curr


def main():
    logic = LogicList()
    build = LogicBuilder(logic)

    curr = counter(build, 4)
    logic.mark_external_output(*curr.signals)

    logic.validate(warn_unused=True, warn_undriven=True, warn_unconnected=True)
    print(logic)

    # net.print(component_cost)
    # net.render()


if __name__ == '__main__':
    main()
