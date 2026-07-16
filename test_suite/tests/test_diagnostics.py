"""Unit tests for ``src/gibbsiq/diagnostics.py``."""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import diagnostics  # noqa: E402
from gibbsiq.diagnostics import (  # noqa: E402
    chain_flags,
    chain_observations,
    chain_section,
    compute_diagnostics,
    diagnostic_candidate_from_input,
    distance_to_best_trace,
    diversity_flags,
    diversity_observations,
    diversity_section,
    energy_flags,
    energy_observations,
    energy_section,
    ess_mean,
    magnetization_trace,
    split_chains,
    state_counts,
)
from gibbsiq.evaluation import compare_values  # noqa: E402

FIXTURE_PATH = REPO_ROOT / "reference" / "08-evaluation" / "fixtures" / "diagnostic-fixtures.json"
TOLERANCE = 1e-9


def load_diagnostic_fixtures() -> list[dict]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8-sig"))
    return payload["fixtures"]


def find_nan_or_inf(value, path: str = "$"):
    """Return a path string to the first NaN/Inf float found, else None."""
    if isinstance(value, float):
        return path if (math.isnan(value) or math.isinf(value)) else None
    if isinstance(value, dict):
        for key, item in value.items():
            found = find_nan_or_inf(item, f"{path}.{key}")
            if found is not None:
                return found
        return None
    if isinstance(value, list):
        for index, item in enumerate(value):
            found = find_nan_or_inf(item, f"{path}[{index}]")
            if found is not None:
                return found
        return None
    return None


class StatusPrecedenceTests(unittest.TestCase):
    """insufficient_data (fewer than 4 raw draws) must be checked before constancy."""

    def test_short_constant_trace_is_insufficient_data(self) -> None:
        result = ess_mean([[5.0, 5.0, 5.0]])
        self.assertEqual(result["autocorrelation_status"], diagnostics.STATUS_INSUFFICIENT_DATA)
        self.assertEqual(result["ess_status"], diagnostics.STATUS_INSUFFICIENT_DATA)

    def test_long_constant_trace_is_constant_trace(self) -> None:
        result = ess_mean([[5.0] * 20])
        self.assertEqual(result["autocorrelation_status"], diagnostics.STATUS_CONSTANT_TRACE)
        self.assertEqual(result["ess_status"], diagnostics.STATUS_UNDEFINED_CONSTANT_TRACE)

    def test_empty_chain_list_is_insufficient_data(self) -> None:
        result = ess_mean([])
        self.assertEqual(result["autocorrelation_status"], diagnostics.STATUS_INSUFFICIENT_DATA)
        self.assertEqual(result["ess_status"], diagnostics.STATUS_INSUFFICIENT_DATA)

    def test_list_of_empty_chains_is_insufficient_data(self) -> None:
        result = ess_mean([[], []])
        self.assertEqual(result["autocorrelation_status"], diagnostics.STATUS_INSUFFICIENT_DATA)
        self.assertEqual(result["ess_status"], diagnostics.STATUS_INSUFFICIENT_DATA)

    def test_single_read_is_insufficient_data(self) -> None:
        result = ess_mean([[5.0]])
        self.assertEqual(result["autocorrelation_status"], diagnostics.STATUS_INSUFFICIENT_DATA)
        self.assertEqual(result["ess_status"], diagnostics.STATUS_INSUFFICIENT_DATA)


class SplitChainsTests(unittest.TestCase):
    def test_odd_length_chain_drops_middle_draw(self) -> None:
        self.assertEqual(split_chains([[1, 2, 3, 4, 5]]), [[1.0, 2.0], [4.0, 5.0]])

    def test_even_length_chain_splits_exactly(self) -> None:
        self.assertEqual(split_chains([[1, 2, 3, 4]]), [[1.0, 2.0], [3.0, 4.0]])

    def test_ragged_chains_truncate_before_split(self) -> None:
        self.assertEqual(split_chains([[1, 2, 3], [1, 2]]), [[1.0], [1.0], [2.0], [2.0]])

    def test_empty_chain_dropped_before_split(self) -> None:
        self.assertEqual(split_chains([[1, 2, 3, 4], []]), [[1.0, 2.0], [3.0, 4.0]])


