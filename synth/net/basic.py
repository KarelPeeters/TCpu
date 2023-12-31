from typing import List, Optional

from synth.net.components import NMOS, Resistor
from synth.net.net_list import NetList, Wire


def gate_not(netlist: NetList, input: Wire) -> Wire:
    output = netlist.new_wire()
    netlist.push_component(NMOS(gate=input, up=output, down=netlist.gnd))
    netlist.push_component(Resistor(netlist.vdd, output))
    return output


def input_wire(netlist: NetList, inputs, inverted_inputs, index: int, value: bool) -> Wire:
    if value:
        return inputs[index]
    else:
        if inverted_inputs[index] is None:
            inverted_inputs[index] = gate_not(netlist, inputs[index])
        return inverted_inputs[index]


def gate_table(
        netlist: NetList, table: List[bool], inputs: List[Wire],
        inverted_inputs: Optional[List[Optional[Wire]]] = None
) -> Wire:
    """
    An empty input list is allowed with a table of size 1, which will produce a constant output.
    All inputs must be defined.

    The table has size 2**len(inputs) and works like this:

    inputs[0]  inputs[1]  output
    0          0          table[0]
    0          1          table[1]
    1          0          table[2]
    1          1          table[3]
    """

    assert len(table) == 2 ** len(inputs)

    # TODO allow inputs and inverting to both be none?
    #   or just create a bunch of duplicate inverters and optimize them later?
    if inverted_inputs is None:
        inverted_inputs = [None] * len(inputs)

    # TODO try both inverting and not-inverting the output

    output = netlist.new_wire()

    for bits, value in enumerate(table):
        print(f"{bits:0{len(inputs)}b} -> {value}")
        match value:
            case True:
                # the resistor will pull up, which is also the cheapest option
                pass
            case False:
                # TODO try to combine multiple pulldown branches (karnaugh map)
                curr = output
                for input_index in range(len(inputs)):
                    input_value = (bits >> input_index) & 1 != 0
                    print(f"  {input_index}: {input_value}")
                    gate = input_wire(netlist, inputs, inverted_inputs, input_index, input_value)
                    next = netlist.new_wire()
                    netlist.push_component(NMOS(gate=gate, up=curr, down=next))
                    curr = next
                netlist.connect(curr, netlist.gnd)
            case _:
                raise ValueError(f"invalid value: {value}")

    netlist.push_component(Resistor(netlist.vdd, output))
    return output


def gate_nor(netlist: NetList, *inputs: Wire) -> Wire:
    output = netlist.new_wire()
    for input in inputs:
        netlist.push_component(NMOS(input, output, netlist.gnd))
    netlist.push_component(Resistor(netlist.vdd, output))
    return output


def gate_nand(netlist: NetList, *inputs: Wire) -> Wire:
    curr = netlist.gnd
    for input in inputs:
        next = netlist.new_wire()
        netlist.push_component(NMOS(input, next, curr))
        curr = next
    return curr


def gate_and(netlist: NetList, *inputs: Wire) -> Wire:
    return gate_not(netlist, gate_nand(netlist, *inputs))


def gate_or(netlist: NetList, *inputs: Wire) -> Wire:
    return gate_not(netlist, gate_nor(netlist, *inputs))


def gate_xor(netlist: NetList, *inputs: Wire) -> Wire:
    #
    # inputs_inv = [gate_not(netlist, input) for input in inputs]
    #
    # output = netlist.new_wire()
    #
    # # iterate over truth table
    # for i in range(2 ** len(inputs)):
    #     pass
    raise NotImplementedError("TODO")