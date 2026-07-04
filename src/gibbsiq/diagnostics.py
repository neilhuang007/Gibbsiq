"""Sampler-health diagnostics for THRML-backed optimization runs (Stage 3).

Every metric here is audited in ``reference/08-evaluation/equation-audit.md``
(EVAL-EQ-007, EVAL-EQ-008, EVAL-EQ-011, EVAL-EQ-012, EVAL-EQ-013) and computed
with the standard library only. The ESS and split R-hat internals are
algorithm-step ports of arviz v0.21.0 ``_ess`` / ``_rhat`` / ``_split_chains``
/ ``_rhat_rank`` (Vehtari et al. 2021 semantics) so golden fixtures cross-check
against arviz to 1e-9 (1e-8 for the rank-normalized variant, whose stdlib
normal quantile differs from scipy's below that), with one audited deviation:
degenerate inputs (constant traces, insufficient draws) return explicit status
strings instead of arviz's NaN or array-size returns.
Non-finite energy values raise ``ValueError`` at the input boundary
(EVAL-EQ-007 non-finite input rule); statuses cover finite inputs only.

Stationarity contract: these estimators assume the recorded draws target a
fixed distribution. The THRML runtime guarantees this by construction — beta
ladders anneal only during warmup and every recorded read is collected at
constant ``beta``. When in-sampling schedules land (parallel tempering), the
metrics must be computed per constant-beta segment.

Cost: the Geyer scan is O(num_chains * num_draws * tau) in pure Python.
Well-mixed traces terminate the scan after a handful of lags; only a genuinely
stuck sampler (tau comparable to the trace length) approaches the quadratic
worst case.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from operator import mul
from statistics import NormalDist, median
from typing import Any

from gibbsiq.model import Variable, finite_float

STATUS_OK = "ok"
STATUS_CONSTANT_TRACE = "constant_trace"
STATUS_UNDEFINED_CONSTANT_TRACE = "undefined_constant_trace"
STATUS_ZERO_WITHIN_VARIANCE = "undefined_or_infinite_zero_within_variance"
STATUS_INSUFFICIENT_DATA = "insufficient_data"
STATUS_NOT_AVAILABLE = "not_available"

RHAT_THRESHOLD = 1.01
LOW_ESS_THRESHOLD = 400.0
MODE_COLLAPSE_TOP1_MASS_THRESHOLD = 0.9
LOW_DIVERSITY_UNIQUE_FRACTION_THRESHOLD = 0.05
NO_RECENT_IMPROVEMENT_WINDOW_FRACTION = 0.5
POOR_MIXING_MIN_TAU_MULTIPLES = 50.0
LOW_FEASIBILITY_RATE_THRESHOLD = 0.5

MIN_DRAWS_FOR_ESS = 4
MIN_DRAWS_FOR_RHAT = 4
MIN_CHAINS_FOR_RHAT = 2

FLAG_ORDER = (
    "mode_collapse",
    "low_diversity",
    "low_ess",
    "poor_mixing",
    "chain_disagreement",
    "no_recent_improvement",
    "zero_energy_variance",
    "zero_within_chain_variance",
    "insufficient_diagnostic_data",
)
RESERVED_FLAGS = ("low_feasibility", "bad_schedule", "block_stuck", "conversion_unverified")

# Matches numpy's finfo(float).resolution, used by arviz's constant-array check.
_CONSTANT_RESOLUTION = 1e-15


def thresholds_summary() -> dict[str, float]:
    """Threshold constants echoed into every diagnostics payload."""
    return {
        "rhat": RHAT_THRESHOLD,
        "low_ess": LOW_ESS_THRESHOLD,
        "mode_collapse_top1_mass": MODE_COLLAPSE_TOP1_MASS_THRESHOLD,
        "low_diversity_unique_fraction": LOW_DIVERSITY_UNIQUE_FRACTION_THRESHOLD,
        "no_recent_improvement_window_fraction": NO_RECENT_IMPROVEMENT_WINDOW_FRACTION,
        "poor_mixing_min_tau_multiples": POOR_MIXING_MIN_TAU_MULTIPLES,
        "low_feasibility_rate": LOW_FEASIBILITY_RATE_THRESHOLD,
    }


def _mean(values: Sequence[float]) -> float:
    return math.fsum(values) / len(values)


def _variance(values: Sequence[float], ddof: int = 0) -> float:
    center = _mean(values)
    return math.fsum((value - center) ** 2 for value in values) / (len(values) - ddof)


def _rectangularize(chains: Sequence[Sequence[float]]) -> list[list[float]]:
    """Drop empty chains and truncate the rest to the shared minimum length.

    The runtime distributes reads across chains with lengths differing by at
    most one, so truncation loses at most ``num_chains - 1`` draws while
    keeping every chain (dropping short chains instead would discard far more).

    Non-finite values raise ``ValueError`` per the EVAL-EQ-007 non-finite
    input rule: NaN would either leak into serialized output or silently
    terminate the Geyer scan into a finite-but-meaningless ESS. The THRML
    runtime cannot produce them; this guards external baseline adapters.
    """
    rows = []
    for chain_index, chain in enumerate(chains):
        row = [finite_float(value, name=f"chain {chain_index} energy value") for value in chain]
        if row:
            rows.append(row)
    if not rows:
        return []
    shortest = min(len(row) for row in rows)
    return [row[:shortest] for row in rows]


def _split_rows(rows: list[list[float]]) -> list[list[float]]:
    """Half-split already-rectangular rows: first halves then last halves.

    The middle draw of an odd-length chain is dropped, matching arviz
    ``_split_chains``. Internal callers that already hold rectangular rows use
    this directly, avoiding a redundant ``_rectangularize`` pass.
    """
    if not rows:
        return []
    half = len(rows[0]) // 2
    return [row[:half] for row in rows] + [row[-half:] for row in rows]


def split_chains(chains: Sequence[Sequence[float]]) -> list[list[float]]:
    """Half-split each chain per EVAL-EQ-007: first halves then last halves.

    Ragged input is rectangularized first; ``_split_rows`` holds the core.
    """
    return _split_rows(_rectangularize(chains))


def _geyer_ess(split_rows: list[list[float]]) -> tuple[float, float]:
    """Geyer initial-sequence tau and ESS on split chains (EVAL-EQ-008).

    Follows arviz ``_ess`` operation-for-operation, with the autocovariance at
    each lag computed lazily as the Geyer scan advances instead of via FFT at
    every lag upfront.
    """
    num_chains = len(split_rows)
    num_draws = len(split_rows[0])
    chain_means = [_mean(row) for row in split_rows]
    demeaned = [[value - center for value in row] for row, center in zip(split_rows, chain_means)]

    def mean_autocovariance(lag: int) -> float:
        total = 0.0
        for deviations in demeaned:
            total += sum(map(mul, deviations, deviations[lag:] if lag else deviations))
        return total / (num_draws * num_chains)

    mean_var = mean_autocovariance(0) * num_draws / (num_draws - 1.0)
    var_plus = mean_var * (num_draws - 1.0) / num_draws
    if num_chains > 1:
        var_plus += _variance(chain_means, ddof=1)

    rho = [0.0] * num_draws
    rho_even = 1.0
    rho[0] = rho_even
    rho_odd = 1.0 - (mean_var - mean_autocovariance(1)) / var_plus
    rho[1] = rho_odd

    # Geyer initial positive sequence.
    t = 1
    while t < (num_draws - 3) and (rho_even + rho_odd) > 0.0:
        rho_even = 1.0 - (mean_var - mean_autocovariance(t + 1)) / var_plus
        rho_odd = 1.0 - (mean_var - mean_autocovariance(t + 2)) / var_plus
        if (rho_even + rho_odd) >= 0:
            rho[t + 1] = rho_even
            rho[t + 2] = rho_odd
        t += 2
    max_t = t - 2
    if rho_even > 0:
        rho[max_t + 1] = rho_even

    # Geyer initial monotone sequence (pair-averaging clamp).
    t = 1
    while t <= max_t - 2:
        if (rho[t + 1] + rho[t + 2]) > (rho[t - 1] + rho[t]):
            rho[t + 1] = (rho[t - 1] + rho[t]) / 2.0
            rho[t + 2] = rho[t + 1]
        t += 2

    size = num_chains * num_draws
    tau_hat = -1.0 + 2.0 * math.fsum(rho[: max_t + 1]) + rho[max_t + 1]
    tau_hat = max(tau_hat, 1.0 / math.log10(size))
    return tau_hat, size / tau_hat


def ess_mean(chains: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Autocorrelation-time and ESS summary per EVAL-EQ-008.

    Statuses replace NaN/Inf: below ``MIN_DRAWS_FOR_ESS`` raw draws both
    statuses are ``insufficient_data``; a constant (post-split) trace reports
    ``constant_trace`` / ``undefined_constant_trace`` instead of arviz's
    healthy array-size ESS (audited deviation).

    Ragged input is rectangularized first; ``_ess_mean_rows`` holds the core.
    """
    return _ess_mean_rows(_rectangularize(chains))