class FlagBoundaryTests(unittest.TestCase):
    """Each flag predicate exercised directly against a minimal section dict."""

    def test_energy_ess_has_no_health_threshold(self) -> None:
        self.assertEqual(energy_flags({"ess_status": "ok", "ess": 399.999999999}), [])
        self.assertNotIn("low_ess", diagnostics.FLAG_ORDER)
        self.assertNotIn("low_ess", diagnostics.thresholds_summary())

    def test_high_sample_concentration_boundary(self) -> None:
        self.assertEqual(
            diversity_observations({"top1_mass": 0.9}),
            ["high_sample_concentration"],
        )
        self.assertEqual(diversity_observations({"top1_mass": 0.8999}), [])
        self.assertEqual(diversity_flags({"top1_mass": 1.0}), [])

    def test_concentrated_exact_boltzmann_target_is_not_mode_collapse(self) -> None:
        # For one spin with h=1 and beta=ln(19)/2, P(s=-1)=19/20 exactly.
        section = diversity_section({(-1,): 95, (1,): 5}, num_variables=1)
        self.assertEqual(section["top1_mass"], 0.95)
        self.assertNotIn("mode_collapse", diversity_flags(section))
        self.assertEqual(diversity_observations(section), ["high_sample_concentration"])

    def test_low_diversity_boundary(self) -> None:
        self.assertEqual(diversity_flags({"occupancy_efficiency": 0.05}), ["low_diversity"])
        self.assertEqual(diversity_flags({"occupancy_efficiency": 0.0501}), [])

    def test_low_diversity_maps_to_unique_fraction(self) -> None:
        self.assertEqual(diversity_flags({"unique_fraction": 0.05}), ["low_diversity"])
        self.assertEqual(diversity_flags({"unique_fraction": 0.0501}), [])

    def test_chain_disagreement_rhat_boundary(self) -> None:
        self.assertEqual(chain_flags({"rhat_status": "ok", "rhat": 1.0100001}), ["chain_disagreement"])
        self.assertEqual(chain_flags({"rhat_status": "ok", "rhat": 1.01}), [])

    def test_chain_disagreement_on_zero_within_variance(self) -> None:
        result = chain_flags({"rhat_status": diagnostics.STATUS_ZERO_WITHIN_VARIANCE, "rhat": None})
        self.assertEqual(result, ["chain_disagreement"])

    def test_poor_mixing_boundary(self) -> None:
        fires = {"autocorrelation_status": "ok", "tau_hat": 2.1, "draws_per_chain": 100}
        silent = {"autocorrelation_status": "ok", "tau_hat": 1.9, "draws_per_chain": 100}
        self.assertEqual(energy_flags(fires), ["poor_mixing"])
        self.assertEqual(energy_flags(silent), [])

    def test_recent_improvement_false_is_observation(self) -> None:
        self.assertEqual(energy_flags({"recent_improvement": False}), [])
        self.assertEqual(energy_observations({"recent_improvement": False}), ["no_recent_improvement"])
        self.assertEqual(energy_observations({"recent_improvement": None}), [])
        self.assertEqual(energy_observations({"recent_improvement": True}), [])

    def test_zero_energy_variance_needs_positive_count(self) -> None:
        self.assertEqual(energy_flags({"variance": 0.0, "count": 5}), [])
        self.assertEqual(energy_observations({"variance": 0.0, "count": 5}), ["zero_energy_variance"])
        self.assertEqual(energy_observations({"variance": 0.0, "count": 0}), [])

    def test_zero_within_chain_variance_as_observation(self) -> None:
        section = {"split_within_chain_variance": 0.0}
        self.assertEqual(chain_flags(section), [])
        self.assertEqual(chain_observations(section), ["zero_within_chain_variance"])


