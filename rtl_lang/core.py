from abc import abstractmethod, ABC
from collections import Counter
from typing import List, Optional, Dict


class Wire:
    def __init__(self, id: int, debug_name: Optional[str] = None):
        self.id = id
        self.debug_name = debug_name
        self.full_name = None

    def __str__(self):
        if self.full_name is not None:
            return f"\"{self.full_name}\""
        if self.debug_name is not None:
            return f"Wire({self.id}, \"{self.debug_name}\")"
        return f"Wire({self.id})"

    def __repr__(self):
        return str(self)


class Component(ABC):
    def __init__(self):
        self.debug_name = None

    @abstractmethod
    def connected_wires(self) -> List[Wire]:
        pass


class NetList:
    # TODO set? ordered set?
    wires: list[Wire]
    components: list[Component]

    vdd: Wire
    gnd: Wire

    def __init__(self):
        self.wires = []
        self.components = []

        self.vdd = self.new_wire("vdd")
        self.vdd.full_name = "vdd"
        self.gnd = self.new_wire("gnd")
        self.gnd.full_name = "gnd"

    def new_wire(self, debug_name: Optional[str] = None) -> Wire:
        wire = Wire(len(self.wires), debug_name)
        self.wires.append(wire)
        return wire

    def push_component(self, component: Component):
        self.components.append(component)

    def connect(self, a: Wire, b: Wire):
        from rtl_lang.components import Bridge
        self.push_component(Bridge(a, b))

    def print(self, component_cost: Optional[Dict[str, float]] = None):
        print("NetList:")
        print("  Wires:")
        for wire in self.wires:
            print(f"    {wire}")
        print("  Components:")
        for component in self.components:
            print(f"    {component}")

        print("  Component counts:")
        counts = Counter(type(c) for c in self.components)
        for component_type, count in counts.items():
            print(f"    {component_type.__name__}: {count}")
        if component_cost is not None:
            total_cost = sum(component_cost.get(component_type.__name__, 0) * count for component_type, count in counts.items())
            print(f"  Total cost: {total_cost}")
