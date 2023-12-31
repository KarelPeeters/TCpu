from typing import List

from rtl_lang.core import Component, Wire


class Bridge(Component):
    def __init__(self, a: Wire, b: Wire):
        super().__init__()
        self.a = a
        self.b = b

    def connected_wires(self) -> List[Wire]:
        return [self.a, self.b]

    def __str__(self):
        return f"Bridge({self.a}, {self.b})"

class Resistor(Component):
    def __init__(self, a: Wire, b: Wire):
        super().__init__()
        self.a = a
        self.b = b

    def connected_wires(self) -> List[Wire]:
        return [self.a, self.b]

    def __str__(self):
        return f"Resistor({self.a}, {self.b})"


class Led(Component):
    def __init__(self, high: Wire, low: Wire):
        """
        high: anode, positive
        low: cathode, negative
        """
        super().__init__()
        self.high = high
        self.low = low

    def connected_wires(self) -> List[Wire]:
        return [self.high, self.low]

    def __str__(self):
        return f"Led(high={self.high}, low={self.low})"


class NMOS(Component):
    def __init__(self, gate: Wire, up: Wire, down: Wire):
        """NMOS: up: drain, down: source"""
        super().__init__()
        self.gate = gate
        self.up = up
        self.down = down

    def connected_wires(self) -> List[Wire]:
        return [self.gate, self.up, self.down]

    def __str__(self):
        return f"NMOS(gate={self.gate}, up={self.up}, down={self.down})"


class PMOS(Component):
    def __init__(self, gate: Wire, up: Wire, down: Wire):
        """PMOS: gate, up: source, down: drain"""
        super().__init__()
        self.gate = gate
        self.up = up
        self.down = down

    def connected_wires(self) -> List[Wire]:
        return [self.gate, self.up, self.down]

    def __str__(self):
        return f"PMOS(gate={self.gate}, up={self.up}, down={self.down})"
