"""Bounded exact reductions for binary higher-order factors.

The module deliberately exposes only the audited cubic monomial reduction in
EVAL-EQ-025.  Callers needing larger or differently structured factors receive
an explicit error instead of an implied universal quadratization policy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from gibbsiq._frozen import freeze
from gibbsiq.conversions import compile_qubo
from gibbsiq.model import (
    IsingModel,
    Variable,
    Vartype,
    exact_label_equal,
    finite_float,
    finite_sum,
    sample_to_spin_values,
    variable_index,
)

PenaltyStatus = Literal[
    "inadequate",
    "adequate_at_energy_boundary",
    "proved_ancilla_unique",
]


@dataclass(frozen=True, slots=True)
class PenaltyPolicy:
    """Audited penalty value and the scope of its adequacy proof."""

    penalty: float
    strict_boundary: float
    status: PenaltyStatus
    selection: Literal["caller_supplied"]
    certificate_arithmetic: Literal["exact"]
    finite_precision_guarantee: Literal["not_universally_certified"]
    proof_scope: str

    def to_metadata(self) -> dict[str, Any]:
        """Return the complete machine-readable certificate record."""
        return {
            "penalty": self.penalty,
            "strict_boundary": self.strict_boundary,
            "status": self.status,
            "selection": self.selection,
            "certificate_arithmetic": self.certificate_arithmetic,
            "finite_precision_guarantee": self.finite_precision_guarantee,
            "proof_scope": self.proof_scope,
        }


@dataclass(frozen=True, slots=True)
class CubicMonomialLowering:
    """One-ancilla QUBO/Ising lowering with a checked binary decoder."""

    source_variables: tuple[Variable, Variable, Variable]
    ancilla: Variable
    ancilla_variables: tuple[Variable, ...]
    variables: tuple[Variable, ...]
    coefficient: float
    qubo_linear: Mapping[Variable, float]
    qubo_quadratic: Mapping[tuple[Variable, Variable], float]
    qubo_offset: float
    ising_model: IsingModel
    penalty_policy: PenaltyPolicy
    source_objective_map: str
    overhead: Mapping[str, Any]

    def _binary_values(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype,
    ) -> dict[Variable, int]:
        if not isinstance(sample, Mapping):
            raise TypeError(f"lowered sample must be a mapping, got {type(sample).__name__}")
        if len(sample) != len(self.variables):
            raise ValueError("lowered sample keys must match encoded variables exactly")
        spins = sample_to_spin_values(sample, self.variables, vartype)
        return {variable: (spin + 1) // 2 for variable, spin in zip(self.variables, spins)}

    def qubo_energy(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> float:
        """Evaluate the published QUBO fields for a well-formed binary word."""
        bits = self._binary_values(sample, vartype=vartype)
        return finite_sum(
            [self.qubo_offset]
            + [self.qubo_linear[variable] * bits[variable] for variable in self.variables]
            + [
                coefficient * bits[left] * bits[right]
                for (left, right), coefficient in self.qubo_quadratic.items()
            ],
            name="cubic lowered QUBO energy",
        )

    def decode(
        self,
        sample: Mapping[Variable, int],
        *,
        vartype: Vartype = "BINARY",
    ) -> dict[Variable, int]:
        """Decode source bits after rejecting an inconsistent product ancilla."""
        bits = self._binary_values(sample, vartype=vartype)
        left, middle, _ = self.source_variables
        if bits[self.ancilla] != bits[left] * bits[middle]:
            raise ValueError("product ancilla does not equal the product of its source bits")
        return {variable: bits[variable] for variable in self.source_variables}


def _nonnegative_penalty(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("factor-lowering penalty must be numeric, not boolean")
    penalty = finite_float(value, name="factor-lowering penalty")
    if penalty < 0.0:
        raise ValueError("factor-lowering penalty must be nonnegative")
    return penalty


def _finite_number(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    return finite_float(value, name=name)


def _cubic_ancilla_label(source_variables: tuple[Variable, Variable, Variable]) -> Variable:
    """Return a deterministic typed label, failing closed on a reserved-label clash."""
    label = ("gibbsiq.factor_lowering", "cubic_product", source_variables)
    if any(exact_label_equal(label, variable) for variable in source_variables):
        raise ValueError("source variables collide with the reserved cubic-ancilla label")
    return label


def reduce_cubic_monomial(
    variables: Sequence[Variable],
    *,
    coefficient: float,
    penalty: float,
    offset: float = 0.0,
) -> CubicMonomialLowering:
    """Lower ``offset + coefficient*x*y*z`` with one Rosenberg ancilla.

    In exact arithmetic, the energy equality criterion is ``penalty >=
    abs(coefficient)``. Strict inequality additionally makes the product
    ancilla unique for every fixed source assignment. Lower penalties are
    accepted and labelled inadequate so callers can record and test the
    failure boundary explicitly. Binary64 evaluation of a one-ULP strict
    margin is not a numerical uniqueness certificate.
    """
    source_variables = tuple(variables)
    if len(source_variables) != 3:
        raise ValueError("reduce_cubic_monomial requires exactly three source variables")
    if len(set(source_variables)) != 3:
        raise ValueError("cubic source variables must be distinct without equality aliases")
    variable_index(source_variables)
    source_variables = (
        source_variables[0],
        source_variables[1],
        source_variables[2],
    )
    source_coefficient = _finite_number(coefficient, name="cubic coefficient")
    if source_coefficient == 0.0:
        raise ValueError("cubic coefficient must be nonzero for the bounded reduction")
    canonical_penalty = _nonnegative_penalty(penalty)
    qubo_offset = _finite_number(offset, name="cubic source offset")
    strict_boundary = abs(source_coefficient)
    ancilla = _cubic_ancilla_label(source_variables)
    encoded_variables = source_variables + (ancilla,)
    variable_index(encoded_variables)
    left, middle, right = source_variables

    if canonical_penalty < strict_boundary:
        status: PenaltyStatus = "inadequate"
    elif canonical_penalty == strict_boundary:
        status = "adequate_at_energy_boundary"
    else:
        status = "proved_ancilla_unique"
    policy = PenaltyPolicy(
        penalty=canonical_penalty,
        strict_boundary=strict_boundary,
        status=status,
        selection="caller_supplied",
        certificate_arithmetic="exact",
        finite_precision_guarantee="not_universally_certified",
        proof_scope=(
            "EVAL-EQ-025 exact arithmetic: penalty >= abs(coefficient) preserves the "
            "minimum source energy; strict inequality makes the product ancilla unique"
        ),
    )

    linear = {variable: 0.0 for variable in encoded_variables}
    linear[ancilla] = 3.0 * canonical_penalty
    quadratic = {
        (left, middle): canonical_penalty,
        (left, ancilla): -2.0 * canonical_penalty,
        (middle, ancilla): -2.0 * canonical_penalty,
        (ancilla, right): source_coefficient,
    }
    qubo_linear = MappingProxyType(linear)
    qubo_quadratic = MappingProxyType({pair: value for pair, value in quadratic.items() if value != 0.0})
    overhead = {
        "source_variable_count": 3,
        "ancilla_count": 1,
        "encoded_variable_count": 4,
        "qubo_linear_term_count": sum(value != 0.0 for value in qubo_linear.values()),
        "qubo_quadratic_term_count": len(qubo_quadratic),
        "source_offset": qubo_offset,
        "source_coefficient": source_coefficient,
        "penalty_policy": policy.to_metadata(),
        "equation_contract": "EVAL-EQ-025",
        "objective_relation": "min_ancilla lowered_energy = source_energy when penalty >= abs(coefficient)",
    }
    ising_model = compile_qubo(
        {
            "variables": list(encoded_variables),
            "linear": dict(qubo_linear),
            "quadratic": dict(qubo_quadratic),
            "offset": qubo_offset,
        },
        metadata=overhead,
        source_format="cubic_monomial_rosenberg_qubo",
    )
    return CubicMonomialLowering(
        source_variables=source_variables,
        ancilla=ancilla,
        ancilla_variables=(ancilla,),
        variables=encoded_variables,
        coefficient=source_coefficient,
        qubo_linear=qubo_linear,
        qubo_quadratic=qubo_quadratic,
        qubo_offset=qubo_offset,
        ising_model=ising_model,
        penalty_policy=policy,
        source_objective_map="identity",
        overhead=freeze(overhead),
    )
