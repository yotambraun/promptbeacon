"""Share-ready result cards (1200x630, the Open Graph / social preview size).

One layout, two renderers: :func:`render_card_svg` (no dependencies; good for
READMEs and docs) and :func:`render_card_png` (needs Pillow,
``pip install 'promptbeacon[share]'``; for X, LinkedIn, Slack and Discord,
which do not accept SVG).

The card answers one question — how often does each brand appear in AI
answers for this category? — and is always labelled with how it was measured
(demo data, base model, or web-grounded) so it can't be mistaken for more than
it is.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from promptbeacon.core.schemas import Report
from promptbeacon.share.text import FONT_STACK, Measure, xml
from promptbeacon.share.text import text_width as _estimate
from promptbeacon.share.text import truncate as _truncate

Theme = Literal["light", "dark"]

WIDTH = 1200
HEIGHT = 630
PAD = 72
MAX_ROWS = 6

INDIGO = "#6366F1"
CYAN = "#22D3EE"

_PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "bg": "#FFFFFF",
        "text": "#0F172A",
        "muted": "#64748B",
        "track": "#EEF2F7",
        "bar": "#CBD5E1",
        "target_text": "#4338CA",
        "rule": "#E2E8F0",
    },
    "dark": {
        "bg": "#0B1020",
        "text": "#F8FAFC",
        "muted": "#94A3B8",
        "track": "#1A2236",
        "bar": "#475569",
        "target_text": "#A5B4FC",
        "rule": "#1E293B",
    },
}

_TIER_PILLS = {
    "demo": ("Demo data", "#B45309", "#FEF3C7", "#FCD34D", "#3A2A0A"),
    "base_model": ("Base model", "#334155", "#F1F5F9", "#CBD5E1", "#1E293B"),
    "api_grounded": ("Web-grounded", "#0E7490", "#ECFEFF", "#67E8F9", "#0A2A33"),
}

_PROVIDER_NAMES = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "google": "Google",
    "gemini": "Google",
    "mistral": "Mistral",
    "cohere": "Cohere",
    "perplexity": "Perplexity",
}


# --- data --------------------------------------------------------------------


@dataclass
class CardRow:
    """One brand on the card."""

    name: str
    appearances: int
    total: int
    is_target: bool = False
    rank: int = 0

    @property
    def rate(self) -> float:
        return self.appearances / self.total if self.total else 0.0


@dataclass
class CardData:
    """Everything the card shows, derived from a report."""

    brand: str
    title: str
    subtitle: str
    rows: list[CardRow]
    hidden_rows: int
    tier: str
    footer: str
    date: str
    models: list[str] = field(default_factory=list)


def card_data(report: Report, max_rows: int = MAX_ROWS) -> CardData:
    """Derive the card's content from a scan report."""
    sov = report.share_of_voice
    entries = list(sov.aggregate.values()) if sov and sov.aggregate else []
    entries.sort(
        key=lambda e: (-e.appearances, e.brand_name != report.brand, e.brand_name)
    )
    rows = [
        CardRow(
            name=e.brand_name,
            appearances=e.appearances,
            total=e.total_prompts,
            is_target=e.brand_name == report.brand,
            rank=i + 1,
        )
        for i, e in enumerate(entries)
    ]
    if not rows:
        total = len(report.provider_results)
        present = sum(1 for r in report.provider_results if r.mentions)
        rows = [CardRow(report.brand, present, total, is_target=True, rank=1)]

    shown = rows[:max_rows]
    if not any(r.is_target for r in shown):
        target = next(r for r in rows if r.is_target)
        shown = shown[: max_rows - 1] + [target]
    hidden = len(rows) - len(shown)

    category = report.categories[0] if report.categories else None
    if category:
        title = f"Which {category} does AI recommend?"
    else:
        title = f"Does AI recommend {report.brand}?"

    prompts = len({r.prompt for r in report.provider_results})
    models = sorted(
        {
            f"{_PROVIDER_NAMES.get(r.provider, r.provider)} {r.model}"
            for r in report.provider_results
        }
    )
    n_models = max(len(models), 1)
    subtitle = (
        f"Share of AI answers that mention each brand · {prompts} "
        f"{'prompt' if prompts == 1 else 'prompts'} × {n_models} "
        f"{'model' if n_models == 1 else 'models'}"
    )
    date = (
        report.timestamp.strftime("%b %-d, %Y")
        if _supports_dash()
        else (report.timestamp.strftime("%b %d, %Y"))
    )
    footer = "Asked " + " · ".join(models) if models else "No answers collected"
    return CardData(
        brand=report.brand,
        title=title,
        subtitle=subtitle,
        rows=shown,
        hidden_rows=hidden,
        tier=report.measurement_tier,
        footer=footer,
        date=date,
        models=models,
    )


