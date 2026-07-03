"""Cross-check gibbsiq.diagnostics ESS/R-hat against arviz (skipped without arviz)."""

from __future__ import annotations

import json
import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    import arviz
    import numpy

    ARVIZ_AVAILABLE = True
except ImportError:
    ARVIZ_AVAILABLE = False

from gibbsiq.diagnostics import ess_mean, rank_normalized_split_rhat, split_rhat  # noqa: E402

SWEEP_SHAPES = ((2, 8), (3, 4), (2, 5), (4, 16), (2, 100), (4, 250))

# NormalDist.inv_cdf (Wichura AS 241) and scipy's Cephes ndtri differ below
# 1e-8 in the tails; the estimator agrees to machine precision on top of that.
RANK_TOLERANCE = 1e-8


def load_diagnostic_fixtures() -> list[dict]:
    path = REPO_ROOT / "reference" / "08-evaluation" / "fixtures" / "diagnostic-fixtures.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload["fixtures"]


def chains_from_fixture_input(fixture_input: dict) -> list[list[float]] | None:
    if "chains" in fixture_input:
        rows = sorted(fixture_input["chains"], key=lambda row: row["chain_id"])
        return [row["energy_trace"] for row in rows]
    if "energy_trace" in fixture_input:
        return [fixture_input["energy_trace"]]
    return None


def gaussian_chains(seed: int, num_chains: int, num_draws: int) -> list[list[float]]:
    rng = random.Random(seed)
    return [[rng.gauss(0.0, 1.0) for _ in range(num_draws)] for _ in range(num_chains)]


def ar1_chains(seed: int, num_chains: int, num_draws: int, phi: float) -> list[list[float]]:
    rng = random.Random(seed)
    chains = []
    for _ in range(num_chains):
        chain = [rng.gauss(0.0, 1.0)]
        for _ in range(num_draws - 1):
            chain.append(phi * chain[-1] + rng.gauss(0.0, 1.0))
        chains.append(chain)
    return chains


