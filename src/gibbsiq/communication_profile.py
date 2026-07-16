"""Paper-grounded communication costs for supplied Ising partitions on a chain.

This module evaluates a partition and a physical chain mapping.  It deliberately
does not partition the graph, place individual variables, or predict physical TSU
performance.  The equations follow Aadit et al. 2026, arXiv:2606.25313v1,
Supplementary Sections S4-S5, with the directed-boundary ambiguity made explicit.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Literal, TypeAlias

from gibbsiq.model import (
    IsingModel,
    Variable,
    exact_label_key,
    finite_float,
    finite_sum,
    variable_sort_key,
)

PartitionLabel: TypeAlias = Any
BoundaryCollapsePolicy: TypeAlias = Literal["max_directed"]
ProxyFrequencyStatus: TypeAlias = Literal[
    "computed_algebraic_proxy",
    "inactive_no_boundary_traffic",
]

AADIT_SOURCE = "Aadit et al. 2026, arXiv:2606.25313v1, Supplementary Sections S4-S5"
BOUNDARY_COLLAPSE_POLICY: BoundaryCollapsePolicy = "max_directed"
MAX_EXACT_CHAIN_PARTITIONS = 6


def _json_safe_label(value: Any) -> Any:
    """Return a JSON-shaped audit representation without changing in-memory labels."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    if isinstance(value, tuple):
        return [_json_safe_label(child) for child in value]
    cls = type(value)
    return {
        "type": f"{cls.__module__}.{cls.__qualname__}",
        "repr": repr(value),
    }


