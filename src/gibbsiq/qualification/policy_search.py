"""Bounded offline policy search with frozen held-out evaluation.

Search callbacks are trusted execution hooks, but their return values are ignored.
All decisions come from inspected qualification bundles written by the callback.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

from gibbsiq.qualification._validation import _json_object as _closed
from gibbsiq.qualification.artifacts import (
    BundleSnapshot,
    cost_from_dict,
    inspect_bundle,
    record_to_dict,
)
from gibbsiq.qualification.contracts import (
    ArtifactIdentity,
    CostRecord,
    Policy,
    ResourceBudget,
    RunPlan,
    SamplingSettings,
    _digest,
    canonical_json,
    identity_digest,
    parse_json,
)
from gibbsiq.qualification.costs import compare_costs
from gibbsiq.qualification.engine import UnsupportedCapabilityError
from gibbsiq.qualification._files import atomic_bytes
from gibbsiq.qualification.model_evaluation import SplitManifest


_PHASES = ("calibration", "development", "evaluation")
_METADATA_RESERVE = 2 * 1024 * 1024
_MIN_BUNDLE_BYTES = 65_536
_REPORT_FIELDS = {
    "schema",
    "lifecycle",
    "selected",
    "baseline",
    "attempts",
    "final",
    "policy",
    "frozen_policy",
    "explored",
    "unexplored",
    "selection_exposure",
    "limitations",
}


def _count(value: object, *, name: str) -> int:
    if type(value) is not int or not 1 <= value <= 4096:
        raise ValueError(f"{name} must be an exact integer from 1 through 4096")
    return value


def _text(value: object, *, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a nonblank string")
    return value


@dataclass(frozen=True, slots=True)
class SearchSpace:
    counts: tuple[int, ...] = (8, 16, 32, 64, 128)
    baseline: int = 128
    groups: tuple[str, ...] = ()
    max_candidates: int = 64

    def __post_init__(self) -> None:
        if type(self.counts) is not tuple or not 1 <= len(self.counts) <= 8:
            raise ValueError("counts must contain one through eight levels")
        counts = tuple(_count(value, name="count") for value in self.counts)
        if len(set(counts)) != len(counts):
            raise ValueError("counts must be distinct")
        baseline = _count(self.baseline, name="baseline")
        if type(self.groups) is not tuple or len(self.groups) > 2:
            raise ValueError("groups must be an exact tuple of at most two IDs")
        groups = tuple(_text(value, name="group ID") for value in self.groups)
        if len(set(groups)) != len(groups):
            raise ValueError("group IDs must be unique")
        if type(self.max_candidates) is not int or not 1 <= self.max_candidates <= 64:
            raise ValueError("max_candidates must be an integer from 1 through 64")
        object.__setattr__(self, "counts", counts)
        object.__setattr__(self, "baseline", baseline)
        object.__setattr__(self, "groups", groups)

    @property
    def levels(self) -> tuple[int, ...]:
        return tuple(sorted({*self.counts, self.baseline}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "counts": list(self.counts),
            "baseline": self.baseline,
            "groups": list(self.groups),
            "max_candidates": self.max_candidates,
        }

    @classmethod
    def from_dict(cls, value: object) -> SearchSpace:
        row = _closed(value, {"counts", "baseline", "groups", "max_candidates"}, name="search space")
        if type(row["counts"]) is not list or type(row["groups"]) is not list:
            raise ValueError("search-space counts and groups must be arrays")
        return cls(tuple(row["counts"]), row["baseline"], tuple(row["groups"]), row["max_candidates"])


@dataclass(frozen=True, slots=True)
class Candidate:
    default_samples: int
    group_samples: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        default = _count(self.default_samples, name="default_samples")
        if type(self.group_samples) is not tuple:
            raise ValueError("group_samples must be an exact tuple")
        groups: list[tuple[str, int]] = []
        for item in self.group_samples:
            if type(item) is not tuple or len(item) != 2:
                raise ValueError("group_samples entries must be (group_id, count) pairs")
            groups.append((_text(item[0], name="group ID"), _count(item[1], name="group sample count")))
        if len({name for name, _ in groups}) != len(groups):
            raise ValueError("group sample IDs must be unique")
        object.__setattr__(self, "default_samples", default)
        object.__setattr__(self, "group_samples", tuple(groups))

    @property
    def settings(self) -> dict[str, Any]:
        result: dict[str, Any] = {"samples": self.default_samples}
        if self.group_samples:
            result["grouped_samples"] = dict(self.group_samples)
        return result

    def effective(self, groups: Sequence[str]) -> tuple[int, ...]:
        overrides = dict(self.group_samples)
        return tuple(overrides.get(group, self.default_samples) for group in groups)

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_samples": self.default_samples,
            "group_samples": [[name, count] for name, count in self.group_samples],
        }

    @classmethod
    def from_dict(cls, value: object) -> Candidate:
        row = _closed(value, {"default_samples", "group_samples"}, name="candidate")
        if type(row["group_samples"]) is not list:
            raise ValueError("group_samples must be an array")
        pairs = []
        for item in row["group_samples"]:
            if type(item) is not list or len(item) != 2:
                raise ValueError("group_samples entries must be two-item arrays")
            pairs.append((item[0], item[1]))
        return cls(row["default_samples"], tuple(pairs))


def _canonical(space: SearchSpace, effective: Sequence[int]) -> Candidate:
    values = tuple(effective)
    if len(values) != len(space.groups):
        raise ValueError("effective group counts do not match the declared groups")
    if not values or len(set(values)) == 1:
        return Candidate(space.baseline if not values else values[0])
    return Candidate(
        space.baseline,
        tuple((group, count) for group, count in zip(space.groups, values) if count != space.baseline),
    )


def enumerate_candidates(space: SearchSpace) -> tuple[Candidate, ...]:
    """Return the complete stable grid, refusing rather than truncating it."""
    if not isinstance(space, SearchSpace):
        raise ValueError("space must be SearchSpace")
    levels = space.levels
    result = [Candidate(count) for count in levels]
    if space.groups:
        import itertools

        uniform_keys = {candidate.effective(space.groups) for candidate in result}
        for effective in itertools.product(levels, repeat=len(space.groups)):
            candidate = _canonical(space, effective)
            key = candidate.effective(space.groups)
            if key not in uniform_keys:
                result.append(candidate)
                uniform_keys.add(key)
    if len(result) > space.max_candidates:
        raise ValueError("complete candidate grid exceeds max_candidates")
    return tuple(result)


def _phase_mapping(value: Mapping[str, Any], *, name: str) -> MappingProxyType[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(_PHASES):
        raise ValueError(f"{name} must be keyed exactly by calibration, development and evaluation")
    return MappingProxyType({phase: value[phase] for phase in _PHASES})


@dataclass(frozen=True, slots=True)
class SearchPlan:
    space: SearchSpace
    splits: SplitManifest
    templates: Mapping[str, RunPlan]
    metric_id: str
    screening_margin: float
    objective: CostRecord
    profile: ArtifactIdentity
    operation_map_digest: str
    master_seed: int = 20260924
    alpha_total: float = 0.05
    max_jobs: int = 256
    max_seconds: float = 600
    max_bytes: int = 67_108_864

    def __post_init__(self) -> None:
        if not isinstance(self.space, SearchSpace) or not isinstance(self.splits, SplitManifest):
            raise ValueError("space and splits must be frozen search records")
        templates = _phase_mapping(self.templates, name="templates")
        if any(not isinstance(value, RunPlan) for value in templates.values()):
            raise ValueError("templates must contain RunPlan values")
        metric_id = _text(self.metric_id, name="metric_id")
        if type(self.screening_margin) not in (int, float) or not math.isfinite(self.screening_margin):
            raise ValueError("screening_margin must be finite")
        if not isinstance(self.objective, CostRecord) or (
            self.objective.provenance != "modeled" or self.objective.availability != "available"
        ):
            raise ValueError("search objective must be an available modeled CostRecord")
        if not isinstance(self.profile, ArtifactIdentity):
            raise ValueError("profile must be ArtifactIdentity")
        operation_map_digest = _digest(self.operation_map_digest, name="operation_map_digest")
        if type(self.master_seed) is not int or not 0 <= self.master_seed <= 2**32 - 3:
            raise ValueError("master_seed must allow three uint32 phase seeds")
        if type(self.alpha_total) not in (int, float) or not 0 < self.alpha_total < 1:
            raise ValueError("alpha_total must lie strictly between zero and one")
        if type(self.max_jobs) is not int or self.max_jobs < 1:
            raise ValueError("max_jobs must be positive")
        if (
            type(self.max_seconds) not in (int, float)
            or not math.isfinite(self.max_seconds)
            or self.max_seconds <= 1
        ):
            raise ValueError("max_seconds must be finite and greater than one second")
        if type(self.max_bytes) is not int or self.max_bytes <= _METADATA_RESERVE:
            raise ValueError("max_bytes must exceed the search metadata reserve")

        candidates = enumerate_candidates(self.space)
        bundle_count = len(candidates) + 4
        share = (self.max_bytes - _METADATA_RESERVE) // bundle_count
        if share < _MIN_BUNDLE_BYTES:
            raise ValueError("search byte budget cannot provide the minimum bundle share")
        worst_jobs = (
            len(candidates) * len(templates["calibration"].runs)
            + 2 * len(templates["development"].runs)
            + 2 * len(templates["evaluation"].runs)
        )
        if worst_jobs > self.max_jobs:
            raise ValueError("worst-case search runs exceed max_jobs")
        self._validate_templates(templates)
        object.__setattr__(self, "templates", templates)
        object.__setattr__(self, "metric_id", metric_id)
        object.__setattr__(self, "screening_margin", float(self.screening_margin))
        object.__setattr__(self, "alpha_total", float(self.alpha_total))
        object.__setattr__(self, "max_seconds", float(self.max_seconds))
        object.__setattr__(self, "operation_map_digest", operation_map_digest)

    @property
    def bundle_bytes(self) -> int:
        return (self.max_bytes - _METADATA_RESERVE) // (len(enumerate_candidates(self.space)) + 4)

    def _validate_templates(self, templates: Mapping[str, RunPlan]) -> None:
        shared: dict[str, Any] | None = None
        fixed_settings: dict[str, Any] | None = None
        for phase in _PHASES:
            template = templates[phase]
            split = getattr(self.splits, phase)
            workload = template.workload
            if not template.runs:
                raise ValueError("templates must contain planned runs")
            for run in template.runs:
                if "samples" not in run.settings or set(run.settings) - set(workload.controls):
                    raise ValueError("template settings must use declared controls and include samples")
                _count(run.settings["samples"], name="template samples")
                grouped = run.settings.get("grouped_samples", {})
                if not isinstance(grouped, Mapping) or set(grouped) - set(self.space.groups):
                    raise ValueError("template grouped_samples must use declared search groups")
                for name, count in grouped.items():
                    if type(name) is not str:
                        raise ValueError("template group IDs must be strings")
                    _count(count, name=f"template group {name}")
                current_fixed = {
                    key: value
                    for key, value in run.settings.items()
                    if key not in {"samples", "grouped_samples"}
                }
                if fixed_settings is None:
                    fixed_settings = current_fixed
                elif current_fixed != fixed_settings:
                    raise ValueError("nonsearched controls must be fixed across every run and phase")
            if any(run.case_id != workload.inputs.cases[0].case_id for run in template.runs):
                raise ValueError("template runs must target the complete-corpus input case")
            if (
                len(workload.inputs.cases) != 1
                or workload.inputs.cases[0].content_digest != split.semantic_digest()
            ):
                raise ValueError("template input case must identify its declared split")
            if "samples" not in workload.controls:
                raise UnsupportedCapabilityError("search templates must support samples")
            if self.space.groups and "grouped_samples" not in workload.controls:
                raise UnsupportedCapabilityError("group search requires grouped_samples capability")
            groups = workload.precision.get("operation_groups")
            if not isinstance(groups, Mapping):
                raise ValueError("precision must declare operation_groups")
            if self.space.groups and tuple(groups) != self.space.groups:
                raise ValueError("v1 grouped search must cover every frozen operation group in order")
            if any(
                not isinstance(names, (list, tuple))
                or not names
                or any(type(name) is not str or not name for name in names)
                or len(set(names)) != len(names)
                for names in groups.values()
            ):
                raise ValueError("operation groups must contain nonempty unique operation IDs")
            flattened = [name for names in groups.values() for name in names]
            if len(flattened) != len(set(flattened)):
                raise ValueError("operation IDs must be disjoint across groups")
            plain_precision = record_to_dict(workload)["precision"]
            if identity_digest(plain_precision.get("operation_map_recipe")) != self.operation_map_digest:
                raise ValueError("operation map digest contradicts the frozen recipe")
            if workload.precision.get("profile_id") != self.profile.identity:
                raise ValueError("profile identity contradicts the frozen workload profile")
            metric = next(
                (item for item in workload.contract.metrics if item.metric_id == self.metric_id), None
            )
            if (
                metric is None
                or not metric.mandatory
                or metric.acceptance.kind != "upper"
                or metric.acceptance.upper != self.screening_margin
            ):
                raise ValueError("metric must be the mandatory predeclared upper-bound screening metric")
            if workload.randomization.independent_runs != len(template.runs):
                raise ValueError("template run count must match randomization replication count")
            if len(workload.operations) != 1 or workload.operations[0].shape or workload.operations[0].axes:
                raise ValueError("v1 search requires one complete-corpus scalar operation")
            if self.objective.scope != workload.cost_scope:
                raise ValueError("objective scope must equal the frozen workload cost scope")
            phase_shared = record_to_dict(workload)
            # Only corpus-bound identity, split metadata, run count, phase seed,
            # resource allocation and alpha may differ between templates.
            phase_shared["inputs"]["identity"]["digest"] = "<phase-corpus>"
            phase_shared["inputs"]["cases"] = "<phase-cases>"
            phase_shared["inputs"]["sequence_length"] = "<phase-sequence>"
            phase_shared["inputs"]["masks_digest"] = "<phase-masks>"
            phase_shared["candidate"]["digest"] = "<phase-candidate>"
            phase_shared["reference"]["digest"] = "<phase-reference>"
            phase_shared["precision"]["corpus"] = "<phase-corpus>"
            phase_shared["contract"]["alpha_total"] = "<phase-alpha>"
            for metric_data in phase_shared["contract"]["metrics"]:
                metric_data["planned_units"] = "<phase-runs>"
            phase_shared["randomization"]["master_seed"] = "<phase-seed>"
            phase_shared["randomization"]["independent_runs"] = "<phase-runs>"
            phase_shared["resources"] = "<phase-resources>"
            if shared is None:
                shared = phase_shared
            elif phase_shared != shared:
                raise ValueError("search templates disagree on shared execution semantics")

    def to_dict(self) -> dict[str, Any]:
        return {
            "space": self.space.to_dict(),
            "splits": self.splits.to_dict(),
            "templates": {phase: record_to_dict(self.templates[phase]) for phase in _PHASES},
            "metric_id": self.metric_id,
            "screening_margin": self.screening_margin,
            "objective": record_to_dict(self.objective),
            "profile": _identity_to_dict(self.profile),
            "operation_map_digest": self.operation_map_digest,
            "master_seed": self.master_seed,
            "alpha_total": self.alpha_total,
            "max_jobs": self.max_jobs,
            "max_seconds": self.max_seconds,
            "max_bytes": self.max_bytes,
        }

    @classmethod
    def from_dict(cls, value: object) -> SearchPlan:
        from gibbsiq.qualification.artifacts import plan_from_dict

        fields = {
            "space",
            "splits",
            "templates",
            "metric_id",
            "screening_margin",
            "objective",
            "profile",
            "operation_map_digest",
            "master_seed",
            "alpha_total",
            "max_jobs",
            "max_seconds",
            "max_bytes",
        }
        row = _closed(value, fields, name="search plan")
        templates = _phase_mapping(row["templates"], name="templates")
        return cls(
            SearchSpace.from_dict(row["space"]),
            SplitManifest.from_dict(row["splits"]),
            {phase: plan_from_dict(templates[phase]) for phase in _PHASES},
            row["metric_id"],
            row["screening_margin"],
            cost_from_dict(row["objective"]),
            _identity_from_dict(row["profile"]),
            row["operation_map_digest"],
            row["master_seed"],
            row["alpha_total"],
            row["max_jobs"],
            row["max_seconds"],
            row["max_bytes"],
        )


def _identity_to_dict(value: ArtifactIdentity) -> dict[str, Any]:
    return {"identity": value.identity, "revision": value.revision, "digest": value.digest}


def _identity_from_dict(value: object) -> ArtifactIdentity:
    row = _closed(value, {"identity", "revision", "digest"}, name="artifact identity")
    return ArtifactIdentity(row["identity"], row["revision"], row["digest"])


def policy_to_dict(policy: Policy) -> dict[str, Any]:
    if not isinstance(policy, Policy):
        raise ValueError("policy must be Policy")
    return {
        "policy_id": policy.policy_id,
        "workload_digest": policy.workload_digest,
        "operation_map_digest": policy.operation_map_digest,
        "profile": _identity_to_dict(policy.profile),
        "backend": _identity_to_dict(policy.backend),
        "input_envelope": _identity_to_dict(policy.input_envelope),
        "default": _settings_to_dict(policy.default),
        "groups": {name: _settings_to_dict(value) for name, value in policy.groups.items()},
        "fallback": _settings_to_dict(policy.fallback),
        "calibration_digest": policy.calibration_digest,
        "frozen_evaluation_digest": policy.frozen_evaluation_digest,
        "objective": record_to_dict(policy.objective),
        "qualification": policy.qualification,
        "validation_bundle": policy.validation_bundle,
        "schema_version": policy.schema_version,
    }


def _settings_to_dict(value: SamplingSettings) -> dict[str, int]:
    return {"samples": value.samples, "warmup": value.warmup, "thinning": value.thinning}


def _settings_from_dict(value: object) -> SamplingSettings:
    row = _closed(value, {"samples", "warmup", "thinning"}, name="sampling settings")
    return SamplingSettings(row["samples"], row["warmup"], row["thinning"])


def policy_from_dict(value: object) -> Policy:
    fields = {
        "policy_id",
        "workload_digest",
        "operation_map_digest",
        "profile",
        "backend",
        "input_envelope",
        "default",
        "groups",
        "fallback",
        "calibration_digest",
        "frozen_evaluation_digest",
        "objective",
        "qualification",
        "validation_bundle",
        "schema_version",
    }
    row = _closed(value, fields, name="policy")
    if not isinstance(row["groups"], Mapping) or any(type(key) is not str for key in row["groups"]):
        raise ValueError("policy groups must be an object")
    return Policy(
        row["policy_id"],
        row["workload_digest"],
        row["operation_map_digest"],
        _identity_from_dict(row["profile"]),
        _identity_from_dict(row["backend"]),
        _identity_from_dict(row["input_envelope"]),
        _settings_from_dict(row["default"]),
        {name: _settings_from_dict(item) for name, item in row["groups"].items()},
        _settings_from_dict(row["fallback"]),
        row["calibration_digest"],
        row["frozen_evaluation_digest"],
        cost_from_dict(row["objective"]),
        row["qualification"],
        row["validation_bundle"],
        row["schema_version"],
    )


def resolve_policy(
    policy: Policy,
    *,
    workload_digest: str,
    operation_map_digest: str,
    profile: ArtifactIdentity,
    backend: ArtifactIdentity,
    input_envelope: ArtifactIdentity,
) -> Candidate:
    if not isinstance(policy, Policy) or policy.qualification != "pass":
        raise UnsupportedCapabilityError("policy is not backed by passing frozen evaluation")
    if (
        policy.workload_digest != workload_digest
        or policy.operation_map_digest != operation_map_digest
        or policy.profile != profile
        or policy.backend != backend
        or policy.input_envelope != input_envelope
    ):
        raise UnsupportedCapabilityError("policy is outside its exact compatibility envelope")
    groups = tuple((name, settings.samples) for name, settings in policy.groups.items())
    return Candidate(policy.default.samples, groups)


def _freeze_plan(
    search: SearchPlan,
    phase: str,
    candidate: Candidate,
    *,
    alpha: float,
    seconds: float,
) -> RunPlan:
    template = search.templates[phase]
    phase_seed = search.master_seed + _PHASES.index(phase)
    controls = set(template.workload.controls)
    if candidate.group_samples and "grouped_samples" not in controls:
        raise UnsupportedCapabilityError("candidate requires grouped_samples capability")
    runs = tuple(
        replace(
            run,
            settings={
                **{
                    key: value
                    for key, value in run.settings.items()
                    if key not in {"samples", "grouped_samples"}
                },
                **candidate.settings,
            },
        )
        for run in template.runs
    )
    resources = ResourceBudget(
        template.workload.resources.max_jobs,
        min(float(seconds), template.workload.resources.max_seconds),
        min(search.bundle_bytes, template.workload.resources.max_bytes),
    )
    workload = replace(
        template.workload,
        contract=replace(template.workload.contract, alpha_total=alpha),
        randomization=replace(template.workload.randomization, master_seed=phase_seed),
        resources=resources,
    )
    return RunPlan(workload, runs, template.schema_version, template.metric_bindings)


def _attempt_data(
    search: SearchPlan,
    candidate: Candidate,
    phase: str,
    bundle: Path,
    snapshot: BundleSnapshot,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "candidate": candidate.to_dict(),
        "phase": phase,
        "bundle": bundle.as_posix(),
        "manifest_digest": snapshot.manifest_digest,
        "execution": snapshot.execution,
        "qualification": snapshot.qualification,
        "screening_eligible": False,
        "quality_mean": None,
        "objective": None,
        "observation_count": 0,
        "randomization": [attempt.randomization for attempt in snapshot.attempts],
        "reason": snapshot.reason,
    }
    if snapshot.execution != "complete" or snapshot.report is None:
        result["reason"] = snapshot.reason or "complete qualification report unavailable"
        return result
    metric = next((item for item in snapshot.report.metrics if item.metric_id == search.metric_id), None)
    if (
        metric is None
        or metric.availability != "available"
        or metric.estimate is None
        or not math.isfinite(metric.estimate)
        or metric.observed_units != metric.planned_units
    ):
        result["reason"] = "complete finite fixed-horizon quality evidence unavailable"
        return result
    complete = {attempt.run_id: attempt for attempt in snapshot.attempts if attempt.execution == "complete"}
    selected_attempts = [complete.get(run.run_id) for run in snapshot.plan.runs]
    if any(attempt is None for attempt in selected_attempts):
        result["reason"] = "latest complete attempt unavailable for every planned run"
        return result
    costs: list[CostRecord] = []
    for attempt in selected_attempts:
        assert attempt is not None
        matches = [
            cost
            for cost in attempt.costs
            if all(
                getattr(cost, field) == getattr(search.objective, field)
                for field in ("quantity", "units", "scope", "provenance", "method", "omissions")
            )
        ]
        if len(matches) != 1 or matches[0].availability != "available" or matches[0].value is None:
            result["reason"] = "exactly one compatible available objective is required per run"
            return result
        costs.append(matches[0])
    values = {cost.value for cost in costs}
    if len(values) != 1:
        result["reason"] = "unsupported stochastic modeled objective across repeated runs"
        return result
    objective = replace(costs[0], value=values.pop())
    result.update(
        quality_mean=metric.estimate,
        objective=record_to_dict(objective),
        observation_count=metric.observed_units,
        screening_eligible=metric.estimate <= search.screening_margin,
        reason=None
        if metric.estimate <= search.screening_margin
        else "quality mean exceeds screening margin",
    )
    return result


def _compatible_value(search: SearchPlan, attempt: Mapping[str, Any]) -> float:
    objective = cost_from_dict(attempt["objective"])
    comparison = compare_costs(search.objective, objective)
    if comparison.availability != "available":
        raise ValueError("observed objective is incompatible with the declared objective")
    assert objective.value is not None
    return objective.value


def _rank(
    search: SearchPlan, candidates: Sequence[Candidate], by_key: Mapping[tuple[Any, ...], Mapping[str, Any]]
) -> Candidate:
    order = {
        key: index
        for index, key in enumerate(
            _candidate_key(search.space, item) for item in enumerate_candidates(search.space)
        )
    }
    return min(
        candidates,
        key=lambda item: (
            _compatible_value(search, by_key[_candidate_key(search.space, item)]),
            bool(item.group_samples),
            order.get(_candidate_key(search.space, item), len(order)),
        ),
    )


def _candidate_key(space: SearchSpace, candidate: Candidate) -> tuple[Any, ...]:
    return candidate.effective(space.groups) if space.groups else (candidate.default_samples,)


def _atomic_json(root: Path, path: Path, value: object, *, limit: int = _METADATA_RESERVE) -> None:
    payload = canonical_json(value)
    current = path.stat().st_size if path.exists() else 0
    retained = sum(item.stat().st_size for item in root.iterdir() if item.is_file())
    if retained - current + len(payload) > limit:
        raise ValueError("search metadata exceeds its reserved byte budget")
    atomic_bytes(path, payload)


def run_search(
    plan: SearchPlan,
    *,
    evaluator: Callable[[Candidate, str, RunPlan, Path], None],
    destination: str | Path,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Execute the fixed bounded search and return its inspectable summary."""
    if not isinstance(plan, SearchPlan) or not callable(evaluator) or not callable(clock):
        raise ValueError("run_search requires a SearchPlan and callable evaluator/clock")
    root = Path(destination)
    if root.exists():
        raise ValueError("search destination must not already exist")
    root.mkdir(parents=True)
    started = clock()
    deadline = started + plan.max_seconds
    candidates = enumerate_candidates(plan.space)
    attempts: list[dict[str, Any]] = []
    snapshots: dict[tuple[str, tuple[Any, ...]], BundleSnapshot] = {}
    evidence: dict[tuple[str, tuple[Any, ...]], dict[str, Any]] = {}
    _atomic_json(root, root / "search-plan.json", plan.to_dict())

    def evaluate(
        candidate: Candidate,
        phase: str,
        *,
        alpha: float,
        seconds: float | None = None,
        frozen_plan: RunPlan | None = None,
    ) -> dict[str, Any]:
        key = (phase, _candidate_key(plan.space, candidate))
        if key in evidence:
            return evidence[key]
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError("search wall-time budget exhausted")
        if frozen_plan is None:
            allocation = min(plan.templates[phase].workload.resources.max_seconds, remaining)
            if seconds is not None:
                allocation = min(allocation, seconds)
            if allocation <= 0:
                raise TimeoutError("search wall-time budget exhausted")
            frozen = _freeze_plan(plan, phase, candidate, alpha=alpha, seconds=allocation)
        else:
            frozen = frozen_plan
        bundle = root / "bundles" / phase / f"candidate-{len(attempts):04d}"
        bundle.parent.mkdir(parents=True, exist_ok=True)
        callback_error: Exception | None = None
        try:
            evaluator(candidate, phase, frozen, bundle)
        except Exception as error:
            callback_error = error
        if not bundle.exists():
            row: dict[str, Any] = {
                "candidate": candidate.to_dict(),
                "phase": phase,
                "bundle": bundle.relative_to(root).as_posix(),
                "manifest_digest": None,
                "execution": "error",
                "qualification": "invalid",
                "screening_eligible": False,
                "quality_mean": None,
                "objective": None,
                "observation_count": 0,
                "randomization": [],
                "reason": f"evaluator raised {type(callback_error).__name__}"
                if callback_error
                else "evaluator wrote no bundle",
            }
            attempts.append(row)
            evidence[key] = row
            _atomic_json(root, root / "attempts.json", attempts)
            if clock() > deadline:
                raise TimeoutError("search wall-time budget exhausted after evaluator callback")
            return row
        snapshot = inspect_bundle(
            bundle, verify=True, max_bytes=min(plan.bundle_bytes, frozen.workload.resources.max_bytes)
        )
        row = _attempt_data(plan, candidate, phase, bundle.relative_to(root), snapshot)
        if record_to_dict(snapshot.plan) != record_to_dict(frozen):
            row.update(
                qualification="invalid",
                screening_eligible=False,
                quality_mean=None,
                objective=None,
                reason="evaluator persisted a plan different from the frozen search plan",
            )
        attempts.append(row)
        if phase == "evaluation":
            snapshots[key] = snapshot
        evidence[key] = row
        if callback_error is not None and row["reason"] is None:
            row["reason"] = f"evaluator raised {type(callback_error).__name__} after writing evidence"
        _atomic_json(root, root / "attempts.json", attempts)
        if clock() > deadline:
            raise TimeoutError("search wall-time budget exhausted after retaining evaluator evidence")
        return row

    lifecycle = "no_feasible_policy"
    selected: Candidate | None = None
    selected_uniform: Candidate | None = None
    final: dict[str, Any] = {}
    policy: Policy | None = None
    frozen_policy: Policy | None = None
    final_family_size = 0
    overlap_detected = False
    try:
        uniform = tuple(candidate for candidate in candidates if not candidate.group_samples)
        calibration_rows: dict[tuple[Any, ...], dict[str, Any]] = {}
        eligible_uniform: list[Candidate] = []
        for candidate in uniform:
            row = evaluate(candidate, "calibration", alpha=plan.alpha_total)
            calibration_rows[_candidate_key(plan.space, candidate)] = row
            if row["screening_eligible"]:
                eligible_uniform.append(candidate)
        if not eligible_uniform:
            if any(row["qualification"] == "invalid" for row in calibration_rows.values()):
                lifecycle = "invalid"
            return _finish_summary(root, plan, lifecycle, None, attempts, final, None, None, candidates, 0)
        selected_uniform = _rank(plan, eligible_uniform, calibration_rows)
        selected = selected_uniform

        if plan.space.groups:
            levels = plan.space.levels
            while True:
                current = selected.effective(plan.space.groups)
                accepted = False
                for index, _group in enumerate(plan.space.groups):
                    position = levels.index(current[index])
                    if position == 0:
                        continue
                    neighbor_values = list(current)
                    neighbor_values[index] = levels[position - 1]
                    neighbor = _canonical(plan.space, neighbor_values)
                    row = evaluate(neighbor, "calibration", alpha=plan.alpha_total)
                    current_row = evidence[("calibration", _candidate_key(plan.space, selected))]
                    if row["screening_eligible"] and (
                        _compatible_value(plan, row) < _compatible_value(plan, current_row)
                    ):
                        selected = neighbor
                        accepted = True
                        break
                if not accepted:
                    break

        development_candidates = tuple(dict.fromkeys((selected, selected_uniform)))
        development_rows: dict[tuple[Any, ...], dict[str, Any]] = {}
        eligible_development: list[Candidate] = []
        for candidate in development_candidates:
            row = evaluate(candidate, "development", alpha=plan.alpha_total)
            development_rows[_candidate_key(plan.space, candidate)] = row
            if row["screening_eligible"]:
                eligible_development.append(candidate)
        if not eligible_development:
            if any(row["qualification"] == "invalid" for row in development_rows.values()):
                lifecycle = "invalid"
            return _finish_summary(root, plan, lifecycle, None, attempts, final, None, None, candidates, 0)
        selected = _rank(plan, eligible_development, development_rows)

        baseline = Candidate(plan.space.baseline)
        final_candidates = tuple(dict.fromkeys((selected, baseline)))
        final_family_size = len(final_candidates)
        family_alpha = plan.alpha_total / len(final_candidates)
        remaining = deadline - clock() - 1.0
        if remaining <= 0:
            raise TimeoutError("no wall-time remains for frozen final family")
        seconds_each = remaining / len(final_candidates)
        final_plans = {
            _candidate_key(plan.space, item): _freeze_plan(
                plan, "evaluation", item, alpha=family_alpha, seconds=seconds_each
            )
            for item in final_candidates
        }
        selected_development = development_rows[_candidate_key(plan.space, selected)]
        frozen_policy = _make_policy(
            plan,
            selected,
            final_plans[_candidate_key(plan.space, selected)],
            cost_from_dict(selected_development["objective"]),
            attempts,
            qualification="unqualified",
            validation_bundle=None,
        )
        _atomic_json(root, root / "frozen-policy.json", policy_to_dict(frozen_policy))
        _atomic_json(
            root,
            root / "frozen-evaluation-plans.json",
            [record_to_dict(final_plans[_candidate_key(plan.space, item)]) for item in final_candidates],
        )
        _atomic_json(root, root / "pre-final-search.json", {"plan": plan.to_dict(), "attempts": attempts})

        selected_row: dict[str, Any] | None = None
        for candidate in final_candidates:
            frozen = final_plans[_candidate_key(plan.space, candidate)]
            if frozen.workload.resources.max_seconds > deadline - clock():
                raise TimeoutError("frozen final allocation no longer fits remaining deadline")
            row = evaluate(
                candidate,
                "evaluation",
                alpha=family_alpha,
                seconds=frozen.workload.resources.max_seconds,
                frozen_plan=frozen,
            )
            earlier_streams = {
                digest
                for item in attempts
                if item["phase"] in {"calibration", "development"}
                for digest in item["randomization"]
            }
            if earlier_streams.intersection(row["randomization"]):
                row["screening_eligible"] = False
                row["reason"] = "final randomization identity overlaps an earlier search phase"
                overlap_detected = True
            snapshot = snapshots.get(("evaluation", _candidate_key(plan.space, candidate)))
            final["selected" if candidate == selected else "baseline"] = {
                "candidate": candidate.to_dict(),
                "execution": row["execution"],
                "qualification": row["qualification"],
                "manifest_digest": row["manifest_digest"],
                "objective": row["objective"],
                "reason": row["reason"],
                "report": None
                if snapshot is None or snapshot.report is None
                else record_to_dict(snapshot.report),
            }
            if candidate == selected:
                selected_row = row
        assert selected_row is not None
        if overlap_detected:
            lifecycle = "invalid"
        elif selected_row["execution"] in {"partial", "cancelled"}:
            lifecycle = "budget_exhausted"
        elif selected_row["execution"] == "error":
            lifecycle = "invalid"
        elif selected_row["qualification"] == "fail":
            lifecycle = "failed_validation"
        elif selected_row["qualification"] == "inconclusive":
            lifecycle = "inconclusive_validation"
        elif selected_row["qualification"] == "invalid":
            lifecycle = "invalid"
        elif selected_row["qualification"] == "unsupported" or selected_row["objective"] is None:
            lifecycle = "unsupported"
        elif selected_row["qualification"] == "pass":
            lifecycle = "qualified"
            selected_snapshot = snapshots[("evaluation", _candidate_key(plan.space, selected))]
            assert selected_snapshot.manifest_digest is not None
            policy = _make_policy(
                plan,
                selected,
                final_plans[_candidate_key(plan.space, selected)],
                cost_from_dict(selected_row["objective"]),
                attempts,
                qualification="pass",
                validation_bundle=selected_snapshot.manifest_digest,
            )
            _atomic_json(root, root / "policy.json", policy_to_dict(policy))
        else:
            lifecycle = "invalid"
    except TimeoutError:
        lifecycle = "budget_exhausted"
    return _finish_summary(
        root,
        plan,
        lifecycle,
        selected,
        attempts,
        final,
        policy,
        frozen_policy,
        candidates,
        final_family_size,
    )


