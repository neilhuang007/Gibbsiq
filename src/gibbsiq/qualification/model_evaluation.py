"""Core records and independent token losses for complete-model evaluation.

This module deliberately has no numerical-backend imports. A document contains
one teacher-forced sequence; its final token is a target, never an input to a
following document.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from gibbsiq.qualification.contracts import _positive_finite, canonical_json, identity_digest
from gibbsiq.qualification.reporting import _cell as cell


def _identifier(value: object, *, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def _fields(value: object, expected: set[str], *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{name} must contain exactly {sorted(expected)}")
    return value


def _sequence(value: object, *, name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence")
    return value


@dataclass(frozen=True, slots=True)
class TokenDocument:
    """One bounded sequence with explicit target selection and source group."""

    document_id: str
    group_id: str
    tokens: tuple[int, ...]
    mask: tuple[bool, ...] | None = None

    def __post_init__(self) -> None:
        _identifier(self.document_id, name="document_id")
        _identifier(self.group_id, name="group_id")
        tokens = tuple(_sequence(self.tokens, name="tokens"))
        if not 2 <= len(tokens) <= 65 or any(type(token) is not int or token < 0 for token in tokens):
            raise ValueError("tokens must contain 2–65 exact nonnegative integers")
        object.__setattr__(self, "tokens", tokens)

        mask = (True,) * (len(tokens) - 1) if self.mask is None else tuple(_sequence(self.mask, name="mask"))
        if len(mask) != len(tokens) - 1 or any(type(selected) is not bool for selected in mask):
            raise ValueError("mask must contain one exact boolean per target")
        if not any(mask):
            raise ValueError("document must have at least one valid target")
        object.__setattr__(self, "mask", mask)

    @property
    def inputs(self) -> tuple[int, ...]:
        return self.tokens[:-1]

    @property
    def targets(self) -> tuple[int, ...]:
        return self.tokens[1:]

    @property
    def content_digest(self) -> str:
        return identity_digest({"tokens": list(self.tokens), "mask": list(self.mask or ())})

    def semantic_digest(self) -> str:
        return identity_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "group_id": self.group_id,
            "tokens": list(self.tokens),
            "mask": list(self.mask or ()),
        }

    @classmethod
    def from_dict(cls, value: object) -> TokenDocument:
        record = _fields(value, {"document_id", "group_id", "tokens", "mask"}, name="document")
        return cls(record["document_id"], record["group_id"], record["tokens"], record["mask"])


@dataclass(frozen=True, slots=True)
class CorpusSplit:
    """A named corpus partition with explicit document membership and order."""

    name: str
    documents: tuple[TokenDocument, ...]

    def __post_init__(self) -> None:
        _identifier(self.name, name="split name")
        documents = tuple(_sequence(self.documents, name="documents"))
        if not 1 <= len(documents) <= 16 or any(not isinstance(doc, TokenDocument) for doc in documents):
            raise ValueError("split must contain 1–16 token documents")
        if len({doc.document_id for doc in documents}) != len(documents):
            raise ValueError("document IDs must be unique within a split")
        object.__setattr__(self, "documents", documents)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "documents": [document.to_dict() for document in self.documents]}

    @classmethod
    def from_dict(cls, value: object) -> CorpusSplit:
        record = _fields(value, {"name", "documents"}, name="split")
        documents = _sequence(record["documents"], name="documents")
        return cls(record["name"], tuple(TokenDocument.from_dict(document) for document in documents))

    def semantic_digest(self) -> str:
        return identity_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SplitManifest:
    """Three explicit, leakage-checked corpus roles."""

    calibration: CorpusSplit
    development: CorpusSplit
    evaluation: CorpusSplit

    def __post_init__(self) -> None:
        splits = (self.calibration, self.development, self.evaluation)
        if any(not isinstance(split, CorpusSplit) for split in splits):
            raise ValueError("manifest entries must be corpus splits")
        if tuple(split.name for split in splits) != ("calibration", "development", "evaluation"):
            raise ValueError("manifest requires calibration, development and evaluation in their named roles")

        document_ids: set[str] = set()
        group_owner: dict[str, str] = {}
        content_owner: dict[str, str] = {}
        sequence_owner: dict[str, str] = {}
        for split in splits:
            for document in split.documents:
                if document.document_id in document_ids:
                    raise ValueError("document ID appears in multiple splits")
                document_ids.add(document.document_id)
                for value, owners, label in (
                    (document.group_id, group_owner, "group"),
                    (document.content_digest, content_owner, "content"),
                    (identity_digest({"tokens": list(document.tokens)}), sequence_owner, "token sequence"),
                ):
                    owner = owners.setdefault(value, split.name)
                    if owner != split.name:
                        raise ValueError(f"{label} appears in multiple splits")

    def to_dict(self) -> dict[str, Any]:
        return {
            "calibration": self.calibration.to_dict(),
            "development": self.development.to_dict(),
            "evaluation": self.evaluation.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: object) -> SplitManifest:
        record = _fields(value, {"calibration", "development", "evaluation"}, name="manifest")
        return cls(
            CorpusSplit.from_dict(record["calibration"]),
            CorpusSplit.from_dict(record["development"]),
            CorpusSplit.from_dict(record["evaluation"]),
        )

    def semantic_digest(self) -> str:
        return identity_digest(self.to_dict())


def tiny_split_manifest() -> SplitManifest:
    """Return the frozen, synthetic three-way example corpus."""
    return SplitManifest(
        CorpusSplit(
            "calibration",
            (
                TokenDocument("calibration-1", "calibration-group-1", (0, 1, 2, 3, 4)),
                TokenDocument("calibration-2", "calibration-group-2", (4, 3, 2, 1)),
            ),
        ),
        CorpusSplit(
            "development",
            (
                TokenDocument("development-1", "development-group-1", (1, 3, 5, 7, 1)),
                TokenDocument("development-2", "development-group-2", (7, 5, 3)),
            ),
        ),
        CorpusSplit(
            "evaluation",
            (
                TokenDocument(
                    "evaluation-1", "evaluation-group-1", (0, 2, 4, 6, 0), (True, True, False, True)
                ),
                TokenDocument("evaluation-2", "evaluation-group-2", (6, 4, 2)),
            ),
        ),
    )


def _cap(value: object) -> float:
    try:
        cap = _positive_finite(value, name="cap")
    except ValueError as error:
        raise ValueError("cap must be finite, positive and at most 128 nats") from error
    if cap > 128:
        raise ValueError("cap must be finite, positive and at most 128 nats")
    return cap


@dataclass(frozen=True, slots=True)
class LossSummary:
    """Additive loss numerators and a valid-token denominator."""

    loss_sum: float
    valid_tokens: int
    capped_loss_sum: float
    cap_hits: int
    cap: float

    def __post_init__(self) -> None:
        if type(self.valid_tokens) is not int or self.valid_tokens < 1:
            raise ValueError("valid_tokens must be a positive integer")
        if type(self.cap_hits) is not int or not 0 <= self.cap_hits <= self.valid_tokens:
            raise ValueError("cap_hits must be between zero and valid_tokens")
        object.__setattr__(self, "cap", _cap(self.cap))
        for name, value in (("loss_sum", self.loss_sum), ("capped_loss_sum", self.capped_loss_sum)):
            if type(value) not in (int, float):
                raise ValueError(f"{name} must be finite and nonnegative")
            try:
                normalized = float(value)
            except OverflowError as error:
                raise ValueError(f"{name} must be finite and nonnegative") from error
            if not math.isfinite(normalized) or normalized < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
            object.__setattr__(self, name, normalized)

        try:
            hit_floor = self.cap_hits * self.cap
            token_ceiling = self.valid_tokens * self.cap
        except OverflowError as error:
            raise ValueError("derived capped-loss bounds must be finite") from error
        if not math.isfinite(hit_floor) or not math.isfinite(token_ceiling):
            raise ValueError("derived capped-loss bounds must be finite")

        # Addition of individually valid token losses can round by a few ULPs.
        # Compare excess directly so a bound near the largest float stays finite.
        if hit_floor > self.capped_loss_sum and hit_floor - self.capped_loss_sum > 2 * math.ulp(hit_floor):
            raise ValueError("capped_loss_sum is below the cap-hit floor")
        for ceiling in (self.loss_sum, token_ceiling):
            if self.capped_loss_sum > ceiling and self.capped_loss_sum - ceiling > 2 * math.ulp(ceiling):
                raise ValueError("capped_loss_sum exceeds a valid upper bound")

    @property
    def nll(self) -> float:
        return self.loss_sum / self.valid_tokens

    @property
    def capped_nll(self) -> float:
        return min(self.cap, self.capped_loss_sum / self.valid_tokens)

    @property
    def cap_hit_rate(self) -> float:
        return self.cap_hits / self.valid_tokens

    @property
    def perplexity(self) -> float | None:
        try:
            value = math.exp(self.nll)
        except OverflowError:
            return None
        return value if math.isfinite(value) else None

    @property
    def perplexity_unavailable_reason(self) -> str | None:
        return None if self.perplexity is not None else "perplexity overflow from raw NLL"


def language_loss(
    logits: Sequence[Sequence[float]],
    targets: Sequence[int],
    *,
    mask: Sequence[bool] | None = None,
    cap: float = 8.0,
) -> LossSummary:
    """Compute stable target NLL independently of a model's training loss."""
    cap = _cap(cap)
    rows = _sequence(logits, name="logits")
    target_values = _sequence(targets, name="targets")
    if not 1 <= len(rows) <= 4096 or len(target_values) != len(rows):
        raise ValueError("logits and targets must have the same 1–4096 row count")
    selected = (True,) * len(rows) if mask is None else _sequence(mask, name="mask")
    if len(selected) != len(rows) or any(type(value) is not bool for value in selected):
        raise ValueError("mask must contain one exact boolean per row")
    if not any(selected):
        raise ValueError("at least one target must be valid")

    width: int | None = None
    raw_losses: list[float] = []
    capped_losses: list[float] = []
    cap_hits = 0
    for row, target, include in zip(rows, target_values, selected):
        entries = _sequence(row, name="logit row")
        if width is None:
            width = len(entries)
            if width < 2 or width * len(rows) > 1_048_576:
                raise ValueError("vocabulary must contain at least two logits within 1048576 total values")
        if len(entries) != width:
            raise ValueError("logit rows must be rectangular")
        if type(target) is not int or not 0 <= target < width:
            raise ValueError("targets must be exact in-range integers")
        values: list[float] = []
        for entry in entries:
            if type(entry) not in (int, float):
                raise ValueError("logits must be finite numbers, not booleans")
            try:
                value = float(entry)
            except OverflowError as error:
                raise ValueError("logits must be finite numbers") from error
            if not math.isfinite(value):
                raise ValueError("logits must be finite numbers")
            values.append(value)
        if not include:
            continue
        maximum = max(values)
        loss = maximum - values[target] + math.log(math.fsum(math.exp(value - maximum) for value in values))
        if not math.isfinite(loss):
            raise ValueError("nonfinite loss arithmetic")
        raw_losses.append(loss)
        capped_losses.append(min(loss, cap))
        cap_hits += loss > cap
    try:
        loss_sum = math.fsum(raw_losses)
        capped_sum = math.fsum(capped_losses)
    except OverflowError as error:
        raise ValueError("nonfinite accumulated loss") from error
    if not math.isfinite(loss_sum) or not math.isfinite(capped_sum):
        raise ValueError("nonfinite accumulated loss")
    return LossSummary(loss_sum, len(raw_losses), capped_sum, cap_hits, cap)


