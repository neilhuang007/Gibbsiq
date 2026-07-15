"""Deterministic, artifact-only summaries for stored sampler results.

The Inspector consumes :class:`~gibbsiq.result.SampleResult` evidence. It never
executes a sampler. A caller-supplied :class:`~gibbsiq.model.IsingModel` enables
strict all-row objective verification; absent that association, stored energies
remain explicitly unverified.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from typing import Any, cast

from gibbsiq._frozen import freeze, thaw
from gibbsiq.benchmark_oracle import DEFAULT_TOLERANCE
from gibbsiq.model import IsingModel, Variable, Vartype
from gibbsiq.result import SampleResult

SUMMARY_SCHEMA_VERSION = "gibbsiq.inspector.summary.v1"
FINGERPRINT_SCHEMA = "gibbsiq.ising_energy.v1"


def _normalized_binary64_hex(value: float) -> str:
    """Encode one finite binary64 value, normalizing signed zero."""
    return float.hex(0.0 if value == 0.0 else value)


def _fingerprint_payload(model: IsingModel) -> dict[str, Any]:
    positions = {variable: index for index, variable in enumerate(model.variables)}
    quadratic: list[list[int | str]] = []
    for (left, right), coefficient in model.quadratic.items():
        left_index = positions[left]
        right_index = positions[right]
        if left_index > right_index:
            left_index, right_index = right_index, left_index
        quadratic.append(
            [
                left_index,
                right_index,
                _normalized_binary64_hex(coefficient),
            ]
        )
    quadratic.sort(key=lambda row: (row[0], row[1]))
    return {
        "schema": FINGERPRINT_SCHEMA,
        "vartype": "SPIN",
        "num_variables": len(model.variables),
        "offset": _normalized_binary64_hex(model.offset),
        "linear": [_normalized_binary64_hex(model.linear[variable]) for variable in model.variables],
        "quadratic": quadratic,
    }


def _model_fingerprint(model: IsingModel) -> tuple[str, dict[str, Any]]:
    payload = _fingerprint_payload(model)
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest(), payload


def _python_type_name(value: object) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _label_token(label: Variable) -> dict[str, Any]:
    """Return deterministic JSON evidence for a positional variable label.

    Built-in immutable labels retain their values. An arbitrary custom object is
    represented by its Python type and its position in the surrounding order;
    object identity and ``repr`` are deliberately excluded.
    """
    if label is None:
        return {"kind": "none"}
    if isinstance(label, bool):
        return {"kind": "bool", "value": label}
    if isinstance(label, int):
        return {"kind": "int", "value": str(label)}
    if isinstance(label, float):
        if math.isnan(label):
            value = "nan"
        elif math.isinf(label):
            value = "+inf" if label > 0.0 else "-inf"
        else:
            value = _normalized_binary64_hex(label)
        return {"kind": "float", "value": value}
    if isinstance(label, str):
        return {"kind": "str", "value": label}
    if isinstance(label, bytes):
        encoded = base64.b64encode(label).decode("ascii")
        return {"kind": "bytes", "base64": encoded}
    if isinstance(label, tuple):
        return {"kind": "tuple", "items": [_label_token(item) for item in label]}
    if isinstance(label, frozenset):
        items = [_label_token(item) for item in label]
        items.sort(key=_canonical_json)
        return {"kind": "frozenset", "items": items}
    return {"kind": "opaque", "python_type": _python_type_name(label)}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _json_evidence(value: Any) -> Any:
    """Detach stored evidence into a deterministic, finite JSON-safe value."""
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        if math.isnan(value):
            classification = "nan"
        else:
            classification = "+inf" if value > 0.0 else "-inf"
        return {"encoding": "non_finite_float", "value": classification}
    if isinstance(value, bytes):
        return {
            "encoding": "bytes_base64",
            "value": base64.b64encode(value).decode("ascii"),
        }
    if isinstance(value, Mapping):
        if all(isinstance(key, str) for key in value):
            return {str(key): _json_evidence(child) for key, child in value.items()}
        entries = [{"key": _label_token(key), "value": _json_evidence(child)} for key, child in value.items()]
        entries.sort(key=_canonical_json)
        return {"encoding": "mapping_entries_v1", "entries": entries}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_evidence(child) for child in value]
    if isinstance(value, Set):
        children = [_json_evidence(child) for child in value]
        children.sort(key=_canonical_json)
        return {"encoding": "set_items_v1", "items": children}
    return {"encoding": "opaque_python_value", "python_type": _python_type_name(value)}


def _variable_order(variables: tuple[Variable, ...]) -> list[dict[str, Any]]:
    return [
        {"position": position, "label": _label_token(variable)} for position, variable in enumerate(variables)
    ]


def _available_section(source: str, data: Any) -> dict[str, Any]:
    return {"status": "available", "source": source, "data": _json_evidence(data)}


def _unavailable(reason: str) -> dict[str, str]:
    return {"status": "not_available", "reason": reason}


def _stored_section(source: str, data: Mapping[str, Any], absent_reason: str) -> dict[str, Any]:
    if data:
        return _available_section(source, data)
    return _unavailable(absent_reason)


def _verify_model_association(result: SampleResult, model: IsingModel) -> dict[str, Any]:
    if tuple(result.variables) != tuple(model.variables):
        raise ValueError("caller-supplied model variable order mismatch")
    if result.vartype not in {"SPIN", "BINARY"}:
        raise ValueError(
            f"result vartype {result.vartype!r} is incompatible with an Ising model; expected SPIN or BINARY"
        )

    vartype = cast(Vartype, result.vartype)
    interaction_energies = result.interaction_energies
    assert interaction_energies is not None
    for row, sample in enumerate(result.samples):
        recomputed_total = model.energy(sample, vartype=vartype)
        if not math.isclose(
            result.energies[row],
            recomputed_total,
            rel_tol=0.0,
            abs_tol=DEFAULT_TOLERANCE,
        ):
            raise ValueError(
                f"total energy mismatch at row {row}: stored={result.energies[row]!r}, "
                f"recomputed={recomputed_total!r}, absolute tolerance={DEFAULT_TOLERANCE!r}"
            )
        recomputed_interaction = model.interaction_energy(sample, vartype=vartype)
        if not math.isclose(
            interaction_energies[row],
            recomputed_interaction,
            rel_tol=0.0,
            abs_tol=DEFAULT_TOLERANCE,
        ):
            raise ValueError(
                f"interaction energy mismatch at row {row}: "
                f"stored={interaction_energies[row]!r}, "
                f"recomputed={recomputed_interaction!r}, "
                f"absolute tolerance={DEFAULT_TOLERANCE!r}"
            )

    fingerprint, payload = _model_fingerprint(model)
    return {
        "status": "caller_supplied_sample_checked",
        "association_source": "caller_supplied_model",
        "checked_row_count": len(result.samples),
        "result_vartype": result.vartype,
        "variable_order": _variable_order(result.variables),
        "verification_tolerance": DEFAULT_TOLERANCE,
        "relative_tolerance": 0.0,
        "model_offset": model.offset,
        "fingerprint_schema": FINGERPRINT_SCHEMA,
        "fingerprint_encoding": "canonical_utf8_json_sorted_keys_compact",
        "model_fingerprint": fingerprint,
        "fingerprint_payload": payload,
        "objective_recomputation": {
            "status": "available",
            "method": "all_rows_total_and_interaction_energy",
        },
    }


def _no_model_association() -> dict[str, Any]:
    reason = "no caller-supplied model was available; stored energies were not independently recomputed"
    return {
        "status": "not_available",
        "reason": reason,
        "objective_recomputation": _unavailable(reason),
    }


def _summary(result: SampleResult, model: IsingModel | None) -> dict[str, Any]:
    interaction_energies = result.interaction_energies
    assert interaction_energies is not None
    selected_index = min(
        range(len(interaction_energies)),
        key=interaction_energies.__getitem__,
    )
    sample = result.samples[selected_index]
    variable_order = _variable_order(result.variables)
    num_states = result.num_states
    categorical_states = None
    if isinstance(num_states, Mapping):
        categorical_states = [num_states[variable] for variable in result.variables]

    diagnostics = result.diagnostics
    if "flags" in diagnostics:
        warnings = {
            "status": "available",
            "source": "result.diagnostics.flags",
            "items": _json_evidence(diagnostics["flags"]),
        }
    else:
        warnings = _unavailable("result.diagnostics contains no stored flags field")

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "artifact": {
            "source_type": "SampleResult",
            "variable_count": len(result.variables),
            "variable_order": variable_order,
            "vartype": result.vartype,
            "sample_count": len(result.samples),
            "categorical_num_states_by_position": categorical_states,
        },
        "stored_energies": {
            "status": "stored_artifact_values",
            "total": list(result.energies),
            "interaction": list(interaction_energies),
        },
        "best_row": {
            "index": selected_index,
            "selection_basis": "first_argmin_stored_interaction_energy",
            "sample_values": [sample[variable] for variable in result.variables],
            "variable_order": variable_order,
            "stored_total_energy": result.energies[selected_index],
            "stored_interaction_energy": interaction_energies[selected_index],
        },
        "model_association": (
            _no_model_association() if model is None else _verify_model_association(result, model)
        ),
        "traces": _stored_section(
            "result.traces",
            result.traces,
            "result artifact contains no stored traces",
        ),
        "diagnostics": _stored_section(
            "result.diagnostics",
            result.diagnostics,
            "result artifact contains no stored diagnostics",
        ),
        "warnings": warnings,
        "metadata": _stored_section(
            "result.metadata",
            result.metadata,
            "result artifact contains no stored metadata",
        ),
        "availability": {
            "compiled_manifest": _unavailable(
                "compiled-manifest binding is deferred to TM-API-001 and TM-REP-001"
            ),
            "topology": _unavailable("SampleResult contains no topology artifact"),
            "block_schedule": _unavailable("SampleResult contains no compiled block schedule"),
            "constraint_feasibility": _unavailable(
                "no general constraint contract is associated with this result"
            ),
            "baseline_comparison": _unavailable(
                "no matched baseline artifact is associated with this result"
            ),
            "thermodynamic_profile": _unavailable("no profiler artifact is associated with this result"),
            "html_report": _unavailable("static HTML rendering is deferred to TM-REP-001"),
        },
    }


@dataclass(frozen=True, slots=True)
class Inspector:
    """Immutable deterministic summary of one stored :class:`SampleResult`."""

    _summary: Mapping[str, Any]

    @classmethod
    def from_result(
        cls,
        result: SampleResult,
        *,
        model: IsingModel | None = None,
    ) -> Inspector:
        """Build an artifact-only report, optionally verifying a supplied model."""
        if not isinstance(result, SampleResult):
            raise TypeError("result must be a SampleResult")
        if model is not None and not isinstance(model, IsingModel):
            raise TypeError("model must be an IsingModel or None")
        return cls(_summary=freeze(_summary(result, model)))

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-safe summary dictionary."""
        return cast(dict[str, Any], thaw(self._summary))

    def to_json(self) -> str:
        """Return deterministic pretty-printed JSON with no NaN/Infinity tokens."""
        return (
            json.dumps(
                self.to_dict(),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        )

    def to_markdown(self) -> str:
        """Return a deterministic Markdown summary with safely fenced JSON evidence."""
        payload = self.to_dict()
        json_text = self.to_json().rstrip("\n")
        longest_run = max((len(match.group(0)) for match in re.finditer(r"`+", json_text)), default=0)
        fence = "`" * max(3, longest_run + 1)
        artifact = payload["artifact"]
        best = payload["best_row"]
        association = payload["model_association"]
        return "\n".join(
            [
                "# Gibbsiq Inspector Summary",
                "",
                f"- Schema: `{payload['schema_version']}`",
                f"- Samples: {artifact['sample_count']}",
                f"- Variables: {artifact['variable_count']}",
                f"- Vartype: `{artifact['vartype']}`",
                f"- Model association: `{association['status']}`",
                "",
                "## Best stored row",
                "",
                f"- Row: {best['index']}",
                f"- Stored interaction energy: {best['stored_interaction_energy']}",
                f"- Stored total energy: {best['stored_total_energy']}",
                "",
                "## Complete machine-readable summary",
                "",
                f"{fence}json",
                json_text,
                fence,
                "",
            ]
        )
