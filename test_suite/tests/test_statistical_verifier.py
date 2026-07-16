"""Independent finite-kernel and empirical-law verification contracts."""

from __future__ import annotations

import itertools
import json
import math
import sys
import unittest
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.reference_sampler import (  # noqa: E402
    ReferenceGibbsSampler,
    ReferenceSamplerConfig,
)
from gibbsiq.verification import (  # noqa: E402
    ExactTransitionKernel,
    build_exact_transition_kernel,
    verify_empirical_distribution,
    verify_transition_kernel,
    verify_transition_matrix,
)


def direct_probabilities(model, beta):
    states = tuple(itertools.product((-1, 1), repeat=len(model.variables)))
    log_weights = []
    for state in states:
        sample = dict(zip(model.variables, state))
        log_weights.append(-beta * model.interaction_energy(sample))
    shift = max(log_weights)
    weights = [math.exp(value - shift) for value in log_weights]
    normalization = math.fsum(weights)
    return states, tuple(weight / normalization for weight in weights)


def direct_single_site_probability(model, variable_position, state, beta):
    variable = model.variables[variable_position]
    gamma = model.linear[variable]
    for (left, right), coefficient in model.quadratic.items():
        if left == variable:
            gamma += coefficient * state[model.variables.index(right)]
        elif right == variable:
            gamma += coefficient * state[model.variables.index(left)]
    return 1.0 / (1.0 + math.exp(2.0 * beta * gamma))


class ExactKernelConstructionTests(unittest.TestCase):
    def test_one_spin_random_kernel_matches_hand_conditional(self) -> None:
        model = compile_ising({"s": 0.75}, offset=1000.0)
        kernel = build_exact_transition_kernel(
            model,
            beta=1.5,
            update_schedule="random_single_site",
        )
        probability_up = 1.0 / (1.0 + math.exp(2.0 * 1.5 * 0.75))
        expected_row = (1.0 - probability_up, probability_up)
        self.assertEqual(kernel.states, ((-1,), (1,)))
        for row in kernel.matrix:
            self.assertAlmostEqual(row[0], expected_row[0], places=15)
            self.assertAlmostEqual(row[1], expected_row[1], places=15)
        self.assertTrue(kernel.detailed_balance_expected)

    def test_two_spin_random_kernel_matches_direct_single_site_mixture(self) -> None:
        model = compile_ising(
            {"a": 0.2, "b": -0.4},
            {("a", "b"): 0.7},
            variables=("a", "b"),
        )
        beta = 1.1
        kernel = build_exact_transition_kernel(model, beta, update_schedule="random_single_site")
        index = {state: position for position, state in enumerate(kernel.states)}
        expected = [[0.0] * 4 for _ in range(4)]
        for row_index, state in enumerate(kernel.states):
            for variable_position in range(2):
                probability_up = direct_single_site_probability(model, variable_position, state, beta)
                for spin, probability in ((-1, 1.0 - probability_up), (1, probability_up)):
                    destination = list(state)
                    destination[variable_position] = spin
                    expected[row_index][index[tuple(destination)]] += 0.5 * probability
        for actual_row, expected_row in zip(kernel.matrix, expected):
            for actual, target in zip(actual_row, expected_row):
                self.assertAlmostEqual(actual, target, places=15)

    def test_systematic_scan_is_stationary_without_claiming_reversibility(self) -> None:
        model = compile_ising(
            {"a": 0.4, "b": -0.25},
            {("a", "b"): 0.9},
        )
        kernel = build_exact_transition_kernel(model, 1.3, update_schedule="systematic")
        report = verify_transition_kernel(model, 1.3, kernel)
        self.assertTrue(report.row_stochastic_passed)
        self.assertTrue(report.stationarity_passed)
        self.assertTrue(report.ergodic)
        self.assertFalse(kernel.detailed_balance_expected)
        self.assertEqual(report.detailed_balance_status, "not_required_non_reversible_schedule")
        self.assertGreater(report.detailed_balance_residual, 1e-6)
        self.assertTrue(report.passed)

    def test_legal_single_independent_block_is_reversible_full_refresh(self) -> None:
        model = compile_ising({"a": 0.3, "b": -0.6}, variables=("a", "b"))
        kernel = build_exact_transition_kernel(
            model,
            0.8,
            update_schedule="blocked",
            blocks=(("a", "b"),),
        )
        _, target = direct_probabilities(model, 0.8)
        for row in kernel.matrix:
            for actual, expected in zip(row, target):
                self.assertAlmostEqual(actual, expected, places=15)
        report = verify_transition_kernel(model, 0.8, kernel)
        self.assertTrue(kernel.detailed_balance_expected)
        self.assertTrue(report.detailed_balance_passed)
        self.assertTrue(report.passed)

    def test_interacting_block_and_state_cap_fail_before_allocation(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): 1.0})
        with self.assertRaisesRegex(ValueError, "interacting|independent"):
            build_exact_transition_kernel(
                model,
                1.0,
                update_schedule="blocked",
                blocks=(("a", "b"),),
            )
        large = compile_ising({position: 0.0 for position in range(9)})
        with self.assertRaisesRegex(ValueError, "max_variables"):
            build_exact_transition_kernel(large, 1.0, max_variables=8)

    def test_zero_variable_kernel_is_one_by_one_identity(self) -> None:
        model = compile_ising({}, offset=4.0)
        for schedule in ("random_single_site", "systematic", "blocked"):
            with self.subTest(schedule=schedule):
                kernel = build_exact_transition_kernel(model, 3.0, update_schedule=schedule)
                self.assertEqual(kernel.states, ((),))
                self.assertEqual(kernel.matrix, ((1.0,),))
                self.assertTrue(verify_transition_kernel(model, 3.0, kernel).passed)


