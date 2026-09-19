"""Immutable value contracts for qualification schema 1.

This module validates metadata only.  It does not execute workloads, inspect
artifacts, read arrays, or establish that an experiment took place.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from gibbsiq._frozen import freeze, thaw
from gibbsiq.qualification._validation import _finite, _integer, _probability


_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_MAX_JSON_DEPTH = 64
_SUPPORTED_DTYPES = frozenset({"bool", "int8", "int16", "int32", "int64", "float32", "float64"})
_INTEGER_RANGES = {
    "int8": (-(1 << 7), (1 << 7) - 1),
    "int16": (-(1 << 15), (1 << 15) - 1),
    "int32": (-(1 << 31), (1 << 31) - 1),
    "int64": (-(1 << 63), (1 << 63) - 1),
}


def _text(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")
    return value.strip()


def _choice(value: Any, choices: tuple[str, ...], *, name: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{name} must be one of {choices}")
    return value


def _optional_text(value: Any, *, name: str) -> str | None:
    if value is None:
        return None
    return _text(value, name=name)


def _schema_version(value: Any) -> int:
    if type(value) is not int or value != 1:
        raise ValueError("schema_version must be the integer 1")
    return value


def _positive_finite(value: Any, *, name: str) -> float:
    result = _finite(value, name=name)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _digest(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{name} must be sha256: followed by 64 lowercase hexadecimal characters")
    return value


def _sequence(value: Any, *, name: str) -> tuple[Any, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence")
    return tuple(value)


def _typed_sequence(value: Any, expected: type, *, name: str) -> tuple[Any, ...]:
    values = _sequence(value, name=name)
    if any(not isinstance(item, expected) for item in values):
        raise ValueError(f"{name} must contain only {expected.__name__} values")
    return values


def _name_sequence(value: Any, *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    values = _sequence(value, name=name)
    result = tuple(_text(item, name=f"{name} item") for item in values)
    if not allow_empty and not result:
        raise ValueError(f"{name} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must contain unique values")
    return result


def _normalize_json(
    value: Any,
    *,
    name: str,
    depth: int = 0,
    active: set[int] | None = None,
) -> Any:
    if depth > _MAX_JSON_DEPTH:
        raise ValueError(f"{name} exceeds the maximum JSON nesting depth")
    value_type = type(value)
    if value is None or value_type in {bool, int, str}:
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise ValueError(f"{name} contains a nonfinite number")
        return 0.0 if value == 0.0 else value
    is_mapping = isinstance(value, Mapping)
    if is_mapping or value_type in {list, tuple}:
        marker = id(value)
        active = set() if active is None else active
        if marker in active:
            raise ValueError(f"{name} contains a cycle")
        active.add(marker)
        try:
            if is_mapping:
                result: dict[str, Any] = {}
                for key, child in value.items():
                    if type(key) is not str:
                        raise ValueError(f"{name} mapping keys must be exact strings")
                    result[key] = _normalize_json(
                        child,
                        name=f"{name}.{key}",
                        depth=depth + 1,
                        active=active,
                    )
                return result
            return [
                _normalize_json(
                    child,
                    name=f"{name}[{index}]",
                    depth=depth + 1,
                    active=active,
                )
                for index, child in enumerate(value)
            ]
        finally:
            active.remove(marker)
    raise ValueError(f"{name} contains unsupported type {value_type.__name__}")


def _frozen_json_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    normalized = _normalize_json(value, name=name)
    return freeze(normalized)


def canonical_json(value: Any) -> bytes:
    """Return the schema-1 compact, finite UTF-8 JSON representation."""
    normalized = _normalize_json(value, name="value")
    try:
        return json.dumps(
            normalized,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except UnicodeError as error:
        raise ValueError("value contains text that cannot be encoded as UTF-8") from error


def parse_json(text: str) -> object:
    """Parse finite JSON while rejecting duplicate object keys at every depth."""
    if type(text) is not str:
        raise ValueError("text must be a string")

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def reject_constant(token: str) -> object:
        raise ValueError(f"nonfinite JSON number {token!r} is not supported")

    try:
        parsed = json.loads(text, object_pairs_hook=object_pairs, parse_constant=reject_constant)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as error:
        raise ValueError("invalid JSON text") from error
    return _normalize_json(parsed, name="parsed JSON")


def identity_digest(value: Any) -> str:
    """Return a schema-1 identity string for JSON metadata."""
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class Bounds:
    lower: float
    upper: float

    def __post_init__(self) -> None:
        lower = _finite(self.lower, name="lower")
        upper = _finite(self.upper, name="upper")
        if lower > upper:
            raise ValueError("lower cannot exceed upper")
        if not math.isfinite(upper - lower):
            raise ValueError("bounds must have finite width")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)


@dataclass(frozen=True, slots=True)
class Acceptance:
    kind: str
    upper: float | None
    lower: float | None = None

    def __post_init__(self) -> None:
        _choice(self.kind, ("upper", "lower", "equivalence"), name="kind")
        upper = None if self.upper is None else _finite(self.upper, name="upper")
        lower = None if self.lower is None else _finite(self.lower, name="lower")
        if self.kind == "upper" and (upper is None or lower is not None):
            raise ValueError("upper acceptance requires upper and forbids lower")
        if self.kind == "lower" and (lower is None or upper is not None):
            raise ValueError("lower acceptance requires lower and upper=None")
        if self.kind == "equivalence":
            if lower is None or upper is None or lower > upper:
                raise ValueError("equivalence acceptance requires ordered lower and upper")
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "lower", lower)

    def classify(self, interval: Bounds) -> str:
        """Classify one closed interval against this closed acceptance region."""
        if not isinstance(interval, Bounds):
            raise ValueError("interval must be Bounds")
        if self.kind == "upper":
            assert self.upper is not None
            if interval.upper <= self.upper:
                return "pass"
            if interval.lower > self.upper:
                return "fail"
            return "inconclusive"
        if self.kind == "lower":
            assert self.lower is not None
            if interval.lower >= self.lower:
                return "pass"
            if interval.upper < self.lower:
                return "fail"
            return "inconclusive"
        assert self.lower is not None and self.upper is not None
        if interval.lower >= self.lower and interval.upper <= self.upper:
            return "pass"
        if interval.upper < self.lower or interval.lower > self.upper:
            return "fail"
        return "inconclusive"


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_id: str
    units: str
    direction: str
    comparison: str
    acceptance: Acceptance
    evidence_mode: str
    planned_units: int
    replication_unit: str
    scope: str
    bounds: Bounds | None = None
    mandatory: bool = True
    aggregation: str = "mean"
    schema_version: int = 1

    def __post_init__(self) -> None:
        metric_id = _text(self.metric_id, name="metric_id")
        units = _text(self.units, name="units")
        comparison = _text(self.comparison, name="comparison")
        _choice(
            self.direction,
            ("smaller_is_better", "larger_is_better", "target"),
            name="direction",
        )
        if not isinstance(self.acceptance, Acceptance):
            raise ValueError("acceptance must be Acceptance")
        expected_kind = {
            "smaller_is_better": "upper",
            "larger_is_better": "lower",
            "target": "equivalence",
        }[self.direction]
        if self.acceptance.kind != expected_kind:
            raise ValueError("metric direction and acceptance kind contradict each other")
        _choice(self.evidence_mode, ("exact", "bounded_fixed_n"), name="evidence_mode")
        planned_units = _integer(self.planned_units, name="planned_units", minimum=1)
        if self.evidence_mode == "exact":
            if planned_units != 1 or self.replication_unit != "deterministic":
                raise ValueError("exact metrics require one deterministic unit")
        else:
            if not isinstance(self.bounds, Bounds):
                raise ValueError("bounded_fixed_n metrics require Bounds")
            _choice(
                self.replication_unit,
                ("independent_draw", "independent_run"),
                name="replication_unit",
            )
        if self.bounds is not None and not isinstance(self.bounds, Bounds):
            raise ValueError("bounds must be Bounds or None")
        _choice(self.scope, ("fixed_inputs",), name="scope")
        _choice(self.aggregation, ("mean",), name="aggregation")
        if type(self.mandatory) is not bool:
            raise ValueError("mandatory must be boolean")
        _schema_version(self.schema_version)
        object.__setattr__(self, "metric_id", metric_id)
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "comparison", comparison)
        object.__setattr__(self, "planned_units", planned_units)


@dataclass(frozen=True, slots=True)
class AcceptanceContract:
    metrics: tuple[MetricSpec, ...]
    alpha_total: float = 0.05
    schema_version: int = 1
    _alpha_by_id: Mapping[str, float | None] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        metrics = _typed_sequence(self.metrics, MetricSpec, name="metrics")
        if not metrics:
            raise ValueError("metrics must not be empty")
        identifiers = tuple(metric.metric_id for metric in metrics)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("metric IDs must be unique")
        if not any(metric.mandatory for metric in metrics):
            raise ValueError("at least one metric must be mandatory")
        alpha_total = _probability(self.alpha_total, name="alpha_total")
        bounded_count = sum(
            metric.mandatory and metric.evidence_mode == "bounded_fixed_n" for metric in metrics
        )
        if bounded_count and alpha_total / bounded_count == 0.0:
            raise ValueError("alpha_total underflows when allocated across bounded metrics")
        bounded_alpha = alpha_total / bounded_count if bounded_count else None
        alpha_by_id = {
            metric.metric_id: (
                bounded_alpha if metric.mandatory and metric.evidence_mode == "bounded_fixed_n" else None
            )
            for metric in metrics
        }
        _schema_version(self.schema_version)
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "alpha_total", alpha_total)
        object.__setattr__(self, "_alpha_by_id", MappingProxyType(alpha_by_id))

    def alpha_for(self, metric_id: str) -> float | None:
        metric_id = _text(metric_id, name="metric_id")
        try:
            return self._alpha_by_id[metric_id]
        except KeyError:
            raise ValueError(f"metric {metric_id!r} is not declared") from None


@dataclass(frozen=True, slots=True)
class MetricResult:
    metric_id: str
    availability: str
    estimate: float | None = None
    interval: Bounds | None = None
    outcome: str | None = None
    reason: str | None = None
    observed_units: int = 0
    planned_units: int = 1
    procedure: str = "exact-v1"
    alpha: float | None = None
    unit_summaries: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        metric_id = _text(self.metric_id, name="metric_id")
        _choice(
            self.availability,
            ("available", "unavailable", "not_applicable"),
            name="availability",
        )
        observed = _integer(self.observed_units, name="observed_units", minimum=0)
        planned = _integer(self.planned_units, name="planned_units", minimum=1)
        if observed > planned:
            raise ValueError("observed_units cannot exceed planned_units")
        procedure = _text(self.procedure, name="procedure")
        alpha = None if self.alpha is None else _probability(self.alpha, name="alpha")
        summaries = tuple(
            _finite(value, name=f"unit_summaries[{index}]")
            for index, value in enumerate(_sequence(self.unit_summaries, name="unit_summaries"))
        )
        if len(summaries) != observed:
            raise ValueError("unit_summaries length must equal observed_units")
        reason = _optional_text(self.reason, name="reason")
        if self.availability == "available":
            if observed == 0:
                raise ValueError("available metrics require at least one observed unit")
            estimate = _finite(self.estimate, name="estimate")
            if not isinstance(self.interval, Bounds):
                raise ValueError("available metrics require a Bounds interval")
            if not self.interval.lower <= estimate <= self.interval.upper:
                raise ValueError("interval must contain estimate")
            _choice(self.outcome, ("pass", "fail", "inconclusive"), name="outcome")
            if self.outcome == "pass" and observed != planned:
                raise ValueError("an incomplete metric cannot pass")
            object.__setattr__(self, "estimate", estimate)
        else:
            if reason is None:
                raise ValueError("unavailable and not_applicable metrics require a reason")
            if any(value is not None for value in (self.estimate, self.interval, self.outcome, self.alpha)):
                raise ValueError("unavailable metrics cannot contain numeric claims or outcomes")
            if observed != 0 or summaries:
                raise ValueError("unavailable metrics cannot contain observed summaries")
        object.__setattr__(self, "metric_id", metric_id)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "observed_units", observed)
        object.__setattr__(self, "planned_units", planned)
        object.__setattr__(self, "procedure", procedure)
        object.__setattr__(self, "alpha", alpha)
        object.__setattr__(self, "unit_summaries", summaries)


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    identity: str
    revision: str
    digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", _text(self.identity, name="identity"))
        object.__setattr__(self, "revision", _text(self.revision, name="revision"))
        object.__setattr__(self, "digest", _digest(self.digest, name="digest"))


@dataclass(frozen=True, slots=True)
class InputCase:
    case_id: str
    content_digest: str
    split: str
    group_id: str

    def __post_init__(self) -> None:
        _choice(
            self.split,
            ("calibration", "development", "evaluation", "fixture"),
            name="split",
        )
        object.__setattr__(self, "case_id", _text(self.case_id, name="case_id"))
        object.__setattr__(self, "content_digest", _digest(self.content_digest, name="content_digest"))
        object.__setattr__(self, "group_id", _text(self.group_id, name="group_id"))


@dataclass(frozen=True, slots=True)
class InputSpec:
    identity: ArtifactIdentity
    preprocessing: ArtifactIdentity
    cases: tuple[InputCase, ...]
    tokenizer: ArtifactIdentity | None = None
    sequence_length: int | None = None
    masks_digest: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ArtifactIdentity):
            raise ValueError("identity must be ArtifactIdentity")
        if not isinstance(self.preprocessing, ArtifactIdentity):
            raise ValueError("preprocessing must be ArtifactIdentity")
        if self.tokenizer is not None and not isinstance(self.tokenizer, ArtifactIdentity):
            raise ValueError("tokenizer must be ArtifactIdentity or None")
        cases = _typed_sequence(self.cases, InputCase, name="cases")
        if not cases:
            raise ValueError("cases must not be empty")
        identifiers = tuple(case.case_id for case in cases)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("case IDs must be unique")
        for attribute in ("content_digest", "group_id"):
            split_by_value: dict[str, str] = {}
            for case in cases:
                key = getattr(case, attribute)
                previous = split_by_value.setdefault(key, case.split)
                if previous != case.split:
                    raise ValueError(f"{attribute} cannot occur across multiple splits")
        length = (
            None
            if self.sequence_length is None
            else _integer(self.sequence_length, name="sequence_length", minimum=1)
        )
        masks_digest = None if self.masks_digest is None else _digest(self.masks_digest, name="masks_digest")
        object.__setattr__(self, "cases", cases)
        object.__setattr__(self, "sequence_length", length)
        object.__setattr__(self, "masks_digest", masks_digest)


def _shape_axes(shape: Any, axes: Any, *, prefix: str = "") -> tuple[tuple[int, ...], tuple[str, ...]]:
    shape_values = _sequence(shape, name=f"{prefix}shape")
    normalized_shape = tuple(
        _integer(value, name=f"{prefix}shape[{index}]", minimum=0) for index, value in enumerate(shape_values)
    )
    normalized_axes = _name_sequence(axes, name=f"{prefix}axes")
    if len(normalized_shape) != len(normalized_axes):
        raise ValueError("shape and axes must have matching ranks")
    if len(normalized_shape) > 16:
        raise ValueError("at most 16 axes are supported")
    return normalized_shape, normalized_axes


@dataclass(frozen=True, slots=True)
class OperationSpec:
    operation_id: str
    shape: tuple[int, ...]
    axes: tuple[str, ...]

    def __post_init__(self) -> None:
        shape, axes = _shape_axes(self.shape, self.axes)
        object.__setattr__(self, "operation_id", _text(self.operation_id, name="operation_id"))
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "axes", axes)


@dataclass(frozen=True, slots=True)
class RandomizationSpec:
    master_seed: int
    independent_runs: int
    replication_unit: str = "independent_run"

    def __post_init__(self) -> None:
        _choice(
            self.replication_unit,
            ("independent_run", "independent_draw"),
            name="replication_unit",
        )
        object.__setattr__(self, "master_seed", _integer(self.master_seed, name="master_seed", minimum=0))
        object.__setattr__(
            self,
            "independent_runs",
            _integer(self.independent_runs, name="independent_runs", minimum=1),
        )


@dataclass(frozen=True, slots=True)
class ResourceBudget:
    max_jobs: int
    max_seconds: float
    max_bytes: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_jobs", _integer(self.max_jobs, name="max_jobs", minimum=1))
        object.__setattr__(self, "max_seconds", _positive_finite(self.max_seconds, name="max_seconds"))
        object.__setattr__(self, "max_bytes", _integer(self.max_bytes, name="max_bytes", minimum=1))


@dataclass(frozen=True, slots=True)
class CostScope:
    boundary: str
    included_components: tuple[str, ...]
    excluded_components: tuple[str, ...] = ()
    batch_size: int = 1
    concurrency: int = 1
    sequence_length: int | None = None

    def __post_init__(self) -> None:
        included = _name_sequence(
            self.included_components,
            name="included_components",
            allow_empty=False,
        )
        excluded = _name_sequence(self.excluded_components, name="excluded_components")
        if set(included).intersection(excluded):
            raise ValueError("included and excluded components must be disjoint")
        sequence_length = (
            None
            if self.sequence_length is None
            else _integer(self.sequence_length, name="sequence_length", minimum=1)
        )
        object.__setattr__(self, "boundary", _text(self.boundary, name="boundary"))
        object.__setattr__(self, "included_components", included)
        object.__setattr__(self, "excluded_components", excluded)
        object.__setattr__(self, "batch_size", _integer(self.batch_size, name="batch_size", minimum=1))
        object.__setattr__(self, "concurrency", _integer(self.concurrency, name="concurrency", minimum=1))
        object.__setattr__(self, "sequence_length", sequence_length)


def _artifact_data(value: ArtifactIdentity) -> dict[str, Any]:
    return {"identity": value.identity, "revision": value.revision, "digest": value.digest}


def _bounds_data(value: Bounds | None) -> dict[str, float] | None:
    if value is None:
        return None
    return {"lower": value.lower, "upper": value.upper}


def _acceptance_data(value: Acceptance) -> dict[str, Any]:
    return {"kind": value.kind, "upper": value.upper, "lower": value.lower}


def _metric_data(value: MetricSpec) -> dict[str, Any]:
    return {
        "metric_id": value.metric_id,
        "units": value.units,
        "direction": value.direction,
        "comparison": value.comparison,
        "acceptance": _acceptance_data(value.acceptance),
        "evidence_mode": value.evidence_mode,
        "planned_units": value.planned_units,
        "replication_unit": value.replication_unit,
        "scope": value.scope,
        "bounds": _bounds_data(value.bounds),
        "mandatory": value.mandatory,
        "aggregation": value.aggregation,
        "schema_version": value.schema_version,
    }


@dataclass(frozen=True, slots=True)
class WorkloadSpec:
    workload_id: str
    description: str
    sources: tuple[ArtifactIdentity, ...]
    model_config: ArtifactIdentity
    inputs: InputSpec
    operations: tuple[OperationSpec, ...]
    dtype: str
    precision: Mapping[str, Any]
    reference: ArtifactIdentity
    candidate: ArtifactIdentity
    controls: tuple[str, ...]
    contract: AcceptanceContract
    randomization: RandomizationSpec
    resources: ResourceBudget
    cost_scope: CostScope
    license_refs: tuple[str, ...]
    retention: str = "summaries"
    checkpoint: ArtifactIdentity | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        workload_id = _text(self.workload_id, name="workload_id")
        if not isinstance(self.description, str):
            raise ValueError("description must be a string")
        sources = _typed_sequence(self.sources, ArtifactIdentity, name="sources")
        if not sources:
            raise ValueError("sources must not be empty")
        if len({source.identity for source in sources}) != len(sources):
            raise ValueError("source identities must be unique")
        if not isinstance(self.model_config, ArtifactIdentity):
            raise ValueError("model_config must be ArtifactIdentity")
        if not isinstance(self.inputs, InputSpec):
            raise ValueError("inputs must be InputSpec")
        operations = _typed_sequence(self.operations, OperationSpec, name="operations")
        if not operations:
            raise ValueError("operations must not be empty")
        if len({operation.operation_id for operation in operations}) != len(operations):
            raise ValueError("operation IDs must be unique")
        _choice(self.dtype, tuple(sorted(_SUPPORTED_DTYPES)), name="dtype")
        precision = _frozen_json_mapping(self.precision, name="precision")
        if not isinstance(self.reference, ArtifactIdentity):
            raise ValueError("reference must be ArtifactIdentity")
        if not isinstance(self.candidate, ArtifactIdentity):
            raise ValueError("candidate must be ArtifactIdentity")
        controls = _name_sequence(self.controls, name="controls")
        supported_controls = {"samples", "warmup", "thinning", "grouped_samples"}
        if not set(controls).issubset(supported_controls):
            raise ValueError("controls contain unsupported values")
        if not isinstance(self.contract, AcceptanceContract):
            raise ValueError("contract must be AcceptanceContract")
        if not isinstance(self.randomization, RandomizationSpec):
            raise ValueError("randomization must be RandomizationSpec")
        if not isinstance(self.resources, ResourceBudget):
            raise ValueError("resources must be ResourceBudget")
        if not isinstance(self.cost_scope, CostScope):
            raise ValueError("cost_scope must be CostScope")
        licenses = _name_sequence(self.license_refs, name="license_refs", allow_empty=False)
        _choice(self.retention, ("summaries", "selected", "all_local"), name="retention")
        if self.checkpoint is not None and not isinstance(self.checkpoint, ArtifactIdentity):
            raise ValueError("checkpoint must be ArtifactIdentity or None")
        _schema_version(self.schema_version)
        object.__setattr__(self, "workload_id", workload_id)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "operations", operations)
        object.__setattr__(self, "precision", precision)
        object.__setattr__(self, "controls", controls)
        object.__setattr__(self, "license_refs", licenses)

    def to_dict(self) -> dict[str, Any]:
        cases = [
            {
                "case_id": case.case_id,
                "content_digest": case.content_digest,
                "split": case.split,
                "group_id": case.group_id,
            }
            for case in self.inputs.cases
        ]
        payload = {
            "workload_id": self.workload_id,
            "description": self.description,
            "sources": [_artifact_data(source) for source in self.sources],
            "model_config": _artifact_data(self.model_config),
            "inputs": {
                "identity": _artifact_data(self.inputs.identity),
                "preprocessing": _artifact_data(self.inputs.preprocessing),
                "cases": cases,
                "tokenizer": (
                    None if self.inputs.tokenizer is None else _artifact_data(self.inputs.tokenizer)
                ),
                "sequence_length": self.inputs.sequence_length,
                "masks_digest": self.inputs.masks_digest,
            },
            "operations": [
                {
                    "operation_id": operation.operation_id,
                    "shape": list(operation.shape),
                    "axes": list(operation.axes),
                }
                for operation in self.operations
            ],
            "dtype": self.dtype,
            "precision": thaw(self.precision),
            "reference": _artifact_data(self.reference),
            "candidate": _artifact_data(self.candidate),
            "controls": list(self.controls),
            "contract": {
                "metrics": [_metric_data(metric) for metric in self.contract.metrics],
                "alpha_total": self.contract.alpha_total,
                "schema_version": self.contract.schema_version,
            },
            "randomization": {
                "master_seed": self.randomization.master_seed,
                "independent_runs": self.randomization.independent_runs,
                "replication_unit": self.randomization.replication_unit,
            },
            "resources": {
                "max_jobs": self.resources.max_jobs,
                "max_seconds": self.resources.max_seconds,
                "max_bytes": self.resources.max_bytes,
            },
            "cost_scope": {
                "boundary": self.cost_scope.boundary,
                "included_components": list(self.cost_scope.included_components),
                "excluded_components": list(self.cost_scope.excluded_components),
                "batch_size": self.cost_scope.batch_size,
                "concurrency": self.cost_scope.concurrency,
                "sequence_length": self.cost_scope.sequence_length,
            },
            "license_refs": list(self.license_refs),
            "retention": self.retention,
            "checkpoint": None if self.checkpoint is None else _artifact_data(self.checkpoint),
            "schema_version": self.schema_version,
        }
        return payload

    def semantic_digest(self) -> str:
        payload = self.to_dict()
        del payload["description"]
        return identity_digest(payload)


@dataclass(frozen=True, slots=True)
class ArrayRef:
    path: str
    digest: str
    byte_length: int
    dtype: str
    shape: tuple[int, ...]
    axes: tuple[str, ...]
    encoding: str = "npy-v1"

    def __post_init__(self) -> None:
        path = _text(self.path, name="path")
        if "\\" in path or ":" in path or path.startswith("/") or "//" in path:
            raise ValueError("path must be a safe relative POSIX path")
        raw_parts = path.split("/")
        if any(part in {"", ".", ".."} for part in raw_parts):
            raise ValueError("path must not contain empty, dot, or dotdot segments")
        _choice(self.dtype, tuple(sorted(_SUPPORTED_DTYPES)), name="dtype")
        shape, axes = _shape_axes(self.shape, self.axes)
        _choice(self.encoding, ("npy-v1",), name="encoding")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "digest", _digest(self.digest, name="digest"))
        object.__setattr__(
            self,
            "byte_length",
            _integer(self.byte_length, name="byte_length", minimum=1),
        )
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "axes", axes)


def _normalize_observation_value(value: Any, *, dtype: str, name: str) -> bool | int | float:
    if dtype == "bool":
        if type(value) is not bool:
            raise ValueError(f"{name} must be boolean")
        return value
    if dtype in _INTEGER_RANGES:
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer")
        lower, upper = _INTEGER_RANGES[dtype]
        if not lower <= value <= upper:
            raise ValueError(f"{name} is outside the {dtype} range")
        return value
    number = _finite(value, name=name)
    if dtype == "float32":
        try:
            number = struct.unpack(">f", struct.pack(">f", number))[0]
        except (OverflowError, struct.error) as error:
            raise ValueError(f"{name} is not representable as float32") from error
        if not math.isfinite(number):
            raise ValueError(f"{name} is not representable as float32")
        return 0.0 if number == 0.0 else number
    return number


@dataclass(frozen=True, slots=True)
class Observation:
    name: str
    operation_id: str
    context_id: str
    run_id: str
    dtype: str
    shape: tuple[int, ...]
    axes: tuple[str, ...]
    values: tuple[bool | int | float, ...] | None = None
    array: ArrayRef | None = None
    units: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        name = _text(self.name, name="name")
        operation_id = _text(self.operation_id, name="operation_id")
        context_id = _text(self.context_id, name="context_id")
        run_id = _text(self.run_id, name="run_id")
        _choice(self.dtype, tuple(sorted(_SUPPORTED_DTYPES)), name="dtype")
        shape, axes = _shape_axes(self.shape, self.axes)
        if (self.values is None) == (self.array is None):
            raise ValueError("exactly one of values or array is required")
        values: tuple[bool | int | float, ...] | None = None
        if self.values is not None:
            raw = _sequence(self.values, name="values")
            size = math.prod(shape)
            if size > 4096:
                raise ValueError("inline observations are capped at 4096 elements")
            if len(raw) != size:
                raise ValueError("inline value count must equal shape product")
            values = tuple(
                _normalize_observation_value(value, dtype=self.dtype, name=f"values[{index}]")
                for index, value in enumerate(raw)
            )
        else:
            if not isinstance(self.array, ArrayRef):
                raise ValueError("array must be ArrayRef")
            if (self.array.dtype, self.array.shape, self.array.axes) != (self.dtype, shape, axes):
                raise ValueError("array metadata must exactly match observation metadata")
        units = _optional_text(self.units, name="units")
        _schema_version(self.schema_version)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "operation_id", operation_id)
        object.__setattr__(self, "context_id", context_id)
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "axes", axes)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "units", units)


@dataclass(frozen=True, slots=True)
class CostRecord:
    quantity: str
    units: str
    scope: CostScope
    provenance: str
    availability: str
    value: float | None = None
    reason: str | None = None
    method: str = "unspecified"
    omissions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        expected_units = {"latency": "seconds", "energy": "joules", "sample_work": "samples"}
        _choice(self.quantity, tuple(expected_units), name="quantity")
        if self.units != expected_units[self.quantity]:
            raise ValueError("cost units do not match quantity")
        if not isinstance(self.scope, CostScope):
            raise ValueError("scope must be CostScope")
        _choice(
            self.provenance,
            ("measured", "modeled", "assumed", "inferred"),
            name="provenance",
        )
        _choice(
            self.availability,
            ("available", "unavailable", "not_applicable"),
            name="availability",
        )
        reason = _optional_text(self.reason, name="reason")
        value = self.value
        if self.availability == "available":
            value = _finite(value, name="value")
            if value < 0.0:
                raise ValueError("available cost must be nonnegative")
        else:
            if reason is None or value is not None:
                raise ValueError("unavailable cost requires reason and value=None")
        method = _text(self.method, name="method")
        omissions = _name_sequence(self.omissions, name="omissions")
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "omissions", omissions)


@dataclass(frozen=True, slots=True)
class PlannedRun:
    run_id: str
    case_id: str
    operation_id: str
    purpose: str
    settings: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _text(self.run_id, name="run_id"))
        object.__setattr__(self, "case_id", _text(self.case_id, name="case_id"))
        object.__setattr__(self, "operation_id", _text(self.operation_id, name="operation_id"))
        object.__setattr__(self, "purpose", _text(self.purpose, name="purpose"))
        object.__setattr__(self, "settings", _frozen_json_mapping(self.settings, name="settings"))


@dataclass(frozen=True, slots=True)
class RunPlan:
    workload: WorkloadSpec
    runs: tuple[PlannedRun, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.workload, WorkloadSpec):
            raise ValueError("workload must be WorkloadSpec")
        runs = _typed_sequence(self.runs, PlannedRun, name="runs")
        if not runs:
            raise ValueError("runs must not be empty")
        identifiers = tuple(run.run_id for run in runs)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("run IDs must be unique")
        if len(runs) > self.workload.resources.max_jobs:
            raise ValueError("run count exceeds max_jobs")
        case_ids = {case.case_id for case in self.workload.inputs.cases}
        operation_ids = {operation.operation_id for operation in self.workload.operations}
        for run in runs:
            if run.case_id not in case_ids:
                raise ValueError(f"run references unknown case {run.case_id!r}")
            if run.operation_id not in operation_ids:
                raise ValueError(f"run references unknown operation {run.operation_id!r}")
        _schema_version(self.schema_version)
        object.__setattr__(self, "runs", runs)


def _validate_result_against_spec(
    result: MetricResult,
    spec: MetricSpec,
    contract: AcceptanceContract,
) -> None:
    if result.planned_units != spec.planned_units:
        raise ValueError(f"metric {spec.metric_id!r} planned_units contradict the contract")
    if not spec.mandatory and result.availability == "available" and result.outcome != "inconclusive":
        raise ValueError("optional metrics are descriptive and must remain inconclusive")
    if result.availability == "available" and spec.bounds is not None:
        assert result.interval is not None
        if result.interval.lower < spec.bounds.lower or result.interval.upper > spec.bounds.upper:
            raise ValueError("metric result interval exceeds declared bounds")
        if any(not spec.bounds.lower <= value <= spec.bounds.upper for value in result.unit_summaries):
            raise ValueError("metric result unit summary exceeds declared bounds")
    if spec.evidence_mode == "exact":
        if result.procedure != "exact-v1" or result.alpha is not None:
            raise ValueError("exact result procedure or alpha contradicts the metric mode")
        if result.availability == "available":
            assert result.interval is not None and result.estimate is not None
            if result.interval.lower != result.estimate or result.interval.upper != result.estimate:
                raise ValueError("exact result must use a point interval")
    else:
        if result.procedure != "bounded-hoeffding-v1":
            raise ValueError("bounded result must use bounded-hoeffding-v1")
        expected_alpha = contract.alpha_for(spec.metric_id) if spec.mandatory else contract.alpha_total
        if result.availability == "available" and result.alpha != expected_alpha:
            raise ValueError("bounded result alpha contradicts the acceptance contract")
    if result.availability != "available" or not spec.mandatory:
        return
    assert result.interval is not None
    expected_outcome = (
        "inconclusive"
        if result.observed_units < result.planned_units
        else spec.acceptance.classify(result.interval)
    )
    if result.outcome != expected_outcome:
        raise ValueError("metric outcome contradicts its interval and acceptance boundary")


@dataclass(frozen=True, slots=True)
class QualificationReport:
    workload_digest: str
    contract: AcceptanceContract
    execution: str
    qualification: str
    metrics: tuple[MetricResult, ...]
    expected_run_ids: tuple[str, ...]
    completed_run_ids: tuple[str, ...]
    reason: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        workload_digest = _digest(self.workload_digest, name="workload_digest")
        if not isinstance(self.contract, AcceptanceContract):
            raise ValueError("contract must be AcceptanceContract")
        _choice(
            self.execution,
            ("complete", "partial", "error", "cancelled"),
            name="execution",
        )
        _choice(
            self.qualification,
            ("pass", "fail", "inconclusive", "invalid", "unsupported"),
            name="qualification",
        )
        metrics = _typed_sequence(self.metrics, MetricResult, name="metrics")
        result_ids = tuple(result.metric_id for result in metrics)
        contract_ids = tuple(metric.metric_id for metric in self.contract.metrics)
        if result_ids != contract_ids:
            raise ValueError("result metric IDs and order must match the contract")
        expected = _name_sequence(self.expected_run_ids, name="expected_run_ids", allow_empty=False)
        completed = _name_sequence(self.completed_run_ids, name="completed_run_ids")
        if not set(completed).issubset(expected):
            raise ValueError("completed_run_ids must be a subset of expected_run_ids")
        if self.execution == "complete" and set(completed) != set(expected):
            raise ValueError("complete execution requires every expected run")
        reason = _optional_text(self.reason, name="reason")
        if self.qualification in {"invalid", "unsupported"} and reason is None:
            raise ValueError("invalid and unsupported qualifications require a reason")
        for result, spec in zip(metrics, self.contract.metrics):
            _validate_result_against_spec(result, spec, self.contract)
        mandatory_pairs = [
            (result, spec) for result, spec in zip(metrics, self.contract.metrics) if spec.mandatory
        ]
        if self.qualification == "pass":
            if self.execution != "complete":
                raise ValueError("passing qualification requires complete execution")
            for result, spec in mandatory_pairs:
                if (
                    result.availability != "available"
                    or result.outcome != "pass"
                    or result.observed_units != spec.planned_units
                ):
                    raise ValueError("passing qualification requires complete passing mandatory metrics")
        if self.qualification in {"pass", "inconclusive"} and any(
            result.availability == "available" and result.outcome == "fail" for result, _ in mandatory_pairs
        ):
            raise ValueError("mandatory metric failure cannot be pass or inconclusive")
        _schema_version(self.schema_version)
        object.__setattr__(self, "workload_digest", workload_digest)
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "expected_run_ids", expected)
        object.__setattr__(self, "completed_run_ids", completed)
        object.__setattr__(self, "reason", reason)


@dataclass(frozen=True, slots=True)
class SamplingSettings:
    samples: int
    warmup: int = 0
    thinning: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "samples", _integer(self.samples, name="samples", minimum=1))
        object.__setattr__(self, "warmup", _integer(self.warmup, name="warmup", minimum=0))
        object.__setattr__(self, "thinning", _integer(self.thinning, name="thinning", minimum=1))


@dataclass(frozen=True, slots=True)
class Policy:
    policy_id: str
    workload_digest: str
    operation_map_digest: str
    profile: ArtifactIdentity
    backend: ArtifactIdentity
    input_envelope: ArtifactIdentity
    default: SamplingSettings
    groups: Mapping[str, SamplingSettings]
    fallback: SamplingSettings
    calibration_digest: str
    frozen_evaluation_digest: str
    objective: CostRecord
    qualification: str = "unqualified"
    validation_bundle: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        policy_id = _text(self.policy_id, name="policy_id")
        workload_digest = _digest(self.workload_digest, name="workload_digest")
        operation_map_digest = _digest(self.operation_map_digest, name="operation_map_digest")
        calibration_digest = _digest(self.calibration_digest, name="calibration_digest")
        frozen_digest = _digest(self.frozen_evaluation_digest, name="frozen_evaluation_digest")
        for name, identity_value in (
            ("profile", self.profile),
            ("backend", self.backend),
            ("input_envelope", self.input_envelope),
        ):
            if not isinstance(identity_value, ArtifactIdentity):
                raise ValueError(f"{name} must be ArtifactIdentity")
        if not isinstance(self.default, SamplingSettings):
            raise ValueError("default must be SamplingSettings")
        if not isinstance(self.fallback, SamplingSettings):
            raise ValueError("fallback must be SamplingSettings")
        if not isinstance(self.groups, Mapping):
            raise ValueError("groups must be a mapping")
        groups: dict[str, SamplingSettings] = {}
        for key, settings in self.groups.items():
            group_id = _text(key, name="group ID")
            if group_id in groups:
                raise ValueError("group IDs must be unique")
            if not isinstance(settings, SamplingSettings):
                raise ValueError("groups must map IDs to SamplingSettings")
            groups[group_id] = settings
        if not isinstance(self.objective, CostRecord):
            raise ValueError("objective must be CostRecord")
        _choice(
            self.qualification,
            (
                "unqualified",
                "pass",
                "fail",
                "inconclusive",
                "invalid",
                "unsupported",
            ),
            name="qualification",
        )
        validation_bundle = (
            None
            if self.validation_bundle is None
            else _digest(self.validation_bundle, name="validation_bundle")
        )
        if self.qualification == "unqualified" and validation_bundle is not None:
            raise ValueError("unqualified policy cannot name a validation bundle")
        if self.qualification != "unqualified" and validation_bundle is None:
            raise ValueError("qualified policy states require a validation bundle")
        _schema_version(self.schema_version)
        object.__setattr__(self, "policy_id", policy_id)
        object.__setattr__(self, "workload_digest", workload_digest)
        object.__setattr__(self, "operation_map_digest", operation_map_digest)
        object.__setattr__(self, "calibration_digest", calibration_digest)
        object.__setattr__(self, "frozen_evaluation_digest", frozen_digest)
        object.__setattr__(self, "groups", MappingProxyType(groups))
        object.__setattr__(self, "validation_bundle", validation_bundle)


__all__ = [
    "Acceptance",
    "AcceptanceContract",
    "ArrayRef",
    "ArtifactIdentity",
    "Bounds",
    "CostRecord",
    "CostScope",
    "InputCase",
    "InputSpec",
    "MetricResult",
    "MetricSpec",
    "Observation",
    "OperationSpec",
    "PlannedRun",
    "Policy",
    "QualificationReport",
    "RandomizationSpec",
    "ResourceBudget",
    "RunPlan",
    "SamplingSettings",
    "WorkloadSpec",
    "canonical_json",
    "identity_digest",
    "parse_json",
]
