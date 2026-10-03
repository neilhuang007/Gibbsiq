"""Independent scalar loss oracles for the complete-model workflow."""

from __future__ import annotations

import math
import unittest

from gibbsiq.qualification.model_evaluation import LossSummary, combine_losses, language_loss


class LanguageLossTests(unittest.TestCase):
    def test_summary_cannot_claim_impossible_capped_losses(self) -> None:
        for fields in (
            (1.0, 1, 2.0, 0, 8.0),
            (20.0, 1, 9.0, 1, 8.0),
            (20.0, 2, 1.0, 1, 8.0),
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                LossSummary(*fields)

    def test_summary_allows_only_two_ulps_of_additive_rounding(self) -> None:
        unit = math.ulp(1.0)
        self.assertEqual(LossSummary(1.0, 1, 1.0 + 2 * unit, 0, 8.0).capped_loss_sum, 1.0 + 2 * unit)
        self.assertEqual(LossSummary(2.0, 1, 1.0 - 2 * unit, 1, 1.0).cap_hits, 1)
        with self.assertRaises(ValueError):
            LossSummary(1.0, 1, 1.0 + 3 * unit, 0, 8.0)
        with self.assertRaises(ValueError):
            LossSummary(2.0, 1, 1.0 - 3 * unit, 1, 1.0)

    def test_summary_rejects_overflow_in_derived_count_bounds(self) -> None:
        with self.assertRaises(ValueError):
            LossSummary(0.0, 10**400, 0.0, 0, 1.0)

    def test_uniform_logits_have_hand_computed_cross_entropy(self) -> None:
        result = language_loss([[0.0] * 4] * 3, [0, 2, 3])
        self.assertEqual(result.valid_tokens, 3)
        self.assertAlmostEqual(result.loss_sum, 3 * math.log(4))
        self.assertAlmostEqual(result.nll, math.log(4))
        self.assertAlmostEqual(result.perplexity, 4.0)
        self.assertIsNone(result.perplexity_unavailable_reason)
        self.assertEqual(result.cap_hits, 0)

    def test_mask_excludes_targets_from_both_numerator_and_denominator(self) -> None:
        result = language_loss([[0.0, 0.0], [-100.0, 100.0]], [0, 0], mask=[True, False])
        self.assertEqual(result.valid_tokens, 1)
        self.assertAlmostEqual(result.nll, math.log(2))
        self.assertAlmostEqual(result.capped_nll, math.log(2))
        self.assertEqual(result.cap_hits, 0)

    def test_combining_unequal_documents_weights_valid_tokens(self) -> None:
        first = language_loss([[0.0, 0.0]] * 2, [0, 1])
        second = language_loss([[0.0] * 4], [3])
        result = combine_losses((first, second))
        expected = 4 * math.log(2) / 3
        self.assertEqual(result.valid_tokens, 3)
        self.assertAlmostEqual(result.nll, expected)
        self.assertNotAlmostEqual(result.nll, (first.nll + second.nll) / 2)

    def test_stable_loss_handles_large_logits_and_reports_perplexity_overflow(self) -> None:
        tied = language_loss([[1000.0, 1000.0]], [1])
        self.assertAlmostEqual(tied.nll, math.log(2))
        wrong = language_loss([[-1000.0, 0.0]], [0], cap=8.0)
        self.assertEqual(wrong.nll, 1000.0)
        self.assertEqual(wrong.capped_nll, 8.0)
        self.assertEqual(wrong.cap_hit_rate, 1.0)
        self.assertIsNone(wrong.perplexity)
        self.assertIn("overflow", wrong.perplexity_unavailable_reason.lower())

    def test_cap_equality_is_not_a_hit(self) -> None:
        result = language_loss([[0.0, 0.0], [-2.0, 0.0]], [0, 0], cap=math.log(2))
        self.assertEqual(result.cap_hits, 1)
        self.assertEqual(result.cap_hit_rate, 0.5)
        self.assertAlmostEqual(result.capped_loss_sum, 2 * math.log(2))
        self.assertGreater(result.loss_sum, result.capped_loss_sum)

    def test_exact_cap_equality_is_not_a_hit(self) -> None:
        result = language_loss([[0.0, 0.0]], [1], cap=math.log(2))
        self.assertEqual(result.cap_hits, 0)
        self.assertEqual(result.cap_hit_rate, 0.0)

    def test_capped_mean_stays_within_closed_bound_after_division(self) -> None:
        result = language_loss([[-10.0, 0.0]] * 3, [0] * 3, cap=0.1)
        self.assertEqual(result.cap_hits, 3)
        self.assertLessEqual(result.capped_nll, 0.1)

    def test_masked_row_still_has_to_be_a_valid_model_output(self) -> None:
        for row in ([float("nan"), 0.0], [0.0], [True, 0.0]):
            with self.subTest(row=row), self.assertRaises(ValueError):
                language_loss([[0.0, 0.0], row], [0, 0], mask=[True, False])

    def test_two_documents_with_different_masks_combine_by_valid_tokens(self) -> None:
        first = language_loss([[0.0, 0.0], [0.0, 0.0]], [0, 0], mask=[True, False])
        second = language_loss([[0.0] * 4] * 3, [0, 1, 2])
        combined = combine_losses((first, second))
        self.assertEqual(combined.valid_tokens, 4)
        self.assertAlmostEqual(combined.nll, (math.log(2) + 3 * math.log(4)) / 4)

    def test_loss_rejects_nonfinite_difference_even_for_finite_logits(self) -> None:
        with self.assertRaises(ValueError):
            language_loss([[1e308, -1e308]], [1])

    def test_invalid_shapes_values_and_masks_fail(self) -> None:
        invalid = (
            ([], []),
            ([[0.0]], [0]),
            ([[0.0, 0.0], [0.0]], [0, 0]),
            ([[0.0, 0.0]], []),
            ([[0.0, 0.0]], [True]),
            ([[0.0, 0.0]], [2]),
            ([[0.0, 0.0]], [-1]),
            ([[False, 0.0]], [0]),
            ([[float("nan"), 0.0]], [0]),
            ([[float("inf"), 0.0]], [0]),
            ([[1e308, -1e308]], [1]),
        )
        for logits, targets in invalid:
            with self.subTest(logits=logits, targets=targets), self.assertRaises(ValueError):
                language_loss(logits, targets)
        for mask in ([False], [1], [], [True, False]):
            with self.subTest(mask=mask), self.assertRaises(ValueError):
                language_loss([[0.0, 0.0]], [0], mask=mask)
        for cap in (0, -1, True, float("inf"), 129):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                language_loss([[0.0, 0.0]], [0], cap=cap)

    def test_combine_rejects_empty_or_incompatible_caps(self) -> None:
        with self.assertRaises(ValueError):
            combine_losses(())
        with self.assertRaises(ValueError):
            combine_losses(
                (
                    language_loss([[0.0, 0.0]], [0], cap=1),
                    language_loss([[0.0, 0.0]], [0], cap=2),
                )
            )


if __name__ == "__main__":
    unittest.main()
