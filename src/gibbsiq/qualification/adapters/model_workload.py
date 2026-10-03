"""Trusted, bounded complete-model backend for a generated tiny Z1T workload.

Plan construction and capability discovery use only the standard library.
Numerical model creation and stochastic execution happen in ``prepare`` and
``execute`` under the supervised qualification worker.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any, cast

from gibbsiq.qualification._validation import _integer
from gibbsiq.qualification.adapters.model_preflight import PINNED_SOURCE_REVISION
from gibbsiq.qualification.adapters.z1t import (
    NumericalZ1T,
    TinyZ1TConfig,
    _operation_groups,
    _operation_recipe,
)
from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel
from gibbsiq.qualification.artifacts import record_to_dict
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
    _positive_finite,
    canonical_json,
    identity_digest,
)
from gibbsiq.qualification.engine import BackendCapabilities, ExecutionResult, RandomizationIdentity
from gibbsiq.qualification.model_evaluation import CorpusSplit, LossSummary, combine_losses, language_loss


_CANDIDATE = "tiny-z1t-ideal-tanh-v1"
_PROFILE = "ideal-tanh-iid-v1"
_MEASUREMENT = "complete-model-evaluation"
_METRIC_VERSION = "teacher-forced-capped-nll-v1"
_RNG_RECIPE = "gibbsiq-run-stream-v1/document-stream-v1/jax-fold-in-v1/ideal-tanh-iid-v1"
_TRACE_LIMIT = 1_048_576
_SPIN_WORK_LIMIT = 8_388_608
_MAX_BYTES = 16 * 1024 * 1024
_MIN_BYTES = 65_536
_DEFAULT_CONFIG = TinyZ1TConfig()
_COST_SCOPE = CostScope(
    "complete-teacher-forced-evaluation",
    ("model-body", "final-head", "host-transfer", "independent-loss", "activation-summary"),
    ("model-preparation", "numerical-reference", "physical-device"),
)


def _count(value: object, *, name: str, maximum: int) -> int:
    return _integer(value, name=name, minimum=1, maximum=maximum)


def _positive_float(value: object, *, name: str, maximum: float) -> float:
    try:
        number = _positive_finite(value, name=name)
    except ValueError as error:
        raise ValueError(f"{name} must be finite, positive and at most {maximum}") from error
    if number > maximum:
        raise ValueError(f"{name} must be finite, positive and at most {maximum}")
    return number


def _identity(name: str, payload: object) -> ArtifactIdentity:
    return ArtifactIdentity(name, "1", identity_digest(payload))


def document_randomization(parent: RandomizationIdentity, document_id: str) -> RandomizationIdentity:
    """Derive one complete-digest stream for a document in an independent run."""
    if not isinstance(parent, RandomizationIdentity):
        raise ValueError("parent must be RandomizationIdentity")
    if type(document_id) is not str or not document_id.strip():
        raise ValueError("document_id must be a nonblank string")
    raw = hashlib.sha256(
        canonical_json(
            {
                "recipe": "gibbsiq-document-stream-v1",
                "parent": parent.digest,
                "document": document_id,
                "purpose": "teacher-forced",
            }
        )
    ).digest()
    return RandomizationIdentity(
        "sha256:" + raw.hex(),
        tuple(int.from_bytes(raw[index : index + 4], "big") for index in range(0, 32, 4)),
    )


class TinyModelBackend:
    """One fixed corpus, generated model recipe, and ideal software profile."""

    def __init__(
        self,
        documents: CorpusSplit,
        *,
        config: TinyZ1TConfig = _DEFAULT_CONFIG,
        initialization_seed: int = 17,
        profile_id: str = _PROFILE,
        cap: float = 8.0,
        observed_operations: tuple[str, ...] | None = None,
    ) -> None:
        if not isinstance(documents, CorpusSplit):
            raise ValueError("documents must be an explicit CorpusSplit")
        if not isinstance(config, TinyZ1TConfig):
            raise ValueError("config must be TinyZ1TConfig")
        if type(initialization_seed) is not int or not 0 <= initialization_seed <= 2**32 - 1:
            raise ValueError("initialization_seed must be a uint32 integer")
        if profile_id != _PROFILE:
            raise ValueError("only the ideal-tanh-iid-v1 software profile is supported")
        normalized_cap = _positive_float(cap, name="cap", maximum=128)
        for document in documents.documents:
            if len(document.inputs) > config.sequence or any(
                token >= config.vocab for token in document.tokens
            ):
                raise ValueError("document exceeds the declared model sequence or vocabulary")

        operations = _operation_recipe(config)
        names = {operation.operation_id for operation in operations}
        selected: tuple[str, ...]
        if observed_operations is None:
            selected = (operations[0].operation_id,)
        elif type(observed_operations) is tuple:
            selected = observed_operations
        else:
            raise ValueError("observed_operations must be a tuple of operation IDs")
        if any(type(name) is not str or name not in names for name in selected) or len(set(selected)) != len(
            selected
        ):
            raise ValueError("observed_operations contains an unknown or duplicate projection")

        self.documents = documents
        self.config = config
        self.initialization_seed = initialization_seed
        self.profile_id = profile_id
        self.cap = normalized_cap
        self.operations = operations
        self.operation_groups = _operation_groups(operations)
        self.observed_operations = selected
        self._preflight_trace()
        self._numerical: NumericalZ1T | None = None
        self._numerical_loss: LossSummary | None = None
        self._prepared_workload_digest: str | None = None

    @classmethod
    def from_plan(cls, plan: RunPlan) -> TinyModelBackend:
        """Reconstruct the trusted tiny-model backend encoded by a frozen plan."""
        if not isinstance(plan, RunPlan) or plan.workload.workload_id != "tiny-z1t-teacher-forced-v1":
            raise ValueError("plan is not a supported tiny Z1T workload")
        precision = plan.workload.precision
        config = precision.get("config")
        corpus = precision.get("corpus")
        observed = precision.get("observed_operations")
        if not isinstance(config, Mapping) or not isinstance(corpus, Mapping):
            raise ValueError("frozen tiny-model plan lacks config or corpus metadata")
        if not isinstance(observed, (list, tuple)):
            raise ValueError("frozen tiny-model plan lacks observed operation metadata")
        backend = cls(
            CorpusSplit.from_dict(corpus),
            config=TinyZ1TConfig(**dict(config)),
            initialization_seed=cast(int, precision.get("initialization_seed")),
            profile_id=cast(str, precision.get("profile_id")),
            cap=cast(float, precision.get("cap")),
            observed_operations=tuple(observed),
        )
        backend.validate_plan(plan)
        return backend

    def __getstate__(self) -> dict[str, Any]:
        state = self.__dict__.copy()
        state["_numerical"] = None
        state["_numerical_loss"] = None
        state["_prepared_workload_digest"] = None
        return state

    @property
    def numerical(self) -> NumericalZ1T:
        if self._numerical is None:
            raise ValueError("backend must be prepared")
        return self._numerical

    @property
    def numerical_loss(self) -> LossSummary:
        if self._numerical_loss is None:
            raise ValueError("backend must be prepared")
        return self._numerical_loss

    @property
    def parameter_identity(self) -> str | None:
        return None if self._numerical is None else self._numerical.parameter_identity

    @property
    def operation_map_identity(self) -> str | None:
        return None if self._numerical is None else self._numerical.operation_map_identity

    def _preflight_trace(self) -> None:
        by_name = {operation.operation_id: operation for operation in self.operations}
        trace_bytes = sum(
            len(document.inputs)
            * 4
            * sum(
                by_name[name].input_features + 2 * by_name[name].output_features
                for name in self.observed_operations
            )
            for document in self.documents.documents
        )
        if trace_bytes > _TRACE_LIMIT:
            raise ValueError("selected activation traces exceed the cumulative 1 MiB limit")

    def _settings(self, samples: object, operation_samples: Mapping[str, int] | None) -> dict[str, Any]:
        count = _count(samples, name="samples", maximum=4096)
        if operation_samples is None:
            return {"samples": count}
        if not isinstance(operation_samples, Mapping):
            raise ValueError("operation_samples must be a mapping")
        all_names = {operation.operation_id for operation in self.operations}
        if any(type(name) is not str or name not in all_names for name in operation_samples):
            raise ValueError("operation_samples contains an unknown projection")
        grouped: dict[str, int] = {}
        for group, names in self.operation_groups.items():
            present = tuple(name for name in names if name in operation_samples)
            if present and len(present) != len(names):
                raise ValueError("operation_samples must assign a complete group")
            if present:
                counts = {_count(operation_samples[name], name=name, maximum=4096) for name in names}
                if len(counts) != 1:
                    raise ValueError("operation_samples must use one count per group")
                grouped[group] = counts.pop()
        return {"samples": count, "grouped_samples": grouped} if grouped else {"samples": count}

    def _counts(self, settings: Mapping[str, Any]) -> dict[str, int]:
        if set(settings) not in ({"samples"}, {"samples", "grouped_samples"}):
            raise ValueError("run settings require samples and optional grouped_samples only")
        default = _count(settings["samples"], name="samples", maximum=4096)
        grouped = settings.get("grouped_samples", {})
        if not isinstance(grouped, Mapping) or not grouped or set(grouped) - set(self.operation_groups):
            if "grouped_samples" in settings:
                raise ValueError("grouped_samples must select known complete groups")
        counts = {operation.operation_id: default for operation in self.operations}
        for group, count in grouped.items():
            validated = _count(count, name=group, maximum=4096)
            for name in self.operation_groups[group]:
                counts[name] = validated
        return counts

    def _preflight_spin_work(self, counts: Mapping[str, int]) -> int:
        total = 0
        for document in self.documents.documents:
            work = sum(
                len(document.inputs) * op.output_features * counts[op.operation_id] for op in self.operations
            )
            if work > _SPIN_WORK_LIMIT:
                raise ValueError("per-document whole-model spin work exceeds 8388608 draws")
            total += work
        return total

    def capabilities(self) -> BackendCapabilities:
        names = (
            "capped_nll_degradation",
            "raw_nll",
            "numerical_raw_nll",
            "capped_nll",
            "numerical_capped_nll",
            "cap_hit_rate",
            "valid_tokens",
            "modeled_spin_draws",
            *(f"activation_mse/{name}" for name in self.observed_operations),
        )
        return BackendCapabilities(_CANDIDATE, ("samples", "grouped_samples"), names)

    def plan(
        self,
        *,
        runs: int = 16,
        samples: int = 32,
        operation_samples: Mapping[str, int] | None = None,
        seed: int = 20260923,
        margin: float = 0.1,
        alpha: float = 0.05,
        max_seconds: float = 180.0,
        max_bytes: int = _MAX_BYTES,
    ) -> RunPlan:
        run_count = _count(runs, name="runs", maximum=256)
        settings = self._settings(samples, operation_samples)
        self._preflight_spin_work(self._counts(settings))
        if type(seed) is not int or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        margin_value = _positive_float(margin, name="margin", maximum=self.cap)
        seconds_value = _positive_float(max_seconds, name="max_seconds", maximum=180)
        if type(max_bytes) is not int or not _MIN_BYTES <= max_bytes <= _MAX_BYTES:
            raise ValueError("max_bytes must be an integer from 65536 through 16777216")

        config = asdict(self.config)
        map_recipe = [asdict(operation) for operation in self.operations]
        corpus = self.documents.to_dict()
        processing = {
            "shift": "inputs=tokens[:-1], targets=tokens[1:]",
            "mask": "explicit boolean per target; default all true",
            "vocabulary": self.config.vocab,
            "boundary": "no shift across documents",
            "metric_version": _METRIC_VERSION,
        }
        source = _identity("sparse-transformers-z1t-source", {"revision": PINNED_SOURCE_REVISION})
        model = _identity(
            "generated-tiny-z1t-parameters",
            {"source": PINNED_SOURCE_REVISION, "config": config, "seed": self.initialization_seed},
        )
        corpus_id = _identity("tiny-z1t-corpus", corpus)
        preprocessing = _identity("teacher-forced-token-loss", processing)
        reference = _identity(
            "tiny-z1t-deterministic-numerical-v1", {"model": model.digest, "inputs": corpus_id.digest}
        )
        candidate = _identity(
            _CANDIDATE,
            {
                "reference": reference.digest,
                "profile_id": self.profile_id,
                "operation_map_recipe": map_recipe,
                "rng_recipe": _RNG_RECIPE,
                "output_precision": "float32 logits / float64 loss",
            },
        )
        cap_hit = MetricSpec(
            "cap_hit_rate",
            "fraction",
            "smaller_is_better",
            "candidate-reference",
            Acceptance("upper", 1.0),
            "bounded_fixed_n",
            run_count,
            "independent_run",
            "fixed_inputs",
            Bounds(0.0, 1.0),
            mandatory=False,
        )
        activation_metrics = tuple(
            MetricSpec(
                f"activation_mse/{name}",
                "squared spin",
                "smaller_is_better",
                "candidate-representation",
                Acceptance("upper", 4.0),
                "bounded_fixed_n",
                run_count,
                "independent_run",
                "fixed_inputs",
                Bounds(0.0, 4.0),
                mandatory=False,
            )
            for name in self.observed_operations
        )
        degradation = MetricSpec(
            "capped_nll_degradation",
            "nats/token",
            "smaller_is_better",
            "candidate-reference",
            Acceptance("upper", margin_value),
            "bounded_fixed_n",
            run_count,
            "independent_run",
            "fixed_inputs",
            Bounds(-self.cap, self.cap),
        )
        case_id = f"{self.documents.name}-corpus"
        precision = {
            "profile_id": self.profile_id,
            "config": config,
            "initialization_seed": self.initialization_seed,
            "corpus": corpus,
            "cap": self.cap,
            "observed_operations": list(self.observed_operations),
            "operation_groups": {name: list(paths) for name, paths in self.operation_groups.items()},
            "source_revision": PINNED_SOURCE_REVISION,
            "rng_recipe": _RNG_RECIPE,
            "metric_version": _METRIC_VERSION,
            "operation_map_recipe": map_recipe,
            "output_precision": "float32 logits / float64 loss",
            "teacher_forcing": processing,
        }
        workload = WorkloadSpec(
            workload_id="tiny-z1t-teacher-forced-v1",
            description="Generated tiny Z1T teacher-forced corpus evaluation; synthetic tokens",
            sources=(source,),
            model_config=model,
            inputs=InputSpec(
                corpus_id,
                preprocessing,
                (
                    InputCase(
                        case_id, self.documents.semantic_digest(), self.documents.name, "complete-corpus"
                    ),
                ),
                sequence_length=max(len(document.inputs) for document in self.documents.documents),
                masks_digest=identity_digest(
                    [
                        {"document_id": doc.document_id, "mask": list(doc.mask or ())}
                        for doc in self.documents.documents
                    ]
                ),
            ),
            operations=(OperationSpec(_MEASUREMENT, (), ()),),
            dtype="float64",
            precision=precision,
            reference=reference,
            candidate=candidate,
            controls=("samples", "grouped_samples"),
            contract=AcceptanceContract((degradation, cap_hit, *activation_metrics), alpha_total=alpha),
            randomization=RandomizationSpec(seed, run_count),
            resources=ResourceBudget(run_count, seconds_value, max_bytes),
            cost_scope=_COST_SCOPE,
            license_refs=("generated-synthetic-tokens", "pinned-z1t-apache-2.0-source"),
        )
        planned = tuple(
            PlannedRun(f"run-{index:04d}", case_id, _MEASUREMENT, self.documents.name, settings)
            for index in range(run_count)
        )
        ids = tuple(run.run_id for run in planned)
        return RunPlan(
            workload,
            planned,
            metric_bindings=(
                MetricBinding("capped_nll_degradation", "capped_nll_degradation", ids, 0.0),
                MetricBinding("cap_hit_rate", "cap_hit_rate", ids, 0.0),
                *(
                    MetricBinding(f"activation_mse/{name}", f"activation_mse/{name}", ids, 0.0)
                    for name in self.observed_operations
                ),
            ),
        )

    def validate_plan(self, plan: RunPlan) -> None:
        if not isinstance(plan, RunPlan):
            raise ValueError("plan must be RunPlan")
        if not plan.runs or not plan.workload.contract.metrics:
            raise ValueError("model plan must have runs and metrics")
        settings = plan.runs[0].settings
        counts = self._counts(settings)
        self._preflight_spin_work(counts)
        grouped = settings.get("grouped_samples", {})
        operation_samples = {
            name: grouped[group]
            for group, names in self.operation_groups.items()
            if group in grouped
            for name in names
        }
        margin = plan.workload.contract.metrics[0].acceptance.upper
        if margin is None:
            raise ValueError("model plan requires an upper acceptance margin")
        expected = self.plan(
            runs=len(plan.runs),
            samples=settings["samples"],
            operation_samples=operation_samples or None,
            seed=plan.workload.randomization.master_seed,
            margin=margin,
            alpha=plan.workload.contract.alpha_total,
            max_seconds=plan.workload.resources.max_seconds,
            max_bytes=plan.workload.resources.max_bytes,
        )
        if record_to_dict(plan) != record_to_dict(expected):
            raise ValueError("model plan differs from the frozen corpus, controls or metric contract")

    def prepare(self, workload: WorkloadSpec) -> None:
        if not isinstance(workload, WorkloadSpec):
            raise ValueError("workload must be WorkloadSpec")
        if not workload.contract.metrics:
            raise ValueError("model workload has no metrics")
        margin = workload.contract.metrics[0].acceptance.upper
        if margin is None:
            raise ValueError("model workload requires an upper acceptance margin")
        expected = self.plan(
            runs=workload.randomization.independent_runs,
            samples=1,
            seed=workload.randomization.master_seed,
            margin=margin,
            alpha=workload.contract.alpha_total,
            max_seconds=workload.resources.max_seconds,
            max_bytes=workload.resources.max_bytes,
        ).workload
        if record_to_dict(workload) != record_to_dict(expected):
            raise ValueError("model workload identity differs from the trusted backend")
        digest = workload.semantic_digest()
        if self._numerical is not None and self._prepared_workload_digest == digest:
            return
        numerical = NumericalZ1T(self.config, seed=self.initialization_seed)
        if numerical.source_identity != f"sparse-transformers:{PINNED_SOURCE_REVISION}:z1t:0.0.1":
            raise ValueError("numerical source revision differs from the frozen model recipe")
        if numerical.operations != self.operations:
            raise ValueError("actual projection map differs from the frozen operation recipe")
        import jax
        import numpy as np

        reference_losses = []
        for document in self.documents.documents:
            logits = np.asarray(jax.device_get(numerical.forward(document.inputs).logits))
            if logits.shape != (len(document.inputs), self.config.vocab) or logits.dtype.name != "float32":
                raise ValueError("numerical reference logits violate frozen shape or precision")
            reference_losses.append(
                language_loss(logits.tolist(), document.targets, mask=document.mask, cap=self.cap)
            )
        self._numerical = numerical
        self._numerical_loss = combine_losses(tuple(reference_losses))
        self._prepared_workload_digest = digest

    def execute(self, run: PlannedRun, randomization: RandomizationIdentity) -> ExecutionResult:
        if self._numerical is None or self._numerical_loss is None or self._prepared_workload_digest is None:
            raise ValueError("backend must be prepared")
        if not isinstance(run, PlannedRun) or not isinstance(randomization, RandomizationIdentity):
            raise ValueError("execute requires a planned run and randomization identity")
        if (run.case_id, run.operation_id, run.purpose) != (
            f"{self.documents.name}-corpus",
            _MEASUREMENT,
            self.documents.name,
        ):
            raise ValueError("run is not for this complete corpus measurement")
        counts = self._counts(run.settings)
        modeled_work = self._preflight_spin_work(counts)
        self._preflight_trace()

        import jax
        import numpy as np

        started = time.perf_counter()
        wrapper = IdealTanhModel(
            self._numerical,
            samples=run.settings["samples"],
            operation_samples={
                name: count for name, count in counts.items() if count != run.settings["samples"]
            },
        )
        if {name: tuple(paths) for name, paths in wrapper.operation_groups.items()} != self.operation_groups:
            raise ValueError("actual profile groups differ from the frozen operation recipe")
        losses = []
        squared: dict[str, float] = {name: 0.0 for name in self.observed_operations}
        elements: dict[str, int] = {name: 0 for name in self.observed_operations}
        for document in self.documents.documents:
            stream = document_randomization(randomization, document.document_id)
            result = wrapper.forward(
                document.inputs,
                stream,
                observe=self.observed_operations,
                retention="trace" if self.observed_operations else "summaries",
                max_trace_bytes=_TRACE_LIMIT,
            )
            logits = np.asarray(jax.device_get(result.logits))
            if logits.shape != (len(document.inputs), self.config.vocab) or logits.dtype.name != "float32":
                raise ValueError("stochastic logits violate frozen shape or precision")
            losses.append(language_loss(logits.tolist(), document.targets, mask=document.mask, cap=self.cap))
            for name in self.observed_operations:
                capture = result.captures[name]
                if capture.field.values is None or capture.output.values is None:
                    raise ValueError("selected activation trace is unavailable")
                field = np.asarray(capture.field.values, dtype=np.float64)
                output = np.asarray(capture.output.values, dtype=np.float64)
                error = output - np.tanh(field)
                squared[name] += float(np.sum(error * error, dtype=np.float64))
                elements[name] += int(output.size)
        candidate_loss = combine_losses(tuple(losses))
        elapsed = time.perf_counter() - started
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("complete evaluation wall time is invalid")

        values = {
            "capped_nll_degradation": candidate_loss.capped_nll - self._numerical_loss.capped_nll,
            "raw_nll": candidate_loss.nll,
            "numerical_raw_nll": self._numerical_loss.nll,
            "capped_nll": candidate_loss.capped_nll,
            "numerical_capped_nll": self._numerical_loss.capped_nll,
            "cap_hit_rate": candidate_loss.cap_hit_rate,
        }
        values.update(
            {f"activation_mse/{name}": squared[name] / elements[name] for name in self.observed_operations}
        )
        observations = tuple(
            Observation(
                name,
                _MEASUREMENT,
                run.case_id,
                run.run_id,
                "float64",
                (),
                (),
                (float(value),),
                units="fraction"
                if name == "cap_hit_rate"
                else "squared spin"
                if name.startswith("activation_mse/")
                else "nats/token",
            )
            for name, value in values.items()
        ) + tuple(
            Observation(
                name,
                _MEASUREMENT,
                run.case_id,
                run.run_id,
                "int64",
                (),
                (),
                (value,),
                units=units,
            )
            for name, value, units in (
                ("valid_tokens", candidate_loss.valid_tokens, "tokens"),
                ("modeled_spin_draws", modeled_work, "draws"),
            )
        )
        costs = (
            CostRecord(
                "sample_work",
                "samples",
                _COST_SCOPE,
                "modeled",
                "available",
                float(modeled_work),
                method="iid-spin-draws-v1",
            ),
            CostRecord(
                "latency",
                "seconds",
                _COST_SCOPE,
                "measured",
                "available",
                elapsed,
                method="perf-counter-synchronized-complete-evaluation-v1",
            ),
            CostRecord(
                "energy",
                "joules",
                _COST_SCOPE,
                "modeled",
                "unavailable",
                reason="physical energy was not measured",
                method="unknown",
            ),
        )
        return ExecutionResult(observations, costs)


def diagnose_operations(
    numerical: NumericalZ1T,
    document: Any,
    randomization: RandomizationIdentity,
    *,
    samples: int = 32,
    operations: Sequence[str],
    joint: Sequence[str] = (),
) -> dict[str, Any]:
    """Replay fixed numerical fields and separately intervene in the full model.

    The replay and interventions share the same document stream. S05 folds in
    operation and draw identities, giving common random variates at a selected
    operation while allowing upstream interventions to change its actual field.
    """
    import jax
    import numpy as np

    from gibbsiq.qualification.adapters.z1t_emulation import sample_iid_tanh
    from gibbsiq.qualification.model_evaluation import TokenDocument

    if not isinstance(numerical, NumericalZ1T):
        raise ValueError("numerical must be a prepared NumericalZ1T")
    if not isinstance(document, TokenDocument):
        raise ValueError("document must be TokenDocument")
    if not isinstance(randomization, RandomizationIdentity):
        raise ValueError("randomization must be RandomizationIdentity")
    count = _count(samples, name="samples", maximum=4096)
    if isinstance(operations, (str, bytes)) or not isinstance(operations, Sequence):
        raise ValueError("operations must be a bounded sequence of projection IDs")
    selected = tuple(operations)
    operation_map = {operation.operation_id: operation for operation in numerical.operations}
    if (
        not 1 <= len(selected) <= 2
        or any(type(name) is not str or name not in operation_map for name in selected)
        or len(set(selected)) != len(selected)
    ):
        raise ValueError("select one or two distinct supported projections")
    if isinstance(joint, (str, bytes)) or not isinstance(joint, Sequence):
        raise ValueError("joint must be a sequence of selected projection IDs")
    joint_names = tuple(joint)
    if (
        len(joint_names) > 2
        or any(type(name) is not str or name not in selected for name in joint_names)
        or len(set(joint_names)) != len(joint_names)
    ):
        raise ValueError("joint must be a distinct subset of selected projections")
    if len(document.inputs) > numerical.config.sequence or any(
        token >= numerical.config.vocab for token in document.tokens
    ):
        raise ValueError("document exceeds the numerical model sequence or vocabulary")
    trace_bytes = (
        4
        * len(document.inputs)
        * sum(
            operation_map[name].input_features + 2 * operation_map[name].output_features for name in selected
        )
    )
    if trace_bytes > _TRACE_LIMIT:
        raise ValueError("selected numerical-boundary trace exceeds 1 MiB")
    for sites in (*((name,) for name in selected), joint_names):
        work = len(document.inputs) * sum(operation_map[name].output_features * count for name in sites)
        if work > _SPIN_WORK_LIMIT:
            raise ValueError("intervention spin work exceeds 8388608 draws")

    stream = document_randomization(randomization, document.document_id)
    captured = numerical.forward(
        document.inputs, observe=selected, retention="trace", max_trace_bytes=_TRACE_LIMIT
    )
    reference_logits = np.asarray(jax.device_get(captured.logits))
    if reference_logits.shape != (len(document.inputs), numerical.config.vocab):
        raise ValueError("numerical logits have the wrong shape")
    reference_loss = language_loss(reference_logits.tolist(), document.targets, mask=document.mask)
    replay: dict[str, dict[str, Any]] = {}
    for name in selected:
        capture = captured.captures[name]
        if capture.field.values is None or capture.output.values is None:
            raise ValueError("selected numerical boundary is unavailable")
        field = np.asarray(capture.field.values)
        representation = np.asarray(capture.output.values, dtype=np.float64)
        sampled = sample_iid_tanh(field, randomization=stream, operation_id=name, samples=count)
        error = np.asarray(jax.device_get(sampled.mean), dtype=np.float64) - representation
        replay[name] = {
            "operation_id": name,
            "provenance": "numerical-boundary-replay",
            "samples": count,
            "elements": int(error.size),
            "mean_error": float(np.mean(error)),
            "mse": float(np.mean(error * error)),
            "analytic_conditional_mean_variance": float(np.mean((1.0 - representation**2) / count)),
        }

    wrapper = IdealTanhModel(numerical, samples=count)

    def evaluate_intervention(selected_operations: tuple[str, ...]) -> dict[str, Any]:
        forward = wrapper.forward(document.inputs, stream, sampled_operations=selected_operations)
        logits = np.asarray(jax.device_get(forward.logits))
        if logits.shape != reference_logits.shape:
            raise ValueError("intervened logits have the wrong shape")
        loss = language_loss(logits.tolist(), document.targets, mask=document.mask)
        return {
            "selected_operations": list(selected_operations),
            "provenance": "actual-intervened-model",
            "raw_nll": loss.nll,
            "capped_nll": loss.capped_nll,
            "raw_nll_degradation": loss.nll - reference_loss.nll,
            "capped_nll_degradation": loss.capped_nll - reference_loss.capped_nll,
            "cap_hit_rate": loss.cap_hit_rate,
            "valid_tokens": loss.valid_tokens,
        }

    one_at_a_time = {name: evaluate_intervention((name,)) for name in selected}
    if not joint_names:
        joint_result = None
    elif len(joint_names) == 1:
        isolated = one_at_a_time[joint_names[0]]
        joint_result = {**isolated, "selected_operations": list(isolated["selected_operations"])}
    else:
        joint_result = evaluate_intervention(joint_names)

    result: dict[str, Any] = {
        "schema": "tiny-model-attribution-v1",
        "profile_id": _PROFILE,
        "document_id": document.document_id,
        "samples": count,
        "cap": 8.0,
        "representation_relation": "R=N by ideal profile",
        "identities": {
            "source": numerical.source_identity,
            "parameters": numerical.parameter_identity,
            "operation_map": numerical.operation_map_identity,
            "document": document.semantic_digest(),
        },
        "randomization": {
            "parent": randomization.digest,
            "document": stream.digest,
            "coupling": "common-document-stream-v1",
            "purpose": "teacher-forced",
        },
        "numerical": {
            "provenance": "deterministic-numerical-model",
            "raw_nll": reference_loss.nll,
            "capped_nll": reference_loss.capped_nll,
            "cap_hit_rate": reference_loss.cap_hit_rate,
            "valid_tokens": reference_loss.valid_tokens,
        },
        "replay": replay,
        "interventions": {
            "one_at_a_time": one_at_a_time,
            "joint": joint_result,
        },
    }
    canonical_json(result)
    return result


__all__ = ["TinyModelBackend", "diagnose_operations", "document_randomization"]