def _supports_dash() -> bool:
    try:
        datetime(2020, 1, 1).strftime("%-d")
    except ValueError:
        return False
    return True


# --- layout primitives -------------------------------------------------------


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float
    fill: str  # "#RRGGBB" or "gradient"
    rx: float = 0
    stroke: str | None = None


@dataclass
class Text:
    x: float
    y: float  # baseline
    text: str
    size: float
    fill: str
    weight: int = 400
    anchor: Literal["start", "end"] = "start"


@dataclass
class Ring:
    cx: float
    cy: float
    r: float
    width: float
    opacity: float
    fill: bool = False


Shape = Rect | Text | Ring


def layout(
    data: CardData, theme: Theme = "light", measure: Measure | None = None
) -> list[Shape]:
    """Position every element of the card (shared by the SVG and PNG renderers).

    ``measure`` returns a text width in pixels; the PNG renderer passes real
    font metrics, the SVG renderer uses the built-in estimate.
    """
    text_width = measure or _estimate

    def truncate(text: str, max_width: float, size: float, bold: bool = False) -> str:
        return _truncate(text, max_width, size, bold, measure=text_width)

    p = _PALETTES[theme]
    shapes: list[Shape] = [Rect(0, 0, WIDTH, HEIGHT, p["bg"])]
    shapes.append(Rect(0, 0, WIDTH, 8, "gradient"))

    # Header: beacon mark + wordmark, tier pill on the right.
    cx, cy = PAD + 16, 70
    for r, w, op in ((16, 3, 0.35), (10, 3, 0.7)):
        shapes.append(Ring(cx, cy, r, w, op))
    shapes.append(Ring(cx, cy, 4.5, 0, 1.0, fill=True))
    shapes.append(Text(PAD + 44, cy + 7, "PromptBeacon", 20, p["text"], 600))

    label, fg_l, bg_l, fg_d, bg_d = _TIER_PILLS.get(
        data.tier, ("Measurement", "#334155", "#F1F5F9", "#CBD5E1", "#1E293B")
    )
    fg, bg = (fg_l, bg_l) if theme == "light" else (fg_d, bg_d)
    pill_w = text_width(label, 16, bold=True) + 32
    shapes.append(Rect(WIDTH - PAD - pill_w, cy - 18, pill_w, 36, bg, rx=18))
    shapes.append(Text(WIDTH - PAD - 16, cy + 6, label, 16, fg, 600, "end"))

    # Title: shrink, then wrap to two lines, then truncate the second line.
    content_w = WIDTH - 2 * PAD
    size = 50
    while size > 40 and text_width(data.title, size, bold=True) > content_w:
        size -= 2
    lines = _wrap(data.title, content_w, size, text_width)
    while (
        len(lines) > 1
        and size > 34
        and text_width(lines[-1], size, bold=True) > content_w
    ):
        size -= 2
        lines = _wrap(data.title, content_w, size, text_width)
    y = 172.0
    for line in lines:
        shapes.append(
            Text(PAD, y, truncate(line, content_w, size, True), size, p["text"], 700)
        )
        y += size * 1.18
    extra = y - 172 - size * 1.18
    shapes.append(
        Text(PAD, 214 + extra, truncate(data.subtitle, content_w, 21), 21, p["muted"])
    )

    # Rows: name | bar | "9/10", vertically centred in the space left.
    top, bottom = 258 + extra, 540
    n = max(len(data.rows), 1)
    row_h = min(64.0, (bottom - top) / n)
    top += ((bottom - top) - row_h * n) / 2
    name_w = 300
    value_w = 120
    bar_x = PAD + name_w + 24
    bar_w = WIDTH - PAD - value_w - 24 - bar_x
    bar_h = 14 if row_h >= 40 else 10
    name_size = 24 if row_h >= 44 else 20
    for i, row in enumerate(data.rows):
        mid = top + row_h * i + row_h / 2
        color = p["target_text"] if row.is_target else p["text"]
        weight = 700 if row.is_target else 500
        name = truncate(row.name, name_w, name_size, bold=row.is_target)
        shapes.append(Text(PAD, mid + name_size * 0.35, name, name_size, color, weight))
        shapes.append(Rect(bar_x, mid - bar_h / 2, bar_w, bar_h, p["track"], bar_h / 2))
        fill_w = bar_w * max(0.0, min(1.0, row.rate))
        if fill_w > 0:
            fill_w = max(fill_w, bar_h)  # keep tiny values visibly rounded
            shapes.append(
                Rect(
                    bar_x,
                    mid - bar_h / 2,
                    fill_w,
                    bar_h,
                    "gradient" if row.is_target else p["bar"],
                    bar_h / 2,
                )
            )
        value = f"{row.appearances}/{row.total}" if row.total else "–"
        shapes.append(
            Text(
                WIDTH - PAD,
                mid + 9,
                value,
                26,
                color,
                700 if row.is_target else 600,
                "end",
            )
        )

    # Footer.
    shapes.append(Rect(PAD, 560, content_w, 1, p["rule"]))
    right = f"{data.date} · measured with PromptBeacon"
    if data.hidden_rows:
        right = f"+{data.hidden_rows} more · " + right
    right_w = text_width(right, 17)
    shapes.append(Text(WIDTH - PAD, 596, right, 17, p["muted"], 400, "end"))
    footer = truncate(data.footer, content_w - right_w - 32, 17)
    shapes.append(Text(PAD, 596, footer, 17, p["muted"]))
    return shapes


