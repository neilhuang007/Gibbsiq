"""Verify that the public core and qualification foundations stay dependency-free."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]


class OptionalImportTests(unittest.TestCase):
    def test_legacy_and_qualification_foundations_work_without_optional_packages(self) -> None:
        program = textwrap.dedent(
            """
            import importlib.abc
            import json
            import math
            import sys

            blocked = {
                "arviz",
                "dimod",
                "equinox",
                "jax",
                "networkx",
                "numpy",
                "thrml",
                "torx",
                "z1t",
            }

            class BlockOptionalPackages(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname.partition(".")[0] in blocked:
                        raise ModuleNotFoundError(
                            f"optional package blocked by core import test: {fullname}"
                        )
                    return None

            sys.meta_path.insert(0, BlockOptionalPackages())
            sys.path.insert(0, sys.argv[1])

            import gibbsiq
            from gibbsiq.qualification.adapters.reference import spin_conditional
            from gibbsiq.qualification.adapters.z1t import TinyZ1TConfig
            from gibbsiq.qualification.adapters.model_preflight import preflight_checkpoint
            from gibbsiq.qualification.adapters.thrml import THRMLIsingBackend
            from gibbsiq.qualification.adapters.torx import TorxCircuitBackend
            from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel
            from gibbsiq.qualification.model_evaluation import language_loss, tiny_split_manifest
            from gibbsiq.qualification.profiles import dy4p_reference, get_profile
            from gibbsiq.qualification.timing import TimingSeries
            from gibbsiq.qualification.contracts import Acceptance, Bounds, MetricSpec
            from gibbsiq.qualification.statistics import evaluate_metric

            assert TinyZ1TConfig().n_embed == 8
            assert not preflight_checkpoint(memory_bytes=0, disk_bytes=0).ready
            assert IdealTanhModel.profile_id == get_profile("ideal-tanh-iid-v1").profile_id
            assert dy4p_reference(value=0, weight=4).representation_mean > 0
            assert language_loss([[0, 0]], [0]).perplexity == 2.0
            assert tiny_split_manifest().evaluation.documents[0].targets == (2, 4, 6, 0)
            assert TimingSeries.from_durations((3, 1, 2)).median == 2
            assert TorxCircuitBackend().plan(runs=2).workload.randomization.independent_runs == 2
            model = gibbsiq.IsingModel(("spin",), {"spin": 0.0}, {})
            assert len(THRMLIsingBackend(model).plan(runs=2).runs) == 2
            spin = spin_conditional(field=math.log(3.0) / 2.0, samples=100)
            spec = MetricSpec(
                metric_id="mean-error",
                units="absolute error",
                direction="target",
                comparison="candidate-reference",
                acceptance=Acceptance("equivalence", lower=-0.1, upper=0.1),
                evidence_mode="bounded_fixed_n",
                planned_units=4096,
                replication_unit="independent_run",
                scope="fixed_inputs",
                bounds=Bounds(-1.5, 0.5),
            )
            metric = evaluate_metric(
                spec,
                [0.5] * 3072 + [-1.5] * 1024,
                alpha=0.05,
            )

            print(
                json.dumps(
                    {
                        "legacy_model_type": gibbsiq.IsingModel.__name__,
                        "spin_mean": spin.mean,
                        "spin_variance": spin.variance,
                        "metric_estimate": metric.estimate,
                        "metric_interval_lower": metric.interval.lower,
                        "metric_interval_upper": metric.interval.upper,
                        "metric_outcome": metric.outcome,
                        "optional_loaded": sorted(blocked.intersection(sys.modules)),
                    },
                    sort_keys=True,
                )
            )
            """
        )

        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-c", program, str(REPO_ROOT / "src")],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["legacy_model_type"], "IsingModel")
        self.assertAlmostEqual(result["spin_mean"], 0.5)
        self.assertAlmostEqual(result["spin_variance"], 0.75)
        self.assertAlmostEqual(result["metric_estimate"], 0.0)
        self.assertAlmostEqual(result["metric_interval_lower"], -0.04244067236689436)
        self.assertAlmostEqual(result["metric_interval_upper"], 0.04244067236689436)
        self.assertEqual(result["metric_outcome"], "pass")
        self.assertEqual(result["optional_loaded"], [])


if __name__ == "__main__":
    unittest.main()
