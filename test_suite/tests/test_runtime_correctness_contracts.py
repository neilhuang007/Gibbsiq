"""Adversarial invariants for the THRML/replica-exchange runtime, independent of sampler quality."""

from __future__ import annotations

import math
import sys
import unittest
import warnings
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import SamplerConfig, color_blocks, compile_ising  # noqa: E402
from gibbsiq.thrml_runtime import (  # noqa: E402
    _Lowering,
    _advance_block_state,
    _reads_by_chain,
    _replica_exchange_log_ratio,
    _replica_exchange_pairs,
)

try:  # noqa: SIM105
    import jax.numpy as jnp  # noqa: E402
    import thrml  # noqa: F401, E402

    from gibbsiq import THRMLSampler  # noqa: E402

    THRML_AVAILABLE = True
except ImportError:
    THRML_AVAILABLE = False


# Distinguishes an actual Gibbs transition from merely recording the input state.
class _FakeSchedule:
    def __init__(self, *, n_warmup: int, n_samples: int, steps_per_sample: int):
        self.n_warmup = n_warmup
        self.n_samples = n_samples
        self.steps_per_sample = steps_per_sample


class _FakeThrml:
    SamplingSchedule = _FakeSchedule
    last_schedule: _FakeSchedule | None = None

    @classmethod
    def sample_states(
        cls,
        key: Any,
        program: Any,
        schedule: _FakeSchedule,
        state: list[list[bool]],
        clamped_states: list[Any],
        free_blocks: list[Any],
    ) -> list[list[list[bool]]]:
        del key, program, clamped_states, free_blocks
        cls.last_schedule = schedule
        initial = list(state[0])
        final = [not initial[0]] if schedule.n_warmup > 0 else initial
        return [[initial, final]]


class RuntimeMathContractTests(unittest.TestCase):
    def test_replica_exchange_log_ratio_sign(self) -> None:
        beta_hot, beta_cold = 0.5, 2.0
        low_energy, high_energy = -3.0, 1.0

        favorable = _replica_exchange_log_ratio(
            beta_hot,
            beta_cold,
            low_energy,
            high_energy,
        )
        unfavorable = _replica_exchange_log_ratio(
            beta_hot,
            beta_cold,
            high_energy,
            low_energy,
        )

        # Derived independently from log(pi_after / pi_before):
        # -beta_h*E_high - beta_c*E_low + beta_h*E_low + beta_c*E_high.
        expected = (
            -beta_hot * high_energy - beta_cold * low_energy + beta_hot * low_energy + beta_cold * high_energy
        )
        self.assertEqual(favorable, expected)
        self.assertGreater(favorable, 0.0)
        self.assertEqual(unfavorable, -expected)

    def test_replica_exchange_ratio_is_offset_invariant(self) -> None:
        baseline = _replica_exchange_log_ratio(0.25, 1.75, -2.5, 4.0)
        shift = 1024.0
        shifted = _replica_exchange_log_ratio(0.25, 1.75, -2.5 + shift, 4.0 + shift)
        self.assertEqual(shifted, baseline)

    def test_replica_exchange_pair_schedule_by_replica_count(self) -> None:
        expected_by_replica_count = {
            2: (
                ((0, 1),),
                ((0, 1),),
                ((0, 1),),
                ((0, 1),),
            ),
            3: (
                ((0, 1),),
                ((1, 2),),
                ((0, 1),),
                ((1, 2),),
            ),
            4: (
                ((0, 1), (2, 3)),
                ((1, 2),),
                ((0, 1), (2, 3)),
                ((1, 2),),
            ),
        }

        for replica_count, expected_rounds in expected_by_replica_count.items():
            for swap_round, expected_pairs in enumerate(expected_rounds):
                with self.subTest(replica_count=replica_count, swap_round=swap_round):
                    pairs = _replica_exchange_pairs(replica_count, swap_round)
                    self.assertEqual(pairs, expected_pairs)
                    flattened = [replica for pair in pairs for replica in pair]
                    self.assertEqual(len(flattened), len(set(flattened)))
                    self.assertTrue(
                        all(right == left + 1 for left, right in pairs),
                        msg=f"non-adjacent pair in {pairs!r}",
                    )

    def test_one_requested_sweep_executes_one_local_transition(self) -> None:
        final = _advance_block_state(
            thrml=_FakeThrml,
            key=object(),
            program=object(),
            state=[[False]],
            free_blocks=[object()],
            sweeps=1,
        )

        self.assertEqual(final, [[True]])
        schedule = _FakeThrml.last_schedule
        self.assertIsNotNone(schedule)
        assert schedule is not None
        self.assertEqual(schedule.n_warmup, 1)
        self.assertEqual(schedule.n_samples, 1)
        self.assertEqual(schedule.steps_per_sample, 1)

    def test_reads_are_balanced_across_chains(self) -> None:
        self.assertEqual(_reads_by_chain(7, 3), (3, 2, 2))
        self.assertEqual(_reads_by_chain(2, 4), (1, 1, 0, 0))
        for total in range(1, 20):
            for chains in range(1, 8):
                allocation = _reads_by_chain(total, chains)
                self.assertEqual(sum(allocation), total)
                self.assertLessEqual(max(allocation) - min(allocation), 1)


