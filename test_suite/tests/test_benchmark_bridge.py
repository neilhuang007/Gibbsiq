"""Benchmark-bridge tests: lowering fidelity, anti-cheat scoring, end-to-end runs."""

# Three layers: (1) compile_fixture is checked against independent exhaustive
# enumeration on every brute-forceable instance, with the expected block
# stripped; (2) doctored/missing/invalid witnesses must fail
# verify_optimum_claim; (3) THRML solves published instances (Petersen
# Max-Cut 12 per Barahona 1983, K_{3,3}, odd cycle C7, an SK glass) and a
# flipped witness spin still fails. The end-to-end classes skip without the
# optional thrml extra.

from __future__ import annotations

import itertools
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.benchmark_bridge import (  # noqa: E402
    ENUMERATION_ONLY_KEYS,
    MAX_WITNESSES,
    SUPPORTED_FAMILIES,
    candidate_from_result,
    compile_fixture,
    optimal_spin_witnesses,
    verify_optimum_claim,
)
from gibbsiq.benchmark_oracle import verify_benchmark_fixture  # noqa: E402
from gibbsiq.result import SampleResult  # noqa: E402

try:
    import thrml  # noqa: F401

    THRML_AVAILABLE = True
except ImportError:
    THRML_AVAILABLE = False

if THRML_AVAILABLE:
    from gibbsiq import SamplerConfig, THRMLSampler

CORPUS_PATH = REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"
CORPUS = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
FIXTURES = {fixture["id"]: fixture for fixture in CORPUS["fixtures"]}
TOLERANCE = 1e-9
# Full 2^n enumeration stays fast up to this size; larger fixtures are covered
# by the witness-energy check instead.
ENUMERATION_LIMIT = 10


def supported_fixtures() -> list[dict]:
    return [f for f in CORPUS["fixtures"] if f["family"] in SUPPORTED_FAMILIES]


def strip_expected(fixture: dict) -> dict:
    """Fixture copy with all proven answers removed (anti-cheat harness)."""
    return {key: value for key, value in fixture.items() if key != "expected"}


def brute_force_minimum_energy(model) -> float:
    best = None
    variables = model.variables
    for spins in itertools.product((-1, 1), repeat=len(variables)):
        energy = model.energy(dict(zip(variables, spins)))
        if best is None or energy < best:
            best = energy
    return best


def expected_optimum_energy(fixture: dict) -> float:
    family = fixture["family"]
    expected = fixture["expected"]
    if family == "maxcut":
        return float(expected["best_ising_energy"])
    if family == "sk_spin_glass":
        return float(expected["ground_state_energy"])
    if family == "number_partition":
        difference = expected["min_subset_sum_difference"]
        return float(difference * difference)
    raise AssertionError(f"unsupported family {family!r}")


class CompileFixtureFidelityTests(unittest.TestCase):
    def test_lowering_never_reads_expected_block(self) -> None:
        for fixture in supported_fixtures():
            with_expected = compile_fixture(fixture)
            without_expected = compile_fixture(strip_expected(fixture))
            self.assertEqual(with_expected.variables, without_expected.variables, msg=fixture["id"])
            self.assertEqual(dict(with_expected.linear), dict(without_expected.linear), msg=fixture["id"])
            self.assertEqual(
                dict(with_expected.quadratic), dict(without_expected.quadratic), msg=fixture["id"]
            )
            self.assertEqual(with_expected.offset, without_expected.offset, msg=fixture["id"])

    def test_expected_spin_witnesses_attain_expected_energy(self) -> None:
        # Ties the lowering to the corpus: every stored witness must land
        # exactly on the proven optimum once evaluated through the lowered model.
        for fixture in supported_fixtures():
            if fixture["family"] == "number_partition":
                continue  # partition witnesses are set pairs, not spin states
            model = compile_fixture(fixture)
            optimum = expected_optimum_energy(fixture)
            for witness in fixture["expected"]["witness_spin_samples"]:
                spins = {variable: int(spin) for variable, spin in witness.items()}
                self.assertAlmostEqual(
                    model.energy(spins),
                    optimum,
                    delta=TOLERANCE,
                    msg=f"{fixture['id']} witness does not attain the proven optimum",
                )

    def test_independent_enumeration_confirms_lowered_optimum(self) -> None:
        # Strongest fidelity proof: re-enumerate the lowered model and require
        # its true minimum to match the fixture's proven optimum.
        checked = 0
        for fixture in supported_fixtures():
            model = compile_fixture(fixture)
            if len(model.variables) > ENUMERATION_LIMIT:
                continue
            self.assertAlmostEqual(
                brute_force_minimum_energy(model),
                expected_optimum_energy(fixture),
                delta=TOLERANCE,
                msg=fixture["id"],
            )
            checked += 1
        self.assertGreaterEqual(checked, 10, "expected at least ten brute-forceable fixtures")

    def test_unsupported_families_raise(self) -> None:
        for family in ("knapsack", "tsp"):
            fixture = next(f for f in CORPUS["fixtures"] if f["family"] == family)
            with self.assertRaises(NotImplementedError):
                compile_fixture(fixture)


