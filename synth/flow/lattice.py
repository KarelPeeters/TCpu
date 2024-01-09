from dataclasses import dataclass
from typing import Self, Optional, TypeVar, Generic, ClassVar

T = TypeVar("T")


@dataclass
class Lattice(Generic[T]):
    is_overdef: bool
    value: Optional[T]

    UNDEF: ClassVar['Lattice']
    OVERDEF: ClassVar['Lattice']

    @staticmethod
    def undef():
        return Lattice.UNDEF

    @staticmethod
    def new_def(value: T):
        return Lattice(is_overdef=False, value=value)

    @staticmethod
    def overdef():
        return Lattice.OVERDEF

    def __post_init__(self):
        assert not(self.is_overdef and self.value is not None)

    @property
    def is_undef(self):
        return self.value is None and not self.is_overdef

    @property
    def is_def(self):
        return self.value is not None

    def can_be(self, v: T) -> bool:
        assert v is not None
        return self.is_overdef or (self.is_def and self.value == v)

    def merge(self, b: Self) -> Self:
        a = self

        if a.is_undef:
            return b
        if b.is_undef:
            return a
        if a.is_overdef or b.is_overdef:
            return Lattice.OVERDEF
        if a.is_def and b.is_def:
            if a.value == b.value:
                return a
            else:
                return Lattice.OVERDEF

        assert False, f"missing type combination {a} {b}"

    def __str__(self):
        if self.is_overdef:
            return "Lattice.overdef"
        elif self.is_undef:
            return "Lattice.undef"
        else:
            return f"Lattice.def({self.value})"

    def __repr__(self):
        return str(self)


Lattice.OVERDEF = Lattice(is_overdef=True, value=None)
Lattice.UNDEF = Lattice(is_overdef=False, value=None)
