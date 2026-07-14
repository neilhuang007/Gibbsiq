"""Metamorphic invariants and sensitivity checks for ``gibbsiq.diagnostics``.

Property checks across seeded random inputs, complementing the hand-picked
unit tests: order-blindness, location/scale invariance, multi-chain
disagreement detection.
"""

from __future__ import annotations

import math
import random
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
    diversity_section,
    energy_section,
    ess_mean,
    magnetization_trace,
    state_counts,
)


def ar1_trace(rng: random.Random, phi: float, num_draws: int, x0: float = 0.0) -> list[float]:
    """A single AR(1) trace: x_t = phi * x_{t-1} + N(0, 1), seeded by ``rng``."""
    value = x0
    trace = []
    for _ in range(num_draws):
        value = phi * value + rng.gauss(0.0, 1.0)
        trace.append(value)
    return trace


class SampleOrderPermutationTests(unittest.TestCase):
    def test_diversity_section_invariant_to_shuffling(self) -> None:
        variables = ["a", "b", "c"]
        rng = random.Random(101)
        samples = [{variable: rng.choice((1, -1)) for variable in variables} for _ in range(200)]

        original_section = diversity_section(state_counts(samples, variables), len(variables))

        shuffled = list(samples)
        random.Random(202).shuffle(shuffled)
        shuffled_section = diversity_section(state_counts(shuffled, variables), len(variables))

        self.assertEqual(original_section, shuffled_section)

    def test_autocorrelated_trace_shuffle_changes_tau(self) -> None:
        # phi=0.9 is strongly autocorrelated; an order-blind estimator built
        # only from marginal counts would report the same tau either way.
        trace = ar1_trace(random.Random(303), phi=0.9, num_draws=256)
        unshuffled = ess_mean([trace])

        shuffled_trace = list(trace)
        random.Random(404).shuffle(shuffled_trace)
        shuffled = ess_mean([shuffled_trace])

        self.assertEqual(unshuffled["ess_status"], "ok")
        self.assertEqual(shuffled["ess_status"], "ok")
        self.assertGreater(abs(unshuffled["tau_hat"] - shuffled["tau_hat"]), 1.0)


class LocationScaleInvarianceTests(unittest.TestCase):
    def _seeded_chains(self) -> list[list[float]]:
        rng = random.Random(505)
        return [[rng.gauss(0.0, 1.0) for _ in range(200)] for _ in range(4)]

    def test_energy_shift_preserves_autocorrelation_shifts_mean(self) -> None:
        chains = self._seeded_chains()
        shifted = [[value + 7.5 for value in chain] for chain in chains]

        base_energy = energy_section(chains)
        shifted_energy = energy_section(shifted)
        base_chains = chain_section(chains)
        shifted_chains = chain_section(shifted)

        self.assertAlmostEqual(base_energy["tau_hat"], shifted_energy["tau_hat"], places=9)
        self.assertAlmostEqual(base_energy["ess"], shifted_energy["ess"], places=9)
        self.assertAlmostEqual(base_chains["rhat"], shifted_chains["rhat"], places=9)
        self.assertAlmostEqual(shifted_energy["mean"], base_energy["mean"] + 7.5, places=9)

    def test_energy_scale_preserves_autocorrelation_scales_variance(self) -> None:
        chains = self._seeded_chains()
        scaled = [[value * 3.0 for value in chain] for chain in chains]

        base_energy = energy_section(chains)
        scaled_energy = energy_section(scaled)
        base_chains = chain_section(chains)
        scaled_chains = chain_section(scaled)

        self.assertAlmostEqual(base_energy["tau_hat"], scaled_energy["tau_hat"], places=9)
        self.assertAlmostEqual(base_energy["ess"], scaled_energy["ess"], places=9)
        self.assertAlmostEqual(base_chains["rhat"], scaled_chains["rhat"], places=9)
        self.assertAlmostEqual(scaled_energy["variance"], base_energy["variance"] * 9.0, places=9)


class ChainRelabelTests(unittest.TestCase):
    def test_reversed_chain_order_keeps_rhat_ess(self) -> None:
        rng = random.Random(606)
        chains = [[rng.gauss(0.0, 1.0) for _ in range(150)] for _ in range(4)]

        forward = chain_section(chains)
        backward = chain_section(list(reversed(chains)))

        self.assertEqual(forward["rhat"], backward["rhat"])
        self.assertEqual(forward["ess"], backward["ess"])


