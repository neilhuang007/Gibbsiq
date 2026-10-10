"""Frozen complete-corpus plans and a real, bounded model evidence bundle."""

from __future__ import annotations

import importlib.util
import os
import pickle
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from gibbsiq.qualification.artifacts import (
    AttemptRecord,
    BundleSnapshot,
    BundleWriter,
    inspect_bundle,
    plan_from_dict,
    record_to_dict,
)
from gibbsiq.qualification.contracts import CostRecord, Observation, PlannedRun, RunPlan
from gibbsiq.qualification.engine import derive_randomization
from gibbsiq.qualification.model_evaluation import (
    CorpusSplit,
    TokenDocument,
    combine_losses,
    language_loss,
    tiny_split_manifest,
)


def _scalar_observations(run: PlannedRun, values: Mapping[str, float | int]) -> tuple[Observation, ...]:
    """Package test-chosen scalars in the declared measurement envelope."""
    return tuple(
        Observation(
            name,
            run.operation_id,
            run.case_id,
            run.run_id,
            "int64" if name in {"valid_tokens", "modeled_spin_draws"} else "float64",
            (),
            (),
            (value,),
        )
        for name, value in values.items()
    )


class ModelPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend

        self.backend = TinyModelBackend(tiny_split_manifest().evaluation)

    def test_pure_plan_has_one_complete_corpus_case_and_frozen_scalar_bindings(self) -> None:
        plan = self.backend.plan(runs=2, samples=8, max_seconds=120)
        self.assertEqual(plan, plan_from_dict(record_to_dict(plan)))
        self.assertEqual(plan.workload.inputs.cases[0].split, "evaluation")
        self.assertEqual(
            plan.workload.inputs.cases[0].content_digest, self.backend.documents.semantic_digest()
        )
        self.assertEqual(len(plan.workload.operations), 1)
        self.assertEqual(plan.workload.operations[0].operation_id, "complete-model-evaluation")
        self.assertEqual(plan.workload.operations[0].shape, ())
        self.assertEqual(plan.workload.randomization.independent_runs, 2)
        self.assertEqual(plan.workload.contract.metrics[0].metric_id, "capped_nll_degradation")
        self.assertEqual(plan.workload.contract.metrics[0].bounds.lower, -8.0)
        self.assertEqual(plan.workload.contract.metrics[0].bounds.upper, 8.0)
        self.assertEqual(plan.workload.contract.alpha_total, 0.05)
        self.assertEqual(plan.workload.resources.max_bytes, 16 * 1024 * 1024)
        activation = plan.workload.contract.metrics[2]
        self.assertEqual(activation.metric_id, "activation_mse/blocks.0.attn.qkv_proj")
        self.assertFalse(activation.mandatory)
        self.assertEqual((activation.bounds.lower, activation.bounds.upper), (0.0, 4.0))
        self.assertEqual(plan.metric_bindings[2].observation_name, activation.metric_id)
        self.assertEqual(plan.metric_bindings[0].reference_value, 0.0)
        self.assertEqual(tuple(run.settings["samples"] for run in plan.runs), (8, 8))
        self.assertEqual(plan.workload.precision["corpus"], self.backend.documents.to_dict())
        self.assertIn("profile_id", plan.workload.precision)
        self.assertIn("operation_groups", plan.workload.precision)
        self.assertIn("metric_version", plan.workload.precision)
        self.assertIn("rng_recipe", plan.workload.precision)
        self.assertEqual(self.backend.capabilities().backend_id, plan.workload.candidate.identity)
        self.backend.validate_plan(plan)

    def test_controls_are_group_complete_and_reject_unknown_or_inconsistent_paths(self) -> None:
        names = tuple(self.backend.operation_groups["attention"])
        valid = self.backend.plan(runs=1, samples=8, operation_samples={names[0]: 16, names[1]: 16})
        self.assertEqual(valid.runs[0].settings["grouped_samples"], {"attention": 16})
        self.backend.validate_plan(valid)
        for overrides in (
            {names[0]: 16},
            {names[0]: 16, names[1]: 32},
            {"not-an-operation": 16},
            {names[0]: True, names[1]: True},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.backend.plan(runs=1, operation_samples=overrides)
        with self.assertRaises(ValueError):
            self.backend.plan(runs=1, samples=4097)
        with self.assertRaises(ValueError):
            self.backend.plan(runs=1, max_seconds=181)
        bounded = self.backend.plan(runs=1, max_bytes=1 * 1024 * 1024)
        self.backend.validate_plan(bounded)
        self.assertEqual(bounded.workload.resources.max_bytes, 1 * 1024 * 1024)
        for max_bytes in (65_535, 16 * 1024 * 1024 + 1, True, 1.0):
            with self.subTest(max_bytes=max_bytes), self.assertRaises(ValueError):
                self.backend.plan(runs=1, max_bytes=max_bytes)
        for alpha in (0.0, -0.1, 1.1, True, float("nan")):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                self.backend.plan(runs=1, alpha=alpha)

    def test_validate_plan_rejects_foreign_controls_and_run_changes(self) -> None:
        plan = self.backend.plan(runs=2, samples=8)
        changed = replace(plan.runs[0], settings={"samples": 8, "warmup": 1})
        with self.assertRaises(ValueError):
            self.backend.validate_plan(
                RunPlan(plan.workload, (changed, *plan.runs[1:]), metric_bindings=plan.metric_bindings)
            )
        changed = PlannedRun(
            "replacement", plan.runs[0].case_id, plan.runs[0].operation_id, "evaluation", {"samples": 8}
        )
        with self.assertRaises(ValueError):
            self.backend.validate_plan(RunPlan(plan.workload, (changed, *plan.runs[1:]), metric_bindings=()))
        changed = replace(plan.runs[0], settings={"samples": 8, "grouped_samples": {"alien": 16}})
        with self.assertRaises(ValueError):
            self.backend.validate_plan(RunPlan(plan.workload, (changed, *plan.runs[1:]), metric_bindings=()))

    def test_document_streams_depend_on_both_run_and_document(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import document_randomization

        plan = self.backend.plan(runs=2, samples=8)
        first, second = (derive_randomization(plan, run) for run in plan.runs)
        first_a = document_randomization(first, "evaluation-1")
        first_b = document_randomization(first, "evaluation-2")
        second_a = document_randomization(second, "evaluation-1")
        self.assertEqual(first_a, document_randomization(first, "evaluation-1"))
        self.assertEqual(len({first_a.digest, first_b.digest, second_a.digest}), 3)
        self.assertEqual(len(first_a.words), 8)

    def test_cumulative_selected_trace_is_preflighted_without_loading_model(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
        from gibbsiq.qualification.adapters.z1t import TinyZ1TConfig

        config = TinyZ1TConfig(vocab=256, sequence=64, n_layers=4, n_embed=64)
        names = tuple(
            f"blocks.{layer}.{site}"
            for layer in range(4)
            for site in ("attn.qkv_proj", "attn.out_proj", "mlp.proj1", "mlp.proj2")
        )
        corpus = CorpusSplit("evaluation", (TokenDocument("large", "large-group", tuple(range(65))),))
        with self.assertRaisesRegex(ValueError, "cumulative 1 MiB"):
            TinyModelBackend(corpus, config=config, observed_operations=names)


@unittest.skipUnless(importlib.util.find_spec("z1t") is not None, "pinned Z1T integration is unavailable")
class RealModelBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import numpy as np

        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend

        cls.np = np
        cls.backend = TinyModelBackend(tiny_split_manifest().evaluation)
        cls.plan = cls.backend.plan(
            runs=2, samples=8, alpha=0.025, max_seconds=120, max_bytes=1 * 1024 * 1024
        )
        cls.backend.validate_plan(cls.plan)
        cls.backend.prepare(cls.plan.workload)

    def test_reference_matches_independent_full_head_and_shifted_losses(self) -> None:
        direct = []
        for document in self.backend.documents.documents:
            logits = self.np.asarray(self.backend.numerical.forward(document.inputs).logits)
            self.assertEqual(logits.shape, (len(document.targets), self.backend.config.vocab))
            direct.append(
                language_loss(logits.tolist(), document.targets, mask=document.mask, cap=self.backend.cap)
            )
        expected = combine_losses(tuple(direct))
        self.assertEqual(expected.valid_tokens, 5)
        self.assertEqual(self.backend.numerical.operations, self.backend.operations)
        self.assertIsNotNone(self.backend.parameter_identity)
        self.assertIsNotNone(self.backend.operation_map_identity)
        self.assertAlmostEqual(self.backend.numerical_loss.nll, expected.nll, places=12)
        self.assertAlmostEqual(self.backend.numerical_loss.capped_nll, expected.capped_nll, places=12)

    def test_executed_scalars_match_independent_document_recalculation(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import document_randomization
        from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

        run = self.plan.runs[0]
        parent = derive_randomization(self.plan, run)
        actual = self.backend.execute(run, parent)
        observed = {item.name: item.values[0] for item in actual.observations}
        wrapper = IdealTanhModel(self.backend.numerical, samples=8)
        selected = self.backend.observed_operations[0]
        direct_losses = []
        squared_error = 0.0
        elements = 0
        for document in self.backend.documents.documents:
            direct = wrapper.forward(
                document.inputs,
                document_randomization(parent, document.document_id),
                observe=(selected,),
                retention="trace",
            )
            logits = self.np.asarray(direct.logits)
            direct_losses.append(
                language_loss(logits.tolist(), document.targets, mask=document.mask, cap=self.backend.cap)
            )
            capture = direct.captures[selected]
            field = self.np.asarray(capture.field.values, dtype=self.np.float64)
            output = self.np.asarray(capture.output.values, dtype=self.np.float64)
            difference = output - self.np.tanh(field)
            squared_error += float(self.np.sum(difference * difference, dtype=self.np.float64))
            elements += output.size
        direct_loss = combine_losses(tuple(direct_losses))
        self.assertEqual(direct_loss.valid_tokens, 5)
        self.assertAlmostEqual(observed["raw_nll"], direct_loss.nll, places=12)
        self.assertAlmostEqual(observed["capped_nll"], direct_loss.capped_nll, places=12)
        self.assertAlmostEqual(
            observed["capped_nll_degradation"],
            direct_loss.capped_nll - self.backend.numerical_loss.capped_nll,
            places=12,
        )
        self.assertAlmostEqual(observed[f"activation_mse/{selected}"], squared_error / elements, places=12)
        expected_work = sum(
            len(document.inputs) * operation.output_features * 8
            for document in self.backend.documents.documents
            for operation in self.backend.operations
        )
        self.assertEqual(observed["modeled_spin_draws"], expected_work)

    def test_execution_preserves_a_valid_small_cap_and_cost_scope(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend

        backend = TinyModelBackend(self.backend.documents, cap=0.01, observed_operations=())
        plan = backend.plan(runs=1, samples=8, margin=0.005)
        backend.validate_plan(plan)
        backend.prepare(plan.workload)
        run = plan.runs[0]
        result = backend.execute(run, derive_randomization(plan, run))
        observed = {item.name: item.values[0] for item in result.observations}
        self.assertEqual(observed["capped_nll"], 0.01)
        self.assertEqual(observed["numerical_capped_nll"], 0.01)
        self.assertEqual(observed["capped_nll_degradation"], 0.0)
        self.assertEqual(observed["valid_tokens"], 5)
        self.assertTrue(all(cost.scope == plan.workload.cost_scope for cost in result.costs))
        self.assertGreater(observed["raw_nll"], observed["capped_nll"])

    def test_prepared_backend_pickles_without_numerical_state_and_replays(self) -> None:
        restored = pickle.loads(pickle.dumps(self.backend))
        self.assertIsNone(restored._numerical)
        self.assertIsNone(restored._numerical_loss)
        run = self.plan.runs[0]
        stream = derive_randomization(self.plan, run)
        first = self.backend.execute(run, stream)
        repeated = self.backend.execute(run, stream)
        self.assertEqual(first.observations, repeated.observations)
        self.assertEqual(
            next(item.values[0] for item in first.observations if item.name == "valid_tokens"), 5
        )
        names = {item.name for item in first.observations}
        self.assertIn("activation_mse/blocks.0.attn.qkv_proj", names)
        self.assertIn("modeled_spin_draws", names)
        self.assertIn("numerical_capped_nll", names)
        self.assertIn("raw_nll", names)
        self.assertIn("capped_nll_degradation", names)
        costs = {cost.quantity: cost for cost in first.costs}
        self.assertEqual(costs["sample_work"].provenance, "modeled")
        self.assertEqual(costs["latency"].provenance, "measured")
        self.assertGreater(costs["latency"].value, 0)
        self.assertEqual(costs["energy"].availability, "unavailable")

    def test_new_run_changes_stochastic_evidence(self) -> None:
        first, second = self.plan.runs
        first_result = self.backend.execute(first, derive_randomization(self.plan, first))
        second_result = self.backend.execute(second, derive_randomization(self.plan, second))
        first_values = {item.name: item.values[0] for item in first_result.observations}
        second_values = {item.name: item.values[0] for item in second_result.observations}
        self.assertNotEqual(
            first_values["activation_mse/blocks.0.attn.qkv_proj"],
            second_values["activation_mse/blocks.0.attn.qkv_proj"],
        )

    def test_real_qualified_bundle_inspects_offline_with_every_attempt_preserved(self) -> None:
        from gibbsiq.qualification.workflow import qualify
        from gibbsiq.qualification.model_evaluation import render_model_summary, summarize_model_bundle

        with tempfile.TemporaryDirectory() as parent:
            destination = Path(parent) / "bundle"
            report = qualify(
                self.plan,
                backends={self.plan.workload.candidate.identity: self.backend},
                destination=destination,
            )
            self.assertEqual(report.execution, "complete")
            self.assertEqual(report.qualification, "inconclusive")
            self.assertEqual(report.contract.alpha_total, 0.025)
            self.assertEqual(report.metrics[0].alpha, 0.025)
            self.assertEqual(report.metrics[2].metric_id, "activation_mse/blocks.0.attn.qkv_proj")
            self.assertEqual(report.metrics[2].outcome, "inconclusive")
            snapshot = inspect_bundle(destination, verify=True)
            self.assertEqual(len(snapshot.attempts), 2)
            self.assertEqual(
                tuple(attempt.execution for attempt in snapshot.attempts), ("complete", "complete")
            )
            self.assertEqual(snapshot.report.qualification, report.qualification)
            summary = summarize_model_bundle(snapshot)
            self.assertEqual(summary["execution"], "complete")
            self.assertEqual(summary["qualification"], "inconclusive")
            self.assertEqual(summary["metrics"]["availability"], "available")
            self.assertEqual(summary["metrics"]["results"][0]["metric_id"], "capped_nll_degradation")
            self.assertEqual(summary["descriptive"]["observed_runs"], 2)
            self.assertEqual(summary["descriptive"]["missing_run_ids"], [])
            self.assertEqual([run["observations"]["valid_tokens"] for run in summary["per_run"]], [5, 5])
            self.assertTrue(all("cap_hit_rate" in run["observations"] for run in summary["per_run"]))
            self.assertTrue(
                all(
                    "activation_mse/blocks.0.attn.qkv_proj" in run["observations"]
                    for run in summary["per_run"]
                )
            )
            self.assertTrue(all(len(run["costs"]) == 3 for run in summary["per_run"]))
            self.assertNotIn("raw_nll_interval", summary["descriptive"])
            supplied = {**summary, "descriptive": {**summary["descriptive"], "mean_raw_nll": 123.456}}
            self.assertIn("123.456", render_model_summary(supplied))
            inspect_code = (
                "import sys; from gibbsiq.qualification.artifacts import inspect_bundle; "
                "s=inspect_bundle(sys.argv[1],verify=True); "
                "assert len(s.attempts)==2; assert 'jax' not in sys.modules; "
                "assert 'z1t' not in sys.modules"
            )
            environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}
            child = subprocess.run(
                [sys.executable, "-S", "-c", inspect_code, str(destination)],
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(child.returncode, 0, child.stderr)


class ModelSummaryTests(unittest.TestCase):
    def test_summary_accepts_frozen_calibration_split_and_reports_seven_targets(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
        from gibbsiq.qualification.model_evaluation import render_model_summary, summarize_model_bundle

        backend = TinyModelBackend(tiny_split_manifest().calibration, observed_operations=())
        plan = backend.plan(runs=1, samples=8)
        run = plan.runs[0]
        values = {
            "capped_nll_degradation": 0.0,
            "raw_nll": 2.0,
            "numerical_raw_nll": 2.0,
            "capped_nll": 2.0,
            "numerical_capped_nll": 2.0,
            "cap_hit_rate": 0.0,
            "valid_tokens": 7,
            "modeled_spin_draws": 100,
        }
        observations = _scalar_observations(run, values)
        attempt = AttemptRecord(
            run.run_id,
            "attempt-0",
            "complete",
            derive_randomization(plan, run).digest,
            observations,
        )
        snapshot = BundleSnapshot(plan, (attempt,), None, "complete", "inconclusive", "verified", None)
        summary = summarize_model_bundle(snapshot)
        self.assertEqual(summary["split"], "calibration")
        self.assertEqual(summary["per_run"][0]["observations"]["valid_tokens"], 7)
        self.assertIn("Split: calibration", render_model_summary(summary))
        wrong_record = record_to_dict(plan)
        wrong_record["workload"]["inputs"]["cases"][0]["split"] = "evaluation"
        with self.assertRaises(ValueError):
            summarize_model_bundle(replace(snapshot, plan=plan_from_dict(wrong_record)))

    def test_summary_rejects_impossible_loss_scalars_and_handles_large_finite_raw_nll(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
        from gibbsiq.qualification.model_evaluation import summarize_model_bundle

        backend = TinyModelBackend(tiny_split_manifest().evaluation)
        plan = backend.plan(runs=1, samples=8)
        selected_mse = f"activation_mse/{backend.observed_operations[0]}"
        valid = {
            "capped_nll_degradation": 1.0,
            "raw_nll": 3.0,
            "numerical_raw_nll": 2.0,
            "capped_nll": 3.0,
            "numerical_capped_nll": 2.0,
            "cap_hit_rate": 0.0,
            selected_mse: 0.125,
            "valid_tokens": 5,
            "modeled_spin_draws": 100,
        }

        def complete(source_plan: RunPlan, run: PlannedRun, values: dict[str, float | int]) -> AttemptRecord:
            return AttemptRecord(
                run.run_id,
                f"attempt-{run.run_id}",
                "complete",
                derive_randomization(source_plan, run).digest,
                _scalar_observations(run, values),
            )

        attempt = complete(plan, plan.runs[0], valid)
        snapshot = BundleSnapshot(plan, (attempt,), None, "complete", "inconclusive", "verified", None)
        self.assertEqual(summarize_model_bundle(snapshot)["descriptive"]["mean_raw_nll"], 3.0)
        impossible = {
            "raw_nll": -1.0,
            "numerical_raw_nll": -1.0,
            "capped_nll": 9.0,
            "numerical_capped_nll": 9.0,
            "cap_hit_rate": 1.1,
            selected_mse: 4.1,
            "valid_tokens": 4,
            "capped_nll_degradation": 0.5,
        }
        for name, bad in impossible.items():
            changed = tuple(
                replace(observation, values=(bad,)) if observation.name == name else observation
                for observation in attempt.observations
            )
            with self.subTest(name=name), self.assertRaises(ValueError):
                summarize_model_bundle(replace(snapshot, attempts=(replace(attempt, observations=changed),)))
        for name, bad in (("capped_nll", 4.0), ("numerical_capped_nll", 3.0)):
            changed = tuple(
                replace(observation, values=(bad,)) if observation.name == name else observation
                for observation in attempt.observations
            )
            with self.subTest(name=f"capped_exceeds_raw_{name}"), self.assertRaises(ValueError):
                summarize_model_bundle(replace(snapshot, attempts=(replace(attempt, observations=changed),)))

        two = backend.plan(runs=2, samples=8)
        large = {
            **valid,
            "raw_nll": 1e308,
            "numerical_raw_nll": 1e308,
            "capped_nll": 8.0,
            "numerical_capped_nll": 8.0,
            "capped_nll_degradation": 0.0,
        }
        large_attempts = tuple(complete(two, run, large) for run in two.runs)
        huge = summarize_model_bundle(
            BundleSnapshot(two, large_attempts, None, "complete", "inconclusive", "verified", None)
        )
        self.assertEqual(huge["descriptive"]["mean_raw_nll"], 1e308)
        self.assertIsNone(huge["descriptive"]["perplexity"])
        self.assertIn("overflows", huge["descriptive"]["perplexity_unavailable_reason"])

        three = backend.plan(runs=3, samples=8)
        maximal = {**large, "raw_nll": sys.float_info.max, "numerical_raw_nll": sys.float_info.max}
        maximal_attempts = tuple(complete(three, run, maximal) for run in three.runs)
        maximal_summary = summarize_model_bundle(
            BundleSnapshot(three, maximal_attempts, None, "complete", "inconclusive", "verified", None)
        )
        self.assertEqual(maximal_summary["descriptive"]["mean_raw_nll"], sys.float_info.max)
        self.assertIsNone(maximal_summary["descriptive"]["perplexity"])

    def test_example_freezes_three_bounded_evaluation_plans(self) -> None:
        from examples.qualification.qualify_tiny_z1t import frozen_plan, main

        plans = [frozen_plan(count) for count in (8, 32, 128)]
        self.assertEqual([len(plan.runs) for plan in plans], [16, 16, 16])
        self.assertEqual([plan.runs[0].settings["samples"] for plan in plans], [8, 32, 128])
        self.assertTrue(all(plan.workload.randomization.master_seed == 20260923 for plan in plans))
        self.assertTrue(all(plan.workload.precision["cap"] == 8.0 for plan in plans))
        self.assertTrue(all(plan.workload.contract.metrics[0].acceptance.upper == 0.1 for plan in plans))
        self.assertTrue(all(plan.workload.contract.alpha_total == 0.05 for plan in plans))
        self.assertEqual(sum(plan.workload.resources.max_seconds for plan in plans), 540)
        self.assertEqual(sum(plan.workload.resources.max_bytes for plan in plans), 48 * 1024 * 1024)
        self.assertEqual(sum(len(plan.runs) for plan in plans), 48)
        with self.assertRaises(ValueError):
            frozen_plan(64)
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "count-008").mkdir()
            with self.assertRaises(FileExistsError):
                main(("--count", "8", "--output-root", directory))

    def test_partial_bundle_preserves_failed_attempts_and_uses_only_completed_run(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
        from gibbsiq.qualification.model_evaluation import (
            render_model_summary,
            summarize_model_bundle,
        )

        backend = TinyModelBackend(tiny_split_manifest().evaluation)
        plan = backend.plan(runs=3, samples=8)
        first, second, third = plan.runs
        observed_name = f"activation_mse/{backend.observed_operations[0]}"

        values = {
            "capped_nll_degradation": 0.5,
            "raw_nll": 2.5,
            "numerical_raw_nll": 2.0,
            "capped_nll": 2.5,
            "numerical_capped_nll": 2.0,
            "cap_hit_rate": 0.0,
            observed_name: 0.125,
            "valid_tokens": 5,
            "modeled_spin_draws": 100,
        }
        costs = (
            CostRecord(
                "latency",
                "seconds",
                plan.workload.cost_scope,
                "measured",
                "available",
                1.25,
                method="test-clock",
            ),
            CostRecord(
                "energy",
                "joules",
                plan.workload.cost_scope,
                "modeled",
                "unavailable",
                reason="not measured",
                method="unknown",
            ),
        )
        stream_first = derive_randomization(plan, first).digest
        stream_second = derive_randomization(plan, second).digest
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "bundle"
            writer = BundleWriter.create(destination, plan)
            writer.append_attempt(
                AttemptRecord(first.run_id, "attempt-1", "error", stream_first, reason="worker interrupted")
            )
            writer.append_attempt(
                AttemptRecord(
                    first.run_id,
                    "attempt-2",
                    "complete",
                    stream_first,
                    _scalar_observations(first, values),
                    costs,
                    retry_of="attempt-1",
                )
            )
            writer.append_attempt(
                AttemptRecord(second.run_id, "attempt-3", "error", stream_second, reason="device unavailable")
            )
            writer.finish(execution="partial")
            summary = summarize_model_bundle(inspect_bundle(destination, verify=True))

        self.assertEqual(summary["schema"], "tiny-model-summary-v1")
        self.assertEqual((summary["execution"], summary["qualification"]), ("partial", "inconclusive"))
        self.assertEqual(summary["profile_id"], "ideal-tanh-iid-v1")
        self.assertEqual(summary["representation_relation"], "R=N by ideal profile")
        self.assertEqual([item["execution"] for item in summary["attempts"]], ["error", "complete", "error"])
        self.assertEqual(
            [item["reason"] for item in summary["attempts"]],
            ["worker interrupted", None, "device unavailable"],
        )
        self.assertEqual(len(summary["per_run"]), 1)
        self.assertEqual(summary["per_run"][0]["run_id"], first.run_id)
        self.assertEqual(summary["per_run"][0]["observations"], values)
        self.assertEqual(summary["per_run"][0]["costs"][0]["value"], 1.25)
        self.assertEqual(summary["per_run"][0]["costs"][1]["availability"], "unavailable")
        self.assertIsNone(summary["per_run"][0]["costs"][1]["value"])
        self.assertEqual(summary["descriptive"]["observed_runs"], 1)
        self.assertEqual(summary["descriptive"]["missing_run_ids"], [second.run_id, third.run_id])
        self.assertEqual(summary["descriptive"]["mean_raw_nll"], 2.5)
        self.assertEqual(summary["descriptive"]["mean_capped_nll"], 2.5)
        self.assertAlmostEqual(summary["descriptive"]["perplexity"], 12.182493960703473)
        self.assertNotIn("raw_nll_interval", summary["descriptive"])
        self.assertEqual(summary["metrics"]["availability"], "unavailable")
        self.assertEqual(summary["observer_overhead"]["status"], "unavailable")
        self.assertIn("not measured separately", summary["observer_overhead"]["reason"])
        self.assertIn("selected activation traces", summary["observer_overhead"]["timing_scope"])
        self.assertIn("loss processing", summary["observer_overhead"]["timing_scope"])
        markdown = render_model_summary(summary)
        self.assertIn("partial", markdown)
        self.assertIn("1/3", markdown)
        self.assertIn("device unavailable", markdown)
        self.assertIn(observed_name, markdown)
        self.assertIn("Physical energy", markdown)
        self.assertIn("Observer overhead: unavailable", markdown)
        self.assertIn("not measured separately", markdown)


if __name__ == "__main__":
    unittest.main()
