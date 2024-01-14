from dataclasses import dataclass
from typing import List, Dict, Optional

from synth.flow.logic_util import UseDef, ExternalInput
from synth.logic.logic_list import LogicList, Signal, LUT, FF


@dataclass
class History:
    logic: LogicList
    use_def: UseDef
    signal_history: List[Dict[Signal, Optional[bool]]]

    def outputs(self):
        return [
            [self.signal_history[i][s] for s in self.logic.external_outputs]
            for i in range(len(self.signal_history))
        ]

    def print(self, skip_unchanged=False):
        print("History:")

        max_len = max(len(str(s)) for s in self.logic.signals)

        # print the time every 8 steps
        print(" " * (max_len + 5), end="  ")
        for i in range(len(self.signal_history)):
            if i % 8 == 0:
                print(f"|{i:<7}", end="")
        print()

        # TODO debug names as separate column
        for s in self.logic.signals:
            suf_f, suf_l, suf_i, suf_o = " ", " ", " ", " "
            for d in self.use_def.defs[s]:
                if isinstance(d, LUT):
                    suf_l = "L"
                elif isinstance(d, FF):
                    suf_f = "F"
                elif isinstance(d, ExternalInput):
                    suf_i = "I"
                if s in self.logic.external_outputs:
                    suf_o = "O"

            print(f"{str(s):{max_len}} {suf_l}{suf_f}{suf_i}{suf_o}: ", end="")
            v_str_prev = None
            for i in range(len(self.signal_history)):
                v = self.signal_history[i][s]
                v_str = str(int(v)) if v is not None else "z"
                if skip_unchanged and v_str == v_str_prev:
                    print(" ", end="")
                else:
                    print(v_str, end="")
                v_str_prev = v_str
            print()


def logic_sim(logic: LogicList, steps: int) -> History:
    logic.validate()
    use_def = UseDef.from_logic(logic)

    prev = {ff.input: ff.init for ff in logic.ffs}
    signal_history = []

    def eval(state, signal: Signal):
        if signal in state:
            return state[signal]

        results = set()
        for d in use_def.defs[signal]:
            assert isinstance(d, LUT)
            results.add(d.eval([eval(state, x) for x in d.inputs]))

        # TODO proper merge, including high impedance
        if len(results) == 0:
            return None
        assert len(results) == 1, f"Multiple results for {signal}: {results}"

        result = results.pop()
        state[signal] = result
        return result

    for i in range(steps):
        curr = {}
        for x in logic.external_inputs:
            # TODO allow user-configurable inputs
            curr[x] = False
        for ff in logic.ffs:
            curr[ff.output] = prev[ff.input]
        for lut in logic.luts:
            curr[lut.output] = eval(curr, lut.output)

        signal_history.append(curr)
        prev = curr

    return History(logic=logic, use_def=use_def, signal_history=signal_history)
