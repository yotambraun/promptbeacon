"""One place that turns plain options into a configured :class:`Beacon`.

The CLI, the MCP server and the GitHub Action all describe a scan with the same
small set of options; this function is the single source of truth for how
those options map onto the fluent API.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import Provider, parse_model_overrides
from promptbeacon.prompts.templates import validate_prompts


def parse_providers(names: Sequence[str | Provider]) -> list[Provider]:
    """Convert provider names (case-insensitive) to :class:`Provider` values.

    Raises:
        ValueError: For an unknown provider, listing the valid ones.
    """
    return [Provider.parse(name) for name in names]


def configure_beacon(
    brand: str | None = None,
    *,
    project: str | None = None,
    competitors: Sequence[str] | None = None,
    providers: Sequence[str | Provider] | None = None,
    models: Mapping[str, str] | Mapping[Provider, str] | Sequence[str] | None = None,
    categories: Sequence[str] | None = None,
    prompt_count: int | None = None,
    demo: bool = False,
    grounded: bool = False,
    infer_category: bool = False,
    max_cost: float | None = None,
    prompts: Sequence[str] | None = None,
    aliases: Sequence[str] | None = None,
    stability_runs: int | None = None,
) -> Beacon:
    """Build a Beacon from plain options.

    Args:
        brand: Brand to measure. Optional when ``project`` is given (the
            project name is used; a brand given here wins and the project name
            becomes an alias).
        project: ``"github:owner/name"``, ``"pypi:pkg"``, ``"npm:pkg"``,
            ``"crates:name"`` or ``"hf:owner/name"`` — reads
            public metadata for the category and competitor candidates.
        competitors: Competitors (override project guesses).
        providers: Provider names such as ``["openai", "anthropic"]``.
        models: Model per provider, as a mapping (``{"openai": "gpt-6-sol"}``)
            or ``provider=model_id`` strings (``["litellm=ollama/llama3.2"]``).
            Providers named here are queried when ``providers`` is not given.
        categories: Categories the prompts ask about (override guesses).
        prompt_count: Prompts per category.
        demo: Keyless demo mode.
        grounded: Web-grounded scan.
        infer_category: Opt-in single LLM call to name the category (and
            competitors) when none is given. Ignored in demo mode.
        max_cost: Spending cap in US dollars (see :meth:`Beacon.with_max_cost`).
        prompts: Your own prompts, asked as written; ``{category}`` in a prompt
            is replaced by each category (see :meth:`Beacon.with_prompts`).
            Cannot be combined with ``prompt_count``.
        aliases: Other names that count as the brand (added to a project's own).
        stability_runs: Repeat the scan this many times (2 or more) and report
            stability (see :meth:`Beacon.with_stability`); 0 or ``None`` for a
            single scan. Multiplies the cost.

    Raises:
        ValueError: If neither brand nor project is given, a provider, model,
            prompt or alias option is invalid, prompts are combined with a
            prompt count, or stability_runs is 1 or negative.
        promptbeacon.projects.ProjectMetadataError: If project metadata cannot be
            fetched.
    """
    if prompts is not None and prompt_count is not None:
        raise ValueError(
            "Give either your own prompts or a prompt count, not both: your "
            "prompts are all asked, as written."
        )
    # Checked before any project metadata request.
    prompt_list = validate_prompts(prompts) if prompts is not None else None
    if stability_runs is not None and stability_runs != 0 and stability_runs < 2:
        raise ValueError(
            f"stability runs must be at least 2 (got {stability_runs}); use 0 "
            "for a single scan."
        )

    if project:
        beacon = Beacon.from_project(
            project, infer=infer_category and not categories and not demo
        )
        if brand and brand != beacon.brand:
            aliases = [beacon.brand, *beacon.config.brand_aliases]
            beacon._config = beacon.config.model_copy(update={"brand": brand})
            beacon = beacon.with_aliases(*aliases)
    elif brand:
        beacon = Beacon(brand)
        if infer_category:
            beacon = beacon.with_category_inference()
    else:
        raise ValueError(
            "Provide a brand or a project (github:, pypi:, npm:, crates: or hf:)."
        )

    if competitors:
        beacon = beacon.with_competitors(*competitors)
    if providers:
        beacon = beacon.with_providers(*parse_providers(providers))
    if models:
        beacon = beacon.with_models(parse_model_overrides(models))
    if categories:
        beacon = beacon.with_categories(*categories)
    if prompt_count is not None:
        beacon = beacon.with_prompt_count(prompt_count)
    if demo:
        beacon = beacon.demo()
    if grounded:
        beacon = beacon.with_grounding()
    if max_cost is not None:
        beacon = beacon.with_max_cost(max_cost)
    if prompt_list is not None:
        beacon = beacon.with_prompts(prompt_list)
    if aliases:
        beacon = beacon.with_aliases(
            *_clean_aliases([*beacon.config.brand_aliases, *aliases], beacon.brand)
        )
    if stability_runs:
        beacon = beacon.with_stability(stability_runs)
    return beacon


def _clean_aliases(aliases: Sequence[str], brand: str) -> list[str]:
    """Aliases without blanks, the brand itself, or repeats (ignoring case)."""
    seen = {brand.strip().lower()}
    cleaned = []
    for alias in aliases:
        name = alias.strip()
        if name and name.lower() not in seen:
            seen.add(name.lower())
            cleaned.append(name)
    return cleaned
