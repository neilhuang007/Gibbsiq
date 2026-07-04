"""Graph-coloring block construction for THRML block-Gibbs sampling.

THRML updates one block of nodes per sub-step, and a block may only be
sampled in parallel when its nodes share no coupling. A proper vertex
coloring of the interaction graph therefore gives legal independent update
blocks, and fewer colors reduce the sequential sub-steps per sweep.

THRML ships no coloring utility (its own spin-model example delegates to
networkx DSATUR), so this module provides deterministic standard-library
coloring over the IR graph. The implementation first uses a linear
bipartite check, which gives the optimal one- or two-block partition for
edgeless graphs, chains, grids, trees, and even cycles. Non-bipartite graphs
fall back to DSATUR with a lazy priority heap, avoiding the full uncolored-set
scan at every step.

On dense graphs the chromatic number approaches the variable count and the
partition degenerates toward one singleton block per variable; callers
record ``num_blocks``, ``block_sizes``, and graph density in run metadata so
that regime is visible instead of silent.
"""

from __future__ import annotations

import functools
import heapq
from collections import deque
from dataclasses import dataclass
from typing import Any

from gibbsiq.model import IsingModel, Variable, variable_index


@dataclass(frozen=True, slots=True)
class BlockPartition:
    """Deterministic partition of model variables into non-interacting blocks."""

    blocks: tuple[tuple[Variable, ...], ...]
    strategy: str = "dsatur-coloring"

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocks", tuple(tuple(block) for block in self.blocks))

    @property
    def num_blocks(self) -> int:
        return len(self.blocks)

    @property
    def block_sizes(self) -> tuple[int, ...]:
        return tuple(len(block) for block in self.blocks)

    def to_metadata(self) -> dict[str, Any]:
        """Serializable block facts recorded in every THRML run's metadata."""
        return {
            "block_strategy": self.strategy,
            "num_blocks": self.num_blocks,
            "block_sizes": list(self.block_sizes),
        }


def graph_density(model: IsingModel) -> float:
    """Fraction of possible couplings present: ``2|E| / (n * (n - 1))``."""
    count = len(model.variables)
    if count < 2:
        return 0.0
    return 2.0 * len(model.quadratic) / (count * (count - 1))


def color_blocks(model: IsingModel) -> BlockPartition:
    """Color the interaction graph into deterministic independent blocks.

    The partition depends only on graph topology, not coefficient values, so
    repeated calls over the same variable order and edge set share the cached
    coloring. Every block lists its variables in canonical order.
    """
    return BlockPartition(blocks=_color_blocks_cached(model.variables, model.graph))


@functools.lru_cache(maxsize=128)
def _color_blocks_cached(
    variables: tuple[Variable, ...], edges: tuple[tuple[Variable, Variable], ...]
) -> tuple[tuple[Variable, ...], ...]:
    """Topology-only cached coloring backend."""
    if not variables:
        return ()
    neighbors = _neighbors_from_edges(variables, edges)
    if not edges:
        return (variables,)

    colors = _bipartite_coloring(variables, neighbors)
    if colors is None:
        colors = _dsatur_coloring(variables, neighbors)
    return _blocks_from_colors(variables, colors)


def _neighbors_from_edges(
    variables: tuple[Variable, ...], edges: tuple[tuple[Variable, Variable], ...]
) -> dict[Variable, set[Variable]]:
    neighbors: dict[Variable, set[Variable]] = {variable: set() for variable in variables}
    for left, right in edges:
        neighbors[left].add(right)
        neighbors[right].add(left)
    return neighbors


def _bipartite_coloring(
    variables: tuple[Variable, ...], neighbors: dict[Variable, set[Variable]]
) -> dict[Variable, int] | None:
    """Return a deterministic two-coloring, or ``None`` for non-bipartite graphs."""
    colors: dict[Variable, int] = {}
    for start in variables:
        if start in colors:
            continue
        colors[start] = 0
        queue: deque[Variable] = deque([start])
        while queue:
            variable = queue.popleft()
            neighbor_color = 1 - colors[variable]
            # Once a component's start color is fixed, neighbor order cannot
            # change the two sides of a bipartite component.
            for neighbor in neighbors[variable]:
                if neighbor not in colors:
                    colors[neighbor] = neighbor_color
                    queue.append(neighbor)
                elif colors[neighbor] != neighbor_color:
                    return None
    return colors


def _dsatur_coloring(
    variables: tuple[Variable, ...], neighbors: dict[Variable, set[Variable]]
) -> dict[Variable, int]:
    """DSATUR coloring with lazy heap priorities.

    Each step colors the uncolored variable with the highest saturation
    (count of distinct colors among its neighbors), breaking ties by higher
    degree and then by canonical variable order. Heap entries are immutable,
    so changed priorities create new entries and stale entries are discarded
    when popped.
    """
    index = variable_index(variables)
    colors: dict[Variable, int] = {}
    neighbor_colors: dict[Variable, set[int]] = {variable: set() for variable in variables}
    uncolored = set(variables)
    heap: list[tuple[int, int, int, Variable]] = [
        (0, -len(neighbors[variable]), index[variable], variable) for variable in variables
    ]
    heapq.heapify(heap)

    while uncolored:
        saturation, negative_degree, position, variable = heapq.heappop(heap)
        if variable not in uncolored:
            continue
        current_priority = (-len(neighbor_colors[variable]), -len(neighbors[variable]), index[variable])
        if (saturation, negative_degree, position) != current_priority:
            continue

        used = neighbor_colors[variable]
        color = 0
        while color in used:
            color += 1
        colors[variable] = color
        uncolored.remove(variable)

        for neighbor in neighbors[variable]:
            if neighbor in uncolored and color not in neighbor_colors[neighbor]:
                neighbor_colors[neighbor].add(color)
                heapq.heappush(
                    heap,
                    (
                        -len(neighbor_colors[neighbor]),
                        -len(neighbors[neighbor]),
                        index[neighbor],
                        neighbor,
                    ),
                )
    return colors


def _blocks_from_colors(
    variables: tuple[Variable, ...], colors: dict[Variable, int]
) -> tuple[tuple[Variable, ...], ...]:
    num_colors = max(colors.values()) + 1 if colors else 0
    return tuple(
        tuple(variable for variable in variables if colors[variable] == color)
        for color in range(num_colors)
    )


def validate_partition(model: IsingModel, partition: BlockPartition) -> None:
    """Raise ``ValueError`` unless the partition is a valid coloring of the model.

    Every variable must appear in exactly one block, and no block may contain
    two variables joined by a nonzero coupling.
    """
    placed = [variable for block in partition.blocks for variable in block]
    if len(placed) != len(set(placed)):
        raise ValueError("partition places at least one variable in multiple blocks")
    missing = set(model.variables) - set(placed)
    extra = set(placed) - set(model.variables)
    if missing:
        raise ValueError(f"partition is missing variables {sorted(missing, key=repr)!r}")
    if extra:
        raise ValueError(f"partition references unknown variables {sorted(extra, key=repr)!r}")

    block_of = {variable: position for position, block in enumerate(partition.blocks) for variable in block}
    for left, right in model.quadratic:
        if block_of[left] == block_of[right]:
            raise ValueError(
                f"coupled variables {left!r} and {right!r} share block {block_of[left]}; "
                "blocks must be independent sets of the interaction graph"
            )
