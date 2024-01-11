from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce
from typing import List, Callable, Self, Union, overload, Optional, TypeVar

from synth.logic.logic_list import LogicList, Signal


class LogicBuilder:
    def __init__(self, logic: LogicList):
        self.logic = logic
        self.connections_to_make: List[(Signal, Signal)] = []

        logic.builder_count += 1

    def finish(self):
        for a, b in self.connections_to_make:
            self.logic.replace_signal(a, b)
        self.connections_to_make.clear()

        self.logic.builder_count -= 1
        self.logic = None

    # construction
    def const_bit(self, value: bool) -> 'Bit':
        signal = self.logic.new_lut([], [value])
        return Bit(self, signal)

    def const_unsigned(self, bits: int, value: int) -> 'Unsigned':
        assert 0 <= value < 2 ** bits
        bits = [self.const_bit(value >> i != 0) for i in range(bits)]
        return Unsigned(self, BitVec.from_bits(self, bits))

    def new_bit(self, name: Optional[str]) -> 'Bit':
        return Bit(self, self.logic.new_signal(name))

    def new_bitvec(self, n: int, name: Optional[str] = None) -> 'BitVec':
        signals = [
            self.logic.new_signal(f"{name}[{i}]" if name is not None else None)
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
        table = [i.bit_count() % 2 == 1 for i in range(2 ** len(signals))]
        return self.logic.new_lut(signals, table)


@dataclass
class BuilderValue(ABC):
    """
    Monad containing signals, allowing for easily implementing utility functions and operator overloading.
    """
    builder: 'LogicBuilder'

    @abstractmethod
    def map(self, other: Self, f: Callable[[Signal, Signal], Signal]) -> Self:
        raise NotImplementedError()

    def map_single(self, f: Callable[[Signal], Signal]) -> Self:
        def wrap(a, b):
            assert b is a
            return f(a)

        return self.map(self, wrap)

    @abstractmethod
    def type_name(self) -> str:
        raise NotImplementedError()

    def delay(self, n: int = 1) -> Self:
        """
        Delay a signal by n cycles by inserting n flip-flops.
        """

        # TODO expose the initial value?
        #   how? it's not just a bool but a constant monad instance containing bool instead of Signal

        def f(a):
            return reduce(
                lambda x, _: self.builder.logic.new_ff(x, init=False),
                range(n),
                a
            )

        return self.map_single(f)

    def __imod__(self, other):
        """
        We use the imod operator to connect two (sets of) signals.
        The following at the same:

        connect(a, b)   # hypothetical
        a %= b
        b %= a
        """

        self_ty = self.type_name()
        other_ty = other.type_name()
        assert self_ty == other_ty, f"Connection type mismatch: {self_ty} vs {other_ty}"

        def f(a, b):
            self.builder.connections_to_make.append((a, b))
            # we have to return a dummy signal
            return a

        _ = self.map(other, f)
        # we want the lhs to just stay the same
        return self


V = TypeVar('V', bound=BuilderValue)


@dataclass
class Bit(BuilderValue):
    signal: Signal

    def __post_init__(self):
        assert isinstance(self.signal, Signal), f"Expected Signal, got {type(self.signal)}"

    def __repr__(self):
        return f"Bit({self.signal})"

    def map(self, other: Optional[Self], f: Callable[[Signal, Optional[Signal]], Signal]) -> Self:
        assert isinstance(other, Bit), f"Type mismatch: expected Bit, got {type(other)}"
        return Bit(self.builder, f(self.signal, other.signal))

    def type_name(self) -> str:
        return "bit"

    def __invert__(self) -> Self:
        return Bit(self.builder, self.builder.gate_not(self.signal))

    def __and__(self, other: Self) -> Self:
        return Bit(self.builder, self.builder.gate_and([self.signal, other.signal]))

    def __or__(self, other: Self) -> Self:
        return Bit(self.builder, self.builder.gate_or([self.signal, other.signal]))

    def __xor__(self, other: Self) -> Self:
        return Bit(self.builder, self.builder.gate_xor([self.signal, other.signal]))

    def eq(self, other: Self) -> Self:
        return ~self.neq(other)

    def neq(self, other: Self) -> Self:
        return Bit(self.builder, self.builder.gate_xor([self.signal, other.signal]))

    def mux(self, value_0: V, value_1: V) -> Self:
        inv = ~self

        def f(signal_0, signal_1):
            return self.builder.gate_or([
                self.builder.gate_and([inv.signal, signal_0]),
                self.builder.gate_and([self.signal, signal_1]),
            ])

        return value_0.map(value_1, f)

    @staticmethod
    def full_add(a: 'Bit', b: 'Bit', c: 'Bit') -> ('Bit', 'Bit'):
        """Full adder, returning (carry, sum)"""
        c_out = (a & b) | (a & c) | (b & c)
        sum = a ^ b ^ c
        return c_out, sum


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

    def __post_init__(self):
        assert isinstance(self.signals, list), f"Expected list, got {type(self.signals)}"
        for s in self.signals:
            assert isinstance(s, Signal), f"Expected Signal, got {type(s)}"

    def __repr__(self):
        return f"BitVec({self.signals})"

    def map(self, other: Optional[Self], f: Callable[[Signal, Optional[Signal]], Signal]) -> Self:
        assert isinstance(other, BitVec), f"Type mismatch: expected Optional[BitVec], got {type(other)}"
        assert len(self) == len(other), f"Length mismatch: {len(self)} vs {len(other)}"
        return BitVec(self.builder, [f(a, b) for a, b in zip(self.signals, other.signals)])

    def type_name(self) -> str:
        return f"bitvec[{len(self)}]"

    @staticmethod
    def empty(builder: LogicBuilder):
        return BitVec(builder, [])

    @staticmethod
    def single(bit: Bit):
        return BitVec(bit.builder, [bit.signal])

    @staticmethod
    def broadcast(bit: Bit, n: int):
        return BitVec(bit.builder, [bit.signal] * n)

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

    def any(self) -> Bit:
        return Bit(self.builder, self.builder.gate_or(self.signals))

    def all(self) -> Bit:
        return Bit(self.builder, self.builder.gate_and(self.signals))


@dataclass
class Unsigned(BuilderValue):
    vec: BitVec

    def __post_init__(self):
        assert isinstance(self.vec, BitVec), f"Expected BitVec, got {type(self.vec)}"

    def __repr__(self):
        return f"Unsigned({self.vec.signals})"

    def map(self, other: Optional[Self], f: Callable[[Signal, Optional[Signal]], Signal]) -> Self:
        assert isinstance(other, Unsigned), f"Type mismatch: expected Unsigned, got {type(other)}"
        return Unsigned(self.builder, self.vec.map(other.vec, f))

    def type_name(self) -> str:
        return f"unsigned[{len(self)}]"

    def as_vec(self) -> BitVec:
        return self.vec

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

    def add_full(self, other: Union[Self, int], cin: Optional[Bit]) -> Self:
        if isinstance(other, int):
            other = self.builder.const_unsigned(len(self), other)

        assert isinstance(other, Unsigned)
        assert cin is None or isinstance(cin, Bit)
        assert self.builder is other.builder
        assert len(self) == len(other)

        carry = cin if cin is not None else self.builder.const_bit(False)
        result = []

        for i in range(len(self)):
            carry, result_i = Bit.full_add(self.vec[i], other.vec[i], carry)
            result.append(result_i)

        result.append(carry)
        return Unsigned(self.builder, BitVec.from_bits(self.builder, result))

    def add_trunc(self, other: Union[Self, int], cin: Optional[Bit] = None) -> Self:
        result = self.add_full(other, cin)
        return result.as_vec()[:-1].as_unsigned()

    def __add__(self, other: Union[Self, int]) -> Self:
        return self.add_full(other, cin=None)
