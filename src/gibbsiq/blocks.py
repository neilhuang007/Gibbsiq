"""Graph-coloring block construction for THRML block-Gibbs sampling.

A block samples in parallel only if its nodes share no coupling, so a proper
vertex coloring of the interaction graph gives legal independent blocks;
fewer colors means fewer sequential sub-steps per sweep.

THRML ships no coloring utility (its own example delegates to networkx
DSATUR). This module colors deterministically: a linear bipartite check
gives the optimal partition for edgeless graphs, chains, grids, trees, and
even cycles; non-bipartite graphs fall back to DSATUR with a lazy heap.

Dense graphs degenerate toward one block per variable; ``num_blocks``,
``block_sizes``, and graph density are recorded in run metadata.
"""

from __future__ import annotations

import functools
import heapq
from collections import deque
from dataclasses import dataclass
from typing import Any

from gibbsiq.model import IsingModel, Variable, exact_label_key, variable_index


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

    Depends only on graph topology (cached), not coefficient values; each
    block lists variables in canonical order.
    """
    blocks, strategy = _color_blocks_cached(model.variables, model.graph)
    return BlockPartition(blocks=blocks, strategy=strategy)


@functools.lru_cache(maxsize=128)
def _color_blocks_cached(
    variables: tuple[Variable, ...], edges: tuple[tuple[Variable, Variable], ...]
) -> tuple[tuple[tuple[Variable, ...], ...], str]:
    """Topology-only cached coloring backend."""
    if not variables:
        return (), "empty-model"
    neighbors = _neighbors_from_edges(variables, edges)
    if not edges:
        return (variables,), "edgeless-single-block"

    colors = _bipartite_coloring(variables, neighbors)
    if colors is None:
        colors = _dsatur_coloring(variables, neighbors)
        strategy = "dsatur-coloring"
    else:
        strategy = "bipartite-coloring"
    return _blocks_from_colors(variables, colors), strategy


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
            # Component start color fixes both sides; neighbor order doesn't matter.
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

    Colors the highest-saturation variable each step, ties broken by degree
    then canonical order. Heap entries are immutable; stale entries are
    discarded on pop.
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
        tuple(variable for variable in variables if colors[variable] == color) for color in range(num_colors)
    )


def validate_partition(model: IsingModel, partition: BlockPartition) -> None:
    """Raise ``ValueError`` unless the partition is a valid coloring.

    Each variable must appear in exactly one block; no block may contain a
    coupled pair.
    """
    empty_blocks = [index for index, block in enumerate(partition.blocks) if not block]
    if empty_blocks:
        raise ValueError(f"partition contains empty blocks at indices {empty_blocks!r}")
    placed = [variable for block in partition.blocks for variable in block]
    placed_blocks: dict[tuple[Any, Any], int] = {}
    for block_position, block in enumerate(partition.blocks):
        for variable in block:
            key = exact_label_key(variable)
            if key in placed_blocks:
                raise ValueError("partition places at least one variable in multiple blocks")
            placed_blocks[key] = block_position
    model_keys = {exact_label_key(variable) for variable in model.variables}
    missing = tuple(
        variable for variable in model.variables if exact_label_key(variable) not in placed_blocks
    )
    extra = tuple(candidate for candidate in placed if exact_label_key(candidate) not in model_keys)
    if missing:
        raise ValueError(f"partition is missing variables {missing!r}")
    if extra:
        raise ValueError(f"partition references unknown variables {extra!r}")

    block_of = {variable: placed_blocks[exact_label_key(variable)] for variable in model.variables}
    for left, right in model.quadratic:
        if block_of[left] == block_of[right]:
            raise ValueError(
                f"coupled variables {left!r} and {right!r} share block {block_of[left]}; "
                "blocks must be independent sets of the interaction graph"
            )
