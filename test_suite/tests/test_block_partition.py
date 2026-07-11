"""Graph-coloring block partition tests (pure stdlib; no thrml extra required)."""

from __future__ import annotations

import itertools
import random
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq import (  # noqa: E402
    BlockPartition,
    color_blocks,
    compile_ising,
    graph_density,
    validate_partition,
)

SEEDS = (3, 17, 91)


def random_model(seed: int, variable_count: int = 8, edge_probability: float = 0.4):
    rng = random.Random(seed)
    variables = tuple(f"v{i}" for i in range(variable_count))
    h = {variable: rng.uniform(-1.0, 1.0) for variable in variables}
    J = {
        pair: rng.uniform(-1.0, 1.0)
        for pair in itertools.combinations(variables, 2)
        if rng.random() < edge_probability
    }
    return compile_ising(h, J)


class ColoringValidityTests(unittest.TestCase):
    def test_every_variable_appears_exactly_once(self) -> None:
        for seed in SEEDS:
            model = random_model(seed)
            partition = color_blocks(model)
            placed = [variable for block in partition.blocks for variable in block]
            self.assertEqual(sorted(placed), sorted(model.variables), msg=f"seed={seed}")
            self.assertEqual(len(placed), len(set(placed)), msg=f"seed={seed}")

    def test_no_coupled_pair_shares_a_block(self) -> None:
        for seed in SEEDS:
            model = random_model(seed)
            partition = color_blocks(model)
            validate_partition(model, partition)

    def test_coloring_is_deterministic(self) -> None:
        for seed in SEEDS:
            first = color_blocks(random_model(seed))
            second = color_blocks(random_model(seed))
            self.assertEqual(first, second, msg=f"seed={seed}")


class ColoringStructureTests(unittest.TestCase):
    def test_complete_graph_uses_one_block_per_variable(self) -> None:
        variables = tuple(f"k{i}" for i in range(5))
        model = compile_ising(
            {variable: 0.0 for variable in variables},
            {pair: 1.0 for pair in itertools.combinations(variables, 2)},
        )
        partition = color_blocks(model)
        self.assertEqual(partition.num_blocks, len(variables))
        self.assertEqual(partition.block_sizes, (1,) * len(variables))

    def test_no_couplings_yields_single_block(self) -> None:
        model = compile_ising({"a": 0.5, "b": -0.5, "c": 1.0})
        partition = color_blocks(model)
        self.assertEqual(partition.num_blocks, 1)
        self.assertEqual(partition.blocks[0], model.variables)

    def test_path_graph_uses_two_blocks(self) -> None:
        model = compile_ising(
            {i: 0.0 for i in range(6)},
            {(i, i + 1): 1.0 for i in range(5)},
        )
        partition = color_blocks(model)
        self.assertEqual(partition.num_blocks, 2)
        validate_partition(model, partition)

    def test_grid_graph_uses_two_blocks(self) -> None:
        variables = tuple((row, column) for row in range(4) for column in range(5))
        edges = {}
        for row, column in variables:
            if row + 1 < 4:
                edges[((row, column), (row + 1, column))] = 1.0
            if column + 1 < 5:
                edges[((row, column), (row, column + 1))] = 1.0
        model = compile_ising({variable: 0.0 for variable in variables}, edges, variables=variables)
        partition = color_blocks(model)
        self.assertEqual(partition.num_blocks, 2)
        validate_partition(model, partition)


class DsaturEdgeCaseTests(unittest.TestCase):
    """Canonical coloring instances from the graph-coloring literature."""

    def test_crown_graph_two_colors_adversarial_order(self) -> None:
        # Crown graph S_3^0 (K_{3,3} minus a perfect matching): interleaved
        # variable order defeats naive sequential greedy (3 colors); DSATUR
        # finds the optimal 2-coloring.
        variables = ("a0", "b0", "a1", "b1", "a2", "b2")
        edges = {(f"a{i}", f"b{j}"): 1.0 for i in range(3) for j in range(3) if i != j}
        model = compile_ising({variable: 0.0 for variable in variables}, edges, variables=variables)
        partition = color_blocks(model)
        self.assertEqual(partition.num_blocks, 2)
        validate_partition(model, partition)

    def test_odd_cycle_needs_three_colors(self) -> None:
        model = compile_ising(
            {i: 0.0 for i in range(5)},
            {(i, (i + 1) % 5): 1.0 for i in range(5)},
        )
        partition = color_blocks(model)
        self.assertEqual(partition.num_blocks, 3)
        validate_partition(model, partition)

    def test_star_graph_separates_center_from_leaves(self) -> None:
        model = compile_ising(
            {i: 0.0 for i in range(6)},
            {(0, leaf): 1.0 for leaf in range(1, 6)},
        )
        partition = color_blocks(model)
        self.assertEqual(partition.num_blocks, 2)
        self.assertEqual(set(partition.block_sizes), {1, 5})
        validate_partition(model, partition)

    def test_isolated_variable_joins_an_existing_block(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0, "c": 0.0}, {("a", "b"): 1.0})
        partition = color_blocks(model)
        self.assertEqual(partition.num_blocks, 2)
        validate_partition(model, partition)

    def test_coefficient_scaling_preserves_partition(self) -> None:
        variables = tuple(range(6))
        edges = {(i, (i + 1) % 6): 1.0 for i in variables}
        scaled_edges = {edge: -7.5 for edge in edges}
        base = compile_ising({variable: 0.0 for variable in variables}, edges)
        scaled = compile_ising({variable: 3.0 for variable in variables}, scaled_edges)
        self.assertEqual(color_blocks(base), color_blocks(scaled))


class ValidatePartitionTests(unittest.TestCase):
    def test_rejects_missing_variable(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): 1.0})
        with self.assertRaises(ValueError):
            validate_partition(model, BlockPartition(blocks=(("a",),)))

    def test_rejects_unknown_variable(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): 1.0})
        with self.assertRaises(ValueError):
            validate_partition(model, BlockPartition(blocks=(("a",), ("b", "c"))))

    def test_rejects_duplicate_placement(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): 1.0})
        with self.assertRaises(ValueError):
            validate_partition(model, BlockPartition(blocks=(("a", "b"), ("a",))))

    def test_rejects_coupled_pair_in_one_block(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): 1.0})
        with self.assertRaises(ValueError):
            validate_partition(model, BlockPartition(blocks=(("a", "b"),)))

    def test_accepts_singleton_partition(self) -> None:
        model = random_model(SEEDS[0])
        singletons = BlockPartition(
            blocks=tuple((variable,) for variable in model.variables), strategy="singleton"
        )
        validate_partition(model, singletons)


class MetadataTests(unittest.TestCase):
    def test_partition_metadata_keys(self) -> None:
        partition = color_blocks(random_model(SEEDS[0]))
        metadata = partition.to_metadata()
        self.assertEqual(metadata["block_strategy"], "dsatur-coloring")
        self.assertEqual(metadata["num_blocks"], partition.num_blocks)
        self.assertEqual(metadata["block_sizes"], list(partition.block_sizes))

    def test_graph_density(self) -> None:
        self.assertEqual(graph_density(compile_ising({"a": 1.0})), 0.0)
        complete = compile_ising(
            {i: 0.0 for i in range(4)},
            {pair: 1.0 for pair in itertools.combinations(range(4), 2)},
        )
        self.assertAlmostEqual(graph_density(complete), 1.0)
        path = compile_ising({i: 0.0 for i in range(4)}, {(i, i + 1): 1.0 for i in range(3)})
        self.assertAlmostEqual(graph_density(path), 0.5)


if __name__ == "__main__":
    unittest.main()
