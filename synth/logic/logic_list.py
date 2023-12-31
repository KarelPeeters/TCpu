from dataclasses import dataclass
from typing import List, Optional, Set


@dataclass
class Signal:
    id: int
    debug_name: Optional[str]
    full_name: Optional[str]

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

    def __str__(self):
        if self.full_name is not None:
            return f"\"{self.full_name}\""
        if self.debug_name is not None:
            return f"Signal({self.id}, \"{self.debug_name}\")"
        return f"Signal({self.id})"

    def __repr__(self):
        return str(self)


@dataclass
class LUT:
    output: Signal
    inputs: List[Signal]
    table: List[bool]

    def __post_init__(self):
        assert 2 ** len(self.inputs) == len(self.table)


@dataclass
class FF:
    init: bool
    input: Signal
    output: Signal


# TODO: with-based context naming scheme?
class LogicList:
    def __init__(self):
        self.signals: List[Signal] = []
        self.luts: List[LUT] = []
        self.ffs: List[FF] = []

        self.external_inputs: Set[Signal] = set()
        self.external_outputs: Set[Signal] = set()

    def new_signal(self, debug_name: Optional[str] = None) -> Signal:
        signal = Signal(id=len(self.signals), debug_name=debug_name, full_name=None)
        self.signals.append(signal)
        return signal

    def mark_external_input(self, *signal: Signal):
        self.external_inputs.update(signal)

    def mark_external_output(self, *signal):
        self.external_outputs.update(signal)

    def push_lut(self, lut: LUT):
        self.luts.append(lut)

    def new_lut(self, inputs: List[Signal], table: List[bool]) -> Signal:
        output = self.new_signal()
        lut = LUT(output=output, inputs=inputs, table=table)
        self.push_lut(lut)
        return output

    def push_ff(self, ff: FF):
        self.ffs.append(ff)

    def new_ff(self, input: Signal, init: bool) -> Signal:
        output = self.new_signal()
        ff = FF(init=init, input=input, output=output)
        self.push_ff(ff)
        return output

    def validate(self, warn_unused=False, warn_undriven=False, warn_unconnected: bool = False):
        signals_driven = set(self.external_inputs)
        signals_used = set(self.external_outputs)
        signals_all = set(self.signals)

        for lut in self.luts:
            signals_driven.add(lut.output)
            signals_used.update(lut.inputs)
        for ff in self.ffs:
            signals_driven.add(ff.output)
            signals_used.add(ff.input)

        for signal in signals_used:
            assert signal in signals_all, f"Used signal {signal} does not exist"
        for signal in signals_driven:
            assert signal in signals_all, f"Driven signal {signal} does not exist"

        indices_all = set()
        for signal in signals_all:
            assert signal.id not in indices_all, f"Signal {signal} has duplicate ID {signal.id}"
            indices_all.add(signal.id)

        if warn_undriven:
            for signal in signals_used:
                if signal not in signals_driven:
                    print(f"Warning: signal {signal} is used but never driven")
        if warn_unused:
            for signal in signals_driven:
                if signal not in signals_used:
                    print(f"Warning: signal {signal} is driven but never signals")
        if warn_unconnected:
            for signal in signals_all:
                if signal not in signals_driven and signal not in signals_used:
                    print(f"Warning: signal {signal} is not connected to anything")

    def __str__(self):
        result = "LogicList(\n"
        result += "  signals: [\n"
        for signal in self.signals:
            result += f"    {signal}"
            if signal in self.external_inputs:
                result += " in"
            if signal in self.external_outputs:
                result += " out"
            result += "\n"
        result += "  ],\n"
        result += "  luts: [\n"
        for lut in self.luts:
            result += f"    {lut.output} = LUT({lut.inputs}, {lut.table})\n"
        result += "  ],\n"
        result += "  ffs: [\n"
        for ff in self.ffs:
            result += f"    {ff.output} = FF({ff.input}, {ff.init})\n"
        result += "  ],\n"
        result += ")"
        return result
