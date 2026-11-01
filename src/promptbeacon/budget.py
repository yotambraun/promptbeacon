"""Scan cost estimates and spending caps (``--max-cost`` / ``Beacon.with_max_cost``).

Before a capped scan runs, :func:`estimate_cost` prices every request it will
make from LiteLLM's bundled price map (offline; no request is sent). If the
estimate is above the cap the scan does not start. While it runs, a
:class:`BudgetTracker` stops issuing new requests once the money already spent
plus the requests in flight reaches the cap, so a scan never runs far past it;
the report then says how many answers it is based on.

The estimate is an estimate. It assumes about :data:`TYPICAL_OUTPUT_TOKENS`
output tokens per answer (real answers vary), and reports an upper bound at
``max_tokens``. Models without a price in LiteLLM's map (for example a local
Ollama model) count as $0 and are listed, so a $0 estimate is never silent.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from promptbeacon.core.config import Provider
from promptbeacon.core.exceptions import ConfigurationError

# About how long a recommendation answer is. The upper bound uses max_tokens.
TYPICAL_OUTPUT_TOKENS = 500
# Grounded answers carry the retrieved pages in their input.
GROUNDED_INPUT_TOKENS = 3000
GROUNDED_SEARCHES_PER_ANSWER = 1
# Smart extraction reads one answer and returns a small JSON document.
EXTRACTION_INPUT_TOKENS = 900
EXTRACTION_OUTPUT_TOKENS = 300
RECOMMENDATIONS_INPUT_TOKENS = 2500
RECOMMENDATIONS_OUTPUT_TOKENS = 900
INFERENCE_INPUT_TOKENS = 200
INFERENCE_OUTPUT_TOKENS = 120


def prompt_tokens(prompt: str) -> int:
    """Rough input-token count for a prompt (about 4 characters per token)."""
    return max(1, math.ceil(len(prompt) / 4)) + 8  # + chat-format overhead


@dataclass
class CostLine:
    """The estimated cost of the requests to one model."""

    provider: str
    model: str
    requests: int
    usd: float
    upper_usd: float
    priced: bool = True
    note: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "requests": self.requests,
            "usd": round(self.usd, 6),
            "upper_usd": round(self.upper_usd, 6),
            "priced": self.priced,
            "note": self.note,
        }


@dataclass
class CostEstimate:
    """What a scan is expected to cost, before it runs."""

    total_usd: float
    upper_usd: float
    requests: int
    answers: int
    lines: list[CostLine] = field(default_factory=list)
    unpriced: list[str] = field(default_factory=list)
    assumptions: str = ""
    demo: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "total_usd": round(self.total_usd, 6),
            "upper_usd": round(self.upper_usd, 6),
            "requests": self.requests,
            "answers": self.answers,
            "lines": [line.as_dict() for line in self.lines],
            "unpriced_models": list(self.unpriced),
            "assumptions": self.assumptions,
            "demo": self.demo,
        }

    def summary(self) -> str:
        """One line, e.g. ``"about $0.0032 (at most $0.0066) for 10 answers"``."""
        if self.demo:
            return "$0: demo mode makes no API calls"
        text = (
            f"about {format_usd(self.total_usd)} (at most "
            f"{format_usd(self.upper_usd)}) for {self.answers} "
            f"{'answer' if self.answers == 1 else 'answers'}"
        )
        if self.requests != self.answers:
            text += f", {self.requests} requests"
        if self.unpriced:
            text += f"; counted as $0 (no known price): {', '.join(self.unpriced)}"
        return text


def format_usd(value: float) -> str:
    """``$0.0032``, ``$0.12``, ``$3.40``: enough digits to be useful."""
    if value == 0:
        return "$0"
    if value < 0.01:
        return f"${value:.4f}"
    if value < 1:
        return f"${value:.3f}"
    return f"${value:.2f}"


def _price(
    provider: Provider, model: str, input_tokens: int, output_tokens: int
) -> float | None:
    from promptbeacon.providers.grounding import token_cost

    return token_cost(provider, model, input_tokens, output_tokens)


def _request_fee(provider: Provider, model: str, grounded: bool) -> float | None:
    """A per-request search fee: grounded searches, or Perplexity Sonar (always)."""
    if not grounded and provider != Provider.PERPLEXITY:
        return 0.0
    from promptbeacon.providers.grounding import search_fee

    fee = search_fee(provider, model)
    if fee is None:
        return None
    return fee * (GROUNDED_SEARCHES_PER_ANSWER if grounded else 1)


def estimate_cost(
    models: Sequence[tuple[Provider, str]],
    prompts: Sequence[str],
    *,
    runs: int = 1,
    max_tokens: int = 1024,
    grounded: bool = False,
    smart_extraction: bool = False,
    smart_recommendations: bool = False,
    infer_category: bool = False,
    demo: bool = False,
) -> CostEstimate:
    """Estimate a scan's cost from LiteLLM's price map, without any request.

    Args:
        models: ``(provider, model)`` for each provider that will be queried.
        prompts: The prompts sent to each provider (each run).
        runs: Stability runs (1 for a normal scan).
        max_tokens: The answer token limit (used for the upper bound).
        grounded: Web-grounded answers (larger inputs plus search fees).
        smart_extraction: One extra extraction request per answer.
        smart_recommendations: One extra request per scan.
        infer_category: One extra request before the scan.
        demo: Demo mode (no paid requests: the estimate is $0).
    """
    runs = max(1, runs)
    n_answers = len(prompts) * len(models) * runs
    if demo or not models:
        return CostEstimate(0.0, 0.0, 0, n_answers, demo=demo)

    typical_out = min(TYPICAL_OUTPUT_TOKENS, max_tokens)
    lines: list[CostLine] = []
    unpriced: list[str] = []
    requests = 0
    for provider, model in models:
        answers = len(prompts) * runs
        in_tokens = sum(prompt_tokens(p) for p in prompts) * runs
        if grounded:
            in_tokens += GROUNDED_INPUT_TOKENS * answers
        typical = _price(provider, model, in_tokens, typical_out * answers)
        upper = _price(provider, model, in_tokens, max_tokens * answers)
        fee = _request_fee(provider, model, grounded)
        note = []
        if fee is None:
            note.append("search fee unknown")
            fee = 0.0
        elif fee:
            note.append(f"includes {format_usd(fee)} per request in search fees")
        extra = 0
        if smart_extraction:
            extra += answers
            more = _price(
                provider,
                model,
                EXTRACTION_INPUT_TOKENS * answers,
                EXTRACTION_OUTPUT_TOKENS * answers,
            )
            typical = None if typical is None or more is None else typical + more
            upper = None if upper is None or more is None else upper + more
        priced = typical is not None and upper is not None and (typical > 0 or fee > 0)
        label = f"{provider.value}/{model}" if provider != Provider.LITELLM else model
        if not priced:
            unpriced.append(label)
        lines.append(
            CostLine(
                provider=provider.value,
                model=model,
                requests=answers + extra,
                usd=(typical or 0.0) + fee * answers,
                upper_usd=(upper or 0.0) + fee * answers,
                priced=priced,
                note="; ".join(note),
            )
        )
        requests += answers + extra

    first_provider, first_model = models[0]
    for enabled, inp, out in (
        (infer_category, INFERENCE_INPUT_TOKENS, INFERENCE_OUTPUT_TOKENS),
        (
            smart_recommendations,
            RECOMMENDATIONS_INPUT_TOKENS,
            RECOMMENDATIONS_OUTPUT_TOKENS,
        ),
    ):
        if enabled:
            cost = _price(first_provider, first_model, inp, out) or 0.0
            lines[0].usd += cost
            lines[0].upper_usd += cost
            lines[0].requests += 1
            requests += 1

    assumptions = (
        f"about {typical_out} output tokens per answer (upper bound: "
        f"max_tokens={max_tokens}); input tokens from the prompt length"
    )
    if grounded:
        assumptions += (
            f"; grounded answers add about {GROUNDED_INPUT_TOKENS} input tokens "
            f"and {GROUNDED_SEARCHES_PER_ANSWER} search each"
        )
    return CostEstimate(
        total_usd=sum(line.usd for line in lines),
        upper_usd=sum(line.upper_usd for line in lines),
        requests=requests,
        answers=n_answers,
        lines=lines,
        unpriced=unpriced,
        assumptions=assumptions + "; prices from LiteLLM's bundled price map",
    )


class BudgetExceededError(ConfigurationError):
    """The estimated cost of a scan is above its ``max_cost`` (nothing was sent)."""

    def __init__(self, estimate: CostEstimate, max_cost: float):
        self.estimate = estimate
        self.max_cost = max_cost
        super().__init__(
            f"Estimated cost {format_usd(estimate.total_usd)} is above the "
            f"{format_usd(max_cost)} budget ({estimate.summary()}). No request "
            "was sent. Lower it with fewer prompts (--prompts 5), fewer providers "
            "(-p openai) or stability runs, a cheaper model (--model "
            "provider=model_id), or raise --max-cost."
        )


class BudgetTracker:
    """Stops new requests once spend plus in-flight estimates reach the cap.

    Used from one event loop, so no locking is needed. ``reserve`` before a
    request (with its estimated cost), ``settle`` after it with the actual
    cost (``None`` counts as $0).
    """

    def __init__(self, max_cost: float, spent: float = 0.0):
        self.max_cost = max_cost
        self.spent = spent
        self.in_flight = 0.0
        self.skipped = 0
        self.completed = 0

    @property
    def exhausted(self) -> bool:
        return self.spent >= self.max_cost

    def reserve(self, estimate: float) -> bool:
        """Whether a request may start; reserves its estimated cost if so."""
        if self.spent + self.in_flight >= self.max_cost:
            self.skipped += 1
            return False
        self.in_flight += estimate
        return True

    def settle(self, estimate: float, actual: float | None) -> None:
        self.in_flight = max(0.0, self.in_flight - estimate)
        self.spent += actual or 0.0
        self.completed += 1

    def add(self, cost: float | None) -> None:
        """Record spend that did not go through reserve (e.g. extraction calls)."""
        self.spent += cost or 0.0


def validate_max_cost(value: float | None) -> float | None:
    """``None`` (no cap) or a positive number of US dollars."""
    if value is None:
        return None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"max_cost must be a positive amount in US dollars, got {value!r}"
        )
    return float(value)