@unittest.skipUnless(ARVIZ_AVAILABLE, "arviz not installed")
class ArvizCrosscheckTest(unittest.TestCase):
    def test_ess_matches_arviz_for_fixtures_our_functions_call_ok(self) -> None:
        for fixture in load_diagnostic_fixtures():
            chains = chains_from_fixture_input(fixture["input"])
            if chains is None:
                continue
            result = ess_mean(chains)
            if result["ess_status"] != "ok":
                continue
            arviz_ess = float(arviz.ess(numpy.asarray(chains, dtype=float), method="mean"))
            self.assertAlmostEqual(result["ess"] / arviz_ess, 1.0, delta=1e-9, msg=fixture["id"])

    def test_rhat_matches_arviz_for_fixtures_our_functions_call_ok(self) -> None:
        for fixture in load_diagnostic_fixtures():
            chains = chains_from_fixture_input(fixture["input"])
            if chains is None or len(chains) < 2:
                continue
            result = split_rhat(chains)
            if result["rhat_status"] != "ok":
                continue
            arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="split"))
            self.assertAlmostEqual(result["rhat"], arviz_rhat, delta=1e-9, msg=fixture["id"])

    def test_ess_matches_arviz_for_seeded_gaussian_sweep(self) -> None:
        for seed in range(10):
            for num_chains, num_draws in SWEEP_SHAPES:
                chains = gaussian_chains(seed, num_chains, num_draws)
                result = ess_mean(chains)
                arviz_ess = float(arviz.ess(numpy.asarray(chains, dtype=float), method="mean"))
                self.assertAlmostEqual(
                    result["ess"] / arviz_ess,
                    1.0,
                    delta=1e-9,
                    msg=f"seed={seed} shape=({num_chains}, {num_draws})",
                )

    def test_rhat_matches_arviz_for_seeded_gaussian_sweep(self) -> None:
        for seed in range(10):
            for num_chains, num_draws in SWEEP_SHAPES:
                if num_chains < 2:
                    continue
                chains = gaussian_chains(seed, num_chains, num_draws)
                result = split_rhat(chains)
                arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="split"))
                self.assertAlmostEqual(
                    result["rhat"],
                    arviz_rhat,
                    delta=1e-9,
                    msg=f"seed={seed} shape=({num_chains}, {num_draws})",
                )

    def test_rank_rhat_matches_arviz_for_fixtures_our_functions_call_ok(self) -> None:
        for fixture in load_diagnostic_fixtures():
            chains = chains_from_fixture_input(fixture["input"])
            if chains is None or len(chains) < 2:
                continue
            result = rank_normalized_split_rhat(chains)
            if result["rank_normalized_rhat_status"] != "ok":
                continue
            arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="rank"))
            self.assertAlmostEqual(
                result["rank_normalized_rhat"], arviz_rhat, delta=RANK_TOLERANCE, msg=fixture["id"]
            )

    def test_rank_rhat_matches_arviz_for_seeded_gaussian_sweep(self) -> None:
        for seed in range(10):
            for num_chains, num_draws in SWEEP_SHAPES:
                if num_chains < 2:
                    continue
                chains = gaussian_chains(seed, num_chains, num_draws)
                result = rank_normalized_split_rhat(chains)
                arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="rank"))
                self.assertAlmostEqual(
                    result["rank_normalized_rhat"],
                    arviz_rhat,
                    delta=RANK_TOLERANCE,
                    msg=f"seed={seed} shape=({num_chains}, {num_draws})",
                )

    def test_rank_rhat_matches_arviz_for_discrete_tie_heavy_chains(self) -> None:
        # The regime this project lives in: energy/magnetization traces over
        # small Ising models take a handful of distinct values, so almost
        # every draw is tied. Average-tie ranking must agree with scipy
        # rankdata exactly for the values to line up.
        rng = random.Random(20260703_42)
        for levels in ((-1.0, 1.0), (-2.0, 0.0, 3.0), (0.0, 1.0, 2.0, 5.0)):
            chains = [[rng.choice(levels) for _ in range(300)] for _ in range(4)]
            result = rank_normalized_split_rhat(chains)
            self.assertEqual(result["rank_normalized_rhat_status"], "ok", msg=str(levels))
            arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="rank"))
            self.assertAlmostEqual(
                result["rank_normalized_rhat"], arviz_rhat, delta=RANK_TOLERANCE, msg=str(levels)
            )

    def test_rank_rhat_folded_collapse_matches_arviz_bulk_only_result(self) -> None:
        # Balanced two-valued chains symmetric around the pooled median fold
        # to a constant: arviz's max(bulk, NaN) silently returns the bulk
        # component, and Gibbsiq's explicit folded-collapse rule
        # (EVAL-EQ-013) must land on the same number.
        import warnings

        chains = [[1.0, -1.0] * 50, [-1.0, 1.0] * 50]
        result = rank_normalized_split_rhat(chains)
        self.assertEqual(result["rank_normalized_rhat_status"], "ok")
        self.assertIsNone(result["rank_normalized_rhat_folded"])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="rank"))
        self.assertAlmostEqual(result["rank_normalized_rhat"], arviz_rhat, delta=RANK_TOLERANCE)

    def test_rank_rhat_matches_arviz_for_variance_only_disagreement(self) -> None:
        rng = random.Random(20260703_09)
        chains = [
            [rng.gauss(0.0, 0.1) for _ in range(500)],
            [rng.gauss(0.0, 0.1) for _ in range(500)],
            [rng.gauss(0.0, 10.0) for _ in range(500)],
            [rng.gauss(0.0, 10.0) for _ in range(500)],
        ]
        result = rank_normalized_split_rhat(chains)
        arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="rank"))
        self.assertGreater(result["rank_normalized_rhat"], 1.01)
        self.assertAlmostEqual(result["rank_normalized_rhat"], arviz_rhat, delta=RANK_TOLERANCE)

    def test_rank_rhat_matches_arviz_for_ar1_process(self) -> None:
        chains = ar1_chains(seed=98765, num_chains=4, num_draws=1000, phi=0.9)
        result = rank_normalized_split_rhat(chains)
        arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="rank"))
        self.assertAlmostEqual(result["rank_normalized_rhat"], arviz_rhat, delta=RANK_TOLERANCE)

    def test_ess_matches_arviz_for_ar1_process(self) -> None:
        chains = ar1_chains(seed=12345, num_chains=4, num_draws=1000, phi=0.9)
        result = ess_mean(chains)
        arviz_ess = float(arviz.ess(numpy.asarray(chains, dtype=float), method="mean"))
        self.assertAlmostEqual(result["ess"] / arviz_ess, 1.0, delta=1e-9)

    def test_rhat_matches_arviz_for_ar1_process(self) -> None:
        chains = ar1_chains(seed=54321, num_chains=4, num_draws=1000, phi=0.9)
        result = split_rhat(chains)
        arviz_rhat = float(arviz.rhat(numpy.asarray(chains, dtype=float), method="split"))
        self.assertAlmostEqual(result["rhat"], arviz_rhat, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
