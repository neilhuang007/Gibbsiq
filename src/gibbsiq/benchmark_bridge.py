"""Bridge from sampler results to strict benchmark-oracle candidates.

This module closes the loop between the THRML runtime and the ground-truth
benchmark corpus (``reference/06-benchmarks/fixtures/ground-truth-small.json``):
it lowers a benchmark fixture into the canonical :class:`IsingModel`, converts a
:class:`SampleResult` into the candidate shape the oracle scores, and verifies
the candidate under the *optimization claim* criterion.

Anti-cheat contract (the reason this module exists):

1. :func:`compile_fixture` and :func:`candidate_from_result` read **only** the
   fixture's ``input`` block -- never ``expected`` -- so a candidate cannot echo
   proven values it did not compute. Both functions accept fixtures whose
   ``expected`` block has been removed entirely.
2. Witnesses are the sampler's own best states. The oracle's family verifiers
   (:data:`gibbsiq.benchmark_oracle.FAMILY_SPECS`) recompute each witness's
   objective from the input model, so a fabricated witness cannot pass.
3. :func:`verify_optimum_claim` checks every scalar a sampler can honestly
   claim against the proven value. Enumeration-only quantities (ground-state
   degeneracy, optimal-selection counts) may be omitted -- sampling cannot
   prove completeness of the optimum set -- but if a candidate volunteers one,
   it is held to the proven value. The full-characterization criterion
   (:func:`gibbsiq.benchmark_oracle.verify_benchmark_fixture`) stays unchanged
   and still requires them.

``knapsack`` and ``tsp`` fixtures are deliberately unsupported: their Ising
encodings need a penalty-weight / one-hot layer (Lucas 2014, secs. 5.2 and 7.2)
that Gibbsiq does not lower yet. :func:`compile_fixture` raises
``NotImplementedError`` for them rather than lowering something unfaithful.
"""

from __future__ import annotations

from typing import Any

from gibbsiq.benchmark_oracle import DEFAULT_TOLERANCE, score_candidate
from gibbsiq.conversions import compile_ising
from gibbsiq.model import IsingModel
from gibbsiq.result import SampleResult

# Proven quantities a sampler cannot honestly claim: they require exhaustive
# enumeration of the optimum set, which sampling can only lower-bound.
ENUMERATION_ONLY_KEYS = frozenset({"ground_state_degeneracy", "num_optimal_selections", "num_optimal_tours"})
MAX_WITNESSES = 8
SUPPORTED_FAMILIES = ("maxcut", "number_partition", "sk_spin_glass")


def compile_fixture(fixture: dict[str, Any]) -> IsingModel:
    """Lower a benchmark fixture's ``input`` block into the canonical Ising IR.

    Reads only ``fixture["input"]`` (and ``id``/``family`` for metadata), so the
    lowered model carries no information about the proven optimum.
    """
    family = fixture.get("family")
    model_input = fixture["input"]
    metadata = {
        "benchmark_fixture_id": fixture.get("id"),
        "benchmark_family": family,
    }
    if family == "maxcut":
        variables = tuple(str(v) for v in model_input["variables"])
        h = {variable: 0.0 for variable in variables}
        maxcut_quadratic = {(str(u), str(v)): 1.0 for u, v in model_input["edges"]}
        return compile_ising(h, maxcut_quadratic, variables=variables, metadata=metadata)
    if family == "sk_spin_glass":
        variables = tuple(str(v) for v in model_input["variables"])
        h = {str(var): float(field) for var, field in model_input.get("linear", {}).items()}
        spin_glass_quadratic: dict[tuple[str, str], float] = {}
        for pair, coupling in model_input.get("quadratic", {}).items():
            left, right = pair.split(",")
            spin_glass_quadratic[(left, right)] = float(coupling)
        return compile_ising(
            h,
            spin_glass_quadratic,
            offset=float(model_input.get("offset", 0.0)),
            variables=variables,
            metadata=metadata,
        )
    if family == "number_partition":
        # E = (sum_i n_i s_i)^2 = sum_i n_i^2 + sum_{i<j} 2 n_i n_j s_i s_j,
        # so the minimum energy equals the squared subset-sum difference.
        numbers = [int(value) for value in model_input["numbers"]]
        variables = tuple(str(i) for i in range(len(numbers)))
        h = {variable: 0.0 for variable in variables}
        partition_quadratic = {
            (str(i), str(j)): 2.0 * numbers[i] * numbers[j]
            for i in range(len(numbers))
            for j in range(i + 1, len(numbers))
        }
        offset = float(sum(value * value for value in numbers))
        return compile_ising(h, partition_quadratic, offset=offset, variables=variables, metadata=metadata)
    raise NotImplementedError(
        f"family {family!r} requires a penalty/one-hot encoding layer that "
        f"Gibbsiq does not lower yet; supported families: {SUPPORTED_FAMILIES}"
    )