def _make_policy(
    plan: SearchPlan,
    candidate: Candidate,
    final_plan: RunPlan,
    objective: CostRecord,
    attempts: Sequence[Mapping[str, Any]],
    *,
    qualification: str,
    validation_bundle: str | None,
) -> Policy:
    default_template = plan.templates["evaluation"].runs[0].settings
    warmup = default_template.get("warmup", 0)
    thinning = default_template.get("thinning", 1)
    default = SamplingSettings(candidate.default_samples, warmup, thinning)
    groups = {name: SamplingSettings(count, warmup, thinning) for name, count in candidate.group_samples}
    calibration_manifests = [item["manifest_digest"] for item in attempts if item["phase"] == "calibration"]
    calibration_digest = identity_digest(
        {"split": plan.splits.calibration.semantic_digest(), "manifests": calibration_manifests}
    )
    frozen_digest = identity_digest(record_to_dict(final_plan))
    payload = {
        "candidate": candidate.to_dict(),
        "workload": final_plan.workload.semantic_digest(),
        "calibration": calibration_digest,
        "frozen": frozen_digest,
    }
    return Policy(
        "bounded-search:" + identity_digest(payload)[7:23],
        final_plan.workload.semantic_digest(),
        plan.operation_map_digest,
        plan.profile,
        final_plan.workload.candidate,
        final_plan.workload.inputs.identity,
        default,
        groups,
        SamplingSettings(plan.space.baseline, warmup, thinning),
        calibration_digest,
        frozen_digest,
        objective,
        qualification,
        validation_bundle,
    )


