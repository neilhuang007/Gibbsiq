"""Bounded THRML Ising qualification adapter for the pinned optional stack."""

from __future__ import annotations

import math
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from gibbsiq.blocks import color_blocks
from gibbsiq.model import IsingModel, encode_variable_label, exact_label_key, exact_variable_position
from gibbsiq.program import _normalize_clamps
from gibbsiq.qualification._validation import _finite, _integer
from gibbsiq.qualification.adapters._jax import RNG_RECIPE, plan_keys, run_key
from gibbsiq.qualification.adapters._pinned import verify_stack
from gibbsiq.qualification.adapters.reference import enumerate_ising
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

SOURCE_REVISION = "9c4e6fbb800f5e5c627122e668ff1b158ef3782b"
SOURCE_HASHES = {
    "block_sampling.py": "f3a61a86c8101b3451948495188903a16fbd43c212edf1869aa6b8e06f5f08cd",
    "observers.py": "9783fb902fe1ab88495327be5fe756c136704400c0517fe30f7f7436e693d427",
    "models/ising.py": "c995fa3a3fff5f5ccd5a6b86f7ef4c8d82965ff2ddd32b886930fcb15a3cf532",
}
BACKEND_ID = "thrml-ising-native-cadence-v1"
STACK_VERSIONS = {"jax": "0.10.2", "jaxlib": "0.10.2", "equinox": "0.13.8", "numpy": "2.4.6"}


def _identity(name: str, value: object) -> ArtifactIdentity:
    return ArtifactIdentity(name, "1", identity_digest(value))


def _stack() -> tuple[Any, Any, Any, Any]:
    try:
        import jax
        import jax.numpy as jnp
        import numpy as np
        import thrml
        import thrml.observers
        import thrml.models
    except ImportError as error:
        raise UnsupportedCapabilityError(
            "THRML adapter requires pinned thrml==0.1.4 and JAX in the optional integration environment"
        ) from error
    verify_stack(
        adapter="THRML",
        module_file=thrml.__file__,
        distribution_versions={"thrml": "0.1.4", **STACK_VERSIONS},
        source_hashes=SOURCE_HASHES,
        source_revision=SOURCE_REVISION,
    )
    return jax, jnp, np, thrml


@dataclass(frozen=True, slots=True)
class THRMLBatch:
    mean: float
    states: Any | None
    axes: tuple[str, str, str]
    variables: tuple[Any, ...]
    retained_observations_per_chain: int
    requested_transitions_per_chain: int


