"""S09 command-line contract checks."""

from __future__ import annotations

import contextlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class CliContractTests(unittest.TestCase):
    def test_doctor_is_static_and_does_not_import_optional_modules_or_use_network(self) -> None:
        root = Path(__file__).resolve().parents[3]
        program = """
import builtins, json, socket, sys
sys.path.insert(0, sys.argv[1])
blocked = {'jax', 'jaxlib', 'equinox', 'numpy', 'thrml', 'torx'}
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in blocked:
        raise AssertionError('optional import: ' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
socket.socket = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network'))
from gibbsiq.qualification.cli import main
raise SystemExit(main(('doctor', '--json')))
"""
        completed = __import__("subprocess").run(
            [__import__("sys").executable, "-I", "-S", "-c", program, str(root / "src")],
            cwd=root,
            env={
                key: value
                for key, value in os.environ.items()
                if key.upper() not in {"PYTHONPATH", "PYTHONHOME"}
            },
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["package"]["name"], "gibbsiq")
        self.assertTrue(all("module_available" in item for item in payload["optional"]))
        self.assertEqual(
            {item["distribution"] for item in payload["optional"]},
            {"numpy", "jax", "jaxlib", "equinox", "thrml", "extro-torx", "z1t"},
        )
        self.assertIn("dy4p-conditional-iid-v1", {item["profile"] for item in payload["supported_profiles"]})
        self.assertGreater(payload["local_disk"]["free_bytes"], 0)

    def test_compare_exit_codes_distinguish_regression_and_incompatibility(self) -> None:
        from gibbsiq.qualification.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline, candidate = root / "baseline", root / "candidate"
            with contextlib.redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        (
                            "qualify",
                            "--example",
                            "spin-conditional",
                            "--runs",
                            "1024",
                            "--output",
                            str(baseline),
                        )
                    ),
                    0,
                )
                self.assertEqual(
                    main(
                        (
                            "qualify",
                            "--example",
                            "spin-conditional",
                            "--candidate",
                            "sign-reversed",
                            "--runs",
                            "256",
                            "--output",
                            str(candidate),
                        )
                    ),
                    1,
                )
            output = StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    (
                        "compare",
                        str(baseline),
                        str(candidate),
                        "--candidate-change",
                        "spin-conditional-sign-reversed-v1",
                        "--json",
                    )
                )
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output.getvalue())["outcome"], "regression")
            with contextlib.redirect_stdout(StringIO()):
                self.assertEqual(main(("compare", str(baseline), str(candidate))), 2)

    def test_actual_unsupported_evidence_and_terminal_exit_codes_remain_distinct(self) -> None:
        from gibbsiq.qualification.artifacts import record_to_dict
        from gibbsiq.qualification.cli import main
        from gibbsiq.qualification.contracts import ArtifactIdentity, canonical_json
        from gibbsiq.qualification.examples import spin_conditional_plan

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = record_to_dict(spin_conditional_plan(runs=1))
            payload["workload"]["candidate"] = record_to_dict(
                ArtifactIdentity("unknown-static-backend", "1", "sha256:" + "e" * 64)
            )
            spec = root / "unsupported.json"
            spec.write_bytes(canonical_json(payload))
            bundles = (root / "left", root / "right")
            with contextlib.redirect_stdout(StringIO()):
                for bundle in bundles:
                    self.assertEqual(main(("qualify", "--spec", str(spec), "--output", str(bundle))), 4)
            output = StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(("compare", str(bundles[0]), str(bundles[1]), "--json")), 4)
            self.assertEqual(json.loads(output.getvalue())["outcome"], "unsupported")

        for outcome, expected in (("invalid", 2), ("inconclusive", 3), ("error", 5), ("cancelled", 130)):
            summary = {"schema": "qualification-comparison-v1", "compatible": True, "outcome": outcome}
            with (
                patch("gibbsiq.qualification.cli.compare_bundles", return_value=summary),
                patch("gibbsiq.qualification.cli.render_comparison", return_value="report\n"),
                contextlib.redirect_stdout(StringIO()),
            ):
                self.assertEqual(main(("compare", "left", "right")), expected)

    def test_malformed_static_tiny_config_is_invalid_input(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
        from gibbsiq.qualification.artifacts import record_to_dict
        from gibbsiq.qualification.cli import main
        from gibbsiq.qualification.contracts import canonical_json
        from gibbsiq.qualification.model_evaluation import tiny_split_manifest

        payload = record_to_dict(TinyModelBackend(tiny_split_manifest().evaluation).plan(runs=1))
        payload["workload"]["precision"]["config"]["unknown_constructor_field"] = 1
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = root / "bad-tiny.json"
            spec.write_bytes(canonical_json(payload))
            stderr = StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(("qualify", "--spec", str(spec), "--output", str(root / "evidence")))
        self.assertEqual(code, 2)
        self.assertIn("unexpected keyword", stderr.getvalue())

    def test_static_builtin_reconstruction_preserves_plan_metadata_without_optional_imports(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
        from gibbsiq.qualification.adapters.torx import TorxCircuitBackend
        from gibbsiq.qualification.model_evaluation import tiny_split_manifest

        tiny_plan = TinyModelBackend(tiny_split_manifest().evaluation).plan(runs=1, samples=8)
        tiny = TinyModelBackend.from_plan(tiny_plan)
        self.assertEqual(tiny.plan(runs=1, samples=8), tiny_plan)
        torx_plan = TorxCircuitBackend(theta=(0.2, -0.1), initial=(1, 0)).plan(runs=1, samples=8)
        torx = TorxCircuitBackend.from_plan(torx_plan)
        self.assertEqual((torx.theta, torx.initial, torx.simulator), ((0.2, -0.1), (1, 0), "dfg"))


if __name__ == "__main__":
    unittest.main()
