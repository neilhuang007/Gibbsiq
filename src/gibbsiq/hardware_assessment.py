"""Conservative direct-target admissibility checks for an Ising model.

This layer composes assessed interaction-graph facts, deterministic block coloring,
fixed-point sensitivity analysis, and direct target-format bounds. It deliberately
does not estimate physical placement, routing, mixing, latency, energy, or ESS.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from itertools import chain
from typing import Any, Literal, TypeAlias

from gibbsiq.blocks import color_blocks, graph_density
from gibbsiq.hardware import FixedPointSpec, ParameterProvenance, TSUSpec
from gibbsiq.model import IsingModel, finite_float, variable_index
from gibbsiq.quantization import QuantizationAnalysis, analyze_quantization

AssessmentStatus: TypeAlias = Literal["admissible", "inadmissible", "conditional"]
CheckStatus: TypeAlias = Literal["pass", "fail", "not_evaluated"]
CheckValue: TypeAlias = bool | int | float | str | None
QuantizationStatus: TypeAlias = Literal["computed", "failed", "not_evaluated"]
GraphAssessmentBasis: TypeAlias = Literal[
    "logical_interaction_graph",
    "fixed_beta_zero_effective_interaction_graph",
]


@dataclass(frozen=True, slots=True)
class AdmissibilityCheck:
    """One immutable, named target check with its supporting evidence."""

    name: str
    status: CheckStatus
    observed: CheckValue
    limit: CheckValue
    reason: str
    provenance: ParameterProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "observed": self.observed,
            "limit": self.limit,
            "reason": self.reason,
            "provenance": None if self.provenance is None else self.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class GraphFacts:
    """Linear-space facts about the assessed fixed-beta interaction graph."""

    variable_count: int
    edge_count: int
    maximum_degree: int
    mean_degree: float
    degree_histogram: tuple[tuple[int, int], ...]
    connected_component_count: int
    connected_component_sizes: tuple[int, ...]
    density: float
    is_bipartite: bool
    is_complete: bool
    block_count: int
    block_sizes: tuple[int, ...]
    coloring_method: str
    color_count_bound: Literal["exact", "upper_bound"]
    known_chromatic_lower_bound: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_count": self.variable_count,
            "edge_count": self.edge_count,
            "maximum_degree": self.maximum_degree,
            "mean_degree": self.mean_degree,
            "degree_histogram": [
                {"degree": degree, "variable_count": count} for degree, count in self.degree_histogram
            ],
            "connected_component_count": self.connected_component_count,
            "connected_component_sizes": list(self.connected_component_sizes),
            "density": self.density,
            "is_bipartite": self.is_bipartite,
            "is_complete": self.is_complete,
            "block_count": self.block_count,
            "block_sizes": list(self.block_sizes),
            "coloring_method": self.coloring_method,
            "color_count_bound": self.color_count_bound,
            "known_chromatic_lower_bound": self.known_chromatic_lower_bound,
            "coloring_interpretation": (
                "the returned blocks are a constructive legal schedule; deterministic DSATUR "
                "supplies an upper bound, and the count is certified exact only when that "
                "upper bound matches a separately valid lower bound"
            ),
        }


@dataclass(frozen=True, slots=True)
class QuantizationEvidence:
    """Label-free summary of fixed-point and exact small-state evidence."""

    status: QuantizationStatus
    reason: str
    fixed_point: FixedPointSpec | None
    coefficient_count: int
    out_of_range_count: int | None
    nonfinite_effective_count: int | None
    saturation_count: int | None = None
    zeroed_nonzero_count: int | None = None
    maximum_absolute_coefficient_error: float | None = None
    rms_coefficient_error: float | None = None
    state_log_weight_error_bound: float | None = None
    total_variation_upper_bound: float | None = None
    maximum_local_logit_error_bound: float | None = None
    exactly_representable: bool | None = None
    exact_comparison_status: str | None = None
    exact_comparison_reason: str | None = None
    exact_num_states: int | None = None
    exact_total_variation: float | None = None
    exact_kl_target_to_implemented: float | None = None
    exact_kl_implemented_to_target: float | None = None
    exact_maximum_state_probability_error: float | None = None
    exact_maximum_marginal_error: float | None = None
    exact_maximum_pair_correlation_error: float | None = None

    def to_dict(self) -> dict[str, Any]:
        fixed_point = None if self.fixed_point is None else self.fixed_point.to_dict()
        exact_comparison = None
        if self.exact_num_states is not None:
            exact_comparison = {
                "num_states": self.exact_num_states,
                "total_variation": self.exact_total_variation,
                "kl_target_to_implemented": self.exact_kl_target_to_implemented,
                "kl_implemented_to_target": self.exact_kl_implemented_to_target,
                "maximum_state_probability_error": self.exact_maximum_state_probability_error,
                "maximum_marginal_error": self.exact_maximum_marginal_error,
                "maximum_pair_correlation_error": self.exact_maximum_pair_correlation_error,
            }
        return {
            "status": self.status,
            "reason": self.reason,
            "fixed_point": fixed_point,
            "coefficient_count": self.coefficient_count,
            "out_of_range_count": self.out_of_range_count,
            "nonfinite_effective_count": self.nonfinite_effective_count,
            "saturation_count": self.saturation_count,
            "zeroed_nonzero_count": self.zeroed_nonzero_count,
            "maximum_absolute_coefficient_error": self.maximum_absolute_coefficient_error,
            "rms_coefficient_error": self.rms_coefficient_error,
            "state_log_weight_error_bound": self.state_log_weight_error_bound,
            "total_variation_upper_bound": self.total_variation_upper_bound,
            "maximum_local_logit_error_bound": self.maximum_local_logit_error_bound,
            "exactly_representable": self.exactly_representable,
            "exact_comparison_status": self.exact_comparison_status,
            "exact_comparison_reason": self.exact_comparison_reason,
            "exact_comparison": exact_comparison,
            "scope_limit": (
                "beta-scaled coefficient quantization only; no physical topology, routing, "
                "accumulator, nonlinear-response, drift, timing, energy, or latency model"
            ),
        }


@dataclass(frozen=True, slots=True)
class HardwareAssessment:
    """Auditable result of direct fixed-beta target-admissibility checks."""

    status: AssessmentStatus
    target: TSUSpec
    beta: float
    max_exact_variables: int
    graph: GraphFacts
    graph_basis: GraphAssessmentBasis
    logical_edge_count: int
    checks: tuple[AdmissibilityCheck, ...]
    quantization: QuantizationEvidence

    def check(self, name: str) -> AdmissibilityCheck:
        """Return one named check, raising ``KeyError`` when it is absent."""
        for row in self.checks:
            if row.name == name:
                return row
        raise KeyError(name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "hardware-assessment-v2",
            "status": self.status,
            "target": self.target.to_dict(),
            "beta": self.beta,
            "max_exact_variables": self.max_exact_variables,
            "graph": self.graph.to_dict(),
            "graph_basis": self.graph_basis,
            "logical_edge_count": self.logical_edge_count,
            "checks": [row.to_dict() for row in self.checks],
            "quantization": self.quantization.to_dict(),
            "scope": {
                "claim": "direct fixed-beta target admissibility under explicitly supplied facts",
                "temperature_scope": (
                    "one fixed-beta configuration; not a reusable multi-beta schedule certificate"
                ),
                "excluded": [
                    "physical placement and routing",
                    "mixing and equilibrium quality",
                    "ESS per second or joule",
                    "hardware energy and latency",
                    "host-device overhead",
                ],
            },
        }


def _validate_exact_limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"max_exact_variables must be an integer >= 0, got {value!r}")
    return value


def _nonnegative_beta(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"beta must be a finite non-negative number, got {value!r}")
    beta = finite_float(value, name="beta")
    if beta < 0.0:
        raise ValueError(f"beta must be non-negative, got {value!r}")
    return 0.0 if beta == 0.0 else beta


def _fixed_beta_graph_model(
    model: IsingModel,
    beta: float,
) -> tuple[IsingModel, GraphAssessmentBasis]:
    """Return the graph whose structure is required at one fixed beta.

    Only ``beta == 0`` has an audited structural simplification.  At positive
    beta the logical graph remains authoritative even when coefficient
    quantization might later round a coupling to zero.
    """
    if beta != 0.0:
        return model, "logical_interaction_graph"
    return (
        IsingModel(
            variables=model.variables,
            linear={},
            quadratic={},
            offset=0.0,
            source_format="fixed_beta_zero_effective_topology",
            metadata={
                "fixed_beta": 0.0,
                "logical_edge_count": len(model.graph),
                "scope": "structural checks for one beta=0 configuration only",
            },
        ),
        "fixed_beta_zero_effective_interaction_graph",
    )


def _assessed_graph_facts(model: IsingModel) -> GraphFacts:
    variables = model.variables
    count = len(variables)
    edges = model.graph
    index = variable_index(variables)
    neighbors: list[list[int]] = [[] for _ in variables]
    for left, right in edges:
        left_position = index[left]
        right_position = index[right]
        neighbors[left_position].append(right_position)
        neighbors[right_position].append(left_position)

    degrees = [len(row) for row in neighbors]
    histogram = tuple(sorted(Counter(degrees).items()))
    component_sizes: list[int] = []
    colors = [-1] * count
    is_bipartite = True
    for start in range(count):
        if colors[start] != -1:
            continue
        colors[start] = 0
        stack = [start]
        component_size = 0
        while stack:
            position = stack.pop()
            component_size += 1
            expected_neighbor_color = 1 - colors[position]
            for neighbor in neighbors[position]:
                if colors[neighbor] == -1:
                    colors[neighbor] = expected_neighbor_color
                    stack.append(neighbor)
                elif colors[neighbor] != expected_neighbor_color:
                    is_bipartite = False
        component_sizes.append(component_size)

    partition = color_blocks(model)
    edge_count = len(edges)
    possible_edges = count * (count - 1) // 2
    is_complete = edge_count == possible_edges
    if count == 0:
        lower_bound = 0
        method = "deterministic edgeless partition"
        bound_kind: Literal["exact", "upper_bound"] = "exact"
    elif edge_count == 0:
        lower_bound = 1
        method = "deterministic edgeless partition"
        bound_kind = "exact"
    elif is_bipartite:
        lower_bound = 2
        method = "deterministic bipartite coloring"
        bound_kind = "exact"
    else:
        lower_bound = count if is_complete else 3
        method = "deterministic DSATUR"
        bound_kind = "exact" if partition.num_blocks == lower_bound else "upper_bound"

    return GraphFacts(
        variable_count=count,
        edge_count=edge_count,
        maximum_degree=max(degrees, default=0),
        mean_degree=0.0 if count == 0 else math.fsum(degrees) / count,
        degree_histogram=histogram,
        connected_component_count=len(component_sizes),
        connected_component_sizes=tuple(sorted(component_sizes, reverse=True)),
        density=graph_density(model),
        is_bipartite=is_bipartite,
        is_complete=is_complete,
        block_count=partition.num_blocks,
        block_sizes=partition.block_sizes,
        coloring_method=method,
        color_count_bound=bound_kind,
        known_chromatic_lower_bound=lower_bound,
    )


def _provenance(target: TSUSpec, parameter: str) -> ParameterProvenance | None:
    evidence = target.provenance.get(parameter)
    return evidence if isinstance(evidence, ParameterProvenance) else None


def _upper_bound_check(
    *,
    name: str,
    observed: int,
    limit: int | None,
    parameter: str,
    target: TSUSpec,
) -> AdmissibilityCheck:
    if limit is None:
        return AdmissibilityCheck(
            name=name,
            status="not_evaluated",
            observed=observed,
            limit=None,
            reason=f"target does not declare {parameter}",
        )
    passed = observed <= limit
    return AdmissibilityCheck(
        name=name,
        status="pass" if passed else "fail",
        observed=observed,
        limit=limit,
        reason=(
            f"observed {observed} is within declared {parameter}={limit}"
            if passed
            else f"observed {observed} exceeds declared {parameter}={limit}"
        ),
        provenance=_provenance(target, parameter),
    )


def _capacity_check(graph: GraphFacts, target: TSUSpec) -> AdmissibilityCheck:
    """Check logical variable count against an explicit scalar or topology capacity."""
    if target.pbit_capacity is not None:
        return _upper_bound_check(
            name="pbit_capacity",
            observed=graph.variable_count,
            limit=target.pbit_capacity,
            parameter="pbit_capacity",
            target=target,
        )
    if target.topology is None:
        return _upper_bound_check(
            name="pbit_capacity",
            observed=graph.variable_count,
            limit=None,
            parameter="pbit_capacity or topology capacity",
            target=target,
        )

    limit = target.topology.capacity
    passed = graph.variable_count <= limit
    return AdmissibilityCheck(
        name="pbit_capacity",
        status="pass" if passed else "fail",
        observed=graph.variable_count,
        limit=limit,
        reason=(
            f"observed {graph.variable_count} is within declared topology capacity={limit}"
            if passed
            else (f"observed {graph.variable_count} exceeds declared topology capacity={limit}")
        ),
        provenance=_provenance(target, "topology"),
    )


def _accumulator_check(
    model: IsingModel,
    target: TSUSpec,
    *,
    beta: float,
    implemented_effective_model: IsingModel | None,
) -> AdmissibilityCheck | None:
    """Bound every beta-scaled conditional local field against the accumulator.

    For spin ``i``, the exact extrema over all neighbor assignments are
    ``b_i +/- sum_j abs(w_ij)``. Here ``b`` and ``w`` are the implemented
    quantized effective coefficients when a coefficient format is declared,
    or the beta-scaled originals otherwise. If the extrema fit but an input
    contribution is not on the accumulator grid, the result remains conditional:
    this contract does not declare an acceptable accumulator-rounding error.
    """
    fixed_point = target.accumulator_format
    if fixed_point is None:
        return None

    if target.coefficient_format is None:
        accumulator_model = model
        coefficient_scale = beta
        coefficient_semantics = "beta-scaled original"
    elif implemented_effective_model is None:
        return AdmissibilityCheck(
            name="accumulator_format",
            status="not_evaluated",
            observed=None,
            limit=f"[{fixed_point.minimum}, {fixed_point.maximum}]",
            reason=(
                "the implemented quantized effective coefficients are unavailable because "
                "coefficient-format analysis failed"
            ),
            provenance=_provenance(target, "accumulator_format"),
        )
    else:
        accumulator_model = implemented_effective_model
        coefficient_scale = 1.0
        coefficient_semantics = "implemented quantized effective"

    incident: dict[Any, list[float]] = {variable: [] for variable in accumulator_model.variables}
    off_grid = 0
    for variable in accumulator_model.variables:
        effective = coefficient_scale * accumulator_model.linear[variable]
        off_grid += not (effective / fixed_point.step).is_integer()
    for (left, right), coefficient in accumulator_model.quadratic.items():
        effective = coefficient_scale * coefficient
        off_grid += not (effective / fixed_point.step).is_integer()
        incident[left].append(effective)
        incident[right].append(effective)

    lower = math.inf
    upper = -math.inf
    try:
        for variable in accumulator_model.variables:
            center = coefficient_scale * accumulator_model.linear[variable]
            radius = math.fsum(abs(value) for value in incident[variable])
            lower = min(lower, center - radius)
            upper = max(upper, center + radius)
    except OverflowError:
        lower = -math.inf
        upper = math.inf
    if not accumulator_model.variables:
        lower = upper = 0.0

    observed = f"[{lower}, {upper}]"
    limit = f"[{fixed_point.minimum}, {fixed_point.maximum}]"
    provenance = _provenance(target, "accumulator_format")
    if not math.isfinite(lower) or not math.isfinite(upper):
        return AdmissibilityCheck(
            name="accumulator_format",
            status="fail",
            observed=observed,
            limit=limit,
            reason="beta-scaled local-field accumulation has a non-finite bound",
            provenance=provenance,
        )
    if lower < fixed_point.minimum or upper > fixed_point.maximum:
        return AdmissibilityCheck(
            name="accumulator_format",
            status="fail",
            observed=observed,
            limit=limit,
            reason=(
                f"the exact {coefficient_semantics} local-field range exceeds the declared accumulator range"
            ),
            provenance=provenance,
        )

    if off_grid:
        return AdmissibilityCheck(
            name="accumulator_format",
            status="not_evaluated",
            observed=off_grid,
            limit=0,
            reason=(
                f"{off_grid} beta-scaled local-field contribution(s) are not exactly "
                "representable on the accumulator grid, and no acceptable rounding-error "
                "threshold is declared"
            ),
            provenance=provenance,
        )
    return AdmissibilityCheck(
        name="accumulator_format",
        status="pass",
        observed=observed,
        limit=limit,
        reason=(
            f"every exact {coefficient_semantics} local-field extremum fits the declared "
            "accumulator range and every contribution is on its representable grid"
        ),
        provenance=provenance,
    )


def _color_phase_check(graph: GraphFacts, target: TSUSpec) -> AdmissibilityCheck:
    limit = target.max_color_phases
    if limit is None:
        return AdmissibilityCheck(
            name="color_phases",
            status="not_evaluated",
            observed=graph.block_count,
            limit=None,
            reason=(
                "target does not declare max_color_phases; the observed deterministic "
                "color count is retained as schedule evidence"
            ),
        )
    evidence = _provenance(target, "max_color_phases")
    if graph.block_count <= limit:
        return AdmissibilityCheck(
            name="color_phases",
            status="pass",
            observed=graph.block_count,
            limit=limit,
            reason=(
                "the deterministic coloring constructively supplies a legal schedule "
                f"within max_color_phases={limit}"
            ),
            provenance=evidence,
        )
    if graph.known_chromatic_lower_bound > limit:
        return AdmissibilityCheck(
            name="color_phases",
            status="fail",
            observed=graph.block_count,
            limit=limit,
            reason=(
                f"known chromatic lower bound {graph.known_chromatic_lower_bound} exceeds "
                f"max_color_phases={limit}; deterministic coloring used {graph.block_count} phases"
            ),
            provenance=evidence,
        )
    return AdmissibilityCheck(
        name="color_phases",
        status="not_evaluated",
        observed=graph.block_count,
        limit=limit,
        reason=(
            f"deterministic DSATUR upper bound {graph.block_count} exceeds the limit, but "
            f"known lower bound {graph.known_chromatic_lower_bound} does not prove infeasibility"
        ),
        provenance=evidence,
    )


def _effective_range_counts(
    model: IsingModel,
    fixed_point: FixedPointSpec,
    beta: float,
) -> tuple[int, int, int]:
    coefficient_count = len(model.variables) + len(model.quadratic)
    outside = 0
    nonfinite = 0
    coefficients = chain(
        (model.linear[variable] for variable in model.variables),
        model.quadratic.values(),
    )
    for coefficient in coefficients:
        effective = beta * coefficient
        if not math.isfinite(effective):
            nonfinite += 1
            outside += 1
        elif effective < fixed_point.minimum or effective > fixed_point.maximum:
            outside += 1
    return coefficient_count, outside, nonfinite


def _computed_quantization_evidence(
    analysis: QuantizationAnalysis,
    *,
    out_of_range_count: int,
    nonfinite_effective_count: int,
    exact_limit: int,
    variable_count: int,
) -> QuantizationEvidence:
    comparison = analysis.exact_comparison
    exact_reason = analysis.exact_comparison_reason
    if analysis.exact_comparison_status == "not_computed_too_many_variables":
        exact_reason = (
            f"variable_count={variable_count} exceeds max_exact_variables={exact_limit}; "
            "analytic bounds remain available"
        )
    return QuantizationEvidence(
        status="computed",
        reason="fixed-point coefficient analysis completed",
        fixed_point=analysis.fixed_point,
        coefficient_count=len(analysis.coefficients),
        out_of_range_count=out_of_range_count,
        nonfinite_effective_count=nonfinite_effective_count,
        saturation_count=analysis.saturation_count,
        zeroed_nonzero_count=analysis.zeroed_nonzero_count,
        maximum_absolute_coefficient_error=analysis.maximum_absolute_coefficient_error,
        rms_coefficient_error=analysis.rms_coefficient_error,
        state_log_weight_error_bound=analysis.state_log_weight_error_bound,
        total_variation_upper_bound=analysis.total_variation_upper_bound,
        maximum_local_logit_error_bound=analysis.maximum_local_logit_error_bound,
        exactly_representable=analysis.exactly_representable,
        exact_comparison_status=analysis.exact_comparison_status,
        exact_comparison_reason=exact_reason,
        exact_num_states=None if comparison is None else comparison.num_states,
        exact_total_variation=None if comparison is None else comparison.total_variation,
        exact_kl_target_to_implemented=(None if comparison is None else comparison.kl_target_to_implemented),
        exact_kl_implemented_to_target=(None if comparison is None else comparison.kl_implemented_to_target),
        exact_maximum_state_probability_error=(
            None if comparison is None else comparison.maximum_state_probability_error
        ),
        exact_maximum_marginal_error=(None if comparison is None else comparison.maximum_marginal_error),
        exact_maximum_pair_correlation_error=(
            None if comparison is None else comparison.maximum_pair_correlation_error
        ),
    )


def _quantization_check(
    model: IsingModel,
    target: TSUSpec,
    *,
    beta: float,
    max_exact_variables: int,
) -> tuple[AdmissibilityCheck, QuantizationEvidence, IsingModel | None]:
    fixed_point = target.coefficient_format
    if fixed_point is None:
        return (
            AdmissibilityCheck(
                name="coefficient_format",
                status="not_evaluated",
                observed=None,
                limit=None,
                reason="target does not declare coefficient_format",
            ),
            QuantizationEvidence(
                status="not_evaluated",
                reason="target does not declare coefficient_format",
                fixed_point=None,
                coefficient_count=len(model.variables) + len(model.quadratic),
                out_of_range_count=None,
                nonfinite_effective_count=None,
            ),
            None,
        )

    coefficient_count, outside_count, nonfinite_count = _effective_range_counts(
        model,
        fixed_point,
        beta,
    )
    provenance = _provenance(target, "coefficient_format")
    try:
        analysis = analyze_quantization(
            model,
            fixed_point,
            beta=beta,
            max_exact_variables=max_exact_variables,
        )
    except ValueError as error:
        reason = f"fixed-point analysis rejected the effective coefficients: {error}"
        return (
            AdmissibilityCheck(
                name="coefficient_format",
                status="fail",
                observed=outside_count,
                limit=0,
                reason=reason,
                provenance=provenance,
            ),
            QuantizationEvidence(
                status="failed",
                reason=reason,
                fixed_point=fixed_point,
                coefficient_count=coefficient_count,
                out_of_range_count=outside_count,
                nonfinite_effective_count=nonfinite_count,
                saturation_count=(
                    outside_count - nonfinite_count
                    if fixed_point.signed
                    and fixed_point.overflow == "saturate"
                    and outside_count > nonfinite_count
                    else None
                ),
            ),
            None,
        )

    quantization = _computed_quantization_evidence(
        analysis,
        out_of_range_count=outside_count,
        nonfinite_effective_count=nonfinite_count,
        exact_limit=max_exact_variables,
        variable_count=len(model.variables),
    )
    if analysis.saturation_count:
        return (
            AdmissibilityCheck(
                name="coefficient_format",
                status="fail",
                observed=analysis.saturation_count,
                limit=0,
                reason=(
                    f"{analysis.saturation_count} beta-scaled coefficients require "
                    "saturation and are outside the declared fixed-point range"
                ),
                provenance=provenance,
            ),
            quantization,
            analysis.implemented_effective_model,
        )
    if not analysis.exactly_representable:
        return (
            AdmissibilityCheck(
                name="coefficient_format",
                status="not_evaluated",
                observed=analysis.maximum_absolute_coefficient_error,
                limit=None,
                reason=(
                    "all beta-scaled coefficients fit the declared range, but rounding changes "
                    "the model and TSUSpec declares no acceptable quantization or distribution-error "
                    "threshold; inspect the attached analytic and exact-small-state evidence"
                ),
                provenance=provenance,
            ),
            quantization,
            analysis.implemented_effective_model,
        )
    return (
        AdmissibilityCheck(
            name="coefficient_format",
            status="pass",
            observed=0,
            limit=0,
            reason=(
                "every beta-scaled coefficient is represented exactly within the declared "
                f"fixed-point range [{fixed_point.minimum}, {fixed_point.maximum}]"
            ),
            provenance=provenance,
        ),
        quantization,
        analysis.implemented_effective_model,
    )


def assess_target_admissibility(
    model: IsingModel,
    target: TSUSpec,
    *,
    beta: float = 1.0,
    max_exact_variables: int = 16,
) -> HardwareAssessment:
    """Assess direct logical admissibility under explicit target constraints.

    ``admissible`` means every check expressible from ``TSUSpec`` passed.  A
    known capacity, degree, phase, or coefficient-range violation produces
    ``inadmissible``.  Any missing fact or unresolved DSATUR/topology question
    produces ``conditional`` unless a hard failure is already known.

    At exactly ``beta == 0``, structural checks use the certified edgeless
    effective graph while capacity still counts every variable.  This result
    covers only that fixed-beta configuration; it does not certify a schedule
    that later uses positive beta.
    """
    if not isinstance(model, IsingModel):
        raise TypeError(f"model must be IsingModel, got {type(model).__name__}")
    if not isinstance(target, TSUSpec):
        raise TypeError(f"target must be TSUSpec, got {type(target).__name__}")
    canonical_beta = _nonnegative_beta(beta)
    exact_limit = _validate_exact_limit(max_exact_variables)
    graph_model, graph_basis = _fixed_beta_graph_model(model, canonical_beta)
    graph = _assessed_graph_facts(graph_model)

    checks = [
        _capacity_check(graph, target),
        _upper_bound_check(
            name="maximum_degree",
            observed=graph.maximum_degree,
            limit=target.max_degree,
            parameter="max_degree",
            target=target,
        ),
        _color_phase_check(graph, target),
    ]
    quantization_check, quantization, implemented_effective_model = _quantization_check(
        model,
        target,
        beta=canonical_beta,
        max_exact_variables=exact_limit,
    )
    checks.append(quantization_check)
    accumulator_check = _accumulator_check(
        model,
        target,
        beta=canonical_beta,
        implemented_effective_model=implemented_effective_model,
    )
    if accumulator_check is not None:
        checks.append(accumulator_check)
    if graph.edge_count == 0:
        checks.append(
            AdmissibilityCheck(
                name="topology_locality",
                status="pass",
                observed="no interaction edges",
                limit="not required",
                reason=(
                    "the assessed fixed-beta interaction graph is edgeless and requires no "
                    "coupling placement or routing"
                ),
            )
        )
    else:
        if target.topology is None:
            locality_reason = (
                "TSUSpec does not declare a physical topology, allowed-neighbor, placement, "
                "routing, or communication constraints; logical coloring is not physical mapping"
            )
        else:
            locality_reason = (
                "TSUSpec declares a physical topology, but no logical-to-physical placement "
                "or routed-edge association was supplied; topology adjacency alone cannot "
                "certify locality"
            )
        checks.append(
            AdmissibilityCheck(
                name="topology_locality",
                status="not_evaluated",
                observed=f"{graph.edge_count} assessed fixed-beta interaction edges",
                limit=None,
                reason=locality_reason,
            )
        )

    if any(row.status == "fail" for row in checks):
        status: AssessmentStatus = "inadmissible"
    elif any(row.status == "not_evaluated" for row in checks):
        status = "conditional"
    else:
        status = "admissible"
    return HardwareAssessment(
        status=status,
        target=target,
        beta=canonical_beta,
        max_exact_variables=exact_limit,
        graph=graph,
        graph_basis=graph_basis,
        logical_edge_count=len(model.graph),
        checks=tuple(checks),
        quantization=quantization,
    )