def combine_losses(summaries: Sequence[LossSummary]) -> LossSummary:
    """Combine document losses using valid tokens as the replication weight."""
    values = _sequence(summaries, name="summaries")
    if not values or any(not isinstance(value, LossSummary) for value in values):
        raise ValueError("summaries must contain at least one LossSummary")
    cap = values[0].cap
    if any(value.cap != cap for value in values):
        raise ValueError("all summaries must have the same cap")
    try:
        loss_sum = math.fsum(value.loss_sum for value in values)
        capped_sum = math.fsum(value.capped_loss_sum for value in values)
    except OverflowError as error:
        raise ValueError("nonfinite combined loss") from error
    if not math.isfinite(loss_sum) or not math.isfinite(capped_sum):
        raise ValueError("nonfinite combined loss")
    return LossSummary(
        loss_sum,
        sum(value.valid_tokens for value in values),
        capped_sum,
        sum(value.cap_hits for value in values),
        cap,
    )


def summarize_model_bundle(snapshot: Any) -> dict[str, Any]:
    """Describe inspected model evidence without executing or importing a backend."""
    from gibbsiq.qualification.artifacts import AttemptRecord, BundleSnapshot, record_to_dict

    if not isinstance(snapshot, BundleSnapshot):
        raise ValueError("model summary requires an inspected BundleSnapshot")
    workload = snapshot.plan.workload
    precision = workload.precision
    if (
        workload.candidate.identity != "tiny-z1t-ideal-tanh-v1"
        or precision.get("profile_id") != "ideal-tanh-iid-v1"
    ):
        raise ValueError("bundle is not the declared tiny ideal-tanh model workload")
    observed = precision.get("observed_operations")
    if not isinstance(observed, (list, tuple)) or any(type(name) is not str for name in observed):
        raise ValueError("model observation recipe is missing")
    try:
        cap = _cap(precision.get("cap"))
    except ValueError as error:
        raise ValueError("model cap recipe is invalid") from error
    corpus = CorpusSplit.from_dict(precision.get("corpus"))
    cases = workload.inputs.cases
    if (
        len(cases) != 1
        or cases[0].split != corpus.name
        or cases[0].content_digest != corpus.semantic_digest()
    ):
        raise ValueError("model corpus differs from the frozen input-case identity")
    expected_tokens = sum(sum(document.mask or ()) for document in corpus.documents)
    expected = {
        "capped_nll_degradation",
        "raw_nll",
        "numerical_raw_nll",
        "capped_nll",
        "numerical_capped_nll",
        "cap_hit_rate",
        "valid_tokens",
        "modeled_spin_draws",
        *(f"activation_mse/{name}" for name in observed),
    }
    planned_ids = tuple(run.run_id for run in snapshot.plan.runs)
    complete: dict[str, AttemptRecord] = {}
    attempts = []
    for history_attempt in snapshot.attempts:
        attempts.append(
            {
                "run_id": history_attempt.run_id,
                "attempt_id": history_attempt.attempt_id,
                "execution": history_attempt.execution,
                "reason": history_attempt.reason,
                "retry_of": history_attempt.retry_of,
            }
        )
        if history_attempt.execution == "complete":
            complete[history_attempt.run_id] = history_attempt
    per_run: list[dict[str, Any]] = []
    costs = []
    for run_id in planned_ids:
        attempt = complete.get(run_id)
        if attempt is None:
            continue
        if {observation.name for observation in attempt.observations} != expected:
            raise ValueError(f"complete run {run_id!r} has unexpected model scalar names")
        observations: dict[str, float | int] = {}
        for observation in attempt.observations:
            if observation.shape != () or observation.axes != () or observation.values is None:
                raise ValueError("model summary requires inline scalar observations")
            if observation.dtype != (
                "int64" if observation.name in {"valid_tokens", "modeled_spin_draws"} else "float64"
            ):
                raise ValueError("model scalar precision differs from its declared recipe")
            value = observation.values[0]
            if type(value) not in (int, float):
                raise ValueError("model scalar value must be numerical")
            observations[observation.name] = value
        if observations["valid_tokens"] <= 0 or observations["modeled_spin_draws"] < 0:
            raise ValueError("model count observations are invalid")
        if observations["valid_tokens"] != expected_tokens:
            raise ValueError("valid-token count contradicts the frozen evaluation corpus")
        raw_nll = observations["raw_nll"]
        numerical_raw = observations["numerical_raw_nll"]
        capped_nll = observations["capped_nll"]
        numerical_capped = observations["numerical_capped_nll"]
        if raw_nll < 0 or numerical_raw < 0:
            raise ValueError("raw model NLL must be nonnegative")
        for name, bounded, raw_value in (
            ("capped_nll", capped_nll, raw_nll),
            ("numerical_capped_nll", numerical_capped, numerical_raw),
        ):
            tolerance = 2 * max(math.ulp(bounded), math.ulp(raw_value))
            if not 0 <= bounded <= cap or bounded > raw_value + tolerance:
                raise ValueError(f"{name} contradicts raw NLL or the frozen cap")
        if not 0 <= observations["cap_hit_rate"] <= 1:
            raise ValueError("cap-hit rate lies outside [0,1]")
        for name in observed:
            if not 0 <= observations[f"activation_mse/{name}"] <= 4:
                raise ValueError("activation MSE lies outside [0,4]")
        difference = capped_nll - numerical_capped
        stored_difference = observations["capped_nll_degradation"]
        tolerance = 2 * max(
            math.ulp(capped_nll),
            math.ulp(numerical_capped),
            math.ulp(difference),
            math.ulp(stored_difference),
        )
        if abs(stored_difference - difference) > tolerance:
            raise ValueError("stored capped-NLL degradation contradicts the two capped losses")
        cost_records = [record_to_dict(cost) for cost in attempt.costs]
        per_run.append(
            {
                "run_id": run_id,
                "attempt_id": attempt.attempt_id,
                "observations": observations,
                "costs": cost_records,
            }
        )
        costs.append({"run_id": run_id, "attempt_id": attempt.attempt_id, "records": cost_records})
    missing = [run_id for run_id in planned_ids if run_id not in complete]
    raw = [float(item["observations"]["raw_nll"]) for item in per_run]
    capped = [float(item["observations"]["capped_nll"]) for item in per_run]

    def finite_mean(values: list[float]) -> float | None:
        if not values:
            return None
        try:
            return math.fsum(values) / len(values)
        except OverflowError:
            scale = max(values)
            return scale * (math.fsum(value / scale for value in values) / len(values))

    mean_raw = finite_mean(raw)
    mean_capped = finite_mean(capped)
    perplexity = None
    perplexity_reason = "no complete model runs" if mean_raw is None else None
    if mean_raw is not None:
        try:
            perplexity = math.exp(mean_raw)
        except OverflowError:
            perplexity_reason = "exp(mean raw NLL) overflows binary64"
    report = snapshot.report
    metrics = (
        {"availability": "unavailable", "reason": "stored qualification report unavailable", "results": []}
        if report is None
        else {
            "availability": "available",
            "reason": None,
            "alpha_total": report.contract.alpha_total,
            "results": record_to_dict(report)["metrics"],
        }
    )
    summary = {
        "schema": "tiny-model-summary-v1",
        "execution": snapshot.execution,
        "qualification": snapshot.qualification,
        "payload_validation": snapshot.payload_validation,
        "reason": snapshot.reason,
        "profile_id": precision["profile_id"],
        "split": corpus.name,
        "representation_relation": "R=N by ideal profile",
        "attempts": attempts,
        "per_run": per_run,
        "descriptive": {
            "planned_runs": len(planned_ids),
            "observed_runs": len(per_run),
            "missing_run_ids": missing,
            "mean_raw_nll": mean_raw,
            "mean_capped_nll": mean_capped,
            "perplexity": perplexity,
            "perplexity_unavailable_reason": perplexity_reason,
        },
        "metrics": metrics,
        "costs": costs,
        "observer_overhead": {
            "status": "unavailable",
            "reason": "observer overhead was not measured separately for this S06 workload",
            "timing_scope": "selected activation traces and loss processing are included in measured complete-evaluation wall time",
        },
        "limitations": [
            "Generated random parameters and synthetic tokens; no useful-language claim.",
            "Fixed teacher-forced corpus; raw NLL and perplexity are descriptive without a confidence interval.",
            "Ideal-tanh IID software profile, not physical Z1 execution or an unpublished compiler.",
            "Physical energy was not measured; unavailable costs are not zero.",
        ],
    }
    canonical_json(summary)
    return summary


