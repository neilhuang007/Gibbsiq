"""Falsifying contracts for the THRML-independent CPU Gibbs reference."""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.reference_sampler import (  # noqa: E402
    ReferenceGibbsSampler,
    ReferenceSamplerConfig,
)


def direct_probability_up(model, variable, state, beta):
    gamma = model.linear[variable]
    for (left, right), coefficient in model.quadratic.items():
        if left == variable:
            gamma += coefficient * state[model.variables.index(right)]
        elif right == variable:
            gamma += coefficient * state[model.variables.index(left)]
    return 1.0 / (1.0 + math.exp(2.0 * beta * gamma))


class ReferenceConditionalTests(unittest.TestCase):
    def test_one_spin_uses_audited_negative_logit_sign(self) -> None:
        model = compile_ising({"s": 0.75}, offset=13.0)
        config = ReferenceSamplerConfig(
            beta=1.5,
            n_warmup=0,
            steps_per_sample=1,
            seed=17,
            initialization="all_up",
            update_schedule="systematic",
        )

        result = ReferenceGibbsSampler(config).sample(model, num_reads=1)

        self.assertEqual(len(result.transitions), 1)
        event = result.transitions[0]
        expected = 1.0 / (1.0 + math.exp(2.0 * 1.5 * 0.75))
        self.assertAlmostEqual(event.probability_up, expected, places=15)
        self.assertEqual(event.state_before, (1,))
        self.assertIn(event.state_after, ((-1,), (1,)))
        self.assertEqual(result.energies[0], model.energy(dict(zip(model.variables, result.samples[0]))))

    def test_two_spin_conditionals_are_recomputed_after_each_update(self) -> None:
        model = compile_ising(
            {"a": 0.3, "b": -0.2},
            {("a", "b"): 0.8},
            variables=("a", "b"),
        )
        config = ReferenceSamplerConfig(
            beta=1.25,
            n_warmup=0,
            steps_per_sample=1,
            seed=23,
            initialization="all_down",
            update_schedule="systematic",
        )

        result = ReferenceGibbsSampler(config).sample(model, num_reads=1)

        self.assertEqual([event.variable for event in result.transitions], ["a", "b"])
        for event in result.transitions:
            expected = direct_probability_up(model, event.variable, event.state_before, 1.25)
            self.assertAlmostEqual(event.probability_up, expected, places=15)
        self.assertEqual(result.transitions[1].state_before, result.transitions[0].state_after)

    def test_legal_independent_block_conditions_on_one_phase_start_state(self) -> None:
        model = compile_ising(
            {"left": 0.2, "middle": -0.1, "right": 0.4},
            {("left", "middle"): 0.7, ("middle", "right"): -0.5},
            variables=("left", "middle", "right"),
        )
        config = ReferenceSamplerConfig(
            beta=0.9,
            seed=31,
            initialization="all_up",
            update_schedule="blocked",
            blocks=(("left", "right"), ("middle",)),
        )

        result = ReferenceGibbsSampler(config).sample(model, num_reads=1)

        first_phase = [event for event in result.transitions if event.phase_index == 0]
        self.assertEqual([event.variable for event in first_phase], ["left", "right"])
        self.assertEqual({event.conditioned_state for event in first_phase}, {(1, 1, 1)})
        for event in first_phase:
            expected = direct_probability_up(model, event.variable, event.conditioned_state, 0.9)
            self.assertAlmostEqual(event.probability_up, expected, places=15)

    def test_interacting_variables_in_one_block_fail_closed(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): 1.0})
        config = ReferenceSamplerConfig(
            update_schedule="blocked",
            blocks=(("a", "b"),),
        )
        with self.assertRaisesRegex(ValueError, "interacting|independent"):
            ReferenceGibbsSampler(config).sample(model, num_reads=1)