class VerifyOptimumClaimAntiCheatTests(unittest.TestCase):
    """Adversarial candidates against the Petersen Max-Cut fixture."""

    def setUp(self) -> None:
        self.fixture = FIXTURES["gt_maxcut_petersen"]
        self.honest = {
            key: value for key, value in self.fixture["expected"].items() if key not in ENUMERATION_ONLY_KEYS
        }

    def test_valid_candidate_passes(self) -> None:
        self.assertEqual(verify_optimum_claim(self.fixture, self.honest, TOLERANCE), [])

    def test_full_oracle_requires_degeneracy(self) -> None:
        self.assertEqual(verify_optimum_claim(self.fixture, self.honest, TOLERANCE), [])
        full = verify_benchmark_fixture(self.fixture, self.honest, TOLERANCE)
        self.assertTrue(any(diff["code"] == "missing_key" for diff in full))

    def test_extra_degeneracy_is_checked(self) -> None:
        candidate = dict(self.honest)
        candidate["ground_state_degeneracy"] = 999
        differences = verify_optimum_claim(self.fixture, candidate, TOLERANCE)
        self.assertTrue(any(diff["code"] == "value_mismatch" for diff in differences))

    def test_doctored_witness_is_rejected(self) -> None:
        candidate = dict(self.honest)
        witness = dict(candidate["witness_spin_samples"][0])
        first_variable = next(iter(witness))
        witness[first_variable] = -witness[first_variable]
        candidate["witness_spin_samples"] = [witness]
        differences = verify_optimum_claim(self.fixture, candidate, TOLERANCE)
        self.assertTrue(any(diff["code"] == "witness_not_optimal" for diff in differences))

    def test_inflated_optimum_claim_is_rejected(self) -> None:
        # Claims a better cut than the published optimum of 12; the scalar
        # check fails even though the witness itself is genuine.
        candidate = dict(self.honest)
        candidate["best_cut_value"] = 13
        candidate["best_ising_energy"] = -11.0
        differences = verify_optimum_claim(self.fixture, candidate, TOLERANCE)
        codes = {diff["code"] for diff in differences}
        self.assertTrue(codes & {"value_mismatch", "float_mismatch"})

    def test_missing_witness_list_is_rejected(self) -> None:
        candidate = dict(self.honest)
        candidate["witness_spin_samples"] = []
        differences = verify_optimum_claim(self.fixture, candidate, TOLERANCE)
        self.assertTrue(any(diff["code"] == "missing_witness" for diff in differences))

    def test_witness_with_missing_variable_is_rejected(self) -> None:
        candidate = dict(self.honest)
        witness = dict(candidate["witness_spin_samples"][0])
        witness.pop(next(iter(witness)))
        candidate["witness_spin_samples"] = [witness]
        differences = verify_optimum_claim(self.fixture, candidate, TOLERANCE)
        self.assertTrue(any(diff["code"] == "invalid_witness" for diff in differences))

    def test_partition_witness_must_use_every_number(self) -> None:
        fixture = FIXTURES["gt_partition_n10_v20_s5"]
        honest = {
            key: value for key, value in fixture["expected"].items() if key not in ENUMERATION_ONLY_KEYS
        }
        cheat = dict(honest)
        witness = dict(honest["witness_partitions"][0])
        witness["set_plus"] = list(witness["set_plus"])[1:]  # drop a number
        cheat["witness_partitions"] = [witness]
        differences = verify_optimum_claim(fixture, cheat, TOLERANCE)
        self.assertTrue(any(diff["code"] == "witness_not_optimal" for diff in differences))


