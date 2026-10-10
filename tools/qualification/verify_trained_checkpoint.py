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
from dataclasses import asdict
from functools import partial
from typing import Any

from gibbsiq.qualification._files import atomic_bytes
from gibbsiq.qualification.artifacts import record_to_dict
from gibbsiq.qualification.contracts import Acceptance, Bounds, MetricSpec, canonical_json
from gibbsiq.qualification.engine import RandomizationIdentity
from gibbsiq.qualification.model_evaluation import (
    CorpusSplit,
    LossSummary,
    TokenDocument,
    combine_losses,
    language_loss,
)
from gibbsiq.qualification.statistics import evaluate_metric, required_units
from gibbsiq.qualification.timing import TimingSeries


BUDGETS = (8, 32, 128)
RUNS = 8
CAP = 16.0
MARGIN = 0.5
ALPHA = 0.05 / len(BUDGETS)
OPERATION = "blocks.3.mlp.proj2"
TEXTS = (
    "The sun rises in the east every morning.",
    "A glass of water was on the table.",
    "She opened the book and started reading.",
    "Two plus three equals five in ordinary arithmetic.",
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


def _stream(study_digest: str, budget: int, run: int) -> RandomizationIdentity:
    raw = hashlib.sha256(
        canonical_json(
            {
                "recipe": "z1t0-checkpoint-study-v1",
                "study": study_digest,
                "samples": budget,
                "run": run,
                "master_seed": 20261002,
            }
        )
    ).digest()
    return RandomizationIdentity(
        "sha256:" + raw.hex(),
        tuple(int.from_bytes(raw[index : index + 4], "big") for index in range(0, 32, 4)),
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
    import jax
    import jax.numpy as jnp
    import numpy as np
    from scipy.special import logsumexp

    from gibbsiq.qualification.adapters.model_workload import document_randomization
    from gibbsiq.qualification.adapters.z1t_emulation import IdealTanhModel

    started = time.perf_counter()
    deadline = started + timeout_seconds
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "results.json"
    if result_path.exists():
        raise FileExistsError("choose a new output directory; prior attempts must be preserved")
    study_digest = (
        "sha256:"
        + hashlib.sha256(
            canonical_json(
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
        ).hexdigest()
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

    def checkpoint() -> None:
        report["elapsed_seconds"] = time.perf_counter() - started
        report["peak_rss_bytes"] = _peak_rss_bytes()
        _save(result_path, report)

    def check_time() -> None:
        if time.perf_counter() > deadline:
            raise TimeoutError("predeclared experiment time budget exhausted")

    def evaluate(document: TokenDocument, forward: Any) -> tuple:
        check_time()
        before = time.perf_counter()
        result = forward(document.inputs)
        logits = result.logits if hasattr(result, "logits") else result
        array = np.asarray(jax.device_get(logits))
        forward_seconds = time.perf_counter() - before
        loss = language_loss(array.tolist(), document.targets, mask=document.mask, cap=CAP)
        return loss, array, forward_seconds, time.perf_counter() - before

    candidates: dict[int, list[LossSummary]] = {budget: [] for budget in BUDGETS}
    try:
        # The same complete logits feed an independent vectorized loss oracle.
        reference_losses, observed_losses, negated_losses = [], [], []
        for document in corpus.documents:
            reference, direct, cold_seconds, complete_seconds = evaluate(
                document,
                lambda tokens: numerical.model(jnp.asarray(tokens, dtype=jnp.int32)),
            )
            expected = (
                logsumexp(direct.astype(np.float64), axis=1)
                - direct[np.arange(len(document.targets)), np.asarray(document.targets)]
            )
            expected_nll = float(expected[np.asarray(document.mask)].mean())
            if not math.isclose(reference.nll, expected_nll, rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("independent full-vocabulary NLL oracle disagrees")
            observed, changed, _, _ = evaluate(
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
            checkpoint()
        reference = combine_losses(reference_losses)
        unchanged = combine_losses(observed_losses)
        negated = combine_losses(negated_losses)
        report["numerical"] = _loss_record(reference)
        report["negated_logits"] = _loss_record(negated)
        report["decisions"] = assess_study(reference, unchanged, negated, candidates)
        checkpoint()

        # Rotate timing order to reduce systematic warm/cache ordering effects.
        methods = {
            "direct": lambda tokens: numerical.model(jnp.asarray(tokens, dtype=jnp.int32)),
            "wrapper": numerical.forward,
            "observed": lambda tokens: numerical.forward(tokens, observe=(operation_id,)),
        }
        timings: dict[str, dict[str, list[float]]] = {
            name: {"complete": [], "forward_and_transfer": []} for name in methods
        }
        names = tuple(methods)
        for repetition in range(3):
            for name in names[repetition:] + names[:repetition]:
                _, _, forward, complete = evaluate(corpus.documents[0], methods[name])
                timings[name]["complete"].append(complete)
                timings[name]["forward_and_transfer"].append(forward)
        report["timings"] = {
            name: {
                "complete": asdict(TimingSeries.from_durations(timings[name]["complete"])),
                "forward_and_transfer": asdict(
                    TimingSeries.from_durations(timings[name]["forward_and_transfer"])
                ),
                "document_id": corpus.documents[0].document_id,
            }
            for name in names
        }
        checkpoint()

        for budget in BUDGETS:
            candidate = IdealTanhModel(numerical, samples=budget)
            for run in range(RUNS):
                parent = _stream(study_digest, budget, run)
                losses, complete_seconds, forward_seconds = [], 0.0, 0.0
                for document in corpus.documents:
                    rng = document_randomization(parent, document.document_id)
                    loss, logits, model_time, total_time = evaluate(
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
                        replay = candidate.forward(document.inputs, rng, sampled_operations=(operation_id,))
                        replay_equal = np.array_equal(logits, np.asarray(jax.device_get(replay.logits)))
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
                checkpoint()
        report["status"] = "complete"
    except Exception as error:
        report["status"] = "resource_limited" if isinstance(error, TimeoutError) else "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        checkpoint()
        raise
    checkpoint()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="explicit local pinned model.eqx")
    parser.add_argument("output", type=Path, help="new experiment evidence directory")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    import tiktoken

    tokenizer = tiktoken.get_encoding("gpt2")
    documents = tuple(
        TokenDocument(
            f"authored-{index}", f"authored-group-{index}", tuple(tokenizer.encode_ordinary(text)[:5])
        )
        for index, text in enumerate(TEXTS)
    )
    if any(len(doc.inputs) != 4 for doc in documents):
        raise ValueError("frozen study needs exactly four input tokens per document")
    corpus = CorpusSplit("evaluation", documents)
    protocol = {
        "recipe": "z1t0-checkpoint-study-v1",
        "texts": TEXTS,
        "corpus": corpus.to_dict(),
        "input_scope": "authored before inference; training membership unknown; no implicit EOT",
        "tokenizer": {"encoding": "gpt2", "version": importlib.metadata.version("tiktoken")},
        "budgets": BUDGETS,
        "independent_corpus_runs_per_budget": RUNS,
        "operation": OPERATION,
        "cap_nats": CAP,
        "degradation_margin_nats": MARGIN,
        "alpha_per_comparison": ALPHA,
        "fixed_policy": "32 draws at last MLP projection; 8 and 128 are separately assessed comparisons",
        "inference_seconds_limit": 1800,
        "memory_limit_bytes": 16 * 1024**3,
        "cpu_quota": 4,
        "logit_equality_tolerance": {"rtol": 1e-5, "atol": 1e-4},
        "timing_scope": "three rotated warmed repeats on first document; all stochastic corpus runs timed",
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
    run_study(numerical, corpus, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
