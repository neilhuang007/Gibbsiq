"""Full-digest JAX stream conversion for optional numerical backends."""

from __future__ import annotations

from typing import Any

from gibbsiq.qualification.contracts import RunPlan
from gibbsiq.qualification.engine import RandomizationIdentity, _derive_randomization

RNG_RECIPE = "gibbsiq-jax-fold-in-v1"


def run_key(randomization: RandomizationIdentity) -> Any:
    """Fold every ordered big-endian SHA-256 word into a typed JAX key."""
    import jax

    if not isinstance(randomization, RandomizationIdentity):
        raise ValueError("randomization must be RandomizationIdentity")
    key = jax.random.key(0)
    for word in randomization.words:
        key = jax.random.fold_in(key, word)
    return key


def plan_keys(plan: RunPlan) -> dict[str, Any]:
    """Derive planned keys and reject concrete key-data collisions."""
    import jax

    if not isinstance(plan, RunPlan):
        raise ValueError("plan must be RunPlan")
    workload_digest = plan.workload.semantic_digest()
    keys = {run.run_id: run_key(_derive_randomization(plan, run, workload_digest)) for run in plan.runs}
    key_data = jax.device_get(tuple(jax.random.key_data(key) for key in keys.values()))
    seen: set[bytes] = set()
    for raw in key_data:
        data = bytes(raw.tobytes())
        if data in seen:
            raise ValueError("planned JAX key-data collision")
        seen.add(data)
    return keys
