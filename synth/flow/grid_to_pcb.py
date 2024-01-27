from dataclasses import dataclass

from kiutils.board import Board

from synth.flow.net_to_grid import Grid
from synth.net.net_list import NetList


@dataclass
class Capabilities:
    via_hole_size: float
    via_diameter: float
    via_hole_clearance: float
    via_track_clearance: float
    trace_width: float
    trace_clearance: float

    layer_vertical: str
    layer_horizontal: str


JLC_PCB_CAPABILITIES = Capabilities(
    via_hole_size=0.3,
    via_diameter=0.6,
    via_hole_clearance=0.3,
    via_track_clearance=0.2,
    trace_width=0.15,
    trace_clearance=0.15,
    layer_vertical="F.Cu",
    layer_horizontal="B.Cu",
)

REF_BOARD_PATH = "res/one_of_each.kicad_pcb"


class BoardBuilder:
    def __init__(self):
        board_ref = Board.from_file(REF_BOARD_PATH)
        print(board_ref)


def grid_to_board(grid: Grid, net: NetList, cap: Capabilities):
    pass


def main():
    pass

if __name__ == '__main__':
    main()