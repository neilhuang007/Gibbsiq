"""Frozen public value objects can be copied with changed execution controls."""

from dataclasses import replace
import unittest

from gibbsiq.qualification.contracts import ResourceBudget
from test_suite.tests.qualification.test_contracts import workload


class ValueUpdateTests(unittest.TestCase):
    def test_changing_budget_preserves_nested_precision_without_serializing_a_workload(self):
        original = replace(workload(), precision={"groups": {"attention": ["qkv", "out"]}})
        changed = replace(original, resources=ResourceBudget(2, 5, 65536))
        self.assertEqual(tuple(changed.precision["groups"]["attention"]), ("qkv", "out"))
        self.assertEqual(changed.resources.max_jobs, 2)
        self.assertEqual(original.precision, changed.precision)
        with self.assertRaises(TypeError):
            changed.precision["groups"]["attention"][0] = "changed"


if __name__ == "__main__":
    unittest.main()
