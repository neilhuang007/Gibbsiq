"""The explicit software codebook has independently hand-computable behavior."""

import math
import importlib.util
import unittest

from test_suite.tests.qualification.test_ideal_tanh_profile import identity


class Dy4pRepresentationTests(unittest.TestCase):
    def test_every_codeword_and_zero_tie_follow_the_declared_encoding(self):
        from gibbsiq.qualification.profiles import encode_dy4p

        for code in range(16):
            value = (2 * code - 15) / 32
            encoded = encode_dy4p(value)
            self.assertEqual(encoded.code, code)
            self.assertEqual(encoded.decoded, value)
            self.assertEqual(encoded.error, 0.0)
            self.assertEqual(
                sum(spin * weight for spin, weight in zip(encoded.spins, (1 / 4, 1 / 8, 1 / 16, 1 / 32))),
                value,
            )
        self.assertEqual(encode_dy4p(0).decoded, 1 / 32)
        self.assertEqual(encode_dy4p(-15 / 32).spins, (-1, -1, -1, -1))
        self.assertEqual(encode_dy4p(15 / 32).spins, (1, 1, 1, 1))
        self.assertEqual(encode_dy4p(math.nextafter(15 / 32, 0)).code, 15)
        with self.assertRaises(ValueError):
            encode_dy4p(math.nextafter(15 / 32, math.inf))
        with self.assertRaises(ValueError):
            encode_dy4p(math.nextafter(-15 / 32, -math.inf))
        for invalid in (True, math.nan, math.inf, "0", 1):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                encode_dy4p(invalid)

    def test_profile_rules_are_immutable_and_unsupported_ids_fail(self):
        from gibbsiq.qualification.profiles import get_profile

        ideal = get_profile("ideal-tanh-iid-v1")
        dy4p = get_profile("dy4p-conditional-iid-v1")
        self.assertEqual(ideal.input_encoding, "existing float32 tensor, unchanged")
        self.assertEqual(dy4p.parent_reuse, "fixed word or independent joint redraw per output draw")
        self.assertEqual(dy4p.unwrapped_operations, "no whole-model support")
        with self.assertRaises((AttributeError, TypeError)):
            dy4p.saturation = "clip"
        with self.assertRaises(ValueError):
            get_profile("dy4p-whole-model")

    def test_deterministic_reference_separates_original_and_encoded_input(self):
        from gibbsiq.qualification.profiles import dy4p_reference

        result = dy4p_reference(value=0, weight=4, bias=0)
        self.assertEqual(result.encoding.code, 8)
        self.assertEqual(result.parent_mean, 1 / 32)
        self.assertEqual(result.numerical_mean, 0)
        self.assertAlmostEqual(result.representation_mean, math.tanh(1 / 8))
        self.assertAlmostEqual(result.variance, 1 - result.representation_mean**2)
        self.assertAlmostEqual(
            dy4p_reference(value=1 / 32, weight=0, bias=0.5).representation_mean, math.tanh(0.5)
        )
        self.assertAlmostEqual(dy4p_reference(value=15 / 32, weight=32, bias=-15).representation_mean, 0)
        self.assertAlmostEqual(dy4p_reference(value=15 / 32, weight=32, bias=32).representation_mean, 1)

    def test_invalid_modes_coefficients_and_masses_fail(self):
        from gibbsiq.qualification.profiles import dy4p_reference

        for kwargs in (
            {},
            {"value": 0, "parent_probabilities": [1 / 16] * 16},
            {"value": 0, "weight": 32.01},
            {"value": 0, "bias": -32.01},
            {"value": 0, "weight": True},
            {"value": 0, "bias": math.inf},
            {"parent_probabilities": [1 / 16] * 15},
            {"parent_probabilities": [-0.1] + [1.1] + [0] * 14},
            {"parent_probabilities": [1 / 16] * 15 + [0.06250000001]},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                dy4p_reference(**kwargs)

    def test_stochastic_parents_average_the_nonlinear_law(self):
        from gibbsiq.qualification.profiles import dy4p_reference

        masses = [0.5] + [0.0] * 14 + [0.5]
        result = dy4p_reference(weight=4, bias=0.5, parent_probabilities=masses)
        expected = (math.tanh(0.5 - 4 * 15 / 32) + math.tanh(0.5 + 4 * 15 / 32)) / 2
        self.assertAlmostEqual(result.representation_mean, expected)
        self.assertAlmostEqual(result.numerical_mean, math.tanh(0.5))
        self.assertGreater(abs(result.representation_mean - result.numerical_mean), 0.25)


@unittest.skipUnless(importlib.util.find_spec("jax") is not None, "optional JAX is not installed")
class Dy4pSamplingTests(unittest.TestCase):
    def test_fixed_word_conditional_and_replay(self):
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import sample_dy4p

        kwargs = dict(
            value=0, weight=4, bias=0, randomization=identity("dy4p-fixed"), samples=2048, retain_draws=True
        )
        first = sample_dy4p(**kwargs)
        second = sample_dy4p(**kwargs)
        np.testing.assert_array_equal(first.draws, second.draws)
        np.testing.assert_array_equal(first.parent_codes, second.parent_codes)
        self.assertTrue(np.all(first.parent_codes == 8))
        self.assertTrue(np.isin(first.draws, (-1, 1)).all())
        self.assertFalse(first.draws.flags.writeable)
        self.assertFalse(first.parent_codes.flags.writeable)
        expected = math.tanh(4 / 32)
        self.assertLessEqual(abs(first.mean - expected), 8 * math.sqrt((1 - expected**2) / 2048))
        other = sample_dy4p(**(kwargs | {"randomization": identity("dy4p-other")}))
        self.assertFalse(np.array_equal(first.draws, other.draws))

    def test_joint_parent_mixture_is_redrawn_per_output(self):
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_emulation import sample_dy4p

        masses = [0.25] + [0] * 14 + [0.75]
        result = sample_dy4p(
            parent_probabilities=masses,
            weight=4,
            bias=0.5,
            randomization=identity("dy4p-mixture"),
            samples=4096,
            retain_draws=True,
        )
        self.assertTrue(np.isin(result.parent_codes, (0, 15)).all())
        p0 = float(np.mean(result.parent_codes == 0))
        self.assertLessEqual(abs(p0 - 0.25), 8 * math.sqrt(0.25 * 0.75 / 4096))
        expected = 0.25 * math.tanh(0.5 - 4 * 15 / 32) + 0.75 * math.tanh(0.5 + 4 * 15 / 32)
        self.assertLessEqual(abs(result.mean - expected), 8 * math.sqrt((1 - expected**2) / 4096))
        for code, field in ((0, 0.5 - 4 * 15 / 32), (15, 0.5 + 4 * 15 / 32)):
            mask = result.parent_codes == code
            observed_count = int(np.sum(mask))
            self.assertGreaterEqual(observed_count, 256)
            conditional_mean = math.tanh(field)
            observed_mean = float(np.mean(result.draws[mask]))
            conditional_limit = 8 * math.sqrt((1 - conditional_mean**2) / observed_count)
            self.assertLessEqual(abs(observed_mean - conditional_mean), conditional_limit)

    def test_preflight_rejects_unsupported_requests(self):
        from gibbsiq.qualification.adapters.z1t_emulation import sample_dy4p

        valid = dict(value=0, randomization=identity("invalid"))
        for overrides in (
            {"value": 1},
            {"weight": 33},
            {"bias": -33},
            {"samples": 0},
            {"samples": 4097},
            {"samples": True},
            {"retain_draws": 1},
            {"max_trace_bytes": True},
            {"parent_probabilities": [1 / 16] * 16},
            {"value": None, "parent_probabilities": [1e308] * 16},
            {"value": None},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                sample_dy4p(**(valid | overrides))
        with self.assertRaises(ValueError):
            sample_dy4p(**(valid | {"samples": 32, "retain_draws": True, "max_trace_bytes": 63}))


if __name__ == "__main__":
    unittest.main()
