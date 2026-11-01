"""Run category protocols: every answer kept, a snapshot per category.

Live runs use PromptBeacon's LiteLLM client and need provider keys and a
``max_cost``; demo runs use PromptBeacon's offline mock and cost nothing.
Nothing here decides a ranking: answers are matched against the candidate
names and counted (see :mod:`pbindex.ranking`).
"""

from __future__ import annotations

import asyncio
import json
import string
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from pbindex.protocol import Candidate, IndexProtocol
from pbindex.ranking import Answer, find_mentions, rank_projects
from promptbeacon.budget import BudgetTracker, CostEstimate, estimate_cost, format_usd
from promptbeacon.core.config import Provider, has_api_key
from promptbeacon.providers.base import BaseLLMClient

DEMO_NOTE = (
    "DEMO DATA: canned answers from PromptBeacon's offline mock model, with "
    "placeholder project names. Not a measurement and not a ranking."
)


def estimate(
    protocols: Sequence[IndexProtocol],
) -> list[tuple[IndexProtocol, CostEstimate]]:
    """Price each protocol with PromptBeacon's estimator (no request is sent)."""
    return [
        (
            p,
            estimate_cost(
                p.provider_models, p.prompts, runs=p.runs, max_tokens=p.max_tokens
            ),
        )
        for p in protocols
    ]


def demo_protocol(proto: IndexProtocol) -> IndexProtocol:
    """The same protocol with placeholder names, so demo numbers never sit
    next to a real project's name."""
    letters = string.ascii_uppercase
    candidates = [
        Candidate(name=f"Project {letters[i]}", url="#")
        for i in range(len(proto.candidates))
    ]
    return proto.model_copy(update={"candidates": candidates})


@dataclass
class CategoryRun:
    """The outcome of one category in one run of the index."""

    protocol: IndexProtocol
    answers: list[Answer] = field(default_factory=list)
    skipped: int = 0
    demo: bool = False

    @property
    def cost_usd(self) -> float:
        return sum(a.cost_usd or 0.0 for a in self.answers)

    @property
    def partial(self) -> bool:
        return self.skipped > 0


ClientFactory = Callable[[Provider, str, IndexProtocol, int, int], BaseLLMClient]


def live_client(
    provider: Provider, model: str, _proto: IndexProtocol, _run: int, _prompt: int
) -> BaseLLMClient:
    from promptbeacon.providers.litellm_client import LiteLLMClient

    return LiteLLMClient(provider=provider, model=model, timeout=60.0, max_retries=2)


def demo_client(
    provider: Provider, model: str, proto: IndexProtocol, run: int, prompt: int
) -> BaseLLMClient:
    """PromptBeacon's mock, with the 'featured' project rotating over prompts."""
    from promptbeacon.providers.mock_client import MockLLMClient

    names = [c.name for c in proto.candidates]
    offset = list(Provider).index(provider)
    featured = names[(prompt + run + offset) % len(names)]
    return MockLLMClient(
        provider,
        brand=featured,
        competitors=[n for n in names if n != featured],
        variation=run,
        model=model,
        topics=[proto.category],
    )


def missing_keys(protocols: Sequence[IndexProtocol]) -> list[str]:
    """Provider names without an API key (live runs need every one)."""
    needed = {p for proto in protocols for p, _ in proto.provider_models}
    return sorted(
        p.value for p in needed if p != Provider.LITELLM and not has_api_key(p)
    )


async def run_category(
    proto: IndexProtocol,
    *,
    client_factory: ClientFactory,
    budget: BudgetTracker | None,
    per_answer_usd: dict[str, float],
    concurrency: int = 4,
    demo: bool = False,
) -> CategoryRun:
    """Ask every prompt, every run, every model; keep every answer."""
    result = CategoryRun(proto, demo=demo)
    semaphores = {p: asyncio.Semaphore(concurrency) for p in proto.providers}

    async def ask(
        provider: Provider, model: str, run: int, index: int
    ) -> Answer | None:
        prompt = proto.prompts[index]
        async with semaphores[provider.value]:
            reserve = per_answer_usd.get(provider.value, 0.0)
            if budget is not None and not budget.reserve(reserve):
                result.skipped += 1
                return None
            answer = Answer(provider.value, model, run, index, prompt)
            try:
                client = client_factory(provider, model, proto, run, index)
                resp = await client.complete(
                    prompt=prompt,
                    temperature=proto.temperature,
                    max_tokens=proto.max_tokens,
                )
                answer.text = resp.content
                answer.cost_usd = resp.cost_usd if not demo else 0.0
                answer.mentions = find_mentions(resp.content, proto.candidates)
            except Exception as e:  # noqa: BLE001 — recorded on the answer
                answer.error = f"{type(e).__name__}: {e}"
            finally:
                if budget is not None:
                    budget.settle(reserve, answer.cost_usd)
            return answer

    tasks = [
        ask(provider, model, run, index)
        for provider, model in proto.provider_models
        for run in range(proto.runs)
        for index in range(len(proto.prompts))
    ]
    for answer in await asyncio.gather(*tasks):
        if answer is not None:
            result.answers.append(answer)
    return result