class GeyerFourDrawEdgeTests(unittest.TestCase):
    def test_four_draw_chain_floors_tau_at_size_bound(self) -> None:
        result = ess_mean([[0.0, 1.0, 0.5, 1.5]])
        self.assertEqual(result["ess_status"], "ok")
        expected_tau = 1.0 / math.log10(4.0)
        self.assertAlmostEqual(result["tau_hat"], expected_tau, places=12)
        self.assertAlmostEqual(result["ess"], 4.0 / expected_tau, places=9)


class DiversityMathTests(unittest.TestCase):
    def test_diversity_section_matches_hand_computed_values(self) -> None:
        section = diversity_section({(1, 1): 3, (1, -1): 1}, num_variables=2)
        self.assertEqual(section["num_reads"], 4)
        self.assertEqual(section["unique_fraction"], 0.5)
        self.assertEqual(section["occupancy_efficiency"], 0.5)
        self.assertEqual(section["top1_mass"], 0.75)
        expected_entropy = -0.75 * math.log(0.75) - 0.25 * math.log(0.25)
        self.assertAlmostEqual(section["entropy_nats"], expected_entropy, places=12)
        self.assertAlmostEqual(section["mean_pairwise_hamming_distance"], 0.5, places=12)
        self.assertAlmostEqual(section["normalized_mean_pairwise_hamming_distance"], 0.25, places=12)

    def test_single_read_has_no_pairwise_hamming_distance(self) -> None:
        section = diversity_section({(1, 1): 1}, num_variables=2)
        self.assertIsNone(section["mean_pairwise_hamming_distance"])
        self.assertIsNone(section["normalized_mean_pairwise_hamming_distance"])

    def test_finite_support_occupancy_stays_stable(self) -> None:
        counts = {(1, 1): 25, (1, -1): 25, (-1, 1): 25, (-1, -1): 25}
        section = diversity_section(counts, num_variables=2)
        self.assertEqual(section["unique_fraction"], 0.04)
        self.assertEqual(section["occupancy_efficiency"], 1.0)
        self.assertNotIn("low_diversity", diversity_flags(section))

    def test_support_bound_caps_large_variable_count(self) -> None:
        section = diversity_section({(1,): 1}, num_variables=1_000_000)
        self.assertEqual(section["occupancy_efficiency"], 1.0)


class FamilyScopingTests(unittest.TestCase):
    def test_chain_family_flags_exclude_low_ess(self) -> None:
        fixtures = {fixture["id"]: fixture for fixture in load_diagnostic_fixtures()}
        fixture = fixtures["chain_disagreement_zero_within_variance"]
        candidate = diagnostic_candidate_from_input(fixture["input"])
        self.assertEqual(candidate["required_flags"], ["chain_disagreement"])
        self.assertEqual(candidate["observations"], ["zero_within_chain_variance"])
        self.assertNotIn("low_ess", candidate["required_flags"])


class AdapterVsGoldenTests(unittest.TestCase):
    def test_fixture_adapter_matches_golden_expected(self) -> None:
        fixtures = load_diagnostic_fixtures()
        self.assertEqual(len(fixtures), 7)
        for fixture in fixtures:
            candidate = diagnostic_candidate_from_input(fixture["input"])
            differences = compare_values(fixture["expected"], candidate, fixture["id"], TOLERANCE)
            self.assertEqual(differences, [], msg=f"fixture={fixture['id']} differences={differences}")


