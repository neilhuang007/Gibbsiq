"""Bounded control/candidate compatibility cycle for the pinned Torx adapter."""

from __future__ import annotations

import argparse
from importlib import metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

MAX_REPORT_BYTES = 32 * 1024 * 1024
TARGET = (0.5, 0.0, 0.25, 0.25)
SAMPLE_TV_LIMIT = 0.10


def _close_vector(observed: object, expected: object, *, tolerance: float = 1e-6) -> bool:
    if not isinstance(observed, list) or not isinstance(expected, list) or len(observed) != len(expected):
        return False
    try:
        return all(
            math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tolerance)
            for a, b in zip(observed, expected)
        )
    except (TypeError, ValueError):
        return False


def _sample_tv(sampling: object) -> float:
    if not isinstance(sampling, dict):
        return math.inf
    draws, counts = sampling.get("draws"), sampling.get("counts")
    if type(draws) is not int or draws <= 0 or not isinstance(counts, list) or len(counts) != 4:
        return math.inf
    if any(type(value) is not int or value < 0 for value in counts) or sum(counts) != draws:
        return math.inf
    return 0.5 * sum(abs(count / draws - target) for count, target in zip(counts, TARGET))


def _probe_checks(probe: dict[str, Any]) -> dict[str, bool]:
    return {
        "adapter_supported": probe.get("adapter", {}).get("status") == "accepted",
        "exact_reference_passed": all(
            _close_vector(probe.get(case, {}).get("observed"), probe.get(case, {}).get("expected"))
            for case in ("exact", "changed_exact")
        ),
        "sample_law_passed": _sample_tv(probe.get("sampling")) <= SAMPLE_TV_LIMIT,
        "dependencies_consistent": probe.get("pip_check", {}).get("exit_code") == 0,
    }


