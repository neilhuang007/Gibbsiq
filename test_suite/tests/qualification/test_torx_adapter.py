from __future__ import annotations

import pickle
import sys
import unittest
from importlib import metadata, util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from gibbsiq.qualification.adapters.torx import TorxCircuitBackend  # noqa: E402
from gibbsiq.qualification.engine import derive_randomization, UnsupportedCapabilityError  # noqa: E402


def _pinned_torx() -> bool:
    if util.find_spec("torx") is None or util.find_spec("jax") is None:
        return False
    try:
        return metadata.version("extro-torx") == "0.0.1" and metadata.version("jax") == "0.10.2"
    except metadata.PackageNotFoundError:
        return False


class TorxAdapterTests(unittest.TestCase):
    def test_plan_and_startup_identity(self) -> None:
        backend = TorxCircuitBackend()
        self.assertIsInstance(pickle.loads(pickle.dumps(backend)), TorxCircuitBackend)
        plan = backend.plan(runs=2, samples=5)
        self.assertEqual(tuple(binding.reference_value for binding in plan.metric_bindings), (0.5, 0.25))
        self.assertEqual(plan.workload.contract.alpha_for("bit0_error"), 0.025)
        self.assertNotEqual(
            plan.workload.candidate, TorxCircuitBackend(simulator="branching").plan(runs=2).workload.candidate
        )
        with self.assertRaises(ValueError):
            backend.plan(samples=0)

    @unittest.skipUnless(
        _pinned_torx(), "requires pinned S03 extro-torx 0.0.1/JAX 0.10.2 integration environment"
    )
    def test_real_modes_and_selected_sites(self) -> None:
        import numpy as np

        for mode in ("dfg", "branching"):
            with self.subTest(mode=mode):
                backend = TorxCircuitBackend(simulator=mode)
                plan = backend.plan(runs=2, samples=2048)
                backend.validate_plan(plan)
                backend.prepare(plan.workload)
                run = plan.runs[0]
                stream = derive_randomization(plan, run)
                batch = backend.sample(run, stream, retain_states=True)
                self.assertEqual(batch.states.shape, (2048, 2))
                self.assertEqual(batch.states.dtype, np.dtype("int32"))
                self.assertFalse(batch.states.flags.writeable)
                self.assertLess(abs(batch.bit_means[0] - 0.5), 0.06)
                self.assertLess(abs(batch.bit_means[1] - 0.25), 0.06)
                counts = np.bincount(batch.states[:, 0] * 2 + batch.states[:, 1], minlength=4) / 2048
                self.assertTrue(np.all(np.abs(counts - np.array([0.5, 0.0, 0.25, 0.25])) < 0.06))
                other = plan.runs[1]
                other_batch = backend.sample(other, derive_randomization(plan, other), retain_states=True)
                self.assertFalse(np.array_equal(batch.states, other_batch.states))
                if mode == "dfg":
                    captured = backend.sample(run, stream, observe=("g0", "out"))
                    self.assertEqual(set(captured.sites), {"g0", "out"})
                    self.assertEqual(captured.sites["g0"].shape, (2048, 1))
                    self.assertEqual(captured.sites["out"].shape, (2048, 2))
                    self.assertEqual(captured.bit_means, batch.bit_means)
                else:
                    with self.assertRaises(UnsupportedCapabilityError):
                        backend.sample(run, stream, observe=("g0",))

    @unittest.skipUnless(
        _pinned_torx(), "requires pinned S03 extro-torx 0.0.1/JAX 0.10.2 integration environment"
    )
    def test_exact_upstream_density(self) -> None:
        from gibbsiq.qualification.adapters.reference import torx_two_gate_reference

        for theta, initial in (((0.0, 0.0), (0, 0)), ((0.7, -0.4), (1, 1))):
            with self.subTest(theta=theta, initial=initial):
                backend = TorxCircuitBackend(theta=theta, initial=initial)
                backend.prepare(backend.plan(runs=1).workload)
                actual = backend.reference_probabilities()
                expected = torx_two_gate_reference(theta, initial).probabilities
                for observed, target in zip(actual, expected):
                    self.assertAlmostEqual(observed, target, delta=1e-6)

    @unittest.skipUnless(
        _pinned_torx(), "requires pinned S03 extro-torx 0.0.1/JAX 0.10.2 integration environment"
    )
    def test_changed_context_replay_and_no_observation_aux(self) -> None:
        from unittest.mock import patch
        from torx import psc

        backend = TorxCircuitBackend(theta=(0.7, -0.4), initial=(1, 1))
        plan = backend.plan(runs=2, samples=32)
        backend.validate_plan(plan)
        backend.prepare(plan.workload)
        self.assertNotEqual(tuple(plan.metric_bindings[i].reference_value for i in range(2)), (0.5, 0.25))
        run = plan.runs[0]
        stream = derive_randomization(plan, run)
        original = psc.DiscretePCircuit.sample
        called = []

        def checked(self, *args, **kwargs):
            called.append((kwargs.get("return_aux", False), kwargs.get("info")))
            return original(self, *args, **kwargs)

        with patch.object(psc.DiscretePCircuit, "sample", checked):
            first = backend.sample(run, stream, retain_states=True)
        self.assertTrue(called)
        self.assertTrue(all(not aux and info is None for aux, info in called))
        second = backend.sample(run, stream, retain_states=True)
        self.assertTrue((first.states == second.states).all())
        self.assertNotEqual(
            plan.workload.candidate,
            TorxCircuitBackend(theta=(0.7, -0.4), initial=(0, 1)).plan().workload.candidate,
        )

    @unittest.skipUnless(
        _pinned_torx(), "requires pinned S03 extro-torx 0.0.1/JAX 0.10.2 integration environment"
    )
    def test_summary_only_host_transfer_and_bounded_cache(self) -> None:
        from unittest.mock import patch
        from gibbsiq.qualification.contracts import PlannedRun

        for mode in ("dfg", "branching"):
            with self.subTest(mode=mode):
                backend = TorxCircuitBackend(simulator=mode)
                plan = backend.plan(runs=1, samples=9)
                backend.prepare(plan.workload)
                stream = derive_randomization(plan, plan.runs[0])
                with self.assertRaises(ValueError):
                    backend.sample(plan.runs[0], stream, retain_states=1)
                transferred = []
                original = backend._jax.device_get

                def checked(values, *, _transferred=transferred, _original=original):
                    _transferred.append(values)
                    return _original(values)

                with patch.object(backend._jax, "device_get", checked):
                    summary = backend.sample(plan.runs[0], stream)
                self.assertIsNone(summary.states)
                self.assertEqual(len(transferred), 1)
                leaves = backend._jax.tree.leaves(transferred[0])
                self.assertFalse(any(getattr(leaf, "shape", None) == (9, 2) for leaf in leaves))
                for n in range(1, 11):
                    run = PlannedRun(
                        "direct", "fixed-initial", "two-gate-circuit", "diagnostic", {"samples": n}
                    )
                    backend.sample(run, stream)
                self.assertLessEqual(len(backend._compiled), 8)
                self.assertFalse(hasattr(backend, "_simulators"))
                restored = pickle.loads(pickle.dumps(backend))
                self.assertIsNone(restored._prepared)
                self.assertEqual(restored._compiled, {})

    @unittest.skipUnless(
        _pinned_torx(), "requires pinned S03 extro-torx 0.0.1/JAX 0.10.2 integration environment"
    )
    def test_installed_gate_source_mismatch_is_not_skipped(self) -> None:
        from unittest.mock import patch

        from gibbsiq.qualification.adapters.torx import SOURCE_HASHES

        backend = TorxCircuitBackend()
        with patch.dict(SOURCE_HASHES, {"psc/gates/_binary.py": "0" * 64}):
            with self.assertRaisesRegex(UnsupportedCapabilityError, "source psc/gates/_binary.py differs"):
                backend.validate_plan(backend.plan(runs=1))


if __name__ == "__main__":
    unittest.main()
