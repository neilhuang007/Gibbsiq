"""Exercise an installed optional qualification stack outside the source checkout."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import sysconfig
import time
from typing import Any


_PROFILE_SECONDS = 180.0


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _installed_context() -> dict[str, Any]:
    import gibbsiq

    package_file = Path(gibbsiq.__file__).resolve(strict=True)
    purelib = Path(sysconfig.get_path("purelib")).resolve(strict=True)
    try:
        package_file.relative_to(purelib)
    except ValueError as error:
        raise RuntimeError(
            f"gibbsiq must resolve inside interpreter purelib: module={package_file}, purelib={purelib}"
        ) from error
    source_entries = []
    for entry in sys.path:
        if not entry:
            continue
        path = Path(entry).resolve()
        if (path / "pyproject.toml").is_file() and (path / "src/gibbsiq").is_dir():
            source_entries.append(str(path))
        if path.name == "src" and (path / "gibbsiq").is_dir() and (path.parent / "pyproject.toml").is_file():
            source_entries.append(str(path))
    _require(not source_entries, f"source checkout paths are active: {source_entries!r}")
    installed_version = importlib.metadata.version("gibbsiq")
    _require(installed_version == gibbsiq.__version__, "distribution and runtime versions disagree")
    return {
        "package_file": str(package_file),
        "purelib": str(purelib),
        "version": installed_version,
        "python": sys.version.split()[0],
        "executable": sys.executable,
    }


def _s03() -> dict[str, Any]:
    import numpy as np

    from gibbsiq.conversions import compile_ising
    from gibbsiq.qualification.adapters.reference import torx_two_gate_reference
    from gibbsiq.qualification.adapters.thrml import THRMLIsingBackend
    from gibbsiq.qualification.adapters.torx import TorxCircuitBackend
    from gibbsiq.qualification.engine import derive_randomization

    coupling = math.log(3.0) / 2.0
    thrml_model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): coupling})
    thrml = THRMLIsingBackend(
        thrml_model,
        clamped={"b": 1},
        observed_variables=("a",),
        chains=2,
    )
    thrml_plan = thrml.plan(runs=1, samples=1024, warmup=16, thinning=1)
    thrml.validate_plan(thrml_plan)
    thrml.prepare(thrml_plan.workload)
    thrml_run = thrml_plan.runs[0]
    thrml_stream = derive_randomization(thrml_plan, thrml_run)
    thrml_first = thrml.sample(thrml_run, thrml_stream, retain_states=True)
    thrml_replay = thrml.sample(thrml_run, thrml_stream, retain_states=True)
    thrml_reference = thrml_plan.metric_bindings[0].reference_value
    _require(thrml_first.states.shape == (2, 1024, 1), "THRML retained-state shape changed")
    _require(np.array_equal(thrml_first.states, thrml_replay.states), "THRML replay changed states")
    _require(abs(thrml_first.mean - thrml_reference) < 0.09, "THRML mean missed independent reference")

    theta = (0.7, -0.4)
    initial = (1, 1)
    torx = TorxCircuitBackend(theta=theta, initial=initial, simulator="dfg")
    torx_plan = torx.plan(runs=1, samples=1024)
    torx.validate_plan(torx_plan)
    torx.prepare(torx_plan.workload)
    exact = torx_two_gate_reference(theta, initial)
    upstream = torx.reference_probabilities()
    _require(
        max(abs(observed - expected) for observed, expected in zip(upstream, exact.probabilities)) < 1e-6,
        "Torx upstream density differs from the independent reference",
    )
    torx_run = torx_plan.runs[0]
    torx_stream = derive_randomization(torx_plan, torx_run)
    torx_first = torx.sample(torx_run, torx_stream, retain_states=True)
    torx_replay = torx.sample(torx_run, torx_stream, retain_states=True)
    _require(np.array_equal(torx_first.states, torx_replay.states), "Torx replay changed states")
    counts = np.bincount(torx_first.states[:, 0] * 2 + torx_first.states[:, 1], minlength=4) / 1024
    _require(
        bool(np.all(np.abs(counts - np.asarray(exact.probabilities)) < 0.09)),
        "Torx sampled joint law missed the independent reference",
    )
    return {
        "thrml": {
            "mean": thrml_first.mean,
            "reference_mean": thrml_reference,
            "state_shape": list(thrml_first.states.shape),
            "replay_equal": True,
        },
        "torx": {
            "sampled_probabilities": counts.tolist(),
            "reference_probabilities": list(exact.probabilities),
            "upstream_probabilities": list(upstream),
            "replay_equal": True,
        },
    }


def _s04(output: Path) -> dict[str, Any]:
    import jax
    import numpy as np
    from z1t.components import Config
    from z1t.model import create_model

    from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
    from gibbsiq.qualification.adapters.z1t import TinyZ1TConfig
    from gibbsiq.qualification.engine import derive_randomization
    from gibbsiq.qualification.model_evaluation import tiny_split_manifest
    from gibbsiq.qualification.workflow import qualify

    config = TinyZ1TConfig()
    backend = TinyModelBackend(tiny_split_manifest().evaluation, config=config, initialization_seed=17)
    plan = backend.plan(runs=2, samples=8, max_seconds=150.0, max_bytes=8 * 1024 * 1024)
    backend.validate_plan(plan)
    backend.prepare(plan.workload)

    direct = create_model(
        Config(**asdict(config), aft_kind="conv", tanh_linear=True, tanh_mlp=True, remat=False),
        jax.random.key(17),
    )
    tokens = np.asarray([0, 1, 2, 3], dtype=np.int32)
    numerical = np.asarray(backend.numerical.forward(tokens).logits)
    independent = np.asarray(direct(tokens))
    _require(numerical.shape == (4, 8) and numerical.dtype.name == "float32", "numerical output changed")
    _require(np.isfinite(numerical).all(), "numerical output contains nonfinite values")
    _require(
        np.allclose(numerical, independent, rtol=0.0, atol=1e-6), "numerical output differs from upstream"
    )

    run = plan.runs[0]
    stream = derive_randomization(plan, run)
    first = backend.execute(run, stream)
    replay = backend.execute(run, stream)
    _require(first.observations == replay.observations, "stochastic replay changed observations")
    observed = {item.name: item.values[0] for item in first.observations}
    _require(observed["valid_tokens"] > 0, "complete-model execution observed no valid tokens")
    _require(math.isfinite(observed["capped_nll_degradation"]), "model degradation is nonfinite")
    _require(observed["modeled_spin_draws"] > 0, "stochastic execution recorded no modeled work")

    bundle = output / "qualification"
    report = qualify(
        plan,
        backends={plan.workload.candidate.identity: TinyModelBackend.from_plan(plan)},
        destination=bundle,
    )
    _require(report.execution == "complete", f"tiny-model qualification did not complete: {report.execution}")
    metric = next(item for item in report.metrics if item.metric_id == "capped_nll_degradation")
    _require(
        metric.observed_units == 2 and metric.estimate is not None, "qualification lost planned evidence"
    )
    _require(math.isfinite(metric.estimate), "qualification estimate is nonfinite")
    _require(
        report.qualification in {"pass", "fail", "inconclusive"},
        f"unexpected scientific qualification: {report.qualification}",
    )
    return {
        "numerical": {
            "shape": list(numerical.shape),
            "max_upstream_error": float(np.max(np.abs(numerical - independent))),
        },
        "replay": {
            "equal": True,
            "valid_tokens": observed["valid_tokens"],
            "capped_nll_degradation": observed["capped_nll_degradation"],
            "modeled_spin_draws": observed["modeled_spin_draws"],
        },
        "qualification": {
            "execution": report.execution,
            "qualification": report.qualification,
            "estimate": metric.estimate,
            "interval": None
            if metric.interval is None
            else {"lower": metric.interval.lower, "upper": metric.interval.upper},
            "observed_units": metric.observed_units,
            "bundle": str(bundle),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=("S03", "S04"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output: Path = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    context = _installed_context()
    profile = _s03() if args.profile == "S03" else _s04(output)
    elapsed = time.monotonic() - started
    _require(elapsed <= _PROFILE_SECONDS, f"{args.profile} smoke exceeded {_PROFILE_SECONDS:.0f} seconds")
    result = {
        "schema": "gibbsiq-installed-optional-smoke-v1",
        "status": "passed",
        "profile": args.profile,
        "elapsed_seconds": elapsed,
        "environment": context,
        "evidence": profile,
        "limitations": [
            "Software-only CPU integration evidence; no physical device execution or energy claim.",
            "A scientifically inconclusive qualification remains inconclusive and is not promoted to pass.",
        ],
    }
    (output / "installed-optional-smoke.json").write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
