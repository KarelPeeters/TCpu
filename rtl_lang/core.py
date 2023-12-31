from abc import abstractmethod, ABC
from collections import Counter
from dataclasses import dataclass
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


@dataclass
class Port:
    name: str
    dir: Optional[str]
    wire: Wire


class Component(ABC):
    def __init__(self):
        self.debug_name = None

    @abstractmethod
    def ports(self) -> List[Port]:
        raise NotImplementedError()


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
        self.clk = self.new_wire("clk")
        self.clk.full_name = "clk"

        self.global_wires = [self.vdd, self.gnd, self.clk]

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
            total_cost = sum(
                component_cost.get(component_type.__name__, 0) * count for component_type, count in counts.items())
            print(f"  Total cost: {total_cost}")

    def render(self):
        import graphviz
        dot = graphviz.Digraph()
        next_dummy_index = 0

        # both wires and components are nodes
        # TODO directly connect wires with only two blocks connected?
        for wire in self.wires:
            if wire in self.global_wires:
                continue
            dot.node(name=f"wire_{wire.id}", label=str(wire))

        for component in self.components:
            dot.node(name=f"component_{id(component)}", label=str(component), shape="box")
            for port in component.ports():
                wire = port.wire
                if wire in self.global_wires:
                    if wire == self.vdd:
                        shape = "triangle"
                        dir = "s"
                    elif wire == self.gnd:
                        shape = "invtriangle"
                        dir = "n"
                    elif wire == self.clk:
                        shape = "square"
                        dir = None
                    else:
                        shape = None
                        dir = None

                    label = str(wire) if shape is None else ""
                    dot.node(name=f"dummy_{next_dummy_index}", label=label, shape=shape)
                    next_dummy_index += 1
                    head_name = f"dummy_{next_dummy_index - 1}"
                else:
                    head_name = f"wire_{wire.id}"
                    dir = "none"

                dot.edge(f"component_{id(component)}", head_name, tailport=port.dir, dir=dir, arrowhead="none")
        print(dot)
        # all_engines = ["dot", "neato", "fdp", "circo", "twopi", "osage", "patchwork"]
        # for engine in all_engines:
        #     dot.render(f"netlist_{engine}", view=True, format="svg", engine=engine)
        # dot.render(f"netlist", view=False, format="svg", engine="neato")
        # dot.render(f"netlist", view=False, format="svg", engine="fdp")
        dot.render(f"netlist", view=False, format="svg", engine="fdp")
