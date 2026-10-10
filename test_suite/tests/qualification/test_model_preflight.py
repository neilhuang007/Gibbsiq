"""Nonexecuting Z1T-0 checkpoint preflight contracts."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import subprocess
import sys
import unittest


class Z1TArrayEstimateTests(unittest.TestCase):
    def test_tiny_source_fixture_and_dense_fallbacks_have_known_byte_counts(self) -> None:
        from gibbsiq.qualification.adapters.model_preflight import Z1TShape, estimate_z1t_array_bytes

        tiny = Z1TShape(vocab=8, sequence=4, n_layers=1, n_embed=8, aft_heads=4, aft_ksize=4, linear_fan_in=4)
        self.assertEqual(estimate_z1t_array_bytes(tiny), 3388)
        self.assertEqual(estimate_z1t_array_bytes(Z1TShape(8, 4, 1, 8, 4, 4, 8)), 3644)
        self.assertEqual(estimate_z1t_array_bytes(Z1TShape(8, 4, 1, 8, 4, 4, 32)), 4156)

    def test_invalid_shapes_do_not_produce_resource_claims(self) -> None:
        from gibbsiq.qualification.adapters.model_preflight import Z1TShape

        for changes in (
            {"vocab": True},
            {"sequence": 0},
            {"n_layers": -1},
            {"n_embed": 9},
            {"aft_heads": 3},
            {"aft_ksize": False},
            {"linear_fan_in": 0},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Z1TShape(**changes)


class ReleasedCheckpointPreflightTests(unittest.TestCase):
    def test_published_metadata_alone_leaves_loading_preconditions_unresolved(self) -> None:
        from gibbsiq.qualification.adapters.model_preflight import RELEASED_Z1T0, preflight_checkpoint

        report = preflight_checkpoint(memory_bytes=10**13, disk_bytes=10**13)
        self.assertFalse(report.ready)
        self.assertIsNone(RELEASED_Z1T0.weights_license)
        self.assertEqual(report.required_disk_bytes, 9_936_600_144)
        self.assertIn("source tree", " ".join(report.issues))
        self.assertIn("parameter tree", " ".join(report.issues))
        self.assertIn("tokenizer", " ".join(report.issues))
        self.assertIn("license", " ".join(report.issues))
        self.assertIn("huggingface_hub", " ".join(report.issues))

    def test_mismatched_identity_and_short_budgets_are_refused(self) -> None:
        from gibbsiq.qualification.adapters.model_preflight import Z1TShape, preflight_checkpoint

        report = preflight_checkpoint(
            memory_bytes=0,
            disk_bytes=0,
            source_revision="wrong-source",
            checkpoint_revision="wrong-checkpoint",
            shape=Z1TShape(),
            source_tree_verified=True,
            parameter_tree_verified=True,
            tokenizer_verified=True,
            license_basis="separately reviewed basis",
            installed_dependencies=("jax", "equinox", "numpy", "z1t", "tiktoken", "huggingface_hub"),
        )
        self.assertFalse(report.ready)
        text = " ".join(report.issues)
        for term in (
            "source revision",
            "checkpoint revision",
            "config shape",
            "memory budget",
            "disk budget",
        ):
            self.assertIn(term, text)

    def test_complete_declarations_only_make_preflight_ready(self) -> None:
        from gibbsiq.qualification.adapters.model_preflight import preflight_checkpoint

        report = preflight_checkpoint(
            memory_bytes=20_026_426_400,
            disk_bytes=9_936_600_144,
            source_tree_verified=True,
            parameter_tree_verified=True,
            tokenizer_verified=True,
            license_basis="caller supplied review reference",
            installed_dependencies=("jax", "equinox", "numpy", "z1t", "tiktoken", "huggingface-hub"),
        )
        self.assertTrue(report.ready)
        self.assertEqual(report.issues, ())
        self.assertEqual(report.model_array_bytes, 4_968_289_448)
        self.assertEqual(report.estimated_peak_bytes, 20_026_426_400)
        self.assertIn("does not fetch", " ".join(report.notes))
        with self.assertRaises(FrozenInstanceError):
            report.ready = False  # type: ignore[misc]

    def test_invalid_budget_and_evidence_types_are_rejected(self) -> None:
        from gibbsiq.qualification.adapters.model_preflight import preflight_checkpoint

        for changes in (
            {"memory_bytes": True},
            {"disk_bytes": -1},
            {"source_revision": 17},
            {"checkpoint_revision": " "},
            {"source_tree_verified": 1},
            {"parameter_tree_verified": "yes"},
            {"tokenizer_verified": 0},
            {"license_basis": False},
            {"installed_dependencies": "jax"},
        ):
            arguments = {"memory_bytes": 10**13, "disk_bytes": 10**13, **changes}
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                preflight_checkpoint(**arguments)

    def test_core_import_and_default_preflight_use_no_optional_backend_or_network(self) -> None:
        source = Path(__file__).resolve().parents[3] / "src"
        script = (
            "import sys, socket; "
            f"sys.path.insert(0, {str(source)!r}); "
            "socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError('network')); "
            "import gibbsiq; "
            "from gibbsiq.qualification.adapters.model_preflight import preflight_checkpoint; "
            "r = preflight_checkpoint(memory_bytes=0, disk_bytes=0); "
            "assert not r.ready; "
            "assert not {'jax', 'numpy', 'equinox', 'z1t'} & set(sys.modules)"
        )
        result = subprocess.run(
            [sys.executable, "-S", "-c", script], capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
