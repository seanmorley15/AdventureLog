"""Pure, deterministic route-ordering algorithm.

No I/O, no Django imports, no LLM — nothing in this module does anything but
rearrange indices of a duration matrix that was already computed by OSRM
(`osrm_client.py`). This is by design: per the Trilho blueprint's central
architectural principle, an LLM never computes or invents a geospatial fact,
and this module is the "deterministic algorithm" half of that split.

Algorithm: nearest-neighbor construction for an initial tour, refined with
2-opt local search. Both steps work on directed (possibly asymmetric) costs —
driving duration A->B is not assumed to equal B->A.
"""
from __future__ import annotations


def _path_cost(matrix: list[list[float]], order: list[int]) -> float:
    """Total cost of visiting `order` as a path (not a closed loop)."""
    return sum(matrix[order[i]][order[i + 1]] for i in range(len(order) - 1))


def _nearest_neighbor(
    matrix: list[list[float]], n: int, start: int, end: int | None
) -> list[int]:
    unvisited = set(range(n)) - {start}
    if end is not None:
        unvisited.discard(end)

    order = [start]
    current = start
    while unvisited:
        nxt = min(unvisited, key=lambda j: matrix[current][j])
        order.append(nxt)
        unvisited.remove(nxt)
        current = nxt

    if end is not None:
        order.append(end)
    return order


def _two_opt(
    matrix: list[list[float]], order: list[int], start_is_fixed: bool, end_is_fixed: bool
) -> list[int]:
    """Improve `order` with classic 2-opt segment reversal.

    The reversal window excludes a fixed first/last element, so a caller
    that pinned `fixed_start`/`fixed_end` always gets them back unmoved.
    Works with asymmetric matrices: cost is recomputed on the *directed*
    edges of each candidate, never assumed symmetric.
    """
    n = len(order)
    lo = 1 if start_is_fixed else 0
    hi = n - 1 if end_is_fixed else n  # exclusive upper bound for reversal end

    best_cost = _path_cost(matrix, order)
    improved = True
    while improved:
        improved = False
        for i in range(lo, hi - 1):
            for j in range(i + 1, hi):
                candidate = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
                candidate_cost = _path_cost(matrix, candidate)
                if candidate_cost < best_cost:
                    order = candidate
                    best_cost = candidate_cost
                    improved = True
    return order


def optimize_order(
    matrix: list[list[float]],
    fixed_start: int | None = None,
    fixed_end: int | None = None,
) -> list[int]:
    """Return a permutation of `range(len(matrix))` approximating the
    lowest-cost path that visits every stop exactly once, per `matrix`.

    Args:
        matrix: matrix[i][j] is the directed cost (OSRM duration in
            seconds) from stop i to stop j. Not assumed symmetric.
        fixed_start: if given, this stop's index is pinned as the first
            element of the returned order (e.g. "start from the hotel").
        fixed_end: if given, this stop's index is pinned as the last
            element of the returned order.

    Returns:
        A list of the same length as `matrix`, containing each index in
        `range(len(matrix))` exactly once.

    Raises:
        ValueError: fixed_start and fixed_end both given and equal (there
            is no valid tour where the same stop is both endpoints unless
            there is exactly one stop).

    Degenerate cases (0, 1 or 2 stops) are returned as the identity order
    unchanged — nothing to optimize.
    """
    n = len(matrix)
    if n <= 2:
        return list(range(n))
    if fixed_start is not None and fixed_start == fixed_end:
        raise ValueError("fixed_start and fixed_end cannot be the same stop")

    start = fixed_start if fixed_start is not None else 0
    order = _nearest_neighbor(matrix, n, start, fixed_end)
    order = _two_opt(matrix, order, fixed_start is not None, fixed_end is not None)
    return order