def snapshot(run: CategoryRun, day: date) -> dict[str, object]:
    """The JSON snapshot for one category (everything the site shows)."""
    proto = run.protocol
    ok = [a for a in run.answers if a.ok]
    return {
        "schema": 1,
        "id": proto.id,
        "category": proto.category,
        "group": proto.group,
        "date": day.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "demo": run.demo,
        "note": DEMO_NOTE if run.demo else "",
        "tier": proto.tier,
        "models": dict(proto.providers),
        "runs": proto.runs,
        "prompts": proto.prompts,
        "temperature": proto.temperature,
        "max_tokens": proto.max_tokens,
        "protocol_sha256": proto.fingerprint(),
        "planned_answers": proto.planned_answers,
        "answers": len(ok),
        "failed_answers": len(run.answers) - len(ok),
        "skipped_answers": run.skipped,
        "partial": run.partial,
        "cost_usd": round(run.cost_usd, 6),
        "results": [r.as_dict() for r in rank_projects(run.answers, proto.candidates)],
    }


def write_run(run: CategoryRun, data_dir: Path, day: date) -> Path:
    """Write ``<data>/<date>/<id>.json`` and ``<data>/<date>/raw/<id>.jsonl``."""
    folder = data_dir / day.isoformat()
    (folder / "raw").mkdir(parents=True, exist_ok=True)
    raw = folder / "raw" / f"{run.protocol.id}.jsonl"
    with raw.open("w", encoding="utf-8", newline="\n") as fh:
        for a in sorted(run.answers, key=lambda a: (a.provider, a.run, a.prompt_index)):
            fh.write(json.dumps(a.as_dict(), ensure_ascii=False) + "\n")
    path = folder / f"{run.protocol.id}.json"
    path.write_text(
        json.dumps(snapshot(run, day), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


class IndexBudgetError(RuntimeError):
    """The estimate is above the cap; nothing was sent."""


async def run_index(
    protocols: Sequence[IndexProtocol],
    data_dir: Path,
    *,
    demo: bool,
    max_cost: float | None,
    day: date | None = None,
    concurrency: int = 4,
    client_factory: ClientFactory | None = None,
    log: Callable[[str], None] = print,
) -> list[Path]:
    """Run the protocols and write snapshots; returns the snapshot paths."""
    day = day or datetime.now(timezone.utc).date()
    if demo:
        protocols = [demo_protocol(p) for p in protocols]
    factory = client_factory or (demo_client if demo else live_client)
    budget: BudgetTracker | None = None
    priced = estimate(protocols)
    total = sum(e.total_usd for _, e in priced)
    if not demo:
        if max_cost is None:
            raise IndexBudgetError(
                f"Live runs need --max-cost (estimated {format_usd(total)} for "
                f"{len(protocols)} categories)."
            )
        if total > max_cost:
            raise IndexBudgetError(
                f"Estimated {format_usd(total)} is above --max-cost "
                f"{format_usd(max_cost)}; nothing was sent. Run fewer categories "
                "(--categories) or raise --max-cost."
            )
        budget = BudgetTracker(max_cost)
    written = []
    for proto, est in priced:
        per_answer = {
            line.provider: (line.usd / line.requests if line.requests else 0.0)
            for line in est.lines
        }
        if budget is not None and budget.exhausted:
            log(f"skip  {proto.id}: the budget is used up")
            continue
        run = await run_category(
            proto,
            client_factory=factory,
            budget=budget,
            per_answer_usd=per_answer,
            concurrency=concurrency,
            demo=demo,
        )
        path = write_run(run, data_dir, day)
        written.append(path)
        flag = " (partial: budget reached)" if run.partial else ""
        log(
            f"done  {proto.id}: {len(run.answers)} answers, "
            f"{format_usd(run.cost_usd)}{flag}"
        )
    return written
