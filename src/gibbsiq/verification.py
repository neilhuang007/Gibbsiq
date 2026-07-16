"""Independent finite-state verification for small Ising Gibbs programs.

The transition constructor does not call the reference sampler.  It enumerates
the state space and conditional tables directly, then the verifier separately
checks rows, the exact Boltzmann stationary law, reversibility where promised,
and finite-state ergodicity.
"""

from __future__ import annotations

import itertools
import math
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Literal, Sequence

from gibbsiq.blocks import BlockPartition, color_blocks, validate_partition
from gibbsiq.exact_distribution import exact_boltzmann_distribution
from gibbsiq.model import (
    IsingModel,
    Variable,
    exact_variable_order,
    finite_float,
    finite_sum,
    sample_to_spin_values,
)

UpdateSchedule = Literal["random_single_site", "systematic", "blocked"]


def _nonnegative_beta(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"beta must be a finite non-negative number, got {value!r}")
    beta = finite_float(value, name="beta")
    if beta < 0.0:
        raise ValueError(f"beta must be non-negative, got {value!r}")
    return beta


def _limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"max_variables must be an integer >= 0, got {value!r}")
    return value


def _positive_tolerance(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"tolerance must be finite and positive, got {value!r}")
    tolerance = finite_float(value, name="tolerance")
    if tolerance <= 0.0:
        raise ValueError(f"tolerance must be positive, got {value!r}")
    return tolerance


def _stable_probability_up(beta: float, gamma: float) -> float:
    if beta == 0.0:
        return 0.5
    argument = -2.0 * beta * gamma
    if argument == math.inf:
        return 1.0
    if argument == -math.inf:
        return 0.0
    if argument >= 0.0:
        return 1.0 / (1.0 + math.exp(-argument))
    exponential = math.exp(argument)
    return exponential / (1.0 + exponential)


def _direct_probability_up(
    model: IsingModel,
    position: int,
    state: tuple[int, ...],
    beta: float,
) -> float:
    variable = model.variables[position]
    positions = {label: index for index, label in enumerate(model.variables)}
    terms = [model.linear[variable]]
    for (left, right), coefficient in model.quadratic.items():
        if left == variable:
            terms.append(coefficient * state[positions[right]])
        elif right == variable:
            terms.append(coefficient * state[positions[left]])
    gamma = finite_sum(terms, name=f"verification local field for {variable!r}")
    return _stable_probability_up(beta, gamma)


def _identity(size: int) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(1.0 if row == column else 0.0 for column in range(size)) for row in range(size))


def _compose(
    left: tuple[tuple[float, ...], ...],
    right: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    size = len(left)
    return tuple(
        tuple(
            math.fsum(left[row][middle] * right[middle][column] for middle in range(size))
            for column in range(size)
        )
        for row in range(size)
    )


def _single_site_matrix(
    model: IsingModel,
    states: tuple[tuple[int, ...], ...],
    state_index: dict[tuple[int, ...], int],
    beta: float,
    variable_position: int,
) -> tuple[tuple[float, ...], ...]:
    matrix: list[tuple[float, ...]] = []
    for state in states:
        probability_up = _direct_probability_up(model, variable_position, state, beta)
        row = [0.0] * len(states)
        for spin, probability in ((-1, 1.0 - probability_up), (1, probability_up)):
            destination = list(state)
            destination[variable_position] = spin
            row[state_index[tuple(destination)]] += probability
        matrix.append(tuple(row))
    return tuple(matrix)


def _block_matrix(
    model: IsingModel,
    states: tuple[tuple[int, ...], ...],
    state_index: dict[tuple[int, ...], int],
    beta: float,
    positions: tuple[int, ...],
) -> tuple[tuple[float, ...], ...]:
    rows: list[tuple[float, ...]] = []
    for state in states:
        probabilities_up = tuple(
            _direct_probability_up(model, position, state, beta) for position in positions
        )
        row = [0.0] * len(states)
        for assignment in itertools.product((-1, 1), repeat=len(positions)):
            probability = 1.0
            destination = list(state)
            for position, spin, probability_up in zip(
                positions,
                assignment,
                probabilities_up,
            ):
                destination[position] = spin
                probability *= probability_up if spin == 1 else 1.0 - probability_up
            row[state_index[tuple(destination)]] += probability
        rows.append(tuple(row))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class ExactTransitionKernel:
    """A capped, fully enumerated Markov transition kernel."""

    variables: tuple[Variable, ...]
    states: tuple[tuple[int, ...], ...]
    matrix: tuple[tuple[float, ...], ...]
    beta: float
    update_schedule: UpdateSchedule
    blocks: tuple[tuple[Variable, ...], ...]
    detailed_balance_expected: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": list(self.variables),
            "states": [list(state) for state in self.states],
            "matrix": [list(row) for row in self.matrix],
            "beta": self.beta,
            "update_schedule": self.update_schedule,
            "blocks": [list(block) for block in self.blocks],
            "detailed_balance_expected": self.detailed_balance_expected,
        }


