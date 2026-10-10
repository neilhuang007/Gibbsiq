"""Bounded, inspectable schema-1 qualification evidence bundles.

Bundle contents are data.  Decoding uses only the value types below and never
loads an adapter, a manifest-named module, or a pickle payload.
"""

from __future__ import annotations

import hashlib
import io
import math
import os
import ast
import stat
from pathlib import Path
from collections.abc import Mapping, Set as AbstractSet
from dataclasses import dataclass, field, fields, is_dataclass
from types import MappingProxyType
from typing import Any

from gibbsiq.qualification._files import atomic_bytes
from gibbsiq.qualification.contracts import (
    Acceptance,
    AcceptanceContract,
    ArrayRef,
    ArtifactIdentity,
    Bounds,
    CostRecord,
    CostScope,
    InputCase,
    InputSpec,
    MetricResult,
    MetricBinding,
    MetricSpec,
    Observation,
    OperationSpec,
    PlannedRun,
    QualificationReport,
    RandomizationSpec,
    ResourceBudget,
    RunPlan,
    WorkloadSpec,
    _digest,
    canonical_json,
    identity_digest,
    parse_json,
)


_BASE = frozenset({"workload.json", "plan.json", "environment.json", "runs.jsonl"})
_FINALS = frozenset({"metrics.json", "costs.json", "report.md", "history.json"})
_MIN_LIMIT = 1
_MAX_ENTRIES = 10_000
_NPY_DTYPES = {
    "bool": ("b1", 1),
    "int8": ("i1", 1),
    "int16": ("i2", 2),
    "int32": ("i4", 4),
    "int64": ("i8", 8),
    "float32": ("f4", 4),
    "float64": ("f8", 8),
}


class StorageLimitError(ValueError):
    """The frozen evidence byte budget cannot retain another payload."""


