"""Independent checks for diagnostic trap fixtures."""

from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def load_diagnostics() -> dict[str, dict]:
    path = REPO_ROOT / "reference" / "08-evaluation" / "fixtures" / "diagnostic-fixtures.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return {fixture["id"]: fixture for fixture in payload["fixtures"]}


def variance(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)


def sample_variance(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / (len(values) - 1)


def best_improvement_count(trace: list[float]) -> int:
    best = math.inf
    improvements = 0
    for index, energy in enumerate(trace):
        if energy < best:
            if index > 0:
                improvements += 1
            best = energy
    return improvements


def hamming(left: dict[str, int], right: dict[str, int]) -> int:
    return sum(1 for variable in left if left[variable] != right[variable])


class DiagnosticFixtureMathTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = load_diagnostics()

    def test_concentrated_sample_metrics_from_counts(self) -> None:
        fixture = self.fixtures["mode_collapse_counts_n4_reads128"]
        sample_counts = fixture["input"]["sample_counts"]
        expected = fixture["expected"]

        total = sum(row["count"] for row in sample_counts)
        counts = sorted((row["count"] for row in sample_counts), reverse=True)
        probabilities = [count / total for count in counts]

        entropy = -sum(prob * math.log(prob) for prob in probabilities)

        weighted_distance = 0
        weighted_pairs = 0
        for left, right in itertools.combinations(sample_counts, 2):
            pair_count = left["count"] * right["count"]
            weighted_pairs += pair_count
            weighted_distance += pair_count * hamming(left["spin"], right["spin"])
        for row in sample_counts:
            same_state_pairs = row["count"] * (row["count"] - 1) // 2
            weighted_pairs += same_state_pairs

        mean_hamming = weighted_distance / weighted_pairs

        self.assertEqual(total, expected["num_reads"])
        self.assertEqual(len(sample_counts), expected["unique_states"])
        self.assertEqual(len(sample_counts) / total, expected["unique_fraction"])
        self.assertEqual(
            len(sample_counts) / min(total, 2 ** len(fixture["input"]["variables"])),
            expected["occupancy_efficiency"],
        )
        self.assertEqual(counts[0] / total, expected["top1_mass"])
        self.assertEqual(sum(counts[:3]) / total, expected["top3_mass"])
        self.assertAlmostEqual(entropy, expected["entropy_nats"], places=12)
        self.assertAlmostEqual(mean_hamming, expected["mean_pairwise_hamming_distance"], places=12)
        self.assertAlmostEqual(
            mean_hamming / len(fixture["input"]["variables"]),
            expected["normalized_mean_pairwise_hamming_distance"],
            places=12,
        )
        self.assertEqual(expected["required_flags"], [])
        self.assertEqual(expected["observations"], ["high_sample_concentration"])

    def test_constant_energy_trace_stats(self) -> None:
        fixture = self.fixtures["constant_energy_trace"]
        trace = fixture["input"]["energy_trace"]
        expected = fixture["expected"]

        best_so_far = []
        best = math.inf
        improvements = 0
        for energy in trace:
            if energy < best:
                if best < math.inf:
                    improvements += 1
                best = energy
            best_so_far.append(best)

        self.assertEqual(len(trace), expected["count"])
        self.assertEqual(min(trace), expected["min"])
        self.assertEqual(max(trace), expected["max"])
        self.assertEqual(variance(trace), expected["variance"])
        self.assertEqual(best, expected["best_energy"])
        self.assertEqual(improvements, expected["best_improvement_count"])
        self.assertEqual(best_so_far, trace)
        self.assertEqual(expected["autocorrelation_status"], "constant_trace")
        self.assertEqual(expected["ess_status"], "undefined_constant_trace")
        self.assertEqual(expected["required_flags"], [])
        self.assertCountEqual(expected["observations"], ["no_recent_improvement", "zero_energy_variance"])

    def test_chain_disagreement_zero_within_variance(self) -> None:
        fixture = self.fixtures["chain_disagreement_zero_within_variance"]
        chains = fixture["input"]["chains"]
        expected = fixture["expected"]

        means = [sum(chain["energy_trace"]) / len(chain["energy_trace"]) for chain in chains]
        within = [variance(chain["energy_trace"]) for chain in chains]
        draws_per_chain = len(chains[0]["energy_trace"])
        grand_mean = sum(means) / len(means)
        between = draws_per_chain / (len(chains) - 1) * sum((mean - grand_mean) ** 2 for mean in means)

        self.assertEqual(len(chains), expected["num_chains"])
        self.assertEqual(draws_per_chain, expected["draws_per_chain"])
        self.assertEqual(means, expected["chain_means"])
        self.assertEqual(within, expected["within_chain_variances"])
        self.assertEqual(between, expected["between_chain_variance"])
        self.assertEqual(expected["rhat_status"], "undefined_or_infinite_zero_within_variance")
        self.assertEqual(expected["required_flags"], ["chain_disagreement"])
        self.assertEqual(expected["observations"], ["zero_within_chain_variance"])

    def test_chain_disagreement_numeric_rhat(self) -> None:
        fixture = self.fixtures["chain_disagreement_numeric_rhat"]
        chains = sorted(fixture["input"]["chains"], key=lambda row: row["chain_id"])
        expected = fixture["expected"]

        chain_means = [sum(chain["energy_trace"]) / len(chain["energy_trace"]) for chain in chains]
        within_chain_variances = [variance(chain["energy_trace"]) for chain in chains]
        draws_per_chain = len(chains[0]["energy_trace"])
        unsplit_between = draws_per_chain * sample_variance(chain_means)

        half = draws_per_chain // 2
        split_rows = [chain["energy_trace"][:half] for chain in chains] + [
            chain["energy_trace"][-half:] for chain in chains
        ]
        split_within = sum(sample_variance(row) for row in split_rows) / len(split_rows)
        split_means = [sum(row) / len(row) for row in split_rows]
        split_between = half * sample_variance(split_means)
        rhat = math.sqrt((split_between / split_within + half - 1) / half)

        self.assertEqual(chain_means, expected["chain_means"])
        self.assertEqual(within_chain_variances, expected["within_chain_variances"])
        self.assertEqual(expected["chain_means"], [1.0, 2.0, 11.0, 12.0])
        self.assertEqual(expected["within_chain_variances"], [1.0, 1.0, 1.0, 1.0])
        self.assertAlmostEqual(unsplit_between, expected["between_chain_variance"], places=9)
        self.assertAlmostEqual(unsplit_between, 808.0 / 3.0, places=9)
        self.assertAlmostEqual(split_within, expected["split_within_chain_variance"], places=12)
        self.assertAlmostEqual(rhat, expected["rhat"], places=12)
        self.assertAlmostEqual(rhat, math.sqrt(627.0 / 28.0), places=12)
        self.assertCountEqual(expected["required_flags"], ["chain_disagreement"])

    def test_healthy_multichain_pooled_statistics(self) -> None:
        fixture = self.fixtures["healthy_multichain_energy_trace"]
        chains = sorted(fixture["input"]["chains"], key=lambda row: row["chain_id"])
        expected = fixture["expected"]

        chain_means = [sum(chain["energy_trace"]) / len(chain["energy_trace"]) for chain in chains]
        within_chain_variances = [variance(chain["energy_trace"]) for chain in chains]
        draws_per_chain = len(chains[0]["energy_trace"])
        between_chain_variance = draws_per_chain * sample_variance(chain_means)

        self.assertEqual(len(chains), expected["num_chains"])
        self.assertEqual(draws_per_chain, expected["draws_per_chain"])
        for actual_mean, expected_mean in zip(chain_means, expected["chain_means"]):
            self.assertAlmostEqual(actual_mean, expected_mean, places=9)
        for actual_variance, expected_variance in zip(
            within_chain_variances, expected["within_chain_variances"]
        ):
            self.assertAlmostEqual(actual_variance, expected_variance, places=9)
        self.assertAlmostEqual(between_chain_variance, expected["between_chain_variance"], places=9)

        self.assertLess(expected["rhat"], 1.01)
        self.assertGreater(expected["ess"], 400.0)
        self.assertEqual(expected["required_flags"], [])

    def test_autocorrelated_ar1_flags_poor_mixing(self) -> None:
        fixture = self.fixtures["autocorrelated_energy_trace_ar1"]
        trace = fixture["input"]["energy_trace"]
        expected = fixture["expected"]

        improvements = best_improvement_count(trace)

        self.assertEqual(len(trace), expected["count"])
        self.assertAlmostEqual(min(trace), expected["min"], places=9)
        self.assertAlmostEqual(max(trace), expected["max"], places=9)
        self.assertAlmostEqual(sum(trace) / len(trace), expected["mean"], places=9)
        self.assertAlmostEqual(variance(trace), expected["variance"], places=9)
        self.assertAlmostEqual(min(trace), expected["best_energy"], places=9)
        self.assertEqual(improvements, expected["best_improvement_count"])

        self.assertEqual(expected["required_flags"], ["poor_mixing"])
        # Raw ESS remains evidence; only the uncalibrated health threshold is removed.
        self.assertLess(expected["ess"], 400.0)
        self.assertLess(expected["count"], 50 * expected["tau_hat"])

    def test_insufficient_data_short_trace_math(self) -> None:
        fixture = self.fixtures["insufficient_data_short_trace"]
        trace = fixture["input"]["energy_trace"]
        expected = fixture["expected"]

        self.assertAlmostEqual(variance(trace), 2.0 / 3.0, places=12)
        self.assertEqual(best_improvement_count(trace), 2)
        self.assertEqual(expected["autocorrelation_status"], "insufficient_data")
        self.assertEqual(expected["ess_status"], "insufficient_data")

    def test_ess_tau_hat_identity_on_pinned_values(self) -> None:
        healthy = self.fixtures["healthy_multichain_energy_trace"]["expected"]
        ar1 = self.fixtures["autocorrelated_energy_trace_ar1"]["expected"]
        numeric_rhat = self.fixtures["chain_disagreement_numeric_rhat"]["expected"]

        self.assertAlmostEqual(healthy["ess"] * healthy["tau_hat"], 512.0, delta=1e-6)
        self.assertAlmostEqual(ar1["ess"] * ar1["tau_hat"], 256.0, delta=1e-6)
        self.assertAlmostEqual(numeric_rhat["ess"] * numeric_rhat["tau_hat"], 32.0, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
