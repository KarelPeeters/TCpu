from dataclasses import dataclass
from typing import List, TypeVar, Generic, Optional


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


@dataclass
class InvPair(OptionalInvPair[T]):
    val: T
    inv: T
