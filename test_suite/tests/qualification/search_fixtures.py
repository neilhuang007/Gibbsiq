"""Deterministic complete-corpus experiments with planted quality/cost tradeoffs."""

from dataclasses import replace

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
from gibbsiq.qualification.engine import BackendCapabilities, ExecutionResult
from gibbsiq.qualification.model_evaluation import CorpusSplit, SplitManifest, TokenDocument
from gibbsiq.qualification.workflow import qualify


def fixture_identity(name, payload):
    return ArtifactIdentity(name, "1", identity_digest(payload))


def search_plan(*, groups=(), counts=(8, 16, 32), baseline=32, max_jobs=32, method="sum"):
    from gibbsiq.qualification.policy_search import SearchPlan, SearchSpace

    splits = SplitManifest(
        *(
            CorpusSplit(phase, (TokenDocument(phase, phase, tokens),))
            for phase, tokens in zip(("calibration", "development", "evaluation"), ((1, 2), (3, 4), (5, 6)))
        )
    )
    operations = {name: [name + ".projection"] for name in groups}
    recipe = [{"operation_id": name + ".projection"} for name in groups]
    scope = CostScope("synthetic-complete-corpus", ("fixture",), ("physical_energy",))
    objective = CostRecord("sample_work", "samples", scope, "modeled", "available", 0, method=method)
    templates = {}
    for phase in ("calibration", "development", "evaluation"):
        split = getattr(splits, phase)
        corpus = fixture_identity("corpus", split.to_dict())
        workload = WorkloadSpec(
            workload_id="synthetic-tradeoff",
            description="Planted finite table, no physical execution",
            sources=(fixture_identity("source", "finite-table-v1"),),
            model_config=fixture_identity("model", "finite-table-v1"),
            inputs=InputSpec(
                corpus,
                fixture_identity("preprocessing", "identity"),
                (InputCase(phase, split.semantic_digest(), phase, "complete-corpus"),),
            ),
            operations=(OperationSpec("quality", (), ()),),
            dtype="float64",
            precision={
                "profile_id": "finite-table",
                "corpus": split.to_dict(),
                "operation_groups": operations,
                "operation_map_recipe": recipe,
            },
            reference=fixture_identity("reference", corpus.digest),
            candidate=fixture_identity("table-backend", corpus.digest),
            controls=("samples", "grouped_samples") if groups else ("samples",),
            contract=AcceptanceContract(
                (
                    MetricSpec(
                        "error",
                        "absolute error",
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
            randomization=RandomizationSpec(7, 1),
            resources=ResourceBudget(1, 10, 1024 * 1024),
            cost_scope=scope,
            license_refs=("generated-test-fixture",),
        )
        templates[phase] = RunPlan(
            workload,
            (PlannedRun("run", phase, "quality", phase, {"samples": baseline}),),
            metric_bindings=(MetricBinding("error", "error", ("run",)),),
        )
    return SearchPlan(
        space=SearchSpace(counts=counts, baseline=baseline, groups=groups),
        splits=splits,
        templates=templates,
        metric_id="error",
        screening_margin=0.1,
        objective=objective,
        profile=fixture_identity("finite-table", "finite-table-v1"),
        operation_map_digest=identity_digest(recipe),
        max_jobs=max_jobs,
        max_seconds=60,
        max_bytes=16 * 1024 * 1024,
    )


class TableBackend:
    """The table is an independent oracle for testing search, not a model claim."""

    def __init__(self, values, *, method="sum", missing_cost=False):
        self.values = values
        self.method = method
        self.missing_cost = missing_cost

    def capabilities(self):
        return BackendCapabilities("table-backend", ("samples", "grouped_samples"), ("error",))

    def prepare(self, workload):
        self.phase = workload.inputs.cases[0].split
        self.groups = tuple(workload.precision["operation_groups"])
        self.scope = workload.cost_scope

    def execute(self, run, randomization):
        default = run.settings["samples"]
        grouped = run.settings.get("grouped_samples", {})
        effective = tuple(grouped.get(group, default) for group in self.groups) or (default,)
        error = self.values.get((self.phase, effective), self.values.get(effective, 0.4))
        cost = max(effective) if self.method == "maximum" else sum(effective)
        observation = Observation(
            "error",
            run.operation_id,
            run.case_id,
            run.run_id,
            "float64",
            (),
            (),
            (error,),
            units="absolute error",
        )
        costs = (
            ()
            if self.missing_cost
            else (
                CostRecord(
                    "sample_work", "samples", self.scope, "modeled", "available", cost, method=self.method
                ),
            )
        )
        return ExecutionResult((observation,), costs)


def table_evaluator(values, *, method="sum", missing_cost=False, calls=None):
    def evaluate(candidate, phase, run_plan, destination):
        if calls is not None:
            calls.append((phase, candidate, run_plan, destination))
        qualify(
            run_plan,
            backends={"table-backend": TableBackend(values, method=method, missing_cost=missing_cost)},
            destination=destination,
        )

    return evaluate


def global_only(plan):
    return replace(
        plan,
        templates={
            phase: replace(template, workload=replace(template.workload, controls=("samples",)))
            for phase, template in plan.templates.items()
        },
    )
