from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce
from typing import List, Callable, Self, Union, overload, Optional, TypeVar

from synth.logic.logic_list import LogicList, Signal


class LogicBuilder:
    def __init__(self, logic: LogicList):
        self.logic = logic
        self.connections_to_make: List[(Signal, Signal)] = []

        self.const_zero = Bit(self, self.logic.new_lut([], [False]))
        self.const_one = Bit(self, self.logic.new_lut([], [True]))

        logic.builder_count += 1

    def finish(self):
        for a, b in self.connections_to_make:
            self.logic.replace_signal(a, b)
        self.connections_to_make.clear()

        self.logic.builder_count -= 1
        self.logic = None

    # construction
    def const_bit(self, value: bool) -> 'Bit':
        assert isinstance(value, bool)
        if value:
            return self.const_one
        else:
            return self.const_zero

    def const_unsigned(self, bits: int, value: int) -> 'Unsigned':
        assert 0 <= value < 2 ** bits
        bits = [self.const_bit(value & (1 << i) != 0) for i in range(bits)]
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

    # io marking
    def mark_external_input(self, *value: 'BuilderValue'):
        for v in value:
            self.logic.mark_external_input(*v.all_signals())

    def mark_external_output(self, *value: 'BuilderValue'):
        for v in value:
            self.logic.mark_external_output(*v.all_signals())

    # basic gates
    def gate_not(self, signal: Signal) -> Signal:
        return self.logic.new_lut([signal], [True, False])

    def gate_and(self, signals: List[Signal]) -> Signal:
        table = [False] * (2 ** len(signals) - 1) + [True]
        return self.logic.new_lut(signals, table)

    def gate_or(self, signals: List[Signal]) -> Signal:
        table = [False] + [True] * (2 ** len(signals) - 1)
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

    @abstractmethod
    def type_name(self) -> str:
        raise NotImplementedError()

    def map_single(self, f: Callable[[Signal], Signal]) -> Self:
        def wrap(a, b):
            assert b is a
            return f(a)

        return self.map(self, wrap)

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

    def all_signals(self) -> List[Signal]:
        """
        Get all signals contained in this value.
        """
        signals = []

        def visit(s):
            signals.append(s)
            return s

        _ = self.map_single(visit)

        return signals

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

    def mux(self, value_0: V, value_1: V) -> V:
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

    @property
    def bits(self) -> List[Bit]:
        return [Bit(self.builder, s) for s in self.signals]

    def __len__(self):
        return len(self.signals)

    def __iter__(self):
        return iter(self.bits)

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
    bits: BitVec

    def __post_init__(self):
        assert isinstance(self.bits, BitVec), f"Expected BitVec, got {type(self.bits)}"

    def __repr__(self):
        return f"Unsigned({self.bits.signals})"

    def map(self, other: Optional[Self], f: Callable[[Signal, Optional[Signal]], Signal]) -> Self:
        assert isinstance(other, Unsigned), f"Type mismatch: expected Unsigned, got {type(other)}"
        return Unsigned(self.builder, self.bits.map(other.bits, f))

    def type_name(self) -> str:
        return f"unsigned[{len(self)}]"

    def as_vec(self) -> BitVec:
        return self.bits

    def __len__(self):
        return len(self.bits)

    def __invert__(self) -> Self:
        return Unsigned(self.builder, self.bits.__invert__())

    def __and__(self, other: Self) -> Self:
        assert self.builder is other.builder
        return Unsigned(self.builder, self.bits.__and__(other.bits))

    def __or__(self, other: Self) -> Self:
        assert self.builder is other.builder
        return Unsigned(self.builder, self.bits.__or__(other.bits))

    def __xor__(self, other: Self) -> Self:
        assert self.builder is other.builder
        return Unsigned(self.builder, self.bits.__xor__(other.bits))

    def shift(self, amount: Union[Self, int], right: bool, pad: Bit) -> Self:
        def get_padded(x, i):
            if 0 <= i < len(x):
                return x[i]
            return pad
        dir_sign = 1 if right else -1

        if isinstance(amount, int):
            # TODO allow negative shifts?
            assert amount >= 0
            result = []
            # TODO try just converting this to bits and letting the optimizer deal with it
            for i_out in range(len(self)):
                i_in = i_out + dir_sign * amount
                result.append(get_padded(self.bits, i_in))
            return Unsigned(self.builder, BitVec.from_bits(self.builder, result))

        assert isinstance(amount, Unsigned)
        assert self.builder is amount.builder

        # generate barrel shifter
        curr = self.bits.bits
        for i_amount, select in enumerate(amount.bits):
            curr = [
                select.mux(curr[i_curr], get_padded(curr, i_curr + dir_sign * (1 << i_amount)))
                for i_curr in range(len(self))
            ]
        return BitVec.from_bits(self.builder, curr).as_unsigned()

    def __rshift__(self, amount: Union[Self, int]) -> Self:
        assert isinstance(amount, Unsigned)
        assert self.builder is amount.builder
        return self.shift(amount=amount, right=True, pad=(self.builder.const_bit(False)))

    def __lshift__(self, amount: Union[Self, int]) -> Self:
        assert isinstance(amount, Unsigned)
        assert self.builder is amount.builder
        return self.shift(amount=amount, right=False, pad=(self.builder.const_bit(False)))

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
            carry, result_i = Bit.full_add(self.bits[i], other.bits[i], carry)
            result.append(result_i)

        result.append(carry)
        return Unsigned(self.builder, BitVec.from_bits(self.builder, result))

    def add_trunc(self, other: Union[Self, int], cin: Optional[Bit] = None) -> Self:
        result = self.add_full(other, cin)
        return result.as_vec()[:-1].as_unsigned()

    def __add__(self, other: Union[Self, int]) -> Self:
        return self.add_full(other, cin=None)
