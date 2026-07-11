"""Stage 3 end-to-end validation: brute-forceable models through the real sampler.

Assertions are anchored to exhaustive state enumeration (distributions, optima) and
hand-analyzable sampler regimes (frozen, trapped, well-mixed) for the diagnostics flags.
Seeds are fixed, so results are deterministic; tolerances keep an order-of-magnitude
margin over observed error.
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
    return {state: model.energy(dict(zip(model.variables, state))) for state in states}


def boltzmann_probabilities(
    energies: dict[tuple[int, ...], float], beta: float
) -> dict[tuple[int, ...], float]:
    weights = {state: math.exp(-beta * energy) for state, energy in energies.items()}
    normalization = math.fsum(weights.values())
    return {state: weight / normalization for state, weight in weights.items()}


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class FrustratedTriangleGroundTruthTests(unittest.TestCase):
    """One well-mixed run on a frustrated triangle, validated against exhaustive enumeration."""

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
        config = SamplerConfig(beta=cls.BETA, n_warmup=500, steps_per_sample=2, num_chains=4, seed=7)
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
        self.assertAlmostEqual(self.model.energy(self.result.best_sample), self.result.best_energy, places=9)

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

    def test_finite_support_plateau_stays_healthy(self) -> None:
        diagnostics = self.result.diagnostics
        # All 8 states are observed: the raw unique fraction is diluted by
        # 8000 reads, while finite-support occupancy remains complete.
        self.assertEqual(diagnostics["diversity"]["unique_states"], 8)
        self.assertEqual(diagnostics["diversity"]["occupancy_efficiency"], 1.0)
        self.assertNotIn("low_diversity", diagnostics["flags"])
        self.assertNotIn("no_recent_improvement", diagnostics["flags"])
        self.assertEqual(diagnostics["observations"], ["no_recent_improvement"])


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class FrozenSamplerTests(unittest.TestCase):
    """At beta=20 on a strong-field model the sampler freezes into the unique ground state."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = compile_ising({"a": 1.0, "b": 1.0, "c": 1.0}, {}, offset=0.5)
        config = SamplerConfig(beta=20.0, n_warmup=200, num_chains=2, seed=3)
        cls.result = THRMLSampler(config).sample(cls.model, num_reads=100)

    def test_frozen_run_finds_exact_optimum(self) -> None:
        self.assertAlmostEqual(self.result.best_energy, -2.5, places=9)
        self.assertEqual(self.result.best_sample, {"a": -1, "b": -1, "c": -1})

    def test_frozen_run_reports_concentration_without_diagnosing_mode_collapse(self) -> None:
        diagnostics = self.result.diagnostics
        self.assertEqual(diagnostics["flags"], [])
        self.assertEqual(
            diagnostics["observations"],
            [
                "high_sample_concentration",
                "no_recent_improvement",
                "zero_energy_variance",
                "zero_within_chain_variance",
            ],
        )
        self.assertEqual(diagnostics["energy"]["ess_status"], "undefined_constant_trace")
        self.assertEqual(diagnostics["energy"]["autocorrelation_status"], "constant_trace")
        self.assertEqual(diagnostics["chains"]["rhat_status"], "undefined_constant_trace")
        self.assertEqual(diagnostics["diversity"]["unique_states"], 1)
        self.assertEqual(diagnostics["diversity"]["top1_mass"], 1.0)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class DegenerateDoubleWellBlindSpotTests(unittest.TestCase):
    """Two-spin ferromagnet at beta=15; both ground states (++ and --) share energy -1."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.model = compile_ising({}, {("a", "b"): -1.0})
        config = SamplerConfig(beta=15.0, n_warmup=300, num_chains=2, seed=0, init="random")
        cls.result = THRMLSampler(config).sample(cls.model, num_reads=100)
        cls.magnetization = cls.result.traces["magnetization"]

    def test_chains_trap_in_opposite_wells(self) -> None:
        # Guard: if a thrml/jax upgrade reseeds the trap away, re-pin the seed
        # rather than let the tests below go vacuous.
        first, second = self.magnetization
        self.assertEqual(set(first), {1.0})
        self.assertEqual(set(second), {-1.0})
        self.assertEqual(self.result.diagnostics["diversity"]["unique_states"], 2)

    def test_equal_energy_wells_fire_chain_disagreement(self) -> None:
        # Both wells sit at energy -1, so the energy-trace R-hat is still
        # constant-trace and can't see the trap. Since the EVAL-EQ-007
        # magnetization wiring (2026-07-03), chains.magnetization catches it:
        # constant +1 vs constant -1 hits the zero-within-variance path.
        diagnostics = self.result.diagnostics
        self.assertTrue(all(energy == -1.0 for chain in self.result.traces["energy"] for energy in chain))
        self.assertEqual(diagnostics["chains"]["rhat_status"], "undefined_constant_trace")
        self.assertIn("chain_disagreement", diagnostics["flags"])
        magnetization = diagnostics["chains"]["magnetization"]
        self.assertEqual(magnetization["rhat_status"], "undefined_or_infinite_zero_within_variance")
        self.assertEqual(
            magnetization["rank_normalized_rhat_status"],
            "undefined_or_infinite_zero_within_variance",
        )
        # Flat-energy facts stay recorded as observations, not flags.
        self.assertNotIn("mode_collapse", diagnostics["flags"])
        self.assertNotIn("zero_energy_variance", diagnostics["flags"])
        self.assertNotIn("zero_within_chain_variance", diagnostics["flags"])
        self.assertNotIn("low_diversity", diagnostics["flags"])
        self.assertEqual(
            diagnostics["observations"],
            ["no_recent_improvement", "zero_energy_variance", "zero_within_chain_variance"],
        )

    def test_magnetization_trace_holds_disagreement_signal(self) -> None:
        # Same estimators as the energy-trace path, applied to magnetization directly.
        section = chain_section(self.magnetization)
        self.assertEqual(section["rhat_status"], "undefined_or_infinite_zero_within_variance")
        self.assertIn("chain_disagreement", chain_flags(section))


if __name__ == "__main__":
    unittest.main()
