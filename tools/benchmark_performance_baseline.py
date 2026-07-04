"""Create a reproducible performance baseline for core Gibbsiq calculations.

This script is intentionally stdlib-only and deterministic. It measures the
current cost of the calculations that are most likely to matter before any
future optimizer rewrite:

* Ising/QUBO compilation
* graph-coloring block construction
* energy and local-field evaluation
* diagnostics assembly
* strict benchmark-oracle scoring
* ground-truth corpus generation

The output is a JSON artifact with command, platform, git commit, parameters,
raw case timings, and summarized medians. It is a baseline, not a performance
claim: compare future branches by rerunning the same command on the same
machine and environment.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from gibbsiq.benchmark_oracle import verify_benchmark_fixture
from gibbsiq.blocks import color_blocks
from gibbsiq.conversions import compile_ising, compile_qubo
from gibbsiq.diagnostics import compute_diagnostics
from gibbsiq.model import IsingModel


def timed(call: Callable[[], Any], repeat: int) -> dict[str, Any]:
    """Run ``call`` repeatedly and return raw seconds plus summary statistics."""
    values = []
    last_result = None
    for _ in range(repeat):
        started = time.perf_counter()
        last_result = call()
        values.append(time.perf_counter() - started)
    return {
        "repeat": repeat,
        "seconds": values,
        "median_seconds": statistics.median(values),
        "min_seconds": min(values),
        "max_seconds": max(values),
        "last_result": last_result,
    }


def git_output(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_metadata() -> dict[str, Any]:
    status = git_output("status", "--short")
    return {
        "commit": git_output("rev-parse", "HEAD"),
        "branch": git_output("branch", "--show-current"),
        "dirty": bool(status),
        "status_short": status.splitlines() if status else [],
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def random_sparse_terms(
    *,
    variables: tuple[str, ...],
    edge_probability: float,
    seed: int,
    coefficient_range: tuple[int, int] = (-3, 3),
) -> tuple[dict[str, float], dict[tuple[str, str], float]]:
    rng = random.Random(seed)
    low, high = coefficient_range
    h = {variable: float(rng.randint(low, high)) for variable in variables}
    quadratic: dict[tuple[str, str], float] = {}
    for left_index, left in enumerate(variables):
        for right in variables[left_index + 1 :]:
            if rng.random() < edge_probability:
                coefficient = rng.randint(low, high)
                if coefficient:
                    quadratic[(left, right)] = float(coefficient)
    return h, quadratic


def random_samples(variables: tuple[str, ...], count: int, seed: int) -> list[dict[str, int]]:
    rng = random.Random(seed)
    return [{variable: rng.choice((-1, 1)) for variable in variables} for _ in range(count)]


def alternating_energy_chains(num_chains: int, draws: int, seed: int) -> list[list[float]]:
    rng = random.Random(seed)
    chains = []
    for chain_index in range(num_chains):
        value = rng.uniform(-1.0, 1.0) + chain_index * 0.05
        row = []
        for draw in range(draws):
            value = 0.82 * value + rng.gauss(0.0, 1.0)
            row.append(value + 0.01 * draw / draws)
        chains.append(row)
    return chains


def load_ground_truth_generator() -> Any:
    path = REPO_ROOT / "tools" / "generate_ground_truth.py"
    spec = importlib.util.spec_from_file_location("gibbsiq_ground_truth_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_ground_truth_fixtures() -> list[dict[str, Any]]:
    path = REPO_ROOT / "reference" / "06-benchmarks" / "fixtures" / "ground-truth-small.json"
    return json.loads(path.read_text(encoding="utf-8"))["fixtures"]


def correct_benchmark_actual(fixture: dict[str, Any]) -> dict[str, Any]:
    expected = fixture["expected"]
    family = fixture["family"]
    if family == "maxcut":
        return {
            key: expected[key]
            for key in (
                "num_nodes",
                "num_edges",
                "best_cut_value",
                "best_ising_energy",
                "ground_state_degeneracy",
                "witness_spin_samples",
            )
        }
    if family == "number_partition":
        return {
            key: expected[key]
            for key in (
                "min_subset_sum_difference",
                "best_ising_energy",
                "ground_state_degeneracy",
                "is_perfect_partition",
                "witness_partitions",
            )
        }
    if family == "knapsack":
        return {
            key: expected[key]
            for key in (
                "max_value",
                "weight_at_optimum",
                "capacity",
                "num_optimal_selections",
                "witness_selections",
            )
        }
    if family == "tsp":
        return {
            key: expected[key]
            for key in ("num_cities", "optimal_tour_length", "num_optimal_tours", "witness_tours")
        }
    if family == "sk_spin_glass":
        return {
            key: expected[key]
            for key in ("num_spins", "ground_state_energy", "ground_state_degeneracy", "witness_spin_samples")
        }
    raise ValueError(f"unsupported family {family!r}")


def benchmark_compile_ising(repeat: int) -> dict[str, Any]:
    cases = []
    for n, probability, seed in ((64, 0.05, 101), (256, 0.02, 102), (512, 0.01, 103)):
        variables = tuple(str(index) for index in range(n))
        h, quadratic = random_sparse_terms(variables=variables, edge_probability=probability, seed=seed)

        def run() -> dict[str, Any]:
            model = compile_ising(h, quadratic, variables=variables)
            return {"variables": len(model.variables), "edges": len(model.quadratic)}

        record = timed(run, repeat)
        cases.append({"n": n, "edge_probability": probability, **record})
    return {"cases": cases}


def benchmark_compile_qubo(repeat: int) -> dict[str, Any]:
    cases = []
    for n, probability, seed in ((64, 0.05, 201), (256, 0.02, 202), (512, 0.01, 203)):
        variables = tuple(str(index) for index in range(n))
        h, quadratic = random_sparse_terms(variables=variables, edge_probability=probability, seed=seed)
        qubo: dict[tuple[str, str], float] = {}
        for variable, coefficient in h.items():
            qubo[(variable, variable)] = coefficient
        qubo.update(quadratic)

        def run() -> dict[str, Any]:
            model = compile_qubo(qubo, variables=variables)
            return {"variables": len(model.variables), "edges": len(model.quadratic)}

        record = timed(run, repeat)
        cases.append({"n": n, "edge_probability": probability, **record})
    return {"cases": cases}


def benchmark_coloring(repeat: int) -> dict[str, Any]:
    cases = []
    for n, probability, seed in ((500, 0.01, 301), (1000, 0.004, 302), (2000, 0.002, 303)):
        variables = tuple(str(index) for index in range(n))
        h, quadratic = random_sparse_terms(variables=variables, edge_probability=probability, seed=seed)
        model = compile_ising(h, quadratic, variables=variables)

        # color_blocks itself is a wrapper; clear the private cached function by
        # rebuilding a fresh same-topology model for cold timing.
        def cold_run() -> dict[str, Any]:
            from gibbsiq.blocks import _color_blocks_cached  # noqa: PLC0415

            _color_blocks_cached.cache_clear()
            partition = color_blocks(model)
            return {"blocks": partition.num_blocks, "max_block_size": max(partition.block_sizes)}

        def cached_run() -> dict[str, Any]:
            partition = color_blocks(model)
            return {"blocks": partition.num_blocks, "max_block_size": max(partition.block_sizes)}

        cold = timed(cold_run, repeat)
        color_blocks(model)
        cached = timed(cached_run, repeat)
        cases.append(
            {
                "n": n,
                "edge_probability": probability,
                "edges": len(model.quadratic),
                "cold": cold,
                "cached": cached,
            }
        )
    return {"cases": cases}


def benchmark_energy_and_local_field(repeat: int) -> dict[str, Any]:
    variables = tuple(str(index) for index in range(256))
    h, quadratic = random_sparse_terms(variables=variables, edge_probability=0.02, seed=401)
    model = compile_ising(h, quadratic, variables=variables)
    samples = random_samples(variables, 2000, seed=402)
    query_variables = [variables[index % len(variables)] for index in range(2000)]

    def energy_run() -> dict[str, Any]:
        total = math.fsum(model.energy(sample) for sample in samples)
        return {"evaluations": len(samples), "checksum": round(total, 6)}

    def local_field_run() -> dict[str, Any]:
        sample = samples[0]
        total = math.fsum(model.local_field(variable, sample) for variable in query_variables)
        return {"queries": len(query_variables), "checksum": round(total, 6)}

    return {
        "model": {"variables": len(model.variables), "edges": len(model.quadratic)},
        "energy": timed(energy_run, repeat),
        "local_field": timed(local_field_run, repeat),
    }


def benchmark_diagnostics(repeat: int) -> dict[str, Any]:
    variables = tuple(str(index) for index in range(64))
    energy_chains = alternating_energy_chains(num_chains=4, draws=512, seed=501)
    samples = random_samples(variables, count=2048, seed=502)
    sample_chains = [samples[index * 512 : (index + 1) * 512] for index in range(4)]
    magnetization = [
        [math.fsum(sample[variable] for variable in variables) / len(variables) for sample in chain]
        for chain in sample_chains
    ]

    def run() -> dict[str, Any]:
        diagnostics = compute_diagnostics(
            energy_chains=energy_chains,
            samples=samples,
            variables=variables,
            magnetization_chains=magnetization,
            timings={"sample_seconds": 1.0},
        )
        return {
            "flags": diagnostics["flags"],
            "energy_count": diagnostics["energy"]["count"],
            "unique_states": diagnostics["diversity"]["unique_states"],
        }

    return {"chains": 4, "draws_per_chain": 512, "variables": 64, **timed(run, repeat)}


def benchmark_oracle(repeat: int) -> dict[str, Any]:
    fixtures = load_ground_truth_fixtures()
    actual_by_id = {fixture["id"]: correct_benchmark_actual(fixture) for fixture in fixtures}

    def run() -> dict[str, Any]:
        failures = 0
        differences = 0
        for fixture in fixtures:
            diff = verify_benchmark_fixture(fixture, actual_by_id[fixture["id"]], 1e-9)
            failures += int(bool(diff))
            differences += len(diff)
        return {"fixtures": len(fixtures), "failures": failures, "differences": differences}

    return timed(run, repeat)


def benchmark_ground_truth_generation(repeat: int) -> dict[str, Any]:
    generator = load_ground_truth_generator()

    def run() -> dict[str, Any]:
        document = generator.build_corpus()
        return {
            "fixtures": len(document["fixtures"]),
            "checksum": generator.checksum(document),
        }

    return timed(run, repeat)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=5, help="Repeats per benchmark case.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("reference/06-benchmarks/artifacts/performance-baseline-current.json"),
        help="Output JSON artifact path.",
    )
    return parser


def validate_repeat(repeat: int) -> int:
    if isinstance(repeat, bool) or repeat < 1:
        raise ValueError("repeat must be an integer >= 1")
    return repeat


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    repeat = validate_repeat(args.repeat)
    started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    metadata = {
        "benchmark_started": started,
        "script_path": str(Path(__file__).relative_to(REPO_ROOT).as_posix()),
        "command": " ".join(os.sys.argv),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "git": git_metadata(),
        "parameters": {"repeat": repeat},
        "notes": [
            "Stdlib deterministic baseline for core calculations.",
            "Compare future runs on the same machine and Python environment.",
            "Timings are wall-clock seconds from time.perf_counter().",
        ],
    }
    benchmarks = {
        "compile_ising": benchmark_compile_ising(repeat),
        "compile_qubo": benchmark_compile_qubo(repeat),
        "block_coloring": benchmark_coloring(repeat),
        "energy_and_local_field": benchmark_energy_and_local_field(repeat),
        "diagnostics": benchmark_diagnostics(repeat),
        "benchmark_oracle": benchmark_oracle(repeat),
        "ground_truth_generation": benchmark_ground_truth_generation(max(1, min(repeat, 3))),
    }
    payload = {
        "schema_version": "2026-07-04",
        "metadata": metadata,
        "benchmarks": benchmarks,
    }
    payload["metadata"]["benchmark_finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksum = sha256_file(args.out)
    payload["metadata"]["payload_sha256_before_checksum_field"] = checksum
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    final_checksum = sha256_file(args.out)
    print(
        json.dumps(
            {
                "output": str(args.out),
                "sha256": final_checksum,
                "commit": payload["metadata"]["git"]["commit"],
                "dirty_at_start": payload["metadata"]["git"]["dirty"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
