"""Frozen S08 search bridge for the generated tiny Z1T workload."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from gibbsiq.qualification.adapters.model_workload import TinyModelBackend
from gibbsiq.qualification.contracts import ArtifactIdentity, CostRecord, identity_digest
from gibbsiq.qualification.model_evaluation import CorpusSplit, SplitManifest, tiny_split_manifest
from gibbsiq.qualification.policy_search import SearchPlan, SearchSpace, run_search
from gibbsiq.qualification.profiles import get_profile
from gibbsiq.qualification.workflow import qualify


_PROFILE_ID = "ideal-tanh-iid-v1"
_GROUPS = ("attention", "mlp")


def _backend(split: CorpusSplit, plan=None) -> TinyModelBackend:
    if plan is None:
        return TinyModelBackend(split, initialization_seed=17, profile_id=_PROFILE_ID, cap=8.0)
    backend = TinyModelBackend.from_plan(plan)
    if backend.documents != split:
        raise ValueError("reconstructed backend corpus differs from the selected search split")
    return backend


def tiny_model_search_plan(*, max_seconds: float = 600, max_bytes: int = 67_108_864) -> SearchPlan:
    """Construct the predeclared three-split tiny-model search plan."""
    splits = tiny_split_manifest()
    templates = {}
    for phase, runs, seed in (
        ("calibration", 2, 20260924),
        ("development", 4, 20260925),
        ("evaluation", 16, 20260926),
    ):
        templates[phase] = _backend(getattr(splits, phase)).plan(
            runs=runs,
            samples=128,
            seed=seed,
            margin=0.1,
            alpha=0.05,
            max_seconds=min(180.0, float(max_seconds)),
            max_bytes=16 * 1024 * 1024,
        )
    calibration = templates["calibration"].workload
    profile = get_profile(_PROFILE_ID)
    map_recipe = calibration.precision["operation_map_recipe"]
    objective = CostRecord(
        "sample_work",
        "samples",
        calibration.cost_scope,
        "modeled",
        "available",
        0.0,
        method="iid-spin-draws-v1",
    )
    return SearchPlan(
        SearchSpace(groups=_GROUPS),
        splits,
        templates,
        "capped_nll_degradation",
        0.1,
        objective,
        ArtifactIdentity(_PROFILE_ID, "1", identity_digest(asdict(profile))),
        identity_digest(map_recipe),
        max_seconds=max_seconds,
        max_bytes=max_bytes,
    )


def _validate_builtin(plan: SearchPlan) -> None:
    expected = tiny_model_search_plan(max_seconds=plan.max_seconds, max_bytes=plan.max_bytes)
    if plan.to_dict() != expected.to_dict():
        raise ValueError("plan is not the validated built-in tiny-model search recipe")


def tune_tiny_model(*, destination: str | Path, plan: SearchPlan | None = None) -> dict[str, object]:
    """Execute the built-in bounded search through supervised qualification."""
    selected_plan = tiny_model_search_plan() if plan is None else plan
    if not isinstance(selected_plan, SearchPlan):
        raise ValueError("plan must be SearchPlan")
    _validate_builtin(selected_plan)
    splits: SplitManifest = selected_plan.splits

    def evaluate(candidate, phase, run_plan, bundle):
        backend = _backend(getattr(splits, phase), run_plan)
        qualify(
            run_plan,
            backends={run_plan.workload.candidate.identity: backend},
            destination=bundle,
        )

    return run_search(selected_plan, evaluator=evaluate, destination=destination)


__all__ = ["tiny_model_search_plan", "tune_tiny_model"]
