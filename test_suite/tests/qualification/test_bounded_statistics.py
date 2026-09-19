from __future__ import annotations

import math
import random
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from gibbsiq.qualification.contracts import (  # noqa: E402
    Acceptance,
    AcceptanceContract,
    Bounds,
    MetricSpec,
)
from gibbsiq.qualification.statistics import (  # noqa: E402
    evaluate_metric,
    evaluate_metrics,
    paired_difference_bounds,
    required_units,
)


def bounded_metric(
    metric_id: str = "signed-error",
    *,
    planned_units: int = 64,
    bounds: Bounds | None = None,
    acceptance: Acceptance | None = None,
    mandatory: bool = True,
) -> MetricSpec:
    return MetricSpec(
        metric_id=metric_id,
        units="signed error",
        direction="target",
        comparison="candidate-reference",
        acceptance=acceptance or Acceptance("equivalence", upper=0.1, lower=-0.1),
        evidence_mode="bounded_fixed_n",
        planned_units=planned_units,
        replication_unit="independent_draw",
        scope="fixed_inputs",
        bounds=bounds or Bounds(-1.5, 0.5),
        mandatory=mandatory,
    )


def exact_metric(
    metric_id: str,
    *,
    direction: str,
    acceptance: Acceptance,
    mandatory: bool = True,
) -> MetricSpec:
    return MetricSpec(
        metric_id=metric_id,
        units="error",
        direction=direction,
        comparison="candidate-reference",
        acceptance=acceptance,
        evidence_mode="exact",
        planned_units=1,
        replication_unit="deterministic",
        scope="fixed_inputs",
        mandatory=mandatory,
    )


class HoeffdingPlanningTests(unittest.TestCase):
    def test_required_units_matches_hand_derived_width_one_fixture(self) -> None:
        self.assertEqual(required_units(Bounds(0, 1), alpha=0.05, half_width=0.05), 738)

    def test_constant_bounds_need_one_unit(self) -> None:
        self.assertEqual(required_units(Bounds(3, 3), alpha=0.05, half_width=1e-300), 1)

    def test_extreme_positive_alpha_remains_numerically_valid(self) -> None:
        self.assertEqual(required_units(Bounds(0, 1), alpha=5e-324, half_width=0.1), 37257)

    def test_large_width_ratio_is_formed_before_squaring(self) -> None:
        self.assertEqual(required_units(Bounds(0, 1e200), alpha=0.05, half_width=1e200), 2)

    def test_invalid_alpha_and_half_width_fail_closed(self) -> None:
        for alpha in (0.0, 1.0, -0.1, True, "0.05", math.nan, math.inf):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                required_units(Bounds(0, 1), alpha=alpha, half_width=0.1)  # type: ignore[arg-type]
        for half_width in (0.0, -0.1, True, "0.1", math.nan, math.inf):
            with self.subTest(half_width=half_width), self.assertRaises(ValueError):
                required_units(Bounds(0, 1), alpha=0.05, half_width=half_width)  # type: ignore[arg-type]

    def test_unrepresentable_sample_size_fails_as_invalid_numeric_request(self) -> None:
        with self.assertRaises(ValueError):
            required_units(Bounds(0, 1), alpha=0.05, half_width=1e-300)


class PairedDifferenceBoundsTests(unittest.TestCase):
    def test_component_ranges_are_combined_for_paired_difference(self) -> None:
        result = paired_difference_bounds(Bounds(-1, 2), Bounds(10, 14))
        self.assertEqual(result, Bounds(-15, -8))
        self.assertEqual(result.upper - result.lower, 7.0)

    def test_constant_components_produce_constant_difference(self) -> None:
        self.assertEqual(paired_difference_bounds(Bounds(2, 2), Bounds(-3, -3)), Bounds(5, 5))

    def test_nonfinite_derived_range_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            paired_difference_bounds(Bounds(0, 1e308), Bounds(-1e308, 0))


