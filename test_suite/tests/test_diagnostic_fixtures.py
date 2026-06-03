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


def hamming(left: dict[str, int], right: dict[str, int]) -> int:
    return sum(1 for variable in left if left[variable] != right[variable])


class DiagnosticFixtureMathTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = load_diagnostics()

    def test_mode_collapse_metrics_from_counts(self) -> None:
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
        self.assertEqual(counts[0] / total, expected["top1_mass"])
        self.assertEqual(sum(counts[:3]) / total, expected["top3_mass"])
        self.assertAlmostEqual(entropy, expected["entropy_nats"], places=12)
        self.assertAlmostEqual(
            mean_hamming, expected["mean_pairwise_hamming_distance"], places=12
        )
        self.assertAlmostEqual(
            mean_hamming / len(fixture["input"]["variables"]),
            expected["normalized_mean_pairwise_hamming_distance"],
            places=12,
        )
        self.assertCountEqual(expected["required_flags"], ["mode_collapse", "low_diversity"])

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
        self.assertCountEqual(
            expected["required_flags"], ["no_recent_improvement", "zero_energy_variance"]
        )

    def test_chain_disagreement_between_chain_variance(self) -> None:
        fixture = self.fixtures["chain_disagreement_zero_within_variance"]
        chains = fixture["input"]["chains"]
        expected = fixture["expected"]

        means = [sum(chain["energy_trace"]) / len(chain["energy_trace"]) for chain in chains]
        within = [variance(chain["energy_trace"]) for chain in chains]
        draws_per_chain = len(chains[0]["energy_trace"])
        grand_mean = sum(means) / len(means)
        between = draws_per_chain / (len(chains) - 1) * sum(
            (mean - grand_mean) ** 2 for mean in means
        )

        self.assertEqual(len(chains), expected["num_chains"])
        self.assertEqual(draws_per_chain, expected["draws_per_chain"])
        self.assertEqual(means, expected["chain_means"])
        self.assertEqual(within, expected["within_chain_variances"])
        self.assertEqual(between, expected["between_chain_variance"])
        self.assertEqual(expected["rhat_status"], "undefined_or_infinite_zero_within_variance")
        self.assertCountEqual(
            expected["required_flags"], ["chain_disagreement", "zero_within_chain_variance"]
        )


if __name__ == "__main__":
    unittest.main()