def _ess_mean_rows(rows: list[list[float]]) -> dict[str, Any]:
    if not rows or len(rows[0]) < MIN_DRAWS_FOR_ESS:
        return {
            "autocorrelation_status": STATUS_INSUFFICIENT_DATA,
            "tau_hat": None,
            "ess_status": STATUS_INSUFFICIENT_DATA,
            "ess": None,
        }
    split_rows = _split_rows(rows)
    flat = [value for row in split_rows for value in row]
    if max(flat) - min(flat) < _CONSTANT_RESOLUTION:
        return {
            "autocorrelation_status": STATUS_CONSTANT_TRACE,
            "tau_hat": None,
            "ess_status": STATUS_UNDEFINED_CONSTANT_TRACE,
            "ess": None,
        }
    tau_hat, ess = _geyer_ess(split_rows)
    return {
        "autocorrelation_status": STATUS_OK,
        "tau_hat": tau_hat,
        "ess_status": STATUS_OK,
        "ess": ess,
    }


def _rhat_core(split_rows: list[list[float]]) -> tuple[float, float, float | None]:
    """EVAL-EQ-007 core on already-split chains: (W, B, rhat-or-None-if-W-zero)."""
    num_draws = len(split_rows[0])
    within = _mean([_variance(row, ddof=1) for row in split_rows])
    between = num_draws * _variance([_mean(row) for row in split_rows], ddof=1)
    if within == 0.0:
        return within, between, None
    return within, between, math.sqrt((between / within + num_draws - 1.0) / num_draws)