def _positive_integer(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")
    return value


def _positive_float(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite positive number, got {value!r}")
    canonical = finite_float(value, name=name)
    if canonical <= 0.0:
        raise ValueError(f"{name} must be positive, got {value!r}")
    return canonical


def _canonical_labels(labels: Iterable[PartitionLabel]) -> tuple[PartitionLabel, ...]:
    return tuple(sorted(labels, key=variable_sort_key))


def _canonical_partition_labels(
    labels: Iterable[PartitionLabel],
) -> tuple[PartitionLabel, ...]:
    canonical = _canonical_labels(labels)
    seen_keys: set[tuple[str, str, str]] = set()
    for label in canonical:
        key = variable_sort_key(label)
        if key in seen_keys:
            raise ValueError(
                f"distinct partition labels must not share the same canonical sort key; collision at {key!r}"
            )
        seen_keys.add(key)
    return canonical


def _label_order_key(order: Sequence[PartitionLabel]) -> tuple[tuple[str, str, str], ...]:
    return tuple(variable_sort_key(label) for label in order)


@dataclass(frozen=True, slots=True)
class _PreparedPartition:
    labels: tuple[PartitionLabel, ...]
    members: Mapping[PartitionLabel, tuple[Variable, ...]]
    assignment: Mapping[Variable, PartitionLabel]


def _prepare_partition(
    model: IsingModel,
    partitions: Mapping[PartitionLabel, Iterable[Variable]],
) -> _PreparedPartition:
    if not isinstance(model, IsingModel):
        raise TypeError(f"model must be IsingModel, got {type(model).__name__}")
    if not isinstance(partitions, Mapping) or not partitions:
        raise ValueError("partitions must be a non-empty mapping")

    members: dict[PartitionLabel, tuple[Variable, ...]] = {}
    assignment: dict[Variable, PartitionLabel] = {}
    for label, raw_members in partitions.items():
        try:
            cluster_members = tuple(raw_members)
        except TypeError as error:
            raise ValueError(f"partition {label!r} members must be iterable") from error
        if not cluster_members:
            raise ValueError(f"partition {label!r} must not be empty")
        members[label] = cluster_members
        local_seen: set[Variable] = set()
        for variable in cluster_members:
            try:
                repeated_locally = variable in local_seen
                repeated_globally = variable in assignment
            except TypeError as error:
                raise ValueError(f"partition variable {variable!r} must be hashable") from error
            if repeated_locally:
                raise ValueError(f"partition {label!r} repeats variable {variable!r}")
            if repeated_globally:
                raise ValueError(
                    f"variable {variable!r} appears in both partition {assignment[variable]!r} and {label!r}"
                )
            local_seen.add(variable)
            assignment[variable] = label

    model_positions = {
        exact_label_key(variable): position for position, variable in enumerate(model.variables)
    }
    try:
        supplied_positions = {variable: model_positions[exact_label_key(variable)] for variable in assignment}
    except (KeyError, TypeError) as error:
        raise ValueError("partitions must cover model variables exactly without equality aliases") from error
    if len(set(supplied_positions.values())) != len(model.variables):
        raise ValueError("partitions must cover model variables exactly without equality aliases")

    canonical_members = {
        label: tuple(model.variables[supplied_positions[variable]] for variable in cluster_members)
        for label, cluster_members in members.items()
    }
    canonical_assignment = {
        model.variables[position]: assignment[variable] for variable, position in supplied_positions.items()
    }

    return _PreparedPartition(
        labels=_canonical_partition_labels(members),
        members=canonical_members,
        assignment=canonical_assignment,
    )


def _validate_chain_order(
    order: Sequence[PartitionLabel],
    labels: tuple[PartitionLabel, ...],
) -> tuple[PartitionLabel, ...]:
    canonical = tuple(order)
    label_positions = {exact_label_key(label): position for position, label in enumerate(labels)}
    matched_positions: set[int] = set()
    for candidate in canonical:
        try:
            position = label_positions[exact_label_key(candidate)]
        except (KeyError, TypeError):
            raise ValueError("chain_order must contain every partition label exactly once") from None
        if position in matched_positions:
            raise ValueError("chain_order must contain every partition label exactly once")
        matched_positions.add(position)
    if len(matched_positions) != len(labels):
        raise ValueError("chain_order must contain every partition label exactly once")
    return canonical


def _validate_link_pins(
    link_usable_pins: Sequence[int],
    *,
    partition_count: int,
) -> tuple[int, ...]:
    pins = tuple(link_usable_pins)
    expected = max(0, partition_count - 1)
    if len(pins) != expected:
        raise ValueError(
            f"link_usable_pins must contain {expected} entries for a {partition_count}-slot chain"
        )
    return tuple(
        _positive_integer(value, name=f"link_usable_pins[{index}]") for index, value in enumerate(pins)
    )


def _directed_boundary_sets(
    model: IsingModel,
    assignment: Mapping[Variable, PartitionLabel],
) -> dict[tuple[PartitionLabel, PartitionLabel], set[Variable]]:
    directed: dict[tuple[PartitionLabel, PartitionLabel], set[Variable]] = {}
    for left, right in model.graph:
        left_partition = assignment[left]
        right_partition = assignment[right]
        if left_partition == right_partition:
            continue
        directed.setdefault((left_partition, right_partition), set()).add(left)
        directed.setdefault((right_partition, left_partition), set()).add(right)
    return directed


def _pair_demands(
    labels: tuple[PartitionLabel, ...],
    directed: Mapping[tuple[PartitionLabel, PartitionLabel], set[Variable]],
) -> tuple[tuple[PartitionLabel, PartitionLabel, int, int, int], ...]:
    positions = {label: index for index, label in enumerate(labels)}
    active_pairs: set[tuple[PartitionLabel, PartitionLabel]] = set()
    for source, target in directed:
        if positions[source] < positions[target]:
            active_pairs.add((source, target))
        else:
            active_pairs.add((target, source))

    rows: list[tuple[PartitionLabel, PartitionLabel, int, int, int]] = []
    for partition_a, partition_b in sorted(
        active_pairs,
        key=lambda pair: (positions[pair[0]], positions[pair[1]]),
    ):
        a_to_b = len(directed[(partition_a, partition_b)])
        b_to_a = len(directed[(partition_b, partition_a)])
        rows.append((partition_a, partition_b, a_to_b, b_to_a, max(a_to_b, b_to_a)))
    return tuple(rows)


def _route_span(
    positions: Mapping[PartitionLabel, int],
    pins: tuple[int, ...],
    partition_a: PartitionLabel,
    partition_b: PartitionLabel,
) -> tuple[int, int, int, int]:
    left = min(positions[partition_a], positions[partition_b])
    right = max(positions[partition_a], positions[partition_b])
    if left == right:
        raise ValueError("distinct partitions cannot occupy the same physical chain slot")
    return left, right, right - left, min(pins[index] for index in range(left, right))


def _route(
    positions: Mapping[PartitionLabel, int],
    pins: tuple[int, ...],
    partition_a: PartitionLabel,
    partition_b: PartitionLabel,
) -> tuple[int, tuple[int, ...], int]:
    left, right, distance, bottleneck = _route_span(
        positions,
        pins,
        partition_a,
        partition_b,
    )
    return distance, tuple(range(left, right)), bottleneck


def _objective_fractions(
    order: tuple[PartitionLabel, ...],
    pins: tuple[int, ...],
    pair_demands: tuple[tuple[PartitionLabel, PartitionLabel, int, int, int], ...],
) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    positions = {label: index for index, label in enumerate(order)}
    costs: list[Fraction] = []
    link_boundary_bits = [0] * len(pins)
    for partition_a, partition_b, _, _, boundary_count in pair_demands:
        left, right, distance, bottleneck = _route_span(
            positions,
            pins,
            partition_a,
            partition_b,
        )
        costs.append(Fraction(boundary_count * distance, bottleneck))
        for link_index in range(left, right):
            link_boundary_bits[link_index] += boundary_count
    link_loads = [
        Fraction(boundary_bits, pins[index]) for index, boundary_bits in enumerate(link_boundary_bits)
    ]
    c_max = max(costs, default=Fraction(0))
    c_tot = sum(costs, start=Fraction(0))
    max_link_load = max(link_loads, default=Fraction(0))
    composite = max(c_max, max_link_load)
    return composite, max_link_load, c_max, c_tot


def _finite_fraction(value: Fraction, *, name: str) -> float:
    try:
        converted = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} exceeds the finite binary64 reporting domain") from error
    canonical = finite_float(converted, name=name)
    if value > 0 and canonical == 0.0:
        raise ValueError(f"positive {name} underflowed the finite binary64 reporting domain")
    return canonical


def _clock_proxies(
    exact_work: Fraction,
    *,
    colors: int,
    communication_frequency_hz: float,
    name: str,
) -> tuple[float, float, float | None, ProxyFrequencyStatus]:
    if exact_work == 0:
        return 0.0, 0.0, None, "inactive_no_boundary_traffic"
    exact_eta = 2 * colors * exact_work
    exact_tau = exact_eta / Fraction.from_float(communication_frequency_hz)
    exact_frequency = Fraction.from_float(communication_frequency_hz) / exact_eta
    return (
        _finite_fraction(exact_tau, name=f"{name} timing proxy"),
        _finite_fraction(exact_eta, name=f"{name} frequency-ratio proxy"),
        _finite_fraction(exact_frequency, name=f"{name} p-bit-frequency proxy"),
        "computed_algebraic_proxy",
    )


@dataclass(frozen=True, slots=True)
class PartitionTrafficSummary:
    partition: PartitionLabel
    vertex_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition": _json_safe_label(self.partition),
            "vertex_count": self.vertex_count,
        }


