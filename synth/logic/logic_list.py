from abc import abstractmethod, ABC
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Optional, Set, Callable


class Signal:
    unique_id: int
    debug_names: Set[str]
    special_name: Optional[str]

    logic: 'LogicList'

    def __init__(self, logic: 'LogicList', unique_id: int):
        self.unique_id = unique_id
        self.debug_names = set()
        self.special_name = None
        self.logic = logic

    def add_name(self, debug_name: str):
        self.debug_names.add(debug_name)

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

    def __str__(self):
        suffix = ""
        if self.special_name is not None:
            suffix += f", {self.special_name}"
        if len(self.debug_names):
            suffix += f", debug={self.debug_names}"
        return f"Signal({self.unique_id}{suffix})"

    def __repr__(self):
        return str(self)


@dataclass
class SignalUser(ABC):
    @abstractmethod
    def replace(self, f: Callable[[Signal], Signal]):
        raise NotImplementedError()


@dataclass
class LUT(SignalUser):
    output: Signal
    # TODO document endianness of these lists (steal from the pulldown network builder)
    inputs: List[Signal]
    table: List[bool]

    def __post_init__(self):
        assert 2 ** len(self.inputs) == len(self.table)

    def replace(self, f: Callable[[Signal], Signal]):
        self.output = f(self.output)
        self.inputs = [f(s) for s in self.inputs]

    def lines(self):
        for i in range(len(self.table)):
            yield [((i >> j & 1) != 0) for j in range(len(self.inputs))], self.table[i]

    def __hash__(self):
        return id(self)


@dataclass
class FF(SignalUser):
    output: Signal
    input: Signal
    init: bool

    def replace(self, f: Callable[[Signal], Signal]):
        self.input = f(self.input)
        self.output = f(self.output)

    def __hash__(self):
        return id(self)


# TODO: with-based context naming scheme?
class LogicList:
    def __init__(self):
        self.signals: List[Signal] = []
        self.luts: List[LUT] = []
        self.ffs: List[FF] = []
        self.connections: List[(Signal, Signal)] = []

        self.external_inputs: Set[Signal] = set()
        self.external_outputs: Set[Signal] = set()

    def check_signal(self, signal: Signal):
        assert isinstance(signal, Signal), f"Expected Signal, got {type(signal)}"
        assert signal.logic is self

    def new_signal(self, debug_name: Optional[str] = None) -> Signal:
        signal = Signal(unique_id=len(self.signals), logic=self)
        if debug_name is not None:
            signal.debug_names.add(debug_name)
        self.signals.append(signal)
        return signal

    def connect(self, a: Signal, b: Signal):
        self.check_signal(a)
        self.check_signal(b)
        self.connections.append((a, b))

    def mark_external_input(self, *signal: Signal):
        for s in signal:
            self.check_signal(s)
        self.external_inputs.update(signal)

    def mark_external_output(self, *signal: Signal):
        for s in signal:
            self.check_signal(s)
        self.external_outputs.update(signal)

    def push_lut(self, lut: LUT):
        for s in lut.inputs:
            self.check_signal(s)
        self.check_signal(lut.output)

        self.luts.append(lut)

    def new_lut(self, inputs: List[Signal], table: List[bool]) -> Signal:
        output = self.new_signal()
        lut = LUT(output=output, inputs=inputs, table=table)
        self.push_lut(lut)
        return output

    def push_ff(self, ff: FF):
        self.check_signal(ff.input)
        self.check_signal(ff.output)
        self.ffs.append(ff)

    def new_ff(self, input: Signal, init: bool) -> Signal:
        output = self.new_signal()
        ff = FF(init=init, input=input, output=output)
        self.push_ff(ff)
        return output

    def replace_signal(self, old: Signal, new: Signal) -> int:
        if old is new:
            return 0

        count = 0

        def replace(s: Signal) -> Signal:
            nonlocal count
            if s is old:
                count += 1
                return new
            return s

        for i in range(len(self.connections)):
            a, b = self.connections[i]
            self.connections[i] = (replace(a), replace(b))

        for lut in self.luts:
            lut.replace(replace)
        for ff in self.ffs:
            ff.replace(replace)

        self.external_inputs = {replace(s) for s in self.external_inputs}
        self.external_outputs = {replace(s) for s in self.external_outputs}
        new.debug_names.update(old.debug_names)

        self.signals = [s for s in self.signals if s is not old]

        return count

    def validate(self, warn_unused=False, warn_undriven=False, warn_unconnected: bool = False):
        signals_driven = set(self.external_inputs)
        signals_used = set(self.external_outputs)
        signals_all = set(self.signals)

        connected = defaultdict(set)
        for s in self.signals:
            connected[s].add(s)
        for a, b in self.connections:
            connected[a].add(b)
            connected[b].add(a)

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
            assert signal.unique_id not in indices_all, f"Signal {signal} has duplicate ID {signal.unique_id}"
            indices_all.add(signal.unique_id)

        if warn_undriven:
            for signal in signals_used:
                if all(c not in signals_driven for c in connected[signal]):
                    print(f"Warning: signal {signal} is used but never driven")
        if warn_unused:
            for signal in signals_driven:
                if all(c not in signals_used for c in connected[signal]):
                    print(f"Warning: signal {signal} is driven but never used")
        if warn_unconnected:
            for signal in signals_all:
                if signal not in signals_driven and signal not in signals_used and len(connected[signal]) == 1:
                    print(f"Warning: signal {signal} is not connected to anything")

    def _count_str(self) -> str:
        result = ""
        luts_per_input_count = Counter()
        for lut in self.luts:
            luts_per_input_count[len(lut.inputs)] += 1
        result += f"    luts: {len(self.luts)},\n"
        result += f"    ffs: {len(self.ffs)},\n"
        result += f"    cons: {len(self.connections)},\n"
        result += f"    luts_per_input_count: {dict(luts_per_input_count)},"
        return result

    def __str__(self):
        result = "LogicList(\n"

        # signals
        result += "  signals: [\n"
        for signal in self.signals:
            result += f"    {signal}"
            if signal in self.external_inputs:
                result += " in"
            if signal in self.external_outputs:
                result += " out"
            result += "\n"
        result += "  ],\n"

        # "components"
        result += "  connections: [\n"
        for a, b in self.connections:
            result += f"    {a} <-> {b}\n"
        result += "  ],\n"
        result += "  luts: [\n"
        for lut in self.luts:
            table_str = "".join("1" if x else "0" for x in lut.table)
            result += f"    {lut.output} = LUT({lut.inputs}, {table_str})\n"
        result += "  ],\n"
        result += "  ffs: [\n"
        for ff in self.ffs:
            result += f"    {ff.output} = FF({ff.input}, {int(ff.init)})\n"
        result += "  ],\n"

        result += "  counts: [\n"
        result += self._count_str()
        result += "\n  ],\n"

        result += ")"
        return result

    def print_counts(self):
        print("LogicList counts:")
        print(self._count_str())
