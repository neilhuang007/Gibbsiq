"""Explicit software-only conditional-spin candidate profiles."""

from __future__ import annotations

import math
import random

from gibbsiq.qualification.contracts import CostRecord, CostScope, Observation, PlannedRun, WorkloadSpec
from gibbsiq.qualification._validation import _finite, _integer
from gibbsiq.qualification.engine import BackendCapabilities, ExecutionResult, RandomizationIdentity
from gibbsiq.qualification.examples import SPIN_CANDIDATES, SPIN_FIELD


class SpinConditionalBackend:
    """Draw IID Python spins with a fresh full-digest RNG stream per run."""

    def __init__(self, profile: str = "iid", *, field: float = SPIN_FIELD) -> None:
        if profile not in SPIN_CANDIDATES:
            raise ValueError("unknown spin profile")
        self.profile = profile
        self.field = _finite(field, name="field")
        self._scope: CostScope | None = None

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(SPIN_CANDIDATES[self.profile], ("samples",), ("mean",))

    def prepare(self, workload: WorkloadSpec) -> None:
        from gibbsiq.qualification.examples import spin_conditional_plan

        expected = spin_conditional_plan(runs=1, samples=1, candidate=self.profile).workload
        fields = (
            "workload_id",
            "sources",
            "model_config",
            "inputs",
            "operations",
            "dtype",
            "precision",
            "reference",
            "candidate",
            "controls",
            "cost_scope",
            "license_refs",
        )
        if self.field != SPIN_FIELD or any(
            getattr(workload, name) != getattr(expected, name) for name in fields
        ):
            raise ValueError("spin backend does not match frozen model/input/reference/profile identities")
        self._scope = workload.cost_scope

    def execute(self, run: PlannedRun, randomization: RandomizationIdentity) -> ExecutionResult:
        if self._scope is None:
            raise ValueError("backend must be prepared")
        if set(run.settings) != {"samples"}:
            raise ValueError("IID spin profile supports only samples")
        samples = _integer(run.settings["samples"], name="samples", minimum=1, maximum=4096)
        probability_up = (1.0 + math.tanh(self.field)) / 2.0
        rng = random.Random(int(randomization.digest[7:], 16))
        mean = sum(1 if rng.random() < probability_up else -1 for _ in range(samples)) / samples
        if self.profile == "sign-reversed":
            mean = -mean
        observation = Observation(
            "mean", run.operation_id, run.case_id, run.run_id, "float64", (), (), (mean,), units="spin"
        )
        work = CostRecord(
            "sample_work",
            "samples",
            self._scope,
            "modeled",
            "available",
            float(samples),
            method="counted-python-random-draws",
        )
        energy = CostRecord(
            "energy",
            "joules",
            self._scope,
            "modeled",
            "unavailable",
            reason="physical energy was not measured",
            method="unknown",
        )
        return ExecutionResult((observation,), (work, energy))


__all__ = ["SpinConditionalBackend"]
