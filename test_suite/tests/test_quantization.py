"""Fixed-point effective-coefficient quantization contracts."""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.hardware import FixedPointSpec  # noqa: E402
from gibbsiq.quantization import analyze_quantization  # noqa: E402


class QuantizationSemanticsTests(unittest.TestCase):
    def test_exactly_representable_model_has_zero_distribution_error(self) -> None:
        model = compile_ising(
            {"a": 0.5, "b": -0.25},
            {("a", "b"): 0.75},
            offset=123.0,
        )
        analysis = analyze_quantization(model, FixedPointSpec(4, 3), beta=1.0)
        self.assertTrue(analysis.exactly_representable)
        self.assertEqual(analysis.state_log_weight_error_bound, 0.0)
        self.assertEqual(analysis.total_variation_upper_bound, 0.0)
        self.assertIsNotNone(analysis.exact_comparison)
        assert analysis.exact_comparison is not None
        self.assertEqual(analysis.exact_comparison.total_variation, 0.0)
        self.assertEqual(analysis.exact_comparison.kl_target_to_implemented, 0.0)
        self.assertEqual(analysis.implemented_effective_model.offset, 0.0)
        self.assertEqual(
            analysis.implemented_effective_model.metadata["original_offset_handling"],
            "omitted; cancels from normalized probabilities",
        )

    def test_nearest_even_rounding_is_deterministic_at_binary_ties(self) -> None:
        model = compile_ising(
            {
                "negative_high": -0.375,
                "negative_low": -0.125,
                "positive_high": 0.375,
                "positive_low": 0.125,
            }
        )
        analysis = analyze_quantization(model, FixedPointSpec(2, 2), beta=1.0)
        quantized = {
            row.left: row.quantized_effective for row in analysis.coefficients if row.kind == "linear"
        }
        self.assertEqual(
            quantized,
            {
                "negative_high": -0.5,
                "negative_low": 0.0,
                "positive_high": 0.5,
                "positive_low": 0.0,
            },
        )
        self.assertEqual(analysis.zeroed_nonzero_count, 2)

    def test_toward_zero_rounding_handles_negative_values(self) -> None:
        model = compile_ising({"s": -0.375})
        analysis = analyze_quantization(
            model,
            FixedPointSpec(2, 2, rounding="toward_zero"),
            beta=1.0,
        )
        self.assertEqual(analysis.coefficients[0].quantized_effective, -0.25)
        self.assertEqual(analysis.coefficients[0].error, 0.125)

    def test_overflow_reject_and_saturate_are_explicit(self) -> None:
        model = compile_ising({"high": 2.0, "low": -2.0})
        with self.assertRaisesRegex(ValueError, "overflow='reject'"):
            analyze_quantization(model, FixedPointSpec(0, 1), beta=1.0)

        analysis = analyze_quantization(
            model,
            FixedPointSpec(0, 1, overflow="saturate"),
            beta=1.0,
        )
        self.assertEqual(analysis.saturation_count, 2)
        quantized = {row.left: row.quantized_effective for row in analysis.coefficients}
        self.assertEqual(quantized, {"high": 0.5, "low": -1.0})
        self.assertFalse(analysis.exactly_representable)

    def test_beta_zero_is_uniform_and_exactly_representable(self) -> None:
        model = compile_ising(
            {"a": 1e300, "b": -1e300},
            {("a", "b"): 1e300},
            offset=1e308,
        )
        analysis = analyze_quantization(model, FixedPointSpec(1, 2), beta=0.0)
        self.assertTrue(analysis.exactly_representable)
        self.assertEqual(analysis.state_log_weight_error_bound, 0.0)
        assert analysis.exact_comparison is not None
        self.assertEqual(analysis.exact_comparison.total_variation, 0.0)

    def test_rejects_unsigned_format_invalid_beta_and_bad_limit(self) -> None:
        model = compile_ising({"s": 0.5})
        with self.assertRaisesRegex(ValueError, "signed"):
            analyze_quantization(
                model,
                FixedPointSpec(2, 2, signed=False),
                beta=1.0,
            )
        for beta in (-1.0, True, float("nan"), float("inf")):
            with self.subTest(beta=beta), self.assertRaises(ValueError):
                analyze_quantization(model, FixedPointSpec(2, 2), beta=beta)
        for limit in (-1, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                analyze_quantization(
                    model,
                    FixedPointSpec(2, 2),
                    beta=1.0,
                    max_exact_variables=limit,  # type: ignore[arg-type]
                )


class QuantizationBoundTests(unittest.TestCase):
    def test_local_logit_and_global_error_bounds_match_hand_calculation(self) -> None:
        model = compile_ising(
            {"a": 0.2, "b": -0.3},
            {("a", "b"): 0.4},
        )
        analysis = analyze_quantization(model, FixedPointSpec(2, 2), beta=1.0)
        rows = {(row.kind, row.left, row.right): row for row in analysis.coefficients}
        delta_a = abs(rows[("linear", "a", None)].error)
        delta_b = abs(rows[("linear", "b", None)].error)
        delta_j = abs(rows[("quadratic", "a", "b")].error)
        expected_epsilon = delta_a + delta_b + delta_j
        bounds = {row.variable: row.bound for row in analysis.local_logit_error_bounds}
        self.assertAlmostEqual(analysis.state_log_weight_error_bound, expected_epsilon)
        self.assertAlmostEqual(bounds["a"], 2.0 * (delta_a + delta_j))
        self.assertAlmostEqual(bounds["b"], 2.0 * (delta_b + delta_j))

    def test_exact_total_variation_respects_analytic_bound(self) -> None:
        model = compile_ising(
            {"a": 0.17, "b": -0.31, "c": 0.43},
            {("a", "b"): 0.29, ("b", "c"): -0.37},
        )
        analysis = analyze_quantization(model, FixedPointSpec(2, 2), beta=1.7)
        assert analysis.exact_comparison is not None
        self.assertLessEqual(
            analysis.exact_comparison.total_variation,
            analysis.total_variation_upper_bound + 1e-15,
        )
        self.assertEqual(
            analysis.total_variation_upper_bound,
            math.tanh(analysis.state_log_weight_error_bound),
        )

    def test_deterministic_small_model_sweep_respects_total_variation_bound(self) -> None:
        coefficient_sets = (
            (
                {"a": 0.17, "b": -0.31, "c": 0.43},
                {("a", "b"): 0.29, ("b", "c"): -0.37},
            ),
            (
                {"a": -0.72, "b": 0.11, "c": -0.23},
                {("a", "c"): 0.51, ("b", "c"): 0.07},
            ),
            (
                {"a": 0.0, "b": 0.125, "c": -0.375},
                {("a", "b"): -0.625, ("a", "c"): 0.875},
            ),
        )
        fixed_point = FixedPointSpec(3, 4)
        for model_index, (linear, quadratic) in enumerate(coefficient_sets):
            for beta in (0.0, 0.25, 0.75, 1.7, 2.25):
                with self.subTest(model_index=model_index, beta=beta):
                    analysis = analyze_quantization(
                        compile_ising(linear, quadratic),
                        fixed_point,
                        beta=beta,
                    )
                    self.assertEqual(analysis.exact_comparison_status, "computed")
                    assert analysis.exact_comparison is not None
                    self.assertLessEqual(
                        analysis.exact_comparison.total_variation,
                        analysis.total_variation_upper_bound + 2e-15,
                    )

    def test_spin_gauge_transform_preserves_quantization_error_away_from_saturation(self) -> None:
        linear = {"a": 0.17, "b": -0.31, "c": 0.43}
        quadratic = {
            ("a", "b"): 0.29,
            ("a", "c"): 0.11,
            ("b", "c"): -0.37,
        }
        gauge = {"a": -1, "b": 1, "c": -1}
        gauged_linear = {variable: gauge[variable] * coefficient for variable, coefficient in linear.items()}
        gauged_quadratic = {
            pair: gauge[pair[0]] * gauge[pair[1]] * coefficient for pair, coefficient in quadratic.items()
        }
        fixed_point = FixedPointSpec(2, 3)
        baseline = analyze_quantization(
            compile_ising(linear, quadratic),
            fixed_point,
            beta=1.7,
        )
        transformed = analyze_quantization(
            compile_ising(gauged_linear, gauged_quadratic),
            fixed_point,
            beta=1.7,
        )
        self.assertEqual(baseline.saturation_count, 0)
        self.assertEqual(transformed.saturation_count, 0)
        self.assertAlmostEqual(
            baseline.state_log_weight_error_bound,
            transformed.state_log_weight_error_bound,
            places=15,
        )
        assert baseline.exact_comparison is not None
        assert transformed.exact_comparison is not None
        self.assertAlmostEqual(
            baseline.exact_comparison.total_variation,
            transformed.exact_comparison.total_variation,
            places=15,
        )

    def test_offset_shift_leaves_all_quantization_metrics_unchanged(self) -> None:
        h = {"a": 0.17, "b": -0.31}
        J = {("a", "b"): 0.29}
        baseline = analyze_quantization(compile_ising(h, J), FixedPointSpec(2, 3), beta=1.7)
        shifted = analyze_quantization(
            compile_ising(h, J, offset=1e308),
            FixedPointSpec(2, 3),
            beta=1.7,
        )
        self.assertEqual(baseline.coefficients, shifted.coefficients)
        self.assertEqual(
            baseline.state_log_weight_error_bound,
            shifted.state_log_weight_error_bound,
        )
        assert baseline.exact_comparison is not None
        assert shifted.exact_comparison is not None
        self.assertEqual(
            baseline.exact_comparison.total_variation,
            shifted.exact_comparison.total_variation,
        )

    def test_large_model_skips_exact_enumeration_but_keeps_bounds(self) -> None:
        variables = tuple(range(8))
        model = compile_ising(
            {variable: 0.13 for variable in variables},
            {(left, left + 1): 0.27 for left in range(7)},
            variables=variables,
        )
        analysis = analyze_quantization(
            model,
            FixedPointSpec(2, 3),
            beta=1.0,
            max_exact_variables=4,
        )
        self.assertEqual(
            analysis.exact_comparison_status,
            "not_computed_too_many_variables",
        )
        self.assertIsNone(analysis.exact_comparison)
        self.assertIsNone(analysis.exact_comparison_reason)
        self.assertGreater(analysis.state_log_weight_error_bound, 0.0)

    def test_extreme_exact_range_skip_keeps_finite_analytic_bounds(self) -> None:
        analysis = analyze_quantization(
            compile_ising({"a": 5e307, "b": 5e307}),
            FixedPointSpec(4, 3, overflow="saturate"),
            beta=1.0,
        )
        self.assertEqual(
            analysis.exact_comparison_status,
            "not_computed_numerical_range",
        )
        self.assertIsNone(analysis.exact_comparison)
        self.assertIn("dynamic range exceeds binary64", analysis.exact_comparison_reason or "")
        self.assertEqual(analysis.state_log_weight_error_bound, 1e308)
        self.assertEqual(analysis.total_variation_upper_bound, 1.0)
        json.dumps(analysis.to_dict(), allow_nan=False)

    def test_serialized_analysis_contains_no_nonfinite_values(self) -> None:
        analysis = analyze_quantization(
            compile_ising({"a": 0.17, "b": -0.31}, {("a", "b"): 0.29}),
            FixedPointSpec(2, 3),
            beta=1.7,
        )
        json.dumps(analysis.to_dict(), allow_nan=False)


if __name__ == "__main__":
    unittest.main()
