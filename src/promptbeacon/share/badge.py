"""README badges: a self-contained SVG and a shields.io endpoint JSON.

Two ways to show AI visibility in a README, both generated from a scan report:

* ``render_badge_svg(report)`` — a standalone SVG you commit and reference
  directly (no third-party service involved).
* ``badge_endpoint(report)`` — JSON for shields.io's endpoint badge
  (https://shields.io/badges/endpoint-badge). Commit it and point shields at
  its raw URL: ``https://img.shields.io/endpoint?url=<url-encoded raw URL>``.

A third variant, ``metric="rank"``, shows the rank in a category ("AI rank:
#2 of 9 · python http clients"). It needs a category and at least three
projects (yours and two others), from a scan with competitors or from the AI
Recommendation Index.

Demo reports are labelled as demo and rendered grey, so canned data is never
mistaken for a measurement. Reports cut short by a cost cap say "partial".
"""

from __future__ import annotations

from typing import Any, Literal

from promptbeacon.core.schemas import Report
from promptbeacon.share.text import FONT_STACK, text_width, xml

BadgeMetric = Literal["both", "score", "sov", "rank"]

DEFAULT_LABEL = "AI visibility"
RANK_LABEL = "AI rank"
MIN_RANK_PROJECTS = 3

# Accessible (>= 4.5:1 with white text) status colors.
COLOR_GOOD = "15803d"  # green-700
COLOR_FAIR = "b45309"  # amber-700
COLOR_POOR = "b91c1c"  # red-700
COLOR_DEMO = "64748b"  # slate-500
LABEL_COLOR = "1e293b"  # slate-800
COLOR_ERROR = "64748b"
# Rank badges use one neutral colour: a rank is a position, not a grade.
COLOR_RANK = "4f46e5"  # indigo-600

# A tiny version of the beacon mark (white rings) for the badge's label side.
_LOGO_RINGS = (
    '<circle cx="7" cy="7" r="6" fill="none" stroke="#fff" stroke-opacity=".45" '
    'stroke-width="1.4"/>'
    '<circle cx="7" cy="7" r="3.4" fill="none" stroke="#fff" stroke-opacity=".8" '
    'stroke-width="1.4"/>'
    '<circle cx="7" cy="7" r="1.5" fill="#fff"/>'
)
LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" '
    f'viewBox="0 0 14 14">{_LOGO_RINGS}</svg>'
)


def score_color(score: float) -> str:
    """Hex color (no ``#``) for a 0-100 visibility score."""
    if score >= 70:
        return COLOR_GOOD
    if score >= 40:
        return COLOR_FAIR
    return COLOR_POOR


def pluralize(category: str) -> str:
    """``"python http client"`` -> ``"python http clients"`` (best effort).

    Categories that already end in "s" ("running shoes") are kept as they are.
    """
    text = category.strip()
    if not text or text[-1].lower() == "s":
        return text
    if text[-1].lower() == "y" and len(text) > 1 and text[-2].lower() not in "aeiou":
        return text[:-1] + "ies"
    if text.lower().endswith(("x", "ch", "sh", "z")):
        return text + "es"
    return text + "s"


class RankUnavailableError(ValueError):
    """A rank badge needs a category and at least three projects."""


def rank_text(rank: int, total: int, category: str, *, tied: bool = False) -> str:
    """``"#2 of 9 · python http clients"`` (``"tied #2 of 9 · ..."`` on a tie)."""
    prefix = "tied " if tied else ""
    return f"{prefix}#{rank} of {total} · {pluralize(category)}"


def report_rank(report: Report) -> tuple[int, int, bool, str]:
    """``(rank, total, tied, category)`` for a report, by answers mentioning each.

    Raises:
        RankUnavailableError: Without a category or with fewer than three
            projects, with the fix in the message.
    """
    if not report.categories:
        raise RankUnavailableError(
            "A rank badge needs a category: re-run the scan with --category "
            '(e.g. -t "python http client").'
        )
    sov = report.share_of_voice
    entries = list(sov.aggregate.values()) if sov and sov.aggregate else []
    if len(entries) < MIN_RANK_PROJECTS:
        raise RankUnavailableError(
            f"A rank badge needs at least {MIN_RANK_PROJECTS} projects in the "
            f"category (got {len(entries)}): add competitors, e.g. "
            "-c requests -c aiohttp."
        )
    target = sov.aggregate.get(report.brand) if sov else None
    mine = target.appearances if target else 0
    rank = 1 + sum(
        1 for e in entries if e.brand_name != report.brand and e.appearances > mine
    )
    tied = any(e.brand_name != report.brand and e.appearances == mine for e in entries)
    return rank, len(entries), tied, report.categories[0]


def badge_message(report: Report, metric: BadgeMetric = "both") -> str:
    """The badge's right-hand text, e.g. ``"62/100 · SoV 34%"``."""
    if metric == "rank":
        rank, total, tied, category = report_rank(report)
        return rank_text(rank, total, category, tied=tied)
    score = f"{round(report.visibility_score)}/100"
    sov_value = report.share_of_voice.target_share if report.share_of_voice else None
    sov = f"SoV {sov_value:.0%}" if sov_value is not None else None
    if metric == "score" or sov is None:
        return score
    if metric == "sov":
        return sov
    return f"{score} · {sov}"


