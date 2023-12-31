from typing import List


class Table:
    def __init__(self, input_count: int, table: List[bool]):
        assert len(table) == 2 ** input_count
        self.input_count = input_count
        self.table = table