def _finish_summary(
    root: Path,
    plan: SearchPlan,
    lifecycle: str,
    selected: Candidate | None,
    attempts: Sequence[Mapping[str, Any]],
    final: Mapping[str, Any],
    policy: Policy | None,
    frozen_policy: Policy | None,
    candidates: Sequence[Candidate],
    final_family_size: int,
) -> dict[str, Any]:
    explored: list[Mapping[str, Any]] = []
    for attempt in attempts:
        if attempt["candidate"] not in explored:
            explored.append(attempt["candidate"])
    explored_keys = {canonical_json(item).decode("utf-8") for item in explored}
    unexplored = [
        item.to_dict()
        for item in candidates
        if canonical_json(item.to_dict()).decode("utf-8") not in explored_keys
    ]
    summary = {
        "schema": "bounded-policy-search-v1",
        "lifecycle": lifecycle,
        "selected": None if selected is None else selected.to_dict(),
        "baseline": Candidate(plan.space.baseline).to_dict(),
        "attempts": list(attempts),
        "final": dict(final),
        "policy": None if policy is None else policy_to_dict(policy),
        "frozen_policy": None if frozen_policy is None else policy_to_dict(frozen_policy),
        "explored": list(explored),
        "unexplored": unexplored,
        "selection_exposure": {
            "calibration_evaluations": sum(item["phase"] == "calibration" for item in attempts),
            "development_evaluations": sum(item["phase"] == "development" for item in attempts),
            "final_family_size": final_family_size,
            "alpha_total": plan.alpha_total,
        },
        "limitations": [
            "Calibration and development means are exploratory screens, not confirmatory decisions.",
            "Final evaluation is fixed-horizon; no post-final replacement search is performed.",
            "The search is bounded and does not establish global optimality.",
            "Trusted evaluator callback wall time cannot be preempted by this Python API itself.",
        ],
    }
    _atomic_json(root, root / "search-report.json", summary)
    human = render_search_summary(summary).encode("utf-8")
    retained = sum(item.stat().st_size for item in root.iterdir() if item.is_file())
    if retained + len(human) > _METADATA_RESERVE:
        raise ValueError("search metadata exceeds its reserved byte budget")
    (root / "search-report.md").write_bytes(human)
    return summary