def render_model_summary(summary: Mapping[str, Any]) -> str:
    """Render only the supplied static summary; do not recompute experiment results."""
    if not isinstance(summary, Mapping) or summary.get("schema") != "tiny-model-summary-v1":
        raise ValueError("render_model_summary requires a tiny-model-summary-v1 record")
    canonical_json(summary)

    descriptive = summary["descriptive"]
    lines = [
        "# Tiny Z1T complete-model evidence",
        "",
        f"Execution: {cell(summary['execution'])}",
        f"Qualification: {cell(summary['qualification'])}",
        f"Payload validation: {cell(summary['payload_validation'])}",
        f"Profile: {cell(summary['profile_id'])}",
        f"Split: {cell(summary['split'])}",
        f"Representation: {cell(summary['representation_relation'])}",
        f"Observed runs: {cell(descriptive['observed_runs'])}/{cell(descriptive['planned_runs'])}",
        f"Mean raw NLL (descriptive): {cell(descriptive['mean_raw_nll'])}",
        f"Mean capped NLL (descriptive): {cell(descriptive['mean_capped_nll'])}",
        f"Perplexity (descriptive): {cell(descriptive['perplexity'])}",
        f"Observer overhead: {cell(summary['observer_overhead']['status'])}; {cell(summary['observer_overhead']['reason'])}.",
        f"Timing scope: {cell(summary['observer_overhead']['timing_scope'])}.",
        "",
        "## Per-run scalar observations and costs",
        "",
    ]
    if descriptive["perplexity_unavailable_reason"] is not None:
        lines.append(f"Perplexity unavailable: {cell(descriptive['perplexity_unavailable_reason'])}")
    if descriptive["missing_run_ids"]:
        lines.append(f"Missing runs: {cell(', '.join(descriptive['missing_run_ids']))}")
    for run in summary["per_run"]:
        lines.extend(["", f"### {cell(run['run_id'])} ({cell(run['attempt_id'])})", ""])
        for name, value in run["observations"].items():
            lines.append(f"- {cell(name)}: {cell(value)}")
        for cost in run["costs"]:
            value = cost["value"] if cost["availability"] == "available" else cost["availability"]
            lines.append(
                f"- {cell(cost['quantity'])} ({cell(cost['provenance'])}): {cell(value)} {cell(cost['units'])}"
                + (f"; {cell(cost['reason'])}" if cost["reason"] else "")
            )
    lines.extend(["", "## Attempts", ""])
    for attempt in summary["attempts"]:
        lines.append(
            f"- {cell(attempt['run_id'])}/{cell(attempt['attempt_id'])}: {cell(attempt['execution'])}"
            + (f"; {cell(attempt['reason'])}" if attempt["reason"] else "")
        )
    lines.extend(["", "## Stored qualification metrics", ""])
    metrics = summary["metrics"]
    if metrics["availability"] == "unavailable":
        lines.append(f"Unavailable: {cell(metrics['reason'])}")
    else:
        for metric in metrics["results"]:
            lines.append(
                f"- {cell(metric['metric_id'])}: {cell(metric['outcome'])}; "
                f"estimate {cell(metric['estimate'])}; interval {cell(metric['interval'])}"
            )
    lines.extend(["", "## Scope and limitations", ""])
    lines.extend(f"- {cell(item)}" for item in summary["limitations"])
    if summary["reason"]:
        lines.append(f"- Evidence reason: {cell(summary['reason'])}")
    return "\n".join(lines) + "\n"
