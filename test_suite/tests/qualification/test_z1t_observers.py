"""Behavioral checks for the pinned tiny model's observation boundaries."""

import importlib.util
import unittest


@unittest.skipUnless(
    importlib.util.find_spec("z1t") is not None, "pinned Z1T integration environment is not installed"
)
class Z1TObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T

        cls.adapter = NumericalZ1T()
        cls.tokens = [0, 1, 2, 3]

    def test_read_only_capture_preserves_forward_and_sparse_arithmetic(self) -> None:
        import numpy as np

        adapter = self.adapter
        names = tuple(operation.operation_id for operation in adapter.operations)
        self.assertEqual(
            names,
            (
                "blocks.0.attn.qkv_proj",
                "blocks.0.attn.out_proj",
                "blocks.0.mlp.proj1",
                "blocks.0.mlp.proj2",
            ),
        )
        expected = np.asarray(adapter.forward(self.tokens).logits)
        observed = adapter.forward(self.tokens, observe=names, retention="trace")
        np.testing.assert_allclose(np.asarray(observed.logits), expected, rtol=0, atol=1e-6)
        self.assertEqual(tuple(observed.captures), names)
        with self.assertRaises(TypeError):
            observed.captures[names[0]] = None

        capture = observed.captures[names[0]]
        linear = adapter.model.blocks[0].attn.qkv_proj.linear
        x = capture.inputs.values
        expected_field = np.sum(
            np.asarray(linear.weight)[None, :, :] * x[:, np.asarray(linear.indices)], axis=-1
        ) + np.asarray(linear.bias)
        np.testing.assert_allclose(capture.field.values, expected_field, rtol=0, atol=1e-6)
        np.testing.assert_allclose(capture.output.values, np.tanh(expected_field), rtol=0, atol=1e-6)
        self.assertEqual(capture.inputs.axes, ("token", "feature"))
        self.assertEqual(capture.field.shape, (4, 20))
        self.assertEqual(capture.output.shape, (4, 20))
        self.assertEqual(adapter.operations[0].fan_in, 4)
        self.assertTrue(np.isfinite(capture.output.values).all())
        with self.assertRaises(ValueError):
            capture.output.values[0, 0] = 0

    def test_summary_trace_agree_and_cap_is_cumulative(self) -> None:
        import numpy as np

        names = tuple(operation.operation_id for operation in self.adapter.operations)
        summary = self.adapter.forward(self.tokens, observe=names, retention="summaries")
        trace = self.adapter.forward(self.tokens, observe=names, retention="trace")
        for name in names:
            for tensor in ("inputs", "field", "output"):
                a = getattr(summary.captures[name], tensor)
                b = getattr(trace.captures[name], tensor)
                self.assertIsNone(a.values)
                self.assertEqual(a.shape, b.shape)
                self.assertEqual(a.dtype, b.dtype)
                for key in ("minimum", "maximum", "mean", "rms"):
                    self.assertAlmostEqual(getattr(a, key), getattr(b, key), places=6)
                self.assertAlmostEqual(a.mean, float(np.mean(b.values)), places=5)
        first = trace.captures[names[0]]
        first_bytes = sum(getattr(first, tensor).values.nbytes for tensor in ("inputs", "field", "output"))
        self.adapter.forward(self.tokens, observe=names[:1], retention="trace", max_trace_bytes=first_bytes)
        with self.assertRaises(ValueError):
            self.adapter.forward(
                self.tokens, observe=names[:2], retention="trace", max_trace_bytes=first_bytes
            )

    def test_identity_and_zero_interventions(self) -> None:
        import jax.numpy as jnp
        import numpy as np

        expected = np.asarray(self.adapter.forward(self.tokens).logits)
        calls = []

        def identity(name, inputs, field, numerical_output):
            calls.append((name, inputs.shape, field.shape, numerical_output.shape))
            return numerical_output

        result = self.adapter.forward(self.tokens, transform=identity)
        np.testing.assert_allclose(np.asarray(result.logits), expected, rtol=0, atol=1e-6)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all(shape[0] == 4 for _, shape, _, _ in calls))

        def zero_one(name, inputs, field, numerical_output):
            if name == "blocks.0.attn.out_proj":
                return jnp.zeros_like(numerical_output)
            return numerical_output

        changed = np.asarray(self.adapter.forward(self.tokens, transform=zero_one).logits)
        self.assertGreater(float(np.max(np.abs(changed - expected))), 1e-6)

        def bad_shape(name, inputs, field, numerical_output):
            return numerical_output[0]

        with self.assertRaises(ValueError):
            self.adapter.forward(self.tokens, transform=bad_shape)

        def bad_dtype(name, inputs, field, numerical_output):
            return numerical_output.astype(jnp.float16)

        with self.assertRaises(ValueError):
            self.adapter.forward(self.tokens, transform=bad_dtype)

    def test_invalid_observation_requests_fail(self) -> None:
        name = "blocks.0.attn.qkv_proj"
        for observe, retention, cap in (
            ((name, name), "trace", 1024),
            (("clf",), "trace", 1024),
            ((), "all", 1024),
            ((name,), "trace", True),
        ):
            with self.subTest(observe=observe, retention=retention, cap=cap), self.assertRaises(ValueError):
                self.adapter.forward(self.tokens, observe=observe, retention=retention, max_trace_bytes=cap)


if __name__ == "__main__":
    unittest.main()
