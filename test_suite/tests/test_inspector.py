"""Artifact-only and independent-oracle tests for the Inspector core."""

from __future__ import annotations

import hashlib
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.inspector import Inspector  # noqa: E402
from gibbsiq.model import IsingModel  # noqa: E402
from gibbsiq.result import SampleResult  # noqa: E402
from gibbsiq.thrml_runtime import THRMLSampler  # noqa: E402


class _OpaqueLabel:
    """Hashable custom label whose repr must not enter Inspector evidence."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.repr_calls = 0

    def __repr__(self) -> str:
        self.repr_calls += 1
        return f"opaque<{self.name}>@{id(self):x}"


def _independent_energy(
    model: IsingModel,
    sample: dict[object, int],
    vartype: str,
) -> tuple[float, float]:
    """Recompute EVAL-EQ-001 without calling an IsingModel energy method."""
    spins = {
        variable: (sample[variable] if vartype == "SPIN" else 2 * sample[variable] - 1)
        for variable in model.variables
    }
    interaction = math.fsum(
        [model.linear[variable] * spins[variable] for variable in model.variables]
        + [coefficient * spins[left] * spins[right] for (left, right), coefficient in model.quadratic.items()]
    )
    return math.fsum((model.offset, interaction)), interaction


def _normalized_hex(value: float) -> str:
    return float.hex(0.0 if value == 0.0 else value)


def _independent_fingerprint(model: IsingModel) -> tuple[str, dict[str, object]]:
    """Reproduce the documented positional fingerprint outside Inspector."""
    positions = {variable: index for index, variable in enumerate(model.variables)}
    quadratic = []
    for (left, right), coefficient in model.quadratic.items():
        left_index = positions[left]
        right_index = positions[right]
        if left_index > right_index:
            left_index, right_index = right_index, left_index
        quadratic.append([left_index, right_index, _normalized_hex(coefficient)])
    quadratic.sort(key=lambda row: (row[0], row[1]))
    payload: dict[str, object] = {
        "schema": "gibbsiq.ising_energy.v1",
        "vartype": "SPIN",
        "num_variables": len(model.variables),
        "offset": _normalized_hex(model.offset),
        "linear": [_normalized_hex(model.linear[variable]) for variable in model.variables],
        "quadratic": quadratic,
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest(), payload


def _model_and_result(
    *,
    offset: float = 4.25,
    vartype: str = "SPIN",
    metadata: dict[str, object] | None = None,
) -> tuple[IsingModel, SampleResult]:
    model = compile_ising(
        {"left": 0.75, "right": -1.25},
        {("left", "right"): 0.5},
        variables=("left", "right"),
        offset=offset,
        metadata={} if metadata is None else metadata,
    )
    spin_samples = (
        {"left": 1, "right": 1},
        {"left": -1, "right": 1},
        {"left": 1, "right": -1},
        {"left": -1, "right": -1},
    )
    samples = (
        spin_samples
        if vartype == "SPIN"
        else tuple(
            {variable: (value + 1) // 2 for variable, value in sample.items()} for sample in spin_samples
        )
    )
    result = SampleResult.from_model(
        model,
        samples,
        vartype=vartype,  # type: ignore[arg-type]
        traces={
            "energy": [[6.0, 4.0], [5.0, 4.0]],
            "chain_labels": ["alpha", "beta"],
        },
        diagnostics={
            "flags": ["chain_disagreement"],
            "future_metric": {"status": "experimental", "value": 17},
        },
        metadata={
            "backend": "stored-test-artifact",
            "seed": 481,
            "timing": {"sample_seconds": 0.125},
        },
    )
    return model, result


class InspectorArtifactOnlyTests(unittest.TestCase):
    def test_construction_does_not_execute_sampler(self) -> None:
        _, result = _model_and_result()

        with patch.object(
            THRMLSampler,
            "sample",
            side_effect=AssertionError("Inspector must not execute THRML"),
        ) as sample:
            report = Inspector.from_result(result)

        sample.assert_not_called()
        payload = report.to_dict()
        self.assertEqual(payload["artifact"]["sample_count"], len(result.samples))
        self.assertEqual(payload["model_association"]["status"], "not_available")
        self.assertIn("no caller-supplied model", payload["model_association"]["reason"])
        self.assertEqual(
            payload["model_association"]["objective_recomputation"]["status"],
            "not_available",
        )
        self.assertNotIn("model_fingerprint", payload["model_association"])

    def test_first_tie_interaction_argmin_selects_same_total_and_sample_row(self) -> None:
        result = SampleResult(
            samples=(
                {"x": -1},
                {"x": 1},
                {"x": -1},
            ),
            variables=("x",),
            energies=(-100.0, 91.0, -200.0),
            interaction_energies=(4.0, -3.0, -3.0),
        )

        best = Inspector.from_result(result).to_dict()["best_row"]

        expected_index = min(
            range(len(result.interaction_energies)),
            key=result.interaction_energies.__getitem__,
        )
        self.assertEqual(expected_index, 1)
        self.assertEqual(best["index"], expected_index)
        self.assertEqual(best["stored_total_energy"], result.energies[expected_index])
        self.assertEqual(
            best["stored_interaction_energy"],
            result.interaction_energies[expected_index],
        )
        self.assertEqual(best["sample_values"], [-1 if expected_index != 1 else 1])
        self.assertEqual(best["selection_basis"], "first_argmin_stored_interaction_energy")

    def test_traces_diagnostics_unknown_fields_and_metadata_are_preserved(self) -> None:
        _, result = _model_and_result()

        payload = Inspector.from_result(result).to_dict()

        self.assertEqual(payload["traces"]["status"], "available")
        self.assertEqual(payload["traces"]["data"]["energy"], [[6.0, 4.0], [5.0, 4.0]])
        self.assertEqual(payload["diagnostics"]["status"], "available")
        self.assertEqual(
            payload["diagnostics"]["data"]["future_metric"],
            {"status": "experimental", "value": 17},
        )
        self.assertEqual(payload["warnings"]["items"], ["chain_disagreement"])
        self.assertEqual(payload["metadata"]["data"]["backend"], "stored-test-artifact")
        self.assertEqual(payload["metadata"]["data"]["seed"], 481)

    def test_sample_key_order_does_not_change_positional_summary(self) -> None:
        model = compile_ising(
            {"a": 0.5, "b": -0.25},
            {("a", "b"): 0.75},
            variables=("a", "b"),
        )
        ordered = SampleResult.from_model(model, ({"a": 1, "b": -1},))
        reordered = SampleResult.from_model(model, ({"b": -1, "a": 1},))

        ordered_payload = Inspector.from_result(ordered, model=model).to_dict()
        reordered_payload = Inspector.from_result(reordered, model=model).to_dict()

        self.assertEqual(ordered_payload, reordered_payload)
        self.assertEqual(ordered_payload["best_row"]["sample_values"], [1, -1])

    def test_same_type_opaque_evidence_keys_do_not_leak_insertion_order(self) -> None:
        first = _OpaqueLabel("first")
        second = _OpaqueLabel("second")
        common = {
            "samples": ({"x": 1},),
            "variables": ("x",),
            "energies": (0.0,),
        }
        forward = SampleResult(
            **common,
            metadata={first: "z-value", second: "a-value"},
        )
        reversed_order = SampleResult(
            **common,
            metadata={second: "a-value", first: "z-value"},
        )
        first.repr_calls = 0
        second.repr_calls = 0

        forward_json = Inspector.from_result(forward).to_json()
        reversed_json = Inspector.from_result(reversed_order).to_json()

        self.assertEqual(forward_json, reversed_json)
        self.assertEqual((first.repr_calls, second.repr_calls), (0, 0))
        entries = json.loads(forward_json)["metadata"]["data"]["entries"]
        self.assertEqual([entry["value"] for entry in entries], ["a-value", "z-value"])

    def test_absent_optional_sections_are_explicitly_unavailable(self) -> None:
        result = SampleResult(
            samples=({"x": 1},),
            variables=("x",),
            energies=(2.0,),
            interaction_energies=(2.0,),
        )

        payload = Inspector.from_result(result).to_dict()

        for section in ("traces", "diagnostics", "warnings", "metadata"):
            with self.subTest(section=section):
                self.assertEqual(payload[section]["status"], "not_available")
                self.assertTrue(payload[section]["reason"])
        for section in (
            "compiled_manifest",
            "topology",
            "block_schedule",
            "constraint_feasibility",
            "baseline_comparison",
            "thermodynamic_profile",
            "html_report",
        ):
            with self.subTest(section=section):
                self.assertEqual(payload["availability"][section]["status"], "not_available")
                self.assertTrue(payload["availability"][section]["reason"])

    def test_json_and_markdown_are_deterministic_round_trippable_summaries(self) -> None:
        _, result = _model_and_result()
        report = Inspector.from_result(result)

        first_json = report.to_json()
        second_json = report.to_json()
        first_markdown = report.to_markdown()
        second_markdown = report.to_markdown()

        self.assertEqual(first_json, second_json)
        self.assertEqual(first_markdown, second_markdown)
        self.assertEqual(json.loads(first_json), report.to_dict())
        self.assertIn("# Gibbsiq Inspector Summary", first_markdown)
        self.assertIn("## Best stored row", first_markdown)
        self.assertIn("not_available", first_markdown)

        detached = report.to_dict()
        detached["artifact"]["sample_count"] = -1
        self.assertEqual(report.to_dict()["artifact"]["sample_count"], len(result.samples))

    def test_hostile_and_custom_labels_render_without_repr_or_markdown_breakout(self) -> None:
        opaque = _OpaqueLabel("address-bearing")
        hostile = "`````\n| forged | row |\n<script>alert(1)</script>"
        labels = (opaque, hostile)
        model = compile_ising(
            {opaque: 0.25, hostile: -0.5},
            {(opaque, hostile): 0.75},
            variables=labels,
            offset=1.0,
        )
        result = SampleResult.from_model(model, ({opaque: 1, hostile: -1},))
        opaque.repr_calls = 0

        report = Inspector.from_result(result, model=model)
        json_text = report.to_json()
        markdown = report.to_markdown()

        self.assertEqual(opaque.repr_calls, 0)
        self.assertNotIn(f"opaque<{opaque.name}>", json_text)
        self.assertNotIn(f"opaque<{opaque.name}>", markdown)
        payload = json.loads(json_text)
        self.assertEqual(payload["artifact"]["sample_count"], 1)
        self.assertEqual(payload["best_row"]["sample_values"], [1, -1])
        self.assertIn("script", json_text)
        self.assertIn("``````", markdown)


class InspectorModelAssociationTests(unittest.TestCase):
    def test_spin_and_binary_rows_are_all_independently_verified(self) -> None:
        for vartype in ("SPIN", "BINARY"):
            with self.subTest(vartype=vartype):
                model, result = _model_and_result(vartype=vartype)
                payload = Inspector.from_result(result, model=model).to_dict()
                association = payload["model_association"]

                self.assertEqual(association["status"], "caller_supplied_sample_checked")
                self.assertEqual(association["checked_row_count"], len(result.samples))
                self.assertEqual(association["result_vartype"], vartype)
                self.assertEqual(association["verification_tolerance"], 1e-9)
                self.assertEqual(association["relative_tolerance"], 0.0)
                for index, sample in enumerate(result.samples):
                    expected_total, expected_interaction = _independent_energy(
                        model,
                        dict(sample),
                        vartype,
                    )
                    self.assertTrue(
                        math.isclose(result.energies[index], expected_total, rel_tol=0.0, abs_tol=1e-9)
                    )
                    self.assertTrue(
                        math.isclose(
                            result.interaction_energies[index],
                            expected_interaction,
                            rel_tol=0.0,
                            abs_tol=1e-9,
                        )
                    )

    def test_offset_is_reported_and_offset_shift_requires_matching_totals(self) -> None:
        model, result = _model_and_result(offset=12.5)

        payload = Inspector.from_result(result, model=model).to_dict()

        best_index = min(
            range(len(result.interaction_energies)),
            key=result.interaction_energies.__getitem__,
        )
        self.assertEqual(payload["model_association"]["model_offset"], 12.5)
        self.assertEqual(payload["metadata"]["data"]["conversion_offset"], 12.5)
        self.assertEqual(
            payload["best_row"]["stored_total_energy"],
            result.interaction_energies[best_index] + 12.5,
        )

        shifted_model = compile_ising(
            dict(model.linear),
            dict(model.quadratic),
            variables=model.variables,
            offset=model.offset + 3.0,
        )
        with self.assertRaisesRegex(ValueError, r"total energy mismatch at row 0"):
            Inspector.from_result(result, model=shifted_model)

    def test_every_total_and_interaction_row_is_checked_at_absolute_tolerance(self) -> None:
        model, correct = _model_and_result()
        corruptions = (
            ("total", 2, 2.0e-9, r"total energy mismatch at row 2"),
            ("interaction", 3, -2.0e-9, r"interaction energy mismatch at row 3"),
        )
        for field, row, delta, message in corruptions:
            with self.subTest(field=field, row=row):
                totals = list(correct.energies)
                interactions = list(correct.interaction_energies)
                if field == "total":
                    totals[row] += delta
                else:
                    interactions[row] += delta
                corrupted = SampleResult(
                    samples=correct.samples,
                    variables=correct.variables,
                    energies=tuple(totals),
                    vartype=correct.vartype,
                    interaction_energies=tuple(interactions),
                )
                with self.assertRaisesRegex(ValueError, message):
                    Inspector.from_result(corrupted, model=model)

        within_tolerance = SampleResult(
            samples=correct.samples,
            variables=correct.variables,
            energies=(correct.energies[0] + 0.5e-9, *correct.energies[1:]),
            vartype=correct.vartype,
            interaction_energies=correct.interaction_energies,
        )
        Inspector.from_result(within_tolerance, model=model)

    def test_variable_order_and_vartype_mismatches_fail_closed(self) -> None:
        model, result = _model_and_result()
        reordered_model = compile_ising(
            {"left": 0.75, "right": -1.25},
            {("left", "right"): 0.5},
            variables=("right", "left"),
            offset=model.offset,
        )
        with self.assertRaisesRegex(ValueError, "variable order mismatch"):
            Inspector.from_result(result, model=reordered_model)

        categorical = SampleResult(
            samples=({"left": 0, "right": 1},),
            variables=("left", "right"),
            energies=(0.0,),
            vartype="CATEGORICAL",
            num_states=2,
        )
        with self.assertRaisesRegex(ValueError, "result vartype.*SPIN or BINARY"):
            Inspector.from_result(categorical, model=model)

    def test_variable_order_rejects_equality_alias_labels(self) -> None:
        aliases = (
            (True, 1),
            ((True,), (1,)),
            (frozenset({True}), frozenset({1})),
        )
        for result_label, model_label in aliases:
            with self.subTest(result_label=result_label, model_label=model_label):
                model = IsingModel(
                    variables=(model_label,),
                    linear={model_label: 2.0},
                    quadratic={},
                    offset=3.0,
                )
                result = SampleResult(
                    samples=({result_label: 1},),
                    variables=(result_label,),
                    energies=(5.0,),
                    interaction_energies=(2.0,),
                    vartype="SPIN",
                )
                with self.assertRaisesRegex(ValueError, "variable order mismatch"):
                    Inspector.from_result(result, model=model)

    def test_fingerprint_matches_independent_payload_and_golden_digest(self) -> None:
        model, result = _model_and_result()
        expected_digest, expected_payload = _independent_fingerprint(model)

        association = Inspector.from_result(result, model=model).to_dict()["model_association"]

        self.assertEqual(association["fingerprint_schema"], "gibbsiq.ising_energy.v1")
        self.assertEqual(association["model_fingerprint"], expected_digest)
        self.assertEqual(association["fingerprint_payload"], expected_payload)
        self.assertEqual(
            expected_digest,
            "a7b042c433de7bb4c0ec3d71cfa63296019744fcfaae2f2d0761874a75291ff5",
        )

    def test_fingerprint_ignores_metadata_and_label_repr_but_tracks_energy_table(self) -> None:
        base_model, base_result = _model_and_result(metadata={"run": "base"})
        metadata_model, metadata_result = _model_and_result(metadata={"run": "changed"})
        base = Inspector.from_result(base_result, model=base_model).to_dict()["model_association"]
        metadata_only = Inspector.from_result(
            metadata_result,
            model=metadata_model,
        ).to_dict()["model_association"]
        self.assertEqual(base["model_fingerprint"], metadata_only["model_fingerprint"])

        changed_model = compile_ising(
            {"left": 0.875, "right": -1.25},
            {("left", "right"): 0.5},
            variables=("left", "right"),
            offset=4.25,
        )
        changed_result = SampleResult.from_model(changed_model, base_result.samples)
        changed = Inspector.from_result(
            changed_result,
            model=changed_model,
        ).to_dict()["model_association"]
        self.assertNotEqual(base["model_fingerprint"], changed["model_fingerprint"])

        reordered_model = compile_ising(
            {"left": 0.75, "right": -1.25},
            {("left", "right"): 0.5},
            variables=("right", "left"),
            offset=4.25,
        )
        reordered_result = SampleResult.from_model(reordered_model, ({"right": -1, "left": 1},))
        reordered = Inspector.from_result(
            reordered_result,
            model=reordered_model,
        ).to_dict()["model_association"]
        self.assertNotEqual(base["model_fingerprint"], reordered["model_fingerprint"])

        first_labels = (_OpaqueLabel("first-a"), _OpaqueLabel("first-b"))
        second_labels = (_OpaqueLabel("second-a"), _OpaqueLabel("second-b"))
        opaque_fingerprints = []
        for labels in (first_labels, second_labels):
            opaque_model = compile_ising(
                {labels[0]: 0.75, labels[1]: -1.25},
                {(labels[0], labels[1]): 0.5},
                variables=labels,
                offset=4.25,
            )
            opaque_result = SampleResult.from_model(
                opaque_model,
                ({labels[0]: 1, labels[1]: -1},),
            )
            for label in labels:
                label.repr_calls = 0
            opaque_fingerprints.append(
                Inspector.from_result(
                    opaque_result,
                    model=opaque_model,
                ).to_dict()["model_association"]["model_fingerprint"]
            )
            self.assertEqual([label.repr_calls for label in labels], [0, 0])
        self.assertEqual(opaque_fingerprints[0], opaque_fingerprints[1])

    def test_fingerprint_normalizes_signed_zero(self) -> None:
        positive_zero = compile_ising(
            {"x": 0.0},
            variables=("x",),
            offset=0.0,
        )
        negative_zero = compile_ising(
            {"x": -0.0},
            variables=("x",),
            offset=-0.0,
        )
        positive_result = SampleResult.from_model(positive_zero, ({"x": 1},))
        negative_result = SampleResult.from_model(negative_zero, ({"x": 1},))

        positive = Inspector.from_result(
            positive_result,
            model=positive_zero,
        ).to_dict()["model_association"]
        negative = Inspector.from_result(
            negative_result,
            model=negative_zero,
        ).to_dict()["model_association"]

        self.assertEqual(positive["model_fingerprint"], negative["model_fingerprint"])
        self.assertEqual(positive["fingerprint_payload"]["offset"], "0x0.0p+0")
        self.assertEqual(positive["fingerprint_payload"]["linear"], ["0x0.0p+0"])


if __name__ == "__main__":
    unittest.main()
