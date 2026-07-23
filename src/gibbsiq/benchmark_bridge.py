"""Bridge from sampler results to strict benchmark-oracle candidates.

Lowers a fixture's ``input`` block into :class:`IsingModel`, builds an oracle
candidate from a :class:`SampleResult`, and scores it under the
optimization-claim criterion.

Echo-proofing: reads only ``input``, never ``expected``. Witnesses are the
sampler's best states, recomputed from the input model by the oracle's
family verifiers (:data:`gibbsiq.benchmark_oracle.FAMILY_SPECS`), so a
fabricated witness cannot pass. Enumeration-only quantities (ground-state
degeneracy, optimal-selection counts) may be omitted -- sampling cannot prove
completeness -- but are checked if volunteered.

``knapsack`` and ``tsp`` use the bounded penalty/one-hot lowerings in
:mod:`gibbsiq.constraints`.  Their candidate path decodes every sampled word
and ranks native feasible witnesses; it never trusts the penalized energy as a
native objective.
"""

from __future__ import annotations

from typing import Any

from gibbsiq.benchmark_oracle import DEFAULT_TOLERANCE, score_candidate
from gibbsiq.constraints import KnapsackEncoding, TspEncoding, compile_knapsack, compile_tsp
from gibbsiq.conversions import compile_ising
from gibbsiq.model import IsingModel, Vartype, exact_variable_order
from gibbsiq.result import SampleResult

# Require exhaustive enumeration of the optimum set; sampling only lower-bounds these.
ENUMERATION_ONLY_KEYS = frozenset({"ground_state_degeneracy", "num_optimal_selections", "num_optimal_tours"})
MAX_WITNESSES = 8
SUPPORTED_FAMILIES = ("knapsack", "maxcut", "number_partition", "sk_spin_glass", "tsp")


def compile_fixture(fixture: dict[str, Any]) -> IsingModel:
    """Lower a fixture's ``input`` block into the canonical Ising IR.

    Reads only ``input`` (and ``id``/``family`` for metadata) -- never the
    proven optimum.
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
    if family == "knapsack":
        return _with_fixture_metadata(_compile_knapsack_input(model_input).ising_model, metadata)
    if family == "tsp":
        return _with_fixture_metadata(_compile_tsp_input(model_input).ising_model, metadata)
    raise NotImplementedError(
        f"family {family!r} has no bounded benchmark lowering; supported families: {SUPPORTED_FAMILIES}"
    )


def optimal_spin_witnesses(
    result: SampleResult, *, tolerance: float = DEFAULT_TOLERANCE
) -> list[dict[str, int]]:
    """Distinct best-energy samples from a result, capped at ``MAX_WITNESSES``.

    Keyed by string variable name to match the fixture witness schema;
    first-seen order preserved.
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
    """Build the oracle candidate from a sampler result.

    Reads only ``input``; every quantity is recomputed from the result's
    samples under the canonical energy convention.
    """
    family = fixture.get("family")
    model_input = fixture["input"]
    if family == "maxcut":
        witnesses = optimal_spin_witnesses(result)
        best_energy = float(result.best_energy)
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
        witnesses = optimal_spin_witnesses(result)
        best_energy = float(result.best_energy)
        return {
            "num_spins": len(model_input["variables"]),
            "ground_state_energy": best_energy,
            "witness_spin_samples": witnesses,
        }
    if family == "number_partition":
        witnesses = optimal_spin_witnesses(result)
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
    if family == "knapsack":
        return _knapsack_candidate_from_result(_compile_knapsack_input(model_input), result)
    if family == "tsp":
        return _tsp_candidate_from_result(_compile_tsp_input(model_input), result)
    raise NotImplementedError(
        f"family {family!r} has no candidate mapping; supported families: {SUPPORTED_FAMILIES}"
    )


def _partition_witness(numbers: list[int], witness: dict[str, int]) -> dict[str, list[int]]:
    ordered = sorted(witness.items(), key=lambda item: int(item[0]))
    set_plus = [numbers[int(var)] for var, spin in ordered if spin == 1]
    set_minus = [numbers[int(var)] for var, spin in ordered if spin == -1]
    return {"set_plus": set_plus, "set_minus": set_minus}


def _compile_knapsack_input(model_input: dict[str, Any]) -> KnapsackEncoding:
    """Compile fixture input with a deterministic strict policy from input only."""
    return compile_knapsack(model_input["weights"], model_input["values"], model_input["capacity"])


def _with_fixture_metadata(model: IsingModel, fixture_metadata: dict[str, Any]) -> IsingModel:
    """Add bridge provenance without changing a lowered energy coefficient."""
    metadata = dict(model.metadata)
    metadata.update(fixture_metadata)
    return IsingModel(
        variables=model.variables,
        linear=model.linear,
        quadratic=model.quadratic,
        offset=model.offset,
        source_format=model.source_format,
        metadata=metadata,
    )


