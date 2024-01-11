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

    def replace_consts(self, consts: List[Optional[bool]]):
        assert len(consts) == len(self.inputs)

        new_table = []
        for line_in, line_out in self.lines():
            if all(c is None or c == v for c, v in zip(consts, line_in)):
                new_table.append(line_out)
        self.table = new_table
        self.inputs = [s for s, c in zip(self.inputs, consts) if c is None]

    def __hash__(self):
        return id(self)

    def operands_tuple(self):
        return *self.inputs, *self.table


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

    def operands_tuple(self):
        return self.input, self.init


# TODO: with-based context naming scheme?
class LogicList:
    def __init__(self):
        self.signals: List[Signal] = []
        self.luts: List[LUT] = []
        self.ffs: List[FF] = []

        # TODO combine these? in/out gets fuzzy once we allow bidirectional, buffers and high impedance
        self.external_inputs: Set[Signal] = set()
        self.external_outputs: Set[Signal] = set()

        self.next_signal_id = 0
        self.builder_count = 0

    def check_signal(self, signal: Signal):
        assert isinstance(signal, Signal), f"Expected Signal, got {type(signal)}"
        assert signal.logic is self

    def new_signal(self, debug_name: Optional[str] = None) -> Signal:
        signal = Signal(unique_id=self.next_signal_id, logic=self)
        self.next_signal_id += 1
        if debug_name is not None:
            signal.debug_names.add(debug_name)
        self.signals.append(signal)
        return signal

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

        for lut in self.luts:
            lut.replace(replace)
        for ff in self.ffs:
            ff.replace(replace)

        self.external_inputs = {replace(s) for s in self.external_inputs}
        self.external_outputs = {replace(s) for s in self.external_outputs}
        new.debug_names.update(old.debug_names)

        self.signals = [s for s in self.signals if s is not old]

        return count

    def check_finished(self):
        assert self.builder_count == 0, "There are still active builders"

    def validate(self, warn_unused=False, warn_undriven=False, warn_unconnected: bool = False):
        self.check_finished()

        # collect signals
        signals_driven = defaultdict(lambda: set())
        for x in self.external_inputs:
            signals_driven[x].add(None)
        signals_used = set(self.external_outputs)
        signals_all = set(self.signals)

        for lut in self.luts:
            signals_driven[lut.output].add(lut)
            signals_used.update(lut.inputs)
        for ff in self.ffs:
            signals_driven[ff.output].add(ff)
            signals_used.add(ff.input)

        # check that signals exist
        for signal in signals_used:
            assert signal in signals_all, f"Used signal {signal} does not exist"
        for signal in signals_driven:
            assert signal in signals_all, f"Driven signal {signal} does not exist"
        for signal in self.external_inputs:
            assert signal in signals_all, f"External input {signal} does not exist"
        for signal in self.external_outputs:
            assert signal in signals_all, f"External output {signal} does not exist"

        # check that signal ids are unique
        indices_all = set()
        for signal in signals_all:
            assert signal.unique_id not in indices_all, f"Signal {signal} has duplicate ID {signal.unique_id}"
            indices_all.add(signal.unique_id)

        # check that signals are connected
        if warn_undriven:
            for signal in signals_used:
                if signal not in signals_driven:
                    print(f"Warning: signal {signal} is used but never driven")
        if warn_unused:
            for signal in signals_driven:
                if signal not in signals_used:
                    print(f"Warning: signal {signal} is driven but never used")
        if warn_unconnected:
            for signal in signals_all:
                if signal not in signals_driven and signal not in signals_used:
                    print(f"Warning: signal {signal} is not connected to anything")

        # check at most one driver per signal
        for signal, drivers in signals_driven.items():
            assert len(drivers) <= 1, f"Signal {signal} has multiple drivers: {drivers}"

        # check for LUT loops (FF "loops" are fine)
        loop_free_luts = set()
        looped_luts = set()
        curr_loop = []

        def is_looped(lut: LUT) -> Optional[List[LUT]]:
            if lut in loop_free_luts:
                return None
            if lut.output in curr_loop:
                found_loop = list(reversed(curr_loop))
                curr_loop.clear()
                return found_loop

            curr_loop.append(lut.output)
            for lut_input in lut.inputs:
                for driver in signals_driven[lut_input]:
                    if isinstance(driver, LUT):
                        found_loop = is_looped(driver)
                        if found_loop is not None:
                            return found_loop

            curr_loop.pop()
            loop_free_luts.add(lut)
            return None

        for lut in self.luts:
            if lut in looped_luts or lut in loop_free_luts:
                continue

            loop = is_looped(lut)
            if loop is not None:
                print(f"Error: LUT loop detected: {is_looped(lut)}")
                looped_luts.update(loop)

        if len(looped_luts) > 0:
            raise RuntimeError("LUT loop detected")

    def _count_str(self) -> str:
        result = ""
        luts_per_input_count = Counter()
        for lut in self.luts:
            luts_per_input_count[len(lut.inputs)] += 1
        result += f"    luts: {len(self.luts)},\n"
        result += f"    ffs: {len(self.ffs)},\n"
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

        # components
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
