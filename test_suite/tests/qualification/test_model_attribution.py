"""Conditional replay and complete-model interventions remain distinct evidence."""

from __future__ import annotations

import importlib.util
import math
import unittest

from gibbsiq.qualification.contracts import canonical_json
from gibbsiq.qualification.engine import derive_randomization
from gibbsiq.qualification.model_evaluation import language_loss, tiny_split_manifest


class HandCalculatedAttributionTests(unittest.TestCase):
    def test_tiny_local_error_can_change_loss_and_large_irrelevant_error_does_not(self) -> None:
        reference = language_loss([[0.0, 0.0]], [0])
        sensitive = language_loss([[1.0, 0.0]], [0])
        irrelevant = language_loss([[0.0, 0.0]], [0])
        self.assertAlmostEqual(reference.nll, math.log(2), places=14)
        self.assertAlmostEqual(sensitive.nll, math.log1p(math.exp(-1)), places=14)
        self.assertAlmostEqual(sensitive.nll - reference.nll, -0.3798854930417225, places=14)
        self.assertEqual(0.01**2, 0.0001)
        self.assertEqual(1.0**2, 1.0)
        self.assertEqual(irrelevant.nll, reference.nll)

    def test_explicit_boundary_substitution_mapping_keeps_irrelevant_coordinate_out_of_head(self) -> None:
        numerical_boundary = {"sensitive": 0.0, "irrelevant": 0.0}
        substitutes = {"sensitive": 0.01, "irrelevant": 1.0}

        def loss(selected: tuple[str, ...]):
            boundary = numerical_boundary | {name: substitutes[name] for name in selected}
            logits = [[100 * boundary["sensitive"] + 0 * boundary["irrelevant"], 0.0]]
            return language_loss(logits, [0])

        reference = loss(())
        sensitive = loss(("sensitive",))
        irrelevant = loss(("irrelevant",))
        self.assertAlmostEqual(reference.nll, math.log(2), places=14)
        self.assertAlmostEqual(sensitive.nll, math.log1p(math.exp(-1)), places=14)
        self.assertEqual(irrelevant.nll, reference.nll)


