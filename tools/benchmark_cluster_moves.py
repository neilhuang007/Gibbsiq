"""Benchmark PT against PT plus isoenergetic cluster moves.

This is a research harness, not a production sampler. It is intended to produce
local pilot numbers for the cluster-move recommendation in the research journal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class GridSpinGlass:
    """A square-grid Ising spin glass with +/-J couplers and no linear fields."""

    size: int
    edges: tuple[tuple[int, int, int], ...]
    adjacency: tuple[tuple[tuple[int, int], ...], ...]

    @property
    def variables(self) -> int:
        return self.size * self.size

    def energy(self, state: list[int]) -> int:
        return sum(weight * state[i] * state[j] for i, j, weight in self.edges)


@dataclass
class RunStats:
    algorithm: str
    size: int
    instance_seed: int
    run_seed: int
    variables: int
    sweeps: int
    beta_count: int
    wall_seconds: float
    best_energy: int
    final_best_energy: int
    best_trace: list[int]
    best_time_trace: list[float]
    swap_attempts: int
    swap_accepts: int
    cluster_attempts: int
    cluster_accepts: int
    cluster_skips_too_small: int
    cluster_skips_too_large: int
    cluster_mean_fraction: float | None


def make_grid_spin_glass(size: int, rng: random.Random) -> GridSpinGlass:
    edges: list[tuple[int, int, int]] = []
    for row in range(size):
        for col in range(size):
            index = row * size + col
            if col + 1 < size:
                edges.append((index, index + 1, rng.choice((-1, 1))))
            if row + 1 < size:
                edges.append((index, index + size, rng.choice((-1, 1))))

    adjacency_lists: list[list[tuple[int, int]]] = [[] for _ in range(size * size)]
    for i, j, weight in edges:
        adjacency_lists[i].append((j, weight))
        adjacency_lists[j].append((i, weight))

    return GridSpinGlass(
        size=size,
        edges=tuple(edges),
        adjacency=tuple(tuple(items) for items in adjacency_lists),
    )


def beta_ladder(min_beta: float, max_beta: float, count: int) -> list[float]:
    if count < 2:
        raise ValueError("beta_count must be at least 2")
    if min_beta <= 0 or max_beta <= min_beta:
        raise ValueError("require 0 < min_beta < max_beta")
    log_min = math.log(min_beta)
    log_max = math.log(max_beta)
    return [math.exp(log_min + (log_max - log_min) * i / (count - 1)) for i in range(count)]


def random_state(variables: int, rng: random.Random) -> list[int]:
    return [rng.choice((-1, 1)) for _ in range(variables)]


def local_field(model: GridSpinGlass, state: list[int], index: int) -> int:
    return sum(weight * state[neighbor] for neighbor, weight in model.adjacency[index])


def heatbath_sweep(
    model: GridSpinGlass,
    state: list[int],
    energy: int,
    beta: float,
    order: list[int],
    rng: random.Random,
) -> int:
    rng.shuffle(order)
    for index in order:
        old_spin = state[index]
        gamma = local_field(model, state, index)
        x = 2.0 * beta * gamma
        if x >= 0.0:
            p_plus = math.exp(-x) / (1.0 + math.exp(-x))
        else:
            p_plus = 1.0 / (1.0 + math.exp(x))
        new_spin = 1 if rng.random() < p_plus else -1
        if new_spin != old_spin:
            energy += -2 * old_spin * gamma
            state[index] = new_spin
    return energy


def try_temperature_swaps(
    states: list[list[int]],
    energies: list[int],
    betas: list[float],
    rng: random.Random,
    offset: int,
) -> tuple[int, int]:
    attempts = 0
    accepts = 0
    for beta_index in range(offset, len(betas) - 1, 2):
        attempts += 1
        left_beta = betas[beta_index]
        right_beta = betas[beta_index + 1]
        left_energy = energies[beta_index]
        right_energy = energies[beta_index + 1]
        log_accept = (left_beta - right_beta) * (left_energy - right_energy)
        if log_accept >= 0.0 or math.log(rng.random()) < log_accept:
            states[beta_index], states[beta_index + 1] = states[beta_index + 1], states[beta_index]
            energies[beta_index], energies[beta_index + 1] = right_energy, left_energy
            accepts += 1
    return attempts, accepts


def disagreement_component(
    model: GridSpinGlass,
    left: list[int],
    right: list[int],
    rng: random.Random,
) -> list[int]:
    disagreement = [index for index, (a, b) in enumerate(zip(left, right)) if a != b]
    if not disagreement:
        return []
    start = rng.choice(disagreement)
    seen = {start}
    stack = [start]
    component: list[int] = []
    while stack:
        index = stack.pop()
        component.append(index)
        for neighbor, _weight in model.adjacency[index]:
            if neighbor not in seen and left[neighbor] != right[neighbor]:
                seen.add(neighbor)
                stack.append(neighbor)
    return component


def try_cluster_move(
    model: GridSpinGlass,
    left: list[int],
    right: list[int],
    left_energy: int,
    right_energy: int,
    rng: random.Random,
    min_cluster_size: int,
    max_cluster_fraction: float,
) -> tuple[int, int, str, int]:
    component = disagreement_component(model, left, right, rng)
    component_size = len(component)
    if component_size < min_cluster_size:
        return left_energy, right_energy, "too_small", component_size
    if component_size > max_cluster_fraction * model.variables:
        return left_energy, right_energy, "too_large", component_size

    for index in component:
        left[index], right[index] = right[index], left[index]

    new_left_energy = model.energy(left)
    new_right_energy = model.energy(right)
    if new_left_energy + new_right_energy != left_energy + right_energy:
        for index in component:
            left[index], right[index] = right[index], left[index]
        return left_energy, right_energy, "rejected", component_size

    return new_left_energy, new_right_energy, "accepted", component_size


def run_algorithm(
    algorithm: str,
    model: GridSpinGlass,
    size: int,
    instance_seed: int,
    run_seed: int,
    sweeps: int,
    betas: list[float],
    icm_interval: int,
    icm_min_beta: float,
    min_cluster_size: int,
    max_cluster_fraction: float,
) -> RunStats:
    if algorithm not in {"pt", "pt_icm"}:
        raise ValueError(f"unknown algorithm: {algorithm}")

    rng = random.Random(run_seed)
    copies = 2
    states = [[random_state(model.variables, rng) for _ in betas] for _ in range(copies)]
    energies = [[model.energy(state) for state in copy_states] for copy_states in states]
    update_orders = [[list(range(model.variables)) for _ in betas] for _ in range(copies)]

    best = min(min(copy_energies) for copy_energies in energies)
    best_trace: list[int] = []
    best_time_trace: list[float] = []
    swap_attempts = 0
    swap_accepts = 0
    cluster_attempts = 0
    cluster_accepts = 0
    cluster_skips_too_small = 0
    cluster_skips_too_large = 0
    accepted_cluster_fractions: list[float] = []

    start = time.perf_counter()
    for sweep in range(sweeps):
        for copy_index in range(copies):
            for beta_index, beta in enumerate(betas):
                energies[copy_index][beta_index] = heatbath_sweep(
                    model=model,
                    state=states[copy_index][beta_index],
                    energy=energies[copy_index][beta_index],
                    beta=beta,
                    order=update_orders[copy_index][beta_index],
                    rng=rng,
                )

        offset = sweep % 2
        for copy_index in range(copies):
            attempts, accepts = try_temperature_swaps(
                states=states[copy_index],
                energies=energies[copy_index],
                betas=betas,
                rng=rng,
                offset=offset,
            )
            swap_attempts += attempts
            swap_accepts += accepts

        if algorithm == "pt_icm" and (sweep + 1) % icm_interval == 0:
            for beta_index, beta in enumerate(betas):
                if beta < icm_min_beta:
                    continue
                cluster_attempts += 1
                left_energy, right_energy, status, cluster_size = try_cluster_move(
                    model=model,
                    left=states[0][beta_index],
                    right=states[1][beta_index],
                    left_energy=energies[0][beta_index],
                    right_energy=energies[1][beta_index],
                    rng=rng,
                    min_cluster_size=min_cluster_size,
                    max_cluster_fraction=max_cluster_fraction,
                )
                energies[0][beta_index] = left_energy
                energies[1][beta_index] = right_energy
                if status == "accepted":
                    cluster_accepts += 1
                    accepted_cluster_fractions.append(cluster_size / model.variables)
                elif status == "too_small":
                    cluster_skips_too_small += 1
                elif status == "too_large":
                    cluster_skips_too_large += 1

        current_best = min(min(copy_energies) for copy_energies in energies)
        best = min(best, current_best)
        best_trace.append(best)
        best_time_trace.append(time.perf_counter() - start)

    wall_seconds = time.perf_counter() - start
    final_best = min(min(copy_energies) for copy_energies in energies)
    cluster_mean_fraction = (
        statistics.fmean(accepted_cluster_fractions) if accepted_cluster_fractions else None
    )

    return RunStats(
        algorithm=algorithm,
        size=size,
        instance_seed=instance_seed,
        run_seed=run_seed,
        variables=model.variables,
        sweeps=sweeps,
        beta_count=len(betas),
        wall_seconds=wall_seconds,
        best_energy=best,
        final_best_energy=final_best,
        best_trace=best_trace,
        best_time_trace=best_time_trace,
        swap_attempts=swap_attempts,
        swap_accepts=swap_accepts,
        cluster_attempts=cluster_attempts,
        cluster_accepts=cluster_accepts,
        cluster_skips_too_small=cluster_skips_too_small,
        cluster_skips_too_large=cluster_skips_too_large,
        cluster_mean_fraction=cluster_mean_fraction,
    )


def time_to_target(run: RunStats, target: float) -> float | None:
    for energy, elapsed in zip(run.best_trace, run.best_time_trace):
        if energy <= target:
            return elapsed
    return None


def sweep_to_target(run: RunStats, target: float) -> int | None:
    for sweep_index, energy in enumerate(run.best_trace, start=1):
        if energy <= target:
            return sweep_index
    return None


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    fraction = index - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def bootstrap_median_ci(
    values: list[float],
    rng: random.Random,
    iterations: int = 2000,
    confidence: float = 0.90,
) -> tuple[float, float] | None:
    if not values:
        return None
    medians = []
    for _ in range(iterations):
        sample = [rng.choice(values) for _ in values]
        medians.append(statistics.median(sample))
    alpha = (1.0 - confidence) / 2.0
    lower = quantile(medians, alpha)
    upper = quantile(medians, 1.0 - alpha)
    if lower is None or upper is None:
        return None
    return lower, upper


def summarize_runs(runs: list[RunStats], target_margin_fraction: float) -> dict[str, object]:
    by_case: dict[tuple[int, int], list[RunStats]] = {}
    for run in runs:
        by_case.setdefault((run.size, run.instance_seed), []).append(run)

    case_targets: dict[tuple[int, int], dict[str, float]] = {}
    for case, case_runs in by_case.items():
        best_observed = min(run.best_energy for run in case_runs)
        margin = max(1.0, abs(best_observed) * target_margin_fraction)
        case_targets[case] = {
            "best_observed_energy": float(best_observed),
            "target_energy": best_observed + margin,
        }

    by_size: dict[int, list[RunStats]] = {}
    for run in runs:
        by_size.setdefault(run.size, []).append(run)

    summaries: dict[str, object] = {}
    for size, size_runs in sorted(by_size.items()):
        by_algorithm = {
            "pt": [run for run in size_runs if run.algorithm == "pt"],
            "pt_icm": [run for run in size_runs if run.algorithm == "pt_icm"],
        }
        algorithm_summaries: dict[str, object] = {}
        for algorithm, algorithm_runs in by_algorithm.items():
            best_values = [run.best_energy for run in algorithm_runs]
            wall_values = [run.wall_seconds for run in algorithm_runs]
            best_gaps = [
                run.best_energy
                - case_targets[(run.size, run.instance_seed)]["best_observed_energy"]
                for run in algorithm_runs
            ]
            target_times: list[float] = []
            target_sweeps: list[int] = []
            for run in algorithm_runs:
                target = case_targets[(run.size, run.instance_seed)]["target_energy"]
                elapsed = time_to_target(run, target)
                if elapsed is not None:
                    target_times.append(elapsed)
                sweep = sweep_to_target(run, target)
                if sweep is not None:
                    target_sweeps.append(sweep)
            cluster_acceptance = None
            cluster_mean_fraction = None
            if algorithm == "pt_icm":
                attempts = sum(run.cluster_attempts for run in algorithm_runs)
                accepts = sum(run.cluster_accepts for run in algorithm_runs)
                cluster_acceptance = accepts / attempts if attempts else None
                fractions = [
                    run.cluster_mean_fraction
                    for run in algorithm_runs
                    if run.cluster_mean_fraction is not None
                ]
                cluster_mean_fraction = statistics.fmean(fractions) if fractions else None
            algorithm_summaries[algorithm] = {
                "runs": len(algorithm_runs),
                "best_energy_min": min(best_values),
                "best_energy_median": statistics.median(best_values),
                "best_energy_mean": statistics.fmean(best_values),
                "best_gap_to_case_best_median": statistics.median(best_gaps),
                "best_gap_to_case_best_mean": statistics.fmean(best_gaps),
                "wall_seconds_median": statistics.median(wall_values),
                "hit_target_runs": len(target_times),
                "target_time_median_seconds": statistics.median(target_times)
                if target_times
                else None,
                "target_time_q80_seconds": quantile(target_times, 0.8),
                "target_sweep_median": statistics.median(target_sweeps)
                if target_sweeps
                else None,
                "target_sweep_q80": quantile([float(value) for value in target_sweeps], 0.8),
                "cluster_acceptance": cluster_acceptance,
                "cluster_mean_fraction": cluster_mean_fraction,
            }

        pt_time = algorithm_summaries["pt"]["target_time_median_seconds"]  # type: ignore[index]
        icm_time = algorithm_summaries["pt_icm"]["target_time_median_seconds"]  # type: ignore[index]
        speedup = None
        if isinstance(pt_time, float) and isinstance(icm_time, float) and icm_time > 0:
            speedup = pt_time / icm_time

        pt_sweep = algorithm_summaries["pt"]["target_sweep_median"]  # type: ignore[index]
        icm_sweep = algorithm_summaries["pt_icm"]["target_sweep_median"]  # type: ignore[index]
        sweep_speedup = None
        if isinstance(pt_sweep, (int, float)) and isinstance(icm_sweep, (int, float)) and icm_sweep > 0:
            sweep_speedup = pt_sweep / icm_sweep

        paired_speedups: list[float] = []
        paired_sweep_speedups: list[float] = []
        paired_gap_deltas: list[float] = []
        paired_both_hit = 0
        paired_pt_only_hit = 0
        paired_icm_only_hit = 0
        paired_neither_hit = 0
        for (case_size, instance_seed), target_info in sorted(case_targets.items()):
            if case_size != size:
                continue
            case_runs = [
                run for run in size_runs if run.instance_seed == instance_seed
            ]
            pt_runs = [run for run in case_runs if run.algorithm == "pt"]
            icm_runs = [run for run in case_runs if run.algorithm == "pt_icm"]
            if not pt_runs or not icm_runs:
                continue
            pt_run = pt_runs[0]
            icm_run = icm_runs[0]
            target = target_info["target_energy"]
            pt_target_time = time_to_target(pt_run, target)
            icm_target_time = time_to_target(icm_run, target)
            pt_target_sweep = sweep_to_target(pt_run, target)
            icm_target_sweep = sweep_to_target(icm_run, target)
            case_best = target_info["best_observed_energy"]
            paired_gap_deltas.append(
                (pt_run.best_energy - case_best) - (icm_run.best_energy - case_best)
            )
            if pt_target_time is not None and icm_target_time is not None:
                paired_both_hit += 1
                if icm_target_time > 0:
                    paired_speedups.append(pt_target_time / icm_target_time)
                if (
                    pt_target_sweep is not None
                    and icm_target_sweep is not None
                    and icm_target_sweep > 0
                ):
                    paired_sweep_speedups.append(pt_target_sweep / icm_target_sweep)
            elif pt_target_time is not None:
                paired_pt_only_hit += 1
            elif icm_target_time is not None:
                paired_icm_only_hit += 1
            else:
                paired_neither_hit += 1

        bootstrap_rng = random.Random(1_000_003 + size)
        paired_speedup_ci = bootstrap_median_ci(paired_speedups, bootstrap_rng)
        paired_sweep_speedup_ci = bootstrap_median_ci(paired_sweep_speedups, bootstrap_rng)

        summaries[str(size)] = {
            "case_targets": {
                str(instance_seed): target
                for (case_size, instance_seed), target in sorted(case_targets.items())
                if case_size == size
            },
            "target_margin_fraction": target_margin_fraction,
            "algorithms": algorithm_summaries,
            "median_time_to_target_speedup_pt_over_pt_icm": speedup,
            "median_sweeps_to_target_speedup_pt_over_pt_icm": sweep_speedup,
            "paired_speedup_values": paired_speedups,
            "paired_speedup_median": statistics.median(paired_speedups)
            if paired_speedups
            else None,
            "paired_speedup_bootstrap_ci_90": paired_speedup_ci,
            "paired_sweep_speedup_values": paired_sweep_speedups,
            "paired_sweep_speedup_median": statistics.median(paired_sweep_speedups)
            if paired_sweep_speedups
            else None,
            "paired_sweep_speedup_bootstrap_ci_90": paired_sweep_speedup_ci,
            "paired_target_both_hit": paired_both_hit,
            "paired_target_pt_only_hit": paired_pt_only_hit,
            "paired_target_pt_icm_only_hit": paired_icm_only_hit,
            "paired_target_neither_hit": paired_neither_hit,
            "paired_best_gap_delta_median": statistics.median(paired_gap_deltas)
            if paired_gap_deltas
            else None,
        }
    return summaries


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sizes(raw_sizes: Iterable[str]) -> list[int]:
    sizes = [int(value) for value in raw_sizes]
    if any(size < 2 for size in sizes):
        raise ValueError("sizes must be at least 2")
    return sizes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", default=["8", "12", "16"])
    parser.add_argument("--instances", type=int, default=5)
    parser.add_argument("--sweeps", type=int, default=300)
    parser.add_argument("--beta-count", type=int, default=12)
    parser.add_argument("--min-beta", type=float, default=0.2)
    parser.add_argument("--max-beta", type=float, default=2.5)
    parser.add_argument("--icm-interval", type=int, default=2)
    parser.add_argument("--icm-min-beta", type=float, default=0.8)
    parser.add_argument("--min-cluster-size", type=int, default=2)
    parser.add_argument("--max-cluster-fraction", type=float, default=0.7)
    parser.add_argument("--target-margin-fraction", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=20260704)
    parser.add_argument("--out", type=Path, default=Path("reference/06-benchmarks/artifacts/cluster-move-benchmark.json"))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    sizes = parse_sizes(args.sizes)
    betas = beta_ladder(args.min_beta, args.max_beta, args.beta_count)
    runs: list[RunStats] = []

    benchmark_started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    for size in sizes:
        for instance_index in range(args.instances):
            instance_seed = args.seed + size * 10_000 + instance_index
            model = make_grid_spin_glass(size, random.Random(instance_seed))
            for algorithm_index, algorithm in enumerate(("pt", "pt_icm")):
                run_seed = args.seed + size * 1_000_000 + instance_index * 10 + algorithm_index
                runs.append(
                    run_algorithm(
                        algorithm=algorithm,
                        model=model,
                        size=size,
                        instance_seed=instance_seed,
                        run_seed=run_seed,
                        sweeps=args.sweeps,
                        betas=betas,
                        icm_interval=args.icm_interval,
                        icm_min_beta=args.icm_min_beta,
                        min_cluster_size=args.min_cluster_size,
                        max_cluster_fraction=args.max_cluster_fraction,
                    )
                )

    payload = {
        "metadata": {
            "benchmark_started": benchmark_started,
            "benchmark_finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "script_path": str(Path(__file__).as_posix()),
            "command": " ".join(os.sys.argv),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "seed": args.seed,
            "parameters": {
                "sizes": sizes,
                "instances": args.instances,
                "sweeps": args.sweeps,
                "beta_count": args.beta_count,
                "min_beta": args.min_beta,
                "max_beta": args.max_beta,
                "icm_interval": args.icm_interval,
                "icm_min_beta": args.icm_min_beta,
                "min_cluster_size": args.min_cluster_size,
                "max_cluster_fraction": args.max_cluster_fraction,
                "target_margin_fraction": args.target_margin_fraction,
            },
            "notes": [
                "Research harness only; this is not a production THRML or TSU kernel.",
                "Target energy is best observed per instance plus a margin, not an exact optimum.",
                "Wall time includes Python cluster labeling and full energy invariant checks.",
            ],
        },
        "summary": summarize_runs(runs, args.target_margin_fraction),
        "runs": [run.__dict__ for run in runs],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    checksum = sha256_file(args.out)
    payload["metadata"]["payload_sha256_before_checksum_field"] = checksum
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    checksum = sha256_file(args.out)
    print(json.dumps({"output": str(args.out), "sha256": checksum, "summary": payload["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
