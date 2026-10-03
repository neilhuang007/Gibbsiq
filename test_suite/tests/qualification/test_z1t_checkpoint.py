"""Trusted-local Z1T checkpoint loading against independent upstream execution."""

from __future__ import annotations

from dataclasses import asdict
import importlib.util
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(
    importlib.util.find_spec("z1t") is not None, "pinned Z1T integration environment is not installed"
)
class Z1TCheckpointTests(unittest.TestCase):
    def _fixture(self, path: Path, *, config=None):
        import equinox as eqx
        import jax
        from z1t.components import Config
        from z1t.model import create_model
        from gibbsiq.qualification.adapters.z1t import TinyZ1TConfig

        tiny = TinyZ1TConfig() if config is None else config
        upstream = Config(**asdict(tiny), aft_kind="conv", tanh_linear=True, tanh_mlp=True, remat=False)
        model = create_model(upstream, jax.random.key(91))
        model = eqx.tree_at(lambda tree: tree.clf.bias, model, model.clf.bias + 0.375)
        eqx.tree_serialise_leaves(path, model)
        return tiny, model

    def test_cpu_leaf_validation_uses_a_shared_numpy_host_view(self) -> None:
        import jax.numpy as jnp
        import numpy as np
        from gibbsiq.qualification.adapters.z1t_checkpoint import _cpu_host_view

        leaf = jnp.arange(16, dtype=jnp.float32)
        host = _cpu_host_view(leaf, np=np)

        self.assertTrue(np.shares_memory(host, np.asarray(leaf)))
        np.testing.assert_array_equal(host, np.arange(16, dtype=np.float32))

    def test_loaded_parameters_drive_forward_observation_and_sampler_replay(self) -> None:
        import numpy as np
        from gibbsiq.qualification.adapters.z1t import NumericalZ1T
        from gibbsiq.qualification.adapters.z1t_checkpoint import load_z1t_checkpoint
        from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel
        from test_suite.tests.qualification.test_ideal_tanh_profile import identity

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tiny.eqx"
            config, direct = self._fixture(path)
            loaded = load_z1t_checkpoint(path, config=config)
            generated = NumericalZ1T(config, seed=91)
            tokens = [0, 1, 2, 3]

            expected = np.asarray(direct(np.asarray(tokens, dtype=np.int32)))
            actual = np.asarray(loaded.forward(tokens).logits)
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-6)
            self.assertGreater(
                float(np.max(np.abs(actual - np.asarray(generated.forward(tokens).logits)))), 0.1
            )
            self.assertEqual(loaded.parameter_identity_type, "checkpoint-sha256")
            self.assertEqual(loaded.provenance, "loaded-local-checkpoint")

            name = loaded.operations[0].operation_id
            observed = loaded.forward(tokens, observe=(name,), retention="trace")
            np.testing.assert_allclose(np.asarray(observed.logits), expected, rtol=0, atol=1e-6)
            wrapper = IdealTanhModel(loaded, samples=8)
            run = identity("loaded-checkpoint")
            first = wrapper.forward(tokens, run, sampled_operations=(name,))
            replay = wrapper.forward(tokens, run, sampled_operations=(name,))
            np.testing.assert_array_equal(first.logits, replay.logits)

    def test_truncation_trailing_bytes_and_wrong_structure_are_rejected(self) -> None:
        from gibbsiq.qualification.adapters.z1t import TinyZ1TConfig
        from gibbsiq.qualification.adapters.z1t_checkpoint import load_z1t_checkpoint

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "tiny.eqx"
            config, _ = self._fixture(path)
            payload = path.read_bytes()
            for name, changed in (
                ("truncated.eqx", payload[:-17]),
                ("trailing.eqx", payload + b"unexpected"),
            ):
                candidate = root / name
                candidate.write_bytes(changed)
                with self.subTest(name=name), self.assertRaises(ValueError):
                    load_z1t_checkpoint(candidate, config=config)

            wrong = root / "wrong.eqx"
            self._fixture(wrong, config=TinyZ1TConfig(n_layers=2))
            with self.assertRaises(ValueError):
                load_z1t_checkpoint(wrong, config=config)

    def test_default_mode_refuses_nonreleased_artifact_identity(self) -> None:
        from gibbsiq.qualification.adapters.z1t_checkpoint import load_z1t_checkpoint

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tiny.eqx"
            self._fixture(path)
            with self.assertRaisesRegex(ValueError, "released Z1T-0"):
                load_z1t_checkpoint(path)

    def test_nonfinite_parameters_and_out_of_bounds_sparse_indices_are_rejected(self) -> None:
        import equinox as eqx
        import jax.numpy as jnp
        from gibbsiq.qualification.adapters.z1t_checkpoint import load_z1t_checkpoint

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "base.eqx"
            config, model = self._fixture(base)
            invalid_models = {
                "nonfinite.eqx": eqx.tree_at(
                    lambda tree: tree.clf.bias,
                    model,
                    model.clf.bias.at[0].set(jnp.inf),
                ),
                "indices.eqx": eqx.tree_at(
                    lambda tree: tree.blocks[0].attn.qkv_proj.linear.indices,
                    model,
                    model.blocks[0].attn.qkv_proj.linear.indices.at[0, 0].set(config.n_embed),
                ),
            }
            for name, invalid in invalid_models.items():
                path = root / name
                eqx.tree_serialise_leaves(path, invalid)
                with self.subTest(name=name), self.assertRaises(ValueError):
                    load_z1t_checkpoint(path, config=config)


if __name__ == "__main__":
    unittest.main()