class GlobalSpinFlipTests(unittest.TestCase):
    def test_spin_flip_negates_magnetization(self) -> None:
        variables = ["a", "b", "c", "d"]
        rng = random.Random(707)
        chain = [{variable: rng.choice((1, -1)) for variable in variables} for _ in range(40)]
        flipped_chain = [{variable: -spin for variable, spin in sample.items()} for sample in chain]

        original_magnetization = magnetization_trace([chain], variables)[0]
        flipped_magnetization = magnetization_trace([flipped_chain], variables)[0]
        for original_value, flipped_value in zip(original_magnetization, flipped_magnetization):
            self.assertAlmostEqual(flipped_value, -original_value, places=12)

        original_section = diversity_section(state_counts(chain, variables), len(variables))
        flipped_section = diversity_section(state_counts(flipped_chain, variables), len(variables))
        self.assertEqual(original_section, flipped_section)


class VariableRelabelTests(unittest.TestCase):
    def test_renaming_variables_leaves_diversity_identical(self) -> None:
        rng = random.Random(808)
        original_variables = ["a", "b", "c"]
        relabel = {"a": "x", "b": "y", "c": "z"}
        renamed_variables = [relabel[variable] for variable in original_variables]

        samples = [{variable: rng.choice((1, -1)) for variable in original_variables} for _ in range(60)]
        renamed_samples = [
            {relabel[variable]: spin for variable, spin in sample.items()} for sample in samples
        ]

        original_section = diversity_section(
            state_counts(samples, original_variables), len(original_variables)
        )
        renamed_section = diversity_section(
            state_counts(renamed_samples, renamed_variables), len(renamed_variables)
        )
        self.assertEqual(original_section, renamed_section)

    def test_spin_chain_disagreement_tracks_variable_relabeling(self) -> None:
        variables = ["a", "b", "c", "d"]
        relabel = {"a": "w", "b": "x", "c": "y", "d": "z"}
        left = {"a": 1, "b": 1, "c": -1, "d": -1}
        right = {"a": 1, "b": -1, "c": 1, "d": -1}
        samples = [left] * 20 + [right] * 20
        renamed = [{relabel[variable]: spin for variable, spin in sample.items()} for sample in samples]

        original = compute_diagnostics(
            energy_chains=[[0.0] * 20, [0.0] * 20],
            samples=samples,
            variables=variables,
        )
        transformed = compute_diagnostics(
            energy_chains=[[0.0] * 20, [0.0] * 20],
            samples=renamed,
            variables=[relabel[variable] for variable in variables],
        )

        self.assertTrue(original["chains"]["spins"]["chain_disagreement"])
        self.assertTrue(transformed["chains"]["spins"]["chain_disagreement"])
        self.assertEqual(original["chains"]["spins"]["offending_variables"], ["b", "c"])
        self.assertEqual(transformed["chains"]["spins"]["offending_variables"], ["x", "y"])

    def test_spin_chain_disagreement_is_gauge_invariant(self) -> None:
        variables = ["a", "b", "c", "d"]
        left = {"a": 1, "b": 1, "c": -1, "d": -1}
        right = {"a": 1, "b": -1, "c": 1, "d": -1}
        samples = [left] * 20 + [right] * 20
        gauge = {"a": -1, "b": 1, "c": -1, "d": 1}
        gauged = [
            {variable: sample[variable] * gauge[variable] for variable in variables} for sample in samples
        ]

        original = compute_diagnostics(
            energy_chains=[[0.0] * 20, [0.0] * 20],
            samples=samples,
            variables=variables,
        )
        transformed = compute_diagnostics(
            energy_chains=[[0.0] * 20, [0.0] * 20],
            samples=gauged,
            variables=variables,
        )

        self.assertEqual(
            original["chains"]["spins"]["offending_variables"],
            transformed["chains"]["spins"]["offending_variables"],
        )
        self.assertEqual(
            original["chains"]["spins"]["offending_variable_count"],
            transformed["chains"]["spins"]["offending_variable_count"],
        )


class TrendingChainTests(unittest.TestCase):
    def test_trending_identical_chains_yield_large_rhat(self) -> None:
        trend = list(range(1, 41))
        section = chain_section([trend, list(trend)])
        self.assertGreater(section["rhat"], 1.5)