def build_exact_transition_kernel(
    model: IsingModel,
    beta: float,
    *,
    update_schedule: UpdateSchedule = "random_single_site",
    blocks: tuple[tuple[Variable, ...], ...] | None = None,
    max_variables: int = 8,
) -> ExactTransitionKernel:
    """Enumerate one scheduled Gibbs step for a small model."""
    if not isinstance(model, IsingModel):
        raise TypeError(f"model must be IsingModel, got {type(model).__name__}")
    canonical_beta = _nonnegative_beta(beta)
    limit = _limit(max_variables)
    if len(model.variables) > limit:
        raise ValueError(
            f"kernel enumeration has {len(model.variables)} variables, exceeding max_variables={limit}"
        )
    if update_schedule not in {"random_single_site", "systematic", "blocked"}:
        raise ValueError(f"unsupported update_schedule {update_schedule!r}")
    if blocks is not None and update_schedule != "blocked":
        raise ValueError("blocks are only valid with update_schedule='blocked'")

    states = tuple(itertools.product((-1, 1), repeat=len(model.variables)))
    state_index = {state: index for index, state in enumerate(states)}
    size = len(states)
    resolved_blocks: tuple[tuple[Variable, ...], ...] = ()
    matrix: tuple[tuple[float, ...], ...]

    if not model.variables:
        matrix = ((1.0,),)
        detailed_balance_expected = True
    elif update_schedule == "random_single_site":
        site_matrices = tuple(
            _single_site_matrix(model, states, state_index, canonical_beta, position)
            for position in range(len(model.variables))
        )
        weight = 1.0 / len(site_matrices)
        matrix = tuple(
            tuple(math.fsum(site[row][column] for site in site_matrices) * weight for column in range(size))
            for row in range(size)
        )
        detailed_balance_expected = True
    elif update_schedule == "systematic":
        matrix = _identity(size)
        for position in range(len(model.variables)):
            matrix = _compose(
                matrix,
                _single_site_matrix(model, states, state_index, canonical_beta, position),
            )
        detailed_balance_expected = len(model.variables) <= 1
    else:
        if blocks is None:
            partition = color_blocks(model)
        else:
            try:
                normalized_blocks = tuple(tuple(block) for block in blocks)
            except TypeError as error:
                raise TypeError("blocks must be an iterable of variable iterables") from error
            partition = BlockPartition(normalized_blocks, strategy="user_supplied")
        validate_partition(model, partition)
        resolved_blocks = partition.blocks
        variable_positions = {variable: position for position, variable in enumerate(model.variables)}
        matrix = _identity(size)
        for block in resolved_blocks:
            matrix = _compose(
                matrix,
                _block_matrix(
                    model,
                    states,
                    state_index,
                    canonical_beta,
                    tuple(variable_positions[variable] for variable in block),
                ),
            )
        detailed_balance_expected = len(resolved_blocks) <= 1

    return ExactTransitionKernel(
        variables=model.variables,
        states=states,
        matrix=matrix,
        beta=canonical_beta,
        update_schedule=update_schedule,
        blocks=resolved_blocks,
        detailed_balance_expected=detailed_balance_expected,
    )


