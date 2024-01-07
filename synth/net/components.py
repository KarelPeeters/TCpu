from typing import List, Callable

from synth.net.net_list import Component, Wire, Port


# TODO automate "replace_wire" codegen, similar to pytorch Module/Parameter stuff

class Bridge(Component):
    def __init__(self, a: Wire, b: Wire):
        super().__init__()
        self.a = a
        self.b = b

    def ports(self) -> List[Port]:
        return [Port("a", None, self.a), Port("b", None, self.b)]

    def __str__(self):
        return f"Bridge({self.a}, {self.b})"

    def replace_wire(self, f: Callable[[Wire], Wire]):
        self.a = f(self.a)
        self.b = f(self.b)


class Resistor(Component):
    def __init__(self, a: Wire, b: Wire):
        super().__init__()
        self.a = a
        self.b = b

    def ports(self) -> List[Port]:
        return [Port("a", None, self.a), Port("b", None, self.b)]

    def __str__(self):
        return f"Resistor({self.a}, {self.b})"

    def replace_wire(self, f: Callable[[Wire], Wire]):
        self.a = f(self.a)
        self.b = f(self.b)


class Led(Component):
    def __init__(self, high: Wire, low: Wire):
        """
        high: anode, positive
        low: cathode, negative
        """
        super().__init__()
        self.high = high
        self.low = low

    def ports(self) -> List[Port]:
        return [Port("high", "n", self.high), Port("low", "s", self.low)]

    def __str__(self):
        return f"Led(high={self.high}, low={self.low})"

    def replace_wire(self, f: Callable[[Wire], Wire]):
        self.high = f(self.high)
        self.low = f(self.low)


class NMOS(Component):
    def __init__(self, gate: Wire, up: Wire, down: Wire):
        """NMOS: up: drain, down: source"""
        super().__init__()
        self.gate = gate
        self.up = up
        self.down = down

    def ports(self) -> List[Port]:
        return [Port("gate", "w", self.gate), Port("up", "n", self.up), Port("down", "s", self.down)]

    def __str__(self):
        return f"NMOS(gate={self.gate}, up={self.up}, down={self.down})"

    def replace_wire(self, f: Callable[[Wire], Wire]):
        self.gate = f(self.gate)
        self.up = f(self.up)
        self.down = f(self.down)


class PMOS(Component):
    def __init__(self, gate: Wire, up: Wire, down: Wire):
        """PMOS: gate, up: source, down: drain"""
        super().__init__()
        self.gate = gate
        self.up = up
        self.down = down

    def ports(self) -> List[Port]:
        return [Port("gate", "w", self.gate), Port("up", "n", self.up), Port("down", "s", self.down)]

    def __str__(self):
        return f"PMOS(gate={self.gate}, up={self.up}, down={self.down})"

    def replace_wire(self, f: Callable[[Wire], Wire]):
        self.gate = f(self.gate)
        self.up = f(self.up)
        self.down = f(self.down)
