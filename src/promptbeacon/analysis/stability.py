"""Run-to-run stability analysis for visibility scans.

Answer engines are probabilistic — the same prompt can mention a brand on one
run and omit it on the next. This module repeats a scan ``N`` times and reports
how trustworthy a single number is, reusing the existing statistics utilities
(confidence interval + volatility) so there is no duplicated math.
"""

from __future__ import annotations

from promptbeacon.analysis.scorer import (
    ScoringWeights,
    _brand_appears,
    calculate_visibility_score,
)
from promptbeacon.analysis.statistics import (
    bootstrap_ci,
    calculate_confidence_interval,
    calculate_volatility,
)
from promptbeacon.core.schemas import (
    PromptStability,
    ProviderResult,
    SourceStability,
    StabilityReport,
)

# Volatility score (std dev of run-to-run changes) at or above this is treated
# as "fully unstable" when normalising into the 0-100 stability score.
_VOLATILITY_CEILING = 25.0


def aggregate_stability(
    runs: list[list[ProviderResult]],
    brand: str,
    weights: ScoringWeights | None = None,
) -> StabilityReport:
    """Aggregate repeated scan runs into a :class:`StabilityReport`.

    Args:
        runs: One inner list of provider results per repeated run.
        brand: The brand being analyzed.
        weights: Optional custom scoring weights (same as the scan).

    Returns:
        A StabilityReport with per-run scores, a confidence interval, volatility,
        per-prompt consistency, and a 0-100 ``stability_score``.
    """
    if not runs:
        raise ValueError("aggregate_stability requires at least one run")

    # Per-run visibility scores -> volatility + confidence interval.
    score_per_run = [
        calculate_visibility_score(run, brand, weights=weights) for run in runs
    ]
    mean_score = sum(score_per_run) / len(score_per_run)
    confidence_interval = calculate_confidence_interval(score_per_run)
    bootstrap_interval = bootstrap_ci(score_per_run)
    volatility = calculate_volatility(score_per_run)

    # Per-prompt presence across runs. A prompt "appears" in a run if the brand
    # is mentioned in at least one provider's response to it that run.
    prompts: list[str] = []
    seen: set[str] = set()
    for run in runs:
        for result in run:
            if result.prompt not in seen:
                seen.add(result.prompt)
                prompts.append(result.prompt)

    appeared_per_run: list[set[str]] = []
    for run in runs:
        appeared = {
            result.prompt
            for result in run
            if result.success and _brand_appears(result, brand)
        }
        appeared_per_run.append(appeared)

    n_runs = len(runs)
    prompt_stability: list[PromptStability] = []
    for prompt in prompts:
        appearances = sum(1 for appeared in appeared_per_run if prompt in appeared)
        presence_rate = appearances / n_runs
        prompt_stability.append(
            PromptStability(
                prompt=prompt,
                runs=n_runs,
                appearances=appearances,
                presence_rate=round(presence_rate, 4),
                flip_flopped=0 < appearances < n_runs,
            )
        )

    overall_presence_consistency = (
        sum(p.presence_rate for p in prompt_stability) / len(prompt_stability)
        if prompt_stability
        else 0.0
    )

    # Per-source citation consistency: which domains the engines cite every run
    # vs. flip-flop. A source "appears" in a run if any provider cited it.
    cited_per_run: list[set[str]] = []
    source_order: list[str] = []
    source_seen: set[str] = set()
    for run in runs:
        domains = {
            citation.source_name
            for result in run
            if result.success
            for citation in result.citations
        }
        cited_per_run.append(domains)
        for domain in domains:
            if domain not in source_seen:
                source_seen.add(domain)
                source_order.append(domain)

    source_stability: list[SourceStability] = []
    for domain in source_order:
        appearances = sum(1 for cited in cited_per_run if domain in cited)
        source_stability.append(
            SourceStability(
                domain=domain,
                runs=n_runs,
                appearances=appearances,
                presence_rate=round(appearances / n_runs, 4),
                flip_flopped=0 < appearances < n_runs,
            )
        )
    source_stability.sort(key=lambda s: (-s.appearances, s.domain))

    # Blend presence consistency with normalised (inverted) volatility.
    normalised_volatility = min(volatility.volatility_score / _VOLATILITY_CEILING, 1.0)
    stability_score = 100 * (
        0.5 * overall_presence_consistency + 0.5 * (1 - normalised_volatility)
    )

    return StabilityReport(
        brand=brand,
        runs=n_runs,
        score_per_run=[round(s, 1) for s in score_per_run],
        mean_score=round(mean_score, 1),
        score_confidence_interval=confidence_interval,
        score_bootstrap_interval=bootstrap_interval,
        volatility=volatility,
        stability_score=round(stability_score, 1),
        overall_presence_consistency=round(overall_presence_consistency, 4),
        prompt_stability=prompt_stability,
        source_stability=source_stability,
    )
