from __future__ import annotations

import math
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from gibbsiq.qualification.contracts import (  # noqa: E402
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
    Policy,
    QualificationReport,
    RandomizationSpec,
    ResourceBudget,
    RunPlan,
    SamplingSettings,
    WorkloadSpec,
    canonical_json,
    parse_json,
)


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


def artifact(name: str, digest: str = DIGEST_A) -> ArtifactIdentity:
    return ArtifactIdentity(name, "v1", digest)


def exact_metric(
    metric_id: str = "exact-error",
    *,
    mandatory: bool = True,
) -> MetricSpec:
    return MetricSpec(
        metric_id=metric_id,
        units="absolute error",
        direction="smaller_is_better",
        comparison="candidate-reference",
        acceptance=Acceptance("upper", upper=0.1),
        evidence_mode="exact",
        planned_units=1,
        replication_unit="deterministic",
        scope="fixed_inputs",
        mandatory=mandatory,
    )


def bounded_metric(
    metric_id: str = "mean-error",
    *,
    mandatory: bool = True,
    planned_units: int = 4,
) -> MetricSpec:
    return MetricSpec(
        metric_id=metric_id,
        units="absolute error",
        direction="target",
        comparison="candidate-reference",
        acceptance=Acceptance("equivalence", upper=0.1, lower=-0.1),
        evidence_mode="bounded_fixed_n",
        planned_units=planned_units,
        replication_unit="independent_run",
        scope="fixed_inputs",
        bounds=Bounds(-2, 2),
        mandatory=mandatory,
    )


def acceptance_contract(*metrics: MetricSpec) -> AcceptanceContract:
    return AcceptanceContract(metrics or (exact_metric(), bounded_metric()))


def input_spec(*cases: InputCase) -> InputSpec:
    return InputSpec(
        identity=artifact("evaluation-corpus", DIGEST_A),
        preprocessing=artifact("preprocessor", DIGEST_B),
        cases=cases
        or (
            InputCase("case-1", DIGEST_A, "evaluation", "document-1"),
            InputCase("case-2", DIGEST_B, "evaluation", "document-2"),
        ),
        tokenizer=artifact("tokenizer", DIGEST_C),
        sequence_length=16,
        masks_digest=DIGEST_C,
    )


def cost_scope() -> CostScope:
    return CostScope(
        boundary="candidate operation",
        included_components=("backend execution", "synchronization"),
        excluded_components=("model load",),
        batch_size=2,
        concurrency=1,
        sequence_length=16,
    )


def workload(
    *,
    contract: AcceptanceContract | None = None,
    resources: ResourceBudget | None = None,
    inputs: InputSpec | None = None,
) -> WorkloadSpec:
    return WorkloadSpec(
        workload_id="toy-workload-v1",
        description="A bounded qualification fixture",
        sources=(artifact("source-package", DIGEST_A),),
        model_config=artifact("model-config", DIGEST_B),
        inputs=input_spec() if inputs is None else inputs,
        operations=(OperationSpec("activation", (2, 4), ("input", "feature")),),
        dtype="float32",
        precision={"accumulator": "float32", "tolerance": 0.0},
        reference=artifact("reference-backend", DIGEST_A),
        candidate=artifact("candidate-backend", DIGEST_B),
        controls=("samples", "warmup"),
        contract=acceptance_contract() if contract is None else contract,
        randomization=RandomizationSpec(7, 4),
        resources=ResourceBudget(4, 30, 4096) if resources is None else resources,
        cost_scope=cost_scope(),
        license_refs=("MIT", "https://example.test/data-license"),
        checkpoint=artifact("checkpoint", DIGEST_C),
    )


def available_result(
    metric_id: str = "exact-error",
    *,
    outcome: str = "pass",
    estimate: float = 0.05,
    observed_units: int = 1,
    planned_units: int = 1,
) -> MetricResult:
    return MetricResult(
        metric_id=metric_id,
        availability="available",
        estimate=estimate,
        interval=Bounds(estimate, estimate),
        outcome=outcome,
        observed_units=observed_units,
        planned_units=planned_units,
        unit_summaries=(estimate,) * observed_units,
    )


