from abc import abstractmethod, ABC
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional, Dict, Set, Callable


class Wire:
    unique_id: int
    debug_names: Set[str]
    special_name: Optional[str]

    def __init__(self, unique_id: int):
        self.unique_id = unique_id

        self.debug_names = set()
        self.special_name = None

    def __str__(self):
        suffix = ""
        if self.special_name is not None:
            suffix += f", {self.special_name}"
        if len(self.debug_names):
            suffix += f", debug={self.debug_names}"
        return f"Wire({self.unique_id}{suffix})"

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

    @abstractmethod
    def replace_wire(self, f: Callable[[Wire], Wire]):
        raise NotImplementedError()


class NetList:
    # TODO set? ordered set?
    wires: list[Wire]
    components: list[Component]

    def __init__(self):
        self.wires: List[Wire] = []
        self.components: List[Component] = []

        self.vdd = self.new_wire("vdd")
        self.vdd.full_name = "vdd"
        self.gnd = self.new_wire("gnd")
        self.gnd.full_name = "gnd"
        self.clk = self.new_wire("clk")
        self.clk.full_name = "clk"

        self.global_wires = [self.vdd, self.gnd, self.clk]

    def new_wire(self, debug_name: Optional[str] = None) -> Wire:
        wire = Wire(len(self.wires))
        if debug_name is not None:
            wire.debug_names.add(debug_name)
        self.wires.append(wire)
        return wire

    def push_component(self, component: Component):
        self.components.append(component)

    def connect(self, a: Wire, b: Wire):
        from synth.net.components import Bridge
        self.push_component(Bridge(a, b))

    def replace_wire(self, old: Wire, new: Wire) -> int:
        if old is new:
            return 0

        count = 0

        def replace(s: Wire) -> Wire:
            nonlocal count
            if s is old:
                count += 1
                return new
            return s

        for c in self.components:
            c.replace_wire(replace)

        new.debug_names.update(old.debug_names)

        return count

    def __str__(self):
        result = ""

        result += "NetList(\n"
        result += "  wires=[\n"
        for wire in self.wires:
            result += f"    {wire},\n"
        result += "  ],\n"
        result += "  components=[\n"
        for component in self.components:
            result += f"    {component},\n"
        result += "  ],\n"
        result += ")\n"
        return result

    def print_cost(self, component_cost: Dict[str, float]):
        print("NetList component counts:")
        counts = Counter(type(c) for c in self.components)
        for component_type, count in counts.items():
            print(f"    {component_type.__name__}: {count}")

        total_cost = sum(
            component_cost.get(component_type.__name__, 0) * count for component_type, count in counts.items())
        print(f"Total cost: {total_cost}")

    def render(self):
        import graphviz
        dot = graphviz.Digraph()
        next_dummy_index = 0

        # both wires and components are nodes
        # TODO directly connect wires with only two blocks connected?
        for wire in self.wires:
            if wire in self.global_wires:
                continue
            dot.node(name=f"wire_{wire.unique_id}", label=str(wire))

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
                    head_name = f"wire_{wire.unique_id}"
                    dir = "none"

                dot.edge(f"component_{id(component)}", head_name, tailport=port.dir, dir=dir, arrowhead="none")
        print(dot)
        # all_engines = ["dot", "neato", "fdp", "circo", "twopi", "osage", "patchwork"]
        # for engine in all_engines:
        #     dot.render(f"netlist_{engine}", view=True, format="svg", engine=engine)
        # dot.render(f"netlist", view=False, format="svg", engine="neato")
        # dot.render(f"netlist", view=False, format="svg", engine="fdp")
        dot.render(f"netlist", view=False, format="svg", engine="fdp")
