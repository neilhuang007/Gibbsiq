"""Graph-coloring block construction for THRML block-Gibbs sampling.

THRML updates one block of nodes per sub-step, and a block may only be
sampled in parallel when its nodes share no coupling. A proper coloring of
the interaction graph therefore yields the block partition with the fewest
sequential sub-steps per sweep. THRML ships no coloring utility (its own
spin-model example delegates to networkx DSATUR), so this module provides a
deterministic DSATUR coloring over the IR graph using only the standard
library. DSATUR colors bipartite graphs optimally with two colors, which
covers the chains, grids, and even cycles common in QUBO encodings.

On dense graphs the chromatic number approaches the variable count and the
partition degenerates toward one singleton block per variable; callers
record ``num_blocks``, ``block_sizes``, and graph density in run metadata so
that regime is visible instead of silent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gibbsiq.model import IsingModel, Variable


@dataclass(frozen=True)
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
    """DSATUR coloring of the interaction graph.

    Each step colors the uncolored variable with the highest saturation
    (count of distinct colors among its neighbors), breaking ties by higher
    degree and then by canonical variable order, so the partition is a pure
    function of the model. Every block lists its variables in canonical order.
    """
    index = {variable: position for position, variable in enumerate(model.variables)}
    neighbors: dict[Variable, set[Variable]] = {variable: set() for variable in model.variables}
    for left, right in model.quadratic:
        neighbors[left].add(right)
        neighbors[right].add(left)

    colors: dict[Variable, int] = {}
    neighbor_colors: dict[Variable, set[int]] = {variable: set() for variable in model.variables}
    uncolored = set(model.variables)
    while uncolored:
        variable = min(
            uncolored,
            key=lambda candidate: (
                -len(neighbor_colors[candidate]),
                -len(neighbors[candidate]),
                index[candidate],
            ),
        )
        used = neighbor_colors[variable]
        color = 0
        while color in used:
            color += 1
        colors[variable] = color
        uncolored.remove(variable)
        for neighbor in neighbors[variable]:
            neighbor_colors[neighbor].add(color)

    num_colors = max(colors.values()) + 1 if colors else 0
    blocks = tuple(
        tuple(variable for variable in model.variables if colors[variable] == color)
        for color in range(num_colors)
    )
    return BlockPartition(blocks=blocks)


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
