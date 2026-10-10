from __future__ import annotations

import math
import pickle
import sys
import unittest
from importlib import metadata, util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from gibbsiq.conversions import compile_ising  # noqa: E402
from gibbsiq.model import IsingModel  # noqa: E402
from gibbsiq.qualification.adapters.thrml import THRMLIsingBackend  # noqa: E402
from gibbsiq.qualification.engine import derive_randomization  # noqa: E402


def _pinned_thrml() -> bool:
    if util.find_spec("thrml") is None or util.find_spec("jax") is None:
        return False
    try:
        return metadata.version("thrml") == "0.1.4" and metadata.version("jax") == "0.10.2"
    except metadata.PackageNotFoundError:
        return False


class THRMLAdapterTests(unittest.TestCase):
    def test_startup_is_picklable_and_plan_is_bounded(self) -> None:
        backend = THRMLIsingBackend(compile_ising({"s": math.log(3) / 2}))
        self.assertIsInstance(pickle.loads(pickle.dumps(backend)), THRMLIsingBackend)
        plan = backend.plan(runs=2, samples=3, warmup=4, thinning=5)
        self.assertEqual(dict(plan.runs[0].settings), {"samples": 3, "warmup": 4, "thinning": 5})
        self.assertAlmostEqual(plan.metric_bindings[0].reference_value, -0.5)
        for settings in ({"samples": 0}, {"samples": 4097}, {"warmup": 4097}, {"thinning": 0}):
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                backend.plan(**settings)

    def test_core_exact_labels_remain_distinct_in_identity(self) -> None:
        tuple_label = ("spin", 1)
        backend = THRMLIsingBackend(compile_ising({tuple_label: 0.0}), observed_variables=(tuple_label,))
        plan = backend.plan(runs=1)
        self.assertEqual(pickle.loads(pickle.dumps(backend)).variables, (tuple_label,))
        self.assertNotEqual(
            plan.workload.model_config,
            THRMLIsingBackend(compile_ising({b"spin": 0.0})).plan(runs=1).workload.model_config,
        )
        unsupported = object()
        with self.assertRaisesRegex(ValueError, "core-encodable variable labels"):
            THRMLIsingBackend(IsingModel((unsupported,), {unsupported: 0.0}, {}))

    @unittest.skipUnless(
        _pinned_thrml(), "requires pinned S03 THRML 0.1.4/JAX 0.10.2 integration environment"
    )
    def test_native_cadence_axes_and_observer_equivalence(self) -> None:
        backend = THRMLIsingBackend(compile_ising({"s": math.log(3) / 2}), chains=2, initial_state="all_up")
        plan = backend.plan(runs=1, samples=1, warmup=0)
        backend.validate_plan(plan)
        backend.prepare(plan.workload)
        run = plan.runs[0]
        stream = derive_randomization(plan, run)
        summary = backend.sample(run, stream)
        trace = backend.sample(run, stream, retain_states=True)
        self.assertEqual((summary.mean, trace.mean), (1.0, 1.0))
        self.assertEqual(trace.states.shape, (2, 1, 1))
        self.assertEqual(trace.states.dtype.name, "int8")
        self.assertFalse(trace.states.flags.writeable)
        self.assertEqual(trace.axes, ("chain", "draw", "variable"))
        self.assertEqual(trace.requested_transitions_per_chain, 0)
        self.assertIsNone(summary.states)

    @unittest.skipUnless(
        _pinned_thrml(), "requires pinned S03 THRML 0.1.4/JAX 0.10.2 integration environment"
    )
    def test_equilibrium_and_conditional_signs(self) -> None:
        model = compile_ising({"a": 0.0, "b": 0.0}, {("a", "b"): math.log(3) / 2})
        for clamp, expected in ((1, -0.5), (-1, 0.5)):
            with self.subTest(clamp=clamp):
                backend = THRMLIsingBackend(model, clamped={"b": clamp}, observed_variables=("a",))
                plan = backend.plan(runs=1, samples=2048, warmup=16)
                self.assertAlmostEqual(plan.metric_bindings[0].reference_value, expected)
                backend.validate_plan(plan)
                backend.prepare(plan.workload)
                batch = backend.sample(plan.runs[0], derive_randomization(plan, plan.runs[0]))
                self.assertLess(abs(batch.mean - expected), 0.08)

    @unittest.skipUnless(
        _pinned_thrml(), "requires pinned S03 THRML 0.1.4/JAX 0.10.2 integration environment"
    )
    def test_trace_summary_replay_and_native_thinning(self) -> None:
        backend = THRMLIsingBackend(compile_ising({"a": 0.1, "b": -0.2}), chains=2)
        plan = backend.plan(runs=2, samples=4, warmup=3, thinning=5)
        backend.validate_plan(plan)
        backend.prepare(plan.workload)
        run = plan.runs[0]
        stream = derive_randomization(plan, run)
        first = backend.sample(run, stream, retain_states=True)
        second = backend.sample(run, stream)
        replay = backend.sample(run, stream, retain_states=True)
        self.assertEqual(first.requested_transitions_per_chain, 18)
        self.assertEqual(first.states.shape, (2, 4, 2))
        self.assertAlmostEqual(first.mean, second.mean)
        self.assertTrue((first.states == replay.states).all())
        self.assertNotEqual(
            backend.plan().workload.candidate,
            THRMLIsingBackend(compile_ising({"a": 0.1, "b": -0.2}), initial_state="all_up")
            .plan()
            .workload.candidate,
        )

    @unittest.skipUnless(
        _pinned_thrml(), "requires pinned S03 THRML 0.1.4/JAX 0.10.2 integration environment"
    )
    def test_compiled_cache_is_bounded_and_prepared_startup_is_plain(self) -> None:
        from gibbsiq.qualification.contracts import PlannedRun

        backend = THRMLIsingBackend(compile_ising({"s": 0.0}), initial_state="all_up")
        plan = backend.plan(runs=1, samples=1, warmup=0)
        backend.prepare(plan.workload)
        stream = derive_randomization(plan, plan.runs[0])
        with self.assertRaises(ValueError):
            backend.sample(plan.runs[0], stream, retain_states=1)
        for warmup in range(10):
            run = PlannedRun(
                "direct",
                "fixed-context",
                "ising-mean",
                "diagnostic",
                {"samples": 1, "warmup": warmup, "thinning": 1},
            )
            backend.sample(run, stream)
        self.assertLessEqual(len(backend._compiled), 8)
        restored = pickle.loads(pickle.dumps(backend))
        self.assertIsNone(restored._prepared)
        self.assertEqual(restored._compiled, {})

    @unittest.skipUnless(
        _pinned_thrml(), "requires pinned S03 THRML 0.1.4/JAX 0.10.2 integration environment"
    )
    def test_planned_streams_produce_distinct_spin_sequences(self) -> None:
        backend = THRMLIsingBackend(compile_ising({"s": 0.0}))
        plan = backend.plan(runs=4, samples=32)
        backend.validate_plan(plan)
        backend.prepare(plan.workload)
        sequences = {
            backend.sample(run, derive_randomization(plan, run), retain_states=True).states.tobytes()
            for run in plan.runs
        }
        self.assertGreater(len(sequences), 1)

    @unittest.skipUnless(
        _pinned_thrml(), "requires pinned S03 THRML 0.1.4/JAX 0.10.2 integration environment"
    )
    def test_clamped_and_free_selected_order_is_explicit(self) -> None:
        backend = THRMLIsingBackend(
            compile_ising({"a": 0.0, "b": 0.0}),
            clamped={"b": -1},
            observed_variables=("b", "a"),
            initial_state="all_up",
        )
        plan = backend.plan(runs=1, samples=1, warmup=0)
        backend.prepare(plan.workload)
        batch = backend.sample(plan.runs[0], derive_randomization(plan, plan.runs[0]), retain_states=True)
        self.assertEqual(batch.variables, ("b", "a"))
        self.assertEqual(batch.states.tolist(), [[[-1, 1]]])
        self.assertEqual(batch.mean, 0.0)

    @unittest.skipUnless(
        _pinned_thrml(), "requires pinned S03 THRML 0.1.4/JAX 0.10.2 integration environment"
    )
    def test_installed_source_mismatch_is_not_skipped(self) -> None:
        from unittest.mock import patch

        from gibbsiq.qualification.adapters.thrml import SOURCE_HASHES
        from gibbsiq.qualification.engine import UnsupportedCapabilityError

        backend = THRMLIsingBackend(compile_ising({"s": 0.0}))
        with patch.dict(SOURCE_HASHES, {"observers.py": "0" * 64}):
            with self.assertRaisesRegex(UnsupportedCapabilityError, "source observers.py differs"):
                backend.validate_plan(backend.plan(runs=1))


if __name__ == "__main__":
    unittest.main()
