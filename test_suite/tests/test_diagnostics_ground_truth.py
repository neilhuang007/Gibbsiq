"""Independent ground-truth tests for ``src/gibbsiq/diagnostics.py`` (Stage 3).

Unlike ``test_diagnostics_arviz_crosscheck.py``, this file avoids arviz and numpy
entirely: expectations come from closed-form statistical theory, hand-derived
arithmetic worked out in comments, or brute-force stdlib recomputation through a
structurally different code path. All random draws use a seeded ``random.Random``
for determinism. Stdlib only (``unittest``, ``random``, ``math``).

The rank-normalized + folded R-hat variant (EVAL-EQ-013) and the magnetization
chain-disagreement wiring (EVAL-EQ-007) both landed 2026-07-03; tests below that
exercise those paths are noted inline. The plain `rhat` key retains its original,
deliberately mean-only semantics.
"""

from __future__ import annotations

import math
import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.diagnostics import (  # noqa: E402
    chain_flags,
    chain_section,
    compute_diagnostics,
    distance_to_best_trace,
    diversity_flags,
    diversity_observations,
    diversity_section,
    energy_flags,
    energy_observations,
    energy_section,
    ess_mean,
    magnetization_trace,
    rank_normalized_split_rhat,
    split_rhat,
    state_counts,
)


def generate_ar1_chains(seed: int, phi: float, num_chains: int, num_draws: int) -> list[list[float]]:
    """AR(1): x_t = phi * x_{t-1} + eps_t, eps ~ N(0, 1), initialized at the
    stationary marginal variance 1 / (1 - phi**2) so the chain starts "warm"
    and every draw targets the same fixed distribution.
    """
    rng = random.Random(seed)
    stationary_sd = 1.0 / math.sqrt(1.0 - phi**2)
    chains = []
    for _ in range(num_chains):
        chain = [rng.gauss(0.0, stationary_sd)]
        for _ in range(num_draws - 1):
            chain.append(phi * chain[-1] + rng.gauss(0.0, 1.0))
        chains.append(chain)
    return chains


