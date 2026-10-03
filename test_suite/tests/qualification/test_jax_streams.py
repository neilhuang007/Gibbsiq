from __future__ import annotations

import sys
import unittest
from importlib import metadata, util
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from gibbsiq.qualification.adapters._jax import plan_keys, run_key  # noqa: E402
from gibbsiq.qualification.engine import RandomizationIdentity  # noqa: E402
from gibbsiq.qualification.examples import spin_conditional_plan  # noqa: E402


def _pinned_jax() -> bool:
    if util.find_spec("jax") is None:
        return False
    try:
        return metadata.version("jax") == "0.10.2" and metadata.version("jaxlib") == "0.10.2"
    except metadata.PackageNotFoundError:
        return False


@unittest.skipUnless(_pinned_jax(), "requires pinned S03 JAX/JAXLIB 0.10.2 integration environment")
class JaxStreamTests(unittest.TestCase):
    def test_all_digest_words_contribute(self) -> None:
        import jax
        import numpy as np

        words = (0,) * 8
        baseline = run_key(RandomizationIdentity("sha256:" + "00" * 32, words))
        for position in range(8):
            changed = list(words)
            changed[position] = 1
            digest = b"".join(word.to_bytes(4, "big") for word in changed)
            key = run_key(RandomizationIdentity("sha256:" + digest.hex(), tuple(changed)))
            self.assertFalse(np.array_equal(jax.random.key_data(baseline), jax.random.key_data(key)))

    def test_plan_keys_are_distinct_and_replay(self) -> None:
        import jax
        import numpy as np

        plan = spin_conditional_plan(runs=8)
        first = plan_keys(plan)
        second = plan_keys(plan)
        self.assertEqual(set(first), {run.run_id for run in plan.runs})
        self.assertEqual(len({bytes(np.asarray(jax.random.key_data(key))) for key in first.values()}), 8)
        for run_id in first:
            np.testing.assert_array_equal(
                jax.random.key_data(first[run_id]), jax.random.key_data(second[run_id])
            )

    def test_concrete_key_data_collision_is_rejected(self) -> None:
        import jax

        with patch("gibbsiq.qualification.adapters._jax.run_key", return_value=jax.random.key(0)):
            with self.assertRaisesRegex(ValueError, "key-data collision"):
                plan_keys(spin_conditional_plan(runs=2))


if __name__ == "__main__":
    unittest.main()
