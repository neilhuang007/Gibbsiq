"""Solver result schema.

Stable shape for samples, energies, traces, diagnostics, metadata, and
optional dimod export.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

from gibbsiq._frozen import freeze, freeze_json_evidence, thaw
from gibbsiq.model import (
    IsingModel,
    Variable,
    Vartype,
    encode_variable_label,
    exact_mapping_index,
    exact_mapping_key,
    exact_variable_position,
    exact_variable_order,
    finite_float,
    legacy_wire_safe,
    normalize_vartype,
    variable_index,
)

ResultVartype: TypeAlias = Literal["SPIN", "BINARY", "CATEGORICAL"]
RESULT_SCHEMA_VERSION = 2
LEGACY_RESULT_SCHEMA_VERSION = 1


def normalize_result_vartype(vartype: Any) -> ResultVartype:
    """Normalize result-level vartypes; dimod's DISCRETE is accepted as CATEGORICAL."""
    name = getattr(vartype, "name", vartype)
    if isinstance(name, str) and name.upper() in {"CATEGORICAL", "DISCRETE"}:
        return "CATEGORICAL"
    return normalize_vartype(vartype)


def best_index(energies: Sequence[float]) -> int:
    """Index of minimal energy; ties resolve to first occurrence.

    Shared by the runtime and :class:`SampleResult` — keeps ``best_sample`` /
    ``best_energy`` and ``distance_to_best`` deterministic on degenerate optima.
    """
    return min(range(len(energies)), key=energies.__getitem__)


def _missing_exact_key(
    mapping: Mapping[Any, Any],
    variable: Variable,
    key_index: Mapping[Any, Any],
) -> bool:
    try:
        exact_mapping_key(mapping, variable, key_index)
    except KeyError:
        return True
    return False


def _missing_exact_position(
    variable: Variable,
    variables: tuple[Variable, ...],
    positions: Mapping[Variable, int],
) -> bool:
    try:
        exact_variable_position(variable, variables, positions)
    except KeyError:
        return True
    return False


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
        count_key_index = exact_mapping_index(num_states)
        missing = [
            variable for variable in variables if _missing_exact_key(num_states, variable, count_key_index)
        ]
        if missing:
            raise ValueError(f"num_states is missing variables {missing!r}")
        counts = {
            variable: num_states[exact_mapping_key(num_states, variable, count_key_index)]
            for variable in variables
        }
    else:
        counts = {variable: num_states for variable in variables}
    for variable, count in counts.items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 2:
            raise ValueError(f"num_states for {variable!r} must be an integer >= 2, got {count!r}")
    return counts


