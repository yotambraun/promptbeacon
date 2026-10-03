"""README badges: a self-contained SVG and a shields.io endpoint JSON.

Two ways to show AI visibility in a README, both generated from a scan report:

* ``render_badge_svg(report)`` — a standalone SVG you commit and reference
  directly (no third-party service involved).
* ``badge_endpoint(report)`` — JSON for shields.io's endpoint badge
  (https://shields.io/badges/endpoint-badge). Commit it and point shields at
  its raw URL: ``https://img.shields.io/endpoint?url=<url-encoded raw URL>``.

Demo reports are labelled as demo and rendered grey, so canned data is never
mistaken for a measurement.
"""

from __future__ import annotations

from typing import Any, Literal

from promptbeacon.core.schemas import Report
from promptbeacon.share.text import FONT_STACK, text_width, xml

BadgeMetric = Literal["both", "score", "sov"]

DEFAULT_LABEL = "AI visibility"

# Accessible (>= 4.5:1 with white text) status colors.
COLOR_GOOD = "15803d"  # green-700
COLOR_FAIR = "b45309"  # amber-700
COLOR_POOR = "b91c1c"  # red-700
COLOR_DEMO = "64748b"  # slate-500
LABEL_COLOR = "1e293b"  # slate-800
COLOR_ERROR = "64748b"

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


def badge_message(report: Report, metric: BadgeMetric = "both") -> str:
    """The badge's right-hand text, e.g. ``"62/100 · SoV 34%"``."""
    score = f"{round(report.visibility_score)}/100"
    sov_value = report.share_of_voice.target_share if report.share_of_voice else None
    sov = f"SoV {sov_value:.0%}" if sov_value is not None else None
    if metric == "score" or sov is None:
        return score
    if metric == "sov":
        return sov
    return f"{score} · {sov}"


def _label_and_color(report: Report, label: str) -> tuple[str, str]:
    if report.measurement_tier == "demo":
        return f"{label} · demo", COLOR_DEMO
    return label, score_color(report.visibility_score)


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
    final_label, color = _label_and_color(report, label)
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
    final_label, color = _label_and_color(report, label)
    return render_badge(final_label, badge_message(report, metric), color)


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
