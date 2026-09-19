"""Public fixture-loading contracts, independent of a repository checkout."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.evaluation import load_fixture_sets, main  # noqa: E402


class EvaluationResourcesTest(unittest.TestCase):
    def test_default_corpus_contains_all_three_maintained_fixture_groups(self) -> None:
        corpus = load_fixture_sets()

        self.assertEqual(
            {group: len(ids) for group, ids in corpus["groups"].items()},
            {"exact": 5, "diagnostic": 7, "benchmark": 27},
        )
        # Independent closed forms: K3 has maximum cut 2; C4 is bipartite.
        self.assertEqual(corpus["fixtures"]["maxcut_triangle_unweighted"]["expected"]["best_cut_value"], 2)
        self.assertEqual(corpus["fixtures"]["maxcut_cycle4_unweighted"]["expected"]["best_cut_value"], 4)

    def test_cli_evaluates_explicit_inputs_without_adding_default_benchmarks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            documents = {
                "exact-small-instances.json": {
                    "schema_version": "custom",
                    "fixtures": [{"id": "one-spin", "expected": {"energy": -2.5}}],
                },
                "diagnostic-fixtures.json": {"schema_version": "custom", "fixtures": []},
                "benchmark.json": {"schema_version": "explicit-empty", "fixtures": []},
                "candidate.json": {"one-spin": {"energy": -2.5}},
            }
            for name, document in documents.items():
                (root / name).write_text(json.dumps(document), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                code = main(
                    [
                        str(root / "candidate.json"),
                        "--fixtures",
                        str(root),
                        "--benchmark",
                        str(root / "benchmark.json"),
                    ]
                )

        report = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(report["passed"])
        self.assertEqual(report["summary"]["total_fixtures"], 1)
        self.assertEqual(report["summary"]["passed"], 1)

    def test_missing_explicit_benchmark_is_not_silently_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                load_fixture_sets(benchmark_path=Path(directory) / "absent.json")

    def test_bundled_corpus_is_readable_from_zip_without_site_packages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "package.zip"
            with ZipFile(archive, "w") as bundle:
                for path in (REPO_ROOT / "src/gibbsiq").rglob("*"):
                    if path.suffix in {".py", ".json"}:
                        bundle.write(path, path.relative_to(REPO_ROOT / "src"))
            execution = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-c",
                    "import json, sys; sys.path.insert(0, sys.argv[1]); "
                    "from gibbsiq.evaluation import evaluate_candidate; "
                    "report = evaluate_candidate({}); "
                    "print(json.dumps({'summary': report['summary'], 'optional': "
                    "sorted(set(sys.modules) & {'numpy', 'jax', 'thrml', 'dimod', 'arviz', 'networkx'})}))",
                    str(archive),
                ],
                cwd=directory,
                text=True,
                capture_output=True,
                timeout=15,
            )

        self.assertEqual(execution.returncode, 0, execution.stdout + execution.stderr)
        result = json.loads(execution.stdout)
        self.assertEqual(result["summary"]["total_fixtures"], 39)
        self.assertEqual(result["summary"]["missing"], 39)
        self.assertEqual(result["optional"], [])


if __name__ == "__main__":
    unittest.main()
