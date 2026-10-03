"""One place that turns plain options into a configured :class:`Beacon`.

The CLI, the MCP server and the GitHub Action all describe a scan with the same
small set of options; this function is the single source of truth for how
those options map onto the fluent API.
"""

from __future__ import annotations

from collections.abc import Sequence

from promptbeacon.beacon import Beacon
from promptbeacon.core.config import Provider


def parse_providers(names: Sequence[str | Provider]) -> list[Provider]:
    """Convert provider names (case-insensitive) to :class:`Provider` values.

    Raises:
        ValueError: For an unknown provider, listing the valid ones.
    """
    providers: list[Provider] = []
    for name in names:
        if isinstance(name, Provider):
            providers.append(name)
            continue
        try:
            providers.append(Provider(str(name).strip().lower()))
        except ValueError:
            valid = ", ".join(p.value for p in Provider)
            raise ValueError(
                f"Invalid provider: {name}. Choose from: {valid}"
            ) from None
    return providers


def configure_beacon(
    brand: str | None = None,
    *,
    project: str | None = None,
    competitors: Sequence[str] | None = None,
    providers: Sequence[str | Provider] | None = None,
    categories: Sequence[str] | None = None,
    prompt_count: int | None = None,
    demo: bool = False,
    grounded: bool = False,
    infer_category: bool = False,
) -> Beacon:
    """Build a Beacon from plain options.

    Args:
        brand: Brand to measure. Optional when ``project`` is given (the
            project name is used; a brand given here wins and the project name
            becomes an alias).
        project: ``"github:owner/name"``, ``"pypi:pkg"`` or ``"npm:pkg"`` — reads
            public metadata for the category and competitor candidates.
        competitors: Competitors (override project guesses).
        providers: Provider names such as ``["openai", "anthropic"]``.
        categories: Categories the prompts ask about (override guesses).
        prompt_count: Prompts per category.
        demo: Keyless demo mode.
        grounded: Web-grounded scan.
        infer_category: Opt-in single LLM call to name the category (and
            competitors) when none is given. Ignored in demo mode.

    Raises:
        ValueError: If neither brand nor project is given, or a provider is
            unknown.
        promptbeacon.projects.ProjectMetadataError: If project metadata cannot be
            fetched.
    """
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
        raise ValueError("Provide a brand or a project (github:, pypi: or npm:).")

    if competitors:
        beacon = beacon.with_competitors(*competitors)
    if providers:
        beacon = beacon.with_providers(*parse_providers(providers))
    if categories:
        beacon = beacon.with_categories(*categories)
    if prompt_count is not None:
        beacon = beacon.with_prompt_count(prompt_count)
    if demo:
        beacon = beacon.demo()
    if grounded:
        beacon = beacon.with_grounding()
    return beacon