class THRMLIsingBackend:
    def __init__(
        self,
        model: IsingModel,
        *,
        beta: float = 1.0,
        clamped: Any = None,
        observed_variables: Any = None,
        chains: int = 1,
        initial_state: str = "hinton",
    ) -> None:
        if not isinstance(model, IsingModel) or not 1 <= len(model.variables) <= 8:
            raise ValueError("THRML adapter needs an IsingModel with 1 through 8 variables")
        try:
            for variable in model.variables:
                encode_variable_label(variable)
        except TypeError as error:
            raise ValueError("THRML adapter requires core-encodable variable labels") from error
        beta = _finite(beta, name="beta")
        if beta <= 0:
            raise ValueError("beta must be positive")
        _integer(chains, name="chains", minimum=1, maximum=8)
        if initial_state not in {"hinton", "all_up", "all_down"}:
            raise ValueError("unsupported initial_state")
        free, clamped_order, clamps = _normalize_clamps(model, clamped)
        if not free:
            raise ValueError("at least one free variable is required")
        selected = model.variables if observed_variables is None else tuple(observed_variables)
        if not selected or len(selected) != len({exact_label_key(v) for v in selected}):
            raise ValueError("observed_variables must be nonempty and unique")
        try:
            canonical = tuple(
                model.variables[exact_variable_position(value, model.variables)] for value in selected
            )
        except KeyError as error:
            raise ValueError("observed_variables contains an unknown exact label") from error
        self.variables = tuple(model.variables)
        self.linear = tuple(model.linear[v] for v in self.variables)
        positions = {v: i for i, v in enumerate(self.variables)}
        self.quadratic = tuple(
            (positions[a], positions[b], value) for (a, b), value in model.quadratic.items()
        )
        self.offset = model.offset
        self.beta = beta
        self.clamped = tuple((positions[v], clamps[v]) for v in clamped_order)
        self.observed = tuple(positions[v] for v in canonical)
        self.chains = chains
        self.initial_state = initial_state
        self._prepared: WorkloadSpec | None = None
        self._compiled: OrderedDict[tuple[int, int, int, bool], Any] = OrderedDict()

    def __getstate__(self) -> dict[str, Any]:
        # Spawn workers reconstruct the trusted numerical program in prepare.
        return {
            name: getattr(self, name)
            for name in (
                "variables",
                "linear",
                "quadratic",
                "offset",
                "beta",
                "clamped",
                "observed",
                "chains",
                "initial_state",
            )
        } | {"_prepared": None, "_compiled": OrderedDict()}

    def _model(self) -> IsingModel:
        return IsingModel(
            self.variables,
            dict(zip(self.variables, self.linear)),
            {(self.variables[a], self.variables[b]): value for a, b, value in self.quadratic},
            offset=self.offset,
        )

    def _fixed(self) -> dict[str, object]:
        return {
            "variables": [encode_variable_label(v) for v in self.variables],
            "linear": self.linear,
            "quadratic": self.quadratic,
            "offset": self.offset,
            "beta": self.beta,
            "clamped": self.clamped,
            "observed": self.observed,
            "chains": self.chains,
            "initial_state": self.initial_state,
        }

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(BACKEND_ID, ("samples", "warmup", "thinning"), ("mean",))

    def _schedule_settings(self, settings: Mapping[str, Any]) -> tuple[int, int, int, int]:
        if set(settings) != {"samples", "warmup", "thinning"}:
            raise UnsupportedCapabilityError("THRML supports only samples, warmup and thinning")
        n = _integer(settings["samples"], name="samples", minimum=1, maximum=4096)
        w = _integer(settings["warmup"], name="warmup", minimum=0, maximum=4096)
        t = _integer(settings["thinning"], name="thinning", minimum=1, maximum=4096)
        transitions = w + (n - 1) * t
        if self.chains * (len(self.variables) - len(self.clamped)) * transitions > 1_000_000:
            raise ValueError("requested spin-update work exceeds 1,000,000 per run")
        return n, w, t, transitions

    def plan(
        self,
        *,
        runs: int = 16,
        samples: int = 32,
        warmup: int = 16,
        thinning: int = 1,
        seed: int = 7,
        margin: float = 0.25,
    ) -> RunPlan:
        runs = _integer(runs, name="runs", minimum=1, maximum=256)
        samples, warmup, thinning, _ = self._schedule_settings(
            {"samples": samples, "warmup": warmup, "thinning": thinning}
        )
        _integer(seed, name="seed", minimum=0, maximum=2**63 - 1)
        margin = _finite(margin, name="margin")
        if margin <= 0:
            raise ValueError("margin must be positive")
        fixed = self._fixed()
        reference = enumerate_ising(
            self._model(), beta=self.beta, clamped={self.variables[i]: s for i, s in self.clamped}
        )
        target = math.fsum(
            probability * state[position] / len(self.observed)
            for state, probability in zip(reference.states, reference.probabilities)
            for position in self.observed
        )
        source = _identity("thrml", {"source_commit": SOURCE_REVISION, "distribution": "0.1.4"})
        model_id = _identity(
            "thrml-ising-model", {k: fixed[k] for k in ("variables", "linear", "quadratic", "offset")}
        )
        context_id = _identity(
            "thrml-ising-context",
            {k: fixed[k] for k in ("beta", "clamped", "observed", "chains", "initial_state")},
        )
        candidate_id = _identity(
            BACKEND_ID, {"fixed": fixed, "cadence": "post-warmup-first-v1", "rng": RNG_RECIPE}
        )
        reference_id = _identity(
            "direct-ising-enumeration",
            {"model": model_id.digest, "context": context_id.digest, "mean": target},
        )
        run_ids = tuple(f"run-{index:04d}" for index in range(runs))
        cost_scope = CostScope(
            "software-thrml-spin-updates", ("gibbs_spin_updates",), ("initialization", "physical_device")
        )
        workload = WorkloadSpec(
            "thrml-ising-v1",
            "Pinned THRML native-cadence Ising run means",
            (source,),
            model_id,
            InputSpec(
                context_id,
                _identity("identity-preprocessing", {"version": 1}),
                (InputCase("fixed-context", context_id.digest, "evaluation", "fixed-context"),),
            ),
            (OperationSpec("ising-mean", (), ()),),
            "float64",
            {
                "beta": self.beta,
                "chains": self.chains,
                "initial_state": self.initial_state,
                "clamped": self.clamped,
                "observed": self.observed,
                "rng_recipe": RNG_RECIPE,
                "cadence": "post-warmup-first-v1",
                "source_revision": SOURCE_REVISION,
                "distribution_version": "0.1.4",
                "stack_versions": STACK_VERSIONS,
                "python_version": "3.13.5",
            },
            reference_id,
            candidate_id,
            ("samples", "warmup", "thinning"),
            AcceptanceContract(
                (
                    MetricSpec(
                        "mean_error",
                        "spin mean difference",
                        "target",
                        "candidate-reference",
                        Acceptance("equivalence", margin, -margin),
                        "bounded_fixed_n",
                        runs,
                        "independent_run",
                        "fixed_inputs",
                        Bounds(-1 - target, 1 - target),
                    ),
                )
            ),
            RandomizationSpec(seed, runs),
            ResourceBudget(runs, 180.0, 16 * 1024 * 1024),
            cost_scope,
            ("Apache-2.0:thrml",),
        )
        planned = tuple(
            PlannedRun(
                run_id,
                "fixed-context",
                "ising-mean",
                "evaluation",
                {"samples": samples, "warmup": warmup, "thinning": thinning},
            )
            for run_id in run_ids
        )
        return RunPlan(
            workload, planned, metric_bindings=(MetricBinding("mean_error", "mean", run_ids, target),)
        )

    def validate_plan(self, plan: RunPlan) -> None:
        if not isinstance(plan, RunPlan) or not 1 <= len(plan.runs) <= 256:
            raise ValueError("unsupported THRML run count")
        for run in plan.runs:
            self._schedule_settings(run.settings)
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
                    "THRML backend does not match frozen model/context/reference/profile identities"
                )
        jax, jnp, np, thrml = _stack()
        from gibbsiq.thrml_runtime import _Lowering

        model = self._model()
        coloring = color_blocks(model)
        lowering = _Lowering(model, coloring)
        ebm, _ = lowering.program(self.beta)
        clamped_positions = {position for position, _ in self.clamped}
        node_of = dict(zip(self.variables, lowering.nodes))
        free_blocks = [
            thrml.Block([node_of[v] for v in block if model.variables.index(v) not in clamped_positions])
            for block in coloring.blocks
        ]
        free_blocks = [block for block in free_blocks if len(block)]
        clamped_nodes = [lowering.nodes[position] for position, _ in self.clamped]
        clamped_blocks = [thrml.Block(clamped_nodes)] if clamped_nodes else []
        self._program = thrml.models.IsingSamplingProgram(ebm, free_blocks, clamped_blocks)
        self._ebm, self._free_blocks = ebm, free_blocks
        self._clamped_state = (
            [jnp.asarray([spin == 1 for _, spin in self.clamped], dtype=bool)] if clamped_nodes else []
        )
        self._selected_block = [thrml.Block([lowering.nodes[position] for position in self.observed])]
        self._jax, self._jnp, self._np, self._thrml = jax, jnp, np, thrml
        self._compiled.clear()
        self._prepared = workload

    def _schedule_function(self, n: int, w: int, t: int, retain: bool) -> Any:
        cache_key = (n, w, t, retain)
        if cache_key not in self._compiled:
            jax, jnp, thrml = self._jax, self._jnp, self._thrml
            schedule = thrml.SamplingSchedule(w, n, t)
            if retain:
                observer = thrml.observers.StateObserver(self._selected_block)
            else:

                def spin_transform(states: Any, _blocks: Any) -> Any:
                    return [2 * state.astype(jnp.int8) - 1 for state in states]

                observer = thrml.observers.MomentAccumulatorObserver(
                    [[(node,) for node in self._selected_block[0].nodes]],
                    spin_transform,
                )

            def sample_one(key: Any) -> Any:
                init_key, sampling_key = jax.random.split(key)
                if self.initial_state == "hinton":
                    initial = thrml.models.hinton_init(init_key, self._ebm, self._free_blocks, ())
                else:
                    initial = [
                        jnp.full((len(block.nodes),), self.initial_state == "all_up", dtype=bool)
                        for block in self._free_blocks
                    ]
                memory, observations = thrml.sample_with_observation(
                    sampling_key,
                    self._program,
                    schedule,
                    initial,
                    self._clamped_state,
                    observer.init(),
                    observer,
                )
                return observations[0] if retain else memory[0]

            if len(self._compiled) >= 8:
                self._compiled.popitem(last=False)
            self._compiled[cache_key] = jax.jit(sample_one)
        self._compiled.move_to_end(cache_key)
        return self._compiled[cache_key]

    def sample(
        self,
        run: PlannedRun,
        randomization: RandomizationIdentity,
        *,
        retain_states: bool = False,
    ) -> THRMLBatch:
        if self._prepared is None:
            raise ValueError("THRML backend must be prepared")
        if type(retain_states) is not bool:
            raise ValueError("retain_states must be boolean")
        n, w, t, transitions = self._schedule_settings(run.settings)
        root = run_key(randomization)
        keys = self._jax.random.split(root, self.chains)
        execute = self._schedule_function(n, w, t, retain_states)
        results = self._jax.device_get(self._jax.vmap(execute)(keys))
        states = None
        if retain_states:
            states = self._np.array(self._np.where(results, 1, -1), dtype=self._np.int8, copy=True)
            states.setflags(write=False)
            mean = float(states.mean())
        else:
            mean = float(self._np.asarray(results).sum() / (self.chains * n * len(self.observed)))
        return THRMLBatch(
            mean,
            states,
            ("chain", "draw", "variable"),
            tuple(self.variables[position] for position in self.observed),
            n,
            transitions,
        )

    def execute(self, run: PlannedRun, randomization: RandomizationIdentity) -> ExecutionResult:
        batch = self.sample(run, randomization)
        assert self._prepared is not None
        scope = self._prepared.cost_scope
        work = self.chains * (len(self.variables) - len(self.clamped)) * batch.requested_transitions_per_chain
        return ExecutionResult(
            (
                Observation(
                    "mean",
                    run.operation_id,
                    run.case_id,
                    run.run_id,
                    "float64",
                    (),
                    (),
                    (batch.mean,),
                    units="spin",
                ),
            ),
            (
                CostRecord(
                    "sample_work",
                    "samples",
                    scope,
                    "modeled",
                    "available",
                    float(work),
                    method="requested-free-spin-updates",
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
