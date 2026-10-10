"""Bounded execution of frozen qualification plans in a spawned worker."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import multiprocessing
from pathlib import Path
import platform
import sys
import time
from typing import Any, Callable, cast

from gibbsiq.qualification.artifacts import (
    AttemptRecord,
    BundleWriter,
    StorageLimitError,
    cost_from_dict,
    observation_from_dict,
    plan_from_dict,
    record_to_dict,
)
from gibbsiq import __version__ as _package_version
from gibbsiq.qualification.contracts import (
    CostRecord,
    Observation,
    PlannedRun,
    RunPlan,
    _digest,
    canonical_json,
    parse_json,
)


class UnsupportedCapabilityError(ValueError):
    """The declared backend cannot honor a frozen plan."""


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    backend_id: str
    controls: tuple[str, ...]
    observation_names: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.backend_id) is not str or not self.backend_id.strip():
            raise ValueError("backend_id must be nonblank")
        for name, values in (("controls", self.controls), ("observation_names", self.observation_names)):
            if type(values) is not tuple or any(
                type(value) is not str or not value.strip() for value in values
            ):
                raise ValueError(f"{name} must contain nonblank strings")
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must be unique")


@dataclass(frozen=True, slots=True)
class RandomizationIdentity:
    digest: str
    words: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.digest) is not str:
            raise ValueError("randomization digest must be a string")
        _digest(self.digest, name="randomization digest")
        raw = bytes.fromhex(self.digest[7:])
        if tuple(int.from_bytes(raw[index : index + 4], "big") for index in range(0, 32, 4)) != self.words:
            raise ValueError("randomization words must match the full digest")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    observations: tuple[Observation, ...]
    costs: tuple[CostRecord, ...]

    def __post_init__(self) -> None:
        if type(self.observations) is not tuple or any(
            not isinstance(item, Observation) for item in self.observations
        ):
            raise ValueError("observations must be a tuple of Observation")
        if type(self.costs) is not tuple or any(not isinstance(item, CostRecord) for item in self.costs):
            raise ValueError("costs must be a tuple of CostRecord")


@dataclass(frozen=True, slots=True)
class ExecutionSummary:
    plan: RunPlan
    attempts: tuple[AttemptRecord, ...]
    execution: str
    reason: str | None = None


def derive_randomization(plan: RunPlan, run: PlannedRun) -> RandomizationIdentity:
    """Derive the stable v1 stream ID and ordered big-endian uint32 words."""
    if not isinstance(plan, RunPlan) or not isinstance(run, PlannedRun) or run not in plan.runs:
        raise ValueError("run must belong to the supplied plan")
    return _derive_randomization(plan, run, plan.workload.semantic_digest())


def _derive_randomization(plan: RunPlan, run: PlannedRun, workload_digest: str) -> RandomizationIdentity:
    payload = {
        "recipe": "gibbsiq-run-stream-v1",
        "master_seed": plan.workload.randomization.master_seed,
        "workload_digest": workload_digest,
        "case_id": run.case_id,
        "operation_id": run.operation_id,
        "run_id": run.run_id,
        "purpose": run.purpose,
    }
    raw = hashlib.sha256(canonical_json(payload)).digest()
    return RandomizationIdentity(
        "sha256:" + raw.hex(),
        tuple(int.from_bytes(raw[index : index + 4], "big") for index in range(0, 32, 4)),
    )


def _send(connection: Any, message: dict[str, object]) -> None:
    connection.send_bytes(canonical_json(message))


def _receive(connection: Any, max_bytes: int) -> dict[str, Any]:
    payload = parse_json(connection.recv_bytes(maxlength=max_bytes).decode("utf-8"))
    if type(payload) is not dict or type(payload.get("kind")) is not str:
        raise ValueError("invalid worker message")
    return cast(dict[str, Any], payload)


def _worker(connection: Any, backend: object) -> None:
    """The only pickled startup input is the explicitly trusted adapter."""
    try:
        capabilities = backend.capabilities()  # type: ignore[attr-defined]
        if not isinstance(capabilities, BackendCapabilities):
            raise ValueError("adapter must return BackendCapabilities")
        _send(
            connection,
            {
                "kind": "capabilities",
                "backend_id": capabilities.backend_id,
                "controls": list(capabilities.controls),
                "observation_names": list(capabilities.observation_names),
            },
        )
        start = _receive(connection, 64 * 1024 * 1024)
        if start.get("kind") != "start":
            raise ValueError("worker expected start message")
        plan = plan_from_dict(start["plan"])
        validate_plan = getattr(backend, "validate_plan", None)
        if callable(validate_plan):
            validate_plan(plan)
        backend.prepare(plan.workload)  # type: ignore[attr-defined]
        _send(connection, {"kind": "ready"})
        runs = {run.run_id: run for run in plan.runs}
        workload_digest = plan.workload.semantic_digest()
        while True:
            request = _receive(connection, 64 * 1024 * 1024)
            if request["kind"] == "stop":
                return
            if request["kind"] != "run" or request.get("run_id") not in runs:
                raise ValueError("worker received an unplanned run")
            run = runs[request["run_id"]]
            randomization = _derive_randomization(plan, run, workload_digest)
            result = backend.execute(run, randomization)  # type: ignore[attr-defined]
            if not isinstance(result, ExecutionResult):
                raise ValueError("adapter must return ExecutionResult")
            _send(
                connection,
                {
                    "kind": "result",
                    "observations": [record_to_dict(item) for item in result.observations],
                    "costs": [record_to_dict(item) for item in result.costs],
                },
            )
    except UnsupportedCapabilityError as error:
        try:
            reason = str(error).strip()[:240] or "backend capability unsupported"
            _send(connection, {"kind": "unsupported", "reason": reason})
        except (OSError, ValueError):
            pass
    except BaseException as error:
        try:
            _send(connection, {"kind": "error", "reason": f"worker raised {type(error).__name__}"})
        except (OSError, ValueError):
            pass
    finally:
        connection.close()


def _validate_result(result: ExecutionResult, capabilities: BackendCapabilities) -> None:
    if any(observation.name not in capabilities.observation_names for observation in result.observations):
        raise ValueError("adapter observation name is unsupported")


def _check_capabilities(plan: RunPlan, capabilities: BackendCapabilities) -> None:
    if capabilities.backend_id != plan.workload.candidate.identity:
        raise UnsupportedCapabilityError("backend identity does not match the frozen candidate")
    declared = set(plan.workload.controls)
    supported = set(capabilities.controls)
    required_names = {binding.observation_name for binding in plan.metric_bindings}
    if not required_names.issubset(capabilities.observation_names):
        raise UnsupportedCapabilityError(
            f"backend does not declare observations: {sorted(required_names - set(capabilities.observation_names))}"
        )
    for run in plan.runs:
        keys = set(run.settings)
        if not keys.issubset(declared):
            raise ValueError("run settings are not declared by the workload")
        if not keys.issubset(supported):
            raise UnsupportedCapabilityError(f"backend does not support controls: {sorted(keys - supported)}")


def _attempt_id(count: int, identifiers: set[str]) -> str:
    index = count + 1
    while f"attempt-{index:06d}" in identifiers:
        index += 1
    return f"attempt-{index:06d}"


def execute_plan(
    plan: RunPlan,
    *,
    backend: object,
    destination: str | Path,
    resume: bool = False,
    cancel: Callable[[], bool] | None = None,
) -> ExecutionSummary:
    """Run planned attempts with a total deadline, keeping an unfinished evidence store."""
    started = time.monotonic()
    if not isinstance(plan, RunPlan):
        raise ValueError("plan must be RunPlan")
    if type(resume) is not bool or (cancel is not None and not callable(cancel)):
        raise ValueError("resume must be bool and cancel must be callable or None")
    workload_digest = plan.workload.semantic_digest()
    streams = {run.run_id: _derive_randomization(plan, run, workload_digest) for run in plan.runs}
    if len({stream.digest for stream in streams.values()}) != len(streams):
        raise ValueError("planned randomization stream collision")
    environment = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        "package": f"gibbsiq {_package_version}",
        "backend": plan.workload.candidate.identity,
        "notes": "Randomization recipe: gibbsiq-run-stream-v1; backend owns RNG conversion",
    }
    writer = (
        BundleWriter.resume(destination, plan)
        if resume
        else BundleWriter.create(destination, plan, environment=environment)
    )
    attempts = list(writer.attempts)
    attempt_ids = {attempt.attempt_id for attempt in attempts}
    last_by_run = {attempt.run_id: attempt for attempt in attempts}

    def retain(record: AttemptRecord) -> None:
        writer.append_attempt(record)
        attempts.append(record)
        attempt_ids.add(record.attempt_id)
        last_by_run[record.run_id] = record

    completed = {attempt.run_id for attempt in attempts if attempt.execution == "complete"}
    pending = [run for run in plan.runs if run.run_id not in completed]
    if not pending:
        return ExecutionSummary(plan, tuple(attempts), "complete")
    if len(attempts) >= plan.workload.resources.max_jobs:
        return ExecutionSummary(plan, tuple(attempts), "partial", "maximum job attempts exhausted")

    deadline = started + plan.workload.resources.max_seconds
    max_message = min(plan.workload.resources.max_bytes, 64 * 1024 * 1024)
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=True)
    process = context.Process(target=_worker, args=(child, backend))
    execution = "complete"
    reason: str | None = None
    current: PlannedRun | None = None
    storage_exhausted = False
    process_started = False
    try:
        process.start()
        process_started = True
        child.close()

        def await_message() -> dict[str, Any]:
            while True:
                if cancel is not None and cancel():
                    raise _Stopped("cancelled", "execution cancelled")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise _Stopped("partial", "execution deadline exceeded")
                if parent.poll(min(0.05, remaining)):
                    return _receive(parent, max_message)
                if not process.is_alive():
                    raise RuntimeError("worker exited without a result")

        def await_kind(expected: str) -> dict[str, Any]:
            response = await_message()
            if response["kind"] == "unsupported":
                explanation = response.get("reason")
                if type(explanation) is not str or not explanation.strip():
                    raise ValueError("invalid unsupported worker response")
                raise UnsupportedCapabilityError(explanation)
            if response["kind"] == "error":
                raise RuntimeError(str(response.get("reason", "worker failed")))
            if response["kind"] != expected:
                raise ValueError(f"worker expected {expected} response")
            return response

        declared = await_kind("capabilities")
        capabilities = BackendCapabilities(
            declared["backend_id"],
            tuple(declared["controls"]),
            tuple(declared["observation_names"]),
        )
        _check_capabilities(plan, capabilities)
        _send(parent, {"kind": "start", "plan": record_to_dict(plan)})
        await_kind("ready")

        for run in pending:
            if cancel is not None and cancel():
                raise _Stopped("cancelled", "execution cancelled")
            if len(attempts) >= plan.workload.resources.max_jobs:
                raise _Stopped("partial", "maximum job attempts exhausted")
            current = run
            _send(parent, {"kind": "run", "run_id": run.run_id})
            response = await_kind("result")
            prior = last_by_run.get(run.run_id)
            retry_of = None if prior is None else prior.attempt_id
            result = ExecutionResult(
                tuple(observation_from_dict(item) for item in response["observations"]),
                tuple(cost_from_dict(item) for item in response["costs"]),
            )
            _validate_result(result, capabilities)
            record = AttemptRecord(
                run.run_id,
                _attempt_id(len(attempts), attempt_ids),
                "complete",
                streams[run.run_id].digest,
                result.observations,
                result.costs,
                retry_of=retry_of,
            )
            retain(record)
            current = None
        if time.monotonic() > deadline:
            raise _Stopped("partial", "execution deadline exceeded during evidence persistence")
    except _Stopped as stopped:
        execution, reason = stopped.execution, stopped.reason
    except StorageLimitError:
        execution, reason = "partial", "retained storage budget exhausted"
        storage_exhausted = True
    except UnsupportedCapabilityError:
        raise
    except (EOFError, OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        detail = str(error) or "worker connection closed unexpectedly"
        execution, reason = "error", f"execution failed: {type(error).__name__}: {detail[:240]}"
    finally:
        if process_started:
            if process.is_alive():
                try:
                    process.terminate()
                except OSError:
                    pass  # The child may have exited between the check and signal.
            process.join(timeout=0.5)
            if process.is_alive():
                try:
                    process.kill()
                except OSError:
                    pass
                process.join(timeout=0.5)
            if process.is_alive():
                execution, reason = "error", "worker could not be reaped after forced termination"
            else:
                process.close()
        parent.close()
        child.close()
    if current is not None and not storage_exhausted and len(attempts) < plan.workload.resources.max_jobs:
        prior = last_by_run.get(current.run_id)
        record = AttemptRecord(
            current.run_id,
            _attempt_id(len(attempts), attempt_ids),
            "cancelled" if execution == "cancelled" else "error",
            streams[current.run_id].digest,
            reason=reason,
            retry_of=None if prior is None else prior.attempt_id,
        )
        try:
            retain(record)
        except StorageLimitError:
            execution, reason = "partial", "retained storage budget exhausted"
    return ExecutionSummary(plan, tuple(attempts), execution, reason)


@dataclass(frozen=True, slots=True)
class _Stopped(Exception):
    execution: str
    reason: str


__all__ = [
    "BackendCapabilities",
    "RandomizationIdentity",
    "ExecutionResult",
    "ExecutionSummary",
    "UnsupportedCapabilityError",
    "derive_randomization",
    "execute_plan",
]