class TraceHelperTests(unittest.TestCase):
    def test_magnetization_and_distance_to_best_traces(self) -> None:
        variables = ["a", "b"]
        chains = [
            [{"a": 1, "b": 1}, {"a": 1, "b": -1}],
            [{"a": -1, "b": -1}],
        ]

        self.assertEqual(magnetization_trace(chains, variables), [[1.0, 0.0], [-1.0]])

        best_sample = {"a": 1, "b": 1}
        self.assertEqual(distance_to_best_trace(chains, best_sample, variables), [[0, 1], [2]])

    def test_sample_helpers_reject_equality_alias_variable_keys(self) -> None:
        aliases = (
            (True, 1),
            ((True,), (1,)),
            (frozenset({True}), frozenset({1})),
        )
        for sample_label, variable in aliases:
            sample = {sample_label: 1}
            calls = (
                lambda sample=sample, variable=variable: state_counts([sample], [variable]),
                lambda sample=sample, variable=variable: magnetization_trace([[sample]], [variable]),
                lambda sample=sample, variable=variable: distance_to_best_trace(
                    [[sample]], sample, [variable]
                ),
                lambda sample=sample, variable=variable: compute_diagnostics(
                    energy_chains=[[0.0]],
                    samples=[sample],
                    variables=[variable],
                ),
            )
            for call in calls:
                with self.subTest(sample_label=sample_label, variable=variable, call=call):
                    with self.assertRaisesRegex(ValueError, "sample variable labels"):
                        call()
            spin_section = diagnostics.spin_chain_section([sample], [variable], [[0.0]])
            self.assertEqual(spin_section["status"], diagnostics.STATUS_NOT_AVAILABLE)
            self.assertIn("sample variable labels", spin_section["reason"])

    def test_empty_variable_magnetization_is_explicitly_undefined(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one variable"):
            magnetization_trace([[{}]], [])

    def test_large_reordered_sample_key_lookup_smoke(self) -> None:
        variables = tuple(range(5_000))
        sample = {variable: 1 for variable in reversed(variables)}

        counts = state_counts([sample], variables)

        self.assertEqual(counts, {(1,) * len(variables): 1})


class ComputeDiagnosticsPayloadTests(unittest.TestCase):
    def test_payload_top_level_keys_are_json_safe(self) -> None:
        energy_chains = [[0.0, 1.0, 0.5, 1.5, 0.25], [0.2, -0.3, 0.6, 0.1, -0.4]]
        samples = [{"a": 1}, {"a": -1}, {"a": 1}, {"a": 1}, {"a": -1}]
        variables = ["a"]
        payload = compute_diagnostics(
            energy_chains=energy_chains,
            samples=samples,
            variables=variables,
            timings={"sample_seconds": 2.0},
        )

        for key in (
            "energy",
            "diversity",
            "chains",
            "constraints",
            "runtime",
            "flags",
            "observations",
            "thresholds",
        ):
            self.assertIn(key, payload)

        energy = energy_section(energy_chains)
        chains_section = chain_section(energy_chains)
        diversity = diversity_section(state_counts(samples, variables), len(variables))
        expected_flags = (
            set(energy_flags(energy)) | set(chain_flags(chains_section)) | set(diversity_flags(diversity))
        )
        expected_order = [flag for flag in diagnostics.FLAG_ORDER if flag in expected_flags]
        self.assertEqual(payload["flags"], expected_order)
        expected_observations = (
            set(energy_observations(energy))
            | set(chain_observations(chains_section))
            | set(diversity_observations(diversity))
        )
        expected_observation_order = [
            observation
            for observation in diagnostics.OBSERVATION_ORDER
            if observation in expected_observations
        ]
        self.assertEqual(payload["observations"], expected_observation_order)

        self.assertEqual(payload["thresholds"], diagnostics.thresholds_summary())

        round_tripped = json.loads(json.dumps(payload))
        self.assertEqual(round_tripped, payload)
        self.assertIsNone(find_nan_or_inf(payload))

    def test_large_finite_energy_scale_does_not_overflow(self) -> None:
        magnitude = 1e154
        energy_chains = [
            [magnitude, -magnitude, magnitude, -magnitude],
            [magnitude, -magnitude, magnitude, -magnitude],
        ]

        payload = compute_diagnostics(energy_chains=energy_chains)

        self.assertEqual(payload["energy"]["mean"], 0.0)
        self.assertEqual(payload["energy"]["variance"], 1e308)
        self.assertEqual(payload["energy"]["ess_status"], "ok")
        self.assertTrue(math.isfinite(payload["energy"]["ess"]))
        self.assertTrue(math.isfinite(payload["energy"]["tau_hat"]))
        json.dumps(payload, allow_nan=False)

    def test_unequal_chain_truncation_reports_every_discarded_draw(self) -> None:
        section = chain_section([[0.0] * 100, [1.0] * 4, [], [2.0] * 7])

        self.assertEqual(section["original_draws_by_chain"], [100, 4, 0, 7])
        self.assertEqual(section["diagnostic_draws_used_by_chain"], [4, 4, 0, 4])
        self.assertEqual(section["diagnostic_discarded_draws_by_chain"], [96, 0, 0, 3])
        self.assertEqual(section["diagnostic_discarded_draws"], 99)


class ReadsPerSecondTests(unittest.TestCase):
    def test_zero_sample_seconds_yields_none(self) -> None:
        payload = compute_diagnostics(
            energy_chains=[[0.0, 1.0, 2.0, 3.0]],
            timings={"sample_seconds": 0.0},
        )
        self.assertIsNone(payload["runtime"]["reads_per_second"])

    def test_reads_per_second_uses_sample_count_over_seconds(self) -> None:
        payload = compute_diagnostics(
            energy_chains=[[0.0, 1.0, 2.0, 3.0]],
            samples=[{"a": 1}] * 10,
            variables=["a"],
            timings={"sample_seconds": 2.0},
        )
        self.assertEqual(payload["runtime"]["reads_per_second"], 5.0)


class NonFiniteInputRejectionTests(unittest.TestCase):
    """NaN/Inf energy values raise ValueError at the boundary (EVAL-EQ-007)."""

    # Guards the baseline-adapter path: THRML itself cannot produce non-finite
    # energies, but a NaN/Inf must not leak into serialized output (e.g. NaN
    # rhat under an "ok" status) or silently truncate the Geyer scan.

    NAN_CHAINS = [[1.0, 2.0, float("nan"), 4.0, 5.0, 6.0], [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]]
    INF_CHAINS = [[1.0, 2.0, float("inf"), 4.0, 5.0, 6.0], [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]]

    def test_ess_mean_rejects_nan(self) -> None:
        with self.assertRaises(ValueError):
            ess_mean(self.NAN_CHAINS)

    def test_split_rhat_rejects_inf(self) -> None:
        with self.assertRaises(ValueError):
            diagnostics.split_rhat(self.INF_CHAINS)

    def test_energy_section_rejects_nan(self) -> None:
        with self.assertRaises(ValueError):
            energy_section(self.NAN_CHAINS)

    def test_compute_diagnostics_rejects_negative_inf(self) -> None:
        chains = [[1.0, 2.0, float("-inf"), 4.0, 5.0, 6.0]]
        with self.assertRaises(ValueError):
            compute_diagnostics(energy_chains=chains)


class OneStuckChainAmongVaryingChainsTests(unittest.TestCase):
    """One frozen chain among varying chains keeps W positive, so rhat takes the numeric path."""

    def test_numeric_rhat_path_flags_disagreement(self) -> None:
        chains = [
            [3.0] * 20,
            [1.0, 2.0] * 10,
            [1.5, 2.5] * 10,
            [1.2, 2.2] * 10,
        ]
        section = chain_section(chains)
        self.assertEqual(section["rhat_status"], "ok")
        self.assertGreater(section["rhat"], 1.01)
        flags = chain_flags(section)
        self.assertIn("chain_disagreement", flags)
        self.assertNotIn("zero_within_chain_variance", flags)


if __name__ == "__main__":
    unittest.main()
