import math
import os
import random
import time
from typing import List, Dict, Tuple

import numpy as np
from matplotlib import pyplot as plt

from synth.net.net_list import NetList, Wire

GRID_EMPTY = -2 ** 32


class Grid:
    wire_to_index: Dict[Wire, int]
    wire_index_to_component_indices: List[List[int]]
    wire_index_to_cost: np.array
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
        # TODO sadly random is worse than the default order for now :)
        # TODO hierarchical grid? first raw placement, then more detailed in separate pass
        # TODO try making the grid a bit too large, it seems to speed things up
        self.grid_size = math.ceil(math.sqrt(len(net.components)))
        self.grid_area = self.grid_size * self.grid_size
        self.grid = np.full((self.grid_size, self.grid_size), GRID_EMPTY)
        self.component_to_grid_pos = []

        indexed_components = list(range(len(net.components)))
        random.shuffle(indexed_components)

        for ci, gi in enumerate(indexed_components):
            x, y = self.grid_index_to_xy(gi)
            self.grid[x, y] = ci
            self.component_to_grid_pos.append(gi)

        self.wire_index_to_cost = self.calc_wire_costs()
        self.curr_cost = np.sum(self.wire_index_to_cost)

    def plot(self):
        plt.figure()
        ax = plt.gca()

        for ci, gi in enumerate(self.component_to_grid_pos):
            x, y = self.grid_index_to_xy(gi)
            ax.add_patch(plt.Rectangle((x + .2, y + .2), .6, .6, color="blue"))

        max_tree_len = 0
        for wi, cs in enumerate(self.wire_index_to_component_indices):
            if len(cs) == 0:
                continue
            tree_len, _ = self.wire_min_spanning_tree(wi)
            max_tree_len = max(max_tree_len, tree_len / len(cs))

        for wi, cs in enumerate(self.wire_index_to_component_indices):
            tree_len, edges = self.wire_min_spanning_tree(wi)
            for ci0, ci1 in edges:
                x0, y0 = self.grid_index_to_xy(self.component_to_grid_pos[ci0])
                x1, y1 = self.grid_index_to_xy(self.component_to_grid_pos[ci1])
                c = (tree_len / len(cs)) / max_tree_len
                ax.plot([x0 + .5, x1 + .5], [y0 + .5, y1 + .5], color=(c, 1 - c, 0))

        ax.set_xlim(0, self.grid_size)
        ax.set_ylim(0, self.grid_size)

    def try_swap_cells(self, ai: int, bi: int, temp: float) -> bool:
        # swap
        if not self.swap_grid_cells_leave_cost(ai, bi):
            return False

        # collect affected wires
        ca = self.grid[*self.grid_index_to_xy(ai)]
        cb = self.grid[*self.grid_index_to_xy(bi)]
        affected_wires = set()
        if ca != GRID_EMPTY:
            affected_wires.update(self.component_index_to_wire_indices[ca])
        if cb != GRID_EMPTY:
            affected_wires.update(self.component_index_to_wire_indices[cb])

        # incrementally update cost
        new_cost = self.curr_cost
        affected_wires_cost = []
        for wi in affected_wires:
            cost = self.wire_cost(wi)
            affected_wires_cost.append(cost)
            new_cost += cost - self.wire_index_to_cost[wi]

        # check if improvement
        # TODO use actual temperature here? is it actually useful? why?
        if new_cost < self.curr_cost or np.random.uniform() < temp:
            # keep
            self.curr_cost = new_cost
            for wi, c in zip(affected_wires, affected_wires_cost):
                self.wire_index_to_cost[wi] = c
            return True
        else:
            # undo
            self.swap_grid_cells_leave_cost(ai, bi)
            return False

    def swap_grid_cells_leave_cost(self, ai: int, bi: int) -> bool:
        if ai == bi:
            return False

        ax, ay = self.grid_index_to_xy(ai)
        bx, by = self.grid_index_to_xy(bi)

        ca = self.grid[ax, ay]
        cb = self.grid[bx, by]
        if ca == cb:
            # both must be empty
            return False

        self.grid[ax, ay] = cb
        self.grid[bx, by] = ca

        if ca != GRID_EMPTY:
            self.component_to_grid_pos[ca] = bi
        if cb != GRID_EMPTY:
            self.component_to_grid_pos[cb] = ai
        return True

    def check_validness(self):
        print("Checking validness")

        # check grid -> component
        seen = set()
        for ci, gi in enumerate(self.component_to_grid_pos):
            x, y = self.grid_index_to_xy(gi)
            assert self.grid[x, y] == ci
            seen.add(gi)

        for gi in range(self.grid_area):
            if gi not in seen:
                x, y = self.grid_index_to_xy(gi)
                assert self.grid[x, y] == GRID_EMPTY

        # check cached costs
        wire_costs = self.calc_wire_costs()
        for wi in range(len(self.wire_index_to_cost)):
            assert wire_costs[wi] == self.wire_index_to_cost[wi]
        assert self.curr_cost == sum(wire_costs)

    def calc_wire_costs(self) -> np.array:
        wire_index_to_cost = np.zeros(len(self.wire_to_index), dtype=int)

        for wi in range(len(self.wire_to_index)):
            cost = self.wire_cost(wi)
            wire_index_to_cost[wi] = cost

        return wire_index_to_cost

    def wire_cost(self, wi: int) -> int:
        return self.wire_half_perimeter_cost(wi)

    def wire_half_perimeter_cost(self, wi: int) -> int:
        cis = self.wire_index_to_component_indices[wi]
        if len(cis) <= 1:
            return 0

        min_x = np.inf
        min_y = np.inf
        max_x = -np.inf
        max_y = -np.inf

        for ci in cis:
            x, y = self.grid_index_to_xy(self.component_to_grid_pos[ci])
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)

        return (max_x - min_x) + (max_y - min_y)

    def wire_min_spanning_tree(self, wi: int) -> Tuple[int, List[Tuple[int, int]]]:
        """ returns (cost, edges)"""

        todo = self.wire_index_to_component_indices[wi]
        if len(todo) <= 1:
            return 0, []

        # weirdly optimizing this for small nets doesn't matter much:
        #   is there a terrible slowdown for large nets?

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
                    cost = self.grid_dist(self.component_to_grid_pos[ci], self.component_to_grid_pos[bi])
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
        # TODO maybe a mix of manhattan and euclidean?
        #   pick whatever ends up best approximating the real wire length?
        #   do we even want to optimize total wire length? we really want PCB area!

        x0, y0 = self.grid_index_to_xy(g0)
        x1, y1 = self.grid_index_to_xy(g1)

        # manhattan for now
        return abs(x1 - x0) + abs(y1 - y0)

        # euclidean
        # return (x1 - x0) ** 2 + (y1 - y0) ** 2

    def grid_index_to_xy(self, gi: int) -> (int, int):
        return gi % self.grid_size, gi // self.grid_size

    def pick_swap_random(self):
        ai = random.randrange(self.grid_area)
        bi = random.randrange(self.grid_area)
        return ai, bi

    def pick_swap_long_wire(self):
        # pick random cell attached to long wire
        # TODO optimize this using priority queue
        wi = np.random.choice(len(self.wire_index_to_cost), p=self.wire_index_to_cost / np.sum(self.wire_index_to_cost))
        # pick random component attached to that wire
        ai = self.component_to_grid_pos[np.random.choice(self.wire_index_to_component_indices[wi])]

        # pick second cell fully randomly
        bi = np.random.randint(self.grid_area)
        return ai, bi

    def pick_swap_directional(self):
        # pick a random component
        ca = random.randrange(len(self.component_to_grid_pos))
        ga = self.component_to_grid_pos[ca]

        # pick second cell in direction of the centroid of all connected components
        sum_x = 0
        sum_y = 0
        sum_n = 0

        for wi in self.component_index_to_wire_indices[ca]:
            for c_other in self.wire_index_to_component_indices[wi]:
                if c_other != ca:
                    x_other, y_other = self.grid_index_to_xy(self.component_to_grid_pos[c_other])
                    sum_x += x_other
                    sum_y += y_other
                    sum_n += 1

        mid_x = sum_x / sum_n
        mid_y = sum_y / sum_n

        variance = self.grid_size / 10

        pick_x = np.clip(int(mid_x + np.random.normal() * variance), 0, self.grid_size - 1)
        pick_y = np.clip(int(mid_y + np.random.normal() * variance), 0, self.grid_size - 1)

        gb = pick_x + pick_y * self.grid_size
        assert self.grid_index_to_xy(gb) == (pick_x, pick_y)

        return ga, gb

    def opt_step(self, temp: float) -> bool:
        ga, gb = self.pick_swap_random()
        # if np.random.uniform() < 0.5:
        #     ga, gb = self.pick_swap_random()
        # else:
        #     ga, gb = self.pick_swap_directional()
        return self.try_swap_cells(ga, gb, temp)


