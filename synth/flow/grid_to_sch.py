import math
import uuid
from dataclasses import dataclass
from typing import Dict, Union, Optional

from kiutils.items.common import Position, Effects, Justify, PageSettings, Property
from kiutils.items.schitems import SchematicSymbol, SymbolProjectInstance, SymbolProjectPath, GlobalLabel
from kiutils.schematic import Schematic
from kiutils.symbol import Symbol

from synth.flow.net_to_grid import Grid, GRID_EMPTY
from synth.net.components import NMOS, Resistor, Bridge
from synth.net.net_list import NetList, Wire, Component

REF_SCHEMATIC_PATH = "res/one_of_each.kicad_sch"
GRID_SIZE = 1.27
COMPONENT_MARGIN = 40
COMPONENT_DISTANCE = 20


@dataclass
class ReferenceComponent:
    ref_prefix: Optional[str]
    lib_symbol: Symbol
    sch_symbol: SchematicSymbol


def grid_to_phys(net: NetList, grid: Grid) -> Schematic:
    build = SchematicBuilder()

    for y in range(grid.grid_size):
        for x in range(grid.grid_size):
            ci = grid.grid[x, y]
            if ci == GRID_EMPTY:
                continue
            comp = net.components[ci]

            build.add_logic(
                comp,
                x=GRID_SIZE * (COMPONENT_MARGIN + x * COMPONENT_DISTANCE),
                y=GRID_SIZE * (COMPONENT_MARGIN + y * COMPONENT_DISTANCE),
            )

    return build.finish()


