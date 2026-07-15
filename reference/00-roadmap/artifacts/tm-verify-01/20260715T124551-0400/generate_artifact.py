"""Regenerate the TM-VERIFY-01 seeded verification evidence bundle."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.reference_sampler import (  # noqa: E402
    ReferenceGibbsSampler,
    ReferenceSamplerConfig,
)
from gibbsiq.verification import (  # noqa: E402
    build_exact_transition_kernel,
    verify_empirical_distribution,
    verify_transition_kernel,
    verify_transition_matrix,
)


def write_json(name: str, payload: object) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    (RUN_DIR / name).write_text(text, encoding="utf-8", newline="\n")


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def as_samples(variables: tuple[object, ...], states: tuple[tuple[int, ...], ...]):
    return [dict(zip(variables, state)) for state in states]


def main() -> None:
    run_started = time.perf_counter()
    compile_seconds = 0.0
    sample_seconds = 0.0
    diagnostics_seconds = 0.0
    kernel_construction_seconds = 0.0
    run_id = RUN_DIR.name
    reproduction_command = (
        "$env:PYTHONPATH='src'; python "
        "reference/00-roadmap/artifacts/tm-verify-01/"
        f"{run_id}/generate_artifact.py"
    )
    write_json(
        "config.json",
        {
            "run_id": run_id,
            "task": "TM-VERIFY-01",
            "state_cap": 8,
            "transition_tolerance": 1e-12,
            "empirical_interval": {
                "method": "Bonferroni-Hoeffding",
                "familywise_confidence": 0.99,
                "sampling_design": "one retained state per independently seeded chain",
            },
            "main_empirical": {
                "model": {"linear": {"s": 0.35}, "offset": 11.0},
                "beta": 0.8,
                "sample_count": 2000,
                "seed": 20260715,
                "n_warmup": 0,
                "steps_per_sample": 1,
                "update_schedule": "systematic",
                "initialization": "all_up",
            },
            "repeated_seed_sensitivity": {
                "sample_counts": [200, 800],
                "seeds": list(range(9100, 9105)),
            },
            "reproduction_command": reproduction_command,
        },
    )

    phase_started = time.perf_counter()
    trace_model = compile_ising(
        {"a": 0.4, "b": -0.3},
        {("a", "b"): 0.6},
        offset=5.25,
        variables=("a", "b"),
    )
    compile_seconds += time.perf_counter() - phase_started
    trace_config = ReferenceSamplerConfig(
        beta=1.1,
        n_warmup=3,
        steps_per_sample=2,
        num_chains=2,
        seed=8128,
        initialization="random",
        update_schedule="random_single_site",
    )
    phase_started = time.perf_counter()
    trace_result = ReferenceGibbsSampler(trace_config).sample(trace_model, num_reads=16)
    sample_seconds += time.perf_counter() - phase_started
    write_json(
        "reference-trace.json",
        {
            "model": trace_model.to_dict(),
            "sampler_result": trace_result.to_dict(),
            "recomputed_energies": [
                trace_model.energy(dict(zip(trace_model.variables, state))) for state in trace_result.samples
            ],
        },
    )

    phase_started = time.perf_counter()
    kernel_model = compile_ising(
        {"a": 0.4, "b": -0.25},
        {("a", "b"): 0.9},
        variables=("a", "b"),
    )
    compile_seconds += time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    random_kernel = build_exact_transition_kernel(kernel_model, 1.3)
    systematic_kernel = build_exact_transition_kernel(
        kernel_model,
        1.3,
        update_schedule="systematic",
    )
    kernel_construction_seconds += time.perf_counter() - phase_started
    identity = tuple(tuple(1.0 if row == column else 0.0 for column in range(4)) for row in range(4))
    wrong_sign_model = compile_ising({"s": 1.0})
    wrong_probability_up = 1.0 / (1.0 + math.exp(-2.0))
    wrong_sign_matrix = (
        (1.0 - wrong_probability_up, wrong_probability_up),
        (1.0 - wrong_probability_up, wrong_probability_up),
    )
    phase_started = time.perf_counter()
    transition_payload = {
        "model": kernel_model.to_dict(),
        "random_single_site": {
            "kernel": random_kernel.to_dict(),
            "report": verify_transition_kernel(
                kernel_model,
                1.3,
                random_kernel,
            ).to_dict(),
        },
        "systematic": {
            "kernel": systematic_kernel.to_dict(),
            "report": verify_transition_kernel(
                kernel_model,
                1.3,
                systematic_kernel,
            ).to_dict(),
        },
        "traps": {
            "wrong_conditional_sign": verify_transition_matrix(
                wrong_sign_model,
                1.0,
                wrong_sign_matrix,
            ).to_dict(),
            "nonergodic_identity": verify_transition_matrix(
                kernel_model,
                1.3,
                identity,
            ).to_dict(),
        },
    }
    diagnostics_seconds += time.perf_counter() - phase_started
    write_json(
        "transition-evidence.json",
        transition_payload,
    )

    phase_started = time.perf_counter()
    empirical_model = compile_ising({"s": 0.35}, offset=11.0)
    compile_seconds += time.perf_counter() - phase_started
    main_count = 2000
    phase_started = time.perf_counter()
    main_result = ReferenceGibbsSampler(
        ReferenceSamplerConfig(
            beta=0.8,
            n_warmup=0,
            steps_per_sample=1,
            num_chains=main_count,
            seed=20260715,
            initialization="all_up",
            update_schedule="systematic",
        )
    ).sample(empirical_model, num_reads=main_count)
    sample_seconds += time.perf_counter() - phase_started
    phase_started = time.perf_counter()
    main_report = verify_empirical_distribution(
        empirical_model,
        as_samples(empirical_model.variables, main_result.samples),
        0.8,
        familywise_confidence=0.99,
        sampling_design="independent_chains",
    )
    diagnostics_seconds += time.perf_counter() - phase_started

    repeated_runs = []
    sensitivity_summary = []
    for sample_count in (200, 800):
        passed = 0
        half_widths = []
        for seed in range(9100, 9105):
            phase_started = time.perf_counter()
            result = ReferenceGibbsSampler(
                ReferenceSamplerConfig(
                    beta=0.8,
                    n_warmup=0,
                    steps_per_sample=1,
                    num_chains=sample_count,
                    seed=seed,
                    initialization="all_up",
                    update_schedule="systematic",
                )
            ).sample(empirical_model, num_reads=sample_count)
            sample_seconds += time.perf_counter() - phase_started
            phase_started = time.perf_counter()
            report = verify_empirical_distribution(
                empirical_model,
                as_samples(empirical_model.variables, result.samples),
                0.8,
                familywise_confidence=0.99,
                sampling_design="independent_chains",
            )
            diagnostics_seconds += time.perf_counter() - phase_started
            passed += report.passed
            half_widths.append(report.intervals[0].half_width)
            repeated_runs.append(
                {
                    "sample_count": sample_count,
                    "seed": seed,
                    "sampler_result": result.to_dict(),
                    "report": report.to_dict(),
                }
            )
        sensitivity_summary.append(
            {
                "sample_count": sample_count,
                "runs": 5,
                "passed": passed,
                "marginal_half_width": half_widths[0],
            }
        )

    bad_samples = [{"s": 1} for _ in range(main_count)]
    phase_started = time.perf_counter()
    biased_report = verify_empirical_distribution(
        empirical_model,
        bad_samples,
        0.8,
        familywise_confidence=0.99,
        sampling_design="independent_chains",
    )
    diagnostics_seconds += time.perf_counter() - phase_started
    write_json(
        "empirical-evidence.json",
        {
            "model": empirical_model.to_dict(),
            "main_seeded_run": {
                "sampler_result": main_result.to_dict(),
                "report": main_report.to_dict(),
            },
            "repeated_seed_runs": repeated_runs,
            "sensitivity_summary": sensitivity_summary,
            "deliberately_biased_all_up_trap": biased_report.to_dict(),
        },
    )

    write_json(
        "timing.json",
        {
            "clock": "time.perf_counter",
            "compile_seconds": compile_seconds,
            "sample_seconds": sample_seconds,
            "kernel_construction_seconds": kernel_construction_seconds,
            "diagnostics_seconds": diagnostics_seconds,
            "tuning_seconds": 0.0,
            "wall_seconds_before_environment_and_manifest": time.perf_counter() - run_started,
            "boundary_note": (
                "Serialization is included only in wall time. Sampler results omit timing "
                "so identical seeds remain byte-for-byte comparable in memory."
            ),
        },
    )

    write_json(
        "environment.json",
        {
            "generated_at": datetime.now().astimezone().isoformat(),
            "git_head_before_task": git_output("rev-parse", "HEAD"),
            "git_status_porcelain": git_output("status", "--short"),
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "os_name": os.name,
            "reproduction_command": reproduction_command,
        },
    )

    artifact_names = (
        "config.json",
        "empirical-evidence.json",
        "environment.json",
        "generate_artifact.py",
        "reference-trace.json",
        "timing.json",
        "transition-evidence.json",
    )
    files = []
    for name in artifact_names:
        path = RUN_DIR / name
        content = path.read_bytes()
        files.append(
            {
                "path": name,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    write_json(
        "manifest.json",
        {
            "run_id": run_id,
            "task": "TM-VERIFY-01",
            "files": files,
            "manifest_note": "The manifest does not recursively checksum itself.",
        },
    )


if __name__ == "__main__":
    main()
