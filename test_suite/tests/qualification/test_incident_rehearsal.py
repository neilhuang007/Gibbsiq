"""Behavioral coverage for the evidence-corruption incident rehearsal."""

from pathlib import Path
import tempfile
import unittest


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }


def _failing_bundle(root: Path) -> Path:
    from gibbsiq.qualification.adapters.spin import SpinConditionalBackend
    from gibbsiq.qualification.examples import SPIN_CANDIDATES, spin_conditional_plan
    from gibbsiq.qualification.workflow import qualify

    plan = spin_conditional_plan(candidate="sign-reversed", runs=64, samples=32, seed=20261002)
    report = qualify(
        plan,
        backends={SPIN_CANDIDATES["sign-reversed"]: SpinConditionalBackend("sign-reversed")},
        destination=root,
    )
    if report.qualification != "fail":
        raise AssertionError(f"fixture must be a real failing qualification, got {report.qualification}")
    return root


class IncidentRehearsalTests(unittest.TestCase):
    def test_corrupted_copy_is_rejected_and_clean_copy_recomputes_result(self):
        from gibbsiq.qualification.artifacts import inspect_bundle
        from tools.qualification.incident_rehearsal import rehearse

        with tempfile.TemporaryDirectory() as temporary:
            source = _failing_bundle(Path(temporary) / "source")
            before = _tree_bytes(source)
            result = rehearse(source, Path(temporary) / "incident", inventory_roots=(source,))
            self.assertEqual(result["classification"], "artifact-integrity incident")
            self.assertEqual(result["containment"]["claim_status"], "suspended for corrupted copy")
            self.assertEqual(result["corruption"]["reader_result"], "rejected")
            self.assertIn("digest", result["corruption"]["reason"].lower())
            restored = inspect_bundle(Path(temporary) / "incident/restored-copy", verify=True)
            self.assertEqual(restored.qualification, "fail")
            self.assertEqual(restored.report, inspect_bundle(source, verify=True).report)
            self.assertEqual(result["reverification"]["qualification"], "fail")
            self.assertEqual(result["affected_inventory"][0]["verification"], "verified public reader")
            self.assertEqual(_tree_bytes(source), before)

    def test_rehearsal_refuses_an_output_inside_the_validated_source(self):
        from tools.qualification.incident_rehearsal import rehearse

        with tempfile.TemporaryDirectory() as temporary:
            source = _failing_bundle(Path(temporary) / "source")
            with self.assertRaises(ValueError):
                rehearse(source, source / "incident-output")


if __name__ == "__main__":
    unittest.main()
