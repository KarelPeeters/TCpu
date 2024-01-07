from typing import TypeVar, List, Callable, Dict, Tuple

T = TypeVar('T')


def canonicalize(connections: List[Tuple[T, T]], prefer: Callable[[T, T], bool] = None) -> Dict[T, T]:
    # for each value, find _some_ value that is better
    better: Dict[T, T] = {}

    for a, b in connections:
        # follow to current best
        if a in better:
            a = better[a]
        if b in better:
            b = better[b]
        assert a not in better and b not in better

        # decide the new best
        if prefer(a, b):
            better[b] = a
        else:
            better[a] = b

    # for each value, find the best value
    best: Dict[T, T] = {}
    for a in better:
        b = better[a]
        while b in better:
            b = better[b]
        best[a] = b

    return best