class KernelVerificationTrapTests(unittest.TestCase):
    def test_wrong_sign_kernel_fails_stationarity(self) -> None:
        model = compile_ising({"s": 1.0})
        beta = 1.0
        wrong_probability_up = 1.0 / (1.0 + math.exp(-2.0 * beta))
        wrong = (
            (1.0 - wrong_probability_up, wrong_probability_up),
            (1.0 - wrong_probability_up, wrong_probability_up),
        )
        report = verify_transition_matrix(
            model,
            beta,
            wrong,
            detailed_balance_expected=True,
        )
        self.assertTrue(report.row_stochastic_passed)
        self.assertFalse(report.stationarity_passed)
        self.assertFalse(report.detailed_balance_passed)
        self.assertFalse(report.passed)

    def test_identity_kernel_fails_ergodicity_even_though_balance_passes(self) -> None:
        model = compile_ising({"s": 0.5})
        report = verify_transition_matrix(
            model,
            1.0,
            ((1.0, 0.0), (0.0, 1.0)),
            detailed_balance_expected=True,
        )
        self.assertTrue(report.row_stochastic_passed)
        self.assertTrue(report.stationarity_passed)
        self.assertTrue(report.detailed_balance_passed)
        self.assertFalse(report.irreducible)
        self.assertFalse(report.ergodic)
        self.assertFalse(report.passed)

    def test_subtle_nonstochastic_row_is_detected_at_declared_tolerance(self) -> None:
        model = compile_ising({"s": 0.0})
        matrix = ((0.5, 0.50000000001), (0.5, 0.5))
        report = verify_transition_matrix(model, 0.0, matrix, tolerance=1e-12)
        self.assertFalse(report.row_stochastic_passed)
        self.assertGreater(report.row_residual, 1e-12)
        self.assertFalse(report.passed)

    def test_permutation_similar_kernel_verifies_in_declared_state_order(self) -> None:
        model = compile_ising({"a": 0.2, "b": -0.1}, {("a", "b"): 0.4})
        kernel = build_exact_transition_kernel(model, 0.7)
        permutation = (2, 0, 3, 1)
        states = tuple(kernel.states[index] for index in permutation)
        matrix = tuple(
            tuple(kernel.matrix[source][target] for target in permutation) for source in permutation
        )
        report = verify_transition_matrix(
            model,
            0.7,
            matrix,
            states=states,
            detailed_balance_expected=True,
        )
        self.assertTrue(report.passed)

    def test_kernel_model_order_or_beta_mismatch_fails_closed(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, variables=("a", "b"))
        reversed_model = compile_ising({"a": 0.0, "b": 0.0}, variables=("b", "a"))
        kernel = build_exact_transition_kernel(model, 1.0)
        with self.assertRaisesRegex(ValueError, "variable order"):
            verify_transition_kernel(reversed_model, 1.0, kernel)
        with self.assertRaisesRegex(ValueError, "beta"):
            verify_transition_kernel(model, 2.0, kernel)

        integer_model = compile_ising({1: 0.0}, variables=(1,))
        boolean_kernel = build_exact_transition_kernel(
            compile_ising({True: 0.0}, variables=(True,)),
            1.0,
        )
        with self.assertRaisesRegex(ValueError, "variable order"):
            verify_transition_kernel(integer_model, 1.0, boolean_kernel)

    def test_forged_reversibility_flag_cannot_bypass_schedule_contract(self) -> None:
        model = compile_ising({"s": 0.5})
        kernel = build_exact_transition_kernel(model, 1.0)
        forged = replace(kernel, detailed_balance_expected=False)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            verify_transition_kernel(model, 1.0, forged)

    def test_nonfinite_and_wrong_shape_matrices_fail_closed(self) -> None:
        model = compile_ising({"s": 0.0})
        bad_matrices = (
            ((1.0, 0.0),),
            ((1.0, 0.0), (float("nan"), 1.0)),
        )
        for matrix in bad_matrices:
            with self.subTest(matrix=matrix), self.assertRaises(ValueError):
                verify_transition_matrix(model, 1.0, matrix)

    def test_state_entries_and_reversibility_claim_are_strictly_typed(self) -> None:
        model = compile_ising({"s": 0.0})
        identity = ((1.0, 0.0), (0.0, 1.0))
        for states in (((-1.0,), (1.0,)), ((-1,), (True,))):
            with self.subTest(states=states), self.assertRaisesRegex(ValueError, "plain int"):
                verify_transition_matrix(model, 1.0, identity, states=states)
        with self.assertRaisesRegex(ValueError, "must be bool"):
            verify_transition_matrix(
                model,
                1.0,
                identity,
                detailed_balance_expected=1,
            )


