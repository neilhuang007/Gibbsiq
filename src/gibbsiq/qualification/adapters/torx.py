"""Pinned two-gate Torx qualification adapter with selected DFG observation."""

from __future__ import annotations

import math
import struct
from collections import OrderedDict
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, cast

from gibbsiq.qualification._validation import _finite, _integer
from gibbsiq.qualification.adapters._jax import RNG_RECIPE, plan_keys, run_key
from gibbsiq.qualification.adapters._pinned import verify_stack
from gibbsiq.qualification.adapters.reference import torx_two_gate_reference
from gibbsiq.qualification.contracts import (
    Acceptance,
    AcceptanceContract,
    ArtifactIdentity,
    Bounds,
    CostRecord,
    CostScope,
    InputCase,
    InputSpec,
    MetricBinding,
    MetricSpec,
    Observation,
    OperationSpec,
    PlannedRun,
    RandomizationSpec,
    ResourceBudget,
    RunPlan,
    WorkloadSpec,
    identity_digest,
)
from gibbsiq.qualification.engine import (
    BackendCapabilities,
    ExecutionResult,
    RandomizationIdentity,
    UnsupportedCapabilityError,
)

SOURCE_REVISION = "f8a46c12615019a96997f294ce07f6c2d50cfc82"
SOURCE_HASHES = {
    "dfg.py": "0d0feab09898bacbd0aa776648810a0160762941f49573a29cbf7ac35a98cb8c",
    "factor.py": "907e75385e9f4b755bdd1cc341f9587160b57f574425a3c84b6f533a05080223",
    "psc/_circuit.py": "010229c7bfe22ddb943b950cf384b3e5d468345fcd9c5ad58966256bb0d4d9cc",
    "psc/gates/_base.py": "5b94b81eebe3ccaee0f4ed239554070bc34852c45615862d5aa36160afef9923",
    "psc/gates/_binary.py": "f283dab02e438a7e17730876c309789f228b1f0d42d4becf7d0d3c3789d8c8da",
    "psc/simulation/sampled.py": "f3879f89a2dc50a9f5616733c420dc5722b750166296891d6c48c6ab1de329b9",
    "psc/simulation/statevector.py": "fb5e5c69fcbf316aee210b5ddc37f5d1efc0529ae78e52a9331ccd7be8553880",
}
STACK_VERSIONS = {"jax": "0.10.2", "jaxlib": "0.10.2", "equinox": "0.13.8", "numpy": "2.4.6"}


def _identity(name: str, value: object) -> ArtifactIdentity:
    return ArtifactIdentity(name, "1", identity_digest(value))


def _stack() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import jax
        import jax.numpy as jnp
        import numpy as np
        import torx
        from torx import psc
        from torx.dfg import DFGInfo
    except ImportError as error:
        raise UnsupportedCapabilityError(
            "Torx adapter requires pinned extro-torx==0.0.1 and JAX in the optional integration environment"
        ) from error
    verify_stack(
        adapter="Torx",
        module_file=torx.__file__,
        distribution_versions={"extro-torx": "0.0.1", **STACK_VERSIONS},
        source_hashes=SOURCE_HASHES,
        source_revision=SOURCE_REVISION,
    )
    return jax, jnp, np, psc, DFGInfo


@dataclass(frozen=True, slots=True)
class TorxBatch:
    bit_means: tuple[float, float]
    states: Any | None
    axes: tuple[str, str]
    sites: Any


