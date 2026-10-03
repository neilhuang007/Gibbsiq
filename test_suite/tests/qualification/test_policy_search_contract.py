"""Planned S08 coordinator behavioral tests; restore before search implementation."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from gibbsiq.qualification.contracts import AcceptanceContract
from gibbsiq.qualification.artifacts import inspect_bundle, parse_json
from test_suite.tests.qualification.policy_fixtures import execute_toy, search_plan, templates


def counts(candidate, groups=("attention", "mlp")):
    overrides = dict(candidate.group_samples)
    return tuple(overrides.get(group, candidate.default_samples) for group in groups)


class EnumerationTests(unittest.TestCase):
    def test_stable_grid_contains_baseline_once_and_deduplicates_uniforms(self):
        from gibbsiq.qualification.policy_search import SearchSpace, enumerate_candidates

        space = SearchSpace(counts=(16, 8), baseline=32, groups=("attention", "mlp"))
        candidates = enumerate_candidates(space)
        self.assertEqual(
            [counts(item) for item in candidates],
            [
                (8, 8),
                (16, 16),
                (32, 32),
                (8, 16),
                (8, 32),
                (16, 8),
                (16, 32),
                (32, 8),
                (32, 16),
            ],
        )
        self.assertTrue(all(not item.group_samples for item in candidates[:3]))
        self.assertEqual(candidates, enumerate_candidates(space))

    def test_oversized_grid_and_invalid_counts_are_rejected_before_execution(self):
        from gibbsiq.qualification.policy_search import SearchSpace, enumerate_candidates

        for values in ((True, 8), (0, 8), (8, 8), (8, 4097)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                enumerate_candidates(SearchSpace(counts=values, baseline=32))
        with self.assertRaises(ValueError):
            enumerate_candidates(
                SearchSpace(counts=(8, 16, 32), baseline=32, groups=("attention", "mlp"), max_candidates=8)
            )

    def test_budget_and_global_only_capability_refuse_grouped_search(self):
        with self.assertRaises(ValueError):
            search_plan(groups=("attention", "mlp"), max_jobs=12)
        with self.assertRaises(ValueError):
            search_plan(groups=("attention", "mlp"), max_bytes=2 * 1024 * 1024)
        with self.assertRaises(ValueError):
            search_plan(groups=("attention", "mlp"), templates=templates(grouped=False))

    def test_phase_templates_cannot_change_model_or_quality_margin(self):
        source = templates()
        development = source["development"]
        changed_metric = replace(
            development.workload.contract.metrics[0],
            acceptance=replace(development.workload.contract.metrics[0].acceptance, upper=0.2),
        )
        source["development"] = replace(
            development,
            workload=replace(development.workload, contract=AcceptanceContract((changed_metric,))),
        )
        with self.assertRaises(ValueError):
            search_plan(templates=source)

    def test_noisy_measured_objective_needs_a_separate_selection_procedure(self):
        plan = search_plan()
        with self.assertRaises(ValueError):
            search_plan(objective=replace(plan.objective, provenance="measured"))

    def test_search_plan_codec_retains_phase_data_and_rejects_unknown_fields(self):
        from gibbsiq.qualification.policy_search import SearchPlan

        plan = search_plan(groups=("attention", "mlp"))
        encoded = plan.to_dict()
        decoded = SearchPlan.from_dict(encoded)
        self.assertEqual(decoded.to_dict(), encoded)
        self.assertEqual(decoded.templates["evaluation"].workload.inputs.cases[0].split, "evaluation")
        with self.assertRaises(ValueError):
            SearchPlan.from_dict({**encoded, "loader": "arbitrary.module"})


class SearchBehaviorTests(unittest.TestCase):
    def run_search(self, mode, *, groups=(), plan_changes=None, before=None):
        from gibbsiq.qualification.policy_search import run_search

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name) / "experiment"
        calls = []

        def evaluator(candidate, phase, plan, destination):
            if before is not None:
                before(root, candidate, phase, plan)
            calls.append((phase, counts(candidate), plan))
            execute_toy(mode, phase, plan, destination)

        report = run_search(
            search_plan(groups=groups, **(plan_changes or {})), evaluator=evaluator, destination=root
        )
        return report, calls, root

    def test_nonmonotonic_uniform_search_evaluates_every_count_and_selects_middle(self):
        from gibbsiq.qualification.engine import UnsupportedCapabilityError
        from gibbsiq.qualification.policy_search import policy_from_dict, policy_to_dict, resolve_policy

        report, calls, root = self.run_search("nonmonotonic")
        self.assertEqual(
            [value for phase, value, _ in calls if phase == "calibration"], [(8, 8), (16, 16), (32, 32)]
        )
        self.assertEqual(report["selected"]["default_samples"], 16)
        self.assertEqual(report["lifecycle"], "qualified")
        self.assertTrue((root / "policy.json").is_file())
        for attempt in report["attempts"]:
            snapshot = inspect_bundle(root / attempt["bundle"], verify=True)
            self.assertEqual(attempt["qualification"], snapshot.report.qualification)
        policy = policy_from_dict(parse_json((root / "policy.json").read_text(encoding="utf-8")))
        self.assertEqual(policy_from_dict(policy_to_dict(policy)), policy)
        matching = dict(
            workload_digest=policy.workload_digest,
            operation_map_digest=policy.operation_map_digest,
            profile=policy.profile,
            backend=policy.backend,
            input_envelope=policy.input_envelope,
        )
        self.assertEqual(resolve_policy(policy, **matching).default_samples, 16)
        wrong_envelope = replace(policy.input_envelope, identity="different-corpus")
        with self.assertRaises(UnsupportedCapabilityError):
            resolve_policy(policy, **{**matching, "input_envelope": wrong_envelope})
        with self.assertRaises(ValueError):
            policy_from_dict({**policy_to_dict(policy), "loader": "arbitrary.module"})

    def test_lower_counts_that_do_not_reduce_declared_cost_are_rejected(self):
        report, calls, _ = self.run_search("maximum", groups=("attention", "mlp"))
        calibration = [value for phase, value, _ in calls if phase == "calibration"]
        self.assertEqual(calibration, [(8, 8), (16, 16), (32, 32), (16, 32), (32, 16)])
        self.assertEqual(report["selected"], {"default_samples": 32, "group_samples": []})

    def test_grouped_greedy_order_rechecks_full_loss_and_reuses_failed_neighbor(self):
        report, calls, _ = self.run_search("grouped", groups=("attention", "mlp"))
        calibration = [value for phase, value, _ in calls if phase == "calibration"]
        self.assertEqual(calibration, [(8, 8), (16, 16), (32, 32), (8, 16), (16, 8)])
        selected = report["selected"]
        self.assertEqual(dict(selected["group_samples"]), {"attention": 16, "mlp": 8})
        self.assertEqual(selected["default_samples"], 32)
        self.assertEqual(report["lifecycle"], "qualified")

    def test_held_out_failure_stays_failed_without_trying_more_final_candidates(self):
        frozen_bytes = []

        def before(root, candidate, phase, plan):
            if phase == "evaluation":
                freeze = root / "frozen-policy.json"
                self.assertTrue(freeze.is_file(), "selection must be frozen before evaluation")
                frozen_bytes.append(freeze.read_bytes())
                self.assertEqual(plan.workload.contract.alpha_total, 0.025)

        report, calls, root = self.run_search("overfit", before=before)
        self.assertEqual(report["lifecycle"], "failed_validation")
        self.assertEqual([value for phase, value, _ in calls if phase == "evaluation"], [(16, 16), (32, 32)])
        self.assertEqual(frozen_bytes[0], frozen_bytes[1])
        self.assertFalse((root / "policy.json").exists())
        self.assertEqual(calls[-2][0], "evaluation")
        self.assertEqual(calls[-1][0], "evaluation")

    def test_unavailable_cost_is_not_zero_cost_feasibility(self):
        report, calls, root = self.run_search("missing_cost")
        self.assertEqual(report["lifecycle"], "no_feasible_policy")
        self.assertTrue(all(phase == "calibration" for phase, _, _ in calls))
        self.assertTrue(all(not item["screening_eligible"] for item in report["attempts"]))
        self.assertFalse((root / "policy.json").exists())

    def test_search_inspection_is_static_and_preserves_stored_outcomes(self):
        from gibbsiq.qualification.policy_search import inspect_search

        report, _, root = self.run_search("overfit")
        self.assertEqual(inspect_search(root)["lifecycle"], report["lifecycle"])
        saved = parse_json((root / "search-report.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["attempts"], report["attempts"])

    def test_deadline_keeps_completed_evidence_and_stops_before_development(self):
        from gibbsiq.qualification.policy_search import run_search

        time_value = [0.0]
        calls = []

        def evaluator(candidate, phase, plan, destination):
            calls.append(phase)
            execute_toy("nonmonotonic", phase, plan, destination)
            time_value[0] = 121.0

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "experiment"
            report = run_search(
                search_plan(), evaluator=evaluator, destination=root, clock=lambda: time_value[0]
            )
            self.assertEqual(report["lifecycle"], "budget_exhausted")
            self.assertEqual(calls, ["calibration"])
            self.assertEqual(len(report["attempts"]), 1)
            self.assertEqual(inspect_bundle(root / report["attempts"][0]["bundle"]).execution, "complete")
            self.assertFalse((root / "policy.json").exists())

    def test_callback_cannot_substitute_a_more_favorable_acceptance_contract(self):
        from gibbsiq.qualification.policy_search import run_search

        def evaluator(candidate, phase, plan, destination):
            metric = plan.workload.contract.metrics[0]
            changed = replace(metric, acceptance=replace(metric.acceptance, upper=0.9))
            alternate = replace(
                plan, workload=replace(plan.workload, contract=AcceptanceContract((changed,)))
            )
            execute_toy("nonmonotonic", phase, alternate, destination)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "experiment"
            report = run_search(search_plan(), evaluator=evaluator, destination=root)
            self.assertEqual(report["lifecycle"], "invalid")
            self.assertFalse((root / "policy.json").exists())


if __name__ == "__main__":
    unittest.main()
