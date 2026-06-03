"""Initial solver result schema.

Stage 1 does not implement a sampler, but downstream layers need a stable shape
for samples, energies, traces, diagnostics, metadata, and optional dimod export.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from gibbsiq.model import IsingModel, Variable, Vartype, normalize_vartype


@dataclass(frozen=True)
class SampleResult:
    """Container for sampler outputs under a fixed variable order."""

    samples: tuple[dict[Variable, int], ...]
    variables: tuple[Variable, ...]
    energies: tuple[float, ...]
    vartype: Vartype = "SPIN"
    traces: Mapping[str, Any] = field(default_factory=dict)
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        vartype = normalize_vartype(self.vartype)
        variables = tuple(self.variables)
        samples = tuple(dict(sample) for sample in self.samples)
        energies = tuple(float(energy) for energy in self.energies)

        if len(samples) != len(energies):
            raise ValueError("samples and energies must have the same length")
        if not samples:
            raise ValueError("SampleResult requires at least one sample")
        if len(set(variables)) != len(variables):
            raise ValueError("variables must be unique")
        valid_values = (-1, 1) if vartype == "SPIN" else (0, 1)
        kind = "spin" if vartype == "SPIN" else "binary"
        for index, sample in enumerate(samples):
            missing = [variable for variable in variables if variable not in sample]
            if missing:
                raise ValueError(f"sample {index} is missing variables {missing!r}")
            for variable in variables:
                value = sample[variable]
                if value not in valid_values:
                    raise ValueError(f"sample {index} has invalid {kind} value {value!r} for {variable!r}")

        object.__setattr__(self, "samples", samples)
        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "energies", energies)
        object.__setattr__(self, "vartype", vartype)
        object.__setattr__(self, "traces", dict(self.traces))
        object.__setattr__(self, "diagnostics", dict(self.diagnostics))
        object.__setattr__(self, "metadata", dict(self.metadata))

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
        sample_rows = tuple(dict(sample) for sample in samples)
        energies = tuple(model.energy(sample, vartype=normalized_vartype) for sample in sample_rows)
        result_metadata = {
            "source_model_format": model.source_format,
            "conversion_offset": model.offset,
            "variable_order": list(model.variables),
        }
        result_metadata.update(model.metadata)
        if metadata:
            result_metadata.update(metadata)
        return cls(
            samples=sample_rows,
            variables=model.variables,
            energies=energies,
            vartype=normalized_vartype,
            traces={} if traces is None else traces,
            diagnostics={} if diagnostics is None else diagnostics,
            metadata=result_metadata,
        )

    @property
    def best_index(self) -> int:
        return min(range(len(self.energies)), key=self.energies.__getitem__)

    @property
    def best_sample(self) -> dict[Variable, int]:
        return dict(self.samples[self.best_index])

    @property
    def best_energy(self) -> float:
        return self.energies[self.best_index]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the schema without requiring optional dependencies."""
        return {
            "samples": [dict(sample) for sample in self.samples],
            "variables": list(self.variables),
            "energies": list(self.energies),
            "best_sample": self.best_sample,
            "best_energy": self.best_energy,
            "vartype": self.vartype,
            "traces": dict(self.traces),
            "diagnostics": dict(self.diagnostics),
            "metadata": dict(self.metadata),
        }

    def to_dimod(self) -> Any:
        """Return a dimod SampleSet when dimod is installed."""
        try:
            import dimod  # type: ignore[import-not-found]
        except ImportError as error:  # pragma: no cover - exercised only without optional dep
            raise ImportError("SampleResult.to_dimod() requires the optional 'dimod' package") from error
        return dimod.SampleSet.from_samples(
            [dict(sample) for sample in self.samples],
            self.vartype,
            list(self.energies),
            info=dict(self.metadata),
        )
