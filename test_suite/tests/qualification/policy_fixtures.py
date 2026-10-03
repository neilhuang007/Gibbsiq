"""Planned S08 deterministic numerical workloads; restore to the qualification tests."""

from __future__ import annotations

from dataclasses import dataclass

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
from gibbsiq.qualification.model_evaluation import tiny_split_manifest
from gibbsiq.qualification.workflow import qualify


def identity(name, value):
    return ArtifactIdentity(name, "1", identity_digest(value))


SCOPE = CostScope("complete-toy-evaluation", ("attention", "mlp"), ("physical-device",))
PROFILE = identity("deterministic-toy-v1", {"law": "enumerated exact losses"})
MAP_DIGEST = identity_digest({"attention": ["attention"], "mlp": ["mlp"]})


def templates(*, grouped=True):
    """Each scalar is the exact result of one complete deterministic toy case."""
    result = {}
    splits = tiny_split_manifest()
    for phase in ("calibration", "development", "evaluation"):
        split = getattr(splits, phase)
        metric = MetricSpec(
            "loss",
            "loss",
            "smaller_is_better",
            "candidate-reference",
            Acceptance("upper", 0.1),
            "exact",
            1,
            "deterministic",
            "fixed_inputs",
        )
        case_id = phase + "-corpus"
        operation_id = "complete-model-evaluation"
        workload = WorkloadSpec(
            workload_id="deterministic-policy-toy-v1",
            description="Exact scalar toy evaluation for search lifecycle checks",
            sources=(identity("toy-source", {"version": 1}),),
            model_config=identity("toy-model", {"version": 1}),
            inputs=InputSpec(
                identity("toy-corpus", split.to_dict()),
                identity("toy-processing", {}),
                (InputCase(case_id, split.semantic_digest(), phase, "whole-corpus"),),
            ),
            operations=(OperationSpec(operation_id, (), ()),),
            dtype="float64",
            precision={
                "profile_id": PROFILE.identity,
                "corpus": split.to_dict(),
                "operation_groups": {"attention": ["attention"], "mlp": ["mlp"]},
                "operation_map_recipe": {"attention": ["attention"], "mlp": ["mlp"]},
            },
            reference=identity("toy-reference", {"corpus": split.semantic_digest()}),
            candidate=identity("toy-candidate", {"corpus": split.semantic_digest()}),
            controls=("samples", "grouped_samples") if grouped else ("samples",),
            contract=AcceptanceContract((metric,)),
            randomization=RandomizationSpec(7, 1),
            resources=ResourceBudget(1, 10, 1024 * 1024),
            cost_scope=SCOPE,
            license_refs=("generated-fixture",),
        )
        run = PlannedRun("run-0000", case_id, operation_id, phase, {"samples": 32})
        result[phase] = RunPlan(
            workload, (run,), metric_bindings=(MetricBinding("loss", "loss", (run.run_id,)),)
        )
    return result


def search_plan(*, counts=(8, 16, 32), groups=(), **changes):
    from gibbsiq.qualification.policy_search import SearchPlan, SearchSpace

    values = dict(
        space=SearchSpace(counts=counts, baseline=32, groups=groups),
        splits=tiny_split_manifest(),
        templates=templates(),
        metric_id="loss",
        screening_margin=0.1,
        objective=CostRecord(
            "sample_work", "samples", SCOPE, "modeled", "available", 0, method="toy-work-v1"
        ),
        profile=PROFILE,
        operation_map_digest=MAP_DIGEST,
        master_seed=100,
        max_jobs=128,
        max_seconds=120,
        max_bytes=16 * 1024 * 1024,
    )
    values.update(changes)
    return SearchPlan(**values)


@dataclass
class ToyBackend:
    """A known deterministic loss surface; engine still executes and stores it."""

    mode: str
    phase: str

    def capabilities(self):
        return BackendCapabilities("toy-candidate", ("samples", "grouped_samples"), ("loss",))

    def prepare(self, workload):
        pass

    def execute(self, run, randomization):
        groups = run.settings.get("grouped_samples", {})
        attention = groups.get("attention", run.settings["samples"])
        mlp = groups.get("mlp", run.settings["samples"])
        if self.mode == "nonmonotonic":
            loss = {8: 0.4, 16: 0.04, 32: 0.3}[run.settings["samples"]]
        elif self.mode == "maximum":
            loss = 0.02 if max(attention, mlp) >= 32 else 0.3
        elif self.mode == "grouped":
            loss = 0.02 if attention >= 16 and mlp >= 8 else 0.3
        elif self.mode == "overfit":
            loss = 0.02 if attention >= 16 else 0.3
            if self.phase == "evaluation" and attention < 32:
                loss = 0.5
        elif self.mode == "missing_cost":
            loss = 0.02
        else:
            raise ValueError("unknown toy mode")
        work = max(attention, mlp) if self.mode == "maximum" else attention + mlp
        cost = CostRecord(
            "sample_work",
            "samples",
            SCOPE,
            "modeled",
            "unavailable" if self.mode == "missing_cost" else "available",
            None if self.mode == "missing_cost" else work,
            reason="toy cost intentionally unavailable" if self.mode == "missing_cost" else None,
            method="toy-work-v1",
        )
        return ExecutionResult(
            (
                Observation(
                    "loss",
                    run.operation_id,
                    run.case_id,
                    run.run_id,
                    "float64",
                    (),
                    (),
                    (loss,),
                    units="loss",
                ),
            ),
            (cost,),
        )


def execute_toy(mode, phase, plan, destination):
    qualify(plan, backends={"toy-candidate": ToyBackend(mode, phase)}, destination=destination)