class ExactMetricDecisionTests(unittest.TestCase):
    def test_inclusive_acceptance_boundaries_pass_for_every_direction(self) -> None:
        cases = (
            (
                exact_metric(
                    "upper",
                    direction="smaller_is_better",
                    acceptance=Acceptance("upper", upper=0.1),
                ),
                0.1,
            ),
            (
                exact_metric(
                    "lower",
                    direction="larger_is_better",
                    acceptance=Acceptance("lower", upper=None, lower=-0.1),
                ),
                -0.1,
            ),
            (
                exact_metric(
                    "target",
                    direction="target",
                    acceptance=Acceptance("equivalence", upper=0.1, lower=-0.1),
                ),
                -0.1,
            ),
        )
        for spec, value in cases:
            with self.subTest(metric_id=spec.metric_id):
                result = evaluate_metric(spec, (value,))
                self.assertEqual(result.outcome, "pass")
                self.assertEqual(result.interval, Bounds(value, value))
                self.assertEqual(result.procedure, "exact-v1")
                self.assertIsNone(result.alpha)
                self.assertEqual(result.unit_summaries, (value,))

    def test_exact_value_strictly_outside_acceptance_fails(self) -> None:
        spec = exact_metric(
            "upper",
            direction="smaller_is_better",
            acceptance=Acceptance("upper", upper=0.1),
        )
        result = evaluate_metric(spec, (0.10000000000000002,))
        self.assertEqual(result.outcome, "fail")

    def test_exact_value_outside_an_optional_declared_range_is_invalid(self) -> None:
        spec = MetricSpec(
            metric_id="bounded-exact",
            units="error",
            direction="smaller_is_better",
            comparison="candidate-reference",
            acceptance=Acceptance("upper", upper=10.0),
            evidence_mode="exact",
            planned_units=1,
            replication_unit="deterministic",
            scope="fixed_inputs",
            bounds=Bounds(-1.0, 1.0),
        )

        with self.assertRaises(ValueError):
            evaluate_metric(spec, (2.0,))

    def test_zero_or_extra_exact_units_do_not_create_a_false_pass(self) -> None:
        spec = exact_metric(
            "upper",
            direction="smaller_is_better",
            acceptance=Acceptance("upper", upper=0.1),
        )

        missing = evaluate_metric(spec, ())
        self.assertEqual(missing.availability, "unavailable")
        self.assertIsNotNone(missing.reason)
        self.assertIsNone(missing.outcome)
        with self.assertRaises(ValueError):
            evaluate_metric(spec, (0.0, 0.0))