def _object(data: Any, expected: set[str], *, optional: AbstractSet[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(data, dict) or any(type(key) is not str for key in data):
        raise ValueError("expected a JSON object")
    missing = expected - data.keys()
    unknown = data.keys() - expected - optional
    if missing or unknown:
        raise ValueError(f"unexpected schema fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
    return data


def _construct(cls: type, data: Any, *, optional: AbstractSet[str] = frozenset()) -> Any:
    """Construct one explicitly selected value type from exact JSON fields."""
    required = {item.name for item in fields(cls) if item.init} - optional
    source = _object(data, required, optional=optional)
    try:
        return cls(**source)
    except (TypeError, KeyError) as error:
        raise ValueError(f"invalid {cls.__name__} record") from error


def _list(data: Any, *, name: str) -> list[Any]:
    if type(data) is not list:
        raise ValueError(f"{name} must be a JSON array")
    return data


def _plain(value: Any) -> Any:
    """Encode only the known schema-1 value graph."""
    if isinstance(value, WorkloadSpec):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {key: _plain(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(child) for child in value]
    known = (
        Acceptance,
        AcceptanceContract,
        ArrayRef,
        ArtifactIdentity,
        Bounds,
        CostRecord,
        CostScope,
        InputCase,
        InputSpec,
        MetricResult,
        MetricSpec,
        Observation,
        OperationSpec,
        PlannedRun,
        MetricBinding,
        QualificationReport,
        RandomizationSpec,
        ResourceBudget,
        RunPlan,
        AttemptRecord,
    )
    if isinstance(value, known):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value) if item.init}
    if value is None or type(value) in {str, int, float, bool}:
        return value
    raise ValueError(f"unsupported record type {type(value).__name__}")


def record_to_dict(value: Any) -> dict[str, Any]:
    """Encode a known schema-1 record into finite plain JSON data."""
    if not is_dataclass(value) or isinstance(value, type):
        raise ValueError("unsupported schema-1 root record")
    result = _plain(value)
    canonical_json(result)
    return result


def _identity(data: Any) -> ArtifactIdentity:
    return _construct(ArtifactIdentity, data)


def _scope(data: Any) -> CostScope:
    return _construct(
        CostScope, data, optional={"excluded_components", "batch_size", "concurrency", "sequence_length"}
    )


def _contract(data: Any) -> AcceptanceContract:
    source = _object(data, {"metrics", "alpha_total", "schema_version"})
    metrics = []
    for raw in _list(source["metrics"], name="metrics"):
        metric = _object(raw, {item.name for item in fields(MetricSpec) if item.init})
        acceptance = _construct(Acceptance, metric["acceptance"])
        bounds = None if metric["bounds"] is None else _construct(Bounds, metric["bounds"])
        metrics.append(MetricSpec(**{**metric, "acceptance": acceptance, "bounds": bounds}))
    return AcceptanceContract(tuple(metrics), source["alpha_total"], source["schema_version"])


def workload_from_dict(data: Any) -> WorkloadSpec:
    """Decode a complete known workload; unsupported fields and versions fail."""
    source = _object(data, {item.name for item in fields(WorkloadSpec) if item.init})
    inputs = _object(source["inputs"], {item.name for item in fields(InputSpec) if item.init})
    decoded_inputs = InputSpec(
        identity=_identity(inputs["identity"]),
        preprocessing=_identity(inputs["preprocessing"]),
        cases=tuple(_construct(InputCase, item) for item in _list(inputs["cases"], name="cases")),
        tokenizer=None if inputs["tokenizer"] is None else _identity(inputs["tokenizer"]),
        sequence_length=inputs["sequence_length"],
        masks_digest=inputs["masks_digest"],
    )
    return WorkloadSpec(
        **{
            **source,
            "sources": tuple(_identity(item) for item in _list(source["sources"], name="sources")),
            "model_config": _identity(source["model_config"]),
            "inputs": decoded_inputs,
            "operations": tuple(
                _construct(OperationSpec, item) for item in _list(source["operations"], name="operations")
            ),
            "reference": _identity(source["reference"]),
            "candidate": _identity(source["candidate"]),
            "contract": _contract(source["contract"]),
            "randomization": _construct(
                RandomizationSpec, source["randomization"], optional={"replication_unit"}
            ),
            "resources": _construct(ResourceBudget, source["resources"]),
            "cost_scope": _scope(source["cost_scope"]),
            "checkpoint": None if source["checkpoint"] is None else _identity(source["checkpoint"]),
        }
    )


def plan_from_dict(data: Any) -> RunPlan:
    source = _object(data, {"workload", "runs", "schema_version"}, optional={"metric_bindings"})
    return RunPlan(
        workload_from_dict(source["workload"]),
        tuple(_construct(PlannedRun, item) for item in _list(source["runs"], name="runs")),
        source["schema_version"],
        tuple(
            _construct(MetricBinding, item, optional={"reference_value"})
            for item in _list(source.get("metric_bindings", []), name="metric_bindings")
        ),
    )


def _array_from_dict(data: Any) -> ArrayRef:
    return _construct(ArrayRef, data)


def observation_from_dict(data: Any) -> Observation:
    source = _object(data, {item.name for item in fields(Observation) if item.init})
    return Observation(
        **{
            **source,
            "array": None if source["array"] is None else _array_from_dict(source["array"]),
        }
    )


def cost_from_dict(data: Any) -> CostRecord:
    source = _object(data, {item.name for item in fields(CostRecord) if item.init})
    return CostRecord(**{**source, "scope": _scope(source["scope"])})


def attempt_from_dict(data: Any) -> AttemptRecord:
    source = _object(data, {item.name for item in fields(AttemptRecord) if item.init})
    return AttemptRecord(
        **{
            **source,
            "observations": tuple(
                observation_from_dict(item) for item in _list(source["observations"], name="observations")
            ),
            "costs": tuple(cost_from_dict(item) for item in _list(source["costs"], name="costs")),
        }
    )


def _report_from_dict(data: Any) -> QualificationReport:
    source = _object(data, {item.name for item in fields(QualificationReport) if item.init})
    metrics = []
    for raw in _list(source["metrics"], name="metrics"):
        metric = _object(raw, {item.name for item in fields(MetricResult) if item.init})
        interval = None if metric["interval"] is None else _construct(Bounds, metric["interval"])
        metrics.append(MetricResult(**{**metric, "interval": interval}))
    return QualificationReport(
        **{
            **source,
            "contract": _contract(source["contract"]),
            "metrics": tuple(metrics),
        }
    )


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    run_id: str
    attempt_id: str
    execution: str
    randomization: str
    observations: tuple[Observation, ...] = ()
    costs: tuple[CostRecord, ...] = ()
    reason: str | None = None
    retry_of: str | None = None

    def __post_init__(self) -> None:
        for name in ("run_id", "attempt_id"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"{name} must be a nonblank string")
            object.__setattr__(self, name, value.strip())
        if self.execution not in {"complete", "error", "cancelled"}:
            raise ValueError("attempt execution must be complete, error or cancelled")
        if type(self.randomization) is not str:
            raise ValueError("randomization must be a full prefixed SHA-256 stream ID")
        _digest(self.randomization, name="randomization")
        observations = tuple(self.observations)
        costs = tuple(self.costs)
        if any(not isinstance(item, Observation) for item in observations):
            raise ValueError("observations must contain Observation values")
        if any(not isinstance(item, CostRecord) for item in costs):
            raise ValueError("costs must contain CostRecord values")
        if self.execution != "complete" and observations:
            raise ValueError("failed attempts cannot contain normal observations")
        if self.execution != "complete" and (type(self.reason) is not str or not self.reason.strip()):
            raise ValueError("failed attempts require a reason")
        if self.reason is not None and (type(self.reason) is not str or not self.reason.strip()):
            raise ValueError("reason must be nonblank when supplied")
        if self.retry_of is not None and (type(self.retry_of) is not str or not self.retry_of.strip()):
            raise ValueError("retry_of must be nonblank when supplied")
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "costs", costs)


@dataclass(frozen=True, slots=True)
class BundleSnapshot:
    plan: RunPlan
    attempts: tuple[AttemptRecord, ...]
    report: QualificationReport | None
    execution: str
    qualification: str
    payload_validation: str
    reason: str | None
    environment: Mapping[str, str] = field(default_factory=dict)
    manifest_digest: str | None = None
    retained_bytes: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "environment", MappingProxyType(_environment(self.environment)))


