"""Numerical-model behavior checked against a direct, separately built upstream model."""

from dataclasses import asdict
import importlib.util
import unittest


class TinyModelInputTests(unittest.TestCase):
    def test_unsupported_dimensions_and_boolean_controls_are_rejected(self) -> None:
        from gibbsiq.qualification.adapters.z1t import TinyZ1TConfig

        for parameters in (
            {"n_embed": 9},
            {"aft_heads": 3},
            {"sequence": 0},
            {"vocab": True},
            {"linear_fan_in": 8},
        ):
            with self.subTest(parameters=parameters), self.assertRaises(ValueError):
                TinyZ1TConfig(**parameters)


@unittest.skipUnless(
    importlib.util.find_spec("z1t") is not None, "pinned Z1T integration environment is not installed"
)
class NumericalZ1TTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import jax
        from z1t.components import Config
        from z1t.model import create_model
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T, TinyZ1TConfig

        cls.adapter = NumericalZ1T(TinyZ1TConfig(), seed=17)
        config = Config(
            **asdict(TinyZ1TConfig()), aft_kind="conv", tanh_linear=True, tanh_mlp=True, remat=False
        )
        cls.direct = create_model(config, jax.random.key(17))

    def test_complete_forward_matches_independent_upstream_call_and_replays(self) -> None:
        import jax.numpy as jnp
        import numpy as np

        tokens = jnp.array([0, 1, 2, 3], dtype=jnp.int32)
        expected = np.asarray(self.direct(tokens))
        result = self.adapter.forward(tokens)
        actual = np.asarray(result.logits)
        self.assertEqual(actual.shape, (4, 8))
        self.assertEqual(str(actual.dtype), "float32")
        self.assertTrue(np.isfinite(actual).all())
        np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-6)
        np.testing.assert_array_equal(np.asarray(self.adapter.forward(tokens).logits), actual)
        self.assertEqual(dict(result.captures), {})

    def test_future_tokens_do_not_change_earlier_logits(self) -> None:
        import numpy as np

        original = np.asarray(self.adapter.forward([0, 1, 2, 3]).logits)
        changed = np.asarray(self.adapter.forward([0, 1, 2, 7]).logits)
        np.testing.assert_allclose(changed[:3], original[:3], rtol=0.0, atol=1e-6)
        self.assertGreater(float(np.max(np.abs(changed[3] - original[3]))), 1e-6)

    def test_invalid_tokens_never_reach_the_numerical_forward(self) -> None:
        import jax.numpy as jnp
        import numpy as np

        for tokens in (
            [],
            [True],
            [0, True],
            [0.0, 1.0],
            [-1],
            [8],
            [0] * 5,
            [[0, 1]],
            np.array([0, 1], dtype=np.float32),
            np.array([True, False]),
            jnp.array([[0, 1]], dtype=jnp.int32),
        ):
            with self.subTest(tokens=tokens), self.assertRaises(ValueError):
                self.adapter.forward(tokens)

    def test_generated_model_identity_and_supported_token_conversion(self) -> None:
        import numpy as np

        self.assertEqual(len(self.adapter.parameter_identity), 64)
        self.assertEqual(len(self.adapter.operation_map_identity), 64)
        self.assertIn("13051e90df9669be5b8f9f34fb097329fa82f674", self.adapter.source_identity)
        expected = np.asarray(self.adapter.forward([0, 1]).logits)
        actual = np.asarray(self.adapter.forward(np.array([0, 1], dtype=np.int64)).logits)
        np.testing.assert_array_equal(actual, expected)
        self.assertEqual(actual.shape, (2, 8))

    def test_two_layer_observed_path_matches_separate_upstream_model(self) -> None:
        import jax
        import numpy as np
        from z1t.components import Config
        from z1t.model import create_model
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T, TinyZ1TConfig

        tiny = TinyZ1TConfig(n_layers=2)
        adapter = NumericalZ1T(tiny, seed=3)
        direct = create_model(
            Config(**asdict(tiny), aft_kind="conv", tanh_linear=True, tanh_mlp=True, remat=False),
            jax.random.key(3),
        )
        tokens = np.array([0, 1], dtype=np.int32)
        observed = adapter.forward(tokens, observe=("blocks.1.mlp.proj2",))
        np.testing.assert_allclose(np.asarray(observed.logits), np.asarray(direct(tokens)), rtol=0, atol=1e-6)
        self.assertEqual(len(adapter.operations), 8)
        self.assertEqual(tuple(observed.captures), ("blocks.1.mlp.proj2",))


if __name__ == "__main__":
    unittest.main()
