"""Compatible cost comparisons and explicitly modeled work/latency accounting."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from gibbsiq.qualification._validation import _integer
from gibbsiq.qualification.contracts import CostRecord, CostScope


@dataclass(frozen=True, slots=True)
class CostComparison:
    availability: str
    delta: float | None
    ratio: float | None
    reason: str | None = None


def compare_costs(reference: CostRecord, candidate: CostRecord) -> CostComparison:
    """Compare candidate minus reference only across the same declared cost claim."""
    if not isinstance(reference, CostRecord) or not isinstance(candidate, CostRecord):
        raise ValueError("reference and candidate must be CostRecord")
    for name in ("quantity", "units", "scope", "provenance", "method", "omissions"):
        if getattr(reference, name) != getattr(candidate, name):
            raise ValueError(f"incompatible cost {name}")
    if reference.availability != "available" or candidate.availability != "available":
        reasons = (
            f"{name}: {record.availability} ({record.reason})"
            for name, record in (("reference", reference), ("candidate", candidate))
            if record.availability != "available"
        )
        return CostComparison("unavailable", None, None, "; ".join(reasons))
    assert reference.value is not None and candidate.value is not None
    delta = candidate.value - reference.value
    if not math.isfinite(delta):
        raise ValueError("cost delta is not finite")
    if reference.value == 0:
        return CostComparison("available", delta, None, "ratio unavailable: zero reference")
    ratio = candidate.value / reference.value
    if not math.isfinite(ratio):
        raise ValueError("cost ratio is not finite")
    return CostComparison("available", delta, ratio)


def sample_work(elements: Mapping[str, int], samples: Mapping[str, int], *, scope: CostScope) -> CostRecord:
    """Count IID output-spin draws, without converting them to time or energy."""
    if (
        not isinstance(elements, Mapping)
        or not isinstance(samples, Mapping)
        or not isinstance(scope, CostScope)
    ):
        raise ValueError("elements and samples must be mappings and scope must be CostScope")
    if not elements or set(elements) != set(samples):
        raise ValueError("elements and samples need identical nonempty operation IDs")
    if any(type(key) is not str or not key.strip() for key in elements):
        raise ValueError("operation IDs must be nonblank strings")
    if set(scope.included_components) != set(elements):
        raise ValueError("scope included components must exactly match sampled operations")
    total = 0
    for operation_id in elements:
        element_count = _integer(
            elements[operation_id], name=f"{operation_id}: output-element count", minimum=1
        )
        sample_count = _integer(samples[operation_id], name=f"{operation_id}: sample count", minimum=1)
        total += element_count * sample_count
    if total > 2**53:
        raise ValueError("sample work exceeds exact integer range of CostRecord.value")
    return CostRecord(
        quantity="sample_work",
        units="samples",
        scope=scope,
        provenance="modeled",
        availability="available",
        value=total,
        method="iid-spin-draws-v1",
        omissions=("other_model_computation", "allocation", "communication", "physical_energy"),
    )


@dataclass(frozen=True, slots=True)
class LatencyRegion:
    region_id: str
    seconds: float
    components: tuple[str, ...]
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.region_id) is not str or not self.region_id.strip():
            raise ValueError("region_id must be a nonblank string")
        if (
            isinstance(self.seconds, bool)
            or not isinstance(self.seconds, (int, float))
            or not math.isfinite(self.seconds)
            or self.seconds < 0
        ):
            raise ValueError("seconds must be finite and nonnegative")
        for name, values, allow_empty in (
            ("components", self.components, False),
            ("depends_on", self.depends_on, True),
        ):
            if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
                raise ValueError(f"{name} must be a sequence")
            if not allow_empty and not values:
                raise ValueError(f"{name} must not be empty")
            if any(type(value) is not str or not value.strip() for value in values) or len(
                set(values)
            ) != len(values):
                raise ValueError(f"{name} must contain unique nonblank strings")
        object.__setattr__(self, "region_id", self.region_id.strip())
        object.__setattr__(self, "seconds", float(self.seconds))
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(self, "depends_on", tuple(self.depends_on))


def _region_duration(
    region_id: str,
    by_id: Mapping[str, LatencyRegion],
    visiting: set[str],
    finished: dict[str, float],
) -> float:
    if region_id not in by_id:
        raise ValueError(f"unknown region dependency {region_id!r}")
    if region_id in visiting:
        raise ValueError("region dependencies contain a cycle")
    if region_id not in finished:
        visiting.add(region_id)
        region = by_id[region_id]
        value = region.seconds + max(
            (_region_duration(dep, by_id, visiting, finished) for dep in region.depends_on), default=0.0
        )
        visiting.remove(region_id)
        if not math.isfinite(value):
            raise ValueError("critical path is not finite")
        finished[region_id] = value
    return finished[region_id]


def critical_path_seconds(regions: Sequence[LatencyRegion]) -> float:
    """Longest declared dependency path across disjoint component regions."""
    if not isinstance(regions, Sequence) or isinstance(regions, (str, bytes)):
        raise ValueError("regions must be a sequence")
    by_id: dict[str, LatencyRegion] = {}
    components: set[str] = set()
    for region in regions:
        if not isinstance(region, LatencyRegion):
            raise ValueError("regions must contain LatencyRegion values")
        if region.region_id in by_id:
            raise ValueError("duplicate region ID")
        if components.intersection(region.components):
            raise ValueError("overlapping components cannot be summed")
        by_id[region.region_id] = region
        components.update(region.components)
    visiting: set[str] = set()
    finished: dict[str, float] = {}

    return max((_region_duration(region_id, by_id, visiting, finished) for region_id in by_id), default=0.0)


__all__ = ["CostComparison", "LatencyRegion", "compare_costs", "critical_path_seconds", "sample_work"]
