"""Cost comparison only computes deltas across identical claim boundaries."""

import unittest

from gibbsiq.qualification.contracts import CostRecord, CostScope
from gibbsiq.qualification.costs import compare_costs, sample_work


class CostContractTests(unittest.TestCase):
    def setUp(self):
        self.scope = CostScope("complete_inference", ("model", "head"), ("compile", "warmup"), 2, 1, 4)

    def record(self, value=1.0, **changes):
        fields = dict(
            quantity="latency",
            units="seconds",
            scope=self.scope,
            provenance="measured",
            availability="available",
            value=value,
            method="perf-counter-v1",
            omissions=("energy",),
        )
        fields.update(changes)
        return CostRecord(**fields)

    def test_compatible_delta_ratio_and_zero_reference(self):
        result = compare_costs(self.record(2), self.record(3))
        self.assertEqual((result.availability, result.delta, result.ratio), ("available", 1, 1.5))
        zero = compare_costs(self.record(0), self.record(3))
        self.assertEqual(zero.delta, 3)
        self.assertIsNone(zero.ratio)
        self.assertIn("zero", zero.reason)

    def test_incompatible_dimensions_boundaries_and_methods(self):
        reference = self.record()
        variants = (
            self.record(quantity="energy", units="joules"),
            self.record(scope=CostScope("model_body", ("model",), ("head",))),
            self.record(provenance="modeled"),
            self.record(method="different-work-recipe"),
            self.record(omissions=("transfer",)),
        )
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                compare_costs(reference, variant)

    def test_missing_energy_remains_unknown(self):
        unavailable = self.record(
            quantity="energy",
            units="joules",
            availability="unavailable",
            value=None,
            reason="No complete-system meter",
        )
        result = compare_costs(unavailable, unavailable)
        self.assertEqual(result.availability, "unavailable")
        self.assertIsNone(result.delta)
        self.assertIsNone(result.ratio)
        self.assertIn("meter", result.reason)

    def test_hand_counted_spin_draws_and_scope(self):
        scope = CostScope("iid_activation", ("a", "b"))
        result = sample_work({"a": 8, "b": 3}, {"a": 4, "b": 7}, scope=scope)
        self.assertEqual(result.value, 53)
        self.assertEqual(
            (result.quantity, result.units, result.provenance, result.method),
            ("sample_work", "samples", "modeled", "iid-spin-draws-v1"),
        )
        self.assertIn("energy", " ".join(result.omissions))
        for elements, samples, selected_scope in (
            ({}, {}, scope),
            ({"a": 8}, {"b": 4}, scope),
            ({"a": True}, {"a": 4}, CostScope("iid_activation", ("a",))),
            ({"a": 8}, {"a": 0}, CostScope("iid_activation", ("a",))),
            ({"a": 8}, {"a": 4}, scope),
            ({"a": 2**53}, {"a": 2}, CostScope("iid_activation", ("a",))),
        ):
            with self.subTest(elements=elements, samples=samples), self.assertRaises(ValueError):
                sample_work(elements, samples, scope=selected_scope)


if __name__ == "__main__":
    unittest.main()
