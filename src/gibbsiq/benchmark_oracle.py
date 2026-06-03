"""Independent re-verification oracle for ground-truth benchmark fixtures.

The benchmark corpus (``reference/06-benchmarks/fixtures/ground-truth-small.json``)
stores proven optima derived by exhaustive enumeration. When scoring a solver
candidate against it we apply the *strictest* pass criterion:

1. every scalar field (optimum value, degeneracy, derived quantities) must match
   the proven value exactly (floats within tolerance);
2. the candidate must supply at least one witness state, and the oracle
   recomputes that witness's objective **from the input model** -- it never
   trusts the candidate's self-reported numbers. A witness only counts if it is
   feasible and actually attains the proven optimum.

This module recomputes each family's objective directly from the fixture
``input`` block, so a candidate cannot pass by echoing the expected value while
returning a state that does not achieve it.

The energy convention matches the project canon
``E(s) = offset + sum_i h_i s_i + sum_{i<j} J_ij s_i s_j`` with ``s_i in {-1,+1}``.

Difference records are returned as plain dicts (same shape as the evaluation
report) so this module has no dependency on ``gibbsiq.evaluation``.
"""

from __future__ import annotations

import math
from typing import Any, Callable


def _diff(path: str, code: str, message: str, **extra: Any) -> dict[str, Any]:
    record = {"path": path, "code": code, "message": message}
    record.update({key: value for key, value in extra.items() if value is not None})
    return record


def _scalar_diffs(expected: Any, actual: Any, path: str, tolerance: float) -> list[dict[str, Any]]:
    """Exact comparison for a single scalar (floats within ``tolerance``)."""
    if isinstance(expected, float):
        if isinstance(actual, (int, float)) and not isinstance(actual, bool):
            if math.isclose(float(actual), expected, rel_tol=0.0, abs_tol=tolerance):
                return []
        return [_diff(path, "float_mismatch", f"float differs by more than {tolerance}",
                      expected=expected, actual=actual)]
    if expected == actual and type(expected) is type(actual):
        return []
    # Allow int/float numeric equality (e.g. expected 12 == actual 12.0).
    if (isinstance(expected, (int, float)) and not isinstance(expected, bool)
            and isinstance(actual, (int, float)) and not isinstance(actual, bool)
            and float(expected) == float(actual)):
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
    spins: dict[str, int] = {}
    raw = {str(key): value for key, value in witness.items()}
    for var in variables:
        if var not in raw:
            raise ValueError(f"spin witness missing variable {var!r}")
        value = raw[var]
        if value not in (-1, 1):
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
    energy = float(model.get("offset", 0.0))
    for var, field in model.get("linear", {}).items():
        energy += float(field) * spins[str(var)]
    for pair, coupling in model.get("quadratic", {}).items():
        left, right = pair.split(",")
        energy += float(coupling) * spins[left] * spins[right]
    return energy


def _verify_maxcut(model, witness, optimum, tolerance):
    spins = _normalize_spins(model, witness)
    cut = maxcut_cut_value(model, spins)
    if cut != optimum:
        return False, f"witness cut value {cut} != proven optimum {optimum}", cut
    return True, None, cut


def _verify_ising(model, witness, optimum, tolerance):
    spins = _normalize_spins(model, witness)
    energy = ising_energy(model, spins)
    if not math.isclose(energy, float(optimum), rel_tol=0.0, abs_tol=tolerance):
        return False, f"witness energy {energy} != proven ground-state energy {optimum}", energy
    return True, None, energy


def _verify_number_partition(model, witness, optimum, tolerance):
    if not isinstance(witness, dict) or "set_plus" not in witness or "set_minus" not in witness:
        return False, "partition witness needs 'set_plus' and 'set_minus' lists", None
    plus = list(witness["set_plus"])
    minus = list(witness["set_minus"])
    if sorted(plus + minus) != sorted(model["numbers"]):
        return False, "partition does not use each input number exactly once", None
    diff = abs(sum(plus) - sum(minus))
    if diff != optimum:
        return False, f"witness discrepancy {diff} != proven minimum {optimum}", diff
    return True, None, diff


