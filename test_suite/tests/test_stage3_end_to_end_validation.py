"""Stage 3 end-to-end validation: brute-forceable models through the real sampler.

Every assertion here is anchored to an independently computable ground truth:
exhaustive state enumeration for distributions and optima, and hand-analyzable
sampler regimes (frozen, trapped, well-mixed) for the diagnostics flags. The
degenerate double-well tests pin the closed blind spot of the energy-only
chain-disagreement family: two chains frozen in distinct ground states of
EQUAL energy are invisible to R-hat over energy, and since 2026-07-03 the
runtime wires the magnetization trace into the chain-disagreement flag
(EVAL-EQ-007 magnetization wiring), so the payload itself now reports the
trap. The formerly-flipping blind-spot assertions were flipped when that
wiring landed.

Statistical assertions use fixed seeds, so they are deterministic; tolerances
keep an order-of-magnitude margin over the observed error (frustrated-triangle
total variation measured at 0.013 with the pinned seed, asserted below 0.03).
"""

from __future__ import annotations

import itertools
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import SamplerConfig, compile_ising  # noqa: E402
from gibbsiq.diagnostics import chain_flags, chain_section  # noqa: E402

try:  # noqa: SIM105
    import thrml  # noqa: F401

    THRML_AVAILABLE = True
except ImportError:
    THRML_AVAILABLE = False

if THRML_AVAILABLE:
    from gibbsiq import THRMLSampler

TRIANGLE_READS = 8000
TRIANGLE_TV_TOLERANCE = 0.03


def enumerate_energies(model) -> dict[tuple[int, ...], float]:
    states = itertools.product((-1, 1), repeat=len(model.variables))
    return {
        state: model.energy(dict(zip(model.variables, state))) for state in states
    }


