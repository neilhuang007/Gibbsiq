"""Independent ground-truth tests for ``src/gibbsiq/diagnostics.py`` (Stage 3).

``test_diagnostics_arviz_crosscheck.py`` pins agreement with arviz's own
algorithm. This file does not lean on arviz (or numpy) at all: every
expectation here comes from statistical theory (closed-form AR(1)
autocorrelation time, iid sample-size recovery), hand-derived arithmetic
worked out in comments, or brute-force stdlib recomputation of the same
quantity by a structurally different code path (e.g. an explicit O(R^2)
pairwise loop standing in for the count-weighted diversity formula). Every
random draw goes through a seeded ``random.Random`` instance so runs are
deterministic. Standard library only: ``unittest``, ``random``, ``math``.

Where a scenario is a documented limitation of the plain (non-rank-normalized,
non-folded) split R-hat variant (EVAL-EQ-007), or a known gap in energy-only
diagnostics versus raw state traces, the test says so in a comment. Both
characterized blind spots were closed on 2026-07-03: the rank-normalized +
folded variant (EVAL-EQ-013) now reports under separately named keys and the
magnetization trace feeds chain-disagreement (EVAL-EQ-007 wiring); the
formerly-flipping characterization tests below were flipped accordingly while
the plain `rhat` key keeps its original, deliberately blind semantics.
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
    diversity_section,
    energy_flags,
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
    """Theoretical integrated autocorrelation time under the project's
    convention (EVAL-EQ-008: tau = 1 + 2 * sum_k rho_k) for an AR(1) process
    with rho_k = phi**k is a geometric series:

        tau_theory = 1 + 2 * sum_{k=1..inf} phi**k = 1 + 2*phi/(1-phi)
                   = (1 - phi + 2*phi) / (1 - phi) = (1 + phi) / (1 - phi)

    This is independent of arviz and independent of the Geyer truncation
    machinery under test; it is closed-form statistics.

    A SINGLE realization's tau_hat has non-trivial sampling variance,
    especially near phi=0.9 (slow decay makes the long-lag rho_hat terms
    noisy): an empirical 8-seed sweep at this file's exact configuration
    gave tau_hat ranging 17.8-23.7 around the true 19.0, i.e. individual
    draws routinely miss a 15% band. Averaging several independent seeded
    replicates (still fully deterministic) is the standard way to compare a
    noisy point estimator against its theoretical target, and is more
    honest than either inflating the tolerance until any single draw passes
    or silently hand-picking one lucky seed.
    """

    def _mean_tau_hat(self, phi: float, num_chains: int, num_draws: int, seeds: range) -> float:
        tau_hats = []
        for seed in seeds:
            chains = generate_ar1_chains(seed=seed, phi=phi, num_chains=num_chains, num_draws=num_draws)
            result = ess_mean(chains)
            self.assertEqual(result["autocorrelation_status"], "ok")
            # size/tau_hat consistency holds for EVERY replicate individually:
            # split doubles the chain count and halves the per-chain draw
            # count, so size = (2*num_chains) * (num_draws//2). This is an
            # algebraic identity of the estimator, not a statistical claim.
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
        # Discrete +-1 traces (heavy ties) mimic a spin/energy trace far from
        # the continuous-Gaussian case the Geyer algorithm is usually
        # exercised on; this pins that mean-ESS still behaves for two-valued
        # data.
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
    def test_variance_only_disagreement_caught_by_rank_normalized_rhat(self) -> None:
        # FLIPPED 2026-07-03 (was
        # test_plain_rhat_blind_to_variance_only_disagreement_known_limitation)
        # when the EVAL-EQ-013 rank-normalized + folded variant landed. The
        # plain split R-hat (EVAL-EQ-007) remains blind by design: it compares
        # between-chain MEAN disagreement (B) against within-chain variance
        # (W), and all four chains share mean 0.0 while differing only in
        # SCALE (sd 0.1 vs sd 10.0) — that blindness is still pinned below
        # because the plain `rhat` key must never change meaning. The folded
        # component of the rank-normalized variant converts the scale
        # difference into a location difference, so the separately named
        # `rank_normalized_rhat` key exceeds the threshold and
        # chain_disagreement now fires through the rank path.
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

    def test_identical_constant_chains_blind_spot_without_magnetization(self) -> None:
        # Synthetic double-well characterization: two chains are each frozen
        # in a DIFFERENT degenerate ground state that happens to carry the
        # SAME energy. Energy-only R-hat is blind to this because the energy
        # trace itself is constant and identical across chains -- only the
        # raw magnetization/state trace exposes the disagreement. Without
        # magnetization_chains the payload therefore must NOT claim
        # disagreement; the closing wiring is exercised in the companion
        # test below.
        payload = compute_diagnostics(
            energy_chains=self.ENERGY_CHAINS, samples=self.SAMPLES, variables=self.VARIABLES
        )

        self.assertNotIn("chain_disagreement", payload["flags"])
        self.assertIn("zero_energy_variance", payload["flags"])
        self.assertIn("zero_within_chain_variance", payload["flags"])
        self.assertIn("low_diversity", payload["flags"])
        self.assertNotIn("mode_collapse", payload["flags"])
        self.assertEqual(payload["diversity"]["unique_states"], 2)
        self.assertEqual(payload["chains"]["rhat_status"], "undefined_constant_trace")
        self.assertEqual(payload["chains"]["rank_normalized_rhat_status"], "undefined_constant_trace")
        self.assertNotIn("magnetization", payload["chains"])

    def test_magnetization_wiring_closes_the_equal_energy_blind_spot(self) -> None:
        # LANDED 2026-07-03 (EVAL-EQ-007 magnetization wiring): the same
        # payload with the per-chain magnetization trace supplied now fires
        # chain_disagreement through the chains.magnetization subsection —
        # chain 0 sits at constant magnetization +1 and chain 1 at -1, the
        # zero-within-variance (infinite R-hat) path. The energy-family
        # constant-trace flags are unchanged: magnetization contributes ONLY
        # chain_disagreement.
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
        # Energy-family flags are untouched by the magnetization subsection.
        self.assertIn("zero_energy_variance", payload["flags"])
        self.assertIn("zero_within_chain_variance", payload["flags"])
        self.assertNotIn("mode_collapse", payload["flags"])
        self.assertEqual(payload["chains"]["rhat_status"], "undefined_constant_trace")

    def test_frozen_same_well_magnetization_adds_no_disagreement(self) -> None:
        # Control for the wiring: a sampler frozen in ONE state produces
        # identical constant magnetization chains, which must map to the
        # constant-trace status, never to chain_disagreement. The residual
        # all-chains-in-one-well trap stays invisible to every within-sample
        # diagnostic (EVAL-EQ-007 honest-caveat note).
        payload = compute_diagnostics(
            energy_chains=self.ENERGY_CHAINS,
            samples=[{"a": 1, "b": 1}] * 100,
            variables=self.VARIABLES,
            magnetization_chains=[[1.0] * 50, [1.0] * 50],
        )
        self.assertNotIn("chain_disagreement", payload["flags"])
        self.assertEqual(payload["chains"]["magnetization"]["rhat_status"], "undefined_constant_trace")


class RankNormalizedRhatHandComputedTests(unittest.TestCase):
    def test_tied_alternating_chains_exact_value_and_folded_collapse(self) -> None:
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

    def test_shifted_tied_chains_match_hand_derived_rank_arithmetic(self) -> None:
        # chains = [[1,2,1,2],[3,4,3,4]] -> split chains [1,2],[3,4],[1,2],[3,4].
        # Pooled: two of each value 1,2,3,4 (S=8); average-tie ranks
        #   1 -> 1.5, 2 -> 3.5, 3 -> 5.5, 4 -> 7.5.
        # The expectation below recomputes bulk/folded from these HAND-LISTED
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
        # The defining property of rank normalization (Vehtari et al. 2021):
        # any strictly increasing transform preserves the pooled ranks, hence
        # the z-scores, hence the BULK component BIT-FOR-BIT. The FOLDED
        # component is deliberately excluded from this claim: folding takes
        # |x - median(x)| on the RAW scale before re-ranking, and a nonlinear
        # transform like exp() moves points asymmetrically around the median,
        # so folded values re-rank differently -- true of arviz and the paper
        # by construction, not a Gibbsiq deviation. The plain split R-hat has
        # no invariance at all, which is exactly why the variants live under
        # separate keys.
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

    def test_all_components_invariant_under_positive_affine_transform(self) -> None:
        # Affine maps commute with the median and scale |x - median|
        # uniformly, so ranks of both the raw and the folded draws are
        # preserved and EVERY key must match. The data and coefficients here
        # are small integers so every operation is exact in floating point:
        # with CONTINUOUS data the invariance holds only up to an inherent
        # knife-edge of the published algorithm (arviz included) -- the
        # pooled split count is always even, the median is the average of
        # the two middle order statistics, and those two draws fold to
        # exactly equidistant values whose bit-exact tie is rounding-luck.
        # Verified empirically: a gaussian seed under x -> 3.5x - 11 flips
        # exactly that one tie and shifts the folded component by 4e-6.
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

    def test_chains_constant_at_distinct_values_report_zero_within_variance(self) -> None:
        result = rank_normalized_split_rhat([[1.0] * 10, [2.0] * 10])
        self.assertEqual(result["rank_normalized_rhat_status"], "undefined_or_infinite_zero_within_variance")
        self.assertIsNone(result["rank_normalized_rhat"])

    def test_folded_infinite_scale_disagreement_reports_zero_within_variance(self) -> None:
        # Extreme variance-only disagreement: both chains alternate
        # symmetrically around the pooled median 0 with different amplitudes,
        # so the folded trace is constant WITHIN each chain (1 vs 3) while
        # differing BETWEEN chains -> folded W = 0 with B > 0, the infinite
        # folded R-hat. Bulk is well defined (all chain means sit at rank
        # center), so the bulk key stays numeric per EVAL-EQ-013 while the
        # combined value is None under the zero-within-variance status, and
        # chain_disagreement fires.
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
    def test_iid_gaussian_and_heavy_tie_binary_chains_report_healthy_values(self) -> None:
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

    def test_mean_shifted_chains_fire_through_rank_path_too(self) -> None:
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
        self.assertAlmostEqual(section["mean_pairwise_hamming_distance"], expected_mean_hamming, places=12)


class TraceBruteForceCrossCheckTests(unittest.TestCase):
    def test_magnetization_and_distance_to_best_match_brute_force(self) -> None:
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
    """Pin the exact inclusive/exclusive boundary semantics of each flag
    predicate by calling the flag functions directly against crafted dicts.
    """

    def test_low_ess_boundary(self) -> None:
        just_below_threshold = {
            "ess_status": "ok",
            "ess": 399.999999999,
            "autocorrelation_status": "ok",
            "tau_hat": 1.0,
            "draws_per_chain": 1000,
            "recent_improvement": True,
            "variance": 1.0,
            "count": 10,
        }
        at_threshold = dict(just_below_threshold, ess=400.0)
        self.assertIn("low_ess", energy_flags(just_below_threshold))
        self.assertNotIn("low_ess", energy_flags(at_threshold))

    def test_mode_collapse_boundary_is_inclusive(self) -> None:
        self.assertIn("mode_collapse", diversity_flags({"top1_mass": 0.9, "unique_fraction": 0.5}))
        self.assertNotIn("mode_collapse", diversity_flags({"top1_mass": 0.8999999, "unique_fraction": 0.5}))

    def test_low_diversity_boundary_is_inclusive(self) -> None:
        self.assertIn("low_diversity", diversity_flags({"top1_mass": 0.1, "unique_fraction": 0.05}))
        self.assertNotIn("low_diversity", diversity_flags({"top1_mass": 0.1, "unique_fraction": 0.0500001}))

    def test_poor_mixing_boundary(self) -> None:
        fires = {"autocorrelation_status": "ok", "tau_hat": 10.0, "draws_per_chain": 499}
        silent = {"autocorrelation_status": "ok", "tau_hat": 10.0, "draws_per_chain": 500}
        self.assertIn("poor_mixing", energy_flags(fires))
        self.assertNotIn("poor_mixing", energy_flags(silent))


class NoRecentImprovementFlagSemanticsTests(unittest.TestCase):
    def test_no_recent_improvement_flag_semantics(self) -> None:
        improving_to_the_end = energy_section([[5.0, 4.0, 3.0, 2.0]])
        self.assertTrue(improving_to_the_end["recent_improvement"])
        self.assertNotIn("no_recent_improvement", energy_flags(improving_to_the_end))

        # A sampler that finds the optimum on the very FIRST read and then
        # never improves again still raises this flag: it is an intended
        # stop-signal ("nothing has gotten better in the back half of the
        # run"), not a claim that the run performed badly.
        never_improves_after_first_read = energy_section([[2.0, 5.0, 5.0, 5.0, 5.0, 5.0]])
        self.assertFalse(never_improves_after_first_read["recent_improvement"])
        self.assertIn("no_recent_improvement", energy_flags(never_improves_after_first_read))


class RaggedAndEmptyChainHandlingTests(unittest.TestCase):
    def test_empty_chain_is_dropped_and_result_matches_without_it(self) -> None:
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
