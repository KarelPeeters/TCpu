from dataclasses import dataclass
from typing import List, Dict, Optional

from synth.flow.logic_util import UseDef, ExternalInput
from synth.logic.logic_list import LogicList, Signal, LUT, FF


@dataclass
class History:
    logic: LogicList
    use_def: UseDef
    signal_history: List[Dict[Signal, Optional[bool]]]

    def print(self):
        print("History:")

        signal_names = []
        for s in self.logic.signals:
            suf_f, suf_l, suf_i, suf_o = "", "", "", ""
            for d in self.use_def.defs[s]:
                if isinstance(d, LUT):
                    suf_l = "L"
                elif isinstance(d, FF):
                    suf_f = "F"
                elif isinstance(d, ExternalInput):
                    suf_i = "I"
            if s in self.logic.external_outputs:
                suf_o = "O"

            name = f"{s} {suf_f}{suf_l} {suf_i}{suf_o}"
            signal_names.append(name)

        max_len = max(len(n) for n in signal_names)

        # print the time every 8 steps
        print(" " * max_len, end="  ")
        for i in range(len(self.signal_history)):
            if i % 8 == 0:
                print(f"|{i:<7}", end="")
        print()

        for n, s in zip(signal_names, self.logic.signals):
            print(f"{n:{max_len}}: ", end="")
            for i in range(len(self.signal_history)):
                v = self.signal_history[i].get(s)
                v_str = str(int(v)) if v is not None else "z"
                print(v_str, end="")
            print()


def logic_sim(logic: LogicList, steps: int) -> History:
    logic.validate()
    use_def = UseDef.from_logic(logic)

    prev = {ff.input: ff.init for ff in logic.ffs}
    signal_history = [prev]

    def eval(state, signal: Signal):
        if signal in state:
            return state[signal]

        results = set()
        for d in use_def.defs[signal]:
            assert isinstance(d, LUT)
            d.eval([eval(state, x) for x in d.inputs])

        # TODO proper merge, including high impedance
        if len(results) == 0:
            return None

        assert len(results) == 1, f"Multiple results for {signal}: {results}"
        return results.pop()

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
