"""Stage 2 THRML runtime contract tests.

Config validation runs everywhere; the sampling classes exercise the real
THRML/JAX stack and skip when the optional thrml extra is not installed.
The statistical assertions use fixed seeds, so they are deterministic; the
tolerances leave an order-of-magnitude margin over the observed error.
"""

from __future__ import annotations

import itertools
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

import random  # noqa: E402

from gibbsiq import (  # noqa: E402
    BlockPartition,
    SamplerConfig,
    compile_ising,
    compile_qubo,
    compute_diagnostics,
    spin_to_binary,
)

try:  # noqa: SIM105
    import thrml  # noqa: F401

    THRML_AVAILABLE = True
except ImportError:
    THRML_AVAILABLE = False

if THRML_AVAILABLE:
    from gibbsiq import THRMLSampler

DISTRIBUTION_TOLERANCE = 0.025
DISTRIBUTION_READS = 8000


def analytic_boltzmann(model, beta: float) -> dict[tuple[int, ...], float]:
    """Exact Boltzmann probabilities by enumeration; the offset cancels in Z."""
    states = list(itertools.product((-1, 1), repeat=len(model.variables)))
    weights = {state: math.exp(-beta * model.energy(dict(zip(model.variables, state)))) for state in states}
    normalization = sum(weights.values())
    return {state: weight / normalization for state, weight in weights.items()}


def empirical_frequencies(result) -> dict[tuple[int, ...], float]:
    counts: dict[tuple[int, ...], int] = {}
    for sample in result.samples:
        state = tuple(sample[variable] for variable in result.variables)
        counts[state] = counts.get(state, 0) + 1
    total = len(result.samples)
    return {state: count / total for state, count in counts.items()}