@dataclass(frozen=True, slots=True)
class TransitionVerificationReport:
    """Residual and graph checks against the exact Boltzmann law."""

    variables: tuple[Variable, ...]
    beta: float
    num_states: int
    tolerance: float
    row_residual: float
    stationarity_residual: float
    detailed_balance_residual: float
    row_stochastic_passed: bool
    stationarity_passed: bool
    detailed_balance_expected: bool
    detailed_balance_passed: bool
    detailed_balance_status: str
    irreducible: bool
    aperiodic: bool
    ergodic: bool
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": list(self.variables),
            "beta": self.beta,
            "num_states": self.num_states,
            "tolerance": self.tolerance,
            "row_residual": self.row_residual,
            "stationarity_residual": self.stationarity_residual,
            "detailed_balance_residual": self.detailed_balance_residual,
            "row_stochastic_passed": self.row_stochastic_passed,
            "stationarity_passed": self.stationarity_passed,
            "detailed_balance_expected": self.detailed_balance_expected,
            "detailed_balance_passed": self.detailed_balance_passed,
            "detailed_balance_status": self.detailed_balance_status,
            "irreducible": self.irreducible,
            "aperiodic": self.aperiodic,
            "ergodic": self.ergodic,
            "passed": self.passed,
        }


def _is_strongly_connected(matrix: tuple[tuple[float, ...], ...]) -> bool:
    size = len(matrix)

    def visit(reverse: bool) -> set[int]:
        seen = {0}
        pending = [0]
        while pending:
            source = pending.pop()
            for target in range(size):
                weight = matrix[target][source] if reverse else matrix[source][target]
                if weight > 0.0 and target not in seen:
                    seen.add(target)
                    pending.append(target)
        return seen

    return len(visit(False)) == size and len(visit(True)) == size


def _is_aperiodic(matrix: tuple[tuple[float, ...], ...]) -> bool:
    """Compute a strongly connected finite chain's period by the graph gcd test."""
    size = len(matrix)
    distances = [-1] * size
    distances[0] = 0
    pending: deque[int] = deque([0])
    while pending:
        source = pending.popleft()
        for target, probability in enumerate(matrix[source]):
            if probability > 0.0 and distances[target] < 0:
                distances[target] = distances[source] + 1
                pending.append(target)
    period = 0
    for source, row in enumerate(matrix):
        for target, probability in enumerate(row):
            if probability > 0.0:
                period = math.gcd(
                    period,
                    abs(distances[source] + 1 - distances[target]),
                )
    return period == 1


def _canonical_matrix(
    matrix: Sequence[Sequence[float]],
    expected_size: int,
) -> tuple[tuple[float, ...], ...]:
    try:
        rows = tuple(tuple(row) for row in matrix)
    except TypeError as error:
        raise ValueError("matrix must be a square sequence") from error
    if len(rows) != expected_size or any(len(row) != expected_size for row in rows):
        raise ValueError(f"matrix must have shape ({expected_size}, {expected_size}), got {len(rows)} rows")
    canonical: list[tuple[float, ...]] = []
    for row_index, row in enumerate(rows):
        values: list[float] = []
        for column_index, value in enumerate(row):
            if isinstance(value, bool):
                raise ValueError(f"matrix[{row_index}][{column_index}] must be finite, got {value!r}")
            values.append(finite_float(value, name=f"matrix[{row_index}][{column_index}]"))
        canonical.append(tuple(values))
    return tuple(canonical)


