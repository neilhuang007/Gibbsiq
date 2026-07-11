"""Contract tests ported from the vendored dimod suite.

Ported from ``test_suite/vendor/dimod/tests/test_bqm.py`` and ``test_sampleset.py``
(dimod commit ``bad4cba``); each case copies the numeric literal asserted by the
cited dimod test and re-expresses it against Gibbsiq's public API so a convention
drift shows up as a failure instead of a silent divergence. Dependency-free, and
complements the dimod-gated ``DimodConformanceTest`` in
``test_conversion_scenarios.py``, which cross-checks against a live dimod install.
``compile_qubo`` returns a SPIN ``IsingModel`` energy-equivalent to the input QUBO
under ``x = (s + 1) / 2``, so binary cases assert
``energy(sample, vartype="BINARY")`` rather than internal spin coefficients.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import IsingModel, SampleResult, compile_ising, compile_qubo  # noqa: E402


class PortedEnergyContractTest(unittest.TestCase):
    """Energy literals copied verbatim from dimod BQM/QM energy assertions."""

    def test_spin_two_path_all_assignments(self) -> None:
        # dimod test_bqm.py:1062-1070 -- h={0:.1,1:-.2}, J[(0,1)]=-1, samples
        # [[-1,-1],[-1,1],[1,-1],[1,1]] -> energies [-.9,.7,1.3,-1.1].
        model = compile_ising({0: 0.1, 1: -0.2}, {(0, 1): -1.0}, variables=[0, 1])
        cases = {
            (-1, -1): -0.9,
            (-1, 1): 0.7,
            (1, -1): 1.3,
            (1, 1): -1.1,
        }
        for (s0, s1), expected in cases.items():
            self.assertAlmostEqual(model.energy({0: s0, 1: s1}), expected, places=12)

    def test_binary_upper_triangular_ones_single_bit(self) -> None:
        # dimod test_bqm.py:1122-1127 -- triu(ones((5,5))) BINARY, sample
        # [0,0,1,0,0] -> energy == 1 (only the diagonal-as-linear term on var 2).
        qubo: dict[tuple[int, int], float] = {}
        for i in range(5):
            qubo[(i, i)] = 1.0
        for i in range(5):
            for j in range(i + 1, 5):
                qubo[(i, j)] = 1.0
        model = compile_qubo(qubo, variables=list(range(5)))
        sample = {0: 0, 1: 0, 2: 1, 3: 0, 4: 0}
        self.assertAlmostEqual(model.energy(sample, vartype="BINARY"), 1.0, places=12)

    def test_binary_offset_ignores_extra_sample_keys(self) -> None:
        # dimod test_bqm.py:1166-1169 -- linear a=1, quad (a,b)=1, offset 1.5;
        # energy({a:1,b:1,c:1})==3.5 and energy({a:1,b:0,c:1})==2.5 (extra key ignored).
        model = compile_qubo(
            {"linear": {"a": 1.0}, "quadratic": {("a", "b"): 1.0}, "offset": 1.5}
        )
        self.assertAlmostEqual(model.energy({"a": 1, "b": 1, "c": 1}, vartype="BINARY"), 3.5, places=12)
        self.assertAlmostEqual(model.energy({"a": 1, "b": 0, "c": 1}, vartype="BINARY"), 2.5, places=12)

    def test_binary_offset_all_assignments(self) -> None:
        # dimod test_bqm.py:1191-1199 -- linear a=1, quad (a,b)=2, offset 3;
        # samples [[0,0],[0,1],[1,0],[1,1]] -> energies [3,3,4,6].
        model = compile_qubo({"linear": {"a": 1.0}, "quadratic": {("a", "b"): 2.0}, "offset": 3.0})
        cases = {(0, 0): 3.0, (0, 1): 3.0, (1, 0): 4.0, (1, 1): 6.0}
        for (a, b), expected in cases.items():
            self.assertAlmostEqual(model.energy({"a": a, "b": b}, vartype="BINARY"), expected, places=12)

    def test_single_spin_binary_energy_mapping(self) -> None:
        # dimod test_quadratic_model.py:338-339 -- var a, linear 1.5; under BINARY
        # energy({a:1})==1.5, energy({a:0})==-1.5 (x=1->s=+1, x=0->s=-1).
        model = compile_ising({"a": 1.5})
        self.assertAlmostEqual(model.energy({"a": 1}, vartype="BINARY"), 1.5, places=12)
        self.assertAlmostEqual(model.energy({"a": 0}, vartype="BINARY"), -1.5, places=12)

    def test_empty_model_energy_is_offset(self) -> None:
        # dimod test_bqm.py:1113-1118 -- empty model energy == 0.
        self.assertEqual(IsingModel((), {}, {}).energy({}), 0.0)


class PortedSpinConventionTest(unittest.TestCase):
    """SPIN diagonal->offset and duplicate-pair summation (compile_ising is identity)."""

    @staticmethod
    def _ones_couplings(variables: list[int]) -> dict[tuple[int, int], float]:
        """Diagonal ones plus both off-diagonal triangles, i.e. dense ones((n,n))."""
        couplings: dict[tuple[int, int], float] = {}
        for i in variables:
            couplings[(i, i)] = 1.0
        for i in variables:
            for j in variables:
                if i < j:
                    couplings[(i, j)] = 1.0
                    couplings[(j, i)] = 1.0
        return couplings

    def test_spin_ones_matrix_folds_diagonal_to_offset(self) -> None:
        # dimod test_bqm.py:372-379 -- ones((5,5)) SPIN -> offset 5 (5 diagonal
        # spins fold to +1 each), every spin linear 0, every coupling 2 (both
        # triangles summed).
        variables = list(range(5))
        model = compile_ising(
            {i: 0.0 for i in variables}, self._ones_couplings(variables), variables=variables
        )
        self.assertEqual(model.offset, 5.0)
        self.assertEqual(set(model.linear.values()), {0.0})
        self.assertEqual(len(model.quadratic), 10)
        self.assertEqual(sorted(model.quadratic.values()), [2.0] * 10)

    def test_spin_linear_untouched_by_diagonal(self) -> None:
        # dimod test_bqm.py:394-402 -- linear ones + ones((5,5)) SPIN quadratic ->
        # offset 5, spin linear stays 1 (diagonal never enters spin linear), coupling 2.
        variables = list(range(5))
        model = compile_ising(
            {i: 1.0 for i in variables}, self._ones_couplings(variables), variables=variables
        )
        self.assertEqual(model.offset, 5.0)
        self.assertEqual(set(model.linear.values()), {1.0})
        self.assertEqual(sorted(model.quadratic.values()), [2.0] * 10)

    def test_spin_self_loop_is_constant_offset(self) -> None:
        # dimod test_bqm.py:2527 -- spin u*u == BQM({'u':0},{},1,SPIN): s^2==1, so a
        # spin self-loop folds to +offset and the energy is spin-independent.
        model = compile_ising({0: 0.0}, {(0, 0): 1.0}, variables=[0])
        self.assertEqual(model.offset, 1.0)
        self.assertEqual(model.quadratic, {})
        self.assertAlmostEqual(model.energy({0: 1}), 1.0, places=12)
        self.assertAlmostEqual(model.energy({0: -1}), 1.0, places=12)


class PortedBinaryConventionTest(unittest.TestCase):
    """BINARY diagonal->linear, duplicate-pair summation, and offset preservation."""

    def test_binary_single_diagonal_is_linear(self) -> None:
        # dimod test_bqm.py:364-368 -- [[1]] BINARY -> linear[0]==1.
        model = compile_qubo({(0, 0): 1.0})
        self.assertAlmostEqual(model.energy({0: 1}, vartype="BINARY"), 1.0, places=12)
        self.assertAlmostEqual(model.energy({0: 0}, vartype="BINARY"), 0.0, places=12)

    def test_binary_diagonal_adds_to_linear(self) -> None:
        # dimod test_bqm.py:383-390 -- linear ones + diagonal ones BINARY -> linear 2.
        # Structured QUBO: a separate linear 1 plus a diagonal (0,0)=1 sum to 2.
        model = compile_qubo({"linear": {0: 1.0}, "quadratic": {(0, 0): 1.0}})
        self.assertAlmostEqual(model.energy({0: 1}, vartype="BINARY"), 2.0, places=12)
        self.assertAlmostEqual(model.energy({0: 0}, vartype="BINARY"), 0.0, places=12)

    def test_binary_duplicate_pairs_are_summed(self) -> None:
        # dimod test_bqm.py:346-352 -- ones((5,5)) BINARY -> linear 1 (diagonal),
        # quadratic 2 (both triangles). With bits 0 and 1 set: linear 1+1 plus the
        # summed pair 2 == 4.
        qubo: dict[tuple[int, int], float] = {}
        for i in range(5):
            qubo[(i, i)] = 1.0
        for i in range(5):
            for j in range(i + 1, 5):
                qubo[(i, j)] = 1.0
                qubo[(j, i)] = 1.0
        model = compile_qubo(qubo, variables=list(range(5)))
        sample = {0: 1, 1: 1, 2: 0, 3: 0, 4: 0}
        self.assertAlmostEqual(model.energy(sample, vartype="BINARY"), 4.0, places=12)

    def test_qubo_diagonal_to_linear_offset_preserved(self) -> None:
        # dimod test_bqm.py:1440-1460 -- from_qubo({(0,0):-1,(0,1):-1,(0,2):-1,(1,2):1})
        # -> linear[0]==-1; offset 0 with no arg, 1.6 when passed. Offset preservation
        # through QUBO->Ising is Gibbsiq's most bug-prone contract.
        qubo = {(0, 0): -1.0, (0, 1): -1.0, (0, 2): -1.0, (1, 2): 1.0}
        model_zero = compile_qubo(qubo, variables=[0, 1, 2])
        self.assertEqual(model_zero.metadata["input_offset"], 0.0)
        self.assertAlmostEqual(model_zero.energy({0: 0, 1: 0, 2: 0}, vartype="BINARY"), 0.0, places=12)
        # diagonal (0,0) landed in linear: setting only bit 0 yields its -1 coefficient.
        self.assertAlmostEqual(model_zero.energy({0: 1, 1: 0, 2: 0}, vartype="BINARY"), -1.0, places=12)

        model_offset = compile_qubo(qubo, offset=1.6, variables=[0, 1, 2])
        self.assertAlmostEqual(model_offset.metadata["input_offset"], 1.6, places=12)
        self.assertAlmostEqual(model_offset.energy({0: 0, 1: 0, 2: 0}, vartype="BINARY"), 1.6, places=12)

    def test_binary_self_multiply_is_linear(self) -> None:
        # dimod test_bqm.py:2509 -- binary u*u == BQM({'u':1},{},0,BINARY): x^2==x.
        model = compile_qubo({(0, 0): 1.0})
        self.assertAlmostEqual(model.energy({0: 1}, vartype="BINARY"), 1.0, places=12)


class PortedBestSelectionTest(unittest.TestCase):
    """Lowest-energy selection over a small Ising model."""

    def test_lowest_energy_sample_is_selected(self) -> None:
        # dimod test_sampleset.py:981-989 -- J[(a,b)]=-1, samples
        # [{a:-1,b:1},{a:1,b:1}]; the lowest-energy sample is {a:1,b:1}.
        model = compile_ising({}, {("a", "b"): -1.0}, variables=["a", "b"])
        result = SampleResult.from_model(model, [{"a": -1, "b": 1}, {"a": 1, "b": 1}])
        self.assertEqual(result.best_sample, {"a": 1, "b": 1})
        self.assertEqual(result.best_index, 1)
        self.assertAlmostEqual(result.best_energy, -1.0, places=12)


class IntentionalDivergenceFromDimodTest(unittest.TestCase):
    """Cases where Gibbsiq deliberately differs from dimod; these pin the difference."""

    def test_empty_result_is_rejected(self) -> None:
        # dimod test_sampleset.py:300-304 allows a 0-sample SampleSet; Gibbsiq rejects
        # it at construction so no downstream layer receives an empty result.
        with self.assertRaisesRegex(ValueError, "at least one sample"):
            SampleResult(samples=(), variables=("a",), energies=())

    def test_ties_resolve_to_first_minimal_index(self) -> None:
        # dimod test_sampleset.py CS4 -- dimod's .first uses an unstable argsort, so the
        # winner among exactly-tied energies is unspecified; Gibbsiq guarantees the first
        # occurrence of the minimum (deterministic on degenerate optima).
        result = SampleResult(
            samples=({"a": 1}, {"a": -1}, {"a": 1}),
            variables=("a",),
            energies=(2.0, 2.0, 2.0),
        )
        self.assertEqual(result.best_index, 0)
        self.assertEqual(result.best_sample, {"a": 1})

    def test_vartype_defaults_to_spin(self) -> None:
        # dimod requires an explicit vartype on from_samples; Gibbsiq defaults to SPIN, so
        # a -1 value (legal only in SPIN) is accepted without specifying a vartype.
        result = SampleResult(samples=({"a": -1},), variables=("a",), energies=(0.0,))
        self.assertEqual(result.vartype, "SPIN")


if __name__ == "__main__":
    unittest.main()
