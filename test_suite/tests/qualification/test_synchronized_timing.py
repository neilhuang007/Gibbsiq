"""Timing includes all asynchronously pending result leaves."""

import importlib.util
import unittest

from gibbsiq.qualification.contracts import CostScope
from gibbsiq.qualification.timing import profile_execution, synchronize_jax


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class Pending:
    def __init__(self, clock, delay):
        self.clock = clock
        self.delay = delay

    def block_until_ready(self):
        self.clock.advance(self.delay)
        return self


class SynchronizedTimingTests(unittest.TestCase):
    def test_all_leaves_and_phases_have_raw_times(self):
        clock = FakeClock()
        calls = []

        def prepare():
            calls.append("prepare")
            clock.advance(0.1)
            return "context"

        def compile_call(context):
            self.assertEqual(context, "context")
            calls.append("compile")
            clock.advance(0.2)
            return "handle"

        def execute(handle):
            self.assertEqual(handle, "handle")
            calls.append("execute")
            clock.advance(0.001)
            return {"first": Pending(clock, 0.002), "nested": [Pending(clock, 0.003)]}

        def synchronize(output):
            for leaf in (output["first"], output["nested"][0]):
                leaf.block_until_ready()

        def handle_output(output):
            calls.append("handle")
            clock.advance(0.004)

        scope = CostScope("complete_inference", ("model", "head"))
        env = {"runtime": {"kind": "fake"}}
        report = profile_execution(
            prepare=prepare,
            compile_call=compile_call,
            execute=execute,
            synchronize=synchronize,
            handle_output=handle_output,
            scope=scope,
            environment=env,
            repeats=3,
            warmups=2,
            clock=clock,
        )
        self.assertEqual(
            tuple(report.series),
            ("preparation", "compilation", "first_execution", "warmed_execution", "output_handling"),
        )
        self.assertAlmostEqual(report.series["preparation"].durations[0], 0.1)
        self.assertAlmostEqual(report.series["compilation"].durations[0], 0.2)
        self.assertAlmostEqual(report.series["first_execution"].durations[0], 0.006)
        self.assertEqual(report.series["warmed_execution"].count, 3)
        for duration in report.series["warmed_execution"].durations:
            self.assertAlmostEqual(duration, 0.006)
        for duration in report.series["output_handling"].durations:
            self.assertAlmostEqual(duration, 0.004)
        self.assertEqual(report.warmups, 2)
        self.assertEqual(report.scope, scope)
        self.assertEqual(calls.count("execute"), 6)
        env["runtime"]["kind"] = "mutated"
        self.assertEqual(report.environment["runtime"]["kind"], "fake")
        with self.assertRaises(TypeError):
            report.environment["runtime"]["kind"] = "mutated"

    def test_backward_clock_and_invalid_counts_refused(self):
        times = iter((2.0, 1.0))
        args = dict(
            prepare=lambda: None,
            compile_call=lambda _: None,
            execute=lambda _: None,
            synchronize=lambda _: None,
            handle_output=lambda _: None,
            scope=CostScope("body", ("model",)),
            environment={},
        )
        with self.assertRaises(ValueError):
            profile_execution(**args, repeats=1, warmups=0, clock=lambda: next(times))
        for repeats, warmups in ((True, 0), (0, 0), (1, -1), (101, 0), (1, 101)):
            with self.subTest(repeats=repeats, warmups=warmups), self.assertRaises(ValueError):
                profile_execution(**args, repeats=repeats, warmups=warmups)

    @unittest.skipUnless(importlib.util.find_spec("jax") is not None, "JAX not installed")
    def test_jax_registered_nested_pytree_and_opaque_leaf(self):
        import jax
        import jax.numpy as jnp
        import numpy as np

        @jax.tree_util.register_pytree_node_class
        class Pair:
            def __init__(self, left, right):
                self.left, self.right = left, right

            def tree_flatten(self):
                return (self.left, self.right), None

            @classmethod
            def tree_unflatten(cls, aux, children):
                return cls(*children)

        pair = Pair(jnp.arange(3), {"nested": [jnp.ones(2), np.array([1]), None, 4]})
        synchronize_jax(pair)
        np.testing.assert_array_equal(np.asarray(pair.left), [0, 1, 2])
        with self.assertRaises(TypeError):
            synchronize_jax({"ok": jnp.ones(1), "unknown": object()})


if __name__ == "__main__":
    unittest.main()