def verify_transition_matrix(
    model: IsingModel,
    beta: float,
    matrix: Sequence[Sequence[float]],
    *,
    states: Sequence[Sequence[int]] | None = None,
    detailed_balance_expected: bool = True,
    tolerance: float = 1e-12,
    max_variables: int = 8,
) -> TransitionVerificationReport:
    """Check a finite kernel without trusting its construction path."""
    if not isinstance(model, IsingModel):
        raise TypeError(f"model must be IsingModel, got {type(model).__name__}")
    canonical_beta = _nonnegative_beta(beta)
    canonical_tolerance = _positive_tolerance(tolerance)
    limit = _limit(max_variables)
    target = exact_boltzmann_distribution(model, canonical_beta, max_variables=limit)
    if states is None:
        ordered_states = target.states
    else:
        try:
            ordered_states = tuple(tuple(state) for state in states)
        except TypeError as error:
            raise ValueError("states must be a complete sequence of spin states") from error
        for state_index, state in enumerate(ordered_states):
            if len(state) != len(model.variables):
                raise ValueError(f"states[{state_index}] must contain {len(model.variables)} spins")
            for spin_index, spin in enumerate(state):
                if type(spin) is not int or spin not in (-1, 1):
                    raise ValueError(f"states[{state_index}][{spin_index}] must be plain int -1 or +1")
        if len(ordered_states) != len(target.states) or set(ordered_states) != set(target.states):
            raise ValueError("states must be a permutation of the complete enumerated state space")
    if not isinstance(detailed_balance_expected, bool):
        raise ValueError("detailed_balance_expected must be bool")
    canonical_matrix = _canonical_matrix(matrix, len(ordered_states))

    target_by_state = dict(zip(target.states, target.probabilities))
    stationary = tuple(target_by_state[state] for state in ordered_states)
    row_sum_residual = max(
        (abs(math.fsum(row) - 1.0) for row in canonical_matrix),
        default=0.0,
    )
    negative_residual = max(
        (max(0.0, -value) for row in canonical_matrix for value in row),
        default=0.0,
    )
    row_residual = max(row_sum_residual, negative_residual)
    stationarity_residual = max(
        (
            abs(
                math.fsum(
                    stationary[source] * canonical_matrix[source][target_index]
                    for source in range(len(ordered_states))
                )
                - stationary[target_index]
            )
            for target_index in range(len(ordered_states))
        ),
        default=0.0,
    )
    detailed_balance_residual = max(
        (
            abs(
                stationary[source] * canonical_matrix[source][destination]
                - stationary[destination] * canonical_matrix[destination][source]
            )
            for source in range(len(ordered_states))
            for destination in range(len(ordered_states))
        ),
        default=0.0,
    )
    row_stochastic_passed = row_residual <= canonical_tolerance
    stationarity_passed = stationarity_residual <= canonical_tolerance
    detailed_balance_passed = detailed_balance_residual <= canonical_tolerance
    if detailed_balance_expected:
        detailed_balance_status = "pass" if detailed_balance_passed else "fail"
    else:
        detailed_balance_status = "not_required_non_reversible_schedule"

    nonnegative_matrix = tuple(
        tuple(value if value > 0.0 else 0.0 for value in row) for row in canonical_matrix
    )
    irreducible = row_stochastic_passed and _is_strongly_connected(nonnegative_matrix)
    aperiodic = irreducible and _is_aperiodic(nonnegative_matrix)
    ergodic = irreducible and aperiodic
    passed = (
        row_stochastic_passed
        and stationarity_passed
        and ergodic
        and (detailed_balance_passed or not detailed_balance_expected)
    )
    return TransitionVerificationReport(
        variables=model.variables,
        beta=canonical_beta,
        num_states=len(ordered_states),
        tolerance=canonical_tolerance,
        row_residual=row_residual,
        stationarity_residual=stationarity_residual,
        detailed_balance_residual=detailed_balance_residual,
        row_stochastic_passed=row_stochastic_passed,
        stationarity_passed=stationarity_passed,
        detailed_balance_expected=bool(detailed_balance_expected),
        detailed_balance_passed=detailed_balance_passed,
        detailed_balance_status=detailed_balance_status,
        irreducible=irreducible,
        aperiodic=aperiodic,
        ergodic=ergodic,
        passed=passed,
    )