@dataclass(frozen=True, slots=True)
class PairCommunicationCost:
    """One active unordered cluster pair and the paper's pair-route proxy."""

    partition_a: PartitionLabel
    partition_b: PartitionLabel
    b_a_to_b: int
    b_b_to_a: int
    b_ab: int
    boundary_collapse_policy: BoundaryCollapsePolicy
    position_a: int
    position_b: int
    d_ab: int
    route_link_indices: tuple[int, ...]
    p_ab: int
    c_ab: float
    paper_pair_tau_proxy_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "partition_a": _json_safe_label(self.partition_a),
            "partition_b": _json_safe_label(self.partition_b),
            "b_a_to_b": self.b_a_to_b,
            "b_b_to_a": self.b_b_to_a,
            "b_ab": self.b_ab,
            "boundary_collapse_policy": self.boundary_collapse_policy,
            "position_a": self.position_a,
            "position_b": self.position_b,
            "d_ab": self.d_ab,
            "route_link_indices": list(self.route_link_indices),
            "p_ab": self.p_ab,
            "c_ab": self.c_ab,
            "paper_pair_tau_proxy_seconds": self.paper_pair_tau_proxy_seconds,
        }


@dataclass(frozen=True, slots=True)
class LinkAggregateLoad:
    """Exact shared-link load under the declared boundary-collapse accounting rule."""

    link_index: int
    left_partition: PartitionLabel
    right_partition: PartitionLabel
    usable_pins: int
    crossing_active_pair_count: int
    aggregate_boundary_bits: int
    normalized_load: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_index": self.link_index,
            "left_partition": _json_safe_label(self.left_partition),
            "right_partition": _json_safe_label(self.right_partition),
            "usable_pins": self.usable_pins,
            "crossing_active_pair_count": self.crossing_active_pair_count,
            "aggregate_boundary_bits": self.aggregate_boundary_bits,
            "normalized_load": self.normalized_load,
        }


