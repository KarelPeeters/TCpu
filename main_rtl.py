from typing import Optional

from synth.flow.synthesys import lower_logic_to_net
from synth.logic.builder import LogicBuilder, Unsigned, Bit
from synth.logic.logic_list import LogicList

COMPONENT_COST = {
    "NMos": 0.0062,
    "Resistor": 0.0005,
}


def build_counter(build: LogicBuilder, bits: int, reset: Optional[Bit]) -> Unsigned:
    if reset is None:
        reset = build.const_bit(False)

    curr = build.new_unsigned(bits)
    curr %= reset.mux(
        build.const_unsigned(bits, 0),
        curr.add_trunc(1)
    )
    return curr


def main():
    logic = LogicList()
    build = LogicBuilder(logic)

    curr = build_counter(build, 32, reset=None)
    logic.mark_external_output(*curr.signals)

    logic.validate(warn_unused=True, warn_undriven=True, warn_unconnected=True)
    print(logic)

    net = lower_logic_to_net(logic)
    net.print(COMPONENT_COST)
    # net.render()


if __name__ == '__main__':
    main()
