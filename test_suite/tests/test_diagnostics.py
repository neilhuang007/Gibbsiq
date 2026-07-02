"""Unit tests for ``src/gibbsiq/diagnostics.py``.

Covers status precedence (insufficient_data before constancy), chain
splitting, per-flag boundary conditions, the four-draw Geyer edge case,
diversity math against hand-computed values, family-scoped flag emission,
the fixture adapter against every golden diagnostic fixture, the
magnetization/distance-to-best trace helpers, and the top-level
``compute_diagnostics`` payload.
"""

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
    chain_section,
    compute_diagnostics,
    diagnostic_candidate_from_input,
    distance_to_best_trace,
    diversity_flags,
    diversity_section,
    energy_flags,
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

    def test_short_constant_trace_is_insufficient_not_constant(self) -> None:
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
    def test_odd_length_chain_drops_the_middle_draw(self) -> None:
        self.assertEqual(split_chains([[1, 2, 3, 4, 5]]), [[1.0, 2.0], [4.0, 5.0]])

    def test_even_length_chain_splits_exactly(self) -> None:
        self.assertEqual(split_chains([[1, 2, 3, 4]]), [[1.0, 2.0], [3.0, 4.0]])

    def test_ragged_chains_are_truncated_before_splitting(self) -> None:
        self.assertEqual(split_chains([[1, 2, 3], [1, 2]]), [[1.0], [1.0], [2.0], [2.0]])

    def test_empty_chain_is_dropped_before_splitting(self) -> None:
        self.assertEqual(split_chains([[1, 2, 3, 4], []]), [[1.0, 2.0], [3.0, 4.0]])


class FlagBoundaryTests(unittest.TestCase):
    """Each flag predicate exercised directly against a minimal section dict."""

    def test_low_ess_boundary(self) -> None:
        self.assertEqual(energy_flags({"ess_status": "ok", "ess": 399.999999999}), ["low_ess"])
        self.assertEqual(energy_flags({"ess_status": "ok", "ess": 400.0}), [])

    def test_mode_collapse_boundary(self) -> None:
        self.assertEqual(diversity_flags({"top1_mass": 0.9}), ["mode_collapse"])
        self.assertEqual(diversity_flags({"top1_mass": 0.8999}), [])

    def test_low_diversity_boundary(self) -> None:
        self.assertEqual(diversity_flags({"unique_fraction": 0.05}), ["low_diversity"])
        self.assertEqual(diversity_flags({"unique_fraction": 0.0501}), [])

    def test_chain_disagreement_rhat_boundary(self) -> None:
        self.assertEqual(chain_flags({"rhat_status": "ok", "rhat": 1.0100001}), ["chain_disagreement"])
        self.assertEqual(chain_flags({"rhat_status": "ok", "rhat": 1.01}), [])

    def test_chain_disagreement_fires_on_zero_within_variance_regardless_of_rhat(self) -> None:
        result = chain_flags({"rhat_status": diagnostics.STATUS_ZERO_WITHIN_VARIANCE, "rhat": None})
        self.assertEqual(result, ["chain_disagreement"])

    def test_poor_mixing_boundary(self) -> None:
        fires = {"autocorrelation_status": "ok", "tau_hat": 2.1, "draws_per_chain": 100}
        silent = {"autocorrelation_status": "ok", "tau_hat": 1.9, "draws_per_chain": 100}
        self.assertEqual(energy_flags(fires), ["poor_mixing"])
        self.assertEqual(energy_flags(silent), [])

    def test_no_recent_improvement_fires_only_on_false(self) -> None:
        self.assertEqual(energy_flags({"recent_improvement": False}), ["no_recent_improvement"])
        self.assertEqual(energy_flags({"recent_improvement": None}), [])
        self.assertEqual(energy_flags({"recent_improvement": True}), [])

    def test_zero_energy_variance_requires_a_positive_count(self) -> None:
        self.assertEqual(energy_flags({"variance": 0.0, "count": 5}), ["zero_energy_variance"])
        self.assertEqual(energy_flags({"variance": 0.0, "count": 0}), [])


class GeyerFourDrawEdgeTests(unittest.TestCase):
    def test_four_draw_single_chain_floors_tau_at_the_size_bound(self) -> None:
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
        self.assertEqual(section["top1_mass"], 0.75)
        expected_entropy = -0.75 * math.log(0.75) - 0.25 * math.log(0.25)
        self.assertAlmostEqual(section["entropy_nats"], expected_entropy, places=12)
        self.assertAlmostEqual(section["mean_pairwise_hamming_distance"], 0.5, places=12)
        self.assertAlmostEqual(section["normalized_mean_pairwise_hamming_distance"], 0.25, places=12)

    def test_single_read_has_no_pairwise_hamming_distance(self) -> None:
        section = diversity_section({(1, 1): 1}, num_variables=2)
        self.assertIsNone(section["mean_pairwise_hamming_distance"])
        self.assertIsNone(section["normalized_mean_pairwise_hamming_distance"])


class FamilyScopingTests(unittest.TestCase):
    def test_chain_family_flags_never_include_low_ess(self) -> None:
        fixtures = {fixture["id"]: fixture for fixture in load_diagnostic_fixtures()}
        fixture = fixtures["chain_disagreement_zero_within_variance"]
        candidate = diagnostic_candidate_from_input(fixture["input"])
        self.assertEqual(candidate["required_flags"], ["chain_disagreement", "zero_within_chain_variance"])
        self.assertNotIn("low_ess", candidate["required_flags"])


class AdapterVsGoldenTests(unittest.TestCase):
    def test_every_fixture_adapter_matches_its_golden_expected_block(self) -> None:
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


class ComputeDiagnosticsPayloadTests(unittest.TestCase):
    def test_payload_has_all_top_level_keys_and_is_json_safe(self) -> None:
        energy_chains = [[0.0, 1.0, 0.5, 1.5, 0.25], [0.2, -0.3, 0.6, 0.1, -0.4]]
        samples = [{"a": 1}, {"a": -1}, {"a": 1}, {"a": 1}, {"a": -1}]
        variables = ["a"]
        payload = compute_diagnostics(
            energy_chains=energy_chains,
            samples=samples,
            variables=variables,
            timings={"sample_seconds": 2.0},
        )

        for key in ("energy", "diversity", "chains", "constraints", "runtime", "flags", "thresholds"):
            self.assertIn(key, payload)

        energy = energy_section(energy_chains)
        chains_section = chain_section(energy_chains)
        diversity = diversity_section(state_counts(samples, variables), len(variables))
        expected_flags = set(energy_flags(energy)) | set(chain_flags(chains_section)) | set(diversity_flags(diversity))
        expected_order = [flag for flag in diagnostics.FLAG_ORDER if flag in expected_flags]
        self.assertEqual(payload["flags"], expected_order)

        self.assertEqual(payload["thresholds"], diagnostics.thresholds_summary())

        round_tripped = json.loads(json.dumps(payload))
        self.assertEqual(round_tripped, payload)
        self.assertIsNone(find_nan_or_inf(payload))


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


if __name__ == "__main__":
    unittest.main()
