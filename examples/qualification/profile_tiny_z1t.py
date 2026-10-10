"""Bounded paired CPU profile of generated tiny Z1T observer modes.

Run in the pinned optional environment. This measures software only; it does
not execute Z1 hardware or an unpublished compiler.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the bounded report as JSON")
    parser.add_argument("--time-budget-seconds", type=float, default=300.0)
    args = parser.parse_args()
    if not 0 < args.time_budget_seconds <= 300:
        parser.error("time budget must be positive and at most 300 seconds")

    import jax
    import numpy as np
    from importlib.metadata import version

    from gibbsiq.qualification.adapters.z1t import NumericalZ1T, TinyZ1TConfig
    from gibbsiq.qualification.timing import observer_overhead, synchronize_jax

    started = time.perf_counter()
    deadline = started + args.time_budget_seconds

    def check_budget() -> None:
        if time.perf_counter() > deadline:
            raise TimeoutError("profile exceeded declared local time budget")

    tokens = [0, 1, 2, 3]
    config = TinyZ1TConfig()
    seed = 0
    observer_modes = ("summary", "trace", "serialized_summary")
    paired_rounds = 7
    agreement_atol = 1e-6
    preparation_start = time.perf_counter()
    adapter = NumericalZ1T(config=config, seed=seed)
    preparation_seconds = time.perf_counter() - preparation_start
    compile_start = time.perf_counter()

    def compile_call(executable):
        return executable  # This eager path has no separate compilation step.

    adapter = compile_call(adapter)
    compilation_seconds = time.perf_counter() - compile_start
    selected = (adapter.operations[0].operation_id,)
    trace_cap_bytes = 16384
    report_cap_bytes = 16384

    def forward(mode: str):
        if mode == "baseline":
            return adapter.forward(tokens)
        if mode == "trace":
            return adapter.forward(
                tokens, observe=selected, retention="trace", max_trace_bytes=trace_cap_bytes
            )
        return adapter.forward(tokens, observe=selected, retention="summaries")

    def serialize_summary(result) -> int:
        payload = {}
        for name, capture in result.captures.items():
            payload[name] = {
                key: {
                    field: getattr(getattr(capture, key), field)
                    for field in ("minimum", "maximum", "mean", "rms")
                }
                for key in ("inputs", "field", "output")
            }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(encoded) > report_cap_bytes:
            raise ValueError("serialized report exceeds retention cap")
        return len(encoded)

    def measured(mode: str):
        check_budget()
        begin = time.perf_counter()
        result = forward(mode)
        synchronize_jax({"logits": result.logits})
        execution_seconds = time.perf_counter() - begin
        handling_seconds = 0.0
        report_bytes = 0
        if mode == "serialized_summary":
            begin = time.perf_counter()
            report_bytes = serialize_summary(result)
            handling_seconds = time.perf_counter() - begin
        logits = np.asarray(result.logits)
        return execution_seconds, handling_seconds, report_bytes, logits

    # Eager first use includes dispatch and any lazy backend setup, not pure compilation.
    first_execution, _, _, reference_logits = measured("baseline")
    for mode in ("baseline", *observer_modes):
        _, _, _, logits = measured(mode)
        np.testing.assert_allclose(logits, reference_logits, rtol=0, atol=agreement_atol)

    mode_reports = {}
    for mode in observer_modes:
        baseline = []
        observed = []
        execution_only = []
        handling_only = []
        serialized_sizes = []
        orders = []
        for round_index in range(paired_rounds):
            order = ("baseline", mode) if round_index % 2 == 0 else (mode, "baseline")
            orders.append(order)
            readings = {}
            for condition in order:
                execution, handling, report_bytes, logits = measured(condition)
                np.testing.assert_allclose(logits, reference_logits, rtol=0, atol=agreement_atol)
                readings[condition] = execution + handling
                if condition == mode:
                    execution_only.append(execution)
                    handling_only.append(handling)
                    serialized_sizes.append(report_bytes)
            baseline.append(readings["baseline"])
            observed.append(readings[mode])
        summary = observer_overhead(baseline, observed)
        mode_reports[mode] = {
            "paired_orders": orders,
            "baseline_seconds": baseline,
            "observed_seconds": observed,
            "observed_execution_seconds": execution_only,
            "observed_output_handling_seconds": handling_only,
            "serialized_bytes": serialized_sizes,
            "overhead": asdict(summary),
        }

    report = {
        "schema": "tiny-z1t-observer-profile-v1",
        "claim_boundary": "generated tiny Z1T, complete logits/head, synchronized JAX CPU software wall time",
        "limitations": [
            "No Z1 device, power, physical energy, large checkpoint, or unpublished compiler measurement",
            "Observed adapter path executes eagerly; first execution is not pure compilation",
            f"{paired_rounds} empirical pairs per mode do not establish future latency or a confidence interval",
        ],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "jax": jax.__version__,
            "jaxlib": version("jaxlib"),
            "numpy": np.__version__,
            "equinox": version("equinox"),
            "z1t": version("z1t"),
            "devices": [str(device) for device in jax.devices()],
            "execution_mode": "eager",
            "compile_call": "explicit no-op",
            "seed": seed,
            "config": asdict(config),
            "tokens": tokens,
            "source_identity": adapter.source_identity,
            "parameter_identity": adapter.parameter_identity,
            "operation_map_identity": adapter.operation_map_identity,
        },
        "scope": {
            "included": ["input conversion", "model body", "final vocabulary head", "synchronization"],
            "excluded": ["adapter construction", "first execution", "warmup", "logit invariant check"],
            "batch_size": 1,
            "sequence_length": len(tokens),
            "concurrency": 1,
        },
        "preparation_seconds": preparation_seconds,
        "compilation_seconds": compilation_seconds,
        "first_execution_seconds": first_execution,
        "additional_warmups_per_mode": 1,
        "paired_rounds_per_mode": paired_rounds,
        "selected_operations": selected,
        "trace_cap_bytes": trace_cap_bytes,
        "report_cap_bytes": report_cap_bytes,
        "output_agreement_atol": agreement_atol,
        "modes": mode_reports,
        "elapsed_seconds": time.perf_counter() - started,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
