"""Re-verification oracle for ground-truth benchmark fixtures.

Strict pass criterion: scalar fields (optimum value, exact degeneracy) must
match the proven value; witness objective is recomputed from the input model,
never trusted from candidate-reported numbers. Energy convention:
``E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j``, ``s_i in {-1,+1}``.
Differences are plain dicts -- no dependency on ``gibbsiq.evaluation``.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, TypeAlias

# Shared tolerance for benchmark_bridge and evaluation.
DEFAULT_TOLERANCE = 1e-9


def validate_tolerance(tolerance: Any) -> float:
    """Return a finite non-negative absolute tolerance, rejecting booleans."""
    if isinstance(tolerance, bool):
        raise ValueError(f"tolerance must be a finite non-negative number, got {tolerance!r}")
    try:
        canonical = float(tolerance)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"tolerance must be a finite non-negative number, got {tolerance!r}") from error
    if not math.isfinite(canonical) or canonical < 0.0:
        raise ValueError(f"tolerance must be a finite non-negative number, got {tolerance!r}")
    return canonical


def close_within(actual: Any, expected: float, tolerance: float) -> bool:
    """True when ``actual`` is a non-bool real number within ``tolerance`` of ``expected``."""
    absolute_tolerance = validate_tolerance(tolerance)
    if not isinstance(actual, (int, float)) or isinstance(actual, bool):
        return False
    try:
        canonical_actual = float(actual)
    except (ValueError, OverflowError):
        return False
    return math.isclose(
        canonical_actual,
        expected,
        rel_tol=0.0,
        abs_tol=absolute_tolerance,
    )


def _diff(path: str, code: str, message: str, **extra: Any) -> dict[str, Any]:
    record = {"path": path, "code": code, "message": message}
    record.update({key: value for key, value in extra.items() if value is not None})
    return record


def _scalar_diffs(expected: Any, actual: Any, path: str, tolerance: float) -> list[dict[str, Any]]:
    """Exact comparison for a single scalar (floats within ``tolerance``)."""
    if isinstance(expected, float):
        if close_within(actual, expected, tolerance):
            return []
        return [
            _diff(
                path,
                "float_mismatch",
                f"float differs by more than {tolerance}",
                expected=expected,
                actual=actual,
            )
        ]
    if expected == actual and type(expected) is type(actual):
        return []
    # Allow int/float numeric equality (e.g. expected 12 == actual 12.0).
    if (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and expected == actual
    ):
        return []
    return [_diff(path, "value_mismatch", "value does not match", expected=expected, actual=actual)]


# --------------------------------------------------------------------------- #
# Objective recomputation per family.
# --------------------------------------------------------------------------- #


def _normalize_spins(model: dict[str, Any], witness: Any) -> dict[str, int]:
    """Validate a spin witness and return it keyed by string variable name."""
    if not isinstance(witness, dict):
        raise ValueError("spin witness must be an object of variable -> +-1")
    variables = [str(v) for v in model["variables"]]
    if len(set(variables)) != len(variables):
        raise ValueError("model variables are not unique after string normalization")
    spins: dict[str, int] = {}
    raw: dict[str, Any] = {}
    for key, value in witness.items():
        normalized_key = str(key)
        if normalized_key in raw:
            raise ValueError(f"spin witness duplicates normalized variable {normalized_key!r}")
        raw[normalized_key] = value
    extra = sorted(set(raw) - set(variables))
    if extra:
        raise ValueError(f"spin witness contains unknown variables {extra!r}")
    for var in variables:
        if var not in raw:
            raise ValueError(f"spin witness missing variable {var!r}")
        value = raw[var]
        if isinstance(value, bool) or not isinstance(value, int) or value not in (-1, 1):
            raise ValueError(f"spin for {var!r} must be -1 or +1, got {value!r}")
        spins[var] = int(value)
    return spins


def maxcut_cut_value(model: dict[str, Any], spins: dict[str, int]) -> int:
    cut = 0
    for u, v in model["edges"]:
        if spins[str(u)] != spins[str(v)]:
            cut += 1
    return cut


def ising_energy(model: dict[str, Any], spins: dict[str, int]) -> float:
    # Independent of IsingModel.energy -- sharing it would let an IR sign/offset
    # bug self-consistently pass. Do not consolidate.
    energy = float(model.get("offset", 0.0))
    for var, field in model.get("linear", {}).items():
        energy += float(field) * spins[str(var)]
    for pair, coupling in model.get("quadratic", {}).items():
        left, right = pair.split(",")
        energy += float(coupling) * spins[left] * spins[right]
    return energy


# (passed, failure message, recomputed objective) from one witness check.
VerifyResult: TypeAlias = tuple[bool, str | None, int | float | None]
# Family verifier: (fixture input model, witness, proven optimum, tolerance).
VerifyFn: TypeAlias = Callable[[dict[str, Any], Any, Any, float], VerifyResult]


def _verify_maxcut(model: dict[str, Any], witness: Any, optimum: Any, tolerance: float) -> VerifyResult:
    spins = _normalize_spins(model, witness)
    cut = maxcut_cut_value(model, spins)
    if cut != optimum:
        return False, f"witness cut value {cut} != proven optimum {optimum}", cut
    return True, None, cut


def _verify_ising(model: dict[str, Any], witness: Any, optimum: Any, tolerance: float) -> VerifyResult:
    spins = _normalize_spins(model, witness)
    energy = ising_energy(model, spins)
    if not math.isclose(energy, float(optimum), rel_tol=0.0, abs_tol=tolerance):
        return False, f"witness energy {energy} != proven ground-state energy {optimum}", energy
    return True, None, energy


def _verify_number_partition(
    model: dict[str, Any], witness: Any, optimum: Any, tolerance: float
) -> VerifyResult:
    if not isinstance(witness, dict) or "set_plus" not in witness or "set_minus" not in witness:
        return False, "partition witness needs 'set_plus' and 'set_minus' lists", None
    plus = list(witness["set_plus"])
    minus = list(witness["set_minus"])
    if any(isinstance(value, bool) or not isinstance(value, int) for value in plus + minus):
        return False, "partition witness values must be integers, not booleans", None
    if sorted(plus + minus) != sorted(model["numbers"]):
        return False, "partition does not use each input number exactly once", None
    diff = abs(sum(plus) - sum(minus))
    if diff != optimum:
        return False, f"witness discrepancy {diff} != proven minimum {optimum}", diff
    return True, None, diff


def _verify_knapsack(model: dict[str, Any], witness: Any, optimum: Any, tolerance: float) -> VerifyResult:
    if not isinstance(witness, list):
        return False, "knapsack witness must be a list of selected item indices", None
    selection = list(witness)
    n = len(model["weights"])
    if len(set(selection)) != len(selection):
        return False, "knapsack witness has duplicate indices", None
    if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= n for i in selection):
        return False, f"knapsack witness indices must be within 0..{n - 1}", None
    weight = sum(model["weights"][i] for i in selection)
    value = sum(model["values"][i] for i in selection)
    capacity = model["capacity"]
    if weight > capacity:
        return False, f"selection weight {weight} exceeds capacity {capacity}", value
    if value != optimum:
        return False, f"feasible selection value {value} != proven optimum {optimum}", value
    return True, None, value


def _verify_tsp(model: dict[str, Any], witness: Any, optimum: Any, tolerance: float) -> VerifyResult:
    if not isinstance(witness, list):
        return False, "tsp witness must be a list (a tour permutation)", None
    tour = list(witness)
    n = model["num_cities"]
    if any(isinstance(city, bool) or not isinstance(city, int) for city in tour):
        return False, "tsp witness cities must be integers, not booleans", None
    if sorted(tour) != list(range(n)):
        return False, f"tsp witness must be a permutation of 0..{n - 1}", None
    distance = model["distance_matrix"]
    length = sum(distance[tour[i]][tour[(i + 1) % n]] for i in range(n))
    if length != optimum:
        return False, f"tour length {length} != proven optimum {optimum}", length
    return True, None, length


# family -> verification spec. ``input`` ``format`` may differ from family name
# (sk_spin_glass uses format "ising").
FAMILY_SPECS: dict[str, dict[str, Any]] = {
    "maxcut": {
        "scalar_keys": [
            "num_nodes",
            "num_edges",
            "best_cut_value",
            "best_ising_energy",
            "ground_state_degeneracy",
        ],
        "optimum_key": "best_cut_value",
        "witness_key": "witness_spin_samples",
        "verify": _verify_maxcut,
    },
    "number_partition": {
        "scalar_keys": [
            "min_subset_sum_difference",
            "best_ising_energy",
            "ground_state_degeneracy",
            "is_perfect_partition",
        ],
        "optimum_key": "min_subset_sum_difference",
        "witness_key": "witness_partitions",
        "verify": _verify_number_partition,
    },
    "knapsack": {
        "scalar_keys": ["max_value", "weight_at_optimum", "capacity", "num_optimal_selections"],
        "optimum_key": "max_value",
        "witness_key": "witness_selections",
        "verify": _verify_knapsack,
    },
    "tsp": {
        "scalar_keys": ["num_cities", "optimal_tour_length", "num_optimal_tours"],
        "optimum_key": "optimal_tour_length",
        "witness_key": "witness_tours",
        "verify": _verify_tsp,
    },
    "sk_spin_glass": {
        "scalar_keys": ["num_spins", "ground_state_energy", "ground_state_degeneracy"],
        "optimum_key": "ground_state_energy",
        "witness_key": "witness_spin_samples",
        "verify": _verify_ising,
    },
}


def score_candidate(
    fixture: dict[str, Any],
    actual: Any,
    tolerance: float,
    *,
    optional_keys: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Score a candidate against a fixture; shared by the two pass criteria.

    ``optional_keys`` names scalar keys the candidate may omit without failing
    (still checked when volunteered). Full characterization passes an empty set;
    the optimization-claim criterion passes the enumeration-only keys.
    """
    tolerance = validate_tolerance(tolerance)
    fixture_id = fixture["id"]
    family = fixture.get("family")
    if not isinstance(family, str):
        return [_diff(fixture_id, "unknown_family", f"no verification oracle for family {family!r}")]
    spec = FAMILY_SPECS.get(family)
    if spec is None:
        return [_diff(fixture_id, "unknown_family", f"no verification oracle for family {family!r}")]

    if not isinstance(actual, dict):
        return [
            _diff(
                fixture_id,
                "type_mismatch",
                "expected an object of solver outputs",
                expected="object",
                actual=type(actual).__name__,
            )
        ]

    expected = fixture["expected"]
    model = fixture["input"]
    differences: list[dict[str, Any]] = []

    # 1. Every required scalar field must match the proven value exactly.
    for key in spec["scalar_keys"]:
        path = f"{fixture_id}.{key}"
        if key not in actual:
            if key in optional_keys:
                continue
            differences.append(_diff(path, "missing_key", "required key is missing", expected=expected[key]))
            continue
        differences.extend(_scalar_diffs(expected[key], actual[key], path, tolerance))

    # 2. Independently re-verify candidate witnesses.
    witness_key = spec["witness_key"]
    verify: VerifyFn = spec["verify"]
    optimum = expected[spec["optimum_key"]]
    witnesses = actual.get(witness_key)
    path = f"{fixture_id}.{witness_key}"
    if not isinstance(witnesses, list) or not witnesses:
        differences.append(
            _diff(path, "missing_witness", "candidate must supply at least one optimal witness state")
        )
        return differences
    for index, witness in enumerate(witnesses):
        witness_path = f"{path}[{index}]"
        try:
            ok, message, computed = verify(model, witness, optimum, tolerance)
        except (ValueError, KeyError, TypeError, IndexError) as error:
            differences.append(_diff(witness_path, "invalid_witness", str(error)))
            continue
        if not ok:
            differences.append(
                _diff(
                    witness_path,
                    "witness_not_optimal",
                    message or "witness did not attain optimum",
                    expected=optimum,
                    actual=computed,
                )
            )
            continue
        if family == "knapsack":
            witness_weight = sum(model["weights"][item] for item in witness)
            expected_weight = expected["weight_at_optimum"]
            if witness_weight != expected_weight:
                differences.append(
                    _diff(
                        witness_path,
                        "witness_weight_mismatch",
                        "optimal-value witness does not match the declared optimum weight",
                        expected=expected_weight,
                        actual=witness_weight,
                    )
                )
    return differences


def verify_benchmark_fixture(fixture: dict[str, Any], actual: Any, tolerance: float) -> list[dict[str, Any]]:
    """Strictly score a candidate under the full-characterization criterion.

    Every scalar field (including enumeration-only quantities) is required.
    Returns a list of difference dicts (empty == pass).
    """
    return score_candidate(fixture, actual, tolerance)
