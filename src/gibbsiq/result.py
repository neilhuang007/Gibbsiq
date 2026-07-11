"""Initial solver result schema.

Stage 1 does not implement a sampler, but downstream layers need a stable shape
for samples, energies, traces, diagnostics, metadata, and optional dimod export.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from gibbsiq._frozen import freeze, thaw
from gibbsiq.model import IsingModel, Variable, Vartype, finite_float, normalize_vartype

ResultVartype: TypeAlias = Literal["SPIN", "BINARY", "CATEGORICAL"]


def normalize_result_vartype(vartype: Any) -> ResultVartype:
    """Normalize result-level vartypes; dimod's DISCRETE is accepted as CATEGORICAL."""
    name = getattr(vartype, "name", vartype)
    if isinstance(name, str) and name.upper() in {"CATEGORICAL", "DISCRETE"}:
        return "CATEGORICAL"
    return normalize_vartype(vartype)


def best_index(energies: Sequence[float]) -> int:
    """Index of the minimal energy, resolving ties to the first occurrence.

    The first-minimal rule keeps ``best_sample`` / ``best_energy`` and the
    diagnostics ``distance_to_best`` trace deterministic on degenerate optima.
    The runtime and :class:`SampleResult` share this one definition so their
    reported best state can never disagree.
    """
    return min(range(len(energies)), key=energies.__getitem__)


def _resolve_num_states(
    num_states: Mapping[Variable, int] | int | None,
    vartype: ResultVartype,
    variables: tuple[Variable, ...],
) -> dict[Variable, int] | None:
    """Validate and broadcast per-variable categorical state counts."""
    if vartype != "CATEGORICAL":
        if num_states is not None:
            raise ValueError(f"num_states applies only to CATEGORICAL results, not {vartype}")
        return None
    if num_states is None:
        raise ValueError("CATEGORICAL results require num_states")
    if isinstance(num_states, Mapping):
        missing = [variable for variable in variables if variable not in num_states]
        if missing:
            raise ValueError(f"num_states is missing variables {missing!r}")
        counts = {variable: num_states[variable] for variable in variables}
    else:
        counts = {variable: num_states for variable in variables}
    for variable, count in counts.items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 2:
            raise ValueError(f"num_states for {variable!r} must be an integer >= 2, got {count!r}")
    return counts