class CandidateFromResultTests(unittest.TestCase):
    """Candidate construction from hand-built results (no thrml required)."""

    def _optimal_petersen_sample(self) -> dict:
        fixture = FIXTURES["gt_maxcut_petersen"]
        witness = fixture["expected"]["witness_spin_samples"][0]
        return {variable: int(spin) for variable, spin in witness.items()}

    def test_maxcut_candidate_passes_oracle(self) -> None:
        fixture = FIXTURES["gt_maxcut_petersen"]
        model = compile_fixture(strip_expected(fixture))
        optimal = self._optimal_petersen_sample()
        suboptimal = dict(optimal)
        first_variable = model.variables[0]
        suboptimal[first_variable] = -suboptimal[first_variable]
        result = SampleResult.from_model(model, [suboptimal, optimal, optimal])
        candidate = candidate_from_result(strip_expected(fixture), result)
        self.assertEqual(candidate["best_cut_value"], 12)
        self.assertEqual(len(candidate["witness_spin_samples"]), 1)  # duplicates deduped
        self.assertEqual(verify_optimum_claim(fixture, candidate, TOLERANCE), [])

    def test_suboptimal_result_fails_oracle(self) -> None:
        fixture = FIXTURES["gt_maxcut_petersen"]
        model = compile_fixture(strip_expected(fixture))
        suboptimal = self._optimal_petersen_sample()
        suboptimal[model.variables[0]] = -suboptimal[model.variables[0]]
        result = SampleResult.from_model(model, [suboptimal])
        candidate = candidate_from_result(strip_expected(fixture), result)
        differences = verify_optimum_claim(fixture, candidate, TOLERANCE)
        self.assertTrue(differences, "a suboptimal candidate must not pass")

    def test_partition_candidate_passes_oracle(self) -> None:
        fixture = FIXTURES["gt_partition_n10_v20_s5"]
        model = compile_fixture(strip_expected(fixture))
        best_sample = None
        best_energy = None
        for spins in itertools.product((-1, 1), repeat=len(model.variables)):
            sample = dict(zip(model.variables, spins))
            energy = model.energy(sample)
            if best_energy is None or energy < best_energy:
                best_energy = energy
                best_sample = sample
        result = SampleResult.from_model(model, [best_sample])
        candidate = candidate_from_result(strip_expected(fixture), result)
        self.assertEqual(verify_optimum_claim(fixture, candidate, TOLERANCE), [])

    def test_witness_cap(self) -> None:
        # Coupling-free model: every state is optimal, so the witness list
        # must cap at MAX_WITNESSES distinct states.
        from gibbsiq import compile_ising

        model = compile_ising({str(i): 0.0 for i in range(4)})
        samples = [dict(zip(model.variables, spins)) for spins in itertools.product((-1, 1), repeat=4)]
        result = SampleResult.from_model(model, samples)
        witnesses = optimal_spin_witnesses(result)
        self.assertEqual(len(witnesses), MAX_WITNESSES)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class ThrmlFamousInstanceTests(unittest.TestCase):
    """End to end: THRML solves published instances; the oracle verifies."""

    def _solve(self, fixture_id: str, config, num_reads: int):
        fixture = FIXTURES[fixture_id]
        model = compile_fixture(strip_expected(fixture))
        result = THRMLSampler(config).sample(model, num_reads=num_reads)
        candidate = candidate_from_result(strip_expected(fixture), result)
        return fixture, candidate

    def test_petersen_maxcut(self) -> None:
        # Petersen graph, published optimum cut 12 (Barahona 1983).
        config = SamplerConfig(
            beta=3.0,
            n_warmup=400,
            steps_per_sample=3,
            warmup_beta_ladder=(0.3, 0.6, 1.2, 2.0, 3.0),
            num_chains=2,
            seed=7,
        )
        fixture, candidate = self._solve("gt_maxcut_petersen", config, num_reads=64)
        self.assertEqual(verify_optimum_claim(fixture, candidate, TOLERANCE), [])

    def test_complete_bipartite_k33_maxcut(self) -> None:
        config = SamplerConfig(
            beta=2.5,
            n_warmup=200,
            steps_per_sample=2,
            warmup_beta_ladder=(0.5, 1.0, 2.5),
            seed=3,
        )
        fixture, candidate = self._solve("gt_maxcut_bipartite_k33", config, num_reads=32)
        self.assertEqual(verify_optimum_claim(fixture, candidate, TOLERANCE), [])

    def test_odd_cycle_c7_maxcut(self) -> None:
        config = SamplerConfig(
            beta=2.5,
            n_warmup=200,
            steps_per_sample=2,
            warmup_beta_ladder=(0.5, 1.0, 2.5),
            seed=5,
        )
        fixture, candidate = self._solve("gt_maxcut_cycle_c7", config, num_reads=32)
        self.assertEqual(verify_optimum_claim(fixture, candidate, TOLERANCE), [])

    def test_sk_spin_glass_n8(self) -> None:
        config = SamplerConfig(
            beta=3.0,
            n_warmup=400,
            steps_per_sample=3,
            warmup_beta_ladder=(0.3, 0.75, 1.5, 3.0),
            num_chains=2,
            seed=11,
        )
        fixture, candidate = self._solve("gt_sk_n8_s13", config, num_reads=64)
        self.assertEqual(verify_optimum_claim(fixture, candidate, TOLERANCE), [])

    def test_doctored_thrml_candidate_fails(self) -> None:
        # A real-sampler candidate is still rejected once its witness is
        # tampered with after the fact.
        config = SamplerConfig(
            beta=2.5,
            n_warmup=200,
            steps_per_sample=2,
            warmup_beta_ladder=(0.5, 1.0, 2.5),
            seed=3,
        )
        fixture, candidate = self._solve("gt_maxcut_bipartite_k33", config, num_reads=32)
        self.assertEqual(verify_optimum_claim(fixture, candidate, TOLERANCE), [])
        witness = dict(candidate["witness_spin_samples"][0])
        variable = next(iter(witness))
        witness[variable] = -witness[variable]
        candidate["witness_spin_samples"] = [witness]
        differences = verify_optimum_claim(fixture, candidate, TOLERANCE)
        self.assertTrue(any(diff["code"] == "witness_not_optimal" for diff in differences))


if __name__ == "__main__":
    unittest.main()
