"""Independent worked cost examples distinguish work from elapsed time."""

import unittest


class CostAccountingTests(unittest.TestCase):
    def test_sequential_and_concurrent_regions_have_different_latency(self):
        from gibbsiq.qualification.costs import LatencyRegion, critical_path_seconds

        first = LatencyRegion("prepare", 0.002, ("input_transfer",))
        sequential = LatencyRegion("compute", 0.003, ("model",), depends_on=("prepare",))
        concurrent = LatencyRegion("compute", 0.003, ("model",))
        self.assertAlmostEqual(critical_path_seconds((first, sequential)), 0.005)
        self.assertAlmostEqual(critical_path_seconds((first, concurrent)), 0.003)

    def test_inclusive_parent_and_child_are_not_double_counted(self):
        from gibbsiq.qualification.costs import LatencyRegion, critical_path_seconds

        parent = LatencyRegion("complete", 0.005, ("attention", "head"))
        child = LatencyRegion("attention-only", 0.002, ("attention",))
        with self.assertRaises(ValueError):
            critical_path_seconds((parent, child))

    def test_invalid_dependencies_and_regions(self):
        from gibbsiq.qualification.costs import LatencyRegion, critical_path_seconds

        with self.assertRaises(ValueError):
            LatencyRegion("negative", -0.01, ("model",))
        with self.assertRaises(ValueError):
            critical_path_seconds((LatencyRegion("a", 1, ("a",), ("missing",)),))
        with self.assertRaises(ValueError):
            critical_path_seconds(
                (LatencyRegion("a", 1, ("a",), ("b",)), LatencyRegion("b", 1, ("b",), ("a",)))
            )
        with self.assertRaises(ValueError):
            critical_path_seconds((LatencyRegion("a", 1, ("a",)), LatencyRegion("a", 2, ("b",))))

    def test_sampling_component_reduction_is_not_complete_model_speedup(self):
        from gibbsiq.qualification.costs import LatencyRegion, critical_path_seconds

        fixed = LatencyRegion("fixed", 0.080, ("digital", "transfer", "head"))
        original = LatencyRegion("sampling", 0.020, ("sampling",), depends_on=("fixed",))
        reduced = LatencyRegion("sampling", 0.005, ("sampling",), depends_on=("fixed",))
        baseline = critical_path_seconds((fixed, original))
        candidate = critical_path_seconds((fixed, reduced))
        self.assertAlmostEqual(baseline, 0.100)
        self.assertAlmostEqual(candidate, 0.085)
        self.assertAlmostEqual(1 - candidate / baseline, 0.15)


if __name__ == "__main__":
    unittest.main()