def _wrap(text: str, max_width: float, size: float, measure: Measure) -> list[str]:
    """Split a title into at most two lines (by words, or characters for CJK)."""
    if measure(text, size, True) <= max_width:
        return [text]
    words = text.split(" ")
    units = words if len(words) > 1 else list(text)
    sep = " " if len(words) > 1 else ""
    first: list[str] = []
    for i, unit in enumerate(units):
        candidate = sep.join([*first, unit])
        if first and measure(candidate, size, True) > max_width:
            return [sep.join(first), sep.join(units[i:])]
        first.append(unit)
    return [text]


# --- SVG ---------------------------------------------------------------------


def render_card_svg(report: Report, theme: Theme = "light") -> str:
    """Render the share card as a self-contained SVG (system fonts, no scripts)."""
    data = card_data(report)
    shapes = layout(data, theme)
    summary = "; ".join(f"{r.name} {r.appearances}/{r.total}" for r in data.rows)
    alt = xml(f"{data.title} {summary}. {data.subtitle}.")
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="{alt}">',
        f"<title>{alt}</title>",
        "<defs>"
        f'<linearGradient id="pb-grad" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{INDIGO}"/><stop offset="1" stop-color="{CYAN}"/>'
        "</linearGradient>"
        "</defs>",
        f'<g font-family="{xml(FONT_STACK)}">',
    ]
    for s in shapes:
        if isinstance(s, Rect):
            fill = "url(#pb-grad)" if s.fill == "gradient" else s.fill
            out.append(
                f'<rect x="{s.x:.1f}" y="{s.y:.1f}" width="{s.w:.1f}" '
                f'height="{s.h:.1f}" rx="{s.rx:.1f}" fill="{fill}"/>'
            )
        elif isinstance(s, Ring):
            if s.fill:
                out.append(
                    f'<circle cx="{s.cx}" cy="{s.cy}" r="{s.r}" fill="url(#pb-grad)"/>'
                )
            else:
                out.append(
                    f'<circle cx="{s.cx}" cy="{s.cy}" r="{s.r}" fill="none" '
                    f'stroke="url(#pb-grad)" stroke-width="{s.width}" '
                    f'stroke-opacity="{s.opacity}"/>'
                )
        else:
            anchor = ' text-anchor="end"' if s.anchor == "end" else ""
            out.append(
                f'<text x="{s.x:.1f}" y="{s.y:.1f}" font-size="{s.size}" '
                f'font-weight="{s.weight}" fill="{s.fill}"{anchor}>{xml(s.text)}</text>'
            )
    out.append("</g></svg>")
    return "".join(out)


# --- PNG (optional Pillow) -----------------------------------------------------

