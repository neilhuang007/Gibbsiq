"""Offline negative search: requested sample budgets cannot repair a sign error."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from gibbsiq.qualification.adapters.reference import spin_conditional
from gibbsiq.qualification.contracts import (
    Acceptance,
    AcceptanceContract,
    ArtifactIdentity,
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
from gibbsiq.qualification.engine import BackendCapabilities, ExecutionResult, RandomizationIdentity
from gibbsiq.qualification.model_evaluation import CorpusSplit, SplitManifest, TokenDocument
from gibbsiq.qualification.policy_search import Candidate, SearchPlan, SearchSpace, run_search
from gibbsiq.qualification.workflow import qualify


_BACKEND = "analytic-sign-error-v1"
_METHOD = "requested-iid-budget-proxy-v1"
_SCOPE = CostScope("analytic-conditional-law", ("requested_budget",), ("sampler_execution", "physical_cost"))


def _identity(name: str, value: object) -> ArtifactIdentity:
    return ArtifactIdentity(name, "1", identity_digest(value))


def no_feasible_search_plan() -> SearchPlan:
    """Predeclare three disjoint generated splits and three global budgets."""
    splits = SplitManifest(
        *(
            CorpusSplit(phase, (TokenDocument(phase, phase, tokens),))
            for phase, tokens in zip(("calibration", "development", "evaluation"), ((1, 2), (3, 4), (5, 6)))
        )
    )
    profile = _identity("analytic-spin-law-v1", {"field": "first_token/4", "candidate": "tanh(-field)"})
    templates = {}
    for phase in ("calibration", "development", "evaluation"):
        split = getattr(splits, phase)
        corpus = _identity("synthetic-conditional-corpus", split.to_dict())
        workload = WorkloadSpec(
            workload_id="analytic-sign-error-search-v1",
            description="Exact conditional-law discrepancy; requested budgets do not execute a sampler",
            sources=(_identity("gibbsiq-analytic-fixture", {"version": 1}),),
            model_config=_identity("conditional-law", {"field": "first_token/4"}),
            inputs=InputSpec(
                corpus,
                _identity("synthetic-token-field", {"divisor": 4}),
                (InputCase(phase, split.semantic_digest(), phase, "complete-corpus"),),
            ),
            operations=(OperationSpec("conditional-law", (), ()),),
            dtype="float64",
            precision={
                "profile_id": profile.identity,
                "corpus": split.to_dict(),
                "field_mapping": "first_token/4",
                "operation_groups": {},
                "operation_map_recipe": [],
            },
            reference=_identity("analytic-spin-reference-v1", {"corpus": corpus.digest}),
            candidate=_identity(_BACKEND, {"corpus": corpus.digest, "law": "tanh(-field)"}),
            controls=("samples",),
            contract=AcceptanceContract(
                (
                    MetricSpec(
                        "mean_absolute_error",
                        "spin",
                        "smaller_is_better",
                        "candidate-reference",
                        Acceptance("upper", 0.1),
                        "exact",
                        1,
                        "deterministic",
                        "fixed_inputs",
                    ),
                )
            ),
            randomization=RandomizationSpec(20261002, 1),
            resources=ResourceBudget(1, 10, 1024 * 1024),
            cost_scope=_SCOPE,
            license_refs=("MIT:generated-synthetic-tokens",),
        )
        templates[phase] = RunPlan(
            workload,
            (PlannedRun("run", phase, "conditional-law", phase, {"samples": 32}),),
            metric_bindings=(MetricBinding("mean_absolute_error", "mean_absolute_error", ("run",)),),
        )
    return SearchPlan(
        space=SearchSpace(counts=(8, 16, 32), baseline=32),
        splits=splits,
        templates=templates,
        metric_id="mean_absolute_error",
        screening_margin=0.1,
        objective=CostRecord("sample_work", "samples", _SCOPE, "modeled", "available", 0, method=_METHOD),
        profile=profile,
        operation_map_digest=identity_digest([]),
        master_seed=20261002,
        max_jobs=16,
        max_seconds=30,
        max_bytes=8 * 1024 * 1024,
    )


class AnalyticSignErrorBackend:
    """Compare independent analytic laws; sample count is a modeled request only."""

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(_BACKEND, ("samples",), ("mean_absolute_error",))

    def prepare(self, workload: WorkloadSpec) -> None:
        self.documents = CorpusSplit.from_dict(workload.precision["corpus"]).documents
        self.scope = workload.cost_scope

    def execute(self, run: PlannedRun, randomization: RandomizationIdentity) -> ExecutionResult:
        differences = []
        for document in self.documents:
            field = document.tokens[0] / 4.0
            reference = spin_conditional(field).mean
            candidate = math.tanh(-field)
            differences.append(abs(candidate - reference))
        observation = Observation(
            "mean_absolute_error",
            run.operation_id,
            run.case_id,
            run.run_id,
            "float64",
            (),
            (),
            (math.fsum(differences) / len(differences),),
            units="spin",
        )
        work = CostRecord(
            "sample_work",
            "samples",
            self.scope,
            "modeled",
            "available",
            run.settings["samples"],
            method=_METHOD,
        )
        return ExecutionResult((observation,), (work,))


def _evaluate(candidate: Candidate, phase: str, run_plan: RunPlan, destination: Path) -> None:
    qualify(run_plan, backends={_BACKEND: AnalyticSignErrorBackend()}, destination=destination)


def tune_no_feasible_policy(*, destination: str | Path) -> dict[str, Any]:
    """Execute the frozen offline negative example through ordinary evidence bundles."""
    return run_search(no_feasible_search_plan(), evaluator=_evaluate, destination=destination)


__all__ = ["no_feasible_search_plan", "tune_no_feasible_policy"]