@dataclass(frozen=True, slots=True)
class ChainCommunicationProfile:
    """Pair-route and aggregate-link proxies for one supplied chain mapping."""

    partition_summaries: tuple[PartitionTrafficSummary, ...]
    chain_order: tuple[PartitionLabel, ...]
    link_usable_pins: tuple[int, ...]
    num_colors: int
    communication_frequency_hz: float
    boundary_collapse_policy: BoundaryCollapsePolicy
    possible_unordered_pair_count: int
    active_pair_count: int
    pair_costs: tuple[PairCommunicationCost, ...]
    link_loads: tuple[LinkAggregateLoad, ...]
    paper_pair_c_tot: float
    paper_pair_c_max: float
    paper_worst_pair: tuple[PartitionLabel, PartitionLabel] | None
    max_link_aggregate_load: float
    worst_link_indices: tuple[int, ...]
    paper_pair_tau_proxy_seconds: float
    paper_pair_eta_proxy: float
    paper_pair_frequency_proxy_hz: float | None
    aggregate_link_tau_proxy_seconds: float
    aggregate_link_eta_proxy: float
    composite_work_proxy: float
    composite_tau_proxy_seconds: float
    composite_eta_proxy: float
    composite_frequency_proxy_hz: float | None
    proxy_frequency_status: ProxyFrequencyStatus

    @property
    def has_boundary_traffic(self) -> bool:
        return self.active_pair_count > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": AADIT_SOURCE,
            "scope": "supplied partition and supplied physical chain mapping; no partitioner or node placer",
            "partition_summaries": [row.to_dict() for row in self.partition_summaries],
            "chain_order": [_json_safe_label(label) for label in self.chain_order],
            "link_usable_pins": list(self.link_usable_pins),
            "num_colors": self.num_colors,
            "communication_frequency_hz": self.communication_frequency_hz,
            "boundary_collapse_policy": self.boundary_collapse_policy,
            "boundary_ambiguity": (
                "paper defines unordered b_ab using a directed shipping description; "
                "both directed unique-vertex demands are reported and max_directed is used"
            ),
            "possible_unordered_pair_count": self.possible_unordered_pair_count,
            "active_pair_count": self.active_pair_count,
            "pair_costs": [row.to_dict() for row in self.pair_costs],
            "link_loads": [row.to_dict() for row in self.link_loads],
            "paper_pair_c_tot": self.paper_pair_c_tot,
            "paper_pair_c_max": self.paper_pair_c_max,
            "paper_worst_pair": (
                None
                if self.paper_worst_pair is None
                else [_json_safe_label(label) for label in self.paper_worst_pair]
            ),
            "max_link_aggregate_load": self.max_link_aggregate_load,
            "worst_link_indices": list(self.worst_link_indices),
            "paper_pair_tau_proxy_seconds": self.paper_pair_tau_proxy_seconds,
            "paper_pair_eta_proxy": self.paper_pair_eta_proxy,
            "paper_pair_frequency_proxy_hz": self.paper_pair_frequency_proxy_hz,
            "aggregate_link_tau_proxy_seconds": self.aggregate_link_tau_proxy_seconds,
            "aggregate_link_eta_proxy": self.aggregate_link_eta_proxy,
            "composite_work_proxy": self.composite_work_proxy,
            "composite_tau_proxy_seconds": self.composite_tau_proxy_seconds,
            "composite_eta_proxy": self.composite_eta_proxy,
            "composite_frequency_proxy_hz": self.composite_frequency_proxy_hz,
            "proxy_frequency_status": self.proxy_frequency_status,
            "has_boundary_traffic": self.has_boundary_traffic,
            "interpretation": (
                "paper pair-route and aggregate-link serialization proxies under max_directed "
                "accounting; the composite is their maximum, not measured latency, a feasible "
                "schedule, a hardware-frequency limit, an energy model, a mixing guarantee, "
                "or a partition-quality certificate"
            ),
            "provenance_limit": (
                "caller partition labels and target parameters are retained by reference/value; "
                "this report is not a detached or self-contained TSUSpec provenance artifact"
            ),
        }