class CrossMetricBoundsTests(unittest.TestCase):
    def test_bounds_hold_across_several_seeded_random_inputs(self) -> None:
        variables = ["a", "b", "c", "d"]
        for seed in (11, 22, 33):
            rng = random.Random(seed)
            energy_chains = [[rng.gauss(0.0, 1.0) for _ in range(128)] for _ in range(3)]
            samples = [{variable: rng.choice((1, -1)) for variable in variables} for _ in range(100)]
            payload = compute_diagnostics(energy_chains=energy_chains, samples=samples, variables=variables)

            total_draws = sum(len(chain) for chain in energy_chains)
            ess = payload["energy"]["ess"]
            if ess is not None:
                self.assertLessEqual(ess, total_draws + 1e-6, msg=f"seed={seed}")

            diversity = payload["diversity"]
            if diversity["unique_states"] > 0:
                self.assertLessEqual(
                    diversity["entropy_nats"],
                    math.log(diversity["unique_states"]) + 1e-12,
                    msg=f"seed={seed}",
                )
            self.assertLessEqual(diversity["top1_mass"], diversity["top3_mass"] + 1e-12)
            self.assertLessEqual(diversity["top3_mass"], diversity["top10_mass"] + 1e-12)
            self.assertLessEqual(diversity["top10_mass"], 1.0 + 1e-12)
            normalized_hamming = diversity["normalized_mean_pairwise_hamming_distance"]
            if normalized_hamming is not None:
                self.assertGreaterEqual(normalized_hamming, 0.0)
                self.assertLessEqual(normalized_hamming, 1.0)

            for flag in payload["flags"]:
                self.assertIn(flag, diagnostics.FLAG_ORDER, msg=f"seed={seed}")


class DeterminismTests(unittest.TestCase):
    def test_same_input_produces_identical_payloads(self) -> None:
        variables = ["a", "b"]
        energy_rng = random.Random(909)
        energy_chains = [[energy_rng.gauss(0.0, 1.0) for _ in range(64)] for _ in range(2)]
        sample_rng = random.Random(910)
        samples = [{variable: sample_rng.choice((1, -1)) for variable in variables} for _ in range(50)]

        first = compute_diagnostics(energy_chains=energy_chains, samples=samples, variables=variables)
        second = compute_diagnostics(energy_chains=energy_chains, samples=samples, variables=variables)
        self.assertEqual(first, second)


class AnalyticAR1TauTests(unittest.TestCase):
    """Analytic integrated autocorrelation time for AR(1): tau = (1 + phi) / (1 - phi)."""

    # Seed 1234 was the first seed tried and lands every phi inside its
    # predeclared interval; do not widen the intervals to chase a new seed.
    SEED = 1234
    NUM_CHAINS = 4
    NUM_DRAWS = 5000

    def _tau_for_phi(self, phi: float) -> float:
        rng = random.Random(self.SEED)
        chains = [ar1_trace(rng, phi=phi, num_draws=self.NUM_DRAWS) for _ in range(self.NUM_CHAINS)]
        result = ess_mean(chains)
        self.assertEqual(result["autocorrelation_status"], "ok")
        return result["tau_hat"]

    def test_phi_zero_tau_near_one(self) -> None:
        tau = self._tau_for_phi(0.0)
        self.assertGreaterEqual(tau, 0.8)
        self.assertLessEqual(tau, 1.3)

    def test_phi_half_tau_near_three(self) -> None:
        tau = self._tau_for_phi(0.5)
        self.assertGreaterEqual(tau, 2.4)
        self.assertLessEqual(tau, 3.6)

    def test_phi_point_nine_tau_near_nineteen(self) -> None:
        tau = self._tau_for_phi(0.9)
        self.assertGreaterEqual(tau, 15.0)
        self.assertLessEqual(tau, 23.0)

    def test_phi_negative_half_tau_near_one_third(self) -> None:
        tau = self._tau_for_phi(-0.5)
        self.assertGreaterEqual(tau, 0.25)
        self.assertLessEqual(tau, 0.45)


class BehaviorTrioTests(unittest.TestCase):
    def test_healthy_chains_are_clean(self) -> None:
        rng = random.Random(1111)
        chains = [[rng.gauss(0.0, 1.0) for _ in range(500)] for _ in range(4)]
        section = chain_section(chains)
        self.assertLess(section["rhat"], 1.05)
        self.assertGreater(section["ess"], 1000.0)
        self.assertEqual(chain_flags(section), [])

    def test_two_region_chains_disagree_low_ess(self) -> None:
        section = self._two_region_section()
        self.assertGreater(section["rhat"], 2.0)
        self.assertIn("chain_disagreement", chain_flags(section))
        self.assertLess(section["ess"], 100.0)

    def test_stuck_chain_rhat_falls_between_regimes(self) -> None:
        rng = random.Random(3333)
        chains = [[rng.gauss(0.0, 1.0) for _ in range(500)] for _ in range(3)]
        chains.append([rng.gauss(0.0, 0.05) for _ in range(500)])
        section = chain_section(chains)
        self.assertTrue(math.isfinite(section["rhat"]))
        self.assertLess(section["rhat"], self._two_region_section()["rhat"])

    @staticmethod
    def _two_region_section() -> dict:
        rng = random.Random(2222)
        chains = [[rng.gauss(0.0, 1.0) for _ in range(500)] for _ in range(2)]
        chains += [[rng.gauss(10.0, 1.0) for _ in range(500)] for _ in range(2)]
        return chain_section(chains)


if __name__ == "__main__":
    unittest.main()