@dataclass(frozen=True, slots=True)
class SampleResult:
    """Sampler output under a fixed variable order.

    ``vartype``: SPIN/BINARY (Ising path) or CATEGORICAL (k-ary/Potts-style),
    with per-variable state counts in ``num_states``.
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
        samples = tuple(self.samples)
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
        positions = variable_index(variables)
        canonical_samples: list[dict[Variable, int]] = []
        for index, sample in enumerate(samples):
            if not isinstance(sample, Mapping):
                raise TypeError(f"sample {index} must be a mapping")
            sample_key_index = exact_mapping_index(sample)
            missing = [
                variable for variable in variables if _missing_exact_key(sample, variable, sample_key_index)
            ]
            if missing:
                raise ValueError(f"sample {index} is missing variables {missing!r}")
            extra = [
                candidate for candidate in sample if _missing_exact_position(candidate, variables, positions)
            ]
            if extra:
                raise ValueError(f"sample {index} has unexpected variables {extra!r}")
            canonical_sample: dict[Variable, int] = {}
            for variable in variables:
                value = sample[exact_mapping_key(sample, variable, sample_key_index)]
                if isinstance(value, bool) or value not in domains[variable]:
                    raise ValueError(f"sample {index} has invalid {kind} value {value!r} for {variable!r}")
                canonical_sample[variable] = value
            canonical_samples.append(canonical_sample)

        object.__setattr__(
            self,
            "samples",
            tuple(MappingProxyType(sample) for sample in canonical_samples),
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
        # defensive copy happens in __post_init__; just materialize the sequence here
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

    @classmethod
    def from_program(
        cls,
        program: Any,
        samples: Sequence[Mapping[Variable, int]],
        *,
        vartype: Vartype = "SPIN",
        traces: Mapping[str, Any] | None = None,
        diagnostics: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "SampleResult":
        """Expand free-variable samples from an Ising thermodynamic program."""
        from gibbsiq.program import PROGRAM_SCHEMA_VERSION, ThermodynamicProgram

        if not isinstance(program, ThermodynamicProgram):
            raise TypeError("from_program requires a ThermodynamicProgram")
        if not isinstance(program.model, IsingModel):
            raise TypeError("from_program currently supports only IsingModel programs")
        normalized_vartype = normalize_vartype(vartype)
        free_set = set(program.free_variables)
        expanded_rows: list[dict[Variable, int]] = []
        for row_index, sample in enumerate(samples):
            if not isinstance(sample, Mapping):
                raise TypeError(f"free sample {row_index} must be a mapping")
            sample_key_index = exact_mapping_index(sample)
            exact_keys = len(sample) == len(program.free_variables) and all(
                not _missing_exact_key(sample, variable, sample_key_index)
                for variable in program.free_variables
            )
            if not exact_keys:
                raise ValueError(f"free sample {row_index} keys must match program free variables exactly")
            expanded: dict[Variable, int] = {}
            for variable in program.model.variables:
                if variable in program.clamp_values:
                    spin = program.clamp_values[variable]
                    expanded[variable] = spin if normalized_vartype == "SPIN" else (spin + 1) // 2
                else:
                    expanded[variable] = sample[exact_mapping_key(sample, variable, sample_key_index)]
            expanded_rows.append(expanded)

        program_metadata = {} if metadata is None else dict(metadata)
        program_metadata.update(
            {
                "thermodynamic_program_schema": PROGRAM_SCHEMA_VERSION,
                "free_variable_positions": [
                    position
                    for position, variable in enumerate(program.model.variables)
                    if variable in free_set
                ],
                "clamped_variable_positions": [
                    position
                    for position, variable in enumerate(program.model.variables)
                    if variable in program.clamp_values
                ],
                "thermodynamic_program_metadata": dict(program.metadata),
            }
        )
        return cls.from_model(
            program.model,
            expanded_rows,
            vartype=normalized_vartype,
            traces=traces,
            diagnostics=diagnostics,
            metadata=program_metadata,
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
        """Serialize without allowing JSON object-key coercion to merge labels."""
        num_states = self.num_states if isinstance(self.num_states, Mapping) else None
        traces = thaw(freeze_json_evidence(self.traces, name="traces"))
        diagnostics = thaw(freeze_json_evidence(self.diagnostics, name="diagnostics"))
        if legacy_wire_safe(self.variables):
            metadata = thaw(freeze_json_evidence(self.metadata, name="metadata"))
            return {
                "schema_version": LEGACY_RESULT_SCHEMA_VERSION,
                "samples": [dict(sample) for sample in self.samples],
                "variables": list(self.variables),
                "best_sample": self.best_sample,
                "num_states": None if num_states is None else dict(num_states),
                "energies": list(self.energies),
                "interaction_energies": list(self.interaction_energies or ()),
                "best_energy": self.best_energy,
                "vartype": self.vartype,
                "traces": traces,
                "diagnostics": diagnostics,
                "metadata": metadata,
            }

        encoded_variables = [encode_variable_label(variable) for variable in self.variables]
        metadata_source = dict(self.metadata)
        includes_variable_order = exact_variable_order(metadata_source.get("variable_order"), self.variables)
        if includes_variable_order:
            metadata_source.pop("variable_order")
        metadata = thaw(freeze_json_evidence(metadata_source, name="metadata"))
        if includes_variable_order:
            metadata["variable_order"] = encoded_variables
        return {
            "schema_version": RESULT_SCHEMA_VERSION,
            "samples": [[sample[variable] for variable in self.variables] for sample in self.samples],
            "variables": encoded_variables,
            "best_sample": [self.best_sample[variable] for variable in self.variables],
            "num_states": (
                None if num_states is None else [num_states[variable] for variable in self.variables]
            ),
            "energies": list(self.energies),
            "interaction_energies": list(self.interaction_energies or ()),
            "best_energy": self.best_energy,
            "vartype": self.vartype,
            "traces": traces,
            "diagnostics": diagnostics,
            "metadata": metadata,
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