def verify_transition_kernel(
    model: IsingModel,
    beta: float,
    kernel: ExactTransitionKernel,
    *,
    tolerance: float = 1e-12,
    max_variables: int = 8,
) -> TransitionVerificationReport:
    """Verify kernel provenance, then delegate to the independent matrix checks."""
    if not isinstance(kernel, ExactTransitionKernel):
        raise TypeError("kernel must be ExactTransitionKernel")
    canonical_beta = _nonnegative_beta(beta)
    if not exact_variable_order(kernel.variables, model.variables):
        raise ValueError("kernel variable order does not match model variable order")
    if canonical_beta != kernel.beta:
        raise ValueError(f"kernel beta {kernel.beta!r} does not match requested beta {canonical_beta!r}")
    if kernel.update_schedule == "random_single_site":
        if kernel.blocks:
            raise ValueError("random_single_site kernel must not declare blocks")
        expected_reversibility = True
    elif kernel.update_schedule == "systematic":
        if kernel.blocks:
            raise ValueError("systematic kernel must not declare blocks")
        expected_reversibility = len(model.variables) <= 1
    elif kernel.update_schedule == "blocked":
        partition = BlockPartition(kernel.blocks, strategy="kernel_declared")
        validate_partition(model, partition)
        expected_reversibility = len(kernel.blocks) <= 1
    else:
        raise ValueError(f"unsupported kernel update_schedule {kernel.update_schedule!r}")
    if kernel.detailed_balance_expected != expected_reversibility:
        raise ValueError("kernel detailed_balance_expected disagrees with its update schedule contract")
    return verify_transition_matrix(
        model,
        canonical_beta,
        kernel.matrix,
        states=kernel.states,
        detailed_balance_expected=expected_reversibility,
        tolerance=tolerance,
        max_variables=max_variables,
    )


@dataclass(frozen=True, slots=True)
class EmpiricalInterval:
    """One predeclared bounded-observable simultaneous interval."""

    observable: str
    target: float
    estimate: float
    lower: float
    upper: float
    half_width: float
    covered: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "observable": self.observable,
            "target": self.target,
            "estimate": self.estimate,
            "lower": self.lower,
            "upper": self.upper,
            "half_width": self.half_width,
            "covered": self.covered,
        }


@dataclass(frozen=True, slots=True)
class EmpiricalVerificationReport:
    """Bonferroni-Hoeffding evidence conditional on caller-asserted independence."""

    variables: tuple[Variable, ...]
    beta: float
    sample_count: int
    familywise_confidence: float
    sampling_design: str
    independence_assumption_status: str
    independence_verified: bool
    interval_method: str
    num_comparisons: int
    intervals: tuple[EmpiricalInterval, ...]
    passed: bool

    @property
    def failed_intervals(self) -> tuple[EmpiricalInterval, ...]:
        return tuple(interval for interval in self.intervals if not interval.covered)

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": list(self.variables),
            "beta": self.beta,
            "sample_count": self.sample_count,
            "familywise_confidence": self.familywise_confidence,
            "sampling_design": self.sampling_design,
            "independence_assumption_status": self.independence_assumption_status,
            "independence_verified": self.independence_verified,
            "interval_method": self.interval_method,
            "num_comparisons": self.num_comparisons,
            "intervals": [interval.to_dict() for interval in self.intervals],
            "failed_intervals": [interval.to_dict() for interval in self.failed_intervals],
            "passed": self.passed,
        }