def optimal_spin_witnesses(
    result: SampleResult, *, tolerance: float = DEFAULT_TOLERANCE
) -> list[dict[str, int]]:
    """Distinct best-energy samples from a result, capped at ``MAX_WITNESSES``.

    Witness states are keyed by string variable name to match the fixture
    witness schema; first-seen sample order is preserved.
    """
    assert result.interaction_energies is not None
    best_interaction_energy = min(result.interaction_energies)
    witnesses: list[dict[str, int]] = []
    seen: set[tuple[int, ...]] = set()
    for sample, interaction_energy in zip(result.samples, result.interaction_energies):
        if abs(interaction_energy - best_interaction_energy) > tolerance:
            continue
        key = tuple(int(sample[variable]) for variable in result.variables)
        if key in seen:
            continue
        seen.add(key)
        witnesses.append({str(variable): int(sample[variable]) for variable in result.variables})
        if len(witnesses) >= MAX_WITNESSES:
            break
    return witnesses


def candidate_from_result(fixture: dict[str, Any], result: SampleResult) -> dict[str, Any]:
    """Build the oracle candidate for one fixture from a sampler result.

    Reads only ``fixture["input"]``; every reported quantity is recomputed from
    the result's samples under the canonical energy convention.
    """
    family = fixture.get("family")
    model_input = fixture["input"]
    witnesses = optimal_spin_witnesses(result)
    best_energy = float(result.best_energy)
    if family == "maxcut":
        num_edges = len(model_input["edges"])
        cut_value = (num_edges - best_energy) / 2.0
        if abs(cut_value - round(cut_value)) > DEFAULT_TOLERANCE:
            raise ValueError(
                f"best energy {best_energy} does not correspond to an integer cut on {num_edges} edges"
            )
        return {
            "num_nodes": len(model_input["variables"]),
            "num_edges": num_edges,
            "best_cut_value": int(round(cut_value)),
            "best_ising_energy": best_energy,
            "witness_spin_samples": witnesses,
        }
    if family == "sk_spin_glass":
        return {
            "num_spins": len(model_input["variables"]),
            "ground_state_energy": best_energy,
            "witness_spin_samples": witnesses,
        }
    if family == "number_partition":
        numbers = [int(value) for value in model_input["numbers"]]
        best_sample = result.best_sample
        signed_sum = sum(numbers[int(str(variable))] * spin for variable, spin in best_sample.items())
        difference = abs(signed_sum)
        return {
            "min_subset_sum_difference": difference,
            "best_ising_energy": float(difference * difference),
            "is_perfect_partition": difference == 0,
            "witness_partitions": [_partition_witness(numbers, witness) for witness in witnesses],
        }
    raise NotImplementedError(
        f"family {family!r} has no candidate mapping; supported families: {SUPPORTED_FAMILIES}"
    )


def _partition_witness(numbers: list[int], witness: dict[str, int]) -> dict[str, list[int]]:
    ordered = sorted(witness.items(), key=lambda item: int(item[0]))
    set_plus = [numbers[int(var)] for var, spin in ordered if spin == 1]
    set_minus = [numbers[int(var)] for var, spin in ordered if spin == -1]
    return {"set_plus": set_plus, "set_minus": set_minus}


def verify_optimum_claim(
    fixture: dict[str, Any], actual: Any, tolerance: float = DEFAULT_TOLERANCE
) -> list[dict[str, Any]]:
    """Score a sampler candidate under the optimization-claim criterion.

    Identical to :func:`gibbsiq.benchmark_oracle.verify_benchmark_fixture`
    except that enumeration-only scalar keys may be omitted (they are still
    checked when the candidate volunteers them). Witness re-verification is
    mandatory and uses the same family verifiers, so every witness objective is
    recomputed from the input model. Returns a list of difference dicts
    (empty == pass).
    """
    return score_candidate(fixture, actual, tolerance, optional_keys=ENUMERATION_ONLY_KEYS)
