"""Focused invariants for optimization-only isoenergetic cluster moves."""

from __future__ import annotations

import itertools
import math
import random
import sys
import unittest
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.cluster_moves import isoenergetic_cluster_move  # noqa: E402
from gibbsiq.model import IsingModel  # noqa: E402


class _AliasMapping(Mapping):
    """Mapping that can expose equality-alias keys a dict would collapse."""

    def __init__(self, items):
        self._items = tuple(items)

    def __iter__(self):
        return iter(key for key, _ in self._items)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, requested):
        for key, value in self._items:
            if type(key) is type(requested) and key == requested:
                return value
        raise KeyError(requested)


class IsoenergeticClusterMoveTests(unittest.TestCase):
    @staticmethod
    def _model(
        *,
        variables=("a", "b", "c", "d"),
        linear=None,
        quadratic=None,
        offset=0.0,
    ) -> IsingModel:
        return IsingModel(
            variables=tuple(variables),
            linear={} if linear is None else linear,
            quadratic={} if quadratic is None else quadratic,
            offset=offset,
        )

    def test_combined_pair_energy_is_invariant_with_fields_and_offset(self) -> None:
        model = self._model(
            linear={"a": 1.75, "b": -0.5, "c": 2.25, "d": -3.0},
            quadratic={
                ("a", "b"): 1.25,
                ("b", "c"): -2.0,
                ("c", "d"): 0.75,
                ("a", "d"): -1.5,
            },
            offset=9.5,
        )
        replica_a = {"a": 1, "b": 1, "c": -1, "d": 1}
        replica_b = {"a": -1, "b": -1, "c": 1, "d": 1}

        move = isoenergetic_cluster_move(
            model,
            replica_a,
            replica_b,
            component_index=0,
        )

        self.assertTrue(move.applied)
        self.assertEqual(move.selected_component, ("a", "b", "c"))
        self.assertGreater(move.selected_component_size, len(model.variables) / 2)
        self.assertEqual(dict(move.replica_a), {"a": -1, "b": -1, "c": 1, "d": 1})
        self.assertEqual(dict(move.replica_b), {"a": 1, "b": 1, "c": -1, "d": 1})
        self.assertAlmostEqual(move.combined_energy_before, move.combined_energy_after, places=12)
        self.assertAlmostEqual(move.combined_energy_residual, 0.0, places=12)
        self.assertTrue(move.combined_energy_invariant)
        self.assertEqual(move.energy_before, (model.energy(replica_a), model.energy(replica_b)))
        self.assertEqual(
            move.energy_after,
            (model.energy(move.replica_a), model.energy(move.replica_b)),
        )

        metadata = move.to_metadata()
        self.assertEqual(metadata["semantics"], "optimization_only_replica_coupling")
        self.assertIs(metadata["replicas_are_independent"], False)
        self.assertIs(metadata["same_temperature_required"], True)
        self.assertEqual(metadata["combined_energy_tolerance"], 1e-9)
        self.assertIs(metadata["combined_energy_invariant"], True)

    def test_same_component_applied_twice_is_an_involution(self) -> None:
        model = self._model(
            quadratic={("a", "b"): -1.0, ("c", "d"): 2.0},
        )
        original_a = {"a": 1, "b": -1, "c": 1, "d": 1}
        original_b = {"a": -1, "b": 1, "c": -1, "d": -1}

        first = isoenergetic_cluster_move(
            model,
            original_a,
            original_b,
            component_index=1,
        )
        second = isoenergetic_cluster_move(
            model,
            first.replica_a,
            first.replica_b,
            component_index=1,
        )

        self.assertEqual(first.components, (("a", "b"), ("c", "d")))
        self.assertEqual(second.selected_component, first.selected_component)
        self.assertEqual(dict(second.replica_a), original_a)
        self.assertEqual(dict(second.replica_b), original_b)

    def test_identical_replicas_are_a_deterministic_no_op(self) -> None:
        model = self._model(
            linear={"a": 1.0},
            quadratic={("a", "b"): 2.0},
            offset=-4.0,
        )
        sample = {"a": 1, "b": -1, "c": 1, "d": -1}

        move = isoenergetic_cluster_move(model, sample, dict(sample))

        self.assertFalse(move.applied)
        self.assertEqual(move.reason, "replicas_identical")
        self.assertEqual(move.disagreement_variables, ())
        self.assertEqual(move.components, ())
        self.assertIsNone(move.selected_component_index)
        self.assertEqual(move.selection_method, "none")
        self.assertEqual(dict(move.replica_a), sample)
        self.assertEqual(dict(move.replica_b), sample)
        self.assertEqual(move.energy_before, move.energy_after)
        self.assertEqual(move.combined_energy_residual, 0.0)

    def test_disconnected_disagreement_components_are_separate(self) -> None:
        model = self._model(
            quadratic={("a", "b"): 1.0, ("c", "d"): -1.0},
        )
        replica_a = {"a": 1, "b": 1, "c": 1, "d": -1}
        replica_b = {"a": -1, "b": -1, "c": -1, "d": 1}

        move = isoenergetic_cluster_move(
            model,
            replica_a,
            replica_b,
            component_index=1,
        )

        self.assertEqual(move.disagreement_variables, ("a", "b", "c", "d"))
        self.assertEqual(move.components, (("a", "b"), ("c", "d")))
        self.assertEqual(move.selected_component, ("c", "d"))
        self.assertEqual(dict(move.replica_a), {"a": 1, "b": 1, "c": -1, "d": 1})
        self.assertEqual(dict(move.replica_b), {"a": -1, "b": -1, "c": 1, "d": -1})

    def test_mixed_type_variable_labels_follow_model_order(self) -> None:
        tuple_label = ("node", 2)
        variables = (tuple_label, 7, "alpha")
        model = self._model(
            variables=variables,
            linear={tuple_label: 0.5, 7: -1.5, "alpha": 2.0},
            quadratic={(tuple_label, 7): 3.0, (7, "alpha"): -0.25},
        )
        replica_a = {tuple_label: 1, 7: -1, "alpha": 1}
        replica_b = {tuple_label: -1, 7: 1, "alpha": -1}

        move = isoenergetic_cluster_move(
            model,
            replica_a,
            replica_b,
            component_index=0,
        )

        self.assertEqual(move.disagreement_variables, variables)
        self.assertEqual(move.components, (variables,))
        self.assertEqual(move.selected_component, variables)
        self.assertTrue(move.combined_energy_invariant)

    def test_seed_and_injected_rng_are_reproducible(self) -> None:
        model = self._model()
        replica_a = {variable: 1 for variable in model.variables}
        replica_b = {variable: -1 for variable in model.variables}

        seeded_first = isoenergetic_cluster_move(model, replica_a, replica_b, seed=47)
        seeded_second = isoenergetic_cluster_move(model, replica_a, replica_b, seed=47)
        rng_first = isoenergetic_cluster_move(
            model,
            replica_a,
            replica_b,
            rng=random.Random(91),
        )
        rng_second = isoenergetic_cluster_move(
            model,
            replica_a,
            replica_b,
            rng=random.Random(91),
        )

        self.assertEqual(seeded_first.components, (("a",), ("b",), ("c",), ("d",)))
        self.assertEqual(seeded_first.selected_component_index, seeded_second.selected_component_index)
        self.assertEqual(dict(seeded_first.replica_a), dict(seeded_second.replica_a))
        self.assertEqual(seeded_first.selection_method, "seed")
        self.assertEqual(seeded_first.seed, 47)
        self.assertEqual(rng_first.selected_component_index, rng_second.selected_component_index)
        self.assertEqual(dict(rng_first.replica_b), dict(rng_second.replica_b))
        self.assertEqual(rng_first.selection_method, "rng")
        self.assertIsNone(rng_first.seed)

    def test_inputs_are_not_mutated_and_outputs_are_immutable(self) -> None:
        model = self._model(quadratic={("a", "b"): 1.0})
        replica_a = {"a": 1, "b": -1, "c": 1, "d": 1}
        replica_b = {"a": -1, "b": 1, "c": 1, "d": 1}
        before_a = dict(replica_a)
        before_b = dict(replica_b)

        move = isoenergetic_cluster_move(
            model,
            replica_a,
            replica_b,
            component_index=0,
        )

        self.assertEqual(replica_a, before_a)
        self.assertEqual(replica_b, before_b)
        self.assertIsNot(move.replica_a, replica_a)
        self.assertIsNot(move.replica_b, replica_b)
        with self.assertRaises(TypeError):
            move.replica_a["a"] = 1  # type: ignore[index]

    def test_rejects_invalid_model_samples_and_selectors(self) -> None:
        model = self._model(quadratic={("a", "b"): 1.0})
        replica_a = {"a": 1, "b": -1, "c": 1, "d": 1}
        replica_b = {"a": -1, "b": 1, "c": 1, "d": 1}

        with self.subTest("model type"):
            with self.assertRaises(TypeError):
                isoenergetic_cluster_move(object(), replica_a, replica_b, seed=1)  # type: ignore[arg-type]
        with self.subTest("mapping type"):
            with self.assertRaises(TypeError):
                isoenergetic_cluster_move(model, [1, -1, 1, 1], replica_b, seed=1)  # type: ignore[arg-type]
        with self.subTest("missing variable"):
            invalid = dict(replica_a)
            del invalid["d"]
            with self.assertRaisesRegex(ValueError, "missing"):
                isoenergetic_cluster_move(model, invalid, replica_b, seed=1)
        with self.subTest("extra variable"):
            invalid = dict(replica_a, extra=-1)
            with self.assertRaisesRegex(ValueError, "extra"):
                isoenergetic_cluster_move(model, invalid, replica_b, seed=1)
        with self.subTest("extra equality-alias variable"):
            boolean_model = self._model(variables=(True,))
            invalid = _AliasMapping(((True, 1), (1, -1)))
            with self.assertRaisesRegex(ValueError, "extra"):
                isoenergetic_cluster_move(
                    boolean_model,
                    invalid,
                    {True: -1},
                    component_index=0,
                )
        for invalid_spin in (True, False, 0, 2):
            with self.subTest(invalid_spin=invalid_spin):
                invalid = dict(replica_a, a=invalid_spin)
                with self.assertRaises(ValueError):
                    isoenergetic_cluster_move(model, invalid, replica_b, seed=1)
        with self.subTest("selector required"):
            with self.assertRaisesRegex(ValueError, "provide rng"):
                isoenergetic_cluster_move(model, replica_a, replica_b)
        with self.subTest("rng and seed conflict"):
            with self.assertRaises(ValueError):
                isoenergetic_cluster_move(
                    model,
                    replica_a,
                    replica_b,
                    rng=random.Random(1),
                    seed=1,
                )
        with self.subTest("seed and forced index conflict"):
            with self.assertRaises(ValueError):
                isoenergetic_cluster_move(
                    model,
                    replica_a,
                    replica_b,
                    seed=1,
                    component_index=0,
                )
        for invalid_index in (-1, 1):
            with self.subTest(invalid_index=invalid_index):
                with self.assertRaisesRegex(ValueError, "component_index"):
                    isoenergetic_cluster_move(
                        model,
                        replica_a,
                        replica_b,
                        component_index=invalid_index,
                    )
        with self.subTest("forced selection from identical replicas"):
            with self.assertRaisesRegex(ValueError, "identical replicas"):
                isoenergetic_cluster_move(
                    model,
                    replica_a,
                    replica_a,
                    component_index=0,
                )
        with self.subTest("bool component index"):
            with self.assertRaises(TypeError):
                isoenergetic_cluster_move(
                    model,
                    replica_a,
                    replica_b,
                    component_index=True,
                )
        with self.subTest("bool seed"):
            with self.assertRaises(TypeError):
                isoenergetic_cluster_move(model, replica_a, replica_b, seed=True)
        with self.subTest("rng type"):
            with self.assertRaises(TypeError):
                isoenergetic_cluster_move(
                    model,
                    replica_a,
                    replica_b,
                    rng=object(),  # type: ignore[arg-type]
                )

    def test_metadata_combined_energy_uses_stable_pair_sum(self) -> None:
        model = self._model(
            linear={"a": 0.1, "b": 0.2},
            quadratic={("a", "b"): 0.3},
            offset=0.4,
        )
        replica_a = {"a": 1, "b": -1, "c": 1, "d": 1}
        replica_b = {"a": -1, "b": 1, "c": 1, "d": 1}

        move = isoenergetic_cluster_move(
            model,
            replica_a,
            replica_b,
            component_index=0,
        )

        self.assertEqual(move.combined_energy_before, math.fsum(move.energy_before))
        self.assertEqual(move.combined_energy_after, math.fsum(move.energy_after))

    def test_exhaustive_pair_energy_invariance_for_every_component(self) -> None:
        model = self._model(
            linear={"a": 0.25, "b": -0.5, "c": 0.75, "d": -1.0},
            quadratic={
                ("a", "b"): 1.25,
                ("b", "c"): -1.5,
                ("c", "d"): 1.75,
                ("a", "d"): -2.0,
            },
            offset=1.125,
        )
        assignments = [
            dict(zip(model.variables, values))
            for values in itertools.product((-1, 1), repeat=len(model.variables))
        ]
        checked_moves = 0

        for replica_a in assignments:
            for replica_b in assignments:
                if replica_a == replica_b:
                    continue
                discovery = isoenergetic_cluster_move(
                    model,
                    replica_a,
                    replica_b,
                    component_index=0,
                )
                for component_index, component in enumerate(discovery.components):
                    with self.subTest(
                        replica_a=replica_a,
                        replica_b=replica_b,
                        component_index=component_index,
                    ):
                        move = isoenergetic_cluster_move(
                            model,
                            replica_a,
                            replica_b,
                            component_index=component_index,
                        )
                        expected_before = math.fsum((model.energy(replica_a), model.energy(replica_b)))
                        expected_after = math.fsum(
                            (model.energy(move.replica_a), model.energy(move.replica_b))
                        )
                        self.assertEqual(move.selected_component, component)
                        self.assertAlmostEqual(expected_before, expected_after, places=12)
                        self.assertAlmostEqual(move.combined_energy_residual, 0.0, places=12)
                        for variable in model.variables:
                            expected_multiplier = -1 if variable in component else 1
                            self.assertEqual(
                                move.replica_a[variable],
                                expected_multiplier * replica_a[variable],
                            )
                            self.assertEqual(
                                move.replica_b[variable],
                                expected_multiplier * replica_b[variable],
                            )
                        checked_moves += 1

        self.assertGreater(checked_moves, 0)


if __name__ == "__main__":
    unittest.main()