def boltzmann_probabilities(
    energies: dict[tuple[int, ...], float], beta: float
) -> dict[tuple[int, ...], float]:
    weights = {state: math.exp(-beta * energy) for state, energy in energies.items()}
    normalization = math.fsum(weights.values())
    return {state: weight / normalization for state, weight in weights.items()}


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class FrustratedTriangleGroundTruthTests(unittest.TestCase):
    """One well-mixed run on a frustrated triangle with fields and offset,
    validated against exhaustive enumeration and shared across tests."""

    BETA = 0.8

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = compile_ising(
            {"a": 0.3, "b": -0.2, "c": 0.1},
            {("a", "b"): 0.5, ("b", "c"): 0.5, ("a", "c"): 0.5},
            offset=1.7,
        )
        cls.energies = enumerate_energies(cls.model)
        cls.probabilities = boltzmann_probabilities(cls.energies, cls.BETA)
        config = SamplerConfig(
            beta=cls.BETA, n_warmup=500, steps_per_sample=2, num_chains=4, seed=7
        )
        cls.result = THRMLSampler(config).sample(cls.model, num_reads=TRIANGLE_READS)

    def test_empirical_distribution_matches_enumeration(self) -> None:
        counts: dict[tuple[int, ...], int] = {}
        for sample in self.result.samples:
            state = tuple(sample[variable] for variable in self.result.variables)
            counts[state] = counts.get(state, 0) + 1
        total_variation = 0.5 * math.fsum(
            abs(counts.get(state, 0) / TRIANGLE_READS - probability)
            for state, probability in self.probabilities.items()
        )
        self.assertLess(total_variation, TRIANGLE_TV_TOLERANCE)

    def test_best_energy_equals_enumerated_optimum_with_offset(self) -> None:
        exact_optimum = min(self.energies.values())
        self.assertAlmostEqual(self.result.best_energy, exact_optimum, places=9)
        self.assertAlmostEqual(
            self.model.energy(self.result.best_sample), self.result.best_energy, places=9
        )

    def test_healthy_run_reports_healthy_core_metrics(self) -> None:
        diagnostics = self.result.diagnostics
        self.assertEqual(diagnostics["energy"]["ess_status"], "ok")
        self.assertGreater(diagnostics["energy"]["ess"], 400.0)
        self.assertEqual(diagnostics["chains"]["rhat_status"], "ok")
        self.assertLess(diagnostics["chains"]["rhat"], 1.01)
        self.assertEqual(diagnostics["chains"]["rank_normalized_rhat_status"], "ok")
        self.assertLess(diagnostics["chains"]["rank_normalized_rhat"], 1.01)
        # A provably well-mixed run must stay quiet on BOTH disagreement
        # traces: the magnetization subsection reports healthy values too.
        magnetization = diagnostics["chains"]["magnetization"]
        self.assertEqual(magnetization["rhat_status"], "ok")
        self.assertLess(magnetization["rhat"], 1.01)
        self.assertNotIn("chain_disagreement", diagnostics["flags"])
        self.assertNotIn("mode_collapse", diagnostics["flags"])
        self.assertNotIn("low_ess", diagnostics["flags"])
        self.assertNotIn("poor_mixing", diagnostics["flags"])
        # Diversity top-1 mass must track the exact Boltzmann maximum, not 1.0.
        self.assertAlmostEqual(
            diagnostics["diversity"]["top1_mass"],
            max(self.probabilities.values()),
            delta=0.05,
        )

    def test_small_state_space_dilutes_diversity_flags_known_limitation(self) -> None:
        # CHARACTERIZATION, not an endorsement: a 3-variable model has 8
        # reachable states, so unique_fraction <= 8/8000 and low_diversity
        # fires on this provably well-mixed run; the long plateau after the
        # optimum is found on an early read likewise fires
        # no_recent_improvement. Any future fix (e.g. normalizing
        # unique_fraction by min(num_reads, 2**num_variables)) must flip this
        # test and update EVAL-EQ-011 first.
        flags = self.result.diagnostics["flags"]
        self.assertIn("low_diversity", flags)
        self.assertIn("no_recent_improvement", flags)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class FrozenSamplerTests(unittest.TestCase):
    """At beta=20 on a strong-field model the sampler freezes into the unique
    ground state; the payload must report pathology, never a healthy ESS."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = compile_ising({"a": 1.0, "b": 1.0, "c": 1.0}, {}, offset=0.5)
        config = SamplerConfig(beta=20.0, n_warmup=200, num_chains=2, seed=3)
        cls.result = THRMLSampler(config).sample(cls.model, num_reads=100)

    def test_frozen_run_finds_exact_optimum(self) -> None:
        self.assertAlmostEqual(self.result.best_energy, -2.5, places=9)
        self.assertEqual(
            self.result.best_sample, {"a": -1, "b": -1, "c": -1}
        )

    def test_frozen_run_flags_collapse_and_reports_constant_statuses(self) -> None:
        diagnostics = self.result.diagnostics
        self.assertEqual(
            diagnostics["flags"],
            [
                "mode_collapse",
                "low_diversity",
                "no_recent_improvement",
                "zero_energy_variance",
                "zero_within_chain_variance",
            ],
        )
        self.assertEqual(diagnostics["energy"]["ess_status"], "undefined_constant_trace")
        self.assertEqual(
            diagnostics["energy"]["autocorrelation_status"], "constant_trace"
        )
        self.assertEqual(diagnostics["chains"]["rhat_status"], "undefined_constant_trace")
        self.assertEqual(diagnostics["diversity"]["unique_states"], 1)
        self.assertEqual(diagnostics["diversity"]["top1_mass"], 1.0)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class DegenerateDoubleWellBlindSpotTests(unittest.TestCase):
    """Two-spin ferromagnet at beta=15: both ground states (++ and --) share
    energy -1. With seed 0 and random init the two chains freeze in OPPOSITE
    wells (verified during calibration), the archetypal multimodal trap."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = compile_ising({}, {("a", "b"): -1.0})
        config = SamplerConfig(
            beta=15.0, n_warmup=300, num_chains=2, seed=0, init="random"
        )
        cls.result = THRMLSampler(config).sample(cls.model, num_reads=100)
        cls.magnetization = cls.result.traces["magnetization"]

    def test_chains_are_actually_trapped_in_opposite_wells(self) -> None:
        # Guard assertion: if a thrml/jax upgrade reseeds the trap away, the
        # blind-spot tests below become vacuous; re-pin the seed instead.
        first, second = self.magnetization
        self.assertEqual(set(first), {1.0})
        self.assertEqual(set(second), {-1.0})
        self.assertEqual(self.result.diagnostics["diversity"]["unique_states"], 2)

    def test_equal_energy_wells_now_fire_chain_disagreement_via_magnetization(self) -> None:
        # FLIPPED 2026-07-03 (was
        # test_energy_only_chain_disagreement_is_blind_to_equal_energy_wells)
        # when the EVAL-EQ-007 magnetization wiring landed. Both wells sit at
        # energy -1, so the energy traces of the two trapped chains are still
        # IDENTICAL constants and the ENERGY-trace R-hat keys still report the
        # constant-trace status -- no statistic of the energy trace can
        # distinguish this pathological run from a frozen unimodal one. The
        # payload nevertheless flags chain_disagreement, because the runtime
        # now feeds the magnetization trace into the chains.magnetization
        # subsection where constant +1 vs constant -1 chains hit the
        # zero-within-variance (infinite R-hat) path.
        diagnostics = self.result.diagnostics
        self.assertTrue(
            all(energy == -1.0 for chain in self.result.traces["energy"] for energy in chain)
        )
        self.assertEqual(diagnostics["chains"]["rhat_status"], "undefined_constant_trace")
        self.assertIn("chain_disagreement", diagnostics["flags"])
        magnetization = diagnostics["chains"]["magnetization"]
        self.assertEqual(
            magnetization["rhat_status"], "undefined_or_infinite_zero_within_variance"
        )
        self.assertEqual(
            magnetization["rank_normalized_rhat_status"],
            "undefined_or_infinite_zero_within_variance",
        )
        # The rest of the pathology report is unchanged by the wiring.
        self.assertNotIn("mode_collapse", diagnostics["flags"])
        self.assertIn("zero_energy_variance", diagnostics["flags"])
        self.assertIn("zero_within_chain_variance", diagnostics["flags"])
        self.assertIn("low_diversity", diagnostics["flags"])

    def test_magnetization_trace_carries_the_disagreement_signal_standalone(self) -> None:
        # The payload wiring above is built from exactly this signal: the
        # chain-disagreement estimators applied directly to the captured
        # magnetization trace expose the trap with zero new estimator code.
        section = chain_section(self.magnetization)
        self.assertEqual(
            section["rhat_status"], "undefined_or_infinite_zero_within_variance"
        )
        self.assertIn("chain_disagreement", chain_flags(section))


if __name__ == "__main__":
    unittest.main()
