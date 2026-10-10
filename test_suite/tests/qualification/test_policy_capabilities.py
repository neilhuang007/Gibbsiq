"""Search preflight honors declared backend controls and resource bounds."""

from dataclasses import replace
import unittest

from gibbsiq.qualification.engine import UnsupportedCapabilityError
from test_suite.tests.qualification.search_fixtures import search_plan


class PolicyCapabilityTests(unittest.TestCase):
    def test_phase_templates_reject_changed_model_quality_and_fixed_control(self):
        from gibbsiq.qualification.artifacts import plan_from_dict, record_to_dict
        from gibbsiq.qualification.policy_search import SearchPlan

        original = search_plan()
        mutations = []
        model = record_to_dict(original.templates["development"])
        model["workload"]["model_config"]["digest"] = "sha256:" + "1" * 64
        mutations.append(model)
        quality = record_to_dict(original.templates["development"])
        quality["workload"]["contract"]["metrics"][0]["acceptance"]["upper"] = 0.09
        mutations.append(quality)
        fixed = record_to_dict(original.templates["development"])
        fixed["workload"]["controls"].append("warmup")
        fixed["runs"][0]["settings"]["warmup"] = 2
        mutations.append(fixed)
        for changed in mutations:
            templates = dict(original.templates)
            templates["development"] = plan_from_dict(changed)
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    SearchPlan(
                        original.space,
                        original.splits,
                        templates,
                        original.metric_id,
                        original.screening_margin,
                        original.objective,
                        original.profile,
                        original.operation_map_digest,
                        original.master_seed,
                        original.alpha_total,
                        original.max_jobs,
                        original.max_seconds,
                        original.max_bytes,
                    )

    def test_grouped_space_is_rejected_by_global_only_templates(self):
        from gibbsiq.qualification.artifacts import plan_from_dict, record_to_dict
        from gibbsiq.qualification.policy_search import SearchPlan

        plan = search_plan(groups=("a",))
        templates = {}
        for phase, template in plan.templates.items():
            value = record_to_dict(template)
            value["workload"]["controls"] = ["samples"]
            templates[phase] = plan_from_dict(value)
        with self.assertRaises(UnsupportedCapabilityError):
            SearchPlan(
                plan.space,
                plan.splits,
                templates,
                plan.metric_id,
                plan.screening_margin,
                plan.objective,
                plan.profile,
                plan.operation_map_digest,
                plan.master_seed,
                plan.alpha_total,
                plan.max_jobs,
                plan.max_seconds,
                plan.max_bytes,
            )

    def test_complete_grid_is_refused_without_truncation(self):
        from gibbsiq.qualification.policy_search import SearchSpace, enumerate_candidates

        with self.assertRaises(ValueError):
            enumerate_candidates(SearchSpace((8, 16, 32), 32, ("a", "b"), max_candidates=8))

    def test_preflight_reserves_minimum_bundle_bytes(self):
        plan = search_plan()
        with self.assertRaises(ValueError):
            replace(plan, max_bytes=2 * 1024 * 1024 + 6 * 65_535)


if __name__ == "__main__":
    unittest.main()