def _verify_knapsack(model, witness, optimum, tolerance):
    if not isinstance(witness, list):
        return False, "knapsack witness must be a list of selected item indices", None
    selection = list(witness)
    n = len(model["weights"])
    if len(set(selection)) != len(selection):
        return False, "knapsack witness has duplicate indices", None
    if any(not isinstance(i, int) or i < 0 or i >= n for i in selection):
        return False, f"knapsack witness indices must be within 0..{n - 1}", None
    weight = sum(model["weights"][i] for i in selection)
    value = sum(model["values"][i] for i in selection)
    capacity = model["capacity"]
    if weight > capacity:
        return False, f"selection weight {weight} exceeds capacity {capacity}", value
    if value != optimum:
        return False, f"feasible selection value {value} != proven optimum {optimum}", value
    return True, None, value


def _verify_tsp(model, witness, optimum, tolerance):
    if not isinstance(witness, list):
        return False, "tsp witness must be a list (a tour permutation)", None
    tour = list(witness)
    n = model["num_cities"]
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
        "scalar_keys": ["num_nodes", "num_edges", "best_cut_value",
                        "best_ising_energy", "ground_state_degeneracy"],
        "optimum_key": "best_cut_value",
        "witness_key": "witness_spin_samples",
        "verify": _verify_maxcut,
    },
    "number_partition": {
        "scalar_keys": ["min_subset_sum_difference", "best_ising_energy",
                        "ground_state_degeneracy", "is_perfect_partition"],
        "optimum_key": "min_subset_sum_difference",
        "witness_key": "witness_partitions",
        "verify": _verify_number_partition,
    },
    "knapsack": {
        "scalar_keys": ["max_value", "weight_at_optimum", "capacity",
                        "num_optimal_selections"],
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


def verify_benchmark_fixture(
    fixture: dict[str, Any], actual: Any, tolerance: float
) -> list[dict[str, Any]]:
    """Strictly score a candidate against one ground-truth benchmark fixture.

    Returns a list of difference dicts (empty == pass).
    """
    fixture_id = fixture["id"]
    family = fixture.get("family")
    spec = FAMILY_SPECS.get(family)
    if spec is None:
        return [_diff(fixture_id, "unknown_family",
                      f"no verification oracle for family {family!r}")]

    if not isinstance(actual, dict):
        return [_diff(fixture_id, "type_mismatch", "expected an object of solver outputs",
                      expected="object", actual=type(actual).__name__)]

    expected = fixture["expected"]
    model = fixture["input"]
    differences: list[dict[str, Any]] = []

    # 1. Every scalar field must match the proven value exactly.
    for key in spec["scalar_keys"]:
        path = f"{fixture_id}.{key}"
        if key not in actual:
            differences.append(_diff(path, "missing_key", "required key is missing",
                                     expected=expected[key]))
            continue
        differences.extend(_scalar_diffs(expected[key], actual[key], path, tolerance))

    # 2. Independently re-verify candidate witnesses.
    witness_key = spec["witness_key"]
    verify: Callable = spec["verify"]
    optimum = expected[spec["optimum_key"]]
    witnesses = actual.get(witness_key)
    path = f"{fixture_id}.{witness_key}"
    if not isinstance(witnesses, list) or not witnesses:
        differences.append(_diff(path, "missing_witness",
                                 "candidate must supply at least one optimal witness state"))
    else:
        for index, witness in enumerate(witnesses):
            witness_path = f"{path}[{index}]"
            try:
                ok, message, computed = verify(model, witness, optimum, tolerance)
            except (ValueError, KeyError, TypeError, IndexError) as error:
                differences.append(_diff(witness_path, "invalid_witness", str(error)))
                continue
            if not ok:
                differences.append(_diff(witness_path, "witness_not_optimal", message,
                                         expected=optimum, actual=computed))

    return differences