def net_to_place(net: NetList):
    grid = Grid(net)
    # grid.check_validness()
    # print(grid.calc_total_cost())

    os.makedirs("ignored/anneal/steps", exist_ok=True)

    grid.plot()
    plt.title("After 0 steps")
    plt.show(block=False)
    plt.savefig(f"ignored/anneal/steps/after_{0:06}.png")
    plt.close()

    cost = []
    time_taken = []
    success_rate = []
    success_count = 0

    start = time.perf_counter()
    delta_iters = 10_000

    for i in range(10_000):
        success = grid.opt_step(temp=0)
        cost.append(grid.curr_cost)
        time_taken.append(time.perf_counter() - start)

        if success:
            success_count += 1

        if (i + 1) % delta_iters == 0:
            # grid.check_validness()

            success_rate.append(success_count / delta_iters)
            print(f"Opt step {i + 1}: success={success_count / delta_iters}, cost={grid.curr_cost}")
            success_count = 0

            grid.plot()
            plt.title(f"After {i + 1} steps")
            os.makedirs("ignored/anneal/steps", exist_ok=True)
            plt.savefig(f"ignored/anneal/steps/after_{i + 1:06}.png")
            plt.close()

    plt.figure()
    plt.plot(time_taken, cost)
    plt.title("Cost vs time")
    plt.savefig("ignored/anneal/cost_vs_time.png")
    plt.close()

    plt.figure()
    plt.plot(cost)
    plt.title("Cost vs steps")
    plt.savefig("ignored/anneal/cost_vs_steps.png")
    plt.close()

    plt.figure()
    plt.plot(success_rate)
    plt.title("Success rate")
    plt.savefig("ignored/anneal/success_rate.png")
    plt.close()

    grid.plot()
    plt.title("After")
    plt.savefig("ignored/anneal/after.png")
    plt.close()
    # plt.show()

    return grid
