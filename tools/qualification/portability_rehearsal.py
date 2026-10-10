"""Rehearse the public qualification workflow with a pinned Torx workload."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from gibbsiq.qualification.adapters.torx import TorxCircuitBackend
from gibbsiq.qualification.artifacts import inspect_bundle, record_to_dict
from gibbsiq.qualification.contracts import ArtifactIdentity, canonical_json
from gibbsiq.qualification.engine import BackendCapabilities, ExecutionResult
from gibbsiq.qualification.workflow import qualify


_COMPLEMENTED_CANDIDATE = ArtifactIdentity(
    "torx-two-gate-dfg-complement-bit0",
    "1",
    "sha256:" + hashlib.sha256(b"pinned-torx-dfg:complement-output-bit-0:v1").hexdigest(),
)


class ComplementedBitBackend:
    """A named planted candidate change that complements Torx output bit zero."""

    def __init__(self, baseline: TorxCircuitBackend) -> None:
        self._baseline = baseline
        self._baseline_candidate = baseline.plan(runs=1, samples=1).workload.candidate

    def capabilities(self) -> BackendCapabilities:
        baseline = self._baseline.capabilities()
        return BackendCapabilities(
            _COMPLEMENTED_CANDIDATE.identity, baseline.controls, baseline.observation_names
        )

    def validate_plan(self, plan: Any) -> None:
        self._baseline.validate_plan(
            replace(plan, workload=replace(plan.workload, candidate=self._baseline_candidate))
        )

    def prepare(self, workload: Any) -> None:
        self._baseline.prepare(replace(workload, candidate=self._baseline_candidate))

    def execute(self, run: Any, randomization: Any) -> ExecutionResult:
        result = self._baseline.execute(run, randomization)
        observations = tuple(
            replace(observation, values=(1.0 - observation.values[0],))
            if observation.name == "bit0_mean"
            else observation
            for observation in result.observations
        )
        return ExecutionResult(observations, result.costs)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rehearse(destination: Path, *, runs: int = 256, samples: int = 64) -> dict[str, Any]:
    """Run the baseline and planted-change candidate through the installed workflow."""
    destination.mkdir(parents=True, exist_ok=False)
    baseline = TorxCircuitBackend(theta=(2.0, -0.75), initial=(1, 0), simulator="dfg")
    baseline_plan = baseline.plan(runs=runs, samples=samples, seed=20261002, margin=0.15)
    changed = ComplementedBitBackend(TorxCircuitBackend(theta=(2.0, -0.75), initial=(1, 0)))
    changed_plan = replace(
        baseline_plan, workload=replace(baseline_plan.workload, candidate=_COMPLEMENTED_CANDIDATE)
    )

    started = time.perf_counter()
    baseline_report = qualify(
        baseline_plan,
        backends={baseline.capabilities().backend_id: baseline},
        destination=destination / "baseline",
    )
    changed_report = qualify(
        changed_plan,
        backends={changed.capabilities().backend_id: changed},
        destination=destination / "changed-candidate",
    )
    elapsed = time.perf_counter() - started
    if baseline_report.qualification != "pass":
        raise RuntimeError(f"baseline Torx candidate did not pass: {baseline_report.qualification}")
    if changed_report.qualification != "fail":
        raise RuntimeError(f"planted candidate change was not detected: {changed_report.qualification}")

    baseline_snapshot = inspect_bundle(destination / "baseline", verify=True)
    changed_snapshot = inspect_bundle(destination / "changed-candidate", verify=True)
    summary = {
        "schema": "gibbsiq-portability-rehearsal-v1",
        "classification": "local portability evidence; not external adoption",
        "workload": "pinned Torx PNOT(0) then PCNOT([0,1])",
        "configuration": {
            "theta": [2.0, -0.75],
            "initial": [1, 0],
            "runs": runs,
            "samples_per_run": samples,
            "seed": 20261002,
            "margin": 0.15,
            "deadline_seconds": baseline_plan.workload.resources.max_seconds,
            "retained_bytes": baseline_plan.workload.resources.max_bytes,
        },
        "independent_reference": "four-branch enumeration shipped by the installed Torx adapter",
        "baseline": record_to_dict(baseline_snapshot.report),
        "changed_candidate": record_to_dict(changed_snapshot.report),
        "elapsed_seconds": elapsed,
        "integration_effort": {
            "shared_engine_or_report_changes": 0,
            "shared_contract_changes": 0,
            "workload_specific_adapter_classes": 1,
            "duplicate_reference_implementations": 0,
            "note": "The rehearsal reused TorxCircuitBackend.plan, qualify, inspect_bundle, and the persisted report schema. The only new adapter is an explicit planted output mutation.",
        },
        "limitations": [
            "The same project agent authored this rehearsal; it is not independent use or endorsement.",
            "Execution used the pinned Torx DFG simulator on CPU, not physical hardware.",
            "Gate-sample work is modeled; physical energy and complete-system latency remain unknown.",
            "The planted output mutation is a regression fixture, not an observed upstream Torx defect.",
        ],
    }
    summary_path = destination / "summary.json"
    summary_path.write_bytes(canonical_json(summary))
    hashes = {
        str(path.relative_to(destination)).replace("\\", "/"): _digest(path)
        for path in sorted(destination.rglob("*"))
        if path.is_file() and path != summary_path
    }
    (destination / "artifact-hashes.json").write_bytes(canonical_json(hashes))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--runs", type=int, default=256)
    parser.add_argument("--samples", type=int, default=64)
    args = parser.parse_args()
    print(json.dumps(rehearse(args.output, runs=args.runs, samples=args.samples), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