def inspect_search(path: str | Path) -> dict[str, Any]:
    from gibbsiq.qualification.artifacts import _report_from_dict

    root = Path(path)
    report = root / "search-report.json" if root.is_dir() else root
    if report.is_symlink() or not report.is_file():
        raise ValueError("search report is unavailable or exceeds its bound")
    try:
        with report.open("rb") as stream:
            payload = stream.read(_METADATA_RESERVE + 1)
        if len(payload) > _METADATA_RESERVE:
            raise ValueError("search report exceeds its bound")
        value = parse_json(payload.decode("utf-8"))
    except (OSError, UnicodeError) as error:
        raise ValueError("search report is unreadable") from error
    row = _closed(value, _REPORT_FIELDS, name="search report")
    if row["schema"] != "bounded-policy-search-v1":
        raise ValueError("unsupported search report schema")
    lifecycles = {
        "qualified",
        "no_feasible_policy",
        "budget_exhausted",
        "inconclusive_validation",
        "failed_validation",
        "invalid",
        "unsupported",
    }
    if row["lifecycle"] not in lifecycles:
        raise ValueError("unsupported search lifecycle")
    if row["selected"] is not None:
        Candidate.from_dict(row["selected"])
    Candidate.from_dict(row["baseline"])
    if (
        type(row["attempts"]) is not list
        or type(row["explored"]) is not list
        or type(row["unexplored"]) is not list
    ):
        raise ValueError("search candidate and attempt collections must be arrays")
    attempt_fields = {
        "candidate",
        "phase",
        "bundle",
        "manifest_digest",
        "execution",
        "qualification",
        "screening_eligible",
        "quality_mean",
        "objective",
        "observation_count",
        "randomization",
        "reason",
    }
    executions = {"complete", "partial", "error", "cancelled"}
    qualifications = {"pass", "fail", "inconclusive", "invalid", "unsupported"}
    for attempt in row["attempts"]:
        item = _closed(attempt, attempt_fields, name="search attempt")
        Candidate.from_dict(item["candidate"])
        if item["phase"] not in _PHASES or type(item["screening_eligible"]) is not bool:
            raise ValueError("invalid search attempt phase or eligibility")
        if item["execution"] not in executions or item["qualification"] not in qualifications:
            raise ValueError("invalid search attempt execution or qualification")
        bundle = item["bundle"]
        if (
            type(bundle) is not str
            or not bundle
            or "\\" in bundle
            or bundle.startswith("/")
            or ".." in bundle.split("/")
        ):
            raise ValueError("unsafe recorded bundle path")
        if item["manifest_digest"] is not None:
            _digest(item["manifest_digest"], name="attempt manifest_digest")
        if item["objective"] is not None:
            cost_from_dict(item["objective"])
        if type(item["randomization"]) is not list or type(item["observation_count"]) is not int:
            raise ValueError("invalid attempt randomization or observation count")
        if item["observation_count"] < 0 or any(type(value) is not str for value in item["randomization"]):
            raise ValueError("invalid attempt observation count or randomization identity")
        if item["quality_mean"] is not None and (
            type(item["quality_mean"]) not in (int, float) or not math.isfinite(item["quality_mean"])
        ):
            raise ValueError("attempt quality mean must be finite or null")
        if item["reason"] is not None and (type(item["reason"]) is not str or not item["reason"]):
            raise ValueError("attempt reason must be a nonblank string or null")
        if item["screening_eligible"] and (
            item["execution"] != "complete" or item["quality_mean"] is None or item["objective"] is None
        ):
            raise ValueError("screening eligibility lacks complete quality and cost evidence")
    for candidate in (*row["explored"], *row["unexplored"]):
        Candidate.from_dict(candidate)
    if not isinstance(row["final"], Mapping) or set(row["final"]) - {"selected", "baseline"}:
        raise ValueError("final evidence must contain only selected and baseline records")
    final_fields = {
        "candidate",
        "execution",
        "qualification",
        "manifest_digest",
        "objective",
        "reason",
        "report",
    }
    for value in row["final"].values():
        item = _closed(value, final_fields, name="final evidence")
        Candidate.from_dict(item["candidate"])
        if item["execution"] not in executions or item["qualification"] not in qualifications:
            raise ValueError("invalid final execution or qualification")
        if item["manifest_digest"] is not None:
            _digest(item["manifest_digest"], name="final manifest_digest")
        if item["objective"] is not None:
            cost_from_dict(item["objective"])
        if item["report"] is not None:
            report_record = _report_from_dict(item["report"])
            if (
                report_record.qualification != item["qualification"]
                or report_record.execution != item["execution"]
            ):
                raise ValueError("final report contradicts its retained scientific status")
        elif item["qualification"] in {"pass", "fail"}:
            raise ValueError("pass/fail final evidence requires its qualification report")
    if row["policy"] is not None:
        decoded_policy = policy_from_dict(row["policy"])
        if row["lifecycle"] != "qualified" or decoded_policy.qualification != "pass":
            raise ValueError("only a qualified lifecycle may export a passing policy")
        selected_evidence = row["final"].get("selected")
        if (
            selected_evidence is None
            or selected_evidence["qualification"] != "pass"
            or decoded_policy.validation_bundle != selected_evidence["manifest_digest"]
            or Candidate.from_dict(row["selected"]) != Candidate.from_dict(selected_evidence["candidate"])
        ):
            raise ValueError("exported policy is not linked to the selected passing final evidence")
    elif row["lifecycle"] == "qualified":
        raise ValueError("qualified lifecycle requires an exported policy")
    selected_final = row["final"].get("selected")
    expected_final_status = {
        "failed_validation": "fail",
        "inconclusive_validation": "inconclusive",
        "unsupported": "unsupported",
        "invalid": "invalid",
        "qualified": "pass",
    }.get(row["lifecycle"])
    if (
        expected_final_status is not None
        and (row["final"] or row["lifecycle"] == "qualified")
        and (selected_final is None or selected_final["qualification"] != expected_final_status)
    ):
        raise ValueError("lifecycle contradicts selected final qualification")
    if row["frozen_policy"] is not None:
        decoded_frozen = policy_from_dict(row["frozen_policy"])
        if decoded_frozen.qualification != "unqualified":
            raise ValueError("frozen pre-evaluation policy must remain unqualified")
    exposure = _closed(
        row["selection_exposure"],
        {"calibration_evaluations", "development_evaluations", "final_family_size", "alpha_total"},
        name="selection exposure",
    )
    for name in ("calibration_evaluations", "development_evaluations", "final_family_size"):
        if type(exposure[name]) is not int or exposure[name] < 0:
            raise ValueError("selection exposure counts must be nonnegative integers")
    if exposure["final_family_size"] not in {0, 1, 2}:
        raise ValueError("final family size must be zero, one or two")
    if type(exposure["alpha_total"]) not in (int, float) or not 0 < exposure["alpha_total"] < 1:
        raise ValueError("selection alpha_total must lie strictly between zero and one")
    if exposure["calibration_evaluations"] != sum(x["phase"] == "calibration" for x in row["attempts"]):
        raise ValueError("calibration exposure contradicts attempt history")
    if exposure["development_evaluations"] != sum(x["phase"] == "development" for x in row["attempts"]):
        raise ValueError("development exposure contradicts attempt history")
    if exposure["final_family_size"] < len(row["final"]):
        raise ValueError("completed final evidence exceeds the frozen family size")
    if type(row["limitations"]) is not list or any(type(item) is not str for item in row["limitations"]):
        raise ValueError("limitations must be a string array")
    canonical_json(row)
    return dict(row)


def render_search_summary(summary: Mapping[str, Any]) -> str:
    from gibbsiq.qualification.reporting import _cell

    row = _closed(summary, _REPORT_FIELDS, name="search summary")
    lines = [
        "# Bounded policy search",
        "",
        f"Lifecycle: {_cell(row['lifecycle'])}",
        f"Selected: {_cell(row['selected'])}",
        f"Attempts: {len(row['attempts'])}",
        "",
        "## Attempts",
        "",
    ]
    for attempt in row["attempts"]:
        lines.append(
            f"- {_cell(attempt['phase'])} {_cell(attempt['candidate'])}: {_cell(attempt['qualification'])}"
            + (f"; {_cell(attempt['reason'])}" if attempt["reason"] else "")
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {_cell(item)}" for item in row["limitations"])
    return "\n".join(lines) + "\n"


__all__ = [
    "Candidate",
    "SearchPlan",
    "SearchSpace",
    "enumerate_candidates",
    "inspect_search",
    "policy_from_dict",
    "policy_to_dict",
    "render_search_summary",
    "resolve_policy",
    "run_search",
]