def profile_chain_communication(
    model: IsingModel,
    partitions: Mapping[PartitionLabel, Iterable[Variable]],
    *,
    chain_order: Sequence[PartitionLabel],
    link_usable_pins: Sequence[int],
    num_colors: int,
    communication_frequency_hz: float,
) -> ChainCommunicationProfile:
    """Evaluate Aadit S4 costs for a complete supplied partition and chain order."""
    prepared = _prepare_partition(model, partitions)
    order = _validate_chain_order(chain_order, prepared.labels)
    pins = _validate_link_pins(link_usable_pins, partition_count=len(prepared.labels))
    colors = _positive_integer(num_colors, name="num_colors")
    f_comm = _positive_float(communication_frequency_hz, name="communication_frequency_hz")

    directed = _directed_boundary_sets(model, prepared.assignment)
    demands = _pair_demands(prepared.labels, directed)
    positions = {label: index for index, label in enumerate(order)}
    pair_rows: list[PairCommunicationCost] = []
    exact_costs: list[Fraction] = []
    link_boundary_bits = [0] * len(pins)
    link_pair_counts = [0] * len(pins)
    for partition_a, partition_b, a_to_b, b_to_a, boundary_count in demands:
        distance, route_links, bottleneck = _route(
            positions,
            pins,
            partition_a,
            partition_b,
        )
        exact_cost = Fraction(boundary_count * distance, bottleneck)
        c_ab = _finite_fraction(exact_cost, name="pair communication cost")
        tau_ab = _finite_fraction(
            2 * exact_cost / Fraction.from_float(f_comm),
            name="paper pair timing proxy",
        )
        exact_costs.append(exact_cost)
        for link_index in route_links:
            link_boundary_bits[link_index] += boundary_count
            link_pair_counts[link_index] += 1
        pair_rows.append(
            PairCommunicationCost(
                partition_a=partition_a,
                partition_b=partition_b,
                b_a_to_b=a_to_b,
                b_b_to_a=b_to_a,
                b_ab=boundary_count,
                boundary_collapse_policy=BOUNDARY_COLLAPSE_POLICY,
                position_a=positions[partition_a],
                position_b=positions[partition_b],
                d_ab=distance,
                route_link_indices=route_links,
                p_ab=bottleneck,
                c_ab=c_ab,
                paper_pair_tau_proxy_seconds=tau_ab,
            )
        )

    exact_c_tot = sum(exact_costs, start=Fraction(0))
    exact_c_max = max(exact_costs, default=Fraction(0))
    paper_c_tot = _finite_fraction(exact_c_tot, name="paper total pair-route proxy")
    paper_c_max = _finite_fraction(exact_c_max, name="paper maximum pair-route proxy")

    exact_link_loads = tuple(
        Fraction(boundary_bits, pins[index]) for index, boundary_bits in enumerate(link_boundary_bits)
    )
    link_rows = tuple(
        LinkAggregateLoad(
            link_index=index,
            left_partition=order[index],
            right_partition=order[index + 1],
            usable_pins=pins[index],
            crossing_active_pair_count=link_pair_counts[index],
            aggregate_boundary_bits=link_boundary_bits[index],
            normalized_load=_finite_fraction(
                exact_link_loads[index],
                name=f"aggregate load for link {index}",
            ),
        )
        for index in range(len(pins))
    )
    exact_max_link_load = max(exact_link_loads, default=Fraction(0))
    max_link_load = _finite_fraction(
        exact_max_link_load,
        name="maximum aggregate link load",
    )
    exact_composite = max(exact_c_max, exact_max_link_load)
    composite_work = _finite_fraction(exact_composite, name="composite communication-work proxy")

    paper_tau, paper_eta, paper_frequency, _ = _clock_proxies(
        exact_c_max,
        colors=colors,
        communication_frequency_hz=f_comm,
        name="paper pair-route",
    )
    aggregate_tau, aggregate_eta, _, _ = _clock_proxies(
        exact_max_link_load,
        colors=colors,
        communication_frequency_hz=f_comm,
        name="aggregate-link",
    )
    composite_tau, composite_eta, composite_frequency, proxy_status = _clock_proxies(
        exact_composite,
        colors=colors,
        communication_frequency_hz=f_comm,
        name="composite communication-work",
    )

    if exact_c_max == 0:
        paper_worst_pair = None
    else:
        worst_index = exact_costs.index(exact_c_max)
        worst_row = pair_rows[worst_index]
        paper_worst_pair = (worst_row.partition_a, worst_row.partition_b)
    worst_link_indices = tuple(
        index
        for index, load in enumerate(exact_link_loads)
        if exact_max_link_load > 0 and load == exact_max_link_load
    )

    summaries = tuple(
        PartitionTrafficSummary(label, len(prepared.members[label])) for label in prepared.labels
    )
    return ChainCommunicationProfile(
        partition_summaries=summaries,
        chain_order=order,
        link_usable_pins=pins,
        num_colors=colors,
        communication_frequency_hz=f_comm,
        boundary_collapse_policy=BOUNDARY_COLLAPSE_POLICY,
        possible_unordered_pair_count=len(prepared.labels) * (len(prepared.labels) - 1) // 2,
        active_pair_count=len(demands),
        pair_costs=tuple(pair_rows),
        link_loads=link_rows,
        paper_pair_c_tot=paper_c_tot,
        paper_pair_c_max=paper_c_max,
        paper_worst_pair=paper_worst_pair,
        max_link_aggregate_load=max_link_load,
        worst_link_indices=worst_link_indices,
        paper_pair_tau_proxy_seconds=paper_tau,
        paper_pair_eta_proxy=paper_eta,
        paper_pair_frequency_proxy_hz=paper_frequency,
        aggregate_link_tau_proxy_seconds=aggregate_tau,
        aggregate_link_eta_proxy=aggregate_eta,
        composite_work_proxy=composite_work,
        composite_tau_proxy_seconds=composite_tau,
        composite_eta_proxy=composite_eta,
        composite_frequency_proxy_hz=composite_frequency,
        proxy_frequency_status=proxy_status,
    )