def _compile_tsp_input(model_input: dict[str, Any]) -> TspEncoding:
    """Compile fixture input with a deterministic strict policy from input only."""
    city_count = model_input.get("num_cities")
    matrix = model_input["distance_matrix"]
    if isinstance(city_count, bool) or not isinstance(city_count, int):
        raise ValueError("TSP fixture num_cities must be an integer")
    if city_count != len(matrix):
        raise ValueError("TSP fixture num_cities must match the distance-matrix size")
    return compile_tsp(matrix)


def _require_encoding_variable_order(result: SampleResult, variables: tuple[Any, ...]) -> Vartype:
    if result.vartype == "SPIN":
        vartype: Vartype = "SPIN"
    elif result.vartype == "BINARY":
        vartype = "BINARY"
    else:
        raise ValueError("constrained benchmark results must use SPIN or BINARY samples")
    if not exact_variable_order(result.variables, variables):
        raise ValueError("result variable order does not match the fixture lowering exactly")
    return vartype


def _knapsack_candidate_from_result(
    encoding: KnapsackEncoding,
    result: SampleResult,
) -> dict[str, Any]:
    """Decode all feasible words and rank them by the native lexicographic rule."""
    vartype = _require_encoding_variable_order(result, encoding.variables)
    best_key: tuple[int, int] | None = None
    witnesses: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    invalid_sample_count = 0
    for sample in result.samples:
        try:
            selection = encoding.decode(sample, vartype=vartype)
        except ValueError:
            invalid_sample_count += 1
            continue
        value, weight = encoding.native_evaluation(selection)
        key = (-value, weight)
        if best_key is None or key < best_key:
            best_key = key
            witnesses = []
            seen = set()
        if key == best_key and selection not in seen and len(witnesses) < MAX_WITNESSES:
            seen.add(selection)
            witnesses.append(list(selection))
    if best_key is None:
        raise ValueError("result contains no feasible decoded knapsack witness")
    return {
        "max_value": -best_key[0],
        "weight_at_optimum": best_key[1],
        "capacity": encoding.capacity,
        "witness_selections": witnesses,
        "lowering_evidence": {
            "native_selection_basis": "maximize value, then minimize weight among feasible decodes",
            "decoded_feasible_sample_count": len(result.samples) - invalid_sample_count,
            "decoded_invalid_sample_count": invalid_sample_count,
            "penalty_policy": encoding.penalty_policy.to_metadata(),
        },
    }


def _tsp_candidate_from_result(encoding: TspEncoding, result: SampleResult) -> dict[str, Any]:
    """Decode all feasible words and rank them by native cyclic tour length."""
    vartype = _require_encoding_variable_order(result, encoding.variables)
    best_length: float | None = None
    witnesses: list[list[int]] = []
    seen: set[tuple[int, ...]] = set()
    invalid_sample_count = 0
    for sample in result.samples:
        try:
            tour = encoding.decode(sample, vartype=vartype)
        except ValueError:
            invalid_sample_count += 1
            continue
        length = encoding.native_length(tour)
        if best_length is None or length < best_length - DEFAULT_TOLERANCE:
            best_length = length
            witnesses = []
            seen = set()
        if best_length is not None and abs(length - best_length) <= DEFAULT_TOLERANCE:
            if tour not in seen and len(witnesses) < MAX_WITNESSES:
                seen.add(tour)
                witnesses.append(list(tour))
    if best_length is None:
        raise ValueError("result contains no feasible decoded TSP witness")
    return {
        "num_cities": encoding.num_cities,
        "optimal_tour_length": best_length,
        "witness_tours": witnesses,
        "lowering_evidence": {
            "native_selection_basis": "minimize native cyclic tour length among feasible decodes",
            "decoded_feasible_sample_count": len(result.samples) - invalid_sample_count,
            "decoded_invalid_sample_count": invalid_sample_count,
            "penalty_policy": encoding.penalty_policy.to_metadata(),
        },
    }


def verify_optimum_claim(
    fixture: dict[str, Any], actual: Any, tolerance: float = DEFAULT_TOLERANCE
) -> list[dict[str, Any]]:
    """Score a candidate under the optimization-claim criterion.

    Like :func:`gibbsiq.benchmark_oracle.verify_benchmark_fixture` but
    enumeration-only keys may be omitted (checked if volunteered). Witness
    verification is mandatory and recomputes each objective from the input
    model. Returns a list of difference dicts (empty == pass).
    """
    return score_candidate(fixture, actual, tolerance, optional_keys=ENUMERATION_ONLY_KEYS)
