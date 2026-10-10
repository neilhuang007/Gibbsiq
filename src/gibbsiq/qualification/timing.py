"""Synchronized wall-clock phases and paired observer overhead."""

from __future__ import annotations

import math
import statistics
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from types import MappingProxyType
from typing import Any

from gibbsiq.qualification.contracts import CostScope, _frozen_json_mapping, canonical_json


def _nonnegative(value: Any, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


def _quantile(sorted_values: tuple[float, ...], fraction: float) -> float:
    position = (len(sorted_values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (position - lower)


@dataclass(frozen=True, slots=True)
class TimingSeries:
    durations: tuple[float, ...]
    count: int
    median: float
    minimum: float
    maximum: float
    iqr: float

    @classmethod
    def from_durations(cls, durations: Sequence[float]) -> TimingSeries:
        values = tuple(_nonnegative(value, "duration") for value in durations)
        if not values:
            raise ValueError("timing series must have observations")
        ordered = tuple(sorted(values))
        middle = len(ordered) // 2
        median = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
        return cls(
            values,
            len(values),
            median,
            ordered[0],
            ordered[-1],
            _quantile(ordered, 0.75) - _quantile(ordered, 0.25),
        )


@dataclass(frozen=True, slots=True)
class TimingReport:
    series: Mapping[str, TimingSeries]
    scope: CostScope
    environment: Mapping[str, Any]
    warmups: int


def profile_execution(
    *,
    prepare: Callable[[], Any],
    compile_call: Callable[[Any], Any],
    execute: Callable[[Any], Any],
    synchronize: Callable[[Any], Any],
    handle_output: Callable[[Any], Any],
    scope: CostScope,
    environment: Mapping[str, Any],
    repeats: int = 7,
    warmups: int = 2,
    clock: Callable[[], float] = time.perf_counter,
) -> TimingReport:
    """Measure preparation, explicit compilation, first and warmed synchronized work."""
    if type(repeats) is not int or not 1 <= repeats <= 100:
        raise ValueError("repeats must be an integer from 1 through 100")
    if type(warmups) is not int or not 0 <= warmups <= 100:
        raise ValueError("warmups must be an integer from 0 through 100")
    if not isinstance(scope, CostScope):
        raise ValueError("scope must be CostScope")
    for name, callback in (
        ("prepare", prepare),
        ("compile_call", compile_call),
        ("execute", execute),
        ("synchronize", synchronize),
        ("handle_output", handle_output),
        ("clock", clock),
    ):
        if not callable(callback):
            raise ValueError(f"{name} must be callable")
    frozen_environment = _frozen_json_mapping(environment, name="environment")
    if len(canonical_json(environment)) > 65536:
        raise ValueError("environment exceeds 65536 JSON bytes")

    def timed(callback: Callable[[], Any]) -> tuple[Any, float]:
        start = _nonnegative(clock(), "clock")
        value = callback()
        end = _nonnegative(clock(), "clock")
        if end < start:
            raise ValueError("clock moved backwards")
        return value, end - start

    context, preparation = timed(prepare)
    handle, compilation = timed(lambda: compile_call(context))

    def run() -> Any:
        output = execute(handle)
        synchronize(output)
        return output

    _, first_execution = timed(run)
    for _ in range(warmups):
        run()
    executions: list[float] = []
    handling: list[float] = []
    for _ in range(repeats):
        output, execution_seconds = timed(run)
        _, handling_seconds = timed(partial(handle_output, output))
        executions.append(execution_seconds)
        handling.append(handling_seconds)
        del output
    series = MappingProxyType(
        {
            "preparation": TimingSeries.from_durations((preparation,)),
            "compilation": TimingSeries.from_durations((compilation,)),
            "first_execution": TimingSeries.from_durations((first_execution,)),
            "warmed_execution": TimingSeries.from_durations(executions),
            "output_handling": TimingSeries.from_durations(handling),
        }
    )
    return TimingReport(series, scope, frozen_environment, warmups)


def synchronize_jax(output: Any) -> None:
    """Wait for the complete JAX output pytree after rejecting opaque leaves."""
    import jax
    import numpy as np

    leaves = jax.tree_util.tree_leaves(output)
    for leaf in leaves:
        if leaf is None or type(leaf) in (bool, int, float, complex, str, bytes):
            continue
        if isinstance(leaf, (np.ndarray, np.generic)):
            continue
        if callable(getattr(leaf, "block_until_ready", None)):
            continue
        raise TypeError(f"unsupported asynchronous output leaf {type(leaf).__name__}")
    jax.block_until_ready(output)


@dataclass(frozen=True, slots=True)
class OverheadSummary:
    ratios: tuple[float, ...]
    median: float
    minimum: float
    maximum: float
    target: float
    outcome: str
    limitation: str


def observer_overhead(
    baseline: Sequence[float], observed: Sequence[float], *, target: float = 0.05
) -> OverheadSummary:
    """Describe paired overhead without treating noisy pairs as independent proof."""
    if (
        isinstance(baseline, (str, bytes))
        or not isinstance(baseline, Sequence)
        or isinstance(observed, (str, bytes))
        or not isinstance(observed, Sequence)
    ):
        raise ValueError("timings must be sequences")
    if not baseline or len(baseline) != len(observed):
        raise ValueError("timings must contain equal nonempty paired vectors")
    target = _nonnegative(target, "target")
    pairs = []
    for left, right in zip(baseline, observed):
        base = _nonnegative(left, "baseline")
        seen = _nonnegative(right, "observed")
        if base == 0 or seen == 0:
            raise ValueError("paired timings must be positive")
        ratio = (seen - base) / base
        if not math.isfinite(ratio):
            raise ValueError("overhead ratio is not finite")
        pairs.append(ratio)
    ratios = tuple(pairs)
    if len(ratios) < 5:
        outcome = "inconclusive"
    elif all(ratio <= target for ratio in ratios):
        outcome = "within_target"
    elif all(ratio > target for ratio in ratios):
        outcome = "above_target"
    else:
        outcome = "inconclusive"
    return OverheadSummary(
        ratios,
        statistics.median(ratios),
        min(ratios),
        max(ratios),
        target,
        outcome,
        "Empirical paired observations only; no confidence interval or claim about future latency.",
    )


__all__ = [
    "OverheadSummary",
    "TimingReport",
    "TimingSeries",
    "observer_overhead",
    "profile_execution",
    "synchronize_jax",
]