class BoundedMetricDecisionTests(unittest.TestCase):
    def test_complete_4096_unit_fixture_passes_with_independent_interval_literal(self) -> None:
        spec = bounded_metric(planned_units=4096)
        values = (0.5,) * 3072 + (-1.5,) * 1024

        result = evaluate_metric(spec, values, alpha=0.05)

        self.assertEqual(result.availability, "available")
        self.assertEqual(result.estimate, 0.0)
        self.assertAlmostEqual(result.interval.lower, -0.04244067236689436, places=15)
        self.assertAlmostEqual(result.interval.upper, 0.04244067236689436, places=15)
        self.assertEqual(result.outcome, "pass")
        self.assertEqual(result.procedure, "bounded-hoeffding-v1")
        self.assertEqual(result.observed_units, 4096)
        self.assertEqual(result.unit_summaries[:2], (0.5, 0.5))
        self.assertEqual(result.unit_summaries[-2:], (-1.5, -1.5))

    def test_precise_biased_fixture_fails_instead_of_becoming_good_precision(self) -> None:
        spec = bounded_metric(planned_units=4096)
        values = (0.5,) * 1024 + (-1.5,) * 3072

        result = evaluate_metric(spec, values, alpha=0.05)

        self.assertEqual(result.estimate, -1.0)
        self.assertAlmostEqual(result.interval.lower, -1.0424406723668944, places=15)
        self.assertAlmostEqual(result.interval.upper, -0.9575593276331057, places=15)
        self.assertEqual(result.outcome, "fail")

    def test_separately_planned_short_experiment_is_inconclusive(self) -> None:
        spec = bounded_metric(planned_units=64)
        values = (0.5,) * 48 + (-1.5,) * 16

        result = evaluate_metric(spec, values, alpha=0.05)

        self.assertEqual(result.estimate, 0.0)
        self.assertAlmostEqual(result.interval.lower, -0.3395253789351549, places=15)
        self.assertAlmostEqual(result.interval.upper, 0.3395253789351549, places=15)
        self.assertEqual(result.outcome, "inconclusive")

    def test_partial_execution_stays_inconclusive_even_when_values_look_decisive(self) -> None:
        spec = bounded_metric(
            planned_units=4096,
            acceptance=Acceptance("equivalence", upper=0.5, lower=-0.5),
        )

        result = evaluate_metric(spec, (0.0,) * 4000, alpha=0.05)

        self.assertEqual(result.outcome, "inconclusive")
        self.assertEqual((result.observed_units, result.planned_units), (4000, 4096))
        self.assertIsNotNone(result.reason)

    def test_zero_units_are_unavailable_and_overrun_is_invalid(self) -> None:
        spec = bounded_metric(planned_units=64)

        missing = evaluate_metric(spec, (), alpha=0.05)
        self.assertEqual(missing.availability, "unavailable")
        self.assertEqual(missing.observed_units, 0)
        self.assertEqual(missing.unit_summaries, ())
        self.assertIsNotNone(missing.reason)
        with self.assertRaises(ValueError):
            evaluate_metric(spec, (0.0,) * 65, alpha=0.05)

    def test_declared_nonconstant_range_retains_uncertainty_for_constant_observations(self) -> None:
        spec = bounded_metric(
            planned_units=100,
            bounds=Bounds(-1, 1),
            acceptance=Acceptance("equivalence", upper=0.5, lower=-0.5),
        )

        result = evaluate_metric(spec, (0.0,) * 100, alpha=0.05)

        self.assertAlmostEqual(result.interval.lower, -0.2716203031481239, places=15)
        self.assertAlmostEqual(result.interval.upper, 0.2716203031481239, places=15)
        self.assertGreater(result.interval.upper - result.interval.lower, 0.0)

    def test_constant_declared_range_produces_a_point_interval(self) -> None:
        spec = bounded_metric(
            planned_units=1,
            bounds=Bounds(3, 3),
            acceptance=Acceptance("equivalence", upper=3, lower=3),
        )

        result = evaluate_metric(spec, (3,), alpha=0.05)

        self.assertEqual(result.interval, Bounds(3, 3))
        self.assertEqual(result.outcome, "pass")

    def test_interval_is_clipped_to_known_bounds(self) -> None:
        spec = bounded_metric(
            planned_units=2,
            bounds=Bounds(0, 1),
            acceptance=Acceptance("equivalence", upper=1, lower=0),
        )

        upper = evaluate_metric(spec, (1, 1), alpha=0.5)
        lower = evaluate_metric(spec, (0, 0), alpha=0.5)

        self.assertEqual(upper.interval.upper, 1.0)
        self.assertEqual(lower.interval.lower, 0.0)
        self.assertAlmostEqual(upper.interval.lower, 0.41129498874226267, places=15)
        self.assertAlmostEqual(lower.interval.upper, 0.5887050112577373, places=15)

    def test_equivalence_interval_touching_margin_is_not_strictly_disjoint(self) -> None:
        spec = bounded_metric(
            planned_units=2,
            bounds=Bounds(0, 1),
            acceptance=Acceptance("equivalence", upper=0.8, lower=0.5887050112577373),
        )

        result = evaluate_metric(spec, (0, 0), alpha=0.5)

        self.assertEqual(result.interval.upper, 0.5887050112577373)
        self.assertEqual(result.outcome, "inconclusive")

    def test_upper_margin_equality_passes(self) -> None:
        spec = MetricSpec(
            metric_id="upper",
            units="error",
            direction="smaller_is_better",
            comparison="candidate-reference",
            acceptance=Acceptance("upper", upper=0.5887050112577373),
            evidence_mode="bounded_fixed_n",
            planned_units=2,
            replication_unit="independent_run",
            scope="fixed_inputs",
            bounds=Bounds(0, 1),
        )

        result = evaluate_metric(spec, (0, 0), alpha=0.5)

        self.assertEqual(result.interval.upper, 0.5887050112577373)
        self.assertEqual(result.outcome, "pass")

    def test_extreme_valid_values_and_alpha_do_not_overflow(self) -> None:
        spec = MetricSpec(
            metric_id="large",
            units="quantity",
            direction="smaller_is_better",
            comparison="candidate-reference",
            acceptance=Acceptance("upper", upper=1e308),
            evidence_mode="bounded_fixed_n",
            planned_units=2,
            replication_unit="independent_run",
            scope="fixed_inputs",
            bounds=Bounds(0, 1e308),
        )

        large = evaluate_metric(spec, (1e308, 1e308), alpha=0.99)
        tiny_alpha = evaluate_metric(
            bounded_metric(
                planned_units=2,
                bounds=Bounds(0, 1),
                acceptance=Acceptance("equivalence", upper=0.6, lower=0.4),
            ),
            (0.5, 0.5),
            alpha=5e-324,
        )

        self.assertEqual(large.estimate, 1e308)
        self.assertEqual(large.interval.upper, 1e308)
        self.assertEqual(large.outcome, "pass")
        self.assertEqual(tiny_alpha.interval, Bounds(0, 1))
        self.assertEqual(tiny_alpha.outcome, "inconclusive")

    def test_malformed_samples_and_alpha_fail_closed(self) -> None:
        spec = bounded_metric(planned_units=1)
        for value in (True, "0", math.nan, math.inf, -math.inf, -1.5000000000000002, 0.5000000000000001):
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_metric(spec, (value,), alpha=0.05)  # type: ignore[arg-type]
        for alpha in (None, 0, 1, True, "0.05", math.nan, math.inf):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                evaluate_metric(spec, (0.0,), alpha=alpha)  # type: ignore[arg-type]
        for unordered in ({"sample": 0.0}, {0.0}, frozenset({0.0})):
            with self.subTest(unordered=unordered), self.assertRaises(ValueError):
                evaluate_metric(spec, unordered, alpha=0.05)  # type: ignore[arg-type]

    def test_generator_is_not_consumed_beyond_the_first_overrun_unit(self) -> None:
        spec = bounded_metric(planned_units=2)

        def overrun_then_explode():
            yield 0.0
            yield 0.0
            yield 0.0
            raise AssertionError("the fixed-n evaluator consumed beyond n + 1")

        with self.assertRaises(ValueError):
            evaluate_metric(spec, overrun_then_explode(), alpha=0.05)

    def test_optional_metric_is_always_descriptive_and_inconclusive(self) -> None:
        spec = bounded_metric(
            planned_units=4096,
            mandatory=False,
            acceptance=Acceptance("equivalence", upper=0.1, lower=-0.1),
        )
        values = (0.5,) * 3072 + (-1.5,) * 1024

        result = evaluate_metric(spec, values, alpha=0.05)

        self.assertEqual(result.outcome, "inconclusive")
        self.assertIsNotNone(result.reason)


