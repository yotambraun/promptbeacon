"""Mention rates, confidence intervals and ranks (no editorial input)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field

from pbindex.protocol import Candidate
from promptbeacon.analysis.statistics import proportion_interval


@dataclass
class Answer:
    """One model answer to one prompt in one run."""

    provider: str
    model: str
    run: int
    prompt_index: int
    prompt: str
    text: str = ""
    error: str | None = None
    cost_usd: float | None = None
    mentions: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class ProjectResult:
    """A candidate's measured mention rate in a category."""

    name: str
    url: str
    mentions: int
    answers: int
    rate: float
    ci_low: float
    ci_high: float
    rank: int = 0
    tied: bool = False
    overlaps_next: bool = False
    by_provider: dict[str, dict[str, float | int]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def find_mentions(text: str, candidates: Sequence[Candidate]) -> list[str]:
    """Names of the candidates an answer mentions (whole-word matches)."""
    return [c.name for c in candidates if c.pattern().search(text)]


def rank_projects(
    answers: Sequence[Answer], candidates: Sequence[Candidate]
) -> list[ProjectResult]:
    """Rank by mention rate over successful answers; ties share a rank.

    Rank = 1 + the number of projects with strictly more mentions
    ("competition ranking"). Each rate has a 95% Wilson interval;
    ``overlaps_next`` marks a project whose interval overlaps the next one's,
    i.e. the order between them is not statistically clear.
    """
    ok = [a for a in answers if a.ok]
    total = len(ok)
    providers = sorted({a.provider for a in ok})
    results = []
    for cand in candidates:
        count = sum(1 for a in ok if cand.name in a.mentions)
        low, high = proportion_interval(count, total)
        by_provider: dict[str, dict[str, float | int]] = {}
        for provider in providers:
            sub = [a for a in ok if a.provider == provider]
            hits = sum(1 for a in sub if cand.name in a.mentions)
            by_provider[provider] = {
                "mentions": hits,
                "answers": len(sub),
                "rate": round(hits / len(sub), 4) if sub else 0.0,
            }
        results.append(
            ProjectResult(
                name=cand.name,
                url=cand.url,
                mentions=count,
                answers=total,
                rate=round(count / total, 4) if total else 0.0,
                ci_low=low,
                ci_high=high,
                by_provider=by_provider,
            )
        )
    results.sort(key=lambda r: (-r.mentions, r.name.lower()))
    for r in results:
        r.rank = 1 + sum(1 for o in results if o.mentions > r.mentions)
        r.tied = sum(1 for o in results if o.mentions == r.mentions) > 1
    for this, nxt in zip(results, results[1:]):
        this.overlaps_next = this.ci_low <= nxt.ci_high
    return results
