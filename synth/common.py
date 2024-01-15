from dataclasses import dataclass
from typing import List, TypeVar, Generic, Optional, Callable


class Table:
    def __init__(self, input_count: int, table: List[bool]):
        assert len(table) == 2 ** input_count
        self.input_count = input_count
        self.table = table


T = TypeVar("T")


@dataclass
class OptionalInvPair(Generic[T]):
    val: T
    inv: Optional[T]

    def require(self, f: Callable[[T], T]) -> 'InvPair':
        if self.inv is None:
            return InvPair(self.val, f(self.val))
        else:
            return InvPair(self.val, self.inv)


@dataclass
class InvPair(OptionalInvPair[T]):
    val: T
    inv: T