class JsonContractTests(unittest.TestCase):
    def test_canonical_json_is_compact_sorted_utf8_and_normalizes_negative_zero(self) -> None:
        payload = canonical_json({"z": -0.0, "é": [2, 1]})
        self.assertEqual(payload, b'{"z":0.0,"\xc3\xa9":[2,1]}')

    def test_canonical_json_rejects_lossy_or_nonfinite_values(self) -> None:
        invalid_values = (
            {1: "coerced key"},
            {"set": {1, 2}},
            {"bytes": b"payload"},
            {"nan": math.nan},
            {"infinity": math.inf},
            {"object": object()},
        )
        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_json(value)

    def test_canonical_json_rejects_cycles_and_excessive_nesting(self) -> None:
        cycle: list[object] = []
        cycle.append(cycle)
        with self.assertRaises(ValueError):
            canonical_json(cycle)

        nested: object = None
        for _ in range(200):
            nested = [nested]
        with self.assertRaises(ValueError):
            canonical_json(nested)

        with self.assertRaises(ValueError):
            canonical_json("\ud800")

    def test_parse_json_rejects_duplicate_keys_at_any_depth_and_nonfinite_numbers(self) -> None:
        invalid_texts = (
            '{"a":1,"a":2}',
            '{"outer":{"a":1,"a":2}}',
            '{"value":NaN}',
            '{"value":Infinity}',
            '{"value":-Infinity}',
        )
        for text in invalid_texts:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_json(text)

        too_deep = "[" * 1100 + "null" + "]" * 1100
        with self.assertRaises(ValueError):
            parse_json(too_deep)

    def test_parse_json_returns_detached_ordinary_json_values(self) -> None:
        parsed = parse_json('{"items":[true,null,1,1.5,"é"]}')
        self.assertEqual(parsed, {"items": [True, None, 1, 1.5, "é"]})