class ContractEvaluationTests(unittest.TestCase):
    def test_alpha_allocation_excludes_exact_and_optional_metrics(self) -> None:
        exact = exact_metric(
            "exact",
            direction="smaller_is_better",
            acceptance=Acceptance("upper", upper=0.1),
        )
        first = bounded_metric("first", planned_units=1, bounds=Bounds(0, 0))
        optional = bounded_metric("optional", planned_units=1, bounds=Bounds(0, 0), mandatory=False)
        second = bounded_metric("second", planned_units=1, bounds=Bounds(0, 0))
        contract = AcceptanceContract((exact, first, optional, second), alpha_total=0.06)

        results = evaluate_metrics(
            contract,
            {"exact": (0.0,), "first": (0.0,), "optional": (0.0,), "second": (0.0,)},
        )

        self.assertEqual(
            tuple(result.metric_id for result in results), ("exact", "first", "optional", "second")
        )
        self.assertIsNone(results[0].alpha)
        self.assertEqual(results[1].alpha, 0.03)
        self.assertEqual(results[2].alpha, 0.06)
        self.assertEqual(results[2].outcome, "inconclusive")
        self.assertEqual(results[3].alpha, 0.03)

    def test_value_mapping_requires_exactly_declared_metric_ids(self) -> None:
        contract = AcceptanceContract((bounded_metric("only", planned_units=1),))

        with self.assertRaises(ValueError):
            evaluate_metrics(contract, {})
        with self.assertRaises(ValueError):
            evaluate_metrics(contract, {"only": (0.0,), "extra": (0.0,)})


class FixedSeedOperatingCharacteristicTests(unittest.TestCase):
    def test_fixed_seed_coverage_respects_predeclared_binomial_tolerance(self) -> None:
        """At 400 trials, <=60 misses is the 99.9% binomial upper cutoff for p=.10."""
        rng = random.Random(20260919)
        trials = 400
        truth = 0.37
        spec = bounded_metric(
            planned_units=64,
            bounds=Bounds(0, 1),
            acceptance=Acceptance("equivalence", upper=1, lower=0),
        )
        misses = 0
        for _ in range(trials):
            values = tuple(1.0 if rng.random() < truth else 0.0 for _ in range(64))
            interval = evaluate_metric(spec, values, alpha=0.1).interval
            misses += not (interval.lower <= truth <= interval.upper)

        self.assertLessEqual(misses, 60)

    def test_fixed_seed_biased_case_meets_predeclared_power_tolerance(self) -> None:
        """At 300 trials, >=272 detections is a 99.9% binomial lower cutoff for p=.95."""
        rng = random.Random(20260920)
        trials = 300
        spec = bounded_metric(planned_units=64)
        failures = 0
        for _ in range(trials):
            values = tuple(0.5 if rng.random() < 0.25 else -1.5 for _ in range(64))
            failures += evaluate_metric(spec, values, alpha=0.05).outcome == "fail"

        self.assertGreaterEqual(failures, 272)


if __name__ == "__main__":
    unittest.main()
