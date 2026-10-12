"""Accept/reject behaviour of the shared private validators."""

from __future__ import annotations

import math
import unittest

from gibbsiq._validation import (
    bounded_int,
    canonical_json,
    exact_limit,
    finite_number,
    nonnegative_beta,
    nonnegative_float,
    positive_float,
    variable_position,
)


class CanonicalJsonTests(unittest.TestCase):
    def test_sorted_compact_text(self) -> None:
        self.assertEqual(canonical_json({"b": 1, "a": [1, 2]}), '{"a":[1,2],"b":1}')

    def test_non_finite_rejection(self) -> None:
        with self.assertRaises(ValueError):
            canonical_json(math.nan)

    def test_non_ascii_escaping(self) -> None:
        self.assertEqual(canonical_json("é"), '"\\u00e9"')


class VariablePositionTests(unittest.TestCase):
    def test_in_range_integer(self) -> None:
        self.assertEqual(variable_position(2, size=3, name="p"), 2)

    def test_rejected_inputs(self) -> None:
        for bad in (True, -1, 3, 1.0, "1", None):
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(ValueError, "^p must be a valid variable position$"),
            ):
                variable_position(bad, size=3, name="p")


class BoundedIntTests(unittest.TestCase):
    message = "{name} needs >= {minimum}, got {value!r}"

    def test_accepted_boundary(self) -> None:
        self.assertEqual(bounded_int(4, name="n", message=self.message, minimum=4), 4)

    def test_below_minimum_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "^n needs >= 4, got 3$"):
            bounded_int(3, name="n", message=self.message, minimum=4)

    def test_boolean_and_float_rejection(self) -> None:
        for bad in (True, 2.0):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                bounded_int(bad, name="n", message=self.message, minimum=0)

    def test_type_message_override(self) -> None:
        with self.assertRaisesRegex(ValueError, "^n must be int, got 'x'$"):
            bounded_int(
                "x",
                name="n",
                message=self.message,
                minimum=0,
                type_message="{name} must be int, got {value!r}",
            )

    def test_unbounded_minimum(self) -> None:
        self.assertEqual(bounded_int(-7, name="n", message=self.message, minimum=None), -7)

    def test_braces_in_name_are_literal(self) -> None:
        with self.assertRaisesRegex(ValueError, r"^\{x\} needs >= 1, got 0$"):
            bounded_int(0, name="{x}", message=self.message, minimum=1)


class ExactLimitTests(unittest.TestCase):
    def test_zero_accepted(self) -> None:
        self.assertEqual(exact_limit(0, name="max_variables"), 0)

    def test_rejection_message(self) -> None:
        for bad in (-1, True, 1.5):
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(ValueError, rf"^max_variables must be an integer >= 0, got {bad!r}$"),
            ):
                exact_limit(bad, name="max_variables")


class FiniteNumberTests(unittest.TestCase):
    def test_float_coercion(self) -> None:
        result = finite_number(3, name="x")
        self.assertIsInstance(result, float)
        self.assertEqual(result, 3.0)

    def test_default_boolean_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "^x must be numeric, not boolean$"):
            finite_number(True, name="x")

    def test_custom_boolean_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "^x is bool True$"):
            finite_number(True, name="x", bool_message="{name} is bool {value!r}")

    def test_non_finite_rejection(self) -> None:
        for bad in (math.nan, math.inf, -math.inf):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "^x must be finite"):
                finite_number(bad, name="x")


class PositiveFloatTests(unittest.TestCase):
    sign = "{name} must be positive, got {value!r}"

    def test_positive_accepted(self) -> None:
        self.assertEqual(positive_float(2, name="x", sign_message=self.sign), 2.0)

    def test_zero_and_negative_rejection(self) -> None:
        for bad in (0, -0.0, -1.5):
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(ValueError, rf"^x must be positive, got {bad!r}$"),
            ):
                positive_float(bad, name="x", sign_message=self.sign)

    def test_boolean_and_non_finite_rejection(self) -> None:
        for bad in (True, math.nan, math.inf):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                positive_float(bad, name="x", sign_message=self.sign)


class NonnegativeFloatTests(unittest.TestCase):
    sign = "{name} must be nonnegative"

    def test_zero_accepted(self) -> None:
        self.assertEqual(nonnegative_float(0, name="x", sign_message=self.sign), 0.0)

    def test_negative_rejection_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "^x must be nonnegative$"):
            nonnegative_float(-1e-300, name="x", sign_message=self.sign)

    def test_negative_zero_preserved_by_default(self) -> None:
        result = nonnegative_float(-0.0, name="x", sign_message=self.sign)
        self.assertEqual(math.copysign(1.0, result), -1.0)

    def test_negative_zero_normalised_on_request(self) -> None:
        result = nonnegative_float(-0.0, name="x", sign_message=self.sign, normalize_negative_zero=True)
        self.assertEqual(math.copysign(1.0, result), 1.0)

    def test_boolean_rejection(self) -> None:
        with self.assertRaisesRegex(ValueError, "^x must be numeric, not boolean$"):
            nonnegative_float(False, name="x", sign_message=self.sign)


class NonnegativeBetaTests(unittest.TestCase):
    def test_accepted_values(self) -> None:
        self.assertEqual(nonnegative_beta(0), 0.0)
        self.assertEqual(nonnegative_beta(1.25), 1.25)

    def test_boolean_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "^beta must be a finite non-negative number, got True$"):
            nonnegative_beta(True)

    def test_negative_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "^beta must be non-negative, got -1$"):
            nonnegative_beta(-1)

    def test_non_finite_rejection(self) -> None:
        for bad in (math.nan, math.inf):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "^beta must be finite"):
                nonnegative_beta(bad)

    def test_negative_zero_flag(self) -> None:
        self.assertEqual(math.copysign(1.0, nonnegative_beta(-0.0)), -1.0)
        self.assertEqual(math.copysign(1.0, nonnegative_beta(-0.0, normalize_negative_zero=True)), 1.0)


if __name__ == "__main__":
    unittest.main()
