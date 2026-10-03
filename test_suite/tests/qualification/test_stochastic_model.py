"""Whole-model integration of selected software spins into the pinned tiny model."""

from __future__ import annotations

import importlib.util
import unittest

from test_suite.tests.qualification.test_ideal_tanh_profile import identity


@unittest.skipUnless(
    importlib.util.find_spec("z1t") is not None, "pinned Z1T integration environment is not installed"
)
class StochasticModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T

        cls.numerical = NumericalZ1T()
        cls.tokens = [0, 1, 2, 3]
        cls.names = tuple(op.operation_id for op in cls.numerical.operations)

    def test_empty_subset_matches_numerical_and_counts_are_immutable(self):
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

        wrapper = IdealTanhModel(self.numerical, samples=8, operation_samples={self.names[0]: 32})
        self.assertEqual(wrapper.profile_id, "ideal-tanh-iid-v1")
        self.assertEqual(tuple(wrapper.operation_samples), self.names)
        self.assertEqual(wrapper.operation_samples[self.names[0]], 32)
        self.assertEqual(wrapper.operation_samples[self.names[1]], 8)
        self.assertEqual(wrapper.operation_groups["attention"], self.names[:2])
        self.assertEqual(wrapper.operation_groups["mlp"], self.names[2:])
        with self.assertRaises(TypeError):
            wrapper.operation_samples[self.names[0]] = 8
        expected = np.asarray(self.numerical.forward(self.tokens).logits)
        result = wrapper.forward(self.tokens, identity("empty"), sampled_operations=())
        np.testing.assert_allclose(result.logits, expected, rtol=0, atol=1e-6)

    def test_full_logits_replay_observation_and_nonlinear_downstream_effect(self):
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

        run = identity("stochastic-model")
        selected = (self.names[0],)
        for count in (8, 32, 128):
            with self.subTest(count=count):
                wrapper = IdealTanhModel(self.numerical, samples=count)
                first = wrapper.forward(self.tokens, run, sampled_operations=selected)
                observed = wrapper.forward(
                    self.tokens, run, sampled_operations=selected, observe=self.names[:2], retention="trace"
                )
                np.testing.assert_array_equal(first.logits, observed.logits)
                self.assertEqual(first.logits.shape, (4, self.numerical.config.vocab))
                self.assertTrue(np.isfinite(np.asarray(first.logits)).all())
                upstream = self.numerical.forward(self.tokens, observe=self.names[:2], retention="trace")
                np.testing.assert_allclose(
                    observed.captures[self.names[0]].field.values,
                    upstream.captures[self.names[0]].field.values,
                    atol=0,
                    rtol=0,
                )
                self.assertGreater(
                    float(
                        np.max(
                            np.abs(
                                observed.captures[self.names[0]].output.values
                                - upstream.captures[self.names[0]].output.values
                            )
                        )
                    ),
                    1e-5,
                )
                self.assertGreater(
                    float(
                        np.max(
                            np.abs(
                                observed.captures[self.names[1]].field.values
                                - upstream.captures[self.names[1]].field.values
                            )
                        )
                    ),
                    1e-7,
                )

    def test_all_selected_projections_and_rejected_requests(self):
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

        wrapper = IdealTanhModel(self.numerical, samples=8)
        result = wrapper.forward(self.tokens, identity("all"))
        self.assertEqual(result.logits.shape, (4, self.numerical.config.vocab))
        self.assertTrue(np.isfinite(np.asarray(result.logits)).all())
        for bad in (
            {"samples": 0},
            {"samples": 4097},
            {"samples": True},
            {"operation_samples": {"clf": 8}},
            {"operation_samples": {self.names[0]: 0}},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                IdealTanhModel(self.numerical, **bad)
        for bad in (("clf",), (self.names[0], self.names[0])):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                wrapper.forward(self.tokens, identity("invalid"), sampled_operations=bad)
        with self.assertRaises(ValueError):
            wrapper.forward(
                self.tokens,
                identity("invalid"),
                retention="trace",
                max_trace_bytes=0,
                observe=(self.names[0],),
            )

    def test_unselected_count_has_no_effect_and_work_refuses_before_forward(self):
        import numpy as np
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T, Operation
        from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

        first = IdealTanhModel(self.numerical, samples=8)
        second = IdealTanhModel(self.numerical, samples=8, operation_samples={self.names[1]: 128})
        run = identity("unselected-count")
        np.testing.assert_array_equal(
            first.forward(self.tokens, run, sampled_operations=self.names[:1]).logits,
            second.forward(self.tokens, run, sampled_operations=self.names[:1]).logits,
        )

        # A minimal contract-shaped numerical object makes a prohibited model
        # execution observable without allocating an oversized model.
        preflight_only = NumericalZ1T.__new__(NumericalZ1T)
        preflight_only.operations = (Operation("blocks.0.attn.out_proj", "tanh_sparse_linear", 64, 64, 4),)
        preflight_only._tokens = lambda _tokens: np.zeros((64,), dtype=np.int32)
        preflight_only.forward = lambda *_args, **_kwargs: self.fail("model executed before work preflight")
        oversized = IdealTanhModel(preflight_only, samples=4096)
        with self.assertRaises(ValueError):
            oversized.forward([0] * 64, identity("oversized"))


if __name__ == "__main__":
    unittest.main()
