from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce
from typing import List, Callable, Self, Union, overload, Optional

from synth.logic.logic_list import LogicList, Signal


class LogicBuilder:
    def __init__(self, logic: LogicList):
        self.logic = logic

    # construction
    def new_const(self, value: bool) -> 'Bit':
        signal = self.logic.new_lut([], [value])
        return Bit(self, signal)

    def new_bit(self, debug_name: Optional[str] = None) -> 'Bit':
        return Bit(self, self.logic.new_signal(debug_name))

    def new_bitvec(self, n: int, debug_name: Optional[str] = None) -> 'BitVec':
        signals = [
            self.logic.new_signal(f"{debug_name}[{i}]" if debug_name is not None else None)
            for i in range(n)
        ]
        return BitVec(self, signals)

    def new_unsigned(self, n: int, debug_name: Optional[str] = None) -> 'Unsigned':
        return Unsigned(self, self.new_bitvec(n, debug_name))

    # basic gates
    def gate_not(self, signal: Signal) -> Signal:
        return self.logic.new_lut([signal], [True, False])

    def gate_and(self, signals: List[Signal]) -> Signal:
        table = [False] * (2 ** len(signals) - 1) + [True]
        return self.logic.new_lut(signals, table)

    def gate_or(self, signals: List[Signal]) -> Signal:
        table = [True] * (2 ** len(signals) - 1) + [False]
        return self.logic.new_lut(signals, table)

    def gate_xor(self, signals: List[Signal]) -> Signal:
        table = [False, True] * (2 ** len(signals) // 2)
        return self.logic.new_lut(signals, table)


@dataclass
class BuilderValue(ABC):
    """
    Wrapper around signals that allow for automatically building utility functions and operator overloading.
    """
    builder: 'LogicBuilder'

    @abstractmethod
    def map_signals(self, f: Callable[[Signal], Signal]) -> Self:
        raise NotImplementedError()

    def delay(self, n: int = 1) -> Self:
        """
        Delay a signal by n cycles by inserting n flip-flops.
        """
        # TODO expose the initial value? how, it's not just a bool but another monad instance
        return self.map_signals(lambda s: reduce(lambda x, _: self.builder.logic.new_ff(x, init=False), range(n), s))


@dataclass
class Bit(BuilderValue):
    signal: Signal

    def __repr__(self):
        return f"Bit({self.signal})"

    def map_signals(self, f: Callable[[Signal], Signal]) -> 'Bit':
        return Bit(self.builder, f(self.signal))

    def __post_init__(self):
        assert isinstance(self.signal, Signal), f"Expected Signal, got {type(self.signal)}"

    def __invert__(self) -> 'Bit':
        return Bit(self.builder, self.builder.gate_not(self.signal))

    def __and__(self, other: 'Bit') -> 'Bit':
        return Bit(self.builder, self.builder.gate_and([self.signal, other.signal]))

    def __or__(self, other: 'Bit') -> 'Bit':
        return Bit(self.builder, self.builder.gate_or([self.signal, other.signal]))

    def __xor__(self, other: 'Bit') -> 'Bit':
        return Bit(self.builder, self.builder.gate_xor([self.signal, other.signal]))


@dataclass
class BitVec(BuilderValue):
    signals: List[Signal]

    @staticmethod
    def from_bits(builder: LogicBuilder, bits: List[Bit]) -> 'BitVec':
        # we need to take a builder arg to handle the empty edge case
        assert isinstance(bits, list)
        for b in bits:
            assert b.builder is builder
            assert isinstance(b, Bit), f"Expected Bit, got {type(b)}"

        return BitVec(builder, [b.signal for b in bits])

    def __repr__(self):
        return f"BitVec({self.signals})"

    def __post_init__(self):
        assert isinstance(self.signals, list), f"Expected list, got {type(self.signals)}"
        for s in self.signals:
            assert isinstance(s, Signal), f"Expected Signal, got {type(s)}"

    @staticmethod
    def empty(builder: LogicBuilder):
        return BitVec(builder, [])

    @staticmethod
    def single(bit: Bit):
        return BitVec(bit.builder, [bit.signal])

    @staticmethod
    def broadcast(bit: Bit, n: int):
        return BitVec(bit.builder, [bit.signal] * n)

    def map_signals(self, f: Callable[[Signal], Signal]) -> Self:
        return BitVec(self.builder, [f(s) for s in self.signals])

    def __len__(self):
        return len(self.signals)

    @overload
    def __getitem__(self, item: int) -> Bit:
        ...

    @overload
    def __getitem__(self, item: slice) -> Self:
        ...

    def __getitem__(self, item: Union[int, slice]) -> Union[Bit, Self]:
        if isinstance(item, int):
            return Bit(self.builder, self.signals[item])
        elif isinstance(item, slice):
            return BitVec(self.builder, self.signals[item])
        else:
            raise TypeError(f"invalid type: {type(item)}")

    def __invert__(self) -> 'BitVec':
        return BitVec(self.builder, [self.builder.gate_not(s) for s in self.signals])

    def __and__(self, other: 'BitVec') -> 'BitVec':
        assert self.builder is other.builder
        return BitVec(self.builder, [self.builder.gate_and([a, b]) for a, b in zip(self.signals, other.signals)])

    def __or__(self, other: 'BitVec') -> 'BitVec':
        assert self.builder is other.builder
        return BitVec(self.builder, [self.builder.gate_or([a, b]) for a, b in zip(self.signals, other.signals)])

    def __xor__(self, other: 'BitVec') -> 'BitVec':
        assert self.builder is other.builder
        return BitVec(self.builder, [self.builder.gate_xor([a, b]) for a, b in zip(self.signals, other.signals)])

    def as_unsigned(self) -> Self:
        return Unsigned(self.builder, self)


@dataclass
class Unsigned(BuilderValue):
    vec: BitVec

    def __post_init__(self):
        assert isinstance(self.vec, BitVec), f"Expected BitVec, got {type(self.vec)}"

    def __repr__(self):
        return f"Unsigned({self.vec.signals})"

    def as_vec(self) -> BitVec:
        return self.vec

    def map_signals(self, f: Callable[[Signal], Signal]) -> Self:
        return Unsigned(self.builder, self.vec.map_signals(f))

    @property
    def signals(self) -> List[Signal]:
        return self.vec.signals

    def __len__(self):
        return len(self.vec)

    def __invert__(self) -> Self:
        return Unsigned(self.builder, self.vec.__invert__())

    def __and__(self, other: Self) -> Self:
        assert self.builder is other.builder
        return Unsigned(self.builder, self.vec.__and__(other.vec))

    def __or__(self, other: Self) -> Self:
        assert self.builder is other.builder
        return Unsigned(self.builder, self.vec.__or__(other.vec))

    def __xor__(self, other: Self) -> Self:
        assert self.builder is other.builder
        return Unsigned(self.builder, self.vec.__xor__(other.vec))

    def add_full(self, other: Self, cin: Optional[Signal]) -> Self:
        assert self.builder is other.builder
        assert len(self) == len(other)

        carry = cin if cin is not None else self.builder.new_const(False)
        result = []

        for i in range(len(self)):
            x = self.vec[i]
            y = other.vec[i]

            # full adder
            result.append(x ^ y ^ carry)
            carry = (x & y) | (x & carry) | (y & carry)

        result.append(carry)
        return Unsigned(self.builder, BitVec.from_bits(self.builder, result))

    def __add__(self, other: Self) -> Self:
        return self.add_full(other, cin=None)