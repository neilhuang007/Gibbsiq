"""Exact small-Ising Boltzmann distributions and distribution comparison.

Enumeration uses the canonical positive-energy law ``p(s) proportional to
exp(-beta * E(s))``.  Offsets are intentionally removed before normalization:
they cancel analytically and retaining them can create avoidable overflow.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any

from gibbsiq.model import IsingModel, Variable, exact_variable_order, finite_float, finite_sum


class ExactDistributionNumericalError(ValueError):
    """Exact probabilities require a log range outside binary64."""


def _nonnegative_beta(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite non-negative number, got {value!r}")
    beta = finite_float(value, name=name)
    if beta < 0.0:
        raise ValueError(f"{name} must be non-negative, got {value!r}")
    return beta


def _exact_limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"max_variables must be an integer >= 0, got {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class ExactDistribution:
    """An exactly enumerated state space with binary64 probabilities."""

    variables: tuple[Variable, ...]
    states: tuple[tuple[int, ...], ...]
    probabilities: tuple[float, ...]
    log_probabilities: tuple[float, ...]
    beta: float
    maximum_log_weight: float
    shifted_log_normalizer: float
    underflowed_probability_count: int

    def to_dict(self, *, include_states: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "variables": list(self.variables),
            "beta": self.beta,
            "num_states": len(self.states),
            "maximum_log_weight": self.maximum_log_weight,
            "shifted_log_normalizer": self.shifted_log_normalizer,
            "underflowed_probability_count": self.underflowed_probability_count,
            "normalization": math.fsum(self.probabilities),
            "offset_handling": "interaction energy only; canonical offset cancels in normalization",
        }
        if include_states:
            payload["state_probabilities"] = [
                {
                    "state": list(state),
                    "probability": probability,
                    "log_probability": log_probability,
                }
                for state, probability, log_probability in zip(
                    self.states,
                    self.probabilities,
                    self.log_probabilities,
                )
            ]
        return payload


@dataclass(frozen=True, slots=True)
class SpinMarginalError:
    variable: Variable
    target_probability_up: float
    implemented_probability_up: float
    absolute_error: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable": self.variable,
            "target_probability_up": self.target_probability_up,
            "implemented_probability_up": self.implemented_probability_up,
            "absolute_error": self.absolute_error,
        }


@dataclass(frozen=True, slots=True)
class PairCorrelationError:
    left: Variable
    right: Variable
    target_correlation: float
    implemented_correlation: float
    absolute_error: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "target_correlation": self.target_correlation,
            "implemented_correlation": self.implemented_correlation,
            "absolute_error": self.absolute_error,
        }


@dataclass(frozen=True, slots=True)
class DistributionComparison:
    """Exact difference between two distributions over the same spin variables."""

    variables: tuple[Variable, ...]
    num_states: int
    total_variation: float
    kl_target_to_implemented: float
    kl_implemented_to_target: float
    maximum_state_probability_error: float
    maximum_state_probability_error_state: tuple[int, ...]
    marginal_errors: tuple[SpinMarginalError, ...]
    pair_correlation_errors: tuple[PairCorrelationError, ...]
    target_underflowed_probability_count: int
    implemented_underflowed_probability_count: int

    @property
    def maximum_marginal_error(self) -> float:
        return max((row.absolute_error for row in self.marginal_errors), default=0.0)

    @property
    def maximum_pair_correlation_error(self) -> float:
        return max((row.absolute_error for row in self.pair_correlation_errors), default=0.0)

    def to_dict(self, *, include_observable_rows: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "variables": list(self.variables),
            "num_states": self.num_states,
            "total_variation": self.total_variation,
            "kl_target_to_implemented": self.kl_target_to_implemented,
            "kl_implemented_to_target": self.kl_implemented_to_target,
            "maximum_state_probability_error": self.maximum_state_probability_error,
            "maximum_state_probability_error_state": list(self.maximum_state_probability_error_state),
            "maximum_marginal_error": self.maximum_marginal_error,
            "maximum_pair_correlation_error": self.maximum_pair_correlation_error,
            "target_underflowed_probability_count": self.target_underflowed_probability_count,
            "implemented_underflowed_probability_count": (self.implemented_underflowed_probability_count),
        }
        if include_observable_rows:
            payload["marginal_errors"] = [row.to_dict() for row in self.marginal_errors]
            payload["pair_correlation_errors"] = [row.to_dict() for row in self.pair_correlation_errors]
        return payload


def exact_boltzmann_distribution(
    model: IsingModel,
    beta: float,
    *,
    max_variables: int = 16,
) -> ExactDistribution:
    """Enumerate ``p(s) proportional to exp(-beta * E(s))`` stably.

    The state order is lexicographic over ``(-1, +1)`` in
    ``model.variables`` order.  The offset is omitted before exponentiation.
    """
    if not isinstance(model, IsingModel):
        raise TypeError(f"model must be IsingModel, got {type(model).__name__}")
    canonical_beta = _nonnegative_beta(beta, name="beta")
    limit = _exact_limit(max_variables)
    variable_count = len(model.variables)
    if variable_count > limit:
        raise ValueError(
            f"exact enumeration requires 2^{variable_count} states, exceeding max_variables={limit}"
        )

    states = tuple(itertools.product((-1, 1), repeat=variable_count))
    if canonical_beta == 0.0:
        probability = 1.0 / len(states)
        log_probability = -math.log(len(states))
        return ExactDistribution(
            variables=model.variables,
            states=states,
            probabilities=(probability,) * len(states),
            log_probabilities=(log_probability,) * len(states),
            beta=canonical_beta,
            maximum_log_weight=0.0,
            shifted_log_normalizer=math.log(len(states)),
            underflowed_probability_count=0,
        )
    log_weights: list[float] = []
    for state in states:
        sample = dict(zip(model.variables, state))
        try:
            interaction = model.interaction_energy(sample)
            log_weight = finite_float(
                -canonical_beta * interaction,
                name="exact Boltzmann log weight",
            )
        except ValueError as error:
            raise ExactDistributionNumericalError(
                "exact Boltzmann energy or log weight exceeds binary64; "
                "rescale the interaction coefficients or beta before requesting "
                "probabilities and KL evidence"
            ) from error
        log_weights.append(log_weight)

    maximum_log_weight = max(log_weights)
    shifted_log_weights: list[float] = []
    for value in log_weights:
        shifted = value - maximum_log_weight
        if not math.isfinite(shifted):
            raise ExactDistributionNumericalError(
                "exact Boltzmann log-weight dynamic range exceeds binary64; "
                "rescale the interaction coefficients or beta before requesting "
                "probabilities and KL evidence"
            )
        shifted_log_weights.append(shifted)
    shifted_weights = [math.exp(value) for value in shifted_log_weights]
    normalization = finite_sum(shifted_weights, name="shifted Boltzmann normalization")
    if normalization <= 0.0:  # defensive; the maximum shifted weight is exactly one
        raise ArithmeticError("shifted Boltzmann normalization must be positive")
    shifted_log_normalizer = math.log(normalization)
    probabilities = tuple(weight / normalization for weight in shifted_weights)
    log_probabilities = tuple(value - shifted_log_normalizer for value in shifted_log_weights)
    return ExactDistribution(
        variables=model.variables,
        states=states,
        probabilities=probabilities,
        log_probabilities=log_probabilities,
        beta=canonical_beta,
        maximum_log_weight=maximum_log_weight,
        shifted_log_normalizer=shifted_log_normalizer,
        underflowed_probability_count=sum(probability == 0.0 for probability in probabilities),
    )


def _nonnegative_metric(value: float, *, name: str) -> float:
    canonical = finite_float(value, name=name)
    if canonical >= 0.0:
        return canonical
    if canonical >= -1e-12:
        return 0.0
    raise ArithmeticError(f"{name} is negative beyond floating-point tolerance: {canonical!r}")


def _directed_kl(
    probabilities: tuple[float, ...],
    log_probabilities: tuple[float, ...],
    other_log_probabilities: tuple[float, ...],
    *,
    name: str,
) -> float:
    terms = [
        probability * (log_probability - other_log_probability)
        for probability, log_probability, other_log_probability in zip(
            probabilities,
            log_probabilities,
            other_log_probabilities,
        )
        if probability > 0.0
    ]
    return _nonnegative_metric(finite_sum(terms, name=name), name=name)


def compare_boltzmann_distributions(
    target_model: IsingModel,
    implemented_model: IsingModel,
    *,
    target_beta: float,
    implemented_beta: float,
    max_variables: int = 16,
) -> DistributionComparison:
    """Exactly compare Boltzmann laws over an identical variable order."""
    if not isinstance(target_model, IsingModel):
        raise TypeError(f"target_model must be IsingModel, got {type(target_model).__name__}")
    if not isinstance(implemented_model, IsingModel):
        raise TypeError(f"implemented_model must be IsingModel, got {type(implemented_model).__name__}")
    if not exact_variable_order(implemented_model.variables, target_model.variables):
        raise ValueError("target and implemented models must have identical variable order")
    target = exact_boltzmann_distribution(
        target_model,
        target_beta,
        max_variables=max_variables,
    )
    implemented = exact_boltzmann_distribution(
        implemented_model,
        implemented_beta,
        max_variables=max_variables,
    )

    probability_errors = tuple(
        abs(target_probability - implemented_probability)
        for target_probability, implemented_probability in zip(
            target.probabilities,
            implemented.probabilities,
        )
    )
    maximum_error_index = max(range(len(probability_errors)), key=probability_errors.__getitem__)
    total_variation = _nonnegative_metric(
        0.5 * finite_sum(probability_errors, name="total variation"),
        name="total variation",
    )
    kl_target_to_implemented = _directed_kl(
        target.probabilities,
        target.log_probabilities,
        implemented.log_probabilities,
        name="KL(target || implemented)",
    )
    kl_implemented_to_target = _directed_kl(
        implemented.probabilities,
        implemented.log_probabilities,
        target.log_probabilities,
        name="KL(implemented || target)",
    )

    marginal_errors: list[SpinMarginalError] = []
    for position, variable in enumerate(target.variables):
        target_up = math.fsum(
            probability
            for state, probability in zip(target.states, target.probabilities)
            if state[position] == 1
        )
        implemented_up = math.fsum(
            probability
            for state, probability in zip(implemented.states, implemented.probabilities)
            if state[position] == 1
        )
        marginal_errors.append(
            SpinMarginalError(
                variable=variable,
                target_probability_up=target_up,
                implemented_probability_up=implemented_up,
                absolute_error=abs(target_up - implemented_up),
            )
        )

    pair_errors: list[PairCorrelationError] = []
    for left_position, right_position in itertools.combinations(range(len(target.variables)), 2):
        target_correlation = math.fsum(
            probability * state[left_position] * state[right_position]
            for state, probability in zip(target.states, target.probabilities)
        )
        implemented_correlation = math.fsum(
            probability * state[left_position] * state[right_position]
            for state, probability in zip(implemented.states, implemented.probabilities)
        )
        pair_errors.append(
            PairCorrelationError(
                left=target.variables[left_position],
                right=target.variables[right_position],
                target_correlation=target_correlation,
                implemented_correlation=implemented_correlation,
                absolute_error=abs(target_correlation - implemented_correlation),
            )
        )

    return DistributionComparison(
        variables=target.variables,
        num_states=len(target.states),
        total_variation=total_variation,
        kl_target_to_implemented=kl_target_to_implemented,
        kl_implemented_to_target=kl_implemented_to_target,
        maximum_state_probability_error=probability_errors[maximum_error_index],
        maximum_state_probability_error_state=target.states[maximum_error_index],
        marginal_errors=tuple(marginal_errors),
        pair_correlation_errors=tuple(pair_errors),
        target_underflowed_probability_count=target.underflowed_probability_count,
        implemented_underflowed_probability_count=implemented.underflowed_probability_count,
    )
