"""Independent spin-law diagnostics for the bounded ideal software sampler."""

from __future__ import annotations

import hashlib
import importlib.util
import math
import unittest

from gibbsiq.qualification.engine import RandomizationIdentity


def identity(label: str) -> RandomizationIdentity:
    raw = hashlib.sha256(label.encode("ascii")).digest()
    return RandomizationIdentity(
        "sha256:" + raw.hex(),
        tuple(int.from_bytes(raw[index : index + 4], "big") for index in range(0, 32, 4)),
    )


@unittest.skipUnless(importlib.util.find_spec("jax") is not None, "optional JAX is not installed")
class IdealTanhSamplerTests(unittest.TestCase):
    def test_mean_and_variance_at_three_counts_against_analytic_spin_law(self):
        import jax.numpy as jnp
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import sample_iid_tanh

        reps = 2048
        for field, expected_mean in ((math.log(3) / 2, 0.5), (0.0, 0.0)):
            for count in (8, 32, 128):
                with self.subTest(field=field, count=count):
                    result = sample_iid_tanh(
                        jnp.full((reps,), field, dtype=jnp.float32),
                        randomization=identity(f"moments:{field}:{count}"),
                        operation_id="moments",
                        samples=count,
                    )
                    means = np.asarray(result.mean, dtype=np.float64)
                    variance = 1 - expected_mean**2
                    mean_limit = 8 * math.sqrt(variance / (count * reps))
                    fourth = (
                        count * (1 + 2 * expected_mean**2 - 3 * expected_mean**4)
                        + 3 * count * (count - 1) * variance**2
                    ) / count**4
                    variance_limit = 8 * math.sqrt((fourth - (variance / count) ** 2) / reps)
                    self.assertLessEqual(abs(float(np.mean(means)) - expected_mean), mean_limit)
                    self.assertLessEqual(
                        abs(float(np.mean((means - expected_mean) ** 2)) - variance / count),
                        variance_limit,
                    )
                    self.assertEqual(result.spin_draws, reps * count)
                    self.assertEqual(result.samples, count)
                    self.assertIsNone(result.draws)
                    np.testing.assert_allclose(
                        np.asarray(result.conditional_mean), expected_mean, rtol=0, atol=2e-7
                    )
                    np.testing.assert_allclose(
                        np.asarray(result.mean_variance), variance / count, rtol=0, atol=2e-7
                    )

    def test_replay_chunk_invariance_exact_spins_and_stream_separation(self):
        import jax.numpy as jnp
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import sample_iid_tanh

        field = jnp.array([[0.0, math.log(3) / 2], [-20.0, 20.0]], dtype=jnp.float32)
        kwargs = dict(
            randomization=identity("locked"), operation_id="block.0.proj", samples=65, retain_draws=True
        )
        a = sample_iid_tanh(field, chunk_size=1, **kwargs)
        b = sample_iid_tanh(field, chunk_size=64, **kwargs)
        np.testing.assert_array_equal(a.draws, b.draws)
        np.testing.assert_array_equal(a.mean, b.mean)
        self.assertEqual(a.draws.shape, (65, 2, 2))
        self.assertEqual(a.draws.dtype, np.int8)
        self.assertFalse(a.draws.flags.writeable)
        self.assertTrue(np.isin(a.draws, (-1, 1)).all())
        self.assertTrue(np.all(a.draws[:, 1, 0] == -1))
        self.assertTrue(np.all(a.draws[:, 1, 1] == 1))
        c = sample_iid_tanh(
            field,
            randomization=identity("changed"),
            operation_id="block.0.proj",
            samples=65,
            retain_draws=True,
        )
        d = sample_iid_tanh(
            field,
            randomization=identity("locked"),
            operation_id="block.0.other",
            samples=65,
            retain_draws=True,
        )
        self.assertFalse(np.array_equal(a.draws, c.draws))
        self.assertFalse(np.array_equal(a.draws, d.draws))

    def test_distinct_tensor_coordinates_and_injected_reused_stream(self):
        import jax.numpy as jnp
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import sample_iid_tanh

        result = sample_iid_tanh(
            jnp.zeros((512, 2), dtype=jnp.float32),
            randomization=identity("independence"),
            operation_id="pair",
            samples=32,
        )
        means = np.asarray(result.mean)
        threshold = 8 * (1 / 32) / math.sqrt(512)
        actual = float(np.mean(means[:, 0] * means[:, 1]))
        copied_stream = float(np.mean(means[:, 0] * means[:, 0]))
        self.assertLessEqual(abs(actual), threshold)
        self.assertGreater(abs(copied_stream), threshold)

    def test_invalid_controls_and_preflight_limits(self):
        import jax.numpy as jnp
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import sample_iid_tanh

        valid = dict(randomization=identity("validation"), operation_id="proj", samples=32)
        for bad_field in (
            jnp.array([float("nan")], dtype=jnp.float32),
            jnp.array([float("inf")], dtype=jnp.float32),
            jnp.zeros((65537,), dtype=jnp.float32),
            np.zeros((2,), dtype=np.float64),
            np.zeros((2,), dtype=np.int32),
            True,
            1,
        ):
            with (
                self.subTest(kind=type(bad_field).__name__, shape=getattr(bad_field, "shape", ())),
                self.assertRaises(ValueError),
            ):
                sample_iid_tanh(bad_field, **valid)
        for overrides in (
            {"samples": 0},
            {"samples": 4097},
            {"samples": True},
            {"chunk_size": 0},
            {"chunk_size": 65},
            {"chunk_size": True},
            {"retain_draws": 1},
            {"max_trace_bytes": True},
            {"operation_id": ""},
            {"operation_id": 3},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                sample_iid_tanh(jnp.zeros((2,), dtype=jnp.float32), **(valid | overrides))
        with self.assertRaises(ValueError):
            sample_iid_tanh(jnp.zeros((4096,), dtype=jnp.float32), **(valid | {"samples": 4096}))
        with self.assertRaises(ValueError):
            sample_iid_tanh(
                jnp.zeros((64,), dtype=jnp.float32),
                **(valid | {"retain_draws": True, "max_trace_bytes": 2047}),
            )


if __name__ == "__main__":
    unittest.main()