def verify_empirical_distribution(
    model: IsingModel,
    samples: Sequence[dict[Variable, int]],
    beta: float,
    *,
    familywise_confidence: float = 0.99,
    sampling_design: str = "independent_chains",
    max_variables: int = 8,
) -> EmpiricalVerificationReport:
    """Check retained states using predeclared simultaneous intervals.

    The Hoeffding guarantee is conditional on independently initialized and
    independently randomized retained states.  ``sampling_design`` preserves
    the public compatibility gate, but a caller-provided string cannot verify
    how samples were generated, so accepted reports explicitly record the
    independence premise as an unverified caller assertion.
    """
    if not isinstance(model, IsingModel):
        raise TypeError(f"model must be IsingModel, got {type(model).__name__}")
    canonical_beta = _nonnegative_beta(beta)
    if isinstance(familywise_confidence, bool):
        raise ValueError("familywise_confidence must be finite and strictly between 0 and 1")
    confidence = finite_float(familywise_confidence, name="familywise_confidence")
    if not 0.0 < confidence < 1.0:
        raise ValueError("familywise_confidence must be strictly between 0 and 1")
    if sampling_design != "independent_chains":
        raise ValueError(
            "Bonferroni-Hoeffding intervals require independent retained states; "
            "use sampling_design='independent_chains' only for independent restarts"
        )
    limit = _limit(max_variables)
    exact = exact_boltzmann_distribution(model, canonical_beta, max_variables=limit)
    if not samples:
        raise ValueError("empirical verification requires at least one sample")
    spin_samples = tuple(sample_to_spin_values(sample, model.variables, "SPIN") for sample in samples)
    sample_count = len(spin_samples)

    observables: list[tuple[str, float, float, float, float]] = []
    for position in range(len(model.variables)):
        target_value = math.fsum(
            probability
            for state, probability in zip(exact.states, exact.probabilities)
            if state[position] == 1
        )
        estimate = math.fsum(state[position] == 1 for state in spin_samples) / sample_count
        observables.append((f"probability_up:{position}", target_value, estimate, 0.0, 1.0))

    for left_position, right_position in itertools.combinations(
        range(len(model.variables)),
        2,
    ):
        target_value = math.fsum(
            probability * state[left_position] * state[right_position]
            for state, probability in zip(exact.states, exact.probabilities)
        )
        estimate = (
            math.fsum(state[left_position] * state[right_position] for state in spin_samples) / sample_count
        )
        observables.append(
            (
                f"pair_correlation:{left_position},{right_position}",
                target_value,
                estimate,
                -1.0,
                1.0,
            )
        )

    exact_energies = tuple(model.energy(dict(zip(model.variables, state))) for state in exact.states)
    sample_energies = tuple(model.energy(dict(zip(model.variables, state))) for state in spin_samples)
    for energy in sorted(set(exact_energies)):
        target_value = math.fsum(
            probability
            for state_energy, probability in zip(exact_energies, exact.probabilities)
            if state_energy == energy
        )
        estimate = math.fsum(sample_energy == energy for sample_energy in sample_energies) / sample_count
        observables.append((f"energy_probability:{energy!r}", target_value, estimate, 0.0, 1.0))

    # Low-order moments and the energy histogram do not identify a general
    # joint law.  At the supported <=8-variable scale, include one Bernoulli
    # indicator per state so any fixed alternative distribution is visible.
    sample_state_counts = Counter(spin_samples)
    for state_index, (state, target_value) in enumerate(zip(exact.states, exact.probabilities)):
        estimate = sample_state_counts[state] / sample_count
        observables.append(
            (
                f"state_probability:{state_index}:{state!r}",
                target_value,
                estimate,
                0.0,
                1.0,
            )
        )

    num_comparisons = len(observables)
    alpha = 1.0 - confidence
    intervals: list[EmpiricalInterval] = []
    for observable, target_value, estimate, observable_minimum, observable_maximum in observables:
        value_range = observable_maximum - observable_minimum
        half_width = value_range * math.sqrt(math.log(2.0 * num_comparisons / alpha) / (2.0 * sample_count))
        lower = max(observable_minimum, estimate - half_width)
        upper = min(observable_maximum, estimate + half_width)
        intervals.append(
            EmpiricalInterval(
                observable=observable,
                target=target_value,
                estimate=estimate,
                lower=lower,
                upper=upper,
                half_width=half_width,
                covered=lower <= target_value <= upper,
            )
        )

    return EmpiricalVerificationReport(
        variables=model.variables,
        beta=canonical_beta,
        sample_count=sample_count,
        familywise_confidence=confidence,
        sampling_design=sampling_design,
        independence_assumption_status="caller_asserted_unverified",
        independence_verified=False,
        interval_method="bonferroni_hoeffding",
        num_comparisons=num_comparisons,
        intervals=tuple(intervals),
        passed=all(interval.covered for interval in intervals),
    )