@dataclass(frozen=True, slots=True)
class ChainOrderSearchResult:
    """Exact small-K search under the declared composite-proxy objective."""

    profile: ChainCommunicationProfile
    exact_partition_limit: int
    orders_evaluated: int
    reversal_reduction_applied: bool
    search_method: str
    optimality_status: Literal["proven_exact_for_composite_proxy_objective"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.to_dict(),
            "exact_partition_limit": self.exact_partition_limit,
            "orders_evaluated": self.orders_evaluated,
            "reversal_reduction_applied": self.reversal_reduction_applied,
            "search_method": self.search_method,
            "optimality_status": self.optimality_status,
            "objective": [
                "composite_work_proxy",
                "max_link_aggregate_load",
                "paper_pair_c_max",
                "paper_pair_c_tot",
                "canonical_partition_order",
            ],
            "scope_limit": (
                "optimal only for the declared diagnostic proxy over chain permutations of the "
                "supplied partition and pin profile; no communication schedule, graph "
                "partitioning, or node placement was performed"
            ),
        }


def search_optimal_chain_order(
    model: IsingModel,
    partitions: Mapping[PartitionLabel, Iterable[Variable]],
    *,
    link_usable_pins: Sequence[int],
    num_colors: int,
    communication_frequency_hz: float,
    exact_partition_limit: int = MAX_EXACT_CHAIN_PARTITIONS,
) -> ChainOrderSearchResult:
    """Prove the best small permutation under the composite-proxy objective."""
    limit = _positive_integer(exact_partition_limit, name="exact_partition_limit")
    if limit > MAX_EXACT_CHAIN_PARTITIONS:
        raise ValueError(
            f"exact_partition_limit cannot exceed the audited hard limit "
            f"{MAX_EXACT_CHAIN_PARTITIONS}; no heuristic fallback is implemented"
        )
    prepared = _prepare_partition(model, partitions)
    partition_count = len(prepared.labels)
    if partition_count > limit:
        raise ValueError(
            f"exact chain-order search refuses {partition_count} partitions above "
            f"exact_partition_limit={limit}; no unproven heuristic fallback is implemented"
        )
    pins = _validate_link_pins(link_usable_pins, partition_count=partition_count)
    colors = _positive_integer(num_colors, name="num_colors")
    f_comm = _positive_float(communication_frequency_hz, name="communication_frequency_hz")
    directed = _directed_boundary_sets(model, prepared.assignment)
    demands = _pair_demands(prepared.labels, directed)

    reversal_symmetric = partition_count >= 2 and pins == tuple(reversed(pins))
    best_order: tuple[PartitionLabel, ...] | None = None
    best_objective: (
        tuple[
            Fraction,
            Fraction,
            Fraction,
            Fraction,
            tuple[tuple[str, str, str], ...],
        ]
        | None
    ) = None
    orders_evaluated = 0
    for permutation in itertools.permutations(prepared.labels):
        order = tuple(permutation)
        if reversal_symmetric and _label_order_key(order) > _label_order_key(tuple(reversed(order))):
            continue
        composite, max_link_load, c_max, c_tot = _objective_fractions(order, pins, demands)
        objective = (composite, max_link_load, c_max, c_tot, _label_order_key(order))
        orders_evaluated += 1
        if best_objective is None or objective < best_objective:
            best_objective = objective
            best_order = order

    assert best_order is not None
    normalized_partitions = {label: prepared.members[label] for label in prepared.labels}
    profile = profile_chain_communication(
        model,
        normalized_partitions,
        chain_order=best_order,
        link_usable_pins=pins,
        num_colors=colors,
        communication_frequency_hz=f_comm,
    )
    if partition_count == 1:
        method = "exhaustive_single_partition_order"
    elif reversal_symmetric:
        method = "exhaustive_permutations_modulo_valid_chain_reversal"
    else:
        method = "exhaustive_permutations_without_invalid_reversal_reduction"
    return ChainOrderSearchResult(
        profile=profile,
        exact_partition_limit=limit,
        orders_evaluated=orders_evaluated,
        reversal_reduction_applied=reversal_symmetric,
        search_method=method,
        optimality_status="proven_exact_for_composite_proxy_objective",
    )


