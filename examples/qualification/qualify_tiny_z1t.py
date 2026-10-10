"""Run one frozen tiny Z1T software-model evaluation count.

Invoke once for each count 8, 32, and 128 in the pinned optional environment.
Each invocation keeps its ordinary qualification bundle immutable and writes a
model summary beside it, including partial or inconclusive outcomes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
from gibbsiq.qualification.artifacts import inspect_bundle
from gibbsiq.qualification.contracts import RunPlan, canonical_json
from gibbsiq.qualification.model_evaluation import (
    render_model_summary,
    summarize_model_bundle,
    tiny_split_manifest,
)
from gibbsiq.qualification.workflow import qualify


COUNTS = (8, 32, 128)
RUNS_PER_COUNT = 16
MAX_SECONDS_PER_COUNT = 180.0
MAX_BYTES_PER_COUNT = 16 * 1024 * 1024


def frozen_plan(count: int) -> RunPlan:
    """Build exactly one of the three predeclared pure model plans."""
    if type(count) is not int or count not in COUNTS:
        raise ValueError("count must be one of 8, 32, or 128")
    backend = TinyModelBackend(tiny_split_manifest().evaluation, initialization_seed=17, cap=8.0)
    return backend.plan(
        runs=RUNS_PER_COUNT,
        samples=count,
        seed=20260923,
        margin=0.1,
        alpha=0.05,
        max_seconds=MAX_SECONDS_PER_COUNT,
        max_bytes=MAX_BYTES_PER_COUNT,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, required=True, choices=COUNTS)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)

    plan = frozen_plan(args.count)
    backend = TinyModelBackend(tiny_split_manifest().evaluation, initialization_seed=17, cap=8.0)
    count_directory = args.output_root / f"count-{args.count:03d}"
    # Creating this directory only once prevents an accidental qualification retry
    # after a negative or incomplete result.
    count_directory.mkdir(parents=True, exist_ok=False)
    bundle = count_directory / "bundle"
    try:
        qualify(
            plan,
            backends={plan.workload.candidate.identity: backend},
            destination=bundle,
        )
    finally:
        if bundle.exists():
            snapshot = inspect_bundle(bundle, verify=True)
            summary = summarize_model_bundle(snapshot)
            (count_directory / "model-report.json").write_bytes(canonical_json(summary) + b"\n")
            (count_directory / "model-report.md").write_text(render_model_summary(summary), encoding="utf-8")
            print(
                json.dumps(
                    {
                        "count": args.count,
                        "execution": summary["execution"],
                        "qualification": summary["qualification"],
                        "observed_runs": summary["descriptive"]["observed_runs"],
                        "planned_runs": summary["descriptive"]["planned_runs"],
                        "bundle": str(bundle),
                    },
                    sort_keys=True,
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