def _split_rows_for_rhat(chains: Sequence[Sequence[float]]) -> list[list[float]] | None:
    """Rectangularize and half-split chains for R-hat, or None below the
    EVAL-EQ-007 minimums (``MIN_CHAINS_FOR_RHAT`` chains, ``MIN_DRAWS_FOR_RHAT``
    raw draws); shared prep of both R-hat variants."""
    rows = _rectangularize(chains)
    if len(rows) < MIN_CHAINS_FOR_RHAT or len(rows[0]) < MIN_DRAWS_FOR_RHAT:
        return None
    return _split_rows(rows)


def _zero_within_status(between: float) -> str:
    """Status when W == 0: every chain constant at one shared value is a
    constant trace (B == 0); chains constant at distinct values make R-hat
    infinite (zero-within-variance)."""
    return STATUS_UNDEFINED_CONSTANT_TRACE if between == 0.0 else STATUS_ZERO_WITHIN_VARIANCE


def split_rhat(chains: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Plain split R-hat per EVAL-EQ-007 (not rank-normalized, not folded)."""
    split_rows = _split_rows_for_rhat(chains)
    if split_rows is None:
        return {"rhat_status": STATUS_INSUFFICIENT_DATA, "rhat": None, "split_within_chain_variance": None}
    within, between, rhat = _rhat_core(split_rows)
    if rhat is None:
        return {
            "rhat_status": _zero_within_status(between),
            "rhat": None,
            "split_within_chain_variance": within,
        }
    return {"rhat_status": STATUS_OK, "rhat": rhat, "split_within_chain_variance": within}


_STANDARD_NORMAL = NormalDist()
# Blom (1958) fractional offset, matching arviz _backtransform_ranks(c=3/8).
_RANK_OFFSET = 3.0 / 8.0


def _average_tie_ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks with ties sharing the mean rank (scipy rankdata "average").

    Ties require EXACT float equality, mirroring arviz semantics and the
    plain variant's ``W == 0.0`` checks (EVAL-EQ-013 ties rule).
    """
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start
        while stop + 1 < len(order) and values[order[stop + 1]] == values[order[start]]:
            stop += 1
        shared_rank = (start + stop) / 2.0 + 1.0
        for position in range(start, stop + 1):
            ranks[order[position]] = shared_rank
        start = stop + 1
    return ranks


def _rank_normalize(split_rows: list[list[float]]) -> list[list[float]]:
    """Pooled ranks -> Blom backtransform -> normal quantile (EVAL-EQ-013).

    Ranking pools ALL split chains together — per-chain ranking would erase
    exactly the between-chain location signal R-hat measures.
    """
    flat = [value for row in split_rows for value in row]
    size = len(flat)
    z_values = [
        _STANDARD_NORMAL.inv_cdf((rank - _RANK_OFFSET) / (size - 2.0 * _RANK_OFFSET + 1.0))
        for rank in _average_tie_ranks(flat)
    ]
    num_draws = len(split_rows[0])
    return [
        z_values[row_index * num_draws : (row_index + 1) * num_draws] for row_index in range(len(split_rows))
    ]


def rank_normalized_split_rhat(chains: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Rank-normalized + folded split R-hat per EVAL-EQ-013.

    Algorithm-step port of arviz v0.21.0 ``_rhat_rank``: half-split first,
    rank-normalize the pooled split draws for the bulk component, fold around
    the pooled median and re-rank-normalize for the folded component, report
    the max. The plain ``rhat`` key (EVAL-EQ-007) is deliberately untouched;
    this variant additionally catches chains that agree in mean but disagree
    in spread. When folding collapses to a constant (balanced two-valued
    trace symmetric around the median), the folded key is None and the
    combined value is the bulk alone, matching arviz's max-with-NaN result.
    """
    keys = (
        "rank_normalized_rhat_status",
        "rank_normalized_rhat",
        "rank_normalized_rhat_bulk",
        "rank_normalized_rhat_folded",
    )

    def result(
        status: str,
        combined: float | None = None,
        bulk: float | None = None,
        folded: float | None = None,
    ) -> dict[str, Any]:
        return dict(zip(keys, (status, combined, bulk, folded)))

    split_rows = _split_rows_for_rhat(chains)
    if split_rows is None:
        return result(STATUS_INSUFFICIENT_DATA)
    _, bulk_between, bulk = _rhat_core(_rank_normalize(split_rows))
    if bulk is None:
        return result(_zero_within_status(bulk_between))
    pooled_median = median(value for row in split_rows for value in row)
    folded_rows = [[abs(value - pooled_median) for value in row] for row in split_rows]
    _, folded_between, folded = _rhat_core(_rank_normalize(folded_rows))
    if folded is None:
        if folded_between > 0.0:
            return result(STATUS_ZERO_WITHIN_VARIANCE, bulk=bulk)
        return result(STATUS_OK, combined=bulk, bulk=bulk)
    return result(STATUS_OK, combined=max(bulk, folded), bulk=bulk, folded=folded)


def _combined_split_rhat(chains: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Plain (EVAL-EQ-007) and rank-normalized/folded (EVAL-EQ-013) split R-hat.

    Both variants are always emitted together because ``_disagreement_signals``
    reads keys from each; a producer must never emit only one half.
    """
    return {**split_rhat(chains), **rank_normalized_split_rhat(chains)}


def energy_section(energy_chains: Sequence[Sequence[float]]) -> dict[str, Any]:
    """Pooled energy statistics, improvement telemetry, and ESS keys."""
    chains = [[float(value) for value in chain] for chain in energy_chains]
    pooled = [value for chain in chains for value in chain]
    section: dict[str, Any] = {"count": len(pooled)}
    if pooled:
        best = min(pooled)
        section["min"] = best
        section["max"] = max(pooled)
        section["mean"] = _mean(pooled)
        section["variance"] = _variance(pooled)
        section["best_energy"] = best
    else:
        section.update({"min": None, "max": None, "mean": None, "variance": None, "best_energy": None})

    improvement_count = 0
    recent_votes: list[bool] = []
    for chain in chains:
        if not chain:
            continue
        running_best = chain[0]
        last_improvement_index = 0
        for index in range(1, len(chain)):
            if chain[index] < running_best:
                running_best = chain[index]
                last_improvement_index = index
                improvement_count += 1
        if len(chain) >= 2:
            cutoff = len(chain) * (1.0 - NO_RECENT_IMPROVEMENT_WINDOW_FRACTION)
            recent_votes.append(last_improvement_index >= cutoff)
    section["best_improvement_count"] = improvement_count
    section["recent_improvement"] = any(recent_votes) if recent_votes else None

    rows = _rectangularize(chains)
    section["draws_per_chain"] = len(rows[0]) if rows else 0
    section.update(_ess_mean_rows(rows))
    return section


def chain_section(
    energy_chains: Sequence[Sequence[float]],
    *,
    ess: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Per-chain statistics, unsplit between-chain variance, and split R-hat.

    ``within_chain_variances`` is the population variance per chain and
    ``between_chain_variance`` is the UNSPLIT B of EVAL-EQ-007; both are
    distinct from the ddof=1 split-chain quantities inside ``rhat``.

    ``ess`` optionally supplies a precomputed ``ess_mean`` summary (any mapping
    with ``ess_status``/``ess``/``tau_hat``); a caller that already ran the
    Geyer scan on the same chains — ``compute_diagnostics`` via the energy
    section — passes it so the scan is not paid for twice.
    """
    rows = _rectangularize(energy_chains)
    section: dict[str, Any] = {
        "num_chains": len(energy_chains),
        "num_chains_used": len(rows),
        "draws_per_chain": len(rows[0]) if rows else 0,
    }
    if rows:
        section["chain_means"] = [_mean(row) for row in rows]
        section["within_chain_variances"] = [_variance(row) for row in rows]
    else:
        section["chain_means"] = []
        section["within_chain_variances"] = []
    if len(rows) >= 2:
        section["between_chain_variance"] = len(rows[0]) * _variance(section["chain_means"], ddof=1)
    else:
        section["between_chain_variance"] = None
    section.update(_combined_split_rhat(energy_chains))
    # The chain section exposes only these three ESS keys; autocorrelation_status
    # stays energy-section-scoped (frozen fixture schema), so do not blanket-copy.
    ess_keys = ess if ess is not None else ess_mean(energy_chains)
    section["ess_status"] = ess_keys["ess_status"]
    section["ess"] = ess_keys["ess"]
    section["tau_hat"] = ess_keys["tau_hat"]
    return section


def state_counts(
    samples: Sequence[Mapping[Variable, int]], variables: Sequence[Variable]
) -> dict[tuple[int, ...], int]:
    """Count reads per distinct state, keyed by the fixed variable order."""
    return Counter(tuple(int(sample[variable]) for variable in variables) for sample in samples)


def diversity_section(
    counts: Mapping[tuple[int, ...], int],
    num_variables: int,
    top_k: Sequence[int] = (1, 3, 10),
) -> dict[str, Any]:
    """Diversity metrics per EVAL-EQ-011 over distinct-state counts."""
    total = sum(counts.values())
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    section: dict[str, Any] = {
        "num_reads": total,
        "unique_states": len(ordered),
        "unique_fraction": len(ordered) / total if total else None,
    }
    masses = [count / total for _, count in ordered] if total else []
    for k in top_k:
        section[f"top{k}_mass"] = math.fsum(masses[:k]) if masses else None
    section["entropy_nats"] = -math.fsum(mass * math.log(mass) for mass in masses) if masses else None
    if total >= 2:
        # Weighted pairwise Hamming via per-position value grouping: at each
        # position the read pairs that differ number (total^2 - sum_v W_v^2)/2,
        # with W_v the read weight of value v there. Same-state pairs share
        # every value and contribute zero, so this equals the explicit
        # O(states^2) pairwise sum exactly — integer arithmetic throughout,
        # in O(states * variables).
        weighted_distance = 0
        for position in range(len(ordered[0][0])):
            value_weights: Counter[int] = Counter()
            for state, count in ordered:
                value_weights[state[position]] += count
            weighted_distance += (
                total * total - sum(weight * weight for weight in value_weights.values())
            ) // 2
        pair_count = total * (total - 1) // 2
        mean_hamming = weighted_distance / pair_count
        section["mean_pairwise_hamming_distance"] = mean_hamming
        section["normalized_mean_pairwise_hamming_distance"] = (
            mean_hamming / num_variables if num_variables else None
        )
    else:
        section["mean_pairwise_hamming_distance"] = None
        section["normalized_mean_pairwise_hamming_distance"] = None
    return section


def energy_flags(energy: Mapping[str, Any]) -> list[str]:
    """Energy-family flags; evaluated only against the energy section."""
    flags = []
    if (
        energy.get("ess_status") == STATUS_OK
        and energy.get("ess") is not None
        and energy["ess"] < LOW_ESS_THRESHOLD
    ):
        flags.append("low_ess")
    if (
        energy.get("autocorrelation_status") == STATUS_OK
        and energy.get("tau_hat") is not None
        and energy.get("draws_per_chain", 0) < POOR_MIXING_MIN_TAU_MULTIPLES * energy["tau_hat"]
    ):
        flags.append("poor_mixing")
    if energy.get("recent_improvement") is False:
        flags.append("no_recent_improvement")
    if energy.get("variance") == 0.0 and energy.get("count", 0) > 0:
        flags.append("zero_energy_variance")
    if energy.get("ess_status") == STATUS_INSUFFICIENT_DATA:
        flags.append("insufficient_diagnostic_data")
    return _canonical_order(flags)


def _disagreement_signals(section: Mapping[str, Any]) -> bool:
    """True when either R-hat variant reports chain disagreement.

    Fires on the zero-within-variance status (infinite R-hat: chains constant
    at distinct values) or a numeric value above ``RHAT_THRESHOLD``, for both
    the plain (EVAL-EQ-007) and rank-normalized (EVAL-EQ-013) keys.
    """
    for status_key, value_key in (
        ("rhat_status", "rhat"),
        ("rank_normalized_rhat_status", "rank_normalized_rhat"),
    ):
        status = section.get(status_key)
        if status == STATUS_ZERO_WITHIN_VARIANCE:
            return True
        if status == STATUS_OK and section.get(value_key) is not None and section[value_key] > RHAT_THRESHOLD:
            return True
    return False


def chain_flags(chains: Mapping[str, Any]) -> list[str]:
    """Chain-family flags; evaluated only against the chain section.

    ``chain_disagreement`` fires from the energy-trace R-hat variants or, when
    the ``magnetization`` subsection is present (EVAL-EQ-007 magnetization
    wiring), from the same estimators on the magnetization trace — the only
    flag that subsection contributes. ``zero_within_chain_variance`` and
    ``insufficient_diagnostic_data`` stay energy-trace-scoped.
    """
    flags = []
    if _disagreement_signals(chains) or _disagreement_signals(chains.get("magnetization") or {}):
        flags.append("chain_disagreement")
    if chains.get("split_within_chain_variance") == 0.0:
        flags.append("zero_within_chain_variance")
    if chains.get("rhat_status") == STATUS_INSUFFICIENT_DATA:
        flags.append("insufficient_diagnostic_data")
    return _canonical_order(flags)


def diversity_flags(diversity: Mapping[str, Any]) -> list[str]:
    """Diversity-family flags; evaluated only against the diversity section."""
    flags = []
    top1 = diversity.get("top1_mass")
    if top1 is not None and top1 >= MODE_COLLAPSE_TOP1_MASS_THRESHOLD:
        flags.append("mode_collapse")
    unique_fraction = diversity.get("unique_fraction")
    if unique_fraction is not None and unique_fraction <= LOW_DIVERSITY_UNIQUE_FRACTION_THRESHOLD:
        flags.append("low_diversity")
    return _canonical_order(flags)


def _canonical_order(flags: Sequence[str]) -> list[str]:
    present = set(flags)
    return [flag for flag in FLAG_ORDER if flag in present]


def magnetization_trace(
    sample_chains: Sequence[Sequence[Mapping[Variable, int]]],
    variables: Sequence[Variable],
) -> list[list[float]]:
    """Per-read mean spin per chain (EVAL-EQ-012), shaped like traces["energy"]."""
    count = len(variables)
    return [
        [math.fsum(sample[variable] for variable in variables) / count for sample in chain]
        for chain in sample_chains
    ]


def distance_to_best_trace(
    sample_chains: Sequence[Sequence[Mapping[Variable, int]]],
    best_sample: Mapping[Variable, int],
    variables: Sequence[Variable],
) -> list[list[int]]:
    """Per-read Hamming distance to the run's best sample (EVAL-EQ-012).

    ``best_sample`` must come from the first-minimal-index rule
    (``SampleResult.best_index``) so degenerate optima stay deterministic.
    """
    return [
        [sum(1 for variable in variables if sample[variable] != best_sample[variable]) for sample in chain]
        for chain in sample_chains
    ]


def compute_diagnostics(
    *,
    energy_chains: Sequence[Sequence[float]],
    samples: Sequence[Mapping[Variable, int]] | None = None,
    variables: Sequence[Variable] | None = None,
    magnetization_chains: Sequence[Sequence[float]] | None = None,
    timings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the full diagnostics payload for one sampler run.

    Unlike the fixture adapter, the runtime path unions the flags of every
    family. ``magnetization_chains`` (the EVAL-EQ-012 trace, per chain) adds
    the ``chains.magnetization`` disagreement subsection: degenerate optima of
    EQUAL energy are invisible to every energy-trace statistic, while the
    magnetization trace separates the wells. ``constraints`` stays
    ``not_available`` until the penalty/encoding layer exists.
    """
    energy = energy_section(energy_chains)
    chains = chain_section(energy_chains, ess=energy)
    if magnetization_chains is not None:
        chains["magnetization"] = _combined_split_rhat(magnetization_chains)
    flags = set(energy_flags(energy)) | set(chain_flags(chains))
    if samples is not None and variables is not None:
        diversity = diversity_section(state_counts(samples, variables), len(variables))
        flags |= set(diversity_flags(diversity))
    else:
        diversity = {"status": STATUS_NOT_AVAILABLE}
    runtime: dict[str, Any] = dict(timings or {})
    num_reads = len(samples) if samples is not None else energy["count"]
    sample_seconds = runtime.get("sample_seconds")
    runtime["reads_per_second"] = num_reads / sample_seconds if sample_seconds else None
    runtime.setdefault("diagnostics_seconds", None)
    return {
        "energy": energy,
        "diversity": diversity,
        "chains": chains,
        "constraints": {"status": STATUS_NOT_AVAILABLE},
        "runtime": runtime,
        "flags": _canonical_order(list(flags)),
        "thresholds": thresholds_summary(),
    }


def diagnostic_candidate_from_input(fixture_input: Mapping[str, Any]) -> dict[str, Any]:
    """Build a diagnostic-fixture candidate from the fixture ``input`` block.

    Reads ONLY the input block (echo-proofing parity with
    ``benchmark_bridge``). ``required_flags`` is family-scoped: each input
    shape exercises exactly one telemetry family, and frozen fixtures pin the
    exact flag multiset of that family alone.
    """
    if "sample_counts" in fixture_input:
        variables = list(fixture_input["variables"])
        counts: dict[tuple[int, ...], int] = {}
        for row in fixture_input["sample_counts"]:
            state = tuple(int(row["spin"][variable]) for variable in variables)
            counts[state] = counts.get(state, 0) + int(row["count"])
        section = diversity_section(counts, len(variables))
        flags = diversity_flags(section)
    elif "chains" in fixture_input:
        rows = sorted(fixture_input["chains"], key=lambda row: row["chain_id"])
        section = chain_section([row["energy_trace"] for row in rows])
        flags = chain_flags(section)
    elif "energy_trace" in fixture_input:
        section = energy_section([fixture_input["energy_trace"]])
        flags = energy_flags(section)
    else:
        raise ValueError("fixture input must contain one of 'sample_counts', 'chains', or 'energy_trace'")
    candidate = dict(section)
    candidate["required_flags"] = flags
    return candidate