@dataclass(frozen=True, slots=True)
class PottsObjectiveEvaluation:
    """Equation S.7 value for one supplied assignment; not a partitioner."""

    partition_order: tuple[PartitionLabel, ...]
    partition_summaries: tuple[PartitionTrafficSummary, ...]
    delta_near: float
    delta_far: float
    balance_penalty_lambda: float
    interaction_term: float
    balance_term: float
    total: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": AADIT_SOURCE,
            "equation": "S.7-S.8",
            "scope": "objective evaluation for a supplied assignment; no optimization",
            "partition_order": [_json_safe_label(label) for label in self.partition_order],
            "partition_summaries": [row.to_dict() for row in self.partition_summaries],
            "delta_near": self.delta_near,
            "delta_far": self.delta_far,
            "balance_penalty_lambda": self.balance_penalty_lambda,
            "interaction_term": self.interaction_term,
            "balance_term": self.balance_term,
            "total": self.total,
        }


def evaluate_potts_assignment(
    model: IsingModel,
    partitions: Mapping[PartitionLabel, Iterable[Variable]],
    *,
    partition_order: Sequence[PartitionLabel],
    delta_near: float,
    delta_far: float,
    balance_penalty_lambda: float,
) -> PottsObjectiveEvaluation:
    """Evaluate Aadit equation S.7 for a validated caller-supplied assignment."""
    prepared = _prepare_partition(model, partitions)
    order = _validate_chain_order(partition_order, prepared.labels)
    near = _positive_float(delta_near, name="delta_near")
    far = _positive_float(delta_far, name="delta_far")
    if far <= near:
        raise ValueError("delta_far must be greater than delta_near")
    penalty = _positive_float(balance_penalty_lambda, name="balance_penalty_lambda")
    positions = {label: index for index, label in enumerate(order)}

    interaction_terms: list[float] = []
    for (left, right), coefficient in model.quadratic.items():
        distance = abs(positions[prepared.assignment[left]] - positions[prepared.assignment[right]])
        kernel = 0.0 if distance == 0 else near if distance == 1 else far
        interaction_terms.append(abs(coefficient) * kernel)
    interaction = finite_sum(interaction_terms, name="Potts interaction term")

    target_size = len(model.variables) / len(prepared.labels)
    balance = finite_sum(
        [penalty * (len(prepared.members[label]) - target_size) ** 2 for label in prepared.labels],
        name="Potts balance term",
    )
    total = finite_sum([interaction, balance], name="Potts objective")
    summaries = tuple(
        PartitionTrafficSummary(label, len(prepared.members[label])) for label in prepared.labels
    )
    return PottsObjectiveEvaluation(
        partition_order=order,
        partition_summaries=summaries,
        delta_near=near,
        delta_far=far,
        balance_penalty_lambda=penalty,
        interaction_term=interaction,
        balance_term=balance,
        total=total,
    )
