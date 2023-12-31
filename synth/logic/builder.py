from typing import List

from synth.logic.logic_list import LogicList, Signal


class LogicBuilder:
    def __init__(self, logic: LogicList):
        self.logic = logic

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
