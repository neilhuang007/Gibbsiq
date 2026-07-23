"""Independent public seams for bounded binary factor lowering."""

from __future__ import annotations

import itertools
import math
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.factor_lowering import reduce_cubic_monomial  # noqa: E402


def direct_qubo_energy(encoding, bits: dict[object, int]) -> float:
    """Evaluate published QUBO fields without calling the lowering methods."""
    return math.fsum(
        [encoding.qubo_offset]
        + [encoding.qubo_linear[variable] * bits[variable] for variable in encoding.variables]
        + [
            coefficient * bits[left] * bits[right]
            for (left, right), coefficient in encoding.qubo_quadratic.items()
        ]
    )


class CubicMonomialReductionTests(unittest.TestCase):
    """The public factor seam is a one-ancilla Rosenberg reduction."""

    def test_minimizing_over_the_ancilla_recovers_every_source_energy(self) -> None:
        variables = ("left", ("middle", 4), b"right")
        coefficient = 2.5
        encoding = reduce_cubic_monomial(
            variables,
            coefficient=coefficient,
            penalty=abs(coefficient),
            offset=-1.75,
        )

        self.assertEqual(encoding.ancilla_variables, (encoding.ancilla,))
        self.assertEqual(encoding.penalty_policy.status, "adequate_at_energy_boundary")
        self.assertEqual(encoding.source_objective_map, "identity")

        for source_values in itertools.product((0, 1), repeat=3):
            source = dict(zip(variables, source_values))
            expected = -1.75 + coefficient * math.prod(source_values)
            energies = []
            for ancilla_value in (0, 1):
                bits = {**source, encoding.ancilla: ancilla_value}
                energies.append(direct_qubo_energy(encoding, bits))
            self.assertAlmostEqual(min(energies), expected, places=12)

    def test_penalty_boundary_has_known_below_equal_and_above_behaviors_for_both_signs(self) -> None:
        cases = (
            (2.0, (1, 1, 1), 1, 0),
            (-2.0, (0, 1, 1), 0, 1),
        )
        for coefficient, source_values, valid_ancilla, invalid_ancilla in cases:
            variables = ("x", "y", "z")
            below = reduce_cubic_monomial(variables, coefficient=coefficient, penalty=1.999999)
            equal = reduce_cubic_monomial(variables, coefficient=coefficient, penalty=2.0)
            above = reduce_cubic_monomial(variables, coefficient=coefficient, penalty=2.000001)
            source = dict(zip(variables, source_values))
            below_valid = direct_qubo_energy(below, {**source, below.ancilla: valid_ancilla})
            below_invalid = direct_qubo_energy(below, {**source, below.ancilla: invalid_ancilla})
            self.assertLess(below_invalid, below_valid)
            equal_valid = direct_qubo_energy(equal, {**source, equal.ancilla: valid_ancilla})
            equal_invalid = direct_qubo_energy(equal, {**source, equal.ancilla: invalid_ancilla})
            self.assertEqual(equal_valid, equal_invalid)
            above_valid = direct_qubo_energy(above, {**source, above.ancilla: valid_ancilla})
            above_invalid = direct_qubo_energy(above, {**source, above.ancilla: invalid_ancilla})
            self.assertLess(above_valid, above_invalid)
            self.assertEqual(below.penalty_policy.status, "inadequate")
            self.assertEqual(equal.penalty_policy.status, "adequate_at_energy_boundary")
            self.assertEqual(above.penalty_policy.status, "proved_ancilla_unique")
            self.assertEqual(equal.decode({**source, equal.ancilla: valid_ancilla}), source)
            with self.assertRaises(ValueError):
                equal.decode({**source, equal.ancilla: invalid_ancilla})

    def test_one_ulp_strict_margin_is_not_a_binary64_uniqueness_certificate(self) -> None:
        """The policy proof is exact-arithmetic, not a promise about cancellation."""
        encoding = reduce_cubic_monomial(
            ("x", "y", "z"),
            coefficient=2.0,
            penalty=math.nextafter(2.0, math.inf),
            offset=-1.75,
        )
        source = {"x": 1, "y": 1, "z": 1}
        invalid_energy = direct_qubo_energy(encoding, {**source, encoding.ancilla: 0})
        valid_energy = direct_qubo_energy(encoding, {**source, encoding.ancilla: 1})
        self.assertEqual(encoding.penalty_policy.status, "proved_ancilla_unique")
        self.assertEqual(encoding.penalty_policy.certificate_arithmetic, "exact")
        self.assertEqual(
            encoding.penalty_policy.finite_precision_guarantee,
            "not_universally_certified",
        )
        self.assertIn("exact arithmetic", encoding.penalty_policy.proof_scope)
        self.assertEqual(invalid_energy, valid_energy)

    def test_qubo_binary_spin_and_ising_energies_include_the_source_offset(self) -> None:
        encoding = reduce_cubic_monomial(
            ("x", "y", "z"),
            coefficient=-3.5,
            penalty=4.0,
            offset=2.25,
        )
        for values in itertools.product((0, 1), repeat=4):
            bits = dict(zip(encoding.variables, values))
            spins = {variable: 2 * bit - 1 for variable, bit in bits.items()}
            expected = direct_qubo_energy(encoding, bits)
            self.assertEqual(encoding.qubo_energy(bits), expected)
            self.assertEqual(encoding.qubo_energy(spins, vartype="SPIN"), expected)
            self.assertEqual(encoding.ising_model.energy(bits, vartype="BINARY"), expected)
            self.assertEqual(encoding.ising_model.energy(spins), expected)
        self.assertEqual(encoding.ising_model.metadata["source_offset"], 2.25)
        self.assertEqual(encoding.ising_model.metadata["penalty_policy"]["status"], "proved_ancilla_unique")
        self.assertEqual(
            encoding.ising_model.metadata["penalty_policy"]["finite_precision_guarantee"],
            "not_universally_certified",
        )

    def test_exact_typed_relabeling_preserves_the_complete_lowered_truth_table(self) -> None:
        original = reduce_cubic_monomial(
            ("x", "y", "z"),
            coefficient=-2.25,
            penalty=3.0,
            offset=0.75,
        )
        relabeled = reduce_cubic_monomial(
            (b"x", ("typed", 2), frozenset({"z"})),
            coefficient=-2.25,
            penalty=3.0,
            offset=0.75,
        )

        for values in itertools.product((0, 1), repeat=4):
            original_bits = dict(zip(original.variables, values))
            relabeled_bits = dict(zip(relabeled.variables, values))
            self.assertEqual(
                direct_qubo_energy(original, original_bits),
                direct_qubo_energy(relabeled, relabeled_bits),
            )

    def test_bounded_interface_rejects_wrong_arity_duplicate_labels_and_boolean_numbers(self) -> None:
        with self.assertRaises(ValueError):
            reduce_cubic_monomial(("x", "y"), coefficient=1.0, penalty=2.0)
        with self.assertRaises(ValueError):
            reduce_cubic_monomial(("x", "x", "z"), coefficient=1.0, penalty=2.0)
        with self.assertRaises(ValueError):
            reduce_cubic_monomial((True, 1, "z"), coefficient=1.0, penalty=2.0)
        with self.assertRaises(ValueError):
            reduce_cubic_monomial(("x", "y", "z"), coefficient=True, penalty=2.0)
        with self.assertRaises(ValueError):
            reduce_cubic_monomial(("x", "y", "z"), coefficient=1.0, penalty=True)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
