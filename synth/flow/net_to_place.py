import math
from typing import List, Dict, Tuple

import numpy as np

from synth.net.net_list import NetList, Wire


class Grid:
    wire_to_index: Dict[Wire, int]
    wire_index_to_component_indices: List[List[int]]
    component_index_to_wire_indices: List[List[int]]
    grid: np.ndarray
    component_to_grid_pos: List[int]

    def __init__(self, net: NetList):
        # build lookup tables
        self.wire_to_index = {wire: wi for wi, wire in enumerate(net.wires)}
        self.wire_index_to_component_indices = [[] for _ in self.wire_to_index]
        self.component_index_to_wire_indices = [[] for _ in net.components]
        for ci, comp in enumerate(net.components):
            for port in comp.ports():
                if port.wire in net.global_wires:
                    continue
                wi = self.wire_to_index[port.wire]
                self.wire_index_to_component_indices[wi].append(ci)
                self.component_index_to_wire_indices[ci].append(wi)

        # print stats
        counts = {}
        for cs in self.wire_index_to_component_indices:
            # print(f"Wire {wire} connected to {len(cs)} components")
            counts.setdefault(len(cs), 0)
            counts[len(cs)] += 1
        counts = dict(sorted([(k, v) for k, v in counts.items()]))
        print(counts)

        # initialize grid
        # TODO try random instead
        self.grid_size = math.ceil(math.sqrt(len(net.components)))
        self.grid = np.full((self.grid_size, self.grid_size), -1)
        self.component_to_grid_pos = []
        for ci, comp in enumerate(net.components):
            self.grid[ci % self.grid_size, ci // self.grid_size] = ci
            self.component_to_grid_pos.append(ci)

        self.curr_cost = self.calc_total_cost()

    def plot(self):
        import matplotlib.pyplot as plt
        plt.figure()
        ax = plt.gca()

        for ci, gi in enumerate(self.component_to_grid_pos):
            x, y = self.grid_index_to_xy(gi)
            ax.add_patch(plt.Rectangle((x + .2, y + .2), .6, .6, color="blue"))

        max_group_cost = 0
        for wi, cs in enumerate(self.wire_index_to_component_indices):
            if len(cs) == 0:
                continue
            cost, _ = self.min_spanning_tree_cost(wi)
            max_group_cost = max(max_group_cost, cost / len(cs))

        for wi, cs in enumerate(self.wire_index_to_component_indices):
            cost, edges = self.min_spanning_tree_cost(wi)
            for ci0, ci1 in edges:
                x0, y0 = self.grid_index_to_xy(self.component_to_grid_pos[ci0])
                x1, y1 = self.grid_index_to_xy(self.component_to_grid_pos[ci1])
                c = (cost / len(cs)) / max_group_cost
                ax.plot([x0 + .5, x1 + .5], [y0 + .5, y1 + .5], color=(c, 1 - c, 0))

        ax.set_xlim(0, self.grid_size)
        ax.set_ylim(0, self.grid_size)
        plt.show()

    def calc_total_cost(self) -> int:
        total_cost = 0
        for wi in range(len(self.wire_to_index)):
            cost, _ = self.min_spanning_tree_cost(wi)
            total_cost += cost
        return total_cost

    def min_spanning_tree_cost(self, wi: int) -> Tuple[int, List[Tuple[int, int]]]:
        todo = self.wire_index_to_component_indices[wi]
        if len(todo) <= 1:
            return 0, []

        total_cost = 0
        done = [todo[0]]
        todo = set(todo) - set(done)
        edges = []

        while len(todo):
            best_cost = np.inf
            best_ci = None
            best_bi = None

            for ci in todo:
                for bi in done:
                    cost = self.grid_dist(ci, bi)
                    if cost < best_cost:
                        best_cost = cost
                        best_ci = ci
                        best_bi = bi

            total_cost += best_cost
            done.append(best_ci)
            todo.remove(best_ci)
            edges.append((best_ci, best_bi))

        return total_cost, edges

    def grid_dist(self, g0: int, g1: int) -> int:
        # manhattan for now
        x0, y0 = self.grid_index_to_xy(g0)
        x1, y1 = self.grid_index_to_xy(g1)
        return abs(x1 - x0) + abs(y1 - y0)

    def grid_index_to_xy(self, gi: int) -> (int, int):
        return gi % self.grid_size, gi // self.grid_size


def net_to_place(net: NetList):
    grid = Grid(net)

    print(grid.calc_total_cost())

    grid.plot()