class SamplerConfigValidationTests(unittest.TestCase):
    """These do not require thrml; SamplerConfig is a plain dataclass."""

    def test_rejects_nonpositive_beta(self) -> None:
        with self.assertRaises(ValueError):
            SamplerConfig(beta=0.0)
        with self.assertRaises(ValueError):
            SamplerConfig(beta=-1.0)

    def test_rejects_unknown_init_policy(self) -> None:
        with self.assertRaises(ValueError):
            SamplerConfig(init="warm")

    def test_rejects_negative_warmup_and_bad_counts(self) -> None:
        with self.assertRaises(ValueError):
            SamplerConfig(n_warmup=-1)
        with self.assertRaises(ValueError):
            SamplerConfig(steps_per_sample=0)
        with self.assertRaises(ValueError):
            SamplerConfig(num_chains=0)

    def test_rejects_ladder_longer_than_warmup(self) -> None:
        with self.assertRaises(ValueError):
            SamplerConfig(n_warmup=2, warmup_beta_ladder=(0.5, 1.0, 2.0))
        with self.assertRaises(ValueError):
            SamplerConfig(warmup_beta_ladder=())
        with self.assertRaises(ValueError):
            SamplerConfig(warmup_beta_ladder=(0.5, -1.0))

    def test_warmup_segments_split_sweeps_with_remainder_on_last(self) -> None:
        config = SamplerConfig(n_warmup=10, warmup_beta_ladder=(0.5, 1.0, 2.0))
        self.assertEqual(config.warmup_segments(), ((0.5, 3), (1.0, 3), (2.0, 4)))
        self.assertEqual(SamplerConfig().warmup_segments(), ())

    def test_parallel_tempering_config_validation(self) -> None:
        config = SamplerConfig(beta=2.0, parallel_tempering_betas=(0.5, 1.0, 2.0))
        self.assertEqual(config.parallel_tempering_betas, (0.5, 1.0, 2.0))
        with self.assertRaises(ValueError):
            SamplerConfig(beta=2.0, parallel_tempering_betas=(2.0,))
        with self.assertRaises(ValueError):
            SamplerConfig(beta=2.0, parallel_tempering_betas=(0.5, 0.5, 2.0))
        with self.assertRaises(ValueError):
            SamplerConfig(beta=2.0, parallel_tempering_betas=(0.5, 1.0))
        with self.assertRaises(ValueError):
            SamplerConfig(
                beta=2.0,
                warmup_beta_ladder=(0.5, 2.0),
                parallel_tempering_betas=(0.5, 1.0, 2.0),
            )
        with self.assertRaises(ValueError):
            SamplerConfig(beta=2.0, parallel_tempering_betas=(0.5, 2.0), parallel_tempering_swap_interval=0)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class TwoSpinDistributionTests(unittest.TestCase):
    """Audits the Gibbsiq-to-THRML sign mapping against exact probabilities."""

    def test_two_spin_frequencies_match_boltzmann(self) -> None:
        beta = 1.2
        model = compile_ising({"a": 0.35, "b": -0.6}, {("a", "b"): 0.8})
        config = SamplerConfig(beta=beta, n_warmup=200, steps_per_sample=2, seed=7)
        result = THRMLSampler(config).sample(model, num_reads=DISTRIBUTION_READS)
        analytic = analytic_boltzmann(model, beta)
        empirical = empirical_frequencies(result)
        for state, probability in analytic.items():
            self.assertAlmostEqual(
                empirical.get(state, 0.0),
                probability,
                delta=DISTRIBUTION_TOLERANCE,
                msg=f"state={state}",
            )


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class ZeroCouplingMarginalTests(unittest.TestCase):
    """Isolated spins exercise the empty-edge lowering and the marginal sign."""

    def test_isolated_spin_marginals_match_conditionals(self) -> None:
        beta = 1.3
        model = compile_ising({"x": 0.7, "y": -0.4})
        config = SamplerConfig(beta=beta, n_warmup=100, seed=11)
        result = THRMLSampler(config).sample(model, num_reads=DISTRIBUTION_READS)
        reference = {"x": 1, "y": 1}
        for variable in model.variables:
            analytic_up = model.conditional_probability(variable, reference, beta=beta)
            empirical_up = sum(1 for sample in result.samples if sample[variable] == 1) / len(result.samples)
            self.assertAlmostEqual(empirical_up, analytic_up, delta=DISTRIBUTION_TOLERANCE, msg=variable)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class ReproducibilityTests(unittest.TestCase):
    def _model(self):
        return compile_ising(
            {i: 0.1 * i - 0.2 for i in range(6)},
            {(i, (i + 1) % 6): 0.5 for i in range(6)},
        )

    def test_fixed_seed_reproduces_samples_and_energies(self) -> None:
        config = SamplerConfig(beta=1.0, n_warmup=50, seed=123, num_chains=2)
        first = THRMLSampler(config).sample(self._model(), num_reads=40)
        second = THRMLSampler(config).sample(self._model(), num_reads=40)
        self.assertEqual(first.samples, second.samples)
        self.assertEqual(first.energies, second.energies)
        self.assertEqual(first.traces["energy"], second.traces["energy"])

    def test_different_seeds_differ(self) -> None:
        model = self._model()
        first = THRMLSampler(SamplerConfig(beta=1.0, n_warmup=50, seed=1)).sample(model, num_reads=50)
        second = THRMLSampler(SamplerConfig(beta=1.0, n_warmup=50, seed=2)).sample(model, num_reads=50)
        self.assertNotEqual(first.samples, second.samples)

    def test_parallel_tempering_fixed_seed_reproduces_samples_and_swaps(self) -> None:
        config = SamplerConfig(
            beta=2.0,
            n_warmup=8,
            steps_per_sample=1,
            seed=19,
            num_chains=2,
            init="random",
            parallel_tempering_betas=(0.5, 1.0, 2.0),
        )
        first = THRMLSampler(config).sample(self._model(), num_reads=8)
        second = THRMLSampler(config).sample(self._model(), num_reads=8)
        self.assertEqual(first.samples, second.samples)
        self.assertEqual(first.energies, second.energies)
        self.assertEqual(
            first.traces["parallel_tempering"]["swap_trace"],
            second.traces["parallel_tempering"]["swap_trace"],
        )


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class ParallelTemperingRuntimeTests(unittest.TestCase):
    def test_parallel_tempering_records_swap_and_per_beta_traces(self) -> None:
        model = compile_ising({"a": 0.2, "b": -0.1}, {("a", "b"): 0.7})
        config = SamplerConfig(
            beta=2.0,
            n_warmup=5,
            steps_per_sample=1,
            num_chains=2,
            seed=23,
            init="random",
            parallel_tempering_betas=(0.5, 2.0),
        )
        result = THRMLSampler(config).sample(model, num_reads=5)
        self.assertEqual(len(result.samples), 5)
        self.assertEqual([len(chain) for chain in result.traces["energy"]], [3, 2])
        self.assertTrue(result.metadata["parallel_tempering_enabled"])
        self.assertEqual(result.metadata["parallel_tempering_betas"], [0.5, 2.0])

        tempering = result.traces["parallel_tempering"]
        self.assertEqual(tempering["target_beta_index"], 1)
        self.assertEqual(tempering["swap_attempts"], 5)
        self.assertEqual(len(tempering["swap_trace"]), 5)
        self.assertEqual(len(tempering["per_beta_energy"]), 2)
        self.assertEqual([len(beta_trace) for beta_trace in tempering["per_beta_energy"][0]], [3, 3])
        self.assertEqual([len(beta_trace) for beta_trace in tempering["per_beta_energy"][1]], [2, 2])
        for event in tempering["swap_trace"]:
            self.assertEqual(event["right_beta_index"], event["left_beta_index"] + 1)
            expected_accept = (
                event["log_acceptance"] >= 0.0 or math.log(event["uniform"]) < event["log_acceptance"]
            )
            self.assertEqual(event["accepted"], expected_accept)
        for sample, energy in zip(result.samples, result.energies):
            self.assertAlmostEqual(model.energy(sample), energy, places=9)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class EnergyContractTests(unittest.TestCase):
    def test_offset_is_preserved_in_reported_energies(self) -> None:
        h = {"a": 0.3, "b": -0.7}
        J = {("a", "b"): 0.4}
        shift = 3.25
        config = SamplerConfig(beta=1.0, n_warmup=50, seed=5)
        base = THRMLSampler(config).sample(compile_ising(h, J), num_reads=30)
        shifted = THRMLSampler(config).sample(compile_ising(h, J, offset=shift), num_reads=30)
        self.assertEqual(base.samples, shifted.samples)
        for base_energy, shifted_energy in zip(base.energies, shifted.energies):
            self.assertAlmostEqual(shifted_energy - base_energy, shift, places=9)

    def test_energies_match_independent_recomputation(self) -> None:
        model = compile_ising({0: 0.2, 1: -0.4, 2: 0.6}, {(0, 1): -0.5, (1, 2): 0.3})
        result = THRMLSampler(SamplerConfig(beta=1.0, n_warmup=50, seed=9)).sample(model, num_reads=25)
        fresh = compile_ising({0: 0.2, 1: -0.4, 2: 0.6}, {(0, 1): -0.5, (1, 2): 0.3})
        for sample, energy in zip(result.samples, result.energies):
            self.assertAlmostEqual(energy, fresh.energy(sample), places=9)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class OptimizationTargetTests(unittest.TestCase):
    """Annealed warmup plus a cold sampling beta must find tiny proven optima."""

    def test_qubo_ground_state_found(self) -> None:
        config = SamplerConfig(
            beta=2.5,
            n_warmup=40,
            warmup_beta_ladder=(0.25, 0.5, 1.0, 2.0),
            num_chains=2,
            seed=21,
        )
        result = THRMLSampler(config).sample_qubo({(0, 0): -1.0, (1, 1): -1.0, (0, 1): 2.0}, num_reads=32)
        self.assertAlmostEqual(result.best_energy, -1.0, places=9)
        best = result.best_sample
        self.assertEqual({best[0], best[1]}, {-1, 1})

    def test_max_cut_four_cycle_ground_state_found(self) -> None:
        model = compile_ising(
            {i: 0.0 for i in range(4)},
            {(0, 1): 1.0, (1, 2): 1.0, (2, 3): 1.0, (0, 3): 1.0},
        )
        config = SamplerConfig(
            beta=3.0,
            n_warmup=60,
            warmup_beta_ladder=(0.2, 0.5, 1.0, 2.0),
            num_chains=2,
            seed=33,
        )
        result = THRMLSampler(config).sample(model, num_reads=32)
        self.assertAlmostEqual(result.best_energy, -4.0, places=9)
        best = result.best_sample
        self.assertEqual(best[0], -best[1])
        self.assertEqual(best[1], -best[2])
        self.assertEqual(best[2], -best[3])


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class ExhaustiveSmallInstanceTests(unittest.TestCase):
    """Roadmap exit criterion: empirical frequencies over the full state space
    of a dense random instance must match analytic Boltzmann probabilities."""

    def test_four_variable_distribution_matches_boltzmann(self) -> None:
        rng = random.Random(2)
        variables = tuple(f"q{i}" for i in range(4))
        h = {variable: rng.uniform(-1.0, 1.0) for variable in variables}
        J = {pair: rng.uniform(-1.0, 1.0) for pair in itertools.combinations(variables, 2)}
        model = compile_ising(h, J)
        beta = 0.8
        config = SamplerConfig(beta=beta, n_warmup=300, steps_per_sample=3, seed=17)
        result = THRMLSampler(config).sample(model, num_reads=12000)
        analytic = analytic_boltzmann(model, beta)
        empirical = empirical_frequencies(result)
        for state, probability in analytic.items():
            self.assertAlmostEqual(
                empirical.get(state, 0.0),
                probability,
                delta=0.03,
                msg=f"state={state}",
            )


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class FrustrationAndDegeneracyTests(unittest.TestCase):
    """The antiferromagnetic triangle is the smallest frustrated instance:
    six degenerate ground states at energy -1 that a healthy sampler visits."""

    def test_frustrated_triangle_finds_multiple_ground_states(self) -> None:
        model = compile_ising(
            {i: 0.0 for i in range(3)},
            {(0, 1): 1.0, (1, 2): 1.0, (0, 2): 1.0},
        )
        config = SamplerConfig(beta=1.5, n_warmup=40, warmup_beta_ladder=(0.3, 0.8), num_chains=2, seed=13)
        result = THRMLSampler(config).sample(model, num_reads=120)
        self.assertAlmostEqual(result.best_energy, -1.0, places=9)
        ground_states = {
            tuple(sample[variable] for variable in result.variables)
            for sample, energy in zip(result.samples, result.energies)
            if abs(energy - (-1.0)) < 1e-9
        }
        self.assertGreaterEqual(len(ground_states), 2)

    def test_sk_spin_glass_reaches_enumerated_optimum(self) -> None:
        rng = random.Random(41)
        variables = tuple(range(8))
        h = {variable: rng.gauss(0.0, 0.1) for variable in variables}
        J = {pair: rng.gauss(0.0, 1.0) for pair in itertools.combinations(variables, 2)}
        model = compile_ising(h, J)
        exact_optimum = min(
            model.energy(dict(zip(variables, state)))
            for state in itertools.product((-1, 1), repeat=len(variables))
        )
        config = SamplerConfig(
            beta=4.0,
            n_warmup=120,
            warmup_beta_ladder=(0.2, 0.5, 1.0, 2.0),
            num_chains=4,
            seed=29,
        )
        result = THRMLSampler(config).sample(model, num_reads=64)
        self.assertAlmostEqual(result.best_energy, exact_optimum, places=9)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class QuboEquivalenceTests(unittest.TestCase):
    def test_binary_decode_reproduces_reported_energies(self) -> None:
        qubo = {(0, 0): -1.0, (1, 1): -1.0, (0, 1): 2.0}
        result = THRMLSampler(SamplerConfig(beta=1.0, n_warmup=30, seed=3)).sample_qubo(qubo, num_reads=20)
        model = compile_qubo(qubo)
        for sample, energy in zip(result.samples, result.energies):
            binary = spin_to_binary(sample, result.variables)
            self.assertAlmostEqual(model.energy(binary, vartype="BINARY"), energy, places=9)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class ResultSchemaTests(unittest.TestCase):
    def _sample(self, num_reads: int = 7, num_chains: int = 3):
        model = compile_ising({"a": 0.1, "b": -0.1, "c": 0.0}, {("a", "b"): 0.2, ("b", "c"): -0.3})
        config = SamplerConfig(beta=1.0, n_warmup=30, num_chains=num_chains, seed=4)
        return THRMLSampler(config).sample(model, num_reads=num_reads)

    def test_num_reads_and_chain_traces_align(self) -> None:
        result = self._sample(num_reads=7, num_chains=3)
        self.assertEqual(len(result.samples), 7)
        self.assertEqual(result.traces["sample_chain_ids"], [0, 0, 0, 1, 1, 1, 2])
        self.assertEqual([len(chain) for chain in result.traces["energy"]], [3, 3, 1])
        flattened = [energy for chain in result.traces["energy"] for energy in chain]
        self.assertEqual(tuple(flattened), result.energies)
        for chain in result.traces["best_energy_so_far"]:
            for previous, current in zip(chain, chain[1:]):
                self.assertLessEqual(current, previous)

    def test_metadata_records_runtime_contract(self) -> None:
        result = self._sample()
        metadata = result.metadata
        for key in (
            "sampler",
            "thrml_version",
            "jax_version",
            "device_platform",
            "seed",
            "beta",
            "n_warmup",
            "steps_per_sample",
            "num_chains",
            "num_reads",
            "reads_per_chain",
            "init",
            "graph_density",
            "block_strategy",
            "num_blocks",
            "block_sizes",
            "energy_convention",
            "thrml_sign_mapping",
            "lower_seconds",
            "sample_seconds",
        ):
            self.assertIn(key, metadata, msg=key)
        self.assertEqual(metadata["num_reads"], 7)
        self.assertEqual(metadata["num_chains"], 3)
        self.assertEqual(metadata["sampler"], "gibbsiq.THRMLSampler")

    def test_beta_schedule_trace_present(self) -> None:
        result = self._sample()
        schedule = result.traces["beta_schedule"]
        self.assertEqual(schedule[-1]["phase"], "sampling")
        self.assertTrue(all(entry["phase"] == "warmup" for entry in schedule[:-1]))

    def test_invalid_partition_is_rejected(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): 1.0})
        sampler = THRMLSampler(SamplerConfig(n_warmup=5, seed=0))
        with self.assertRaises(ValueError):
            sampler.sample(model, num_reads=2, partition=BlockPartition(blocks=(("a", "b"),)))

    def test_rejects_bad_num_reads(self) -> None:
        model = compile_ising({"a": 0.0})
        sampler = THRMLSampler(SamplerConfig(n_warmup=5))
        with self.assertRaises(ValueError):
            sampler.sample(model, num_reads=0)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class DiagnosticsWiringTests(unittest.TestCase):
    """Stage 3: every sample() call embeds the full diagnostics payload."""

    def _sample(self, num_reads: int = 24, num_chains: int = 2):
        model = compile_ising({"a": 0.1, "b": -0.1, "c": 0.0}, {("a", "b"): 0.2, ("b", "c"): -0.3})
        config = SamplerConfig(beta=1.0, n_warmup=30, num_chains=num_chains, seed=4)
        return THRMLSampler(config).sample(model, num_reads=num_reads)

    def test_payload_sections_thresholds_and_timing_present(self) -> None:
        result = self._sample()
        diagnostics = result.diagnostics
        for key in ("energy", "diversity", "chains", "constraints", "runtime", "flags", "thresholds"):
            self.assertIn(key, diagnostics, msg=key)
        self.assertEqual(diagnostics["constraints"], {"status": "not_available"})
        runtime = diagnostics["runtime"]
        for key in (
            "lower_seconds",
            "sample_seconds",
            "device_platform",
            "device_kind",
            "reads_per_second",
            "diagnostics_seconds",
        ):
            self.assertIn(key, runtime, msg=key)
        self.assertGreaterEqual(runtime["diagnostics_seconds"], 0.0)
        self.assertEqual(result.metadata["diagnostics_seconds"], runtime["diagnostics_seconds"])

    def test_new_traces_shaped_like_energy_and_independently_recomputed(self) -> None:
        result = self._sample(num_reads=7, num_chains=3)
        magnetization = result.traces["magnetization"]
        distance = result.traces["distance_to_best"]
        shape = [len(chain) for chain in result.traces["energy"]]
        self.assertEqual([len(chain) for chain in magnetization], shape)
        self.assertEqual([len(chain) for chain in distance], shape)
        best = result.best_sample
        positions = {chain_index: 0 for chain_index in range(3)}
        for sample, chain_id in zip(result.samples, result.traces["sample_chain_ids"]):
            position = positions[chain_id]
            mean_spin = sum(sample[variable] for variable in result.variables) / len(result.variables)
            self.assertAlmostEqual(magnetization[chain_id][position], mean_spin, places=12)
            hamming = sum(1 for variable in result.variables if sample[variable] != best[variable])
            self.assertEqual(distance[chain_id][position], hamming)
            positions[chain_id] += 1

    def test_embedded_diagnostics_equal_recomputation_from_result(self) -> None:
        # The recomputation mirrors the runtime call exactly, including the
        # magnetization trace (EVAL-EQ-007 magnetization wiring): everything
        # the payload contains must be reproducible from the result alone.
        result = self._sample()
        recomputed = compute_diagnostics(
            energy_chains=result.traces["energy"],
            samples=list(result.samples),
            variables=result.variables,
            magnetization_chains=result.traces["magnetization"],
        )
        for section in ("energy", "diversity", "chains", "flags", "thresholds"):
            self.assertEqual(result.diagnostics[section], recomputed[section], msg=section)

    def test_single_read_with_many_chains_reports_insufficient_data(self) -> None:
        result = self._sample(num_reads=1, num_chains=4)
        chains = result.diagnostics["chains"]
        self.assertEqual(chains["num_chains"], 4)
        self.assertEqual(chains["num_chains_used"], 1)
        self.assertIn("insufficient_diagnostic_data", result.diagnostics["flags"])
        self.assertEqual([len(chain) for chain in result.traces["magnetization"]], [1, 0, 0, 0])

    def test_trapped_ferromagnet_flags_chain_disagreement(self) -> None:
        # Asymmetric two-well: the strong ferromagnetic ring locks each chain
        # into the all-up or all-down well; the small field separates the well
        # energies, so trapped chains disagree with zero within-chain variance
        # (seed 1 puts chains in both wells).
        model = compile_ising(
            {i: 0.05 for i in range(6)},
            {(i, (i + 1) % 6): -2.0 for i in range(6)},
        )
        config = SamplerConfig(beta=3.0, n_warmup=20, num_chains=4, init="random", seed=1)
        result = THRMLSampler(config).sample(model, num_reads=200)
        self.assertIn("chain_disagreement", result.diagnostics["flags"])
        self.assertEqual(
            result.diagnostics["chains"]["rhat_status"],
            "undefined_or_infinite_zero_within_variance",
        )

    def test_well_mixed_hot_run_has_no_disagreement_or_collapse(self) -> None:
        # low_diversity and no_recent_improvement fire legitimately on a small
        # stationary state space, so assert specific flags absent, never
        # flags == [].
        model = compile_ising({"a": 0.1, "b": -0.1}, {("a", "b"): 0.2})
        config = SamplerConfig(beta=0.5, n_warmup=100, steps_per_sample=2, num_chains=4, seed=0)
        result = THRMLSampler(config).sample(model, num_reads=400)
        flags = result.diagnostics["flags"]
        self.assertNotIn("chain_disagreement", flags)
        self.assertNotIn("mode_collapse", flags)
        chains = result.diagnostics["chains"]
        self.assertEqual(chains["rhat_status"], "ok")
        self.assertLess(chains["rhat"], 1.01)
        self.assertEqual(chains["ess_status"], "ok")
        self.assertGreater(chains["ess"], 400.0)


if __name__ == "__main__":
    unittest.main()
