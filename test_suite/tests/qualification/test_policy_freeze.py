"""Closed policy codecs and exact compatibility resolution."""

from pathlib import Path
import tempfile
import unittest

from gibbsiq.qualification.engine import UnsupportedCapabilityError
from test_suite.tests.qualification.search_fixtures import search_plan, table_evaluator


class PolicyFreezeTests(unittest.TestCase):
    def test_pass_policy_round_trips_and_resolves_only_exact_envelope(self):
        from gibbsiq.qualification.policy_search import (
            policy_from_dict,
            policy_to_dict,
            resolve_policy,
            run_search,
        )

        plan = search_plan()
        with tempfile.TemporaryDirectory() as directory:
            summary = run_search(
                plan,
                evaluator=table_evaluator({(8,): 0.01, (16,): 0.2, (32,): 0.02}),
                destination=Path(directory) / "search",
            )
        policy = policy_from_dict(summary["policy"])
        self.assertEqual(policy_to_dict(policy), summary["policy"])
        candidate = resolve_policy(
            policy,
            workload_digest=policy.workload_digest,
            operation_map_digest=policy.operation_map_digest,
            profile=policy.profile,
            backend=policy.backend,
            input_envelope=policy.input_envelope,
        )
        self.assertEqual(candidate.default_samples, 8)
        with self.assertRaises(UnsupportedCapabilityError):
            resolve_policy(
                policy,
                workload_digest=plan.templates["calibration"].workload.semantic_digest(),
                operation_map_digest=policy.operation_map_digest,
                profile=policy.profile,
                backend=policy.backend,
                input_envelope=policy.input_envelope,
            )

    def test_policy_codec_rejects_unknown_fields(self):
        from gibbsiq.qualification.policy_search import policy_from_dict

        with self.assertRaises(ValueError):
            policy_from_dict({"policy_id": "x", "unexpected": True})


if __name__ == "__main__":
    unittest.main()