class ReferenceReplayAndAccountingTests(unittest.TestCase):
    def test_same_seed_replays_every_raw_trace_value(self) -> None:
        model = compile_ising(
            {"a": 0.4, "b": -0.3},
            {("a", "b"): 0.6},
            offset=5.25,
        )
        config = ReferenceSamplerConfig(
            beta=1.1,
            n_warmup=3,
            steps_per_sample=2,
            num_chains=2,
            seed=8128,
            initialization="random",
            update_schedule="random_single_site",
        )

        first = ReferenceGibbsSampler(config).sample(model, num_reads=5)
        second = ReferenceGibbsSampler(config).sample(model, num_reads=5)

        self.assertEqual(first, second)
        self.assertEqual(first.chain_ids, (0, 0, 0, 1, 1))
        self.assertEqual(first.metadata["rng"], "random.Random (MT19937)")
        self.assertEqual(first.metadata["seed"], 8128)
        self.assertEqual(first.metadata["work_unit"], "single_site_conditional_evaluation")
        self.assertEqual(first.metadata["conditional_evaluations"], 16)

    def test_offset_shift_preserves_states_and_moves_total_energy_trace(self) -> None:
        config = ReferenceSamplerConfig(
            beta=0.8,
            n_warmup=2,
            steps_per_sample=2,
            seed=47,
            update_schedule="systematic",
        )
        base_model = compile_ising({"a": 0.2, "b": -0.4}, {("a", "b"): 0.7})
        shifted_model = compile_ising(
            {"a": 0.2, "b": -0.4},
            {("a", "b"): 0.7},
            offset=123.5,
        )

        base = ReferenceGibbsSampler(config).sample(base_model, num_reads=8)
        shifted = ReferenceGibbsSampler(config).sample(shifted_model, num_reads=8)

        self.assertEqual(base.samples, shifted.samples)
        self.assertEqual(base.interaction_energies, shifted.interaction_energies)
        self.assertEqual(
            shifted.energies,
            tuple(energy + 123.5 for energy in base.energies),
        )

    def test_beta_zero_is_uniform_at_each_one_spin_refresh(self) -> None:
        model = compile_ising({"isolated": 1e200}, offset=-9.0)
        result = ReferenceGibbsSampler(
            ReferenceSamplerConfig(
                beta=0.0,
                n_warmup=2,
                steps_per_sample=1,
                seed=5,
                update_schedule="systematic",
            )
        ).sample(model, num_reads=4)
        self.assertTrue(all(event.probability_up == 0.5 for event in result.transitions))

    def test_zero_variable_model_retains_the_only_state_without_rng_updates(self) -> None:
        model = compile_ising({}, offset=-3.5)
        result = ReferenceGibbsSampler(
            ReferenceSamplerConfig(n_warmup=4, steps_per_sample=3, num_chains=2, seed=1)
        ).sample(model, num_reads=3)
        self.assertEqual(result.samples, ((), (), ()))
        self.assertEqual(result.energies, (-3.5, -3.5, -3.5))
        self.assertEqual(result.interaction_energies, (0.0, 0.0, 0.0))
        self.assertEqual(result.transitions, ())
        self.assertEqual(result.metadata["conditional_evaluations"], 0)

    def test_result_is_json_finite_and_keeps_full_raw_state_trace(self) -> None:
        model = compile_ising({"s": 0.25})
        result = ReferenceGibbsSampler(ReferenceSamplerConfig(n_warmup=2, steps_per_sample=2, seed=9)).sample(
            model, num_reads=3
        )
        payload = result.to_dict()
        json.dumps(payload, allow_nan=False)
        self.assertEqual(len(payload["state_traces"][0]), 1 + 2 + 2 * 3)
        self.assertEqual(payload["samples"], [list(sample) for sample in result.samples])
        with self.assertRaises(TypeError):
            result.metadata["seed"] = 10
        with self.assertRaises(TypeError):
            result.metadata["chain_seeds"][0] = 10

    def test_configuration_rejects_ambiguous_or_nonfinite_controls(self) -> None:
        invalid = (
            {"beta": -1.0},
            {"beta": float("nan")},
            {"n_warmup": -1},
            {"steps_per_sample": 0},
            {"num_chains": 0},
            {"seed": True},
            {"update_schedule": "unknown"},
            {"initialization": "unknown"},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises((TypeError, ValueError)):
                ReferenceSamplerConfig(**values)


if __name__ == "__main__":
    unittest.main()