class Ar1AutocorrelationTimeTheoryTests(unittest.TestCase):
    """Pins Geyer tau_hat against the closed-form AR(1) autocorrelation time."""

    # EVAL-EQ-008: tau = 1 + 2*sum_k rho_k. For AR(1) with rho_k = phi**k this
    # geometric series collapses to tau_theory = (1 + phi) / (1 - phi).
    def _mean_tau_hat(self, phi: float, num_chains: int, num_draws: int, seeds: range) -> float:
        # A single realization's tau_hat is noisy (near phi=0.9, an 8-seed
        # sweep ranged 17.8-23.7 around the true 19.0), so average several
        # seeded replicates rather than tolerate one lucky/unlucky draw.
        tau_hats = []
        for seed in seeds:
            chains = generate_ar1_chains(seed=seed, phi=phi, num_chains=num_chains, num_draws=num_draws)
            result = ess_mean(chains)
            self.assertEqual(result["autocorrelation_status"], "ok")
            # split doubles the chain count and halves the per-chain draw
            # count: size = (2*num_chains) * (num_draws//2). Algebraic
            # identity of the estimator, holds per-replicate exactly.
            expected_ess = (2 * num_chains) * (num_draws // 2) / result["tau_hat"]
            self.assertAlmostEqual(result["ess"], expected_ess, places=9)
            tau_hats.append(result["tau_hat"])
        return sum(tau_hats) / len(tau_hats)

    def test_tau_hat_matches_ar1_theory_phi_09(self) -> None:
        phi = 0.9
        tau_theory = (1.0 + phi) / (1.0 - phi)  # = 19.0
        seeds = range(20260703_01, 20260703_01 + 7)
        mean_tau_hat = self._mean_tau_hat(phi, num_chains=4, num_draws=20000, seeds=seeds)
        relative_error = abs(mean_tau_hat - tau_theory) / tau_theory
        self.assertLess(relative_error, 0.15, msg=f"mean_tau_hat={mean_tau_hat} tau_theory={tau_theory}")

    def test_tau_hat_matches_ar1_theory_phi_05(self) -> None:
        phi = 0.5
        tau_theory = (1.0 + phi) / (1.0 - phi)  # = 3.0
        seeds = range(20260703_01, 20260703_01 + 7)
        mean_tau_hat = self._mean_tau_hat(phi, num_chains=4, num_draws=5000, seeds=seeds)
        relative_error = abs(mean_tau_hat - tau_theory) / tau_theory
        self.assertLess(relative_error, 0.15, msg=f"mean_tau_hat={mean_tau_hat} tau_theory={tau_theory}")


class IidSampleSizeRecoveryTests(unittest.TestCase):
    """For genuinely iid draws (tau_theory = 1), ESS should recover close to
    the raw sample size and split R-hat should show no chain disagreement.
    """

    def test_ess_close_to_sample_size_for_iid_gaussian(self) -> None:
        rng = random.Random(20260703_03)
        num_chains, num_draws = 4, 2000
        chains = [[rng.gauss(0.0, 1.0) for _ in range(num_draws)] for _ in range(num_chains)]

        result = ess_mean(chains)
        self.assertEqual(result["ess_status"], "ok")
        ratio = result["ess"] / (num_chains * num_draws)
        self.assertGreaterEqual(ratio, 0.8)
        self.assertLessEqual(ratio, 1.25)

        rhat_result = split_rhat(chains)
        self.assertEqual(rhat_result["rhat_status"], "ok")
        self.assertLess(rhat_result["rhat"], 1.01)
        self.assertEqual(chain_flags(chain_section(chains)), [])

    def test_ess_close_to_sample_size_for_iid_binary_spins(self) -> None:
        # Discrete +-1 traces (heavy ties) stand in for a real spin/energy
        # trace, far from the continuous-Gaussian case Geyer is usually run on.
        rng = random.Random(20260703_04)
        num_chains, num_draws = 4, 2000
        chains = [[rng.choice([-1.0, 1.0]) for _ in range(num_draws)] for _ in range(num_chains)]

        result = ess_mean(chains)
        self.assertEqual(result["ess_status"], "ok")
        ratio = result["ess"] / (num_chains * num_draws)
        self.assertGreaterEqual(ratio, 0.8)
        self.assertLessEqual(ratio, 1.25)


class SplitRhatHandComputedValueTests(unittest.TestCase):
    def test_split_rhat_exact_hand_computed_value(self) -> None:
        # chains = [[1,2,3,4],[3,4,5,6]], N_raw=4 per chain -> half=2.
        # split_chains yields [first halves] + [last halves]:
        #   [1,2], [3,4]   (first halves of chain0, chain1)
        #   [3,4], [5,6]   (last halves of chain0, chain1)
        # so the 4 split-chains are [1,2], [3,4], [3,4], [5,6].
        # split-chain means: 1.5, 3.5, 3.5, 5.5.
        # W (EVAL-EQ-007 "s_m^2", ddof=1 per split-chain, then averaged):
        #   each pair {a, a+1} has ddof=1 variance 0.5 -> W = 0.5.
        # B = N/(M-1) * sum_m (mean_m - grand_mean)^2, N=2, M=4:
        #   grand_mean = 3.5; deviations -2, 0, 0, 2 -> sum of squares = 8
        #   B = 2/3 * 8 = 16/3.
        # var_hat_plus = (N-1)/N * W + (1/N) * B
        #              = (1/2)*0.5 + (1/2)*(16/3) = 1/4 + 8/3 = 35/12
        # rhat = sqrt(var_hat_plus / W) = sqrt((35/12) / (1/2)) = sqrt(35/6)
        chains = [[1, 2, 3, 4], [3, 4, 5, 6]]
        result = split_rhat(chains)
        self.assertEqual(result["rhat_status"], "ok")
        self.assertAlmostEqual(result["rhat"], math.sqrt(35.0 / 6.0), places=12)


class EssTauFloorExactTests(unittest.TestCase):
    def test_ess_tau_floor_exact_for_eight_draw_single_chain(self) -> None:
        # Single chain of 8 raw draws splits into 2 chains x 4 draws each
        # (post-split N=4). The Geyer positive-sequence loop guard is
        # `t < N - 3` = `1 < 1`, which is false already at t=1, so the loop
        # body never executes and tau_hat collapses to the documented floor
        # 1/log10(size) with size = num_split_chains * N = 2 * 4 = 8.
        # Hence ess = size / tau_hat = 8 * log10(8) exactly.
        chains = [[1, 2, 3, 4, 5, 6, 7, 8]]
        result = ess_mean(chains)
        self.assertEqual(result["ess_status"], "ok")
        expected_tau = 1.0 / math.log10(8.0)
        self.assertAlmostEqual(result["tau_hat"], expected_tau, places=12)
        self.assertAlmostEqual(result["ess"], 8.0 * math.log10(8.0), places=12)


class AntitheticSuperefficientEssTests(unittest.TestCase):
    def test_antithetic_chain_reports_superefficient_ess(self) -> None:
        # Deterministic alternation gives strong NEGATIVE lag-1
        # autocorrelation, which pulls tau_hat below 1 and ESS above the raw
        # sample size. This documents that ESS is not clamped to the sample
        # count -- "superefficient" traces are a real, intended output, not
        # a bug to be capped away.
        chain = [1.0 if index % 2 == 0 else -1.0 for index in range(100)]
        result = ess_mean([chain])
        self.assertEqual(result["ess_status"], "ok")
        self.assertGreater(result["ess"], 100.0)


class SplitRhatWithinChainTrendTests(unittest.TestCase):
    def test_split_rhat_detects_within_chain_trend(self) -> None:
        # Two IDENTICAL deterministic ramp chains. Splitting each in half
        # turns a single nonstationary trend into two disagreeing halves:
        # first-half mean ~ average of 0.00..0.49 = 0.245, second-half mean
        # ~ average of 0.50..0.99 = 0.745. Because both raw chains are
        # identical, the 4 split-chains collapse into two mean clusters
        # (0.245, 0.245, 0.745, 0.745), which the within-chain ramp variance
        # cannot explain away. This is precisely why R-hat is computed on
        # SPLIT chains: it turns within-chain nonstationarity into a
        # detectable between-chain disagreement.
        ramp = [index / 100.0 for index in range(100)]
        chains = [list(ramp), list(ramp)]

        result = split_rhat(chains)
        self.assertEqual(result["rhat_status"], "ok")
        self.assertGreater(result["rhat"], 1.5)
        self.assertIn("chain_disagreement", chain_flags(chain_section(chains)))


class SplitRhatMeanShiftedChainsTests(unittest.TestCase):
    def test_split_rhat_detects_mean_shifted_chains(self) -> None:
        rng = random.Random(20260703_08)
        chains = [
            [rng.gauss(0.0, 1.0) for _ in range(200)],
            [rng.gauss(0.0, 1.0) for _ in range(200)],
            [rng.gauss(3.0, 1.0) for _ in range(200)],
            [rng.gauss(3.0, 1.0) for _ in range(200)],
        ]
        result = split_rhat(chains)
        self.assertEqual(result["rhat_status"], "ok")
        self.assertGreater(result["rhat"], 1.2)
        self.assertIn("chain_disagreement", chain_flags(chain_section(chains)))


class VarianceOnlyDisagreementTests(unittest.TestCase):
    def test_rank_rhat_catches_variance_only_disagreement(self) -> None:
        # All four chains share mean 0.0, differing only in scale (sd 0.1 vs
        # 10.0). Plain split R-hat (EVAL-EQ-007) compares mean disagreement
        # (B) against within-chain variance (W), so it stays blind to this by
        # design — pinned below since the plain `rhat` key must never change
        # meaning. The rank-normalized variant's folded component converts
        # the scale difference into a location difference, so
        # `rank_normalized_rhat` exceeds threshold and chain_disagreement
        # fires through the rank path instead.
        rng = random.Random(20260703_09)
        chains = [
            [rng.gauss(0.0, 0.1) for _ in range(500)],
            [rng.gauss(0.0, 0.1) for _ in range(500)],
            [rng.gauss(0.0, 10.0) for _ in range(500)],
            [rng.gauss(0.0, 10.0) for _ in range(500)],
        ]
        result = split_rhat(chains)
        self.assertEqual(result["rhat_status"], "ok")
        self.assertLess(result["rhat"], 1.01)

        section = chain_section(chains)
        self.assertEqual(section["rank_normalized_rhat_status"], "ok")
        self.assertGreater(section["rank_normalized_rhat"], 1.01)
        # The signal comes from the FOLDED component; the bulk (mean-level)
        # component agrees with the plain variant that means coincide.
        self.assertGreater(section["rank_normalized_rhat_folded"], 1.01)
        self.assertLess(section["rank_normalized_rhat_bulk"], 1.01)
        self.assertIn("chain_disagreement", chain_flags(section))


class MultimodalFreezeBlindSpotTests(unittest.TestCase):
    ENERGY_CHAINS = [[-1.0] * 50, [-1.0] * 50]
    SAMPLES = [{"a": 1, "b": 1}] * 50 + [{"a": -1, "b": -1}] * 50
    VARIABLES = ["a", "b"]

    def test_frozen_state_screen_closes_energy_only_blind_spot(self) -> None:
        # Double-well setup: two chains are each frozen in a DIFFERENT
        # degenerate ground state that happens to carry the SAME energy.
        # Energy-only R-hat cannot see this, but aligned raw samples now supply
        # a whole-state cross-chain screen without requiring a caller to
        # precompute a magnetization trace.
        payload = compute_diagnostics(
            energy_chains=self.ENERGY_CHAINS, samples=self.SAMPLES, variables=self.VARIABLES
        )

        self.assertIn("chain_disagreement", payload["flags"])
        self.assertNotIn("zero_energy_variance", payload["flags"])
        self.assertNotIn("zero_within_chain_variance", payload["flags"])
        self.assertNotIn("low_diversity", payload["flags"])
        self.assertCountEqual(
            payload["observations"],
            ["no_recent_improvement", "zero_energy_variance", "zero_within_chain_variance"],
        )
        self.assertNotIn("mode_collapse", payload["flags"])
        self.assertEqual(payload["diversity"]["unique_states"], 2)
        self.assertEqual(payload["chains"]["rhat_status"], "undefined_constant_trace")
        self.assertEqual(payload["chains"]["rank_normalized_rhat_status"], "undefined_constant_trace")
        self.assertNotIn("magnetization", payload["chains"])
        spins = payload["chains"]["spins"]
        self.assertTrue(spins["chain_disagreement"])
        self.assertEqual(spins["offending_variables"], ["a", "b"])
        self.assertEqual(spins["offending_variable_count"], 2)
        self.assertIn("not a convergence proof", spins["interpretation_note"])

    def test_equal_energy_equal_magnetization_frozen_modes_are_detected(self) -> None:
        left_mode = {"a": 1, "b": 1, "c": -1, "d": -1}
        right_mode = {"a": 1, "b": -1, "c": 1, "d": -1}
        samples = [left_mode] * 16 + [right_mode] * 16
        payload = compute_diagnostics(
            energy_chains=[[0.0] * 16, [0.0] * 16],
            samples=samples,
            variables=["a", "b", "c", "d"],
            magnetization_chains=[[0.0] * 16, [0.0] * 16],
        )

        self.assertEqual(payload["chains"]["rhat_status"], "undefined_constant_trace")
        self.assertEqual(
            payload["chains"]["magnetization"]["rhat_status"],
            "undefined_constant_trace",
        )
        self.assertIn("chain_disagreement", payload["flags"])
        self.assertEqual(payload["chains"]["spins"]["offending_variables"], ["b", "c"])

    def test_seeded_iid_spins_do_not_trigger_variable_screen(self) -> None:
        variables = [f"v{index}" for index in range(64)]
        rng = random.Random(20260714)
        sample_chains = [
            [{variable: rng.choice((-1, 1)) for variable in variables} for _ in range(256)] for _ in range(4)
        ]
        payload = compute_diagnostics(
            energy_chains=[[0.0] * 256 for _ in range(4)],
            samples=[sample for chain in sample_chains for sample in chain],
            variables=variables,
        )

        self.assertNotIn("chain_disagreement", payload["flags"])
        self.assertFalse(payload["chains"]["spins"]["chain_disagreement"])
        self.assertEqual(payload["chains"]["spins"]["offending_variables"], [])
        self.assertEqual(payload["chains"]["spins"]["variables_checked"], 64)

    def test_one_draw_per_chain_is_insufficient_frozen_mode_evidence(self) -> None:
        payload = compute_diagnostics(
            energy_chains=[[0.0], [0.0]],
            samples=[{"a": 1, "b": -1}, {"a": -1, "b": 1}],
            variables=["a", "b"],
        )

        self.assertNotIn("chain_disagreement", payload["flags"])
        spins = payload["chains"]["spins"]
        self.assertEqual(spins["status"], "ok")
        self.assertEqual(spins["evidence_status"], "insufficient_data")
        self.assertFalse(spins["frozen_mode_disagreement"])
        self.assertEqual(spins["offending_variables"], [])

    def test_frozen_mode_evidence_caps_explanatory_variable_list(self) -> None:
        variables = [f"v{index}" for index in range(105)]
        left = {variable: 1 for variable in variables}
        right = {variable: -1 for variable in variables}
        payload = compute_diagnostics(
            energy_chains=[[0.0] * 4, [0.0] * 4],
            samples=[left] * 4 + [right] * 4,
            variables=variables,
        )

        spins = payload["chains"]["spins"]
        self.assertTrue(spins["frozen_mode_disagreement"])
        self.assertEqual(spins["offending_variable_count"], 105)
        self.assertEqual(len(spins["offending_variables"]), 100)
        self.assertTrue(spins["offending_variables_truncated"])

    def test_magnetization_wiring_fires_chain_disagreement(self) -> None:
        # Same payload as above but with the per-chain magnetization trace
        # supplied (EVAL-EQ-007 wiring, landed 2026-07-03): chain 0 sits at
        # constant magnetization +1 and chain 1 at -1, the zero-within-variance
        # (infinite R-hat) path, so chain_disagreement now fires through
        # chains.magnetization. Energy-family constant-trace flags are
        # unchanged -- magnetization contributes only chain_disagreement.
        magnetization_chains = [[1.0] * 50, [-1.0] * 50]
        payload = compute_diagnostics(
            energy_chains=self.ENERGY_CHAINS,
            samples=self.SAMPLES,
            variables=self.VARIABLES,
            magnetization_chains=magnetization_chains,
        )

        self.assertIn("chain_disagreement", payload["flags"])
        magnetization = payload["chains"]["magnetization"]
        self.assertEqual(magnetization["rhat_status"], "undefined_or_infinite_zero_within_variance")
        self.assertEqual(
            magnetization["rank_normalized_rhat_status"],
            "undefined_or_infinite_zero_within_variance",
        )
        # Energy-family observations are untouched by the magnetization subsection.
        self.assertNotIn("zero_energy_variance", payload["flags"])
        self.assertNotIn("zero_within_chain_variance", payload["flags"])
        self.assertCountEqual(
            payload["observations"],
            ["no_recent_improvement", "zero_energy_variance", "zero_within_chain_variance"],
        )
        self.assertNotIn("mode_collapse", payload["flags"])
        self.assertEqual(payload["chains"]["rhat_status"], "undefined_constant_trace")

    def test_frozen_same_well_no_disagreement(self) -> None:
        # Control for the wiring above: a sampler frozen in ONE state produces
        # identical constant magnetization chains, which must map to the
        # constant-trace status, never to chain_disagreement. A sampler stuck
        # in a single well this way stays invisible to any within-sample
        # diagnostic -- there is no cross-chain signal to detect it.
        payload = compute_diagnostics(
            energy_chains=self.ENERGY_CHAINS,
            samples=[{"a": 1, "b": 1}] * 100,
            variables=self.VARIABLES,
            magnetization_chains=[[1.0] * 50, [1.0] * 50],
        )
        self.assertNotIn("chain_disagreement", payload["flags"])
        self.assertEqual(payload["chains"]["magnetization"]["rhat_status"], "undefined_constant_trace")


class RankNormalizedRhatHandComputedTests(unittest.TestCase):
    def test_tied_alternating_chains_folded_collapse(self) -> None:
        # Fully hand-derivable EVAL-EQ-013 case exercising ties, the Blom
        # backtransform symmetry, and the folded-collapse rule at once.
        # chains = [[1,2,1,2],[1,2,1,2]] -> split: four chains, each [1,2].
        # Pooled split draws: four 1s and four 2s (S=8). Average-tie ranks:
        #   1s -> (1+2+3+4)/4 = 2.5;  2s -> (5+6+7+8)/4 = 6.5.
        # Blom probabilities p = (r - 3/8) / (S + 1/4):
        #   p_low = 2.125/8.25, p_high = 6.125/8.25, and p_low + p_high = 1,
        # so z_high = -z_low = z0 > 0 by normal-quantile symmetry (no quantile
        # value is ever needed -- it cancels).
        # Every split chain is [-z0, +z0]: all chain means are 0 -> B = 0;
        # ddof=1 variance per chain = 2*z0^2 -> W = 2*z0^2 > 0.
        # bulk = sqrt((B/W + N - 1)/N), N = 2 -> sqrt(1/2).
        # Fold: pooled median of {1 x4, 2 x4} = 1.5 -> |x - 1.5| = 0.5 for
        # every draw -> constant folded trace -> folded collapses to None and
        # the combined value is the bulk alone (matching arviz max-with-NaN).
        result = rank_normalized_split_rhat([[1.0, 2.0, 1.0, 2.0], [1.0, 2.0, 1.0, 2.0]])
        self.assertEqual(result["rank_normalized_rhat_status"], "ok")
        self.assertAlmostEqual(result["rank_normalized_rhat"], math.sqrt(0.5), places=12)
        self.assertAlmostEqual(result["rank_normalized_rhat_bulk"], math.sqrt(0.5), places=12)
        self.assertIsNone(result["rank_normalized_rhat_folded"])

    def test_shifted_tied_chains_match_rank_arithmetic(self) -> None:
        # chains = [[1,2,1,2],[3,4,3,4]] -> split chains [1,2],[3,4],[1,2],[3,4].
        # Pooled: two of each value 1,2,3,4 (S=8); average-tie ranks
        #   1 -> 1.5, 2 -> 3.5, 3 -> 5.5, 4 -> 7.5.
        # The expectation below recomputes bulk/folded from these hand-listed
        # ranks through the audited EVAL-EQ-007 core -- a code path that
        # never touches the ranking/median machinery under test.
        from statistics import NormalDist

        inv_cdf = NormalDist().inv_cdf
        z = {
            value: inv_cdf((rank - 0.375) / 8.25)
            for value, rank in ((1.0, 1.5), (2.0, 3.5), (3.0, 5.5), (4.0, 7.5))
        }
        bulk_expected = split_rhat([[z[1.0], z[2.0], z[1.0], z[2.0]], [z[3.0], z[4.0], z[3.0], z[4.0]]])[
            "rhat"
        ]
        # Fold around the pooled median 2.5: |x-2.5| gives 1.5 for values
        # {1,4} and 0.5 for values {2,3} -> folded ranks: 0.5s -> 2.5,
        # 1.5s -> 6.5 (four-way ties each).
        z_folded = {0.5: inv_cdf((2.5 - 0.375) / 8.25), 1.5: inv_cdf((6.5 - 0.375) / 8.25)}
        folded_expected = split_rhat(
            [
                [z_folded[1.5], z_folded[0.5], z_folded[1.5], z_folded[0.5]],
                [z_folded[0.5], z_folded[1.5], z_folded[0.5], z_folded[1.5]],
            ]
        )["rhat"]

        result = rank_normalized_split_rhat([[1.0, 2.0, 1.0, 2.0], [3.0, 4.0, 3.0, 4.0]])
        self.assertEqual(result["rank_normalized_rhat_status"], "ok")
        self.assertAlmostEqual(result["rank_normalized_rhat_bulk"], bulk_expected, places=12)
        self.assertAlmostEqual(result["rank_normalized_rhat_folded"], folded_expected, places=12)
        self.assertAlmostEqual(result["rank_normalized_rhat"], max(bulk_expected, folded_expected), places=12)


class RankNormalizedRhatInvarianceTests(unittest.TestCase):
    def test_bulk_invariant_under_strictly_monotone_transform(self) -> None:
        # Defining property of rank normalization (Vehtari et al. 2021): any
        # strictly increasing transform preserves the pooled ranks, hence the
        # z-scores, hence the bulk component bit-for-bit. Folded is exempt:
        # it takes |x - median(x)| on the raw scale before re-ranking, and a
        # nonlinear transform like exp() moves points asymmetrically around
        # the median, so folded values re-rank differently -- true of arviz
        # and the paper by construction. Plain split R-hat has no invariance
        # at all, which is why the variants live under separate keys.
        rng = random.Random(20260703_13)
        chains = [[rng.gauss(0.0, 1.0) for _ in range(200)] for _ in range(4)]
        transformed = [[math.exp(value) for value in chain] for chain in chains]

        original = rank_normalized_split_rhat(chains)
        after = rank_normalized_split_rhat(transformed)
        self.assertEqual(original["rank_normalized_rhat_bulk"], after["rank_normalized_rhat_bulk"])
        self.assertNotEqual(original["rank_normalized_rhat_folded"], after["rank_normalized_rhat_folded"])

        plain_original = split_rhat(chains)["rhat"]
        plain_after = split_rhat(transformed)["rhat"]
        self.assertGreater(abs(plain_original - plain_after), 1e-12)

    def test_all_components_invariant_under_affine_transform(self) -> None:
        # Affine maps commute with the median and scale |x - median|
        # uniformly, so ranks of both raw and folded draws are preserved and
        # every key must match. Small integer data/coefficients keep every
        # operation exact in floating point: with continuous data the
        # invariance holds only up to a knife-edge in the published algorithm
        # (arviz included) -- the pooled split count is always even, the
        # median averages the two middle order statistics, and those two
        # draws fold to exactly equidistant values whose bit-exact tie is
        # rounding-luck. Verified empirically: a gaussian seed under
        # x -> 3.5x - 11 flips exactly that one tie and shifts folded by 4e-6.
        rng = random.Random(20260703_15)
        chains = [[float(rng.choice((0, 1, 2, 3, 5))) for _ in range(200)] for _ in range(4)]
        transformed = [[2.0 * value + 7.0 for value in chain] for chain in chains]
        self.assertEqual(rank_normalized_split_rhat(chains), rank_normalized_split_rhat(transformed))


class RankNormalizedRhatDegenerateStatusTests(unittest.TestCase):
    def test_insufficient_data_gate_matches_plain_variant(self) -> None:
        for chains in ([[1.0, 2.0, 3.0, 4.0]], [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]):
            result = rank_normalized_split_rhat(chains)
            self.assertEqual(result["rank_normalized_rhat_status"], "insufficient_data")
            self.assertIsNone(result["rank_normalized_rhat"])

    def test_identical_constant_chains_report_constant_trace(self) -> None:
        result = rank_normalized_split_rhat([[2.0] * 10, [2.0] * 10])
        self.assertEqual(result["rank_normalized_rhat_status"], "undefined_constant_trace")
        self.assertIsNone(result["rank_normalized_rhat"])

    def test_distinct_constant_values_zero_within_variance(self) -> None:
        result = rank_normalized_split_rhat([[1.0] * 10, [2.0] * 10])
        self.assertEqual(result["rank_normalized_rhat_status"], "undefined_or_infinite_zero_within_variance")
        self.assertIsNone(result["rank_normalized_rhat"])

    def test_folded_scale_disagreement_zero_within_variance(self) -> None:
        # Both chains alternate symmetrically around the pooled median 0 with
        # different amplitudes, so the folded trace is constant WITHIN each
        # chain (1 vs 3) while differing BETWEEN chains -> folded W = 0 with
        # B > 0, the infinite folded R-hat. Bulk stays numeric (all chain
        # means sit at rank center) per EVAL-EQ-013, so the combined value is
        # None under the zero-within-variance status, and chain_disagreement
        # fires.
        chains = [[-1.0, 1.0] * 10, [-3.0, 3.0] * 10]
        result = rank_normalized_split_rhat(chains)
        self.assertEqual(result["rank_normalized_rhat_status"], "undefined_or_infinite_zero_within_variance")
        self.assertIsNone(result["rank_normalized_rhat"])
        self.assertIsNotNone(result["rank_normalized_rhat_bulk"])
        self.assertIsNone(result["rank_normalized_rhat_folded"])
        self.assertIn("chain_disagreement", chain_flags(chain_section(chains)))
        # The plain variant is blind to this run (means agree; W is finite).
        self.assertEqual(split_rhat(chains)["rhat_status"], "ok")
        self.assertLess(split_rhat(chains)["rhat"], 1.01)


class RankNormalizedRhatRecoveryTests(unittest.TestCase):
    def test_gaussian_binary_chains_report_healthy_rhat(self) -> None:
        # Healthy-run control including the discrete regime this project
        # actually lives in: a two-valued (+-1) iid trace is MAXIMALLY tied,
        # and average-tie ranking must still deliver a near-1 value rather
        # than degenerating (EVAL-EQ-013 ties rule).
        rng = random.Random(20260703_14)
        gaussian = [[rng.gauss(0.0, 1.0) for _ in range(2000)] for _ in range(4)]
        binary = [[float(rng.choice((-1, 1))) for _ in range(2000)] for _ in range(4)]
        for chains in (gaussian, binary):
            result = rank_normalized_split_rhat(chains)
            self.assertEqual(result["rank_normalized_rhat_status"], "ok")
            self.assertLess(result["rank_normalized_rhat"], 1.01)
        self.assertNotIn("chain_disagreement", chain_flags(chain_section(binary)))

    def test_mean_shifted_chains_fire_via_rank_path(self) -> None:
        rng = random.Random(20260703_08)
        chains = [
            [rng.gauss(0.0, 1.0) for _ in range(200)],
            [rng.gauss(0.0, 1.0) for _ in range(200)],
            [rng.gauss(3.0, 1.0) for _ in range(200)],
            [rng.gauss(3.0, 1.0) for _ in range(200)],
        ]
        result = rank_normalized_split_rhat(chains)
        self.assertEqual(result["rank_normalized_rhat_status"], "ok")
        self.assertGreater(result["rank_normalized_rhat"], 1.01)


class DiversityBruteForcePairEnumerationTests(unittest.TestCase):
    def test_diversity_metrics_match_brute_force_pair_enumeration(self) -> None:
        variables = ["v0", "v1", "v2", "v3", "v4"]
        state_a = (1, 1, 1, 1, 1)
        state_b = (1, 1, 1, -1, -1)
        state_c = (-1, -1, 1, 1, 1)
        state_d = (-1, -1, -1, -1, -1)
        reads = (
            [dict(zip(variables, state_a))] * 60
            + [dict(zip(variables, state_b))] * 40
            + [dict(zip(variables, state_c))] * 20
            + [dict(zip(variables, state_d))] * 8
        )
        self.assertEqual(len(reads), 128)

        flat_states = [tuple(read[variable] for variable in variables) for read in reads]

        # Independent count/fraction pass (does not reuse state_counts).
        counts: dict[tuple[int, ...], int] = {}
        for state in flat_states:
            counts[state] = counts.get(state, 0) + 1
        total = len(flat_states)
        fractions = {state: count / total for state, count in counts.items()}
        expected_entropy = -math.fsum(fraction * math.log(fraction) for fraction in fractions.values())
        sorted_fractions = sorted(fractions.values(), reverse=True)
        expected_top1_mass = sorted_fractions[0]
        expected_top3_mass = math.fsum(sorted_fractions[:3])
        expected_unique_fraction = len(counts) / total
        expected_occupancy_efficiency = len(counts) / min(total, 2 ** len(variables))

        # LITERAL O(R^2) double loop over the flat 128-read list, independent
        # of the count-weighted state-pair formula under test.
        pair_count = 0
        distance_sum = 0
        for first in range(len(flat_states)):
            for second in range(first + 1, len(flat_states)):
                differing = sum(1 for a, b in zip(flat_states[first], flat_states[second]) if a != b)
                distance_sum += differing
                pair_count += 1
        expected_pair_count = total * (total - 1) // 2
        self.assertEqual(pair_count, expected_pair_count)
        expected_mean_hamming = distance_sum / pair_count

        section = diversity_section(state_counts(reads, variables), len(variables))
        self.assertAlmostEqual(section["entropy_nats"], expected_entropy, places=12)
        self.assertAlmostEqual(section["top1_mass"], expected_top1_mass, places=12)
        self.assertAlmostEqual(section["top3_mass"], expected_top3_mass, places=12)
        self.assertAlmostEqual(section["unique_fraction"], expected_unique_fraction, places=12)
        self.assertAlmostEqual(section["occupancy_efficiency"], expected_occupancy_efficiency, places=12)
        self.assertAlmostEqual(section["mean_pairwise_hamming_distance"], expected_mean_hamming, places=12)


class TraceBruteForceCrossCheckTests(unittest.TestCase):
    def test_magnetization_distance_match_brute_force(self) -> None:
        variables = ["x", "y", "z"]
        chains = [
            [
                {"x": 1, "y": 1, "z": -1},
                {"x": 1, "y": -1, "z": -1},
                {"x": -1, "y": -1, "z": -1},
            ],
            [
                {"x": 1, "y": 1, "z": 1},
                {"x": -1, "y": 1, "z": -1},
                {"x": 1, "y": -1, "z": 1},
            ],
        ]
        best_sample = {"x": 1, "y": 1, "z": -1}

        # Hand-computed magnetization (mean spin per read):
        #   chain0: (1+1-1)/3=1/3, (1-1-1)/3=-1/3, (-1-1-1)/3=-1
        #   chain1: (1+1+1)/3=1,   (-1+1-1)/3=-1/3, (1-1+1)/3=1/3
        expected_magnetization = [
            [1.0 / 3.0, -1.0 / 3.0, -1.0],
            [1.0, -1.0 / 3.0, 1.0 / 3.0],
        ]
        # Hand-computed Hamming distance to best_sample=(x=1,y=1,z=-1):
        #   chain0: (1,1,-1)->0, (1,-1,-1)->1 (y differs), (-1,-1,-1)->2 (x,y)
        #   chain1: (1,1,1)->1 (z), (-1,1,-1)->1 (x), (1,-1,1)->2 (y,z)
        expected_distance = [
            [0, 1, 2],
            [1, 1, 2],
        ]

        actual_magnetization = magnetization_trace(chains, variables)
        for chain_index, chain in enumerate(actual_magnetization):
            for read_index, value in enumerate(chain):
                self.assertAlmostEqual(value, expected_magnetization[chain_index][read_index], places=12)
        self.assertEqual(distance_to_best_trace(chains, best_sample, variables), expected_distance)

        # Independent inline brute-force recomputation, structurally
        # different from magnetization_trace/distance_to_best_trace.
        brute_force_magnetization = [
            [sum(read[variable] for variable in variables) / len(variables) for read in chain]
            for chain in chains
        ]
        brute_force_distance = [
            [sum(1 for variable in variables if read[variable] != best_sample[variable]) for read in chain]
            for chain in chains
        ]
        self.assertEqual(magnetization_trace(chains, variables), brute_force_magnetization)
        self.assertEqual(distance_to_best_trace(chains, best_sample, variables), brute_force_distance)


class FlagThresholdBoundaryTests(unittest.TestCase):
    """Pins exact inclusive/exclusive flag boundaries via direct calls to the flag functions."""

    def test_raw_energy_ess_has_no_health_threshold(self) -> None:
        section = {
            "ess_status": "ok",
            "ess": 399.999999999,
            "autocorrelation_status": "ok",
            "tau_hat": 1.0,
            "draws_per_chain": 1000,
            "recent_improvement": True,
            "variance": 1.0,
            "count": 10,
        }
        self.assertEqual(section["ess"], 399.999999999)
        self.assertNotIn("low_ess", energy_flags(section))

    def test_high_sample_concentration_boundary_is_inclusive(self) -> None:
        self.assertIn(
            "high_sample_concentration",
            diversity_observations({"top1_mass": 0.9, "unique_fraction": 0.5}),
        )
        self.assertNotIn(
            "high_sample_concentration",
            diversity_observations({"top1_mass": 0.8999999, "unique_fraction": 0.5}),
        )
        self.assertNotIn("mode_collapse", diversity_flags({"top1_mass": 1.0}))

    def test_low_diversity_boundary_is_inclusive(self) -> None:
        self.assertIn(
            "low_diversity",
            diversity_flags({"top1_mass": 0.1, "occupancy_efficiency": 0.05}),
        )
        self.assertNotIn(
            "low_diversity",
            diversity_flags({"top1_mass": 0.1, "occupancy_efficiency": 0.0500001}),
        )

    def test_poor_mixing_boundary(self) -> None:
        fires = {"autocorrelation_status": "ok", "tau_hat": 10.0, "draws_per_chain": 499}
        silent = {"autocorrelation_status": "ok", "tau_hat": 10.0, "draws_per_chain": 500}
        self.assertIn("poor_mixing", energy_flags(fires))
        self.assertNotIn("poor_mixing", energy_flags(silent))


class NoRecentImprovementObservationSemanticsTests(unittest.TestCase):
    def test_no_recent_improvement_observation_semantics(self) -> None:
        improving_to_the_end = energy_section([[5.0, 4.0, 3.0, 2.0]])
        self.assertTrue(improving_to_the_end["recent_improvement"])
        self.assertNotIn("no_recent_improvement", energy_flags(improving_to_the_end))

        # A sampler that finds the optimum on the first read and never
        # improves again still records this: it's an intended stop-signal,
        # not a claim that the run performed badly.
        never_improves_after_first_read = energy_section([[2.0, 5.0, 5.0, 5.0, 5.0, 5.0]])
        self.assertFalse(never_improves_after_first_read["recent_improvement"])
        self.assertNotIn("no_recent_improvement", energy_flags(never_improves_after_first_read))
        self.assertIn("no_recent_improvement", energy_observations(never_improves_after_first_read))


class RaggedAndEmptyChainHandlingTests(unittest.TestCase):
    def test_empty_chain_dropped_result_matches(self) -> None:
        with_empty_chain = ess_mean([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], []])
        without_empty_chain = ess_mean([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]])
        self.assertEqual(with_empty_chain, without_empty_chain)

    def test_ragged_chains_truncate_to_shortest_before_rhat(self) -> None:
        ragged = split_rhat([[1, 2, 3, 4, 5, 6, 7], [1, 2, 3, 4]])
        truncated_equivalent = split_rhat([[1, 2, 3, 4], [1, 2, 3, 4]])
        self.assertEqual(ragged["rhat_status"], "ok")
        self.assertEqual(ragged, truncated_equivalent)

    def test_below_minimum_draws_reports_insufficient_data(self) -> None:
        result = ess_mean([[1.0, 2.0, 3.0]])
        self.assertEqual(result["autocorrelation_status"], "insufficient_data")
        self.assertEqual(result["ess_status"], "insufficient_data")

    def test_single_chain_reports_insufficient_data_for_rhat(self) -> None:
        result = split_rhat([[1.0] * 10])
        self.assertEqual(result["rhat_status"], "insufficient_data")


class NearConstantTraceResolutionThresholdTests(unittest.TestCase):
    def test_range_below_resolution_is_constant_trace(self) -> None:
        # max - min = 5e-16 - 0.0 = 5e-16 < 1e-15 (the arviz-matching
        # constant-array resolution), so this must be treated as constant.
        chain = [0.0, 5e-16, 0.0, 5e-16, 0.0, 5e-16, 0.0, 5e-16]
        result = ess_mean([chain])
        self.assertEqual(result["autocorrelation_status"], "constant_trace")
        self.assertEqual(result["ess_status"], "undefined_constant_trace")

    def test_range_above_resolution_is_ok(self) -> None:
        # max - min = 2e-15 - 0.0 = 2e-15 >= 1e-15, so this must NOT be
        # treated as constant and must return a numeric result.
        chain = [0.0, 2e-15, 0.0, 2e-15, 0.0, 2e-15, 0.0, 2e-15]
        result = ess_mean([chain])
        self.assertEqual(result["autocorrelation_status"], "ok")
        self.assertIsNotNone(result["tau_hat"])
        self.assertIsNotNone(result["ess"])


if __name__ == "__main__":
    unittest.main()
