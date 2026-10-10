"""Human comparison rendering uses retained numerical summary values."""

import unittest


class ComparisonRenderingTests(unittest.TestCase):
    def test_escapes_fields_and_labels_union_bound(self) -> None:
        from gibbsiq.qualification.reporting import render_comparison

        summary = {
            "schema": "qualification-comparison-v1",
            "compatible": True,
            "outcome": "inconclusive",
            "issues": [],
            "metrics": [
                {
                    "metric_id": "unsafe|metric\nrow",
                    "baseline": {"estimate": 0.1},
                    "candidate": {"estimate": 0.2},
                    "delta": 0.1,
                    "difference_interval": {"lower": -0.1, "upper": 0.3},
                    "joint_error_bound": 0.1,
                }
            ],
            "limitations": ["Difference range is a union bound."],
        }
        rendered = render_comparison(summary)
        self.assertIn("unsafe\\|metric row", rendered)
        self.assertIn("[-0.1, 0.3]", rendered)
        self.assertIn("Union-bound difference range", rendered)


if __name__ == "__main__":
    unittest.main()
