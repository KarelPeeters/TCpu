import math
import uuid
from typing import Dict, Union

from kiutils.items.common import Position, Effects, Justify, PageSettings
from kiutils.items.schitems import SchematicSymbol, SymbolProjectInstance, SymbolProjectPath, GlobalLabel
from kiutils.schematic import Schematic
from kiutils.symbol import Symbol

from synth.net.components import NMOS, Resistor, Bridge
from synth.net.net_list import NetList, Wire

REF_SCHEMATIC_PATH = "res/one_of_each.kicad_sch"
GRID_SIZE = 1.27
COMPONENT_MARGIN = 40
COMPONENT_DISTANCE = 20


def net_to_phys(net: NetList) -> Schematic:
    build = SchematicBuilder()

    width = math.ceil(math.sqrt(len(net.components)))

    # components
    for index, comp in enumerate(net.components):
        x = GRID_SIZE * (COMPONENT_MARGIN + (index % width) * COMPONENT_DISTANCE)
        y = GRID_SIZE * (COMPONENT_MARGIN + (index // width) * COMPONENT_DISTANCE)

        if isinstance(comp, NMOS):
            build.add_nmos(
                x=x, y=y,
                gate=wire_text(comp.gate), up=wire_text(comp.up), down=wire_text(comp.down)
            )
        elif isinstance(comp, Resistor):
            build.add_resistor(
                x=x, y=y,
                a=wire_text(comp.a), b=wire_text(comp.b)
            )
        elif isinstance(comp, Bridge):
            build.add_label(Position(X=x, Y=y, angle=0), wire_text(comp.a))
            build.add_label(Position(X=x, Y=y, angle=180), wire_text(comp.b))
        else:
            raise NotImplementedError(f"Unknown component type {type(comp)}")

    return build.finish()


def wire_text(wire: Wire) -> str:
    if wire.full_name is not None:
        return wire.full_name
    return f"wire_{wire.id}"


class SchematicBuilder:
    def __init__(self):
        sch_ref = Schematic.from_file(REF_SCHEMATIC_PATH)

        self.sch = Schematic.create_new()
        self.sch.version = sch_ref.version
        self.sch.libSymbols = sch_ref.libSymbols

        def find(lib: str, name: str) -> Symbol:
            for s in self.sch.libSymbols:
                if s.libraryNickname == lib and s.entryName == name:
                    return s
            raise KeyError(f"Could not find symbol {lib}:{name}")

        self.lib_nmos = find("Custom", "NMOS")
        self.lib_pmos = find("Custom", "PMOS")
        self.lib_resistor = find("Device", "R_Small")
        self.lib_vdd = find("power", "VDD")
        self.lib_gnd = find("power", "GND")
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

    def add_component(self, symbol: Symbol, pos: Position, pin_labels: Dict[Union[str, int], str]):
        # collect and check pins
        actual_pins = {}
        for unit in [symbol] + symbol.units:
            for pin in unit.pins:
                name = pin.name if pin.name != "~" else int(pin.number)
                if name in actual_pins:
                    raise KeyError(f"Duplicate pin {name} in symbol {symbol.libraryNickname}:{symbol.entryName}")
                actual_pins[name] = pin
        assert actual_pins.keys() == pin_labels.keys(), \
            f"Pin labels do not match pins: Expected {actual_pins.keys()}, got {pin_labels.keys()}"

        # fully random UUID
        uuid_str = str(uuid.uuid4())

        # TODO pin UUIDs?, more properties? (reference, value, footprint, datasheet)
        instance = SchematicSymbol(
            libraryNickname=symbol.libraryNickname,
            entryName=symbol.entryName,
            position=pos,
            inBom=True,
            onBoard=True,
            fieldsAutoplaced=True,
            mirror=None,
            uuid=uuid_str,
            instances=[
                # TODO reference? name?
                SymbolProjectInstance(paths=[SymbolProjectPath(sheetInstancePath=f"/{uuid_str}")])
            ]
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
