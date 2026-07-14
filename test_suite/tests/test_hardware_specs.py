"""Target-specification contracts for the first ThermoMap tranche."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.hardware import (  # noqa: E402
    FixedPointSpec,
    ParameterProvenance,
    TSUSpec,
)


def assumed(source: str = "unit-test assumption") -> ParameterProvenance:
    return ParameterProvenance("assumed", source)


class ParameterProvenanceTests(unittest.TestCase):
    def test_accepts_evidence_classes_and_strips_source(self) -> None:
        for classification in ("measured", "modeled", "assumed", "inferred"):
            with self.subTest(classification=classification):
                row = ParameterProvenance(classification, "  arXiv:test  ")
                self.assertEqual(row.source, "arXiv:test")
                self.assertEqual(row.to_dict()["classification"], classification)

    def test_rejects_unknown_classification_or_empty_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "classification"):
            ParameterProvenance("projected", "paper")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "source"):
            ParameterProvenance("assumed", "  ")
        with self.assertRaisesRegex(ValueError, "note"):
            ParameterProvenance("assumed", "paper", note=3)  # type: ignore[arg-type]


class FixedPointSpecTests(unittest.TestCase):
    def test_signed_s4_3_contract(self) -> None:
        spec = FixedPointSpec(integer_bits=4, fractional_bits=3)
        self.assertEqual(spec.total_bits, 8)
        self.assertEqual(spec.step, 0.125)
        self.assertEqual(spec.minimum, -16.0)
        self.assertEqual(spec.maximum, 15.875)
        self.assertEqual(spec.minimum_code, -128)
        self.assertEqual(spec.maximum_code, 127)

    def test_paper_declared_s4_fractional_variants_have_expected_endpoints(self) -> None:
        # Aadit et al. 2026, arXiv:2606.25313v1, Supplementary S9-S12,
        # declares s{4}{1}, s{4}{3}, and s{4}{6} fixed-point formats.
        for fractional_bits, expected_step, expected_maximum in (
            (1, 0.5, 15.5),
            (3, 0.125, 15.875),
            (6, 0.015625, 15.984375),
        ):
            with self.subTest(fractional_bits=fractional_bits):
                spec = FixedPointSpec(4, fractional_bits)
                self.assertEqual(spec.total_bits, 5 + fractional_bits)
                self.assertEqual(spec.step, expected_step)
                self.assertEqual(spec.minimum, -16.0)
                self.assertEqual(spec.maximum, expected_maximum)

    def test_unsigned_contract(self) -> None:
        spec = FixedPointSpec(integer_bits=2, fractional_bits=2, signed=False)
        self.assertEqual(spec.total_bits, 4)
        self.assertEqual(spec.minimum, 0.0)
        self.assertEqual(spec.maximum, 3.75)
        self.assertEqual(spec.minimum_code, 0)
        self.assertEqual(spec.maximum_code, 15)

    def test_rejects_invalid_bit_and_policy_values(self) -> None:
        for kwargs in (
            {"integer_bits": True, "fractional_bits": 1},
            {"integer_bits": -1, "fractional_bits": 1},
            {"integer_bits": 1, "fractional_bits": -1},
            {"integer_bits": 1, "fractional_bits": 1, "signed": 1},
            {"integer_bits": 1, "fractional_bits": 1, "rounding": "up"},
            {"integer_bits": 1, "fractional_bits": 1, "overflow": "wrap"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                FixedPointSpec(**kwargs)  # type: ignore[arg-type]

    def test_rejects_code_words_binary64_cannot_represent_exactly(self) -> None:
        with self.assertRaisesRegex(ValueError, "53-bit"):
            FixedPointSpec(integer_bits=30, fractional_bits=23)


class TSUSpecTests(unittest.TestCase):
    def test_requires_provenance_for_every_supplied_parameter(self) -> None:
        with self.assertRaisesRegex(ValueError, "pbit_capacity"):
            TSUSpec(name="abstract", pbit_capacity=100)

    def test_accepts_explicit_abstract_target_without_speculative_defaults(self) -> None:
        target = TSUSpec(name="analysis-only")
        self.assertIsNone(target.pbit_capacity)
        self.assertIsNone(target.max_degree)
        self.assertIsNone(target.coefficient_format)
        self.assertEqual(target.provenance, {})

    def test_complete_target_is_immutable_and_serializable(self) -> None:
        provenance = {
            "pbit_capacity": assumed(),
            "max_degree": assumed(),
            "max_color_phases": assumed(),
            "coefficient_format": assumed("arXiv:2606.25313 format convention"),
            "cell_energy_joules": ParameterProvenance("modeled", "arXiv:2606.17327"),
            "cell_update_seconds": assumed(),
        }
        target = TSUSpec(
            name="explicit-test-target",
            pbit_capacity=128,
            max_degree=12,
            max_color_phases=4,
            coefficient_format=FixedPointSpec(4, 3),
            cell_energy_joules=1.3e-15,
            cell_update_seconds=1e-7,
            provenance=provenance,
        )
        provenance.clear()
        self.assertEqual(
            set(target.provenance),
            {
                "pbit_capacity",
                "max_degree",
                "max_color_phases",
                "coefficient_format",
                "cell_energy_joules",
                "cell_update_seconds",
            },
        )
        with self.assertRaises(TypeError):
            target.provenance["extra"] = assumed()  # type: ignore[index]
        payload = target.to_dict()
        self.assertEqual(payload["name"], "explicit-test-target")
        self.assertEqual(payload["coefficient_format"]["total_bits"], 8)

    def test_rejects_dangling_unknown_or_mistyped_provenance(self) -> None:
        with self.assertRaisesRegex(ValueError, "unset"):
            TSUSpec(name="target", provenance={"max_degree": assumed()})
        with self.assertRaisesRegex(ValueError, "unknown"):
            TSUSpec(name="target", provenance={"degree": assumed()})
        with self.assertRaisesRegex(ValueError, "ParameterProvenance"):
            TSUSpec(
                name="target",
                max_degree=4,
                provenance={"max_degree": "paper"},  # type: ignore[dict-item]
            )
        with self.assertRaisesRegex(ValueError, "parameter-name strings"):
            TSUSpec(name="target", provenance={1: assumed()})  # type: ignore[dict-item]
        with self.assertRaisesRegex(ValueError, "mapping"):
            TSUSpec(name="target", provenance=None)  # type: ignore[arg-type]

    def test_rejects_invalid_target_values(self) -> None:
        for field_name, value in (
            ("pbit_capacity", 0),
            ("pbit_capacity", True),
            ("max_degree", -1),
            ("max_color_phases", 0),
            ("cell_energy_joules", 0.0),
            ("cell_update_seconds", float("inf")),
        ):
            with self.subTest(field_name=field_name, value=value), self.assertRaises(ValueError):
                TSUSpec(
                    name="invalid",
                    **{field_name: value},
                    provenance={field_name: assumed()},
                )


if __name__ == "__main__":
    unittest.main()
