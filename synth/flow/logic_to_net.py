from typing import Dict, List

from synth.common import OptionalInvPair
from synth.logic.logic_list import LogicList, Signal
from synth.net.basic import gate_table, new_ff
from synth.net.net_list import NetList, Wire


def lower_logic_to_net(logic: LogicList) -> NetList:
    net = NetList()

    # signals
    signal_to_wire = {}
    for signal in logic.signals:
        wire = net.new_wire()
        wire.special_name = signal.special_name
        wire.debug_names = signal.debug_names
        signal_to_wire[signal] = wire

    # actual blocks
    for lut in logic.luts:
        __append_lut(net, signal_to_wire, output=lut.output, inputs=lut.inputs, table=lut.table)
    for ff in logic.ffs:
        __append_ff(net, signal_to_wire, output=ff.output, input=ff.input)

    # connections
    for (a, b) in logic.connections:
        net.connect(signal_to_wire[a], signal_to_wire[b])

    return net


def __append_lut(net: NetList, signal_to_wire, output: Signal, inputs: List[Signal], table: List[bool]):
    wire_inputs = [signal_to_wire[i] for i in inputs]
    gate_output = gate_table(net, table, wire_inputs, None)

    wire_output = signal_to_wire[output]
    net.connect(wire_output, gate_output)


def __append_ff(net: NetList, signal_to_wire: Dict[Signal, Wire], output: Signal, input: Signal):
    wire_input = signal_to_wire[input]
    wire_output = signal_to_wire[output]

    ff_output = new_ff(net, net.clk, OptionalInvPair(wire_input, None))
    net.connect(wire_output, ff_output.val)