_FONT_CANDIDATES = {
    False: [
        "segoeui.ttf",
        "Arial.ttf",
        "arial.ttf",
        "Helvetica.ttc",
        "LiberationSans-Regular.ttf",
        "NotoSans-Regular.ttf",
        "DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ],
    True: [
        "segoeuib.ttf",
        "Arial Bold.ttf",
        "arialbd.ttf",
        "LiberationSans-Bold.ttf",
        "NotoSans-Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ],
}


# Fallbacks for scripts the Latin UI fonts above do not cover.
_CJK_FONTS = [
    "NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
    "C:/Windows/Fonts/malgun.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
]
_WIDE_SCRIPT_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "DejaVuSans.ttf",
    "C:/Windows/Fonts/seguisym.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]


def _script(text: str) -> str:
    """'cjk', 'other' (non-Latin/Greek/Cyrillic/Hebrew) or 'latin'."""
    script = "latin"
    for ch in text:
        cp = ord(ch)
        if 0x2E80 <= cp <= 0x9FFF or 0xAC00 <= cp <= 0xD7AF or 0xF900 <= cp <= 0xFAFF:
            return "cjk"
        if cp > 0x05FF and not (0x2000 <= cp <= 0x206F) and ch not in "…·×–":
            script = "other"
    return script


def _hex(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _mix(a: str, b: str, t: float) -> tuple[int, int, int]:
    ra, ga, ba = _hex(a)
    rb, gb, bb = _hex(b)
    return (
        round(ra + (rb - ra) * t),
        round(ga + (gb - ga) * t),
        round(ba + (bb - ba) * t),
    )


def render_card_png(report: Report, theme: Theme = "light", scale: int = 2) -> bytes:
    """Render the share card as PNG bytes (``scale=2`` gives a crisp 2400x1260).

    Requires Pillow: ``pip install 'promptbeacon[share]'``.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:  # pragma: no cover - exercised via CLI message
        raise ImportError(
            "PNG export needs Pillow: pip install 'promptbeacon[share]'"
        ) from e

    fonts: dict[
        tuple[int, bool, str], ImageFont.FreeTypeFont | ImageFont.ImageFont
    ] = {}

    def font(size: float, bold: bool, script: str = "latin"):
        key = (round(size * scale), bold, script)
        if key not in fonts:
            candidates = list(_FONT_CANDIDATES[bold])
            if script == "cjk":
                candidates = _CJK_FONTS + candidates
            elif script == "other":
                candidates = _WIDE_SCRIPT_FONTS + candidates
            loaded = None
            for name in candidates:
                try:
                    loaded = ImageFont.truetype(name, key[0])
                    break
                except OSError:
                    continue
            fonts[key] = loaded or ImageFont.load_default(size=key[0])
        return fonts[key]

    def measure(text: str, size: float, bold: bool = False) -> float:
        return float(font(size, bold, _script(text)).getlength(text)) / scale

    data = card_data(report)
    shapes = layout(data, theme, measure=measure)
    bg = _PALETTES[theme]["bg"]
    img = Image.new("RGB", (WIDTH * scale, HEIGHT * scale), _hex(bg))
    draw = ImageDraw.Draw(img)

    def gradient_rect(x: float, y: float, w: float, h: float, rx: float) -> None:
        x0, y0 = round(x * scale), round(y * scale)
        x1, y1 = round((x + w) * scale), round((y + h) * scale)
        if x1 <= x0 or y1 <= y0:
            return
        grad = Image.new("RGB", (x1 - x0, y1 - y0))
        gd = ImageDraw.Draw(grad)
        span = max(x1 - x0 - 1, 1)
        for i in range(x1 - x0):
            gd.line([(i, 0), (i, y1 - y0)], fill=_mix(INDIGO, CYAN, i / span))
        mask = Image.new("L", grad.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, grad.size[0] - 1, grad.size[1] - 1],
            radius=round(rx * scale),
            fill=255,
        )
        img.paste(grad, (x0, y0), mask)

    for s in shapes:
        if isinstance(s, Rect):
            if s.fill == "gradient":
                gradient_rect(s.x, s.y, s.w, s.h, s.rx)
                continue
            box = [
                round(s.x * scale),
                round(s.y * scale),
                round((s.x + s.w) * scale) - 1,
                round((s.y + s.h) * scale) - 1,
            ]
            draw.rounded_rectangle(box, radius=round(s.rx * scale), fill=_hex(s.fill))
        elif isinstance(s, Ring):
            color = _mix(bg, INDIGO, s.opacity)
            ring_box = [
                round((s.cx - s.r) * scale),
                round((s.cy - s.r) * scale),
                round((s.cx + s.r) * scale),
                round((s.cy + s.r) * scale),
            ]
            if s.fill:
                draw.ellipse(ring_box, fill=_hex(CYAN))
            else:
                draw.ellipse(ring_box, outline=color, width=round(s.width * scale))
        else:
            anchor = "rs" if s.anchor == "end" else "ls"
            draw.text(
                (s.x * scale, s.y * scale),
                s.text,
                fill=_hex(s.fill),
                font=font(s.size, s.weight >= 600, _script(s.text)),
                anchor=anchor,
            )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