def net_to_phys(net: NetList) -> Schematic:
    build = SchematicBuilder()

    width = math.ceil(math.sqrt(len(net.components)))

    # components
    for index, comp in enumerate(net.components):
        x = GRID_SIZE * (COMPONENT_MARGIN + (index % width) * COMPONENT_DISTANCE)
        y = GRID_SIZE * (COMPONENT_MARGIN + (index // width) * COMPONENT_DISTANCE)
        build.add_logic(comp, x, y)

    return build.finish()


def wire_text(wire: Wire) -> str:
    # TODO these are not actually unique
    if len(wire.debug_names):
        return next(iter(wire.debug_names))
    return f"wire_{wire.unique_id}"


class SchematicBuilder:
    def __init__(self):
        sch_ref = Schematic.from_file(REF_SCHEMATIC_PATH)

        self.sch = Schematic.create_new()
        self.sch.version = sch_ref.version
        self.sch.libSymbols = sch_ref.libSymbols

        self.next_ref_index = {}

        def find(ref_prefix: Optional[str], lib: str, name: str) -> ReferenceComponent:
            lib_symbol = None
            for lib_symbol in self.sch.libSymbols:
                if lib_symbol.libraryNickname == lib and lib_symbol.entryName == name:
                    break

            sch_symbol = None
            for sch_symbol in sch_ref.schematicSymbols:
                if sch_symbol.libraryNickname == lib and sch_symbol.entryName == name:
                    break

            if lib_symbol is None or sch_symbol is None:
                raise KeyError(f"Could not find symbol {lib}:{name}")

            return ReferenceComponent(ref_prefix=ref_prefix, lib_symbol=lib_symbol, sch_symbol=sch_symbol)

        self.lib_nmos = find("N", "Custom", "NMOS")
        self.lib_pmos = find("P", "Custom", "PMOS")
        self.lib_resistor = find("R", "Device", "R_Small")
        self.lib_vdd = find(None, "power", "VDD")
        self.lib_gnd = find(None, "power", "GND")
        # self.lib_pwr_flag = find("power", "PWR_FLAG") # TODO why is this not found?

    def finish(self) -> Schematic:
        max_x = 0.0
        max_y = 0.0
        for c in self.sch.schematicSymbols:
            max_x = max(max_x, c.position.X)
            max_y = max(max_y, c.position.Y)

        self.sch.paper = PageSettings(paperSize="User", width=max_x + 2 * COMPONENT_MARGIN,
                                      height=max_y + 2 * COMPONENT_MARGIN)
        return self.sch

    def add_label(self, pos: Position, text: str):
        quadrant = int((pos.angle // 90) % 4)
        justify = ["left", "left", "right", "right", ][quadrant]

        label = GlobalLabel(
            text=text,
            # TODO different shapes? do we care enough?
            shape="input",
            fieldsAutoplaced=True,
            position=pos,
            effects=Effects(justify=Justify(horizontally=justify))
        )
        self.sch.globalLabels.append(label)

    def add_component(self, symbol: ReferenceComponent, pos: Position, pin_labels: Dict[Union[str, int], str]):
        lib_symbol = symbol.lib_symbol
        sch_symbol = symbol.sch_symbol

        # collect and check pins
        actual_pins = {}
        for unit in [lib_symbol] + lib_symbol.units:
            for pin in unit.pins:
                name = pin.name if pin.name != "~" else int(pin.number)
                if name in actual_pins:
                    raise KeyError(
                        f"Duplicate pin {name} in symbol {lib_symbol.libraryNickname}:{lib_symbol.entryName}")
                actual_pins[name] = pin
        assert actual_pins.keys() == pin_labels.keys(), \
            f"Pin labels do not match pins: Expected {actual_pins.keys()}, got {pin_labels.keys()}"

        # fully random UUID
        uuid_str = str(uuid.uuid4())

        # footprint
        properties = []
        for prop in sch_symbol.properties:
            if prop.key == "Footprint":
                properties.append(Property(key="Footprint", value=prop.value))
                break

        # reference
        ref_index = self.next_ref_index.get(symbol.ref_prefix, 0)
        self.next_ref_index[symbol.ref_prefix] = ref_index + 1
        reference = f"{symbol.ref_prefix}{ref_index}"
        properties.append(Property(key="Reference", value=reference))

        # TODO pin UUIDs?, more properties? (reference, value, footprint, datasheet)
        instance = SchematicSymbol(
            libraryNickname=lib_symbol.libraryNickname,
            entryName=lib_symbol.entryName,
            position=pos,
            inBom=True,
            onBoard=True,
            fieldsAutoplaced=True,
            mirror=None,
            uuid=uuid_str,
            instances=[
                # TODO reference? name?
                SymbolProjectInstance(paths=[SymbolProjectPath(sheetInstancePath=f"/{uuid_str}", reference=reference)])
            ],
            properties=properties,
        )
        self.sch.schematicSymbols.append(instance)

        for pin_name, pin in actual_pins.items():
            pin_pos = Position(
                X=pos.X + pin.position.X,
                Y=pos.Y + pin.position.Y,
                angle=pin.position.angle if pin.position.angle != 0 else 180,
            )
            self.add_label(pin_pos, pin_labels[pin_name])

    def add_nmos(self, x: float, y: float, gate: str, up: str, down: str):
        labels = {"G": gate, "D": down, "S": up}
        self.add_component(self.lib_nmos, Position(X=x, Y=y, angle=0), labels)

    def add_resistor(self, x: float, y: float, a: str, b: str):
        labels = {1: a, 2: b}
        self.add_component(self.lib_resistor, Position(X=x, Y=y, angle=0), labels)

    def add_logic(self, comp: Component, x, y):
        if isinstance(comp, NMOS):
            self.add_nmos(
                x=x, y=y,
                gate=wire_text(comp.gate), up=wire_text(comp.up), down=wire_text(comp.down)
            )
        elif isinstance(comp, Resistor):
            self.add_resistor(
                x=x, y=y,
                a=wire_text(comp.a), b=wire_text(comp.b)
            )
        elif isinstance(comp, Bridge):
            self.add_label(Position(X=x, Y=y, angle=0), wire_text(comp.a))
            self.add_label(Position(X=x, Y=y, angle=180), wire_text(comp.b))
        else:
            raise NotImplementedError(f"Unknown component type {type(comp)}")