class EmpiricalVerificationTests(unittest.TestCase):
    def test_seeded_independent_restarts_from_reference_sampler_cover_exact_law(self) -> None:
        """Exercise real draws, with one retained state per independent RNG chain."""
        model = compile_ising({"s": 0.35}, offset=11.0)
        sample_count = 2000
        result = ReferenceGibbsSampler(
            ReferenceSamplerConfig(
                beta=0.8,
                n_warmup=0,
                steps_per_sample=1,
                num_chains=sample_count,
                seed=20260715,
                initialization="all_up",
                update_schedule="systematic",
            )
        ).sample(model, num_reads=sample_count)
        samples = [dict(zip(model.variables, state)) for state in result.samples]

        report = verify_empirical_distribution(
            model,
            samples,
            beta=0.8,
            familywise_confidence=0.99,
            sampling_design="independent_chains",
        )

        self.assertTrue(report.passed)
        self.assertEqual(result.chain_ids, tuple(range(sample_count)))
        self.assertEqual(len(set(result.metadata["chain_seeds"])), sample_count)
        self.assertEqual(result.metadata["conditional_evaluations"], sample_count)
        self.assertTrue(all(len(trace) == 2 for trace in result.state_traces))
        self.assertEqual(report.intervals[0].observable, "probability_up:0")
        self.assertTrue(all(0.0 <= interval.lower <= interval.upper <= 1.0 for interval in report.intervals))

    def test_predeclared_simultaneous_intervals_cover_exactly_allocated_law(self) -> None:
        model = compile_ising(
            {"a": 0.3, "b": -0.2},
            {("a", "b"): 0.5},
            offset=7.0,
        )
        states, probabilities = direct_probabilities(model, 0.9)
        sample_count = 4000
        counts = [round(probability * sample_count) for probability in probabilities]
        counts[-1] += sample_count - sum(counts)
        samples = [
            dict(zip(model.variables, state)) for state, count in zip(states, counts) for _ in range(count)
        ]

        report = verify_empirical_distribution(
            model,
            samples,
            beta=0.9,
            familywise_confidence=0.99,
            sampling_design="independent_chains",
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.interval_method, "bonferroni_hoeffding")
        self.assertEqual(report.sample_count, sample_count)
        self.assertEqual(
            report.num_comparisons,
            2 + 1 + len({model.energy(dict(zip(model.variables, state))) for state in states}) + len(states),
        )
        self.assertEqual(report.independence_assumption_status, "caller_asserted_unverified")
        self.assertFalse(report.independence_verified)
        self.assertTrue(all(interval.covered for interval in report.intervals))
        json.dumps(report.to_dict(), allow_nan=False)

    def test_even_parity_law_fails_full_state_probability_checks(self) -> None:
        """First/second moments and energy levels do not identify a joint law."""
        model = compile_ising({"a": 0.0, "b": 0.0, "c": 0.0})
        even_parity_states = (
            {"a": -1, "b": -1, "c": 1},
            {"a": -1, "b": 1, "c": -1},
            {"a": 1, "b": -1, "c": -1},
            {"a": 1, "b": 1, "c": 1},
        )
        samples = [dict(even_parity_states[index % 4]) for index in range(10_000)]

        report = verify_empirical_distribution(
            model,
            samples,
            beta=1.0,
            familywise_confidence=0.99,
            sampling_design="independent_chains",
        )

        self.assertFalse(report.passed)
        failed_state_intervals = [
            interval
            for interval in report.failed_intervals
            if interval.observable.startswith("state_probability:")
        ]
        self.assertEqual(len(failed_state_intervals), 8)
        self.assertTrue(
            all(
                interval.covered
                for interval in report.intervals
                if not interval.observable.startswith("state_probability:")
            )
        )

    def test_bad_empirical_law_fails_multiple_intervals(self) -> None:
        model = compile_ising({"s": 1.0}, offset=2.0)
        samples = [{"s": 1} for _ in range(2000)]
        report = verify_empirical_distribution(
            model,
            samples,
            beta=1.0,
            familywise_confidence=0.99,
            sampling_design="independent_chains",
        )
        self.assertFalse(report.passed)
        self.assertGreaterEqual(len(report.failed_intervals), 2)
        self.assertTrue(all(0.0 <= interval.lower <= interval.upper <= 1.0 for interval in report.intervals))

    def test_correlated_chain_design_is_rejected_for_independence_interval(self) -> None:
        model = compile_ising({"s": 0.0})
        with self.assertRaisesRegex(ValueError, "independent"):
            verify_empirical_distribution(
                model,
                [{"s": -1}, {"s": 1}],
                beta=0.0,
                sampling_design="single_correlated_chain",
            )

    def test_invalid_confidence_samples_and_cap_fail_closed(self) -> None:
        model = compile_ising({"s": 0.0})
        for confidence in (0.0, 1.0, float("nan"), True):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                verify_empirical_distribution(
                    model,
                    [{"s": 1}],
                    beta=1.0,
                    familywise_confidence=confidence,
                )
        with self.assertRaisesRegex(ValueError, "at least one"):
            verify_empirical_distribution(model, [], beta=1.0)
        large = compile_ising({position: 0.0 for position in range(9)})
        with self.assertRaisesRegex(ValueError, "max_variables"):
            verify_empirical_distribution(
                large,
                [{position: 1 for position in range(9)}],
                beta=1.0,
                max_variables=8,
            )

    def test_transition_payload_is_json_finite(self) -> None:
        model = compile_ising({"s": 0.25})
        kernel = build_exact_transition_kernel(model, 1.0)
        report = verify_transition_kernel(model, 1.0, kernel)
        json.dumps(kernel.to_dict(), allow_nan=False)
        json.dumps(report.to_dict(), allow_nan=False)
        self.assertIsInstance(kernel, ExactTransitionKernel)


if __name__ == "__main__":
    unittest.main()