@unittest.skipUnless(importlib.util.find_spec("z1t") is not None, "pinned Z1T integration is unavailable")
class TinyModelAttributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import numpy as np

        from gibbsiq.qualification.adapters.model_workload import TinyModelBackend

        cls.np = np
        cls.document = tiny_split_manifest().evaluation.documents[0]
        cls.backend = TinyModelBackend(tiny_split_manifest().evaluation)
        cls.plan = cls.backend.plan(runs=1, samples=8, max_seconds=120)
        cls.backend.prepare(cls.plan.workload)
        cls.names = tuple(operation.operation_id for operation in cls.backend.numerical.operations[:2])
        cls.parent = derive_randomization(cls.plan, cls.plan.runs[0])

    def test_fixed_numerical_boundary_replay_has_independent_analytic_variance(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import diagnose_operations, document_randomization
        from gibbsiq.qualification.adapters.z1t_emulation import sample_iid_tanh

        result = diagnose_operations(
            self.backend.numerical,
            self.document,
            self.parent,
            samples=8,
            operations=self.names,
            joint=self.names,
        )
        self.assertEqual(result["schema"], "tiny-model-attribution-v1")
        self.assertEqual(result["profile_id"], "ideal-tanh-iid-v1")
        self.assertEqual(result["cap"], 8.0)
        self.assertEqual(result["representation_relation"], "R=N by ideal profile")
        self.assertEqual(result["document_id"], self.document.document_id)
        self.assertEqual(result["identities"]["source"], self.backend.numerical.source_identity)
        self.assertEqual(result["identities"]["parameters"], self.backend.numerical.parameter_identity)
        self.assertEqual(result["identities"]["operation_map"], self.backend.numerical.operation_map_identity)
        self.assertEqual(result["identities"]["document"], self.document.semantic_digest())
        self.assertEqual(result["randomization"]["parent"], self.parent.digest)
        self.assertEqual(
            result["randomization"]["document"],
            document_randomization(self.parent, self.document.document_id).digest,
        )
        self.assertEqual(result["randomization"]["coupling"], "common-document-stream-v1")
        numerical = self.backend.numerical.forward(
            self.document.inputs, observe=self.names, retention="trace"
        )
        direct_loss = language_loss(
            self.np.asarray(numerical.logits).tolist(),
            self.document.targets,
            mask=self.document.mask,
        )
        self.assertEqual(result["numerical"]["valid_tokens"], 3)
        self.assertAlmostEqual(result["numerical"]["raw_nll"], direct_loss.nll, places=12)
        for name in self.names:
            replay = result["replay"][name]
            self.assertEqual(replay["provenance"], "numerical-boundary-replay")
            self.assertEqual(replay["samples"], 8)
            capture = numerical.captures[name]
            field = self.np.asarray(capture.field.values, dtype=self.np.float64)
            reference = self.np.asarray(capture.output.values, dtype=self.np.float64)
            direct = sample_iid_tanh(
                capture.field.values,
                randomization=document_randomization(self.parent, self.document.document_id),
                operation_id=name,
                samples=8,
            )
            error = self.np.asarray(direct.mean, dtype=self.np.float64) - reference
            self.assertAlmostEqual(replay["mean_error"], float(self.np.mean(error)), places=12)
            self.assertAlmostEqual(replay["mse"], float(self.np.mean(error * error)), places=12)
            self.assertAlmostEqual(
                replay["analytic_conditional_mean_variance"],
                float(self.np.mean((1.0 - reference * reference) / 8)),
                places=12,
            )
            self.assertEqual(replay["elements"], field.size)
        self.assertLess(len(canonical_json(result)), 65_536)

    def test_one_at_a_time_and_joint_losses_use_actual_intervened_model(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import diagnose_operations, document_randomization
        from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

        result = diagnose_operations(
            self.backend.numerical,
            self.document,
            self.parent,
            samples=8,
            operations=self.names,
            joint=self.names,
        )
        wrapper = IdealTanhModel(self.backend.numerical, samples=8)
        stream = document_randomization(self.parent, self.document.document_id)
        for name in self.names:
            intervention = result["interventions"]["one_at_a_time"][name]
            self.assertEqual(intervention["provenance"], "actual-intervened-model")
            self.assertEqual(intervention["selected_operations"], [name])
            logits = self.np.asarray(
                wrapper.forward(self.document.inputs, stream, sampled_operations=(name,)).logits
            )
            direct = language_loss(logits.tolist(), self.document.targets, mask=self.document.mask)
            self.assertAlmostEqual(intervention["raw_nll"], direct.nll, places=12)
            self.assertAlmostEqual(intervention["capped_nll"], direct.capped_nll, places=12)
            self.assertEqual(intervention["valid_tokens"], 3)
        joint = result["interventions"]["joint"]
        self.assertEqual(joint["provenance"], "actual-intervened-model")
        self.assertEqual(joint["selected_operations"], list(self.names))
        logits = self.np.asarray(
            wrapper.forward(self.document.inputs, stream, sampled_operations=self.names).logits
        )
        direct_joint = language_loss(logits.tolist(), self.document.targets, mask=self.document.mask)
        self.assertAlmostEqual(joint["raw_nll"], direct_joint.nll, places=12)
        self.assertAlmostEqual(joint["capped_nll"], direct_joint.capped_nll, places=12)
        summed_individual = sum(
            result["interventions"]["one_at_a_time"][name]["raw_nll_degradation"] for name in self.names
        )
        self.assertNotAlmostEqual(joint["raw_nll_degradation"], summed_individual, places=6)

        singleton = diagnose_operations(
            self.backend.numerical,
            self.document,
            self.parent,
            samples=8,
            operations=(self.names[0],),
            joint=(self.names[0],),
        )["interventions"]
        isolated = singleton["one_at_a_time"][self.names[0]]
        single_joint = singleton["joint"]
        self.assertEqual(single_joint, isolated)
        self.assertIsNot(single_joint, isolated)
        self.assertIsNot(single_joint["selected_operations"], isolated["selected_operations"])
        single_joint["selected_operations"].append("diagnostic-only-marker")
        self.assertEqual(isolated["selected_operations"], [self.names[0]])

    def test_attribution_rejects_unknown_duplicate_or_oversized_selections(self) -> None:
        from gibbsiq.qualification.adapters.model_workload import diagnose_operations

        bad = (
            {"operations": ()},
            {"operations": (*self.names, self.backend.numerical.operations[2].operation_id)},
            {"operations": (self.names[0], self.names[0])},
            {"operations": ("clf",)},
            {"operations": self.names, "joint": ("clf",)},
            {"operations": self.names, "joint": (self.names[0], self.names[0])},
            {"operations": self.names, "samples": 0},
        )
        for kwargs in bad:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                diagnose_operations(self.backend.numerical, self.document, self.parent, **kwargs)


if __name__ == "__main__":
    unittest.main()
