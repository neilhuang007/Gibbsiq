"""Observer overhead preserves every paired timing and conservative decisions."""

import unittest

from gibbsiq.qualification.timing import observer_overhead


class ObserverOverheadTests(unittest.TestCase):
    def test_within_above_and_mixed(self):
        baseline = (100, 100, 100, 100, 100)
        within = observer_overhead(baseline, (100, 101, 102, 103, 105))
        self.assertEqual(within.outcome, "within_target")
        self.assertEqual(len(within.ratios), 5)
        self.assertAlmostEqual(within.median, 0.02)
        self.assertAlmostEqual(within.minimum, 0)
        self.assertAlmostEqual(within.maximum, 0.05)
        self.assertEqual(observer_overhead(baseline, (106,) * 5).outcome, "above_target")
        mixed = observer_overhead(baseline, (100, 107, 100, 110, 100))
        self.assertEqual(mixed.outcome, "inconclusive")
        for actual, expected in zip(mixed.ratios, (0, 0.07, 0, 0.1, 0)):
            self.assertAlmostEqual(actual, expected)
        self.assertIn("future", mixed.limitation)

    def test_short_and_invalid_vectors(self):
        self.assertEqual(observer_overhead((1,) * 4, (1,) * 4).outcome, "inconclusive")
        for base, observed in (((1,), ()), ((0,), (1,)), ((1,), (float("inf"),))):
            with self.subTest(base=base, observed=observed), self.assertRaises(ValueError):
                observer_overhead(base, observed)


if __name__ == "__main__":
    unittest.main()