@dataclass(frozen=True, slots=True)
class SampleResult:
    """Container for sampler outputs under a fixed variable order.

    ``vartype`` covers spin and binary samples from the Ising path plus
    CATEGORICAL samples for k-ary (Potts-style) models, whose per-variable
    state counts are recorded in ``num_states``.
    """

    samples: tuple[Mapping[Variable, int], ...]
    variables: tuple[Variable, ...]
    energies: tuple[float, ...]
    vartype: ResultVartype = "SPIN"
    interaction_energies: tuple[float, ...] | None = None
    traces: Mapping[str, Any] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    num_states: Mapping[Variable, int] | int | None = None

    def __post_init__(self) -> None:
        vartype = normalize_result_vartype(self.vartype)
        variables = tuple(self.variables)
        samples = tuple(dict(sample) for sample in self.samples)
        energies = tuple(
            finite_float(energy, name=f"energy at index {index}")
            for index, energy in enumerate(self.energies)
        )
        interaction_energies = (
            energies
            if self.interaction_energies is None
            else tuple(
                finite_float(energy, name=f"interaction energy at index {index}")
                for index, energy in enumerate(self.interaction_energies)
            )
        )

        if len(samples) != len(energies):
            raise ValueError("samples and energies must have the same length")
        if len(interaction_energies) != len(energies):
            raise ValueError("interaction_energies and energies must have the same length")
        if not samples:
            raise ValueError("SampleResult requires at least one sample")
        if len(set(variables)) != len(variables):
            raise ValueError("variables must be unique")
        num_states = _resolve_num_states(self.num_states, vartype, variables)
        if vartype == "CATEGORICAL":
            assert num_states is not None
            domains: Mapping[Variable, Any] = {
                variable: range(num_states[variable]) for variable in variables
            }
        else:
            shared = (-1, 1) if vartype == "SPIN" else (0, 1)
            domains = {variable: shared for variable in variables}
        kind = vartype.lower()
        variable_set = set(variables)
        for index, sample in enumerate(samples):
            missing = [variable for variable in variables if variable not in sample]
            if missing:
                raise ValueError(f"sample {index} is missing variables {missing!r}")
            extra = [variable for variable in sample if variable not in variable_set]
            if extra:
                raise ValueError(f"sample {index} has unexpected variables {extra!r}")
            for variable in variables:
                value = sample[variable]
                if isinstance(value, bool) or value not in domains[variable]:
                    raise ValueError(f"sample {index} has invalid {kind} value {value!r} for {variable!r}")

        object.__setattr__(
            self,
            "samples",
            tuple(MappingProxyType(sample) for sample in samples),
        )
        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "energies", energies)
        object.__setattr__(self, "interaction_energies", interaction_energies)
        object.__setattr__(self, "vartype", vartype)
        object.__setattr__(
            self,
            "traces",
            freeze(dict(self.traces)),
        )
        object.__setattr__(
            self,
            "diagnostics",
            freeze(dict(self.diagnostics)),
        )
        object.__setattr__(
            self,
            "metadata",
            freeze(dict(self.metadata)),
        )
        object.__setattr__(
            self,
            "num_states",
            None if num_states is None else freeze(num_states),
        )

    @classmethod
    def from_model(
        cls,
        model: IsingModel,
        samples: Sequence[Mapping[Variable, int]],
        *,
        vartype: Vartype = "SPIN",
        traces: Mapping[str, Any] | None = None,
        diagnostics: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "SampleResult":
        """Build a result and compute energies from the canonical model."""
        normalized_vartype = normalize_vartype(vartype)
        # __post_init__ copies each sample defensively, so only materialize here.
        sample_rows = tuple(samples)
        energies = tuple(model.energy(sample, vartype=normalized_vartype) for sample in sample_rows)
        interaction_energies = tuple(
            model.interaction_energy(sample, vartype=normalized_vartype) for sample in sample_rows
        )
        interactions_by_total: dict[float, set[float]] = {}
        for total_energy, interaction_energy in zip(energies, interaction_energies):
            interactions_by_total.setdefault(total_energy, set()).add(interaction_energy)
        reported_energy_collision_count = sum(
            len(interactions) - 1 for interactions in interactions_by_total.values()
        )
        result_metadata = dict(model.metadata)
        if metadata:
            result_metadata.update(metadata)
        result_metadata.update(
            {
                "source_model_format": model.source_format,
                "conversion_offset": model.offset,
                "variable_order": list(model.variables),
                "best_sample_selection_basis": "offset-free Ising interaction energy",
                "reported_energy_collision_count": reported_energy_collision_count,
            }
        )
        return cls(
            samples=sample_rows,
            variables=model.variables,
            energies=energies,
            vartype=normalized_vartype,
            interaction_energies=interaction_energies,
            traces={} if traces is None else traces,
            diagnostics={} if diagnostics is None else diagnostics,
            metadata=result_metadata,
        )

    @property
    def best_index(self) -> int:
        assert self.interaction_energies is not None
        return best_index(self.interaction_energies)

    @property
    def best_sample(self) -> dict[Variable, int]:
        return dict(self.samples[self.best_index])

    @property
    def best_energy(self) -> float:
        return self.energies[self.best_index]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the schema without requiring optional dependencies."""
        num_states = self.num_states if isinstance(self.num_states, Mapping) else None
        return {
            "samples": [dict(sample) for sample in self.samples],
            "variables": list(self.variables),
            "energies": list(self.energies),
            "interaction_energies": list(self.interaction_energies or ()),
            "best_sample": self.best_sample,
            "best_energy": self.best_energy,
            "vartype": self.vartype,
            "num_states": None if num_states is None else dict(num_states),
            "traces": thaw(self.traces),
            "diagnostics": thaw(self.diagnostics),
            "metadata": thaw(self.metadata),
        }

    def to_dimod(self) -> Any:
        """Return a dimod SampleSet when dimod is installed."""
        try:
            import dimod  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - exercised only without optional dep
            raise ImportError("SampleResult.to_dimod() requires the optional 'dimod' package") from error
        dimod_vartype = "DISCRETE" if self.vartype == "CATEGORICAL" else self.vartype
        samples_like = (
            [[sample[variable] for variable in self.variables] for sample in self.samples],
            list(self.variables),
        )
        return dimod.SampleSet.from_samples(
            samples_like,
            dimod_vartype,
            list(self.energies),
            info=thaw(self.metadata),
            sort_labels=False,
            interaction_energy=list(self.interaction_energies or ()),
        )