def compare_probes(control: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    control_checks = _probe_checks(control)
    candidate_checks = _probe_checks(candidate)
    if not all(control_checks.values()):
        outcome, recommendation = "invalid_control", "repair_control_before_comparison"
    elif all(candidate_checks.values()):
        outcome, recommendation = "compatible", "candidate_eligible_for_review"
    else:
        outcome, recommendation = "incompatible", "retain_pinned_control"
    variations = [_sample_tv(probe.get("sampling")) for probe in (control, candidate)]
    return {
        "schema": "torx-compatibility-cycle-v1",
        "outcome": outcome,
        "candidate_adapter_supported": candidate_checks["adapter_supported"],
        "candidate_upstream_exact_reference_passed": candidate_checks["exact_reference_passed"],
        "candidate_sample_law_passed": candidate_checks["sample_law_passed"],
        "control_checks": control_checks,
        "candidate_checks": candidate_checks,
        "control": control,
        "candidate": candidate,
        "comparison": {
            "control_exact_reference_passed": control_checks["exact_reference_passed"],
            "control_total_variation": variations[0] if math.isfinite(variations[0]) else None,
            "candidate_total_variation": variations[1] if math.isfinite(variations[1]) else None,
            "sample_tv_limit": SAMPLE_TV_LIMIT,
        },
        "recommendation": recommendation,
    }


def _invoke_probe(python: Path, timeout_seconds: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    command = [str(python), "-I", str(Path(__file__).resolve()), "--probe"]
    environment = {
        key: value for key, value in os.environ.items() if key.upper() not in {"PYTHONPATH", "PYTHONHOME"}
    }
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout_seconds, check=False, env=environment
        )
    except subprocess.TimeoutExpired:
        return None, {"exit_code": None, "timed_out": True}
    status = {"exit_code": result.returncode, "timed_out": False, "stderr": result.stderr[-4000:]}
    if result.returncode:
        return None, status
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        status["stderr"] = (status["stderr"] + "\ninvalid JSON probe output").strip()
        return None, status
    return payload, status


def run_cycle(control_python: Path, candidate_python: Path, *, timeout_seconds: int = 180) -> dict[str, Any]:
    control, control_status = _invoke_probe(control_python, timeout_seconds)
    candidate, candidate_status = _invoke_probe(candidate_python, timeout_seconds)
    if control is None or candidate is None:
        failure = {
            "schema": "torx-compatibility-cycle-v1",
            "outcome": "control_probe_failed" if control is None else "candidate_probe_failed",
            "control_probe": control_status,
            "candidate_probe": candidate_status,
        }
        if control is not None:
            failure["control"] = control
        return failure
    report = compare_probes(control, candidate)
    report["control_probe"] = control_status
    report["candidate_probe"] = candidate_status
    return report


def write_report(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_REPORT_BYTES:
        raise RuntimeError("compatibility report exceeds the 32 MiB artifact limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def _probe() -> dict[str, Any]:
    import jax
    import jax.numpy as jnp
    import numpy as np
    from torx import psc

    import gibbsiq
    from gibbsiq.qualification.adapters.reference import torx_two_gate_reference
    from gibbsiq.qualification.adapters.torx import TorxCircuitBackend
    from gibbsiq.qualification.engine import UnsupportedCapabilityError

    adapter: dict[str, Any]
    backend = TorxCircuitBackend()
    try:
        backend.validate_plan(backend.plan(runs=1, samples=8))
    except UnsupportedCapabilityError as error:
        adapter = {"status": "rejected_unqualified", "reason": str(error)}
    else:
        adapter = {"status": "accepted", "reason": None}

    def circuit_result(
        theta: tuple[float, float], initial: tuple[int, int], *, draws: int = 0
    ) -> tuple[list[float], list[list[int]]]:
        circuit = psc.DiscretePCircuit([psc.PNOT(0), psc.PCNOT([0, 1])])
        angles = [jnp.asarray([theta[0]], dtype=jnp.float32), jnp.asarray([theta[1]], dtype=jnp.float32)]
        simulator = psc.StateVectorSimulator()
        compiled = simulator.build_circuit(circuit, angles)
        state = jnp.zeros((4,), dtype=jnp.float32).at[initial[0] * 2 + initial[1]].set(1.0)
        exact = np.asarray(jax.device_get(simulator.density(compiled, state)), dtype=float).tolist()
        samples: list[list[int]] = []
        if draws:
            keys = jax.random.split(jax.random.key(271828), draws)
            raw = jax.vmap(lambda key: circuit.sample(key, {"in": jnp.asarray(initial)}, angles))(keys)
            samples = np.asarray(jax.device_get(raw), dtype=np.int32).tolist()
        return exact, samples

    exact, samples = circuit_result((0.0, 0.0), (0, 0), draws=2048)
    changed_exact, _ = circuit_result((0.7, -0.4), (1, 1))
    changed_expected = list(torx_two_gate_reference((0.7, -0.4), (1, 1)).probabilities)
    counts = [0, 0, 0, 0]
    for left, right in samples:
        counts[int(left) * 2 + int(right)] += 1
    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"], capture_output=True, text=True, timeout=60, check=False
    )
    return {
        "schema": "torx-compatibility-probe-v1",
        "environment": {
            name.replace("-", "_"): metadata.version(name)
            for name in ("extro-torx", "jax", "jaxlib", "equinox", "numpy")
        }
        | {
            "python": platform.python_version(),
            "gibbsiq": metadata.version("gibbsiq"),
            "gibbsiq_path": str(Path(gibbsiq.__file__).resolve()),
        },
        "pip_check": {
            "exit_code": pip_check.returncode,
            "stdout": pip_check.stdout.strip(),
            "stderr": pip_check.stderr.strip(),
        },
        "adapter": adapter,
        "exact": {"observed": exact, "expected": list(TARGET)},
        "changed_exact": {"observed": changed_exact, "expected": changed_expected},
        "sampling": {"draws": len(samples), "counts": counts},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--control-python", type=Path)
    parser.add_argument("--candidate-python", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(_probe(), sort_keys=True))
        return 0
    if not args.control_python or not args.candidate_python or not args.output:
        parser.error("cycle mode requires --control-python, --candidate-python, and --output")
    if not 1 <= args.timeout_seconds <= 180:
        parser.error("--timeout-seconds must be between 1 and 180")
    report = run_cycle(args.control_python, args.candidate_python, timeout_seconds=args.timeout_seconds)
    write_report(args.output, report)
    print(json.dumps({"outcome": report["outcome"], "output": str(args.output)}))
    return 0 if report["outcome"] == "compatible" else 3


if __name__ == "__main__":
    raise SystemExit(main())
