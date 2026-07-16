"""Regression tests for deterministic ground-truth generation."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = REPO_ROOT / "tools" / "generate_ground_truth.py"
CORPUS_PATH = REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_ground_truth", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def with_checksum(generator, document: dict) -> dict:
    result = dict(document)
    result["content_sha256"] = generator.checksum(document)
    return result


class GroundTruthGeneratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = load_generator()
        self.fixture_document = json.loads(CORPUS_PATH.read_text(encoding="utf-8-sig"))

    def test_build_corpus_reproduces_checked_in_fixture(self) -> None:
        generated = with_checksum(self.generator, self.generator.build_corpus())
        self.assertEqual(generated, self.fixture_document)

    def test_main_write_output_preserves_fixture_path(self) -> None:
        before = CORPUS_PATH.read_text(encoding="utf-8-sig")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "ground-truth-small.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = self.generator.main(["--out", str(out_path)])
            self.assertEqual(exit_code, 0)
            self.assertIn("wrote 27 fixtures", stdout.getvalue())
            written = json.loads(out_path.read_text(encoding="utf-8"))
        after = CORPUS_PATH.read_text(encoding="utf-8-sig")

        self.assertEqual(before, after)
        self.assertEqual(written, self.fixture_document)

    def test_structured_closed_form_instances_remain_in_corpus(self) -> None:
        by_id = {fixture["id"]: fixture for fixture in self.fixture_document["fixtures"]}
        cases = {
            "gt_maxcut_complete_k7": 12,
            "gt_maxcut_cycle_c6": 6,
            "gt_maxcut_cycle_c7": 6,
            "gt_maxcut_bipartite_k33": 9,
            "gt_maxcut_hypercube_q3": 12,
            "gt_maxcut_petersen": 12,
        }
        for fixture_id, optimum in cases.items():
            with self.subTest(fixture=fixture_id):
                fixture = by_id[fixture_id]
                self.assertEqual(
                    fixture["provenance"]["method"],
                    "closed_form_with_enumeration_crosscheck",
                )
                self.assertEqual(fixture["expected"]["best_cut_value"], optimum)

    def test_path_graph_has_n_minus_one_edges_and_full_maxcut(self) -> None:
        for num_vertices in range(1, 9):
            with self.subTest(num_vertices=num_vertices):
                edges = self.generator.path_graph_edges(num_vertices)
                self.assertEqual(len(edges), num_vertices - 1)
                self.assertEqual(edges, [(index, index + 1) for index in range(num_vertices - 1)])
                solved = self.generator.solve_maxcut(num_vertices, edges)
                self.assertEqual(solved["num_edges"], num_vertices - 1)
                self.assertEqual(solved["best_cut_value"], num_vertices - 1)

    def test_knapsack_optimal_weight_is_a_tie_breaking_contract(self) -> None:
        solved = self.generator.solve_knapsack([1, 2], [5, 5], capacity=2)

        self.assertEqual(solved["max_value"], 5)
        self.assertEqual(solved["weight_at_optimum"], 1)
        self.assertEqual(solved["num_optimal_selections"], 1)
        self.assertEqual(solved["witness_selections"], [[0]])

    def test_generic_ising_solver_does_not_round_ground_energy_to_six_decimals(self) -> None:
        solved = self.generator.solve_ising(1, {}, {0: 0.1234567894})

        self.assertEqual(solved["ground_state_energy"], -0.1234567894)
        self.assertLess(abs(solved["ground_state_energy"] - (-0.1234567894)), 1e-9)


if __name__ == "__main__":
    unittest.main()