@unittest.skipUnless(THRML_AVAILABLE, "requires the optional 'thrml' package")
class RuntimeBackendContractTests(unittest.TestCase):
    def test_float32_rejects_unstable_accumulation(self) -> None:
        if str(jnp.asarray(1.0).dtype) != "float32":
            self.skipTest("active JAX backend has x64 enabled")

        magnitude = float(2**24)
        model = compile_ising(
            {"a": 0.0, "b": 0.0, "c": 0.0, "d": 0.0},
            {
                ("a", "b"): -magnitude,
                ("a", "c"): -1.0,
                ("a", "d"): magnitude,
            },
        )
        all_up = {variable: 1 for variable in model.variables}
        exact_local_field = model.local_field("a", all_up)
        backend_terms = jnp.asarray([0.0, -magnitude, -1.0, magnitude])
        backend_local_field = float(jnp.sum(backend_terms))

        # Every coefficient is exactly representable in float32, so the coefficient-delta
        # bound is zero; the reduction itself loses -1, turning sigmoid(2) into sigmoid(0).
        self.assertEqual(exact_local_field, -1.0)
        self.assertEqual(backend_local_field, 0.0)
        self.assertAlmostEqual(model.conditional_probability("a", all_up), 0.880797078, places=8)

        lowering = _Lowering(model, color_blocks(model))
        with self.assertRaisesRegex(
            ValueError,
            "JAX dtype|accumulation|local field|logit|rescale",
        ):
            lowering.program(1.0)

    def test_float32_lowering_rejects_local_field_cancellation(self) -> None:
        if str(jnp.asarray(1.0).dtype) != "float32":
            self.skipTest("active JAX backend has x64 enabled")

        magnitude = float(2**24)
        model = compile_ising(
            {"a": magnitude + 1.0, "b": -magnitude},
            {("a", "b"): -magnitude},
        )
        neighbor_up = {"a": -1, "b": 1}
        exact_local_field = model.local_field("a", neighbor_up)
        lowered_local_field = float(jnp.asarray(model.linear["a"])) + float(
            jnp.asarray(model.quadratic[("a", "b")])
        )

        # float32 cannot retain the +1 in 2**24 + 1: the exact Gibbs conditional is
        # sigmoid(-2), but the lowered one would be sigmoid(0), moving P(a=+1|b=+1)
        # from about 0.119 to 0.5.
        self.assertEqual(exact_local_field, 1.0)
        self.assertEqual(lowered_local_field, 0.0)
        self.assertAlmostEqual(model.conditional_probability("a", neighbor_up), 0.119202922, places=8)

        lowering = _Lowering(model, color_blocks(model))
        with self.assertRaisesRegex(ValueError, "JAX dtype|local field|cancellation|rescale"):
            lowering.program(1.0)

    def test_two_replicas_swap_same_pair_each_round(self) -> None:
        model = compile_ising({"a": 0.25}, offset=0.0)
        config = SamplerConfig(
            beta=2.0,
            n_warmup=1,
            steps_per_sample=1,
            num_chains=1,
            seed=17,
            init="random",
            parallel_tempering_betas=(0.5, 2.0),
        )

        result = THRMLSampler(config).sample(model, num_reads=6)
        tempering = result.traces["parallel_tempering"]

        self.assertEqual(tempering["swap_attempts"], 6)
        self.assertEqual(tempering["swap_attempts_by_pair"], {"0-1": 6})
        self.assertTrue(
            all(
                (event["left_beta_index"], event["right_beta_index"]) == (0, 1)
                for event in tempering["swap_trace"]
            )
        )

    def test_pt_log_densities_match_recorded_float32_target(self) -> None:
        if str(jnp.asarray(1.0).dtype) != "float32":
            self.skipTest("contract targets the default float32 JAX backend")

        model = compile_ising(
            {"a": 0.1, "b": -0.2, "c": 0.05},
            {("a", "b"): 0.3, ("b", "c"): -0.15},
        )
        config = SamplerConfig(
            beta=2.0,
            n_warmup=1,
            steps_per_sample=1,
            num_chains=1,
            seed=37,
            init="random",
            parallel_tempering_betas=(0.5, 1.0, 2.0),
        )
        result = THRMLSampler(config).sample(model, num_reads=6)
        targets = {float(target["requested_beta"]): target for target in result.metadata["lowered_targets"]}
        edge_order = [tuple(edge) for edge in result.metadata["lowered_edge_order"]]

        def reconstruct(target: Any, sample: Any) -> float:
            terms = [
                float(coefficient) * int(sample[variable])
                for variable, coefficient in zip(
                    result.variables,
                    target["effective_biases"],
                )
            ]
            terms.extend(
                float(coefficient) * int(sample[left]) * int(sample[right])
                for (left, right), coefficient in zip(
                    edge_order,
                    target["effective_weights"],
                )
            )
            return math.fsum(terms)

        exact_targets = []
        lowered_targets = []
        for beta, target in targets.items():
            exact_targets.extend(-beta * model.linear[variable] for variable in model.variables)
            exact_targets.extend(-beta * coefficient for coefficient in model.quadratic.values())
            lowered_targets.extend(float(value) for value in target["effective_biases"])
            lowered_targets.extend(float(value) for value in target["effective_weights"])
        self.assertTrue(
            any(exact != lowered for exact, lowered in zip(exact_targets, lowered_targets)),
            "fixture must contain at least one non-exact float32 target coefficient",
        )

        events = result.traces["parallel_tempering"]["swap_trace"]
        self.assertTrue(events)
        for event in events:
            with self.subTest(read_index=event["read_index"], pair=event["left_beta_index"]):
                left_target = targets[float(event["left_beta"])]
                right_target = targets[float(event["right_beta"])]
                left_sample = event["left_sample_before"]
                right_sample = event["right_sample_before"]
                left_left = reconstruct(left_target, left_sample)
                right_left = reconstruct(left_target, right_sample)
                left_right = reconstruct(right_target, left_sample)
                right_right = reconstruct(right_target, right_sample)

                self.assertEqual(event["left_log_density_left_target"], left_left)
                self.assertEqual(event["right_log_density_left_target"], right_left)
                self.assertEqual(event["left_log_density_right_target"], left_right)
                self.assertEqual(event["right_log_density_right_target"], right_right)
                expected_cross_ratio = math.fsum((right_left, left_right, -left_left, -right_right))
                self.assertEqual(event["log_acceptance"], expected_cross_ratio)
                self.assertEqual(event["acceptance_target"], "lowered_backend_coefficients")

    def test_parallel_tempering_decisions_ignore_large_common_offset(self) -> None:
        h = {"a": 0.3, "b": -0.4}
        J = {("a", "b"): 0.8}
        config = SamplerConfig(
            beta=2.0,
            n_warmup=3,
            steps_per_sample=1,
            num_chains=1,
            seed=29,
            init="random",
            parallel_tempering_betas=(0.5, 1.0, 2.0),
        )

        base = THRMLSampler(config).sample(compile_ising(h, J), num_reads=12)
        shifted = THRMLSampler(config).sample(
            compile_ising(h, J, offset=float(2**55)),
            num_reads=12,
        )
        base_events = base.traces["parallel_tempering"]["swap_trace"]
        shifted_events = shifted.traces["parallel_tempering"]["swap_trace"]

        self.assertTrue(any(abs(event["log_acceptance"]) > 1e-12 for event in base_events))
        self.assertEqual(base.samples, shifted.samples)
        self.assertEqual(
            [event["log_acceptance"] for event in base_events],
            [event["log_acceptance"] for event in shifted_events],
        )
        self.assertEqual(
            [event["accepted"] for event in base_events],
            [event["accepted"] for event in shifted_events],
        )
        interaction_model = compile_ising(h, J)
        interaction_energies = [interaction_model.interaction_energy(sample) for sample in base.samples]
        self.assertGreater(len(set(interaction_energies)), 1)
        expected_best = dict(
            base.samples[min(range(len(base.samples)), key=interaction_energies.__getitem__)]
        )
        self.assertEqual(base.best_sample, expected_best)
        self.assertEqual(shifted.best_sample, expected_best)

    def test_float32_backend_rejects_overflow_underflow(self) -> None:
        if str(jnp.asarray(1.0).dtype) != "float32":
            self.skipTest("active JAX backend has x64 enabled")

        sampler = THRMLSampler(SamplerConfig(n_warmup=0, seed=0))
        for coefficient in (1e40, 1e-45, 1e-50):
            with (
                self.subTest(coefficient=coefficient),
                self.assertRaisesRegex(
                    ValueError,
                    "JAX dtype|rescale",
                ),
            ):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    sampler.sample(compile_ising({"a": coefficient}), num_reads=1)


if __name__ == "__main__":
    unittest.main()