class TorxCircuitBackend:
    def __init__(
        self,
        *,
        theta: tuple[float, float] = (0.0, 0.0),
        initial: tuple[int, int] = (0, 0),
        simulator: str = "dfg",
    ) -> None:
        if not isinstance(theta, (list, tuple)) or len(theta) != 2:
            raise ValueError("theta must contain two angles")
        if (
            not isinstance(initial, (list, tuple))
            or len(initial) != 2
            or any(type(value) is not int or value not in (0, 1) for value in initial)
        ):
            raise ValueError("initial must contain two exact integer bits")
        angles = tuple(_finite(value, name=f"theta[{index}]") for index, value in enumerate(theta))
        for index, value in enumerate(angles):
            try:
                lowered = struct.unpack("f", struct.pack("f", value))[0]
            except (OverflowError, struct.error) as error:
                raise ValueError(f"theta[{index}] is not representable in float32") from error
            if not math.isfinite(lowered) or (value != 0.0 and lowered == 0.0):
                raise ValueError(f"theta[{index}] is not representable in float32")
        if simulator not in {"dfg", "branching"}:
            raise UnsupportedCapabilityError("Torx adapter supports only dfg or branching simulator")
        self.theta = angles
        self.initial = tuple(initial)
        self.simulator = simulator
        self._prepared: WorkloadSpec | None = None
        self._compiled: OrderedDict[tuple[int, tuple[str, ...], bool], Any] = OrderedDict()

    @classmethod
    def from_plan(cls, plan: RunPlan) -> TorxCircuitBackend:
        """Reconstruct the pinned two-gate backend encoded by a frozen plan."""
        if not isinstance(plan, RunPlan) or plan.workload.workload_id != "torx-two-gate-v1":
            raise ValueError("plan is not a supported Torx two-gate workload")
        precision = plan.workload.precision
        backend = cls(
            theta=cast(tuple[float, float], precision.get("theta")),
            initial=cast(tuple[int, int], precision.get("initial")),
            simulator=cast(str, precision.get("simulator")),
        )
        if backend.capabilities().backend_id != plan.workload.candidate.identity:
            raise ValueError("Torx candidate identity differs from its encoded simulator")
        return backend

    def __getstate__(self) -> dict[str, Any]:
        return {
            "theta": self.theta,
            "initial": self.initial,
            "simulator": self.simulator,
            "_prepared": None,
            "_compiled": OrderedDict(),
        }

    def _candidate_id(self) -> str:
        return f"torx-two-gate-{self.simulator}-v1"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(self._candidate_id(), ("samples",), ("bit0_mean", "bit1_mean"))

    def plan(
        self,
        *,
        runs: int = 16,
        samples: int = 32,
        seed: int = 7,
        margin: float = 0.25,
    ) -> RunPlan:
        runs = _integer(runs, name="runs", minimum=1, maximum=256)
        samples = _integer(samples, name="samples", minimum=1, maximum=4096)
        _integer(seed, name="seed", minimum=0, maximum=2**63 - 1)
        margin = _finite(margin, name="margin")
        if margin <= 0:
            raise ValueError("margin must be positive")
        reference = torx_two_gate_reference(self.theta, self.initial)
        source = _identity("extro-torx", {"source_commit": SOURCE_REVISION, "distribution": "0.0.1"})
        model = _identity("torx-pnot-pcnot", {"gates": ["PNOT(0)", "PCNOT([0,1])"], "theta": self.theta})
        context = _identity("torx-initial-bits", {"initial": self.initial})
        candidate = _identity(
            self._candidate_id(),
            {
                "model": model.digest,
                "context": context.digest,
                "simulator": self.simulator,
                "rng": RNG_RECIPE,
            },
        )
        reference_id = _identity(
            "four-branch-enumeration",
            {
                "model": model.digest,
                "context": context.digest,
                "probabilities": reference.probabilities,
            },
        )
        run_ids = tuple(f"run-{index:04d}" for index in range(runs))
        metrics = tuple(
            MetricSpec(
                f"bit{index}_error",
                "bit mean difference",
                "target",
                "candidate-reference",
                Acceptance("equivalence", margin, -margin),
                "bounded_fixed_n",
                runs,
                "independent_run",
                "fixed_inputs",
                Bounds(-reference.bit_means[index], 1 - reference.bit_means[index]),
            )
            for index in range(2)
        )
        scope = CostScope("software-torx-gate-draws", ("gate_samples",), ("physical_device",))
        workload = WorkloadSpec(
            "torx-two-gate-v1",
            "Pinned Torx PNOT followed by PCNOT",
            (source,),
            model,
            InputSpec(
                context,
                _identity("identity-preprocessing", {"version": 1}),
                (InputCase("fixed-initial", context.digest, "evaluation", "fixed-initial"),),
            ),
            (OperationSpec("two-gate-circuit", (), ()),),
            "float64",
            {
                "theta": self.theta,
                "initial": self.initial,
                "simulator": self.simulator,
                "rng_recipe": RNG_RECIPE,
                "source_revision": SOURCE_REVISION,
                "distribution_version": "0.0.1",
                "stack_versions": STACK_VERSIONS,
                "python_version": "3.13.5",
            },
            reference_id,
            candidate,
            ("samples",),
            AcceptanceContract(metrics),
            RandomizationSpec(seed, runs),
            ResourceBudget(runs, 180.0, 16 * 1024 * 1024),
            scope,
            ("Apache-2.0:extro-torx",),
        )
        planned = tuple(
            PlannedRun(run_id, "fixed-initial", "two-gate-circuit", "evaluation", {"samples": samples})
            for run_id in run_ids
        )
        bindings = tuple(
            MetricBinding(f"bit{index}_error", f"bit{index}_mean", run_ids, reference.bit_means[index])
            for index in range(2)
        )
        return RunPlan(workload, planned, metric_bindings=bindings)

    def validate_plan(self, plan: RunPlan) -> None:
        if not isinstance(plan, RunPlan) or not 1 <= len(plan.runs) <= 256:
            raise ValueError("unsupported Torx run count")
        for run in plan.runs:
            if set(run.settings) != {"samples"}:
                raise UnsupportedCapabilityError("Torx two-gate adapter supports only samples")
            _integer(run.settings["samples"], name="samples", minimum=1, maximum=4096)
        _stack()
        plan_keys(plan)

    def prepare(self, workload: WorkloadSpec) -> None:
        expected = self.plan(
            runs=workload.randomization.independent_runs, seed=workload.randomization.master_seed
        ).workload
        for name in (
            "sources",
            "model_config",
            "inputs",
            "operations",
            "precision",
            "reference",
            "candidate",
            "controls",
            "cost_scope",
        ):
            if getattr(workload, name) != getattr(expected, name):
                raise ValueError(
                    "Torx backend does not match frozen model/context/reference/profile identities"
                )
        jax, jnp, np, psc, DFGInfo = _stack()
        circuit = psc.DiscretePCircuit([psc.PNOT(0), psc.PCNOT([0, 1])])
        if tuple(site.name for site in circuit.sites) != ("g0", "g1", "out"):
            raise UnsupportedCapabilityError("pinned Torx circuit site names changed")
        angles = [jnp.asarray([value], dtype=jnp.float32) for value in self.theta]
        self._jax, self._jnp, self._np, self._psc, self._DFGInfo = jax, jnp, np, psc, DFGInfo
        self._circuit, self._angles = circuit, angles
        self._initial = jnp.asarray(self.initial, dtype=jnp.int32)
        self._compiled.clear()
        self._prepared = workload

    def reference_probabilities(self) -> tuple[float, float, float, float]:
        if self._prepared is None:
            raise ValueError("Torx backend must be prepared")
        density = (
            self._jnp.zeros((4,), dtype=self._jnp.float32).at[self.initial[0] * 2 + self.initial[1]].set(1.0)
        )
        simulator = self._psc.StateVectorSimulator()
        compiled = simulator.build_circuit(self._circuit, self._angles)
        probabilities = self._jax.device_get(simulator.density(compiled, density))
        return (
            float(probabilities[0]),
            float(probabilities[1]),
            float(probabilities[2]),
            float(probabilities[3]),
        )

    def _sampling_function(self, n: int, selected: tuple[str, ...], retain_states: bool) -> Any:
        cache_key = (n, selected, retain_states)
        if cache_key not in self._compiled:
            jax, jnp = self._jax, self._jnp
            if self.simulator == "branching":
                simulator = self._psc.BranchingSimulator(num_samples=n)
                compiled = simulator.build_circuit(self._circuit, self._angles)

                def sample_many(key: Any) -> Any:
                    states = simulator.sample(compiled, self._initial, key)
                    return jnp.sum(states, axis=0), states if retain_states else None, ()
            else:

                def sample_many(key: Any) -> Any:
                    keys = jax.random.split(key, n)
                    if not selected:
                        states = jax.vmap(
                            lambda draw_key: self._circuit.sample(
                                draw_key,
                                {"in": self._initial},
                                self._angles,
                            )
                        )(keys)
                        return jnp.sum(states, axis=0), states if retain_states else None, ()
                    info = self._DFGInfo(expose_site_outputs=True)

                    def one(draw_key: Any) -> Any:
                        output, auxiliary = self._circuit.sample(
                            draw_key,
                            {"in": self._initial},
                            self._angles,
                            info=info,
                            return_aux=True,
                        )
                        sites = auxiliary[0]
                        return output, tuple(sites[name] for name in selected)

                    states, sites = jax.vmap(one)(keys)
                    return jnp.sum(states, axis=0), states if retain_states else None, sites

            if len(self._compiled) >= 8:
                self._compiled.popitem(last=False)
            self._compiled[cache_key] = jax.jit(sample_many)
        self._compiled.move_to_end(cache_key)
        return self._compiled[cache_key]

    def sample(
        self,
        run: PlannedRun,
        randomization: RandomizationIdentity,
        *,
        retain_states: bool = False,
        observe: tuple[str, ...] = (),
    ) -> TorxBatch:
        if self._prepared is None:
            raise ValueError("Torx backend must be prepared")
        if type(retain_states) is not bool:
            raise ValueError("retain_states must be boolean")
        if set(run.settings) != {"samples"}:
            raise UnsupportedCapabilityError("Torx two-gate adapter supports only samples")
        n = _integer(run.settings["samples"], name="samples", minimum=1, maximum=4096)
        selected = tuple(observe)
        if len(selected) != len(set(selected)) or any(name not in {"g0", "g1", "out"} for name in selected):
            raise UnsupportedCapabilityError("unknown or duplicate Torx observation site")
        if self.simulator == "branching" and selected:
            raise UnsupportedCapabilityError("branching simulator cannot expose matching DFG site traces")
        sums, raw_states, raw_sites = self._sampling_function(n, selected, retain_states)(
            run_key(randomization)
        )
        host_sums, host_states, host_sites = self._jax.device_get((sums, raw_states, raw_sites))
        means = (int(host_sums[0]) / n, int(host_sums[1]) / n)
        states = None
        if retain_states:
            states = self._np.array(host_states, dtype=self._np.int32, copy=True)
            states.setflags(write=False)
        sites = {}
        for name, raw in zip(selected, host_sites):
            copied = self._np.array(raw, copy=True)
            copied.setflags(write=False)
            sites[name] = copied
        return TorxBatch(means, states, ("draw", "variable"), MappingProxyType(sites))

    def execute(self, run: PlannedRun, randomization: RandomizationIdentity) -> ExecutionResult:
        batch = self.sample(run, randomization)
        assert self._prepared is not None
        scope = self._prepared.cost_scope
        observations = tuple(
            Observation(
                f"bit{index}_mean",
                run.operation_id,
                run.case_id,
                run.run_id,
                "float64",
                (),
                (),
                (value,),
                units="bit",
            )
            for index, value in enumerate(batch.bit_means)
        )
        return ExecutionResult(
            observations,
            (
                CostRecord(
                    "sample_work",
                    "samples",
                    scope,
                    "modeled",
                    "available",
                    float(2 * run.settings["samples"]),
                    method="two-gates-per-draw",
                ),
                CostRecord(
                    "energy",
                    "joules",
                    scope,
                    "modeled",
                    "unavailable",
                    reason="physical energy was not measured",
                    method="unknown",
                ),
            ),
        )
