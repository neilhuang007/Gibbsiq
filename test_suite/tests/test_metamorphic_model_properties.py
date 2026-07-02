"""Metamorphic invariants for the Ising IR: relabeling, offset shift, spin gauge.

Fixture tests pin exact values for hand-picked instances; these property checks
assert transformations that must hold for every assignment of every instance.
They are the Stage 1 carry-over items tracked in the roadmap.
"""

from __future__ import annotations

import itertools
import math
import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import compile_ising  # noqa: E402

TOLERANCE = 1e-9
VARIABLE_COUNT = 4
SEEDS = (11, 23, 47)


def random_ising_fields(seed: int, variables: tuple[str, ...]) -> tuple[dict, dict, float]:
    """Return seeded (h, J, offset) with a dense-ish random coupling graph."""
    rng = random.Random(seed)
    h = {variable: rng.uniform(-2.0, 2.0) for variable in variables}
    J = {
        pair: rng.uniform(-2.0, 2.0)
        for pair in itertools.combinations(variables, 2)
        if rng.random() < 0.7
    }
    return h, J, rng.uniform(-3.0, 3.0)


def all_spin_assignments(variables: tuple[str, ...]):
    for values in itertools.product((-1, 1), repeat=len(variables)):
        yield dict(zip(variables, values))


class RelabelingInvarianceTests(unittest.TestCase):
    """A bijective renaming of variables must not change any energy."""

    def test_energy_is_invariant_under_variable_relabeling(self) -> None:
        variables = tuple(f"x{i}" for i in range(VARIABLE_COUNT))
        relabel = {variable: f"renamed_{variable}" for variable in variables}
        for seed in SEEDS:
            h, J, offset = random_ising_fields(seed, variables)
            model = compile_ising(h, J, offset=offset)
            relabeled_model = compile_ising(
                {relabel[variable]: bias for variable, bias in h.items()},
                {(relabel[u], relabel[v]): coupling for (u, v), coupling in J.items()},
                offset=offset,
            )
            for sample in all_spin_assignments(variables):
                relabeled_sample = {relabel[variable]: spin for variable, spin in sample.items()}
                self.assertTrue(
                    math.isclose(
                        model.energy(sample),
                        relabeled_model.energy(relabeled_sample),
                        abs_tol=TOLERANCE,
                    ),
                    msg=f"seed={seed} sample={sample}",
                )


class OffsetShiftTests(unittest.TestCase):
    """Adding a constant to the offset shifts every energy by exactly that constant."""

    def test_offset_shift_moves_all_energies_uniformly(self) -> None:
        variables = tuple(f"x{i}" for i in range(VARIABLE_COUNT))
        shift = 7.25
        for seed in SEEDS:
            h, J, offset = random_ising_fields(seed, variables)
            model = compile_ising(h, J, offset=offset)
            shifted_model = compile_ising(h, J, offset=offset + shift)
            for sample in all_spin_assignments(variables):
                self.assertTrue(
                    math.isclose(
                        shifted_model.energy(sample),
                        model.energy(sample) + shift,
                        abs_tol=TOLERANCE,
                    ),
                    msg=f"seed={seed} sample={sample}",
                )

    def test_offset_does_not_affect_gibbs_conditionals(self) -> None:
        variables = tuple(f"x{i}" for i in range(VARIABLE_COUNT))
        for seed in SEEDS:
            h, J, offset = random_ising_fields(seed, variables)
            model = compile_ising(h, J, offset=offset)
            shifted_model = compile_ising(h, J, offset=offset + 100.0)
            sample = next(all_spin_assignments(variables))
            for variable in variables:
                self.assertTrue(
                    math.isclose(
                        model.conditional_probability(variable, sample, beta=1.3),
                        shifted_model.conditional_probability(variable, sample, beta=1.3),
                        abs_tol=TOLERANCE,
                    ),
                    msg=f"seed={seed} variable={variable}",
                )


class SpinGaugeTests(unittest.TestCase):
    """Flipping spins in a set F, with h and boundary couplings negated, preserves energy.

    For the gauge transform over a flip set F: ``h'_i = -h_i`` for ``i`` in F,
    ``J'_ij = -J_ij`` when exactly one endpoint is in F, and the transformed
    sample flips exactly the spins in F. The audited energy convention demands
    ``E'(gauge(s)) == E(s)`` for every assignment; a sign error in either the
    linear or quadratic term breaks it.
    """

    def test_energy_is_invariant_under_spin_gauge_transform(self) -> None:
        variables = tuple(f"x{i}" for i in range(VARIABLE_COUNT))
        flip_sets = ({"x0"}, {"x1", "x3"}, set(variables))
        for seed, flipped in itertools.product(SEEDS, flip_sets):
            h, J, offset = random_ising_fields(seed, variables)
            gauged_h = {
                variable: -bias if variable in flipped else bias for variable, bias in h.items()
            }
            gauged_J = {
                (u, v): -coupling if (u in flipped) != (v in flipped) else coupling
                for (u, v), coupling in J.items()
            }
            model = compile_ising(h, J, offset=offset)
            gauged_model = compile_ising(gauged_h, gauged_J, offset=offset)
            for sample in all_spin_assignments(variables):
                gauged_sample = {
                    variable: -spin if variable in flipped else spin
                    for variable, spin in sample.items()
                }
                self.assertTrue(
                    math.isclose(
                        gauged_model.energy(gauged_sample),
                        model.energy(sample),
                        abs_tol=TOLERANCE,
                    ),
                    msg=f"seed={seed} flipped={sorted(flipped)} sample={sample}",
                )


if __name__ == "__main__":
    unittest.main()
