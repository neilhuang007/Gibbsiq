"""Immutable physical-topology declarations for target-aware compilation.

The records in this module describe adjacency only.  They do not perform
placement or routing and do not infer a hardware topology from a logical model.
Grid offsets and explicit graph edges are caller-supplied target facts.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import product
from math import prod
from typing import Any, TypeAlias

GridCoordinate: TypeAlias = tuple[int, ...]
ExplicitEdge: TypeAlias = tuple[int, int]


def _plain_int(value: Any, *, name: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, got {value!r}")
    return value


def _integer_tuple(
    values: Iterable[Any],
    *,
    name: str,
    minimum: int | None = None,
    allow_empty: bool = False,
) -> tuple[int, ...]:
    try:
        canonical = tuple(
            _plain_int(value, name=f"{name}[{index}]", minimum=minimum) for index, value in enumerate(values)
        )
    except TypeError as error:
        raise ValueError(f"{name} must be an iterable of integers") from error
    if not allow_empty and not canonical:
        raise ValueError(f"{name} must contain at least one integer")
    return canonical


@dataclass(frozen=True, slots=True)
class GridTopology:
    """Finite open grid with an explicit origin and undirected neighbor offsets.

    ``shape`` and ``origin`` define the physical cell coordinates.  Every
    offset must have its additive inverse in ``neighbor_offsets`` so the
    declared adjacency is unambiguously undirected.  ``tile_shape`` describes
    an exact rectangular tiling when supplied; every tile dimension must divide
    the corresponding grid dimension.
    """

    shape: tuple[int, ...]
    neighbor_offsets: tuple[tuple[int, ...], ...]
    origin: tuple[int, ...] = ()
    tile_shape: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        shape = _integer_tuple(self.shape, name="shape", minimum=1)
        dimension = len(shape)
        if self.origin:
            origin = _integer_tuple(self.origin, name="origin")
            if len(origin) != dimension:
                raise ValueError(f"origin has dimension {len(origin)} but shape has dimension {dimension}")
        else:
            origin = (0,) * dimension

        try:
            supplied_offsets = tuple(
                _integer_tuple(offset, name=f"neighbor_offsets[{index}]")
                for index, offset in enumerate(self.neighbor_offsets)
            )
        except TypeError as error:
            raise ValueError("neighbor_offsets must be an iterable of integer vectors") from error
        for offset in supplied_offsets:
            if len(offset) != dimension:
                raise ValueError(
                    f"neighbor offset {offset!r} has dimension {len(offset)}; expected {dimension}"
                )
            if all(component == 0 for component in offset):
                raise ValueError("neighbor_offsets cannot contain the zero vector")
        if len(set(supplied_offsets)) != len(supplied_offsets):
            raise ValueError("neighbor_offsets cannot contain duplicates")
        offset_set = set(supplied_offsets)
        missing_inverses = sorted(
            offset for offset in offset_set if tuple(-component for component in offset) not in offset_set
        )
        if missing_inverses:
            raise ValueError(
                "neighbor_offsets must be inversion-symmetric for undirected adjacency; "
                f"missing inverses for {missing_inverses!r}"
            )

        tile_shape = None
        if self.tile_shape is not None:
            tile_shape = _integer_tuple(self.tile_shape, name="tile_shape", minimum=1)
            if len(tile_shape) != dimension:
                raise ValueError(
                    f"tile_shape has dimension {len(tile_shape)} but shape has dimension {dimension}"
                )
            for axis, (length, tile_length) in enumerate(zip(shape, tile_shape, strict=True)):
                if length % tile_length:
                    raise ValueError(f"tile_shape[{axis}]={tile_length} must divide shape[{axis}]={length}")

        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "neighbor_offsets", tuple(sorted(supplied_offsets)))
        object.__setattr__(self, "tile_shape", tile_shape)

    @property
    def kind(self) -> str:
        return "grid"

    @property
    def capacity(self) -> int:
        return prod(self.shape)

    def cells(self) -> tuple[GridCoordinate, ...]:
        """Return cells in deterministic lexicographic grid order."""
        return tuple(
            tuple(self.origin[axis] + local[axis] for axis in range(len(self.shape)))
            for local in product(*(range(length) for length in self.shape))
        )

    def _coordinate(self, value: Sequence[Any], *, name: str) -> GridCoordinate:
        coordinate = _integer_tuple(value, name=name)
        if len(coordinate) != len(self.shape):
            raise ValueError(
                f"{name} has dimension {len(coordinate)} but topology has dimension {len(self.shape)}"
            )
        if any(
            component < lower or component >= lower + length
            for component, lower, length in zip(
                coordinate,
                self.origin,
                self.shape,
                strict=True,
            )
        ):
            raise ValueError(f"{name} {coordinate!r} is outside the declared grid")
        return coordinate

    def neighbors(self, cell: Sequence[Any]) -> tuple[GridCoordinate, ...]:
        canonical = self._coordinate(cell, name="cell")
        rows: list[GridCoordinate] = []
        for offset in self.neighbor_offsets:
            candidate = tuple(canonical[axis] + offset[axis] for axis in range(len(self.shape)))
            if all(
                lower <= component < lower + length
                for component, lower, length in zip(
                    candidate,
                    self.origin,
                    self.shape,
                    strict=True,
                )
            ):
                rows.append(candidate)
        return tuple(sorted(rows))

    def degree(self, cell: Sequence[Any]) -> int:
        return len(self.neighbors(cell))

    @property
    def maximum_degree(self) -> int:
        return max((self.degree(cell) for cell in self.cells()), default=0)

    def allows_edge(self, left: Sequence[Any], right: Sequence[Any]) -> bool:
        canonical_left = self._coordinate(left, name="left")
        canonical_right = self._coordinate(right, name="right")
        displacement = tuple(
            right_component - left_component
            for left_component, right_component in zip(
                canonical_left,
                canonical_right,
                strict=True,
            )
        )
        return displacement in self.neighbor_offsets

    def edges(self) -> tuple[tuple[GridCoordinate, GridCoordinate], ...]:
        rows: set[tuple[GridCoordinate, GridCoordinate]] = set()
        for left in self.cells():
            for right in self.neighbors(left):
                rows.add((left, right) if left < right else (right, left))
        return tuple(sorted(rows))

    def distance(self, left: Sequence[Any], right: Sequence[Any]) -> int | None:
        """Return unweighted shortest-path distance, or ``None`` if disconnected."""
        start = self._coordinate(left, name="left")
        stop = self._coordinate(right, name="right")
        if start == stop:
            return 0
        visited = {start}
        queue: deque[tuple[GridCoordinate, int]] = deque([(start, 0)])
        while queue:
            cell, depth = queue.popleft()
            for neighbor in self.neighbors(cell):
                if neighbor == stop:
                    return depth + 1
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "shape": list(self.shape),
            "origin": list(self.origin),
            "tile_shape": None if self.tile_shape is None else list(self.tile_shape),
            "neighbor_offsets": [list(offset) for offset in self.neighbor_offsets],
        }


@dataclass(frozen=True, slots=True)
class ExplicitTopology:
    """Finite undirected topology over canonical physical node indices."""

    node_count: int
    edges: tuple[ExplicitEdge, ...]
    tile_shape: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        node_count = _plain_int(self.node_count, name="node_count", minimum=1)
        try:
            supplied_edges = tuple(self.edges)
        except TypeError as error:
            raise ValueError("edges must be an iterable of integer pairs") from error
        canonical_edges: list[ExplicitEdge] = []
        for index, edge in enumerate(supplied_edges):
            try:
                edge_tuple = tuple(edge)
            except TypeError as error:
                raise ValueError(f"edges[{index}] must be an integer pair") from error
            if len(edge_tuple) != 2:
                raise ValueError(f"edges[{index}] must contain exactly two node indices")
            left = _plain_int(edge_tuple[0], name=f"edges[{index}][0]", minimum=0)
            right = _plain_int(edge_tuple[1], name=f"edges[{index}][1]", minimum=0)
            if left >= node_count or right >= node_count:
                raise ValueError(
                    f"edges[{index}]={(left, right)!r} references node outside 0..{node_count - 1}"
                )
            if left == right:
                raise ValueError(f"edges[{index}] is a self-loop")
            canonical_edges.append((left, right) if left < right else (right, left))
        if len(set(canonical_edges)) != len(canonical_edges):
            raise ValueError("edges cannot contain duplicate undirected pairs")

        tile_shape = None
        if self.tile_shape is not None:
            tile_shape = _integer_tuple(self.tile_shape, name="tile_shape", minimum=1)
            if prod(tile_shape) != node_count:
                raise ValueError(
                    f"tile_shape capacity {prod(tile_shape)} does not equal node_count={node_count}"
                )

        object.__setattr__(self, "node_count", node_count)
        object.__setattr__(self, "edges", tuple(sorted(canonical_edges)))
        object.__setattr__(self, "tile_shape", tile_shape)

    @property
    def kind(self) -> str:
        return "explicit"

    @property
    def capacity(self) -> int:
        return self.node_count

    def neighbors(self, node: Any) -> tuple[int, ...]:
        canonical = _plain_int(node, name="node", minimum=0)
        if canonical >= self.node_count:
            raise ValueError(f"node {canonical} is outside 0..{self.node_count - 1}")
        rows: list[int] = []
        for left, right in self.edges:
            if left == canonical:
                rows.append(right)
            elif right == canonical:
                rows.append(left)
        return tuple(sorted(rows))

    def degree(self, node: Any) -> int:
        return len(self.neighbors(node))

    @property
    def maximum_degree(self) -> int:
        degrees = [0] * self.node_count
        for left, right in self.edges:
            degrees[left] += 1
            degrees[right] += 1
        return max(degrees, default=0)

    def allows_edge(self, left: Any, right: Any) -> bool:
        canonical_left = _plain_int(left, name="left", minimum=0)
        canonical_right = _plain_int(right, name="right", minimum=0)
        if canonical_left >= self.node_count or canonical_right >= self.node_count:
            raise ValueError("edge endpoint is outside the declared explicit topology")
        if canonical_left == canonical_right:
            return False
        edge = (
            (canonical_left, canonical_right)
            if canonical_left < canonical_right
            else (canonical_right, canonical_left)
        )
        return edge in self.edges

    def distance(self, left: Any, right: Any) -> int | None:
        start = _plain_int(left, name="left", minimum=0)
        stop = _plain_int(right, name="right", minimum=0)
        if start >= self.node_count or stop >= self.node_count:
            raise ValueError("distance endpoint is outside the declared explicit topology")
        if start == stop:
            return 0
        visited = {start}
        queue: deque[tuple[int, int]] = deque([(start, 0)])
        while queue:
            node, depth = queue.popleft()
            for neighbor in self.neighbors(node):
                if neighbor == stop:
                    return depth + 1
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "node_count": self.node_count,
            "tile_shape": None if self.tile_shape is None else list(self.tile_shape),
            "edges": [list(edge) for edge in self.edges],
        }


TopologySpec: TypeAlias = GridTopology | ExplicitTopology
