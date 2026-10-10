"""Explicit, bounded Z1T-0 experiment. Importing this tool never fetches weights."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from functools import partial
from typing import Any

from gibbsiq.qualification._files import atomic_bytes
from gibbsiq.qualification.artifacts import record_to_dict
from gibbsiq.qualification.contracts import (
    Acceptance,
    Bounds,
    MetricSpec,
    canonical_json,
    identity_digest,
)
from gibbsiq.qualification.engine import RandomizationIdentity
from gibbsiq.qualification.model_evaluation import (
    CorpusSplit,
    LossSummary,
    TokenDocument,
    combine_losses,
    language_loss,
)
from gibbsiq.qualification.statistics import evaluate_metric, required_units
from gibbsiq.qualification.timing import TimingSeries, observer_overhead


BUDGETS = (8, 32, 128)
RUNS = 8
CAP = 16.0
MARGIN = 0.5
ALPHA = 0.05 / len(BUDGETS)
OPERATION = "blocks.3.mlp.proj2"
POLICY_OPERATIONS = ("blocks.3.attn.out_proj", "blocks.3.mlp.proj2")
POLICY_SAMPLES = {POLICY_OPERATIONS[0]: 8, POLICY_OPERATIONS[1]: 128}
UNIFORM_SAMPLES = {operation: 68 for operation in POLICY_OPERATIONS}
POLICY_RUNS = 32
POLICY_ALPHA = 0.05 / 3
POLICY_MARGIN = 0.25
MAX_SPIN_WORK = 8_388_608
MAX_FIELD_ELEMENTS = 65_536
TEXTS = (
    "The sun rises in the east every morning.",
    "A glass of water was on the table.",
    "She opened the book and started reading.",
    "Two plus three equals five in ordinary arithmetic.",
)
POLICY_TEXTS = (
    "Clouds gathered quietly above the distant hills.",
    "The mechanic checked every bolt before departure.",
    "Fresh bread cooled beside the kitchen window.",
    "Seven minus four leaves three objects behind.",
)


def assess_study(
    reference: LossSummary,
    unchanged: LossSummary,
    negated: LossSummary,
    candidates: Mapping[int, Sequence[LossSummary]],
) -> dict:
    """Keep exact fixture decisions separate from uncertainty across random runs."""
    if set(candidates) != set(BUDGETS):
        raise ValueError("candidate budgets must match the frozen study")
    all_losses = [reference, unchanged, negated, *(loss for rows in candidates.values() for loss in rows)]
    if any(loss.cap != CAP or loss.valid_tokens != reference.valid_tokens for loss in all_losses):
        raise ValueError("loss summaries must cover the same targets and frozen cap")
    bounds = Bounds(-reference.capped_nll, CAP - reference.capped_nll)

    def evaluate(name: str, rows: Sequence[LossSummary], *, exact: bool) -> dict:
        metric = MetricSpec(
            name,
            "nats/token",
            "smaller_is_better",
            "candidate-minus-numerical",
            Acceptance("upper", MARGIN),
            "exact" if exact else "bounded_fixed_n",
            1 if exact else RUNS,
            "deterministic" if exact else "independent_run",
            "fixed_inputs",
            bounds,
        )
        return record_to_dict(
            evaluate_metric(
                metric,
                [loss.capped_nll - reference.capped_nll for loss in rows],
                alpha=None if exact else ALPHA,
            )
        )

    return {
        "controls": {
            "unchanged": evaluate("unchanged", [unchanged], exact=True),
            "negated_logits": evaluate("negated_logits", [negated], exact=True),
        },
        "candidates": {
            str(budget): evaluate(f"samples-{budget}", candidates[budget], exact=False) for budget in BUDGETS
        },
        "runs_for_half_width_0_5": required_units(bounds, alpha=ALPHA, half_width=0.5),
    }


def assess_policy_study(
    reference: LossSummary,
    heterogeneous: Sequence[LossSummary],
    uniform: Sequence[LossSummary],
) -> dict:
    """Assess the frozen policies without treating correlated tokens as units."""
    if len(heterogeneous) != len(uniform):
        raise ValueError("policy results must contain paired whole-corpus runs")
    rows = [reference, *heterogeneous, *uniform]
    if any(loss.cap != CAP or loss.valid_tokens != reference.valid_tokens for loss in rows):
        raise ValueError("loss summaries must cover the same targets and frozen cap")
    degradation_bounds = Bounds(-reference.capped_nll, CAP - reference.capped_nll)

    def decision(name: str, values: Sequence[float], bounds: Bounds, margin: float) -> dict:
        metric = MetricSpec(
            name,
            "nats/token",
            "smaller_is_better",
            "paired fixed-corpus comparison",
            Acceptance("upper", margin),
            "bounded_fixed_n",
            POLICY_RUNS,
            "independent_run",
            "fixed_inputs",
            bounds,
        )
        return record_to_dict(evaluate_metric(metric, values, alpha=POLICY_ALPHA))

    return {
        "heterogeneous_vs_numerical": decision(
            "heterogeneous-minus-numerical",
            [loss.capped_nll - reference.capped_nll for loss in heterogeneous],
            degradation_bounds,
            MARGIN,
        ),
        "uniform_vs_numerical": decision(
            "uniform-minus-numerical",
            [loss.capped_nll - reference.capped_nll for loss in uniform],
            degradation_bounds,
            MARGIN,
        ),
        "heterogeneous_vs_uniform": decision(
            "heterogeneous-minus-uniform",
            [left.capped_nll - right.capped_nll for left, right in zip(heterogeneous, uniform)],
            Bounds(-CAP, CAP),
            POLICY_MARGIN,
        ),
        "required_runs": _policy_required_runs(),
    }


def _policy_plan(numerical: Any, corpus: CorpusSplit) -> dict:
    operations = {operation.operation_id: operation for operation in numerical.operations}
    if any(name not in operations for name in POLICY_OPERATIONS):
        raise ValueError("checkpoint operation map does not support the frozen policy")
    selected = tuple(operations[name] for name in POLICY_OPERATIONS)
    if any(operation.kind != "tanh_sparse_linear" for operation in selected):
        raise ValueError("frozen policy requires tanh_sparse_linear operations")
    widths = {operation.output_features for operation in selected}
    if len(widths) != 1:
        raise ValueError("frozen policy operations must have equal output widths")
    max_tokens = max(len(document.inputs) for document in corpus.documents)
    corpus_tokens = sum(len(document.inputs) for document in corpus.documents)
    max_field_elements = max_tokens * next(iter(widths))
    if max_field_elements > MAX_FIELD_ELEMENTS:
        raise ValueError("frozen policy exceeds the per-operation field-element cap")

    def work(settings: Mapping[str, int]) -> int:
        return max_tokens * sum(
            operations[name].output_features * settings[name] for name in POLICY_OPERATIONS
        )

    work_per_token = sum(
        operations[name].output_features * POLICY_SAMPLES[name] for name in POLICY_OPERATIONS
    )

    policy_work, uniform_work = work(POLICY_SAMPLES), work(UNIFORM_SAMPLES)
    if policy_work != uniform_work:
        raise ValueError("frozen policy and uniform baseline must have equal modeled spin work")
    if policy_work > MAX_SPIN_WORK:
        raise ValueError("frozen policy exceeds the per-forward spin-work cap")
    return {
        "operations": list(POLICY_OPERATIONS),
        "heterogeneous_samples": dict(POLICY_SAMPLES),
        "uniform_samples": dict(UNIFORM_SAMPLES),
        "max_input_tokens": max_tokens,
        "corpus_input_tokens": corpus_tokens,
        "max_field_elements_per_operation": max_field_elements,
        "field_element_cap": MAX_FIELD_ELEMENTS,
        "modeled_spin_work_per_forward": policy_work,
        "modeled_spin_work_per_corpus": corpus_tokens * work_per_token,
        "spin_work_cap": MAX_SPIN_WORK,
    }


def _policy_required_runs() -> dict[str, int]:
    return {
        "numerical_half_width_0_5": required_units(Bounds(0.0, CAP), alpha=POLICY_ALPHA, half_width=0.5),
        "paired_half_width_0_25": required_units(Bounds(-CAP, CAP), alpha=POLICY_ALPHA, half_width=0.25),
    }


def _save(path: Path, value: Any) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def _loss_record(loss: LossSummary) -> dict:
    return {
        **asdict(loss),
        "nll": loss.nll,
        "capped_nll": loss.capped_nll,
        "perplexity": loss.perplexity,
        "cap_hit_rate": loss.cap_hit_rate,
    }


@dataclass(slots=True)
class _StudyRun:
    report: dict[str, Any]
    result_path: Path
    started: float
    deadline: float

    @classmethod
    def create(
        cls, report: dict[str, Any], output_dir: Path, filename: str, timeout_seconds: float
    ) -> _StudyRun:
        output_dir.mkdir(parents=True, exist_ok=True)
        result_path = output_dir / filename
        if result_path.exists():
            raise FileExistsError("choose a new output directory; prior attempts must be preserved")
        started = time.perf_counter()
        return cls(report, result_path, started, started + timeout_seconds)

    def checkpoint(self) -> None:
        self.report["elapsed_seconds"] = time.perf_counter() - self.started
        self.report["peak_rss_bytes"] = _peak_rss_bytes()
        _save(self.result_path, self.report)

    def check_time(self, message: str) -> None:
        if time.perf_counter() > self.deadline:
            raise TimeoutError(message)

    @staticmethod
    def _transfer_logits(document: TokenDocument, forward: Any) -> tuple[Any, float]:
        import jax
        import numpy as np

        before = time.perf_counter()
        result = forward(document.inputs)
        logits = result.logits if hasattr(result, "logits") else result
        array = np.asarray(jax.device_get(logits))
        return array, time.perf_counter() - before

    def logits(self, document: TokenDocument, forward: Any) -> tuple[Any, float]:
        self.check_time("predeclared experiment time budget exhausted")
        return self._transfer_logits(document, forward)

    def evaluate(self, document: TokenDocument, forward: Any) -> tuple[LossSummary, Any, float, float]:
        self.check_time("predeclared experiment time budget exhausted")
        before = time.perf_counter()
        array, forward_seconds = self._transfer_logits(document, forward)
        loss = language_loss(array.tolist(), document.targets, mask=document.mask, cap=CAP)
        return loss, array, forward_seconds, time.perf_counter() - before

    def record_failure(self, error: Exception) -> None:
        self.report["status"] = "resource_limited" if isinstance(error, TimeoutError) else "failed"
        self.report["error"] = f"{type(error).__name__}: {error}"
        self.checkpoint()


def _independent_nll(direct: Any, document: TokenDocument) -> float:
    import numpy as np
    from scipy.special import logsumexp

    expected = (
        logsumexp(direct.astype(np.float64), axis=1)
        - direct[np.arange(len(document.targets)), np.asarray(document.targets)]
    )
    return float(expected[np.asarray(document.mask)].mean())


def _rotated_timings(
    run: _StudyRun,
    document: TokenDocument,
    methods: Mapping[str, Any],
    *,
    repeats: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, list[float]]]]:
    rows: dict[str, dict[str, list[float]]] = {
        name: {"complete": [], "forward_and_transfer": []} for name in methods
    }
    names = tuple(methods)
    for repetition in range(repeats):
        offset = repetition % len(names)
        for name in names[offset:] + names[:offset]:
            _, _, forward, complete = run.evaluate(document, methods[name])
            rows[name]["complete"].append(complete)
            rows[name]["forward_and_transfer"].append(forward)
    return (
        {
            name: {phase: asdict(TimingSeries.from_durations(values)) for phase, values in phases.items()}
            for name, phases in rows.items()
        },
        rows,
    )


def _randomization_stream(payload: Mapping[str, Any]) -> RandomizationIdentity:
    raw = hashlib.sha256(canonical_json(payload)).digest()
    return RandomizationIdentity(
        "sha256:" + raw.hex(),
        tuple(int.from_bytes(raw[index : index + 4], "big") for index in range(0, 32, 4)),
    )


def _stream(study_digest: str, budget: int, run: int) -> RandomizationIdentity:
    return _randomization_stream(
        {
            "recipe": "z1t0-checkpoint-study-v1",
            "study": study_digest,
            "samples": budget,
            "run": run,
            "master_seed": 20261002,
        }
    )


def _policy_stream(study_digest: str, policy: str, run: int) -> RandomizationIdentity:
    return _randomization_stream(
        {
            "recipe": "z1t0-checkpoint-policy-study-v1",
            "study": study_digest,
            "policy": policy,
            "run": run,
            "master_seed": 20261004,
        }
    )


def _peak_rss_bytes() -> int | None:
    if sys.platform == "linux":
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    return None


def run_study(
    numerical: Any,
    corpus: CorpusSplit,
    output_dir: Path,
    *,
    operation_id: str = OPERATION,
    timeout_seconds: float = 1800,
) -> dict:
    """Evaluate one already-loaded model; keep every completed corpus replicate."""
    import jax.numpy as jnp
    import numpy as np

    from gibbsiq.qualification.adapters.model_workload import document_randomization
    from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

    study_digest = identity_digest(
        {
            "corpus": corpus.to_dict(),
            "parameters": numerical.parameter_identity,
            "operation": operation_id,
            "budgets": BUDGETS,
            "runs": RUNS,
            "cap": CAP,
            "margin": MARGIN,
            "alpha_per_comparison": ALPHA,
        }
    )
    report: dict[str, Any] = {
        "status": "running",
        "study_digest": study_digest,
        "corpus": corpus.to_dict(),
        "parameter_identity": numerical.parameter_identity,
        "source_identity": numerical.source_identity,
        "operation": operation_id,
        "baseline_documents": [],
        "runs": [],
        "timings": {},
        "scope": "fixed inputs; full vocabulary head; one sampled projection; CPU software only",
    }

    study = _StudyRun.create(report, output_dir, "results.json", timeout_seconds)

    candidates: dict[int, list[LossSummary]] = {budget: [] for budget in BUDGETS}
    try:
        # The same complete logits feed an independent vectorized loss oracle.
        reference_losses, observed_losses, negated_losses = [], [], []
        for document in corpus.documents:
            reference, direct, cold_seconds, complete_seconds = study.evaluate(
                document,
                lambda tokens: numerical.model(jnp.asarray(tokens, dtype=jnp.int32)),
            )
            expected_nll = _independent_nll(direct, document)
            if not math.isclose(reference.nll, expected_nll, rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("independent full-vocabulary NLL oracle disagrees")
            observed, changed, _, _ = study.evaluate(
                document,
                lambda tokens: numerical.forward(tokens, observe=(operation_id,)),
            )
            if not np.allclose(direct, changed, rtol=1e-5, atol=1e-4):
                raise ValueError("observed traversal differs from the official forward")
            negated = language_loss((-direct).tolist(), document.targets, mask=document.mask, cap=CAP)
            reference_losses.append(reference)
            observed_losses.append(observed)
            negated_losses.append(negated)
            report["baseline_documents"].append(
                {
                    "document_id": document.document_id,
                    "loss": _loss_record(reference),
                    "negated_loss": _loss_record(negated),
                    "independent_nll": expected_nll,
                    "traversal_max_abs_difference": float(np.max(np.abs(direct - changed))),
                    "first_forward_seconds": cold_seconds,
                    "first_complete_seconds": complete_seconds,
                    "logit_shape": list(direct.shape),
                }
            )
            study.checkpoint()
        reference = combine_losses(reference_losses)
        unchanged = combine_losses(observed_losses)
        negated = combine_losses(negated_losses)
        report["numerical"] = _loss_record(reference)
        report["negated_logits"] = _loss_record(negated)
        report["decisions"] = assess_study(reference, unchanged, negated, candidates)
        study.checkpoint()

        # Rotate timing order to reduce systematic warm/cache ordering effects.
        methods = {
            "direct": lambda tokens: numerical.model(jnp.asarray(tokens, dtype=jnp.int32)),
            "wrapper": numerical.forward,
            "observed": lambda tokens: numerical.forward(tokens, observe=(operation_id,)),
        }
        timing_summary, _ = _rotated_timings(study, corpus.documents[0], methods, repeats=3)
        report["timings"] = {
            name: {**summary, "document_id": corpus.documents[0].document_id}
            for name, summary in timing_summary.items()
        }
        study.checkpoint()

        for budget in BUDGETS:
            candidate = IdealTanhModel(numerical, samples=budget)
            for run in range(RUNS):
                parent = _stream(study_digest, budget, run)
                losses, complete_seconds, forward_seconds = [], 0.0, 0.0
                for document in corpus.documents:
                    rng = document_randomization(parent, document.document_id)
                    loss, logits, model_time, total_time = study.evaluate(
                        document,
                        partial(
                            candidate.forward,
                            randomization=rng,
                            sampled_operations=(operation_id,),
                        ),
                    )
                    losses.append(loss)
                    complete_seconds += total_time
                    forward_seconds += model_time
                    # A duplicate stream is ONLY a replay check, never an additional replicate.
                    if run == 0 and document == corpus.documents[0]:
                        replay, _ = study.logits(
                            document,
                            partial(
                                candidate.forward,
                                randomization=rng,
                                sampled_operations=(operation_id,),
                            ),
                        )
                        replay_equal = np.array_equal(logits, replay)
                        if not replay_equal:
                            raise ValueError("stochastic checkpoint replay changed logits")
                combined = combine_losses(losses)
                candidates[budget].append(combined)
                report["runs"].append(
                    {
                        "samples": budget,
                        "run": run,
                        "randomization_digest": parent.digest,
                        "loss": _loss_record(combined),
                        "complete_seconds": complete_seconds,
                        "forward_and_transfer_seconds": forward_seconds,
                        "replay_checked": run == 0,
                    }
                )
                report["decisions"] = assess_study(reference, unchanged, negated, candidates)
                print(
                    json.dumps(
                        {"samples": budget, "run": run, "nll": combined.nll, "seconds": complete_seconds}
                    ),
                    flush=True,
                )
                study.checkpoint()
        report["status"] = "complete"
    except Exception as error:
        study.record_failure(error)
        raise
    study.checkpoint()
    return report


def run_policy_study(
    numerical: Any,
    corpus: CorpusSplit,
    output_dir: Path,
    *,
    timeout_seconds: float = 1800,
) -> dict:
    """Run the frozen equal-work heterogeneous-policy comparison."""
    import jax.numpy as jnp
    import numpy as np

    from gibbsiq.qualification.adapters.model_workload import document_randomization
    from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

    plan = _policy_plan(numerical, corpus)
    study_digest = identity_digest(
        {
            "corpus": corpus.to_dict(),
            "parameters": numerical.parameter_identity,
            "plan": plan,
            "runs": POLICY_RUNS,
            "cap": CAP,
            "numerical_margin": MARGIN,
            "paired_margin": POLICY_MARGIN,
            "alpha_per_comparison": POLICY_ALPHA,
        }
    )
    report: dict[str, Any] = {
        "status": "running",
        "study_digest": study_digest,
        "corpus": corpus.to_dict(),
        "parameter_identity": numerical.parameter_identity,
        "source_identity": numerical.source_identity,
        "plan": plan,
        "baseline_documents": [],
        "runs": [],
        "randomization_recipe": {
            "root": "sha256(canonical recipe, study digest, policy, run, master seed 20261004)",
            "document": "document_randomization(root, document_id)",
        },
        "scope": (
            "fresh fixed inputs; full vocabulary model head included; two sampled final-block "
            "projections; CPU software only; energy and temperature unavailable"
        ),
    }

    study = _StudyRun.create(report, output_dir, "policy-results.json", timeout_seconds)

    heterogeneous_rows: list[LossSummary] = []
    uniform_rows: list[LossSummary] = []
    try:
        reference_rows = []
        for document in corpus.documents:
            reference, direct, direct_forward_seconds, direct_complete_seconds = study.evaluate(
                document,
                lambda tokens: numerical.model(jnp.asarray(tokens, dtype=jnp.int32)),
            )
            expected_nll = _independent_nll(direct, document)
            if not math.isclose(reference.nll, expected_nll, rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("independent full-vocabulary NLL oracle disagrees")
            _, changed, observed_forward_seconds, observed_complete_seconds = study.evaluate(
                document,
                lambda tokens: numerical.forward(tokens, observe=POLICY_OPERATIONS),
            )
            if not np.allclose(direct, changed, rtol=1e-5, atol=1e-4):
                raise ValueError("observed traversal differs from the official forward")
            reference_rows.append(reference)
            report["baseline_documents"].append(
                {
                    "document_id": document.document_id,
                    "loss": _loss_record(reference),
                    "independent_nll": expected_nll,
                    "first_direct_forward_and_transfer_seconds": direct_forward_seconds,
                    "first_direct_complete_seconds": direct_complete_seconds,
                    "first_observed_forward_and_transfer_seconds": observed_forward_seconds,
                    "first_observed_complete_seconds": observed_complete_seconds,
                    "traversal_max_abs_difference": float(np.max(np.abs(direct - changed))),
                    "logit_shape": list(direct.shape),
                }
            )
            study.checkpoint()
        reference = combine_losses(reference_rows)
        report["numerical"] = _loss_record(reference)
        report["decisions"] = assess_policy_study(reference, heterogeneous_rows, uniform_rows)
        study.checkpoint()

        methods = {
            "direct": lambda tokens: numerical.model(jnp.asarray(tokens, dtype=jnp.int32)),
            "wrapper": numerical.forward,
            "observed": lambda tokens: numerical.forward(tokens, observe=POLICY_OPERATIONS),
        }
        report["warmed_timings"], timing_rows = _rotated_timings(
            study, corpus.documents[0], methods, repeats=5
        )
        report["observer_overhead"] = asdict(
            observer_overhead(
                timing_rows["wrapper"]["forward_and_transfer"],
                timing_rows["observed"]["forward_and_transfer"],
            )
        )
        study.checkpoint()

        candidates = {
            "heterogeneous": IdealTanhModel(numerical, samples=1, operation_samples=POLICY_SAMPLES),
            "uniform": IdealTanhModel(numerical, samples=1, operation_samples=UNIFORM_SAMPLES),
        }
        for run in range(POLICY_RUNS):
            order = ("heterogeneous", "uniform") if run % 2 == 0 else ("uniform", "heterogeneous")
            for execution_order, policy_name in enumerate(order):
                parent = _policy_stream(study_digest, policy_name, run)
                losses, forward_elapsed, elapsed = [], 0.0, 0.0
                for document_index, document in enumerate(corpus.documents):
                    rng = document_randomization(parent, document.document_id)
                    loss, logits, forward_seconds, complete_seconds = study.evaluate(
                        document,
                        partial(
                            candidates[policy_name].forward,
                            randomization=rng,
                            sampled_operations=POLICY_OPERATIONS,
                        ),
                    )
                    losses.append(loss)
                    forward_elapsed += forward_seconds
                    elapsed += complete_seconds
                    if run == 0 and document_index == 0:
                        replay_logits, _ = study.logits(
                            document,
                            partial(
                                candidates[policy_name].forward,
                                randomization=rng,
                                sampled_operations=POLICY_OPERATIONS,
                            ),
                        )
                        if not np.array_equal(logits, replay_logits):
                            raise ValueError("stochastic checkpoint policy replay changed logits")
                combined = combine_losses(losses)
                (heterogeneous_rows if policy_name == "heterogeneous" else uniform_rows).append(combined)
                report["runs"].append(
                    {
                        "policy": policy_name,
                        "run": run,
                        "execution_order": execution_order,
                        "randomization_digest": parent.digest,
                        "loss": _loss_record(combined),
                        "forward_and_transfer_seconds": forward_elapsed,
                        "forward_transfer_and_loss_seconds": elapsed,
                        "replay_checked": run == 0,
                    }
                )
                print(json.dumps({"policy": policy_name, "run": run, "nll": combined.nll}), flush=True)
                study.checkpoint()
            report["decisions"] = assess_policy_study(reference, heterogeneous_rows, uniform_rows)
            study.checkpoint()
        report["status"] = "complete"
    except Exception as error:
        study.record_failure(error)
        raise
    study.checkpoint()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="explicit local pinned model.eqx")
    parser.add_argument("output", type=Path, help="new experiment evidence directory")
    parser.add_argument(
        "--policy-study",
        action="store_true",
        help="run the frozen heterogeneous-policy versus uniform-baseline study",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import tiktoken

    tokenizer = tiktoken.get_encoding("gpt2")
    texts = POLICY_TEXTS if args.policy_study else TEXTS
    documents = tuple(
        TokenDocument(
            f"authored-{index}", f"authored-group-{index}", tuple(tokenizer.encode_ordinary(text)[:5])
        )
        for index, text in enumerate(texts)
    )
    if any(len(doc.inputs) != 4 for doc in documents):
        raise ValueError("frozen study needs exactly four input tokens per document")
    corpus = CorpusSplit("evaluation", documents)
    protocol: dict[str, Any] = {
        "recipe": ("z1t0-checkpoint-policy-study-v1" if args.policy_study else "z1t0-checkpoint-study-v1"),
        "texts": texts,
        "corpus": corpus.to_dict(),
        "input_scope": "authored before inference; training membership unknown; no implicit EOT",
        "tokenizer": {"encoding": "gpt2", "version": importlib.metadata.version("tiktoken")},
        "cap_nats": CAP,
        "degradation_margin_nats": MARGIN,
        "inference_seconds_limit": 1800,
        "memory_limit_bytes": 16 * 1024**3,
        "cpu_quota": 4,
        "logit_equality_tolerance": {"rtol": 1e-5, "atol": 1e-4},
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("gibbsiq", "jax", "jaxlib", "equinox", "numpy", "scipy", "z1t")
            },
            "JAX_PLATFORMS": os.environ.get("JAX_PLATFORMS"),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
        },
    }
    if args.policy_study:
        protocol.update(
            {
                "policies": {
                    "heterogeneous": POLICY_SAMPLES,
                    "uniform": UNIFORM_SAMPLES,
                },
                "operations": POLICY_OPERATIONS,
                "independent_paired_corpus_runs": POLICY_RUNS,
                "paired_degradation_margin_nats": POLICY_MARGIN,
                "alpha_per_comparison": POLICY_ALPHA,
                "required_runs": _policy_required_runs(),
                "resource_caps": {
                    "field_elements_per_operation": MAX_FIELD_ELEMENTS,
                    "spin_work_per_forward": MAX_SPIN_WORK,
                },
                "randomization": "independent policy/document streams; paired by corpus replicate",
                "execution_order": "counterbalanced by replicate parity",
                "cost_objective": "modeled spin work; policies have equal work",
                "unavailable_costs": ["energy", "temperature", "physical-device latency"],
            }
        )
    else:
        protocol.update(
            {
                "budgets": BUDGETS,
                "independent_corpus_runs_per_budget": RUNS,
                "operation": OPERATION,
                "alpha_per_comparison": ALPHA,
                "fixed_policy": "32 draws at last MLP projection; 8 and 128 are separately assessed comparisons",
                "timing_scope": (
                    "three rotated warmed repeats on first document; all stochastic corpus runs timed"
                ),
            }
        )
    _save(args.output / "protocol.json", protocol)
    from gibbsiq.qualification.adapters.z1t_checkpoint import load_z1t_checkpoint
    import jax
    import numpy as np

    before = time.perf_counter()
    numerical = load_z1t_checkpoint(args.checkpoint)
    load_seconds = time.perf_counter() - before
    before = time.perf_counter()
    smoke = np.asarray(jax.device_get(numerical.forward([documents[0].tokens[0]]).logits))
    if smoke.shape != (1, 50257) or not np.isfinite(smoke).all():
        raise ValueError("one-token full-head smoke failed")
    _save(
        args.output / "load-and-smoke.json",
        {
            "load_seconds": load_seconds,
            "first_one_token_seconds": time.perf_counter() - before,
            "peak_rss_bytes": _peak_rss_bytes(),
            "shape": list(smoke.shape),
            "finite": True,
        },
    )
    print("Loaded checkpoint; one-token full-head smoke passed", flush=True)
    if args.policy_study:
        run_policy_study(numerical, corpus, args.output)
    else:
        run_study(numerical, corpus, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