def _label_and_color(
    report: Report, label: str, metric: BadgeMetric = "both"
) -> tuple[str, str]:
    if report.measurement_tier == "demo":
        return f"{label} · demo", COLOR_DEMO
    if report.partial:
        label = f"{label} · partial"
    if metric == "rank":
        return label, COLOR_RANK
    return label, score_color(report.visibility_score)


def default_label(metric: BadgeMetric) -> str:
    """``"AI rank"`` for rank badges, ``"AI visibility"`` otherwise."""
    return RANK_LABEL if metric == "rank" else DEFAULT_LABEL


def badge_endpoint(
    report: Report,
    *,
    label: str = DEFAULT_LABEL,
    metric: BadgeMetric = "both",
    with_logo: bool = True,
) -> dict[str, Any]:
    """Build a shields.io endpoint-badge JSON document for a report.

    Follows the endpoint schema: ``schemaVersion`` (always 1), ``label``,
    ``message`` (non-empty), plus optional ``color``, ``labelColor`` and
    ``logoSvg``.
    """
    final_label, color = _label_and_color(report, label, metric)
    data: dict[str, Any] = {
        "schemaVersion": 1,
        "label": final_label,
        "message": badge_message(report, metric),
        "color": color,
        "labelColor": LABEL_COLOR,
    }
    if with_logo:
        data["logoSvg"] = LOGO_SVG
    return data


def render_badge_svg(
    report: Report,
    *,
    label: str = DEFAULT_LABEL,
    metric: BadgeMetric = "both",
) -> str:
    """Render a flat, self-contained README badge as SVG."""
    final_label, color = _label_and_color(report, label, metric)
    return render_badge(final_label, badge_message(report, metric), color)


def rank_badge_parts(
    rank: int,
    total: int,
    category: str,
    *,
    demo: bool = False,
    tied: bool = False,
    label: str = RANK_LABEL,
) -> tuple[str, str, str]:
    """``(label, message, color)`` for a rank badge built from any ranking.

    Used for rank badges outside a single report (e.g. the AI Recommendation
    Index). Demo rankings are grey and say "demo".
    """
    message = rank_text(rank, total, category, tied=tied)
    if demo:
        return f"{label} · demo", message, COLOR_DEMO
    return label, message, COLOR_RANK


def rank_endpoint(
    rank: int, total: int, category: str, *, demo: bool = False, tied: bool = False
) -> dict[str, Any]:
    """shields.io endpoint JSON for a rank badge (see :func:`rank_badge_parts`)."""
    label, message, color = rank_badge_parts(
        rank, total, category, demo=demo, tied=tied
    )
    return {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
        "labelColor": LABEL_COLOR,
        "logoSvg": LOGO_SVG,
    }


def render_badge(label: str, message: str, color: str, *, logo: bool = True) -> str:
    """Render a generic two-part flat badge (20px tall, 11px text)."""
    size = 11
    pad = 7
    logo_w = 14 + 5 if logo else 0
    label_text_w = text_width(label, size, safety=False) if label else 0
    msg_text_w = text_width(message, size, bold=True, safety=False)
    left = round(pad + logo_w + label_text_w + pad) if (label or logo) else 0
    right = round(pad + msg_text_w + pad)
    total = left + right
    label_x = pad + logo_w
    msg_x = left + pad
    title = xml(f"{label}: {message}" if label else message)
    logo_markup = f'<g transform="translate({pad} 3)">{_LOGO_RINGS}</g>' if logo else ""
    label_markup = (
        f'<text x="{label_x}" y="14" textLength="{label_text_w:.1f}" '
        f'lengthAdjust="spacingAndGlyphs">{xml(label)}</text>'
        if label
        else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" '
        f'viewBox="0 0 {total} 20" role="img" aria-label="{title}">'
        f"<title>{title}</title>"
        f'<clipPath id="pb-badge-r"><rect width="{total}" height="20" rx="4"/></clipPath>'
        f'<g clip-path="url(#pb-badge-r)">'
        f'<rect width="{left}" height="20" fill="#{LABEL_COLOR}"/>'
        f'<rect x="{left}" width="{right}" height="20" fill="#{color}"/>'
        f"</g>"
        f"{logo_markup}"
        f'<g fill="#fff" font-family="{xml(FONT_STACK)}" font-size="{size}">'
        f"{label_markup}"
        f'<text x="{msg_x}" y="14" font-weight="600" textLength="{msg_text_w:.1f}" '
        f'lengthAdjust="spacingAndGlyphs">{xml(message)}</text>'
        f"</g></svg>"
    )


def shields_url(raw_json_url: str, *, link: str | None = None) -> str:
    """The shields.io image URL for an endpoint JSON hosted at ``raw_json_url``."""
    from urllib.parse import quote

    url = f"https://img.shields.io/endpoint?url={quote(raw_json_url, safe='')}"
    if link:
        url += f"&link={quote(link, safe='')}"
    return url