class MetricContractTests(unittest.TestCase):
    def test_bounds_normalize_integers_and_signed_zero(self) -> None:
        bounds = Bounds(-0.0, 2)
        self.assertEqual((bounds.lower, bounds.upper), (0.0, 2.0))
        self.assertEqual(math.copysign(1.0, bounds.lower), 1.0)

    def test_bounds_reject_invalid_numeric_values_and_reversed_interval(self) -> None:
        invalid_pairs = ((True, 1), ("0", 1), (0, math.nan), (0, math.inf), (2, 1))
        for lower, upper in invalid_pairs:
            with self.subTest(lower=lower, upper=upper), self.assertRaises(ValueError):
                Bounds(lower, upper)

    def test_acceptance_modes_require_their_exact_boundary_shape(self) -> None:
        valid = (
            Acceptance("upper", upper=0),
            Acceptance("lower", upper=None, lower=0),
            Acceptance("equivalence", upper=0.1, lower=-0.1),
        )
        self.assertEqual([item.kind for item in valid], ["upper", "lower", "equivalence"])

        invalid = (
            {"kind": "upper", "upper": 1, "lower": 0},
            {"kind": "lower", "upper": 1, "lower": 0},
            {"kind": "lower", "upper": None, "lower": None},
            {"kind": "equivalence", "upper": None, "lower": -1},
            {"kind": "equivalence", "upper": -1, "lower": 1},
            {"kind": "unknown", "upper": 1},
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                Acceptance(**arguments)

    def test_acceptance_classifies_closed_boundaries_and_strict_disjointness(self) -> None:
        upper = Acceptance("upper", upper=0.1)
        lower = Acceptance("lower", upper=None, lower=-0.1)
        equivalence = Acceptance("equivalence", upper=0.1, lower=-0.1)
        self.assertEqual(upper.classify(Bounds(0.0, 0.1)), "pass")
        self.assertEqual(upper.classify(Bounds(0.1, 0.2)), "inconclusive")
        self.assertEqual(upper.classify(Bounds(0.100001, 0.2)), "fail")
        self.assertEqual(lower.classify(Bounds(-0.1, 0.0)), "pass")
        self.assertEqual(equivalence.classify(Bounds(-0.1, 0.1)), "pass")
        self.assertEqual(equivalence.classify(Bounds(0.1, 0.2)), "inconclusive")
        self.assertEqual(equivalence.classify(Bounds(0.100001, 0.2)), "fail")
        with self.assertRaises(ValueError):
            upper.classify((-1, 1))  # type: ignore[arg-type]

    def test_metric_spec_enforces_direction_acceptance_pairing(self) -> None:
        mismatches = (
            {"direction": "larger_is_better"},
            {"direction": "target"},
            {"acceptance": Acceptance("lower", upper=None, lower=0)},
        )
        for change in mismatches:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(exact_metric(), **change)

    def test_metric_spec_rejects_invalid_modes_units_and_schema(self) -> None:
        changes = (
            {"evidence_mode": "bootstrap"},
            {"evidence_mode": "bounded_fixed_n", "bounds": None},
            {"evidence_mode": "exact", "planned_units": 2},
            {"replication_unit": "token"},
            {"scope": "population"},
            {"aggregation": "median"},
            {"planned_units": True},
            {"mandatory": 1},
            {"schema_version": 2},
            {"units": " "},
            {"comparison": ""},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(exact_metric(), **change)

    def test_bounded_metric_requires_independent_replication(self) -> None:
        with self.assertRaises(ValueError):
            replace(bounded_metric(), replication_unit="deterministic")

    def test_acceptance_contract_allocates_alpha_only_to_mandatory_bounded_metrics(self) -> None:
        contract = AcceptanceContract(
            (
                exact_metric(),
                bounded_metric("bounded-1"),
                bounded_metric("bounded-2"),
                bounded_metric("exploratory", mandatory=False),
            ),
            alpha_total=0.06,
        )
        self.assertEqual(contract.alpha_for("bounded-1"), 0.03)
        self.assertEqual(contract.alpha_for("bounded-2"), 0.03)
        self.assertIsNone(contract.alpha_for("exact-error"))
        self.assertIsNone(contract.alpha_for("exploratory"))
        with self.assertRaises(ValueError):
            contract.alpha_for("undeclared")

    def test_acceptance_contract_requires_unique_metrics_mandatory_claim_and_valid_alpha(self) -> None:
        invalid_contracts = (
            ((exact_metric(), exact_metric()), 0.05),
            ((bounded_metric(mandatory=False),), 0.05),
            ((exact_metric(),), 0.0),
            ((exact_metric(),), 1.0),
            ((exact_metric(),), True),
        )
        for metrics, alpha in invalid_contracts:
            with self.subTest(metrics=metrics, alpha=alpha), self.assertRaises(ValueError):
                AcceptanceContract(metrics, alpha_total=alpha)

        with self.assertRaises(ValueError):
            AcceptanceContract(
                (bounded_metric("bounded-1"), bounded_metric("bounded-2")),
                alpha_total=5e-324,
            )

    def test_unhashable_enum_values_are_normalized_to_value_errors(self) -> None:
        constructors = (
            lambda: Acceptance([], upper=1),
            lambda: replace(exact_metric(), direction=[]),
            lambda: replace(exact_metric(), evidence_mode={}),
            lambda: InputCase("case", DIGEST_A, [], "group"),
            lambda: RandomizationSpec(0, 1, {}),
            lambda: replace(workload(), dtype=[]),
            lambda: replace(workload(), retention={}),
        )
        for constructor in constructors:
            with self.subTest(constructor=constructor), self.assertRaises(ValueError):
                constructor()

    def test_metric_result_available_requires_complete_finite_consistent_evidence(self) -> None:
        result = MetricResult(
            "mean-error",
            "available",
            estimate=0,
            interval=Bounds(-0.1, 0.1),
            outcome="inconclusive",
            observed_units=2,
            planned_units=4,
            procedure="bounded-hoeffding-v1",
            alpha=0.05,
            unit_summaries=(-0.5, 0.5),
        )
        self.assertEqual(result.estimate, 0.0)
        self.assertEqual(result.unit_summaries, (-0.5, 0.5))

        changes = (
            {"estimate": math.nan},
            {"estimate": 2.0},
            {"interval": None},
            {"outcome": None},
            {"outcome": "pass"},
            {"observed_units": 5},
            {"unit_summaries": (0.0,)},
            {"alpha": 1.0},
            {"procedure": ""},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(result, **change)

    def test_metric_result_unavailable_requires_reason_and_no_numeric_claim(self) -> None:
        result = MetricResult(
            "mean-error",
            "unavailable",
            reason="backend did not expose this output",
            planned_units=4,
        )
        self.assertEqual(result.observed_units, 0)

        invalid = (
            {"reason": None},
            {"estimate": 0.0},
            {"interval": Bounds(0, 0)},
            {"outcome": "inconclusive"},
            {"unit_summaries": (0.0,), "observed_units": 1},
        )
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(result, **change)

        with self.assertRaises(ValueError):
            replace(result, alpha=0.05)


class WorkloadValueTests(unittest.TestCase):
    def test_artifact_identity_requires_three_nonblank_structurally_valid_fields(self) -> None:
        identity = artifact(" source ")
        self.assertEqual(identity.identity, "source")
        invalid = (
            {"identity": "", "revision": "v1", "digest": DIGEST_A},
            {"identity": "source", "revision": " ", "digest": DIGEST_A},
            {"identity": "source", "revision": "v1", "digest": "a" * 64},
            {"identity": "source", "revision": "v1", "digest": "sha256:" + "A" * 64},
            {"identity": "source", "revision": "v1", "digest": "sha256:" + "g" * 64},
        )
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                ArtifactIdentity(**arguments)

    def test_input_spec_blocks_content_and_group_contamination_across_splits(self) -> None:
        contaminated_sets = (
            (
                InputCase("cal", DIGEST_A, "calibration", "group-a"),
                InputCase("eval", DIGEST_A, "evaluation", "group-b"),
            ),
            (
                InputCase("cal", DIGEST_A, "calibration", "group-a"),
                InputCase("eval", DIGEST_B, "evaluation", "group-a"),
            ),
        )
        for cases in contaminated_sets:
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                input_spec(*cases)

    def test_input_spec_accepts_shared_split_and_rejects_duplicate_case_ids(self) -> None:
        same_split = input_spec(
            InputCase("dev-1", DIGEST_A, "development", "group-a"),
            InputCase("dev-2", DIGEST_A, "development", "group-a"),
        )
        self.assertEqual(len(same_split.cases), 2)
        with self.assertRaises(ValueError):
            input_spec(
                InputCase("same", DIGEST_A, "fixture", "group-a"),
                InputCase("same", DIGEST_B, "fixture", "group-b"),
            )

    def test_input_values_reject_unknown_split_bad_digest_and_nonpositive_length(self) -> None:
        with self.assertRaises(ValueError):
            InputCase("case", DIGEST_A, "holdout", "group")
        with self.assertRaises(ValueError):
            InputCase("case", "bad", "fixture", "group")
        with self.assertRaises(ValueError):
            replace(input_spec(), sequence_length=0)
        with self.assertRaises(ValueError):
            replace(input_spec(), masks_digest="bad")

    def test_operation_spec_accepts_scalar_and_zero_extent_but_rejects_bad_axes(self) -> None:
        self.assertEqual(OperationSpec("scalar", (), ()).shape, ())
        self.assertEqual(OperationSpec("empty", (0, 4), ("input", "feature")).shape, (0, 4))
        invalid = (
            ("op", (-1,), ("feature",)),
            ("op", (True,), ("feature",)),
            ("op", (2, 4), ("feature",)),
            ("op", (2, 4), ("feature", "feature")),
            ("op", tuple(1 for _ in range(17)), tuple(f"a{i}" for i in range(17))),
        )
        for operation_id, shape, axes in invalid:
            with self.subTest(shape=shape, axes=axes), self.assertRaises(ValueError):
                OperationSpec(operation_id, shape, axes)

    def test_randomization_and_resource_budgets_enforce_exact_integer_boundaries(self) -> None:
        randomization = RandomizationSpec(0, 1, "independent_draw")
        budget = ResourceBudget(1, 0.001, 1)
        self.assertEqual(randomization.master_seed, 0)
        self.assertEqual(budget.max_seconds, 0.001)

        invalid_randomization = ((-1, 1), (True, 1), (0, 0), (0, True))
        for seed, runs in invalid_randomization:
            with self.subTest(seed=seed, runs=runs), self.assertRaises(ValueError):
                RandomizationSpec(seed, runs)
        for arguments in ((0, 1, 1), (1, 0, 1), (1, 1, 0), (1.5, 1, 1), (1, math.inf, 1)):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                ResourceBudget(*arguments)

    def test_cost_scope_requires_disjoint_unique_components_and_positive_conditions(self) -> None:
        invalid_changes = (
            {"included_components": ()},
            {"included_components": ("execution", "execution")},
            {"excluded_components": ("model load", "model load")},
            {"included_components": ("execution",), "excluded_components": ("execution",)},
            {"batch_size": 0},
            {"concurrency": True},
            {"sequence_length": 0},
            {"boundary": " "},
        )
        for change in invalid_changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(cost_scope(), **change)

        with self.assertRaises(ValueError):
            replace(cost_scope(), included_components={"execution"})

    def test_workload_rejects_untyped_nested_fields(self) -> None:
        typed = workload()
        fields = (
            "model_config",
            "inputs",
            "reference",
            "candidate",
            "contract",
            "randomization",
            "resources",
            "cost_scope",
            "checkpoint",
        )
        for field_name in fields:
            with self.subTest(field=field_name), self.assertRaises(ValueError):
                replace(typed, **{field_name: {"looks": "plausible"}})
        with self.assertRaises(ValueError):
            replace(typed, sources=("source",))
        with self.assertRaises(ValueError):
            replace(typed, operations=({"operation_id": "activation"},))

    def test_workload_validates_supported_modes_identities_and_nonempty_collections(self) -> None:
        base = workload()
        changes = (
            {"sources": ()},
            {"operations": ()},
            {"license_refs": ()},
            {"license_refs": (" ",)},
            {"dtype": "float16"},
            {"controls": ("samples", "samples")},
            {"controls": ("adaptive_stopping",)},
            {"retention": "cloud"},
            {"schema_version": 2},
            {"precision": {"nan": math.nan}},
            {"precision": {1: "coerced key"}},
        )
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(base, **change)

    def test_workload_defensively_freezes_nested_sequences_and_metadata(self) -> None:
        sources = [artifact("source")]
        operations = [OperationSpec("activation", (1,), ("feature",))]
        precision = {"nested": ["float32"]}
        controls = ["samples"]
        spec = replace(
            workload(),
            sources=sources,
            operations=operations,
            precision=precision,
            controls=controls,
        )
        sources.append(artifact("later"))
        operations.clear()
        precision["nested"].append("changed")
        controls.append("warmup")
        self.assertEqual(len(spec.sources), 1)
        self.assertEqual(len(spec.operations), 1)
        self.assertEqual(spec.precision["nested"], ["float32"])
        self.assertEqual(spec.controls, ("samples",))
        with self.assertRaises(TypeError):
            spec.precision["new"] = "value"  # type: ignore[index]
        with self.assertRaises(FrozenInstanceError):
            spec.description = "changed"  # type: ignore[misc]

    def test_workload_to_dict_is_detached(self) -> None:
        first = workload()
        payload = first.to_dict()
        payload["precision"]["accumulator"] = "changed"
        payload["sources"].append({"identity": "injected"})
        self.assertEqual(first.precision["accumulator"], "float32")
        self.assertEqual(len(first.sources), 1)


class ObservationContractTests(unittest.TestCase):
    def test_array_ref_rejects_unsafe_paths_and_invalid_metadata(self) -> None:
        safe = ArrayRef("arrays/value.npy", DIGEST_A, 32, "float32", (2, 4), ("input", "feature"))
        self.assertEqual(safe.path, "arrays/value.npy")
        unsafe_paths = (
            "../value.npy",
            "arrays/../value.npy",
            "/absolute/value.npy",
            "C:/value.npy",
            "\\\\server\\share\\value.npy",
            "arrays\\value.npy",
            "arrays//value.npy",
            "./value.npy",
            "arrays/:value.npy",
        )
        for path in unsafe_paths:
            with self.subTest(path=path), self.assertRaises(ValueError):
                replace(safe, path=path)
        for change in (
            {"byte_length": 0},
            {"byte_length": True},
            {"digest": "bad"},
            {"dtype": "object"},
            {"shape": (-1,)},
            {"axes": ("input",)},
            {"encoding": "pickle"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(safe, **change)

    def test_inline_observation_requires_exactly_one_matching_payload(self) -> None:
        observation = Observation(
            "activation",
            "activation",
            "case-1",
            "run-1",
            "float64",
            (2,),
            ("feature",),
            values=(0, 1),
        )
        self.assertEqual(observation.values, (0.0, 1.0))
        with self.assertRaises(ValueError):
            replace(observation, values=None)
        with self.assertRaises(ValueError):
            replace(
                observation,
                array=ArrayRef("arrays/value.npy", DIGEST_A, 16, "float64", (2,), ("feature",)),
            )
        with self.assertRaises(ValueError):
            replace(observation, values=(0.0,))

    def test_inline_observation_handles_scalar_and_zero_extent_shapes(self) -> None:
        scalar = Observation("value", "op", "ctx", "run", "int8", (), (), values=(7,))
        empty = Observation("value", "op", "ctx", "run", "bool", (2, 0), ("row", "column"), values=())
        self.assertEqual(scalar.values, (7,))
        self.assertEqual(empty.values, ())

    def test_inline_observation_caps_element_count(self) -> None:
        values = tuple(0 for _ in range(4096))
        accepted = Observation("value", "op", "ctx", "run", "int8", (4096,), ("item",), values=values)
        self.assertEqual(len(accepted.values or ()), 4096)
        with self.assertRaises(ValueError):
            replace(accepted, shape=(4097,), values=values + (0,))

    def test_integer_observation_rejects_booleans_floats_and_out_of_range_values(self) -> None:
        for dtype, value in (("int8", -129), ("int8", 128), ("int16", True), ("int32", 1.0), ("int64", "1")):
            with self.subTest(dtype=dtype, value=value), self.assertRaises(ValueError):
                Observation("value", "op", "ctx", "run", dtype, (1,), ("item",), values=(value,))

    def test_float_observation_normalizes_to_declared_dtype_and_rejects_overflow(self) -> None:
        float32_value = Observation("value", "op", "ctx", "run", "float32", (1,), ("item",), values=(1 / 10,))
        self.assertEqual(float32_value.values, (0.10000000149011612,))
        normalized_zero = Observation("value", "op", "ctx", "run", "float64", (1,), ("item",), values=(-0.0,))
        self.assertEqual(math.copysign(1.0, normalized_zero.values[0]), 1.0)  # type: ignore[index]
        for value in (True, "1.0", math.nan, math.inf, 1e100):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Observation("value", "op", "ctx", "run", "float32", (1,), ("item",), values=(value,))

    def test_referenced_observation_must_exactly_match_array_metadata(self) -> None:
        array = ArrayRef("arrays/value.npy", DIGEST_A, 16, "float32", (2,), ("feature",))
        observation = Observation(
            "activation", "activation", "case-1", "run-1", "float32", (2,), ("feature",), array=array
        )
        self.assertIs(observation.array, array)
        for change in (
            {"dtype": "float64"},
            {"shape": (1, 2), "axes": ("input", "feature")},
            {"axes": ("item",)},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(observation, **change)


class ExecutionAndPolicyContractTests(unittest.TestCase):
    def test_cost_records_keep_availability_provenance_and_units_consistent(self) -> None:
        measured = CostRecord("latency", "seconds", cost_scope(), "measured", "available", value=0.0)
        self.assertEqual(measured.value, 0.0)
        unknown = CostRecord(
            "energy",
            "joules",
            cost_scope(),
            "modeled",
            "unavailable",
            reason="No device energy interface",
        )
        self.assertIsNone(unknown.value)
        invalid = (
            {"quantity": "latency", "units": "joules"},
            {"quantity": "energy", "units": "seconds"},
            {"quantity": "sample_work", "units": "joules", "provenance": "measured"},
            {"availability": "available", "value": -1},
            {"availability": "available", "value": math.nan},
            {"availability": "unavailable", "value": 1, "reason": "unknown"},
            {"availability": "unavailable", "value": None, "reason": None},
            {"provenance": "estimated"},
        )
        for change in invalid:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(measured, **change)

    def test_planned_run_freezes_finite_json_settings(self) -> None:
        settings = {"samples": 32, "nested": ["fixed"]}
        run = PlannedRun("run-1", "case-1", "activation", "qualification", settings)
        settings["samples"] = 64
        settings["nested"].append("changed")
        self.assertEqual(run.settings["samples"], 32)
        self.assertEqual(run.settings["nested"], ["fixed"])
        with self.assertRaises(TypeError):
            run.settings["samples"] = 128  # type: ignore[index]
        with self.assertRaises(ValueError):
            replace(run, settings={"bad": math.nan})

    def test_run_plan_validates_references_uniqueness_schema_and_job_budget(self) -> None:
        spec = workload(resources=ResourceBudget(2, 30, 4096))
        first = PlannedRun("run-1", "case-1", "activation", "qualification", {"samples": 1})
        second = PlannedRun("run-2", "case-2", "activation", "qualification", {"samples": 1})
        plan = RunPlan(spec, (first, second))
        self.assertEqual(tuple(run.run_id for run in plan.runs), ("run-1", "run-2"))
        invalid_runs = (
            (),
            (first, first),
            (first, second, replace(second, run_id="run-3")),
            (replace(first, case_id="missing"),),
            (replace(first, operation_id="missing"),),
        )
        for runs in invalid_runs:
            with self.subTest(runs=runs), self.assertRaises(ValueError):
                RunPlan(spec, runs)
        with self.assertRaises(ValueError):
            RunPlan(spec, (first,), schema_version=2)
        with self.assertRaises(ValueError):
            RunPlan({"workload_id": spec.workload_id}, (first,))  # type: ignore[arg-type]

    def test_qualification_report_accepts_complete_passing_evidence(self) -> None:
        contract = acceptance_contract(exact_metric())
        report = QualificationReport(
            DIGEST_A,
            contract,
            "complete",
            "pass",
            (available_result(),),
            ("run-1",),
            ("run-1",),
        )
        self.assertEqual(report.qualification, "pass")

    def test_qualification_report_blocks_false_completion_and_false_pass(self) -> None:
        contract = acceptance_contract(exact_metric())
        passing = available_result()
        base = QualificationReport(
            DIGEST_A,
            contract,
            "complete",
            "pass",
            (passing,),
            ("run-1",),
            ("run-1",),
        )
        invalid_changes = (
            {"completed_run_ids": ()},
            {"execution": "complete", "completed_run_ids": ()},
            {"execution": "partial", "qualification": "pass", "completed_run_ids": ()},
            {"metrics": (replace(passing, outcome="inconclusive"),)},
            {
                "metrics": (
                    replace(
                        passing,
                        availability="unavailable",
                        estimate=None,
                        interval=None,
                        outcome=None,
                        reason="missing",
                        observed_units=0,
                        unit_summaries=(),
                    ),
                )
            },
            {"expected_run_ids": ("run-1", "run-1")},
            {"completed_run_ids": ("unknown",)},
            {"schema_version": 2},
        )
        for change in invalid_changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(base, **change)

    def test_mandatory_failure_cannot_be_reported_pass_or_inconclusive(self) -> None:
        contract = acceptance_contract(exact_metric())
        failure = available_result(outcome="fail", estimate=0.2)
        for qualification in ("pass", "inconclusive"):
            with self.subTest(qualification=qualification), self.assertRaises(ValueError):
                QualificationReport(
                    DIGEST_A,
                    contract,
                    "complete",
                    qualification,
                    (failure,),
                    ("run-1",),
                    ("run-1",),
                )
        failed = QualificationReport(
            DIGEST_A,
            contract,
            "complete",
            "fail",
            (failure,),
            ("run-1",),
            ("run-1",),
        )
        self.assertEqual(failed.qualification, "fail")

    def test_invalid_and_unsupported_reports_require_reason(self) -> None:
        contract = acceptance_contract(exact_metric())
        for qualification in ("invalid", "unsupported"):
            with self.subTest(qualification=qualification), self.assertRaises(ValueError):
                QualificationReport(
                    DIGEST_A,
                    contract,
                    "error",
                    qualification,
                    (MetricResult("exact-error", "unavailable", reason="missing"),),
                    ("run-1",),
                    (),
                )

    def test_report_requires_exactly_the_contract_metric_ids(self) -> None:
        contract = acceptance_contract(exact_metric())
        with self.assertRaises(ValueError):
            QualificationReport(
                DIGEST_A,
                contract,
                "complete",
                "pass",
                (available_result("other"),),
                ("run-1",),
                ("run-1",),
            )

    def test_report_rejects_optional_pass_but_allows_descriptive_optional_evidence(self) -> None:
        contract = acceptance_contract(exact_metric(), bounded_metric("exploratory", mandatory=False))
        mandatory = available_result()
        descriptive = MetricResult(
            "exploratory",
            "available",
            estimate=0,
            interval=Bounds(-0.2, 0.2),
            outcome="inconclusive",
            reason="descriptive only",
            observed_units=4,
            planned_units=4,
            procedure="bounded-hoeffding-v1",
            alpha=0.05,
            unit_summaries=(-0.1, 0.1, -0.1, 0.1),
        )
        report = QualificationReport(
            DIGEST_A,
            contract,
            "complete",
            "pass",
            (mandatory, descriptive),
            ("run-1",),
            ("run-1",),
        )
        self.assertEqual(report.qualification, "pass")
        with self.assertRaises(ValueError):
            replace(report, metrics=(mandatory, replace(descriptive, outcome="pass")))

    def test_report_checks_result_planning_mode_alpha_and_declared_bounds(self) -> None:
        contract = acceptance_contract(exact_metric(), bounded_metric())
        exact = available_result()
        bounded = MetricResult(
            "mean-error",
            "available",
            estimate=0,
            interval=Bounds(-0.2, 0.2),
            outcome="inconclusive",
            observed_units=4,
            planned_units=4,
            procedure="bounded-hoeffding-v1",
            alpha=0.05,
            unit_summaries=(-0.1, 0.1, -0.1, 0.1),
        )
        base = QualificationReport(
            DIGEST_A,
            contract,
            "complete",
            "inconclusive",
            (exact, bounded),
            ("run-1",),
            ("run-1",),
        )
        invalid_metrics = (
            (replace(exact, outcome="inconclusive", planned_units=2), bounded),
            (replace(exact, procedure="bounded-hoeffding-v1"), bounded),
            (replace(exact, alpha=0.05), bounded),
            (replace(exact, interval=Bounds(0.0, 0.1)), bounded),
            (exact, replace(bounded, procedure="exact-v1")),
            (exact, replace(bounded, alpha=0.01)),
            (exact, replace(bounded, interval=Bounds(-3, 0.2))),
            (exact, replace(bounded, unit_summaries=(-3.0, 0.1, -0.1, 0.1))),
            (exact, replace(bounded, outcome="pass")),
        )
        for metrics in invalid_metrics:
            with self.subTest(metrics=metrics), self.assertRaises(ValueError):
                replace(base, metrics=metrics)

        unavailable = MetricResult(
            "mean-error",
            "unavailable",
            reason="no completed bounded units",
            planned_units=4,
            procedure="bounded-hoeffding-v1",
        )
        partial = replace(
            base,
            execution="partial",
            metrics=(exact, unavailable),
            completed_run_ids=(),
        )
        self.assertEqual(partial.qualification, "inconclusive")

        incomplete = MetricResult(
            "mean-error",
            "available",
            estimate=0,
            interval=Bounds(-0.05, 0.05),
            outcome="inconclusive",
            observed_units=2,
            planned_units=4,
            procedure="bounded-hoeffding-v1",
            alpha=0.05,
            unit_summaries=(-0.05, 0.05),
        )
        partial_with_evidence = replace(partial, metrics=(exact, incomplete))
        self.assertEqual(partial_with_evidence.metrics[1].observed_units, 2)

        range_limited_exact = replace(
            exact_metric(),
            bounds=Bounds(-1, 1),
            acceptance=Acceptance("upper", upper=100),
        )
        with self.assertRaises(ValueError):
            QualificationReport(
                DIGEST_A,
                acceptance_contract(range_limited_exact),
                "complete",
                "pass",
                (available_result(estimate=2),),
                ("run-1",),
                ("run-1",),
            )

    def test_sampling_settings_enforce_integer_boundaries(self) -> None:
        settings = SamplingSettings(1, warmup=0, thinning=1)
        self.assertEqual((settings.samples, settings.warmup, settings.thinning), (1, 0, 1))
        for arguments in ((0, 0, 1), (1, -1, 1), (1, 0, 0), (True, 0, 1), (1, 0.0, 1)):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                SamplingSettings(*arguments)

    def test_policy_validates_lifecycle_digests_and_typed_settings(self) -> None:
        policy = Policy(
            policy_id="policy-v1",
            workload_digest=DIGEST_A,
            operation_map_digest=DIGEST_B,
            profile=artifact("profile", DIGEST_A),
            backend=artifact("backend", DIGEST_B),
            input_envelope=artifact("input-envelope", DIGEST_C),
            default=SamplingSettings(32),
            groups={"attention": SamplingSettings(64, warmup=4, thinning=2)},
            fallback=SamplingSettings(128),
            calibration_digest=DIGEST_A,
            frozen_evaluation_digest=DIGEST_B,
            objective=CostRecord("sample_work", "samples", cost_scope(), "modeled", "available", value=64),
        )
        self.assertEqual(policy.qualification, "unqualified")
        with self.assertRaises(TypeError):
            policy.groups["mlp"] = SamplingSettings(16)  # type: ignore[index]

        invalid_changes = (
            {"workload_digest": "bad"},
            {"operation_map_digest": "bad"},
            {"calibration_digest": "bad"},
            {"frozen_evaluation_digest": "bad"},
            {"profile": "profile"},
            {"default": {"samples": 32}},
            {"groups": {"": SamplingSettings(1)}},
            {"groups": {"group": {"samples": 1}}},
            {"qualification": "unqualified", "validation_bundle": DIGEST_C},
            {"qualification": "pass", "validation_bundle": None},
            {"qualification": "unknown"},
            {"schema_version": 2},
        )
        for change in invalid_changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(policy, **change)

        qualified = replace(policy, qualification="pass", validation_bundle=DIGEST_C)
        self.assertEqual(qualified.validation_bundle, DIGEST_C)


if __name__ == "__main__":
    unittest.main()