def _hash(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _is_link(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(attributes & reparse)


def _path(root: Path, relative: str) -> Path:
    if (
        type(relative) is not str
        or not relative
        or "\\" in relative
        or ":" in relative
        or relative.startswith("/")
    ):
        raise ValueError("unsafe bundle path")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("unsafe bundle path")
    if _is_link(root):
        raise ValueError("bundle root must not be a link")
    result = root
    for part in parts:
        result = result / part
        if result.exists() or result.is_symlink():
            if _is_link(result):
                raise ValueError("bundle contains a linked path")
    return result


def _files(root: Path, maximum: int) -> dict[str, int]:
    if not root.is_dir() or _is_link(root):
        raise ValueError("bundle destination must be a regular directory")
    result: dict[str, int] = {}
    total = 0
    entries = 0
    for parent, directories, files in os.walk(root, followlinks=False):
        entries += len(directories) + len(files)
        if entries > _MAX_ENTRIES:
            raise ValueError("bundle exceeds payload entry limit")
        for name in directories:
            directory = Path(parent) / name
            if _is_link(directory):
                raise ValueError("bundle contains a linked directory")
        for name in files:
            candidate = Path(parent) / name
            if _is_link(candidate) or not candidate.is_file():
                raise ValueError("bundle contains an unsafe payload")
            relative = candidate.relative_to(root).as_posix()
            if relative in result:
                raise ValueError("duplicate payload path")
            size = candidate.stat().st_size
            total += size
            if total > maximum:
                raise ValueError("bundle exceeds cumulative byte limit")
            result[relative] = size
    return result


def _read(root: Path, relative: str, sizes: Mapping[str, int]) -> bytes:
    if relative not in sizes:
        raise ValueError(f"missing bundle payload {relative!r}")
    path = _path(root, relative)
    with path.open("rb") as stream:
        payload = stream.read(sizes[relative] + 1)
    if len(payload) != sizes[relative]:
        raise ValueError(f"bundle payload {relative!r} changed during inspection")
    return payload


def _json(root: Path, relative: str, sizes: Mapping[str, int]) -> Any:
    try:
        return parse_json(_read(root, relative, sizes).decode("utf-8"))
    except UnicodeError as error:
        raise ValueError(f"bundle payload {relative!r} is not UTF-8") from error


def _atomic(root: Path, relative: str, payload: bytes, limit: int) -> None:
    target = _path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    sizes = _files(root, limit)
    old_size = sizes.get(relative, 0)
    if sum(sizes.values()) - old_size + len(payload) > limit:
        raise StorageLimitError("bundle byte budget exceeded")
    atomic_bytes(target, payload)


def _attempts(root: Path, sizes: Mapping[str, int], plan: RunPlan) -> tuple[AttemptRecord, ...]:
    payload = _read(root, "runs.jsonl", sizes)
    if payload and not payload.endswith(b"\n"):
        raise ValueError("torn attempt journal")
    if payload.count(b"\n") > plan.workload.resources.max_jobs:
        raise ValueError("attempt journal exceeds max_jobs")
    rows = payload.splitlines()
    if len(rows) > plan.workload.resources.max_jobs:
        raise ValueError("attempt journal exceeds max_jobs")
    attempts: list[AttemptRecord] = []
    attempt_ids: set[str] = set()
    last_by_run: dict[str, AttemptRecord] = {}
    run_map = {run.run_id: run for run in plan.runs}
    operation_map = {operation.operation_id: operation for operation in plan.workload.operations}
    for line in rows:
        try:
            wrapper = parse_json(line.decode("utf-8"))
        except UnicodeError as error:
            raise ValueError("attempt journal is not UTF-8") from error
        wrapper = _object(wrapper, {"record", "digest"})
        if wrapper["digest"] != identity_digest(wrapper["record"]):
            raise ValueError("attempt journal row digest mismatch")
        record = attempt_from_dict(wrapper["record"])
        _validate_attempt(
            plan,
            attempts,
            record,
            attempt_ids=attempt_ids,
            last_by_run=last_by_run,
            run_map=run_map,
            operation_map=operation_map,
        )
        attempts.append(record)
        attempt_ids.add(record.attempt_id)
        last_by_run[record.run_id] = record
    return tuple(attempts)


def _validate_attempt(
    plan: RunPlan,
    previous: list[AttemptRecord] | tuple[AttemptRecord, ...],
    record: AttemptRecord,
    *,
    attempt_ids: set[str] | None = None,
    last_by_run: Mapping[str, AttemptRecord] | None = None,
    run_map: Mapping[str, PlannedRun] | None = None,
    operation_map: Mapping[str, OperationSpec] | None = None,
) -> None:
    run = (run_map if run_map is not None else {item.run_id: item for item in plan.runs}).get(record.run_id)
    if run is None:
        raise ValueError("attempt names an unplanned run")
    if (
        record.attempt_id in attempt_ids
        if attempt_ids is not None
        else any(item.attempt_id == record.attempt_id for item in previous)
    ):
        raise ValueError("duplicate attempt ID")
    prior = (
        last_by_run.get(record.run_id)
        if last_by_run is not None
        else next((item for item in reversed(previous) if item.run_id == record.run_id), None)
    )
    if prior is not None:
        if prior.execution == "complete":
            raise ValueError("a completed run cannot be retried")
        if record.retry_of != prior.attempt_id or record.randomization != prior.randomization:
            raise ValueError("retry must link the preceding failed attempt and preserve its stream")
    elif record.retry_of is not None:
        raise ValueError("first attempt cannot be a retry")
    operation = (
        operation_map
        if operation_map is not None
        else {item.operation_id: item for item in plan.workload.operations}
    )[run.operation_id]
    names: set[str] = set()
    for observation in record.observations:
        if (observation.run_id, observation.context_id, observation.operation_id) != (
            run.run_id,
            run.case_id,
            run.operation_id,
        ):
            raise ValueError("observation contradicts planned run identity")
        if (observation.shape, observation.axes) != (operation.shape, operation.axes):
            raise ValueError("observation contradicts planned operation shape or axes")
        if observation.name in names:
            raise ValueError("duplicate observation name in attempt")
        names.add(observation.name)


def _report_check(
    plan: RunPlan, attempts: tuple[AttemptRecord, ...], report: QualificationReport, execution: str
) -> None:
    from gibbsiq.qualification.statistics import evaluate_metric, evaluate_metrics

    completed_ids = {item.run_id for item in attempts if item.execution == "complete"}
    completed = tuple(run.run_id for run in plan.runs if run.run_id in completed_ids)
    if report.workload_digest != plan.workload.semantic_digest() or report.contract != plan.workload.contract:
        raise ValueError("report contradicts workload identity or acceptance contract")
    if report.expected_run_ids != tuple(run.run_id for run in plan.runs):
        raise ValueError("report expected runs contradict plan")
    if set(report.completed_run_ids) != set(completed) or report.execution != execution:
        raise ValueError("report completed runs or execution contradict journal")
    if report.qualification in {"invalid", "unsupported"} and any(
        result.availability == "available" and result.outcome == "pass" for result in report.metrics
    ):
        raise ValueError("invalid or unsupported report cannot claim a passing metric")
    if plan.metric_bindings:
        try:
            actual = evaluate_metrics(plan.workload.contract, bound_metric_values(plan, attempts))
        except ValueError:
            if report.qualification not in {"invalid", "unsupported"} or any(
                result.availability != "unavailable" for result in report.metrics
            ):
                raise
        else:
            if report.qualification not in {"invalid", "unsupported"} and report.metrics != actual:
                raise ValueError("report metrics contradict bound observations")
    for result, spec in zip(report.metrics, report.contract.metrics):
        if result.availability != "available":
            continue
        alpha = report.contract.alpha_for(spec.metric_id) if spec.mandatory else report.contract.alpha_total
        recomputed = evaluate_metric(
            spec, result.unit_summaries, alpha=alpha if spec.evidence_mode == "bounded_fixed_n" else None
        )
        if (result.estimate, result.interval, result.outcome, result.observed_units, result.alpha) != (
            recomputed.estimate,
            recomputed.interval,
            recomputed.outcome,
            recomputed.observed_units,
            recomputed.alpha,
        ):
            raise ValueError("stored metric contradicts retained unit summaries")
    mandatory = [
        (result, spec) for result, spec in zip(report.metrics, report.contract.metrics) if spec.mandatory
    ]
    if report.qualification in {"pass", "fail", "inconclusive"}:
        expected = (
            "fail"
            if any(result.outcome == "fail" for result, _ in mandatory)
            else (
                "pass"
                if execution == "complete" and all(result.outcome == "pass" for result, _ in mandatory)
                else "inconclusive"
            )
        )
        if report.qualification != expected:
            raise ValueError("report qualification contradicts mandatory metrics")


def bound_metric_values(
    plan: RunPlan, attempts: tuple[AttemptRecord, ...] | list[AttemptRecord]
) -> dict[str, tuple[float, ...]]:
    """Reconstruct ordered metric units from completed, named scalar observations."""
    if not isinstance(plan, RunPlan) or not plan.metric_bindings:
        raise ValueError("plan requires explicit metric bindings")
    by_run = {item.run_id: item for item in attempts if item.execution == "complete"}
    values_by_id: dict[str, tuple[float, ...]] = {}
    for binding in plan.metric_bindings:
        units: list[float] = []
        for run_id in binding.run_ids:
            attempt = by_run.get(run_id)
            if attempt is None:
                continue
            matches = [item for item in attempt.observations if item.name == binding.observation_name]
            if (
                len(matches) != 1
                or matches[0].shape != ()
                or matches[0].values is None
                or type(matches[0].values[0]) not in {int, float}
            ):
                raise ValueError(
                    "bound metric requires one retained numeric scalar observation per completed run"
                )
            summary = float(matches[0].values[0]) - binding.reference_value
            if not math.isfinite(summary):
                raise ValueError("bound metric summary is nonfinite")
            units.append(0.0 if summary == 0.0 else summary)
        values_by_id[binding.metric_id] = tuple(units)
    return values_by_id


def _npy_header(payload: bytes, ref: ArrayRef, limit: int) -> None:
    if len(payload) < 10 or payload[:6] != b"\x93NUMPY":
        raise ValueError("invalid NPY signature")
    major, minor = payload[6], payload[7]
    if (major, minor) not in {(1, 0), (2, 0), (3, 0)}:
        raise ValueError("unsupported NPY version")
    width = 2 if major == 1 else 4
    offset = 8 + width
    header_length = int.from_bytes(payload[8:offset], "little")
    if header_length > 4096 or offset + header_length > len(payload):
        raise ValueError("NPY header exceeds bounded size")
    try:
        header = ast.literal_eval(payload[offset : offset + header_length].decode("latin1"))
    except (ValueError, SyntaxError, UnicodeError, RecursionError) as error:
        raise ValueError("invalid NPY header") from error
    header = _object(header, {"descr", "fortran_order", "shape"})
    descriptor = header["descr"]
    if (
        type(descriptor) is not str
        or len(descriptor) != 3
        or descriptor[0] not in "<>|="
        or descriptor[1:] != _NPY_DTYPES[ref.dtype][0]
    ):
        raise ValueError("NPY dtype contradicts array reference")
    if header["fortran_order"] is not False or header["shape"] != ref.shape:
        raise ValueError("NPY shape or storage order contradicts array reference")
    count = math.prod(ref.shape)
    byte_count = count * _NPY_DTYPES[ref.dtype][1]
    if byte_count > limit or offset + header_length + byte_count != len(payload):
        raise ValueError("NPY allocation or payload length is invalid")


def _array_check(root: Path, sizes: Mapping[str, int], ref: ArrayRef, *, verify: bool, limit: int) -> bool:
    if not ref.path.startswith("arrays/") or not ref.path.endswith(".npy"):
        raise ValueError("array reference must name an arrays/*.npy payload")
    payload = _read(root, ref.path, sizes)
    if ref.byte_length != sizes.get(ref.path) or _hash(payload) != ref.digest:
        raise ValueError("array reference length or digest mismatch")
    element_count = math.prod(ref.shape)
    if element_count > limit // _NPY_DTYPES[ref.dtype][1]:
        raise ValueError("declared array allocation exceeds byte limit")
    _npy_header(payload, ref, limit)
    if not verify:
        return False
    try:
        import numpy as np
    except ImportError:
        return False
    stream = io.BytesIO(payload)
    try:
        values = np.load(stream, allow_pickle=False)
    except (ValueError, EOFError, OSError) as error:
        raise ValueError("invalid NPY payload") from error
    if (values.dtype.name, values.shape) != (ref.dtype, ref.shape):
        raise ValueError("array dtype or shape mismatch")
    if values.dtype.hasobject or values.dtype.fields is not None or not values.flags.c_contiguous:
        raise ValueError("unsupported array layout")
    if stream.tell() != len(payload):
        raise ValueError("trailing data in NPY payload")
    if values.dtype.kind == "f" and not bool(np.isfinite(values).all()):
        raise ValueError("nonfinite normal observation array")
    return True


def _inventory(root: Path, sizes: Mapping[str, int]) -> dict[str, dict[str, Any]]:
    return {
        name: {"byte_length": size, "digest": _hash(_read(root, name, sizes))}
        for name, size in sorted(sizes.items())
        if name != "manifest.json"
    }


def _environment(value: Mapping[str, Any] | None) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("environment must be a mapping")
    allowed = {"python", "platform", "backend", "device", "package", "notes"}
    if set(value) - allowed or any(type(key) is not str for key in value):
        raise ValueError("environment contains unknown fields")
    if any(type(item) is not str or len(item) > 512 for item in value.values()):
        raise ValueError("environment values must be short strings")
    result = dict(value)
    if len(canonical_json(result)) > 4096:
        raise ValueError("environment is too large")
    return result


def _inspect(destination: Path, *, verify: bool, max_bytes: int) -> BundleSnapshot:
    if type(verify) is not bool:
        raise ValueError("verify must be boolean")
    if type(max_bytes) is not int or max_bytes < _MIN_LIMIT:
        raise ValueError("max_bytes must be a positive integer")
    sizes = _files(destination, max_bytes)
    if not _BASE.issubset(sizes):
        raise ValueError("bundle lacks required frozen files")
    plan = plan_from_dict(_json(destination, "plan.json", sizes))
    workload = workload_from_dict(_json(destination, "workload.json", sizes))
    if record_to_dict(plan.workload) != record_to_dict(workload):
        raise ValueError("plan and workload payloads disagree")
    if sum(sizes.values()) > plan.workload.resources.max_bytes:
        raise ValueError("bundle exceeds frozen workload byte budget")
    environment = _environment(_json(destination, "environment.json", sizes))
    attempts = _attempts(destination, sizes, plan)
    array_refs = list(
        dict.fromkeys(
            observation.array
            for attempt in attempts
            for observation in attempt.observations
            if observation.array is not None
        )
    )
    array_paths = {ref.path for ref in array_refs}
    other_arrays = {name for name in sizes if name.startswith("arrays/")}
    if not other_arrays.issuperset(array_paths):
        raise ValueError("missing referenced array")
    if set(sizes) - _BASE - _FINALS - {"manifest.json"} - other_arrays:
        raise ValueError("bundle contains an unrecognized payload")
    if any(not name.endswith(".npy") for name in other_arrays):
        raise ValueError("unsupported array payload")
    manifest: dict[str, Any] | None = None
    manifest_digest = None
    if "manifest.json" in sizes:
        manifest_bytes = _read(destination, "manifest.json", sizes)
        manifest_digest = _hash(manifest_bytes)
        manifest = _object(
            parse_json(manifest_bytes.decode("utf-8")),
            {
                "schema_version",
                "workload_digest",
                "plan_digest",
                "execution",
                "qualification",
                "reason",
                "files",
            },
        )
        if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
            raise ValueError("unsupported manifest schema version")
        if manifest["workload_digest"] != plan.workload.semantic_digest():
            raise ValueError("manifest workload identity mismatch")
        if manifest["plan_digest"] != identity_digest(record_to_dict(plan)):
            raise ValueError("manifest plan identity mismatch")
        listed = _object(manifest["files"], set(sizes) - {"manifest.json"})
        for name, properties in listed.items():
            _path(destination, name)
            item = _object(properties, {"byte_length", "digest"})
            if type(item["byte_length"]) is not int or item["byte_length"] != sizes[name]:
                raise ValueError("manifest payload length mismatch")
            if item["digest"] != _hash(_read(destination, name, sizes)):
                raise ValueError("manifest payload digest mismatch")
        execution = manifest["execution"]
        qualification = manifest["qualification"]
        reason = manifest["reason"]
    else:
        execution = "partial"
        qualification = "inconclusive"
        reason = "bundle has no final manifest"
    if execution not in {"complete", "partial", "error", "cancelled"}:
        raise ValueError("unsupported execution state")
    if qualification not in {"pass", "fail", "inconclusive", "invalid", "unsupported"}:
        raise ValueError("unsupported qualification state")
    completed = {item.run_id for item in attempts if item.execution == "complete"}
    if execution == "complete" and completed != {run.run_id for run in plan.runs}:
        raise ValueError("complete bundle is missing planned runs")
    if execution != "complete" and qualification == "pass":
        raise ValueError("incomplete bundle cannot pass")
    if manifest is not None and "metrics.json" in sizes:
        stored_report = _report_from_dict(_json(destination, "metrics.json", sizes))
        _report_check(plan, attempts, stored_report, execution)
        if stored_report.qualification != qualification:
            raise ValueError("manifest and report qualification disagree")
    else:
        stored_report = None
        if manifest is not None and qualification in {"pass", "fail"}:
            raise ValueError("successful qualification requires stored metrics")
    if manifest is not None and "costs.json" in sizes:
        costs = _json(destination, "costs.json", sizes)
        if not isinstance(costs, list):
            raise ValueError("costs payload must be a list")
        stored_costs = tuple(cost_from_dict(item) for item in costs)
        expected_costs = tuple(cost for attempt in attempts for cost in attempt.costs)
        if stored_costs != expected_costs:
            raise ValueError("stored costs contradict attempt journal")
    if manifest is not None and "report.md" in sizes:
        try:
            _read(destination, "report.md", sizes).decode("utf-8")
        except UnicodeError as error:
            raise ValueError("human report is not UTF-8") from error
    if "history.json" in sizes:
        history = _json(destination, "history.json", sizes)
        if not isinstance(history, list) or any(not isinstance(item, dict) for item in history):
            raise ValueError("invalid terminal history")
    all_verified = not bool(other_arrays - array_paths)
    if manifest is not None and execution == "complete" and not all_verified:
        raise ValueError("completed bundle contains unreferenced arrays")
    for ref in array_refs:
        all_verified = (
            _array_check(
                destination,
                sizes,
                ref,
                verify=verify,
                limit=min(max_bytes, plan.workload.resources.max_bytes),
            )
            and all_verified
        )
    if verify and not all_verified:
        qualification = "unsupported"
        reason = "NumPy is required to verify NPY evidence"
    return BundleSnapshot(
        plan,
        attempts,
        stored_report,
        execution,
        qualification,
        "verified" if all_verified else "unavailable",
        reason,
        environment,
        manifest_digest,
        sum(sizes.values()),
    )


def inspect_bundle(
    destination: str | Path, *, verify: bool = True, max_bytes: int = 64 * 1024 * 1024
) -> BundleSnapshot:
    """Read and validate a bounded evidence bundle without executing a model."""
    return _inspect(Path(destination), verify=verify, max_bytes=max_bytes)


class BundleWriter:
    """A writer bound to a frozen plan and one evidence directory."""

    def __init__(
        self, destination: Path, plan: RunPlan, attempts: tuple[AttemptRecord, ...], used_bytes: int
    ) -> None:
        self.destination = destination
        self.plan = plan
        self._attempts = list(attempts)
        self._attempt_ids = {item.attempt_id for item in attempts}
        self._last_by_run = {item.run_id: item for item in attempts}
        self._run_map = {item.run_id: item for item in plan.runs}
        self._operation_map = {item.operation_id: item for item in plan.workload.operations}
        self._used_bytes = used_bytes
        self._journal_size = _path(destination, "runs.jsonl").stat().st_size

    @property
    def attempts(self) -> tuple[AttemptRecord, ...]:
        """The validated attempts already loaded or retained by this writer."""
        return tuple(self._attempts)

    @classmethod
    def create(
        cls, destination: str | Path, plan: RunPlan, *, environment: Mapping[str, Any] | None = None
    ) -> BundleWriter:
        if not isinstance(plan, RunPlan):
            raise ValueError("plan must be RunPlan")
        root = Path(destination)
        if root.exists():
            if _is_link(root) or not root.is_dir() or any(root.iterdir()):
                raise ValueError("bundle destination must be empty")
        else:
            root.mkdir(parents=True)
        limit = plan.workload.resources.max_bytes
        payloads = {
            "workload.json": canonical_json(record_to_dict(plan.workload)),
            "plan.json": canonical_json(record_to_dict(plan)),
            "environment.json": canonical_json(_environment(environment)),
            "runs.jsonl": b"",
        }
        if sum(map(len, payloads.values())) > limit:
            raise StorageLimitError("frozen bundle metadata exceeds byte budget")
        for name, payload in payloads.items():
            _atomic(root, name, payload, limit)
        return cls(root, plan, (), sum(map(len, payloads.values())))

    @classmethod
    def resume(cls, destination: str | Path, plan: RunPlan) -> BundleWriter:
        if not isinstance(plan, RunPlan):
            raise ValueError("plan must be RunPlan")
        root = Path(destination)
        snapshot = inspect_bundle(root, max_bytes=plan.workload.resources.max_bytes)
        if record_to_dict(snapshot.plan) != record_to_dict(plan):
            raise ValueError("resume plan differs from frozen plan")
        if "manifest.json" in _files(root, plan.workload.resources.max_bytes):
            if snapshot.execution == "complete":
                raise ValueError("completed bundle is immutable")
            history_path = _path(root, "history.json")
            history: list[Any] = []
            if history_path.exists():
                history = _json(root, "history.json", _files(root, plan.workload.resources.max_bytes))
            history.append(
                {
                    "execution": snapshot.execution,
                    "qualification": snapshot.qualification,
                    "reason": snapshot.reason,
                }
            )
            _atomic(root, "history.json", canonical_json(history), plan.workload.resources.max_bytes)
            _path(root, "manifest.json").unlink()
        for name in ("metrics.json", "costs.json", "report.md"):
            path = _path(root, name)
            if path.exists():
                path.unlink()
        return cls(
            root, plan, snapshot.attempts, sum(_files(root, plan.workload.resources.max_bytes).values())
        )

    def _current(self) -> None:
        if _path(self.destination, "manifest.json").exists():
            raise ValueError("finished bundle is immutable")
        if _path(self.destination, "runs.jsonl").stat().st_size != self._journal_size:
            raise ValueError("attempt journal changed outside this writer")

    def append_attempt(self, record: AttemptRecord) -> None:
        if not isinstance(record, AttemptRecord):
            raise ValueError("record must be AttemptRecord")
        self._current()
        if len(self._attempts) >= self.plan.workload.resources.max_jobs:
            raise StorageLimitError("attempt count exceeds max_jobs")
        _validate_attempt(
            self.plan,
            self._attempts,
            record,
            attempt_ids=self._attempt_ids,
            last_by_run=self._last_by_run,
            run_map=self._run_map,
            operation_map=self._operation_map,
        )
        for observation in record.observations:
            if observation.array is not None:
                sizes = _files(self.destination, self.plan.workload.resources.max_bytes)
                _array_check(
                    self.destination,
                    sizes,
                    observation.array,
                    verify=True,
                    limit=self.plan.workload.resources.max_bytes,
                )
        row_record = record_to_dict(record)
        row = canonical_json({"record": row_record, "digest": identity_digest(row_record)}) + b"\n"
        reserve = min(4096, self.plan.workload.resources.max_bytes // 8)
        if self._used_bytes + len(row) + reserve > self.plan.workload.resources.max_bytes:
            raise StorageLimitError("attempt journal would exceed byte budget")
        with _path(self.destination, "runs.jsonl").open("ab") as stream:
            stream.write(row)
            stream.flush()
            os.fsync(stream.fileno())
        self._attempts.append(record)
        self._attempt_ids.add(record.attempt_id)
        self._last_by_run[record.run_id] = record
        self._used_bytes += len(row)
        self._journal_size += len(row)

    def add_array(self, relative_path: str, values: Any, *, axes: tuple[str, ...]) -> ArrayRef:
        self._current()
        if not relative_path.startswith("arrays/") or not relative_path.endswith(".npy"):
            raise ValueError("arrays must use an arrays/*.npy path")
        target = _path(self.destination, relative_path)
        if target.exists():
            raise ValueError("array payload already exists")
        try:
            import numpy as np
        except ImportError as error:
            raise ValueError("NumPy is required to write NPY arrays") from error
        if not isinstance(values, np.ndarray):
            raise ValueError("values must be a NumPy ndarray")
        dtype = values.dtype.name
        if dtype not in {"bool", "int8", "int16", "int32", "int64", "float32", "float64"}:
            raise ValueError("unsupported or lossful array dtype")
        if values.dtype.hasobject or values.dtype.fields is not None:
            raise ValueError("object or structured array is unsupported")
        if values.nbytes > self.plan.workload.resources.max_bytes:
            raise StorageLimitError("array allocation exceeds byte budget")
        if dtype.startswith("float") and not bool(np.isfinite(values).all()):
            raise ValueError("normal observation array must be finite")
        if not values.flags.c_contiguous:
            values = np.array(values, copy=True, order="C")
        stream = io.BytesIO()
        np.save(stream, values, allow_pickle=False)
        payload = stream.getvalue()
        ref = ArrayRef(relative_path, _hash(payload), len(payload), dtype, values.shape, axes)
        reserve = min(4096, self.plan.workload.resources.max_bytes // 8)
        sizes = _files(self.destination, self.plan.workload.resources.max_bytes)
        if sum(sizes.values()) + len(payload) + reserve > self.plan.workload.resources.max_bytes:
            raise StorageLimitError("array would exceed byte budget")
        _atomic(self.destination, relative_path, payload, self.plan.workload.resources.max_bytes)
        self._used_bytes += len(payload)
        return ref

    def finish(self, *, execution: str, report: QualificationReport | None = None) -> BundleSnapshot:
        from gibbsiq.qualification.reporting import render_report

        self._current()
        snapshot = inspect_bundle(self.destination, max_bytes=self.plan.workload.resources.max_bytes)
        if execution not in {"complete", "partial", "error", "cancelled"}:
            raise ValueError("unsupported execution state")
        completed = {item.run_id for item in snapshot.attempts if item.execution == "complete"}
        if execution == "complete" and completed != {run.run_id for run in self.plan.runs}:
            raise ValueError("complete execution requires every planned run")
        if report is not None:
            if not isinstance(report, QualificationReport):
                raise ValueError("report must be QualificationReport")
            _report_check(self.plan, snapshot.attempts, report, execution)
        elif _path(self.destination, "metrics.json").exists():
            _path(self.destination, "metrics.json").unlink()
        qualification = "inconclusive" if report is None else report.qualification
        if execution != "complete" and qualification == "pass":
            raise ValueError("incomplete execution cannot pass")
        limit = self.plan.workload.resources.max_bytes
        if execution == "complete":
            sizes = _files(self.destination, limit)
            referenced = {
                observation.array.path
                for attempt in snapshot.attempts
                for observation in attempt.observations
                if observation.array is not None
            }
            if {name for name in sizes if name.startswith("arrays/")} - referenced:
                raise ValueError("completed bundle contains unreferenced arrays")
        if report is not None:
            _atomic(self.destination, "metrics.json", canonical_json(record_to_dict(report)), limit)
        costs = [record_to_dict(cost) for attempt in snapshot.attempts for cost in attempt.costs]
        _atomic(self.destination, "costs.json", canonical_json(costs), limit)
        human = render_report(
            self.plan, execution=execution, qualification=qualification, report=report
        ).encode("utf-8")
        _atomic(self.destination, "report.md", human, limit)
        sizes = _files(self.destination, limit)
        manifest = {
            "schema_version": 1,
            "workload_digest": self.plan.workload.semantic_digest(),
            "plan_digest": identity_digest(record_to_dict(self.plan)),
            "execution": execution,
            "qualification": qualification,
            "reason": None if report is None else report.reason,
            "files": _inventory(self.destination, sizes),
        }
        _atomic(self.destination, "manifest.json", canonical_json(manifest), limit)
        return inspect_bundle(self.destination, max_bytes=limit)


__all__ = [
    "AttemptRecord",
    "BundleSnapshot",
    "BundleWriter",
    "StorageLimitError",
    "attempt_from_dict",
    "bound_metric_values",
    "cost_from_dict",
    "inspect_bundle",
    "observation_from_dict",
    "plan_from_dict",
    "record_to_dict",
    "workload_from_dict",
]
